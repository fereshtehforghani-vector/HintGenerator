"""
demo_lms_upload.py — show the build_rag auto-rebuild path end-to-end.

Story for the audience:
    1. We snapshot the current pgvector collection (uuid + chunk count).
    2. We pick one file under
         AI Pilot/Vector_AI/LMS/LMS_PARSED/rag_output_sdv/
       and upload a copy of it (under a new filename) to
         gs://zebra-rag-documents/LMS/LMS_PARSED/rag_output_sdv/<new>.md
    3. The Eventarc trigger 'build-rag-on-bucket-change' fires
       build-rag-database, which drops the collection, re-chunks every doc
       in the bucket (now including our new file), embeds with Gemini
       Embedding 2, and re-populates pgvector.
    4. We poll the DB until the collection uuid changes AND the chunk
       count comes back above the snapshot — then we report the delta to
       prove the new file got chunked, embedded, and saved.

Usage:
    cd zebra-hint-generator
    python3 demo_lms_upload.py
        ↳ uploads a copy of 00_course_overview.md as 99_demo_new_lesson.md
    python3 demo_lms_upload.py --source 05_working_with_motors.md \\
                               --name   99_demo_motors_copy.md
    python3 demo_lms_upload.py --keep    # leave the demo file in GCS
                                         # (default cleans up + re-rebuilds)

Notes:
  - Real rebuild — overwrites pgvector and burns Gemini embedding quota.
  - Total wall time is dominated by embedding (~1-3 min for ~400 chunks).
  - Auth: same path as demo_show_db.py (DB_PASSWORD env var or Secret
    Manager 'conversation_history_DB-PASSWORD').
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.config import (  # noqa: E402
    BUCKET_NAME,
    COLLECTION_NAME,
    GCP_PROJECT_ID,
    get_db_engine,
    get_secret,
)
from sqlalchemy import text  # noqa: E402


LOCAL_SDV_DIR = (
    Path(__file__).parent.parent
    / "AI Pilot" / "Vector_AI" / "LMS" / "LMS_PARSED" / "rag_output_sdv"
)
GCS_PREFIX = "LMS/LMS_PARSED/rag_output_sdv"
EVENTARC_TRIGGER = "build-rag-on-bucket-change"
REGION = "us-central1"

DEFAULT_SOURCE = "00_course_overview.md"
DEFAULT_DEMO_NAME = "99_demo_new_lesson.md"


def cyan(s):    return f"\033[1;36m{s}\033[0m"
def green(s):   return f"\033[1;32m{s}\033[0m"
def yellow(s):  return f"\033[1;33m{s}\033[0m"
def red(s):     return f"\033[1;31m{s}\033[0m"
def dim(s):     return f"\033[2m{s}\033[0m"

def section(title):
    print()
    print(cyan(f"── {title} ──"))


def resolve_db_password() -> str:
    import os
    pw = os.environ.get("DB_PASSWORD")
    if pw:
        print(dim("  (using DB_PASSWORD from environment)"))
        return pw
    return get_secret("conversation_history_DB-PASSWORD")


def snapshot_collection(conn):
    """Return (uuid, total_chunks, sdv_chunks) for the active collection."""
    uuid = conn.execute(
        text("SELECT uuid FROM langchain_pg_collection WHERE name = :n"),
        {"n": COLLECTION_NAME},
    ).scalar()
    if uuid is None:
        return None, 0, 0
    total = conn.execute(text("""
        SELECT count(*) FROM langchain_pg_embedding e
          JOIN langchain_pg_collection c ON e.collection_id = c.uuid
         WHERE c.name = :n
    """), {"n": COLLECTION_NAME}).scalar() or 0
    sdv = conn.execute(text("""
        SELECT count(*) FROM langchain_pg_embedding e
          JOIN langchain_pg_collection c ON e.collection_id = c.uuid
         WHERE c.name = :n
           AND e.cmetadata->>'course_id' = 'sdv'
    """), {"n": COLLECTION_NAME}).scalar() or 0
    return str(uuid), total, sdv


def count_for_source(conn, source_substr: str) -> int:
    """How many chunks point at a `source` containing this substring."""
    return conn.execute(text("""
        SELECT count(*) FROM langchain_pg_embedding e
          JOIN langchain_pg_collection c ON e.collection_id = c.uuid
         WHERE c.name = :n
           AND e.cmetadata->>'source' LIKE :pat
    """), {"n": COLLECTION_NAME, "pat": f"%{source_substr}%"}).scalar() or 0


def upload_blob(local_path: Path, blob_path: str):
    from google.cloud import storage
    client = storage.Client(project=GCP_PROJECT_ID)
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_path)
    blob.upload_from_filename(str(local_path), content_type="text/markdown")
    print(f"  uploaded gs://{BUCKET_NAME}/{blob_path}  "
          f"({local_path.stat().st_size} bytes)")


def delete_blob(blob_path: str):
    from google.cloud import storage
    client = storage.Client(project=GCP_PROJECT_ID)
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_path)
    if blob.exists():
        blob.delete()
        print(f"  deleted gs://{BUCKET_NAME}/{blob_path}")


def show_eventarc_trigger():
    """Print the wired Eventarc trigger so the audience sees the bucket→service link."""
    import subprocess
    try:
        out = subprocess.check_output(
            ["gcloud", "eventarc", "triggers", "describe", EVENTARC_TRIGGER,
             "--location", REGION, "--project", GCP_PROJECT_ID,
             "--format", "value(name,destination.cloudRun.service,eventFilters)"],
            stderr=subprocess.STDOUT, text=True, timeout=15,
        )
        print("  " + out.strip().replace("\n", "\n  "))
    except Exception as e:
        print(yellow(f"  (could not describe trigger: {e})"))


def drain_pubsub_backlog():
    """Seek the Eventarc subscription to 'now' so any queued retries from
    pre-fix runs don't fire spurious rebuilds during the demo."""
    import subprocess
    sub = "eventarc-us-central1-build-rag-on-bucket-change-sub-082"
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        subprocess.check_output(
            ["gcloud", "pubsub", "subscriptions", "seek", sub,
             "--time", now, "--project", GCP_PROJECT_ID],
            stderr=subprocess.STDOUT, text=True, timeout=15,
        )
        print(f"  drained Pub/Sub subscription up to {now}")
    except Exception as e:
        print(yellow(f"  (could not seek subscription: {e})"))


def _poll_once(engine, before_uuid):
    with engine.connect() as conn:
        uuid_now, total_now, sdv_now = snapshot_collection(conn)
    return uuid_now, total_now, sdv_now


def wait_for_stable(engine, *, poll_every=10, stability_polls=3, timeout=600,
                    label="state"):
    """Poll until (uuid, total) has been unchanged for `stability_polls`
    consecutive polls. Returns the final (uuid, total, sdv)."""
    t0 = time.time()
    history: list[tuple] = []
    last_print = ""
    while time.time() - t0 < timeout:
        uuid_now, total_now, sdv_now = _poll_once(engine, None)
        elapsed = int(time.time() - t0)
        line = f"  t+{elapsed:>3}s  uuid={(uuid_now or 'none')[:8]}  total={total_now}  sdv={sdv_now}"
        if line != last_print:
            print(line)
            last_print = line
        history.append((uuid_now, total_now))
        if len(history) >= stability_polls:
            recent = history[-stability_polls:]
            if all(r == recent[0] for r in recent) and recent[0][0] is not None:
                return uuid_now, total_now, sdv_now
        time.sleep(poll_every)
    raise TimeoutError(f"{label} did not stabilize within {timeout}s.")


def wait_for_rebuild(engine, before_uuid, *, target_min_total,
                     poll_every=10, stability_polls=3, timeout=900):
    """
    Poll until the rebuild fired by our upload has finished:
      Phase 1 — wait for collection uuid to change (drop+create ran).
      Phase 2 — wait until total >= target_min_total AND state is stable
                for `stability_polls` consecutive polls.

    rebuild_vectorstore indexes text first (in 20-doc batches) then images
    in one big batch at the end. Without target_min_total we'd terminate
    on the text plateau between the two phases — that's the bug we hit
    when 'after' came back as 327 (text only) instead of 417 (text+image).
    """
    t0 = time.time()
    saw_uuid_change = False
    history: list[tuple] = []
    last_print = ""
    while time.time() - t0 < timeout:
        uuid_now, total_now, sdv_now = _poll_once(engine, before_uuid)
        elapsed = int(time.time() - t0)

        if uuid_now and uuid_now != before_uuid:
            saw_uuid_change = True

        flag = "NEW" if saw_uuid_change else "same"
        line = (f"  t+{elapsed:>3}s  uuid={flag}  "
                f"total={total_now}  sdv={sdv_now}")
        if line != last_print:
            print(line)
            last_print = line

        if saw_uuid_change and total_now >= target_min_total:
            history.append((uuid_now, total_now))
            if len(history) >= stability_polls:
                recent = history[-stability_polls:]
                if all(r == recent[0] for r in recent):
                    return uuid_now, total_now, sdv_now
        else:
            history.clear()  # plateau below target doesn't count as stable

        time.sleep(poll_every)

    raise TimeoutError(
        f"Rebuild did not finish+stabilize within {timeout}s "
        f"(target_min_total={target_min_total}). "
        f"Check logs:  gcloud run services logs tail build-rag-database "
        f"--region={REGION} --project={GCP_PROJECT_ID}"
    )


def trigger_manual_rebuild():
    """POST to build-rag-database with an authenticated identity token.
    Used in cleanup since GCS delete events don't fire the Eventarc trigger
    (the filter is `finalized`-only)."""
    import subprocess
    import urllib.request
    url = subprocess.check_output(
        ["gcloud", "run", "services", "describe", "build-rag-database",
         "--region", REGION, "--project", GCP_PROJECT_ID,
         "--format", "value(status.url)"],
        text=True, timeout=15,
    ).strip()
    token = subprocess.check_output(
        ["gcloud", "auth", "print-identity-token"],
        text=True, timeout=15,
    ).strip()
    req = urllib.request.Request(
        url, data=b"{}", method="POST",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
    )
    # Fire-and-forget — we don't wait for the (200s+) response here, the
    # caller polls the DB to detect completion. Use a short connect timeout
    # so we don't hang if the service is unhealthy.
    try:
        urllib.request.urlopen(req, timeout=30).read()
    except Exception as e:
        # Even a read timeout is fine — the rebuild has started server-side.
        print(dim(f"  (manual trigger sent; client read returned: {e})"))
        return
    print("  manual trigger accepted; rebuild started.")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--source", default=DEFAULT_SOURCE,
                        help=f"file under {LOCAL_SDV_DIR.name}/ to copy "
                             f"(default: {DEFAULT_SOURCE})")
    parser.add_argument("--name", default=DEFAULT_DEMO_NAME,
                        help=f"new filename in GCS (default: {DEFAULT_DEMO_NAME})")
    parser.add_argument("--keep", action="store_true",
                        help="leave the demo file in GCS at the end "
                             "(default: delete it and trigger a final cleanup rebuild)")
    parser.add_argument("--timeout", type=int, default=600,
                        help="seconds to wait for each rebuild (default: 600)")
    args = parser.parse_args()

    src = LOCAL_SDV_DIR / args.source
    if not src.is_file():
        sys.exit(red(f"local source not found: {src}"))
    if not args.name.endswith(".md"):
        sys.exit(red(f"--name must end in .md (got {args.name!r})"))

    blob_path = f"{GCS_PREFIX}/{args.name}"
    gcs_url = f"gs://{BUCKET_NAME}/{blob_path}"

    # ── Connect ──────────────────────────────────────────────────────────────
    print(cyan("Connecting to Cloud SQL via Cloud SQL Python Connector..."))
    db_password = resolve_db_password()
    engine = get_db_engine(db_password)

    # ── Step 0 · Drain any pending Pub/Sub redeliveries ──────────────────────
    section("Step 0 · Drain Pub/Sub backlog (avoid stale retries firing rebuilds)")
    drain_pubsub_backlog()

    # ── Step 1 · BEFORE snapshot (wait until the DB is stable first) ─────────
    section("Step 1 · BEFORE — wait for a stable starting state, then snapshot")
    print("  If a rebuild is in flight from a prior run, we wait it out so")
    print("  the BEFORE numbers reflect a finished collection, not a partial one.")
    print()
    before_uuid, before_total, before_sdv = wait_for_stable(
        engine, timeout=args.timeout, label="initial state",
    )
    with engine.connect() as conn:
        before_demo_chunks = count_for_source(conn, args.name)
    if before_uuid is None:
        sys.exit(red(
            f"collection '{COLLECTION_NAME}' does not exist yet. "
            "Run an initial build first."
        ))
    print()
    print(f"  collection uuid : {before_uuid}")
    print(f"  total chunks    : {before_total}")
    print(f"  sdv chunks      : {before_sdv}")
    print(f"  chunks already pointing at '{args.name}': {before_demo_chunks}")

    # ── Step 2 · Show the bucket→service trigger ─────────────────────────────
    section(f"Step 2 · Eventarc trigger '{EVENTARC_TRIGGER}'")
    print("  This trigger watches the bucket and invokes build-rag-database")
    print("  on every object change. The handler skips paths outside")
    print("  LMS/LMS_PARSED/, so only LMS uploads cause a rebuild.")
    print()
    show_eventarc_trigger()

    # ── Step 3 · Upload the demo file ────────────────────────────────────────
    section(f"Step 3 · Upload {src.name} → {gcs_url}")
    upload_blob(src, blob_path)
    upload_t = time.time()
    print(green("  upload complete — Eventarc should fire build-rag-database now."))

    # ── Step 4 · Wait for the auto-triggered rebuild to finish ──────────────
    section("Step 4 · Watch the auto-triggered rebuild")
    print("  Polling pgvector every 10s. The collection uuid will change")
    print("  (drop+create), then the chunk count climbs back up as Gemini")
    print("  embeds each batch and PGVector inserts the rows.")
    print()
    # target_min_total guards against the text/image plateau: text indexes
    # first (~327), then images commit in one batch (+90 → 417). Adding a
    # new file should produce at least as many chunks as before.
    after_uuid, after_total, after_sdv = wait_for_rebuild(
        engine, before_uuid,
        target_min_total=before_total,
        timeout=args.timeout,
    )
    rebuild_secs = int(time.time() - upload_t)

    # ── Step 5 · AFTER snapshot + diff ───────────────────────────────────────
    section("Step 5 · AFTER — confirm the new file was indexed")
    with engine.connect() as conn:
        after_demo_chunks = count_for_source(conn, args.name)
    delta_total = after_total - before_total
    delta_sdv = after_sdv - before_sdv
    print(f"  collection uuid : {after_uuid}     "
          f"{green('(new — drop+create ran)') if after_uuid != before_uuid else red('(unchanged?!)')}")
    print(f"  total chunks    : {before_total}  →  {after_total}     "
          f"({'+' if delta_total >= 0 else ''}{delta_total})")
    print(f"  sdv chunks      : {before_sdv}  →  {after_sdv}     "
          f"({'+' if delta_sdv >= 0 else ''}{delta_sdv})")
    verdict = (green("✓ new doc was chunked + embedded + saved")
               if after_demo_chunks > 0
               else red("✗ demo file produced 0 chunks"))
    print(f"  chunks for '{args.name}': "
          f"{before_demo_chunks}  →  {after_demo_chunks}     {verdict}")
    print(f"  rebuild wall time: ~{rebuild_secs}s")

    # ── Step 6 · Cleanup ─────────────────────────────────────────────────────
    section("Step 6 · Cleanup")
    if args.keep:
        print(yellow(f"  --keep set — leaving {gcs_url} in place."))
        print(yellow(f"  Remove later with:  gsutil rm {gcs_url}"))
    else:
        print(f"  Deleting demo file from GCS...")
        delete_blob(blob_path)
        # GCS delete events fire `deleted`, not `finalized`, so the Eventarc
        # trigger doesn't fire on cleanup. Trigger build_rag manually.
        print(f"  Triggering rebuild via authenticated POST...")
        trigger_manual_rebuild()
        print(f"  Waiting for cleanup rebuild to finish (target ~{before_total - 27} chunks,")
        print(f"  i.e. before-state minus the demo file's contribution)...")
        cleanup_uuid, cleanup_total, cleanup_sdv = wait_for_rebuild(
            engine, after_uuid,
            target_min_total=max(before_total - 50, 100),
            timeout=args.timeout,
        )
        print(f"  cleanup rebuild done: total={cleanup_total}  sdv={cleanup_sdv}")

    print()
    print(green("✓ demo complete."))


if __name__ == "__main__":
    main()

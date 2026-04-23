"""
Local demo UI for the ZebraBot RAG hint generator.

Usage:
    cd zebra-hint-generator
    GOOGLE_API_KEY=<key> OPENAI_API_KEY=<key> python3 demo_app.py
    → open http://localhost:8080

Upload rules:
    - .cpp file  → course_id = "sdv"
    - image file → course_id = "reactive_robtics"
"""

import os
import sys
from pathlib import Path

from flask import Flask, jsonify, redirect, request, send_file
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).parent))
from shared.rag_utils import get_retriever, get_vectorstore
from shared.tutor import AgenticTutor

# ── config ─────────────────────────────────────────────────────────────────────
LOCAL_DB_URL    = "postgresql+psycopg://fereshteh@localhost:5432/zbot_rag"
COLLECTION_NAME = "zbot_chunks"
REPO_ROOT       = Path(__file__).parent.parent.resolve()

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
CPP_EXTS   = {".cpp", ".h", ".hpp", ".ino", ".cc"}

for key in ("OPENAI_API_KEY", "GOOGLE_API_KEY"):
    if not os.environ.get(key):
        raise EnvironmentError(f"{key} is not set. Export it before running this script.")

app = Flask(__name__)


# ── HTML (inline so there is no templates/ dir to manage) ──────────────────────
INDEX_HTML = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>ZebraBot Hint Generator — Demo</title>
<style>
  :root { --bg:#0f172a; --panel:#1e293b; --text:#e2e8f0; --muted:#94a3b8; --accent:#38bdf8; --ok:#22c55e; --warn:#f59e0b; }
  body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:var(--bg); color:var(--text); }
  .wrap { max-width: 960px; margin: 0 auto; padding: 32px 24px; }
  h1 { margin:0 0 8px; font-size:24px; }
  .sub { color:var(--muted); margin-bottom:24px; font-size:14px; }
  .card { background:var(--panel); border-radius:12px; padding:20px; margin-bottom:16px; }
  label { display:block; font-size:13px; color:var(--muted); margin-bottom:6px; }
  input[type=file], textarea { width:100%; box-sizing:border-box; background:#0b1220; color:var(--text); border:1px solid #334155; border-radius:8px; padding:10px; font-family:inherit; font-size:14px; }
  textarea { min-height:80px; resize:vertical; }
  button { background:var(--accent); color:#0b1220; border:0; border-radius:8px; padding:10px 18px; font-weight:600; cursor:pointer; font-size:14px; }
  button:disabled { opacity:.5; cursor:progress; }
  .meta { font-size:13px; color:var(--muted); margin-top:8px; }
  .meta b { color:var(--text); }
  #response { white-space:pre-wrap; line-height:1.55; }
  #response a.cite { color:var(--accent); text-decoration:none; font-weight:600; background:#0b1220; padding:1px 6px; border-radius:4px; }
  #response a.cite:hover { text-decoration:underline; }
  .ref { border-left:3px solid var(--accent); padding:10px 14px; background:#0b1220; border-radius:6px; margin-top:10px; }
  .ref h4 { margin:0 0 4px; font-size:14px; }
  .ref .rmeta { font-size:12px; color:var(--muted); margin-bottom:6px; }
  .ref .rcontent { font-size:13px; color:#cbd5e1; white-space:pre-wrap; max-height:120px; overflow:hidden; position:relative; }
  .hint { color:var(--warn); font-size:12px; margin-top:4px; }
  .err { color:#f87171; }
</style>
</head>
<body>
<div class="wrap">
  <h1>ZebraBot Hint Generator</h1>
  <div class="sub">Upload a <b>.cpp file</b> (Self Driving Car) or an <b>image</b> (Reactive Robotics), add your question, and get a Socratic hint.</div>

  <div class="card">
    <label for="file">Upload file (.cpp or image)</label>
    <input id="file" type="file" accept=".cpp,.h,.hpp,.ino,image/*">
    <div id="fileMeta" class="meta"></div>

    <label for="question" style="margin-top:16px">Your question</label>
    <textarea id="question" placeholder="e.g. Why doesn't my stop condition trigger?"></textarea>

    <div style="margin-top:14px; display:flex; align-items:center; gap:12px;">
      <button id="submit">Ask ZebraBot</button>
      <span id="status" class="meta"></span>
    </div>
  </div>

  <div id="result" class="card" style="display:none">
    <h3 style="margin-top:0">Response</h3>
    <div id="response"></div>
    <h3 id="refsHeader" style="display:none">LMS References</h3>
    <div id="refs"></div>
  </div>
</div>

<script>
const fileInput = document.getElementById('file');
const fileMeta  = document.getElementById('fileMeta');
const question  = document.getElementById('question');
const submit    = document.getElementById('submit');
const status    = document.getElementById('status');
const result    = document.getElementById('result');
const responseEl= document.getElementById('response');
const refsEl    = document.getElementById('refs');
const refsHeader= document.getElementById('refsHeader');

function detectCourse(file) {
  if (!file) return { kind: null, course: null };
  const ext = file.name.toLowerCase().match(/\\.[^.]+$/)?.[0] || '';
  if (file.type.startsWith('image/')) return { kind: 'image', course: 'reactive_robtics' };
  if (['.cpp','.h','.hpp','.ino','.cc'].includes(ext)) return { kind: 'cpp', course: 'sdv' };
  return { kind: 'other', course: null };
}

fileInput.addEventListener('change', () => {
  const f = fileInput.files[0];
  if (!f) { fileMeta.textContent = ''; return; }
  const { kind, course } = detectCourse(f);
  if (!course) {
    fileMeta.innerHTML = '<span class="err">Unsupported file type. Use .cpp or an image.</span>';
  } else {
    fileMeta.innerHTML = `Detected: <b>${kind}</b> → course_id = <b>${course}</b>`;
  }
});

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function linkifyCitations(text, refs) {
  const byRef = {};
  refs.forEach(r => { byRef[r.ref] = r; });
  // Replace [1], [2], ... with clickable links when we have a matching ref
  return escapeHtml(text).replace(/\\[(\\d+)\\]/g, (m, n) => {
    const r = byRef[parseInt(n, 10)];
    if (!r || !r.source) return m;
    const url = '/api/source?path=' + encodeURIComponent(r.source);
    return `<a class="cite" target="_blank" href="${url}" title="${escapeHtml(r.title || '')}">[${n}]</a>`;
  });
}

function renderRefs(refs) {
  refsEl.innerHTML = '';
  if (!refs.length) { refsHeader.style.display = 'none'; return; }
  refsHeader.style.display = '';
  refs.forEach(r => {
    const url = '/api/source?path=' + encodeURIComponent(r.source);
    const div = document.createElement('div');
    div.className = 'ref';
    div.innerHTML = `
      <h4>[${r.ref}] <a class="cite" target="_blank" href="${url}">${escapeHtml(r.title || '(untitled)')}</a></h4>
      <div class="rmeta">${escapeHtml(r.course || '')} (${escapeHtml(r.course_id || '')}) · module ${r.module}</div>
      <div class="rcontent">${escapeHtml((r.content || '').slice(0, 400))}…</div>`;
    refsEl.appendChild(div);
  });
}

submit.addEventListener('click', async () => {
  const f = fileInput.files[0];
  if (!f) { status.innerHTML = '<span class="err">Please upload a file.</span>'; return; }
  const { kind, course } = detectCourse(f);
  if (!course) { status.innerHTML = '<span class="err">Unsupported file type.</span>'; return; }

  submit.disabled = true;
  status.textContent = 'Running RAG query...';
  result.style.display = 'none';

  const fd = new FormData();
  fd.append('file', f);
  fd.append('question', question.value);
  fd.append('kind', kind);
  fd.append('course_id', course);

  try {
    const res  = await fetch('/api/query', { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Request failed');
    responseEl.innerHTML = linkifyCitations(data.response || '', data.lms_references || []);
    renderRefs(data.lms_references || []);
    result.style.display = '';
    status.textContent = `Done in ${Math.round(data.latency_ms || 0)} ms`;
  } catch (e) {
    status.innerHTML = '<span class="err">Error: ' + escapeHtml(e.message) + '</span>';
  } finally {
    submit.disabled = false;
  }
});
</script>
</body>
</html>
"""


# ── RAG setup (build once, reuse) ──────────────────────────────────────────────
_engine      = create_engine(LOCAL_DB_URL)
_vectorstore = get_vectorstore(_engine, COLLECTION_NAME)


# ── routes ─────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return INDEX_HTML


@app.route("/api/query", methods=["POST"])
def api_query():
    import time

    f         = request.files.get("file")
    question  = request.form.get("question", "")
    kind      = request.form.get("kind", "")
    course_id = request.form.get("course_id") or None

    if not f:
        return jsonify({"error": "No file uploaded"}), 400

    retriever = get_retriever(_vectorstore, top_k=10, course_id=course_id)
    tutor     = AgenticTutor(provider="OpenAI", retriever=retriever, enable_security=False)

    t0 = time.perf_counter()
    if kind == "image":
        image_bytes = f.read()
        result = tutor.analyse_image(image_bytes, question)
    else:
        code = f.read().decode("utf-8", errors="replace")
        result = tutor.analyse_code(code, question)
    elapsed = (time.perf_counter() - t0) * 1000

    result["latency_ms"] = elapsed
    return jsonify(result)


@app.route("/api/source")
def api_source():
    """Serve an LMS source file so [N] citation links can open it in a new tab.

    If the source is an http(s) URL (image chunks and GCS-backed lessons),
    redirect to it. Otherwise treat it as a local path — only files inside
    REPO_ROOT are allowed, which blocks path-traversal attempts.
    """
    raw = request.args.get("path", "")
    if not raw:
        return "Missing path", 400
    if raw.startswith(("http://", "https://")):
        return redirect(raw, code=302)
    try:
        target = Path(raw).resolve()
    except OSError:
        return "Invalid path", 400
    if REPO_ROOT not in target.parents and target != REPO_ROOT:
        return "Path outside repo root", 403
    if not target.is_file():
        return "Not found", 404
    mimetype = "text/markdown" if target.suffix == ".md" else None
    return send_file(str(target), mimetype=mimetype)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Demo UI: http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)

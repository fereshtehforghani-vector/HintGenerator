import gradio as gr
import requests
import shutil
import subprocess
import os
import re
import sys
import uuid
import json

from sqlalchemy import text

from shared.config import get_db_engine, get_secret

# If running from test_frontend.sh, comment the following line and uncomment the one after that
QUERY_RAG_URL = "https://query-rag-773402166266.us-central1.run.app"
# QUERY_RAG_URL = os.environ.get("QUERY_RAG_URL")
if not QUERY_RAG_URL:
    sys.exit("QUERY_RAG_URL is not set. Run via test_frontend.sh, or export "
             "QUERY_RAG_URL=https://<your-cloud-run-host> before running.")


def fetch_students() -> tuple[list[tuple[str, int]], dict[int, str]]:
    """Pull (label, student_id) pairs from the Cloud SQL `students` table so the
    dropdown reflects whoever is actually seeded. Also returns a {student_id:
    track} map used to toggle the C++ paste box. Requires gcloud auth with
    Secret Manager + Cloud SQL access."""
    engine = get_db_engine(get_secret("conversation_history_DB-PASSWORD"))
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT student_id, name, grade, track FROM students ORDER BY student_id")
        ).fetchall()
    choices: list[tuple[str, int]] = []
    tracks: dict[int, str] = {}
    for sid, name, grade, track in rows:
        bits = [str(name or f"student {sid}")]
        if grade:
            bits.append(f"grade {grade}")
        if track:
            bits.append(track)
        choices.append((f"{' • '.join(bits)} (id={sid})", sid))
        tracks[sid] = (track or "").lower()
    return choices, tracks


STUDENT_CHOICES, STUDENT_TRACKS = fetch_students()
if not STUDENT_CHOICES:
    sys.exit("No rows found in `students` table — seed it before running the demo.")


_VIMEO_PLAYER_RE = re.compile(r"https?://player\.vimeo\.com/video/(\d+)")


def _viewable_video_url(url: str) -> str:
    """Vimeo player.vimeo.com/video/<id> URLs are embed-only and 403 in a
    browser tab. Rewrite them to vimeo.com/<id>, which is the public viewer
    page. Other URLs pass through unchanged."""
    m = _VIMEO_PLAYER_RE.match(url)
    if m:
        return f"https://vimeo.com/{m.group(1)}"
    return url

# TODO: Change my authentication token - ideally the user should be able to be authenticated from the front-end in their own way
def get_auth_token():
    # Resolve `gcloud` via PATH so this works on Windows (gcloud.cmd), macOS,
    # and Linux without needing shell=True (which breaks list-args on Unix).
    gcloud = shutil.which("gcloud")
    if not gcloud:
        sys.exit("gcloud CLI not found on PATH. Install the Google Cloud SDK "
                 "and run `gcloud auth login` before starting this script.")
    result = subprocess.run(
        [gcloud, "auth", "print-identity-token"],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        sys.exit(f"`gcloud auth print-identity-token` failed: "
                 f"{result.stderr.strip() or 'empty token'}")
    return result.stdout.strip()

# Once the user submits a message to the Gradio chatbot, this function is called. It takes in the user's message (which includes the query text and optionally a file), the pasted code (cpp-track only), and the current chat display.
def handle_request(message: dict, pasted_code: str, chat_display: list, conversation_id: str, student_id: int):
    try:
        query = message["text"]
        file = message["files"][0] if message["files"] else None
        pasted_code = (pasted_code or "").strip()

        # Get auth token and send request to Cloud Function, along with the user's query, file type, and file data (if they exist)
        token = get_auth_token()
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "query": query,
            "conversation_id": conversation_id,
            "student_id": student_id,
        }
        # Only include `code` when the student actually pasted something. A
        # .cpp file upload (handled below) takes priority server-side at
        # query_rag/main.py:108, so sending both is harmless but the file wins.
        if pasted_code:
            data["code"] = pasted_code

        # If the user attached a file, include it in the request to the Cloud Function.
        if file:
            with open(file, "rb") as f:
                response = requests.post(
                    QUERY_RAG_URL,
                    headers=headers,
                    data=data,
                    files={"file": (os.path.basename(file), f)},
                    stream=True,
                )
        # If the user did not attach a file, just send the query and conversation ID to the Cloud Function.
        else:
            response = requests.post(
                QUERY_RAG_URL,
                headers=headers,
                data=data,
                stream=True,
            )

        # add user message to chat display immediately — show the file/code too if present
        if file:
            chat_display.append({"role": "user", "content": {"path": file}})
        if pasted_code:
            chat_display.append({"role": "user", "content": f"```cpp\n{pasted_code}\n```"})
        if query:
            chat_display.append({"role": "user", "content": query})
        chat_display.append({"role": "assistant", "content": ""})  # placeholder for streaming response

        # MODIFIED - stream chunks and yield updated chat display as each chunk arrives
        accumulated = ""
        print("RAW RESPONSE: ", end="", flush=True)  # print label before chunks start
        for chunk in response.iter_content(chunk_size=None, decode_unicode=True):  # iterate over streamed chunks
            if chunk:
                print(chunk, end="", flush=True)  # print each chunk to terminal as it arrives
                accumulated += chunk  # build up the full response
                chat_display[-1] = {"role": "assistant", "content": accumulated}  # update last message with new chunk
                yield {"text": "", "files": []}, "", chat_display, chat_display, conversation_id, student_id  # yield updated display to Gradio
        print()  # print newline after full response is done

        # Append curriculum references parsed from the X-LMS-References header.
        try:
            refs = json.loads(response.headers.get("X-LMS-References", "[]"))
        except Exception:
            refs = []
        if refs:
            lines = ["\n\n---\n**References**"]
            for r in refs:
                title = r.get("title") or r.get("source", "reference")
                src   = r.get("source", "")
                meta  = []
                if r.get("course"):
                    meta.append(r["course"])
                if r.get("module"):
                    meta.append(f"module {r['module']}")
                suffix = f" — {', '.join(meta)}" if meta else ""
                lines.append(f"- [{r.get('ref','?')}] [{title}]({src}){suffix}")
                for i, vid in enumerate(r.get("video_urls") or [], 1):
                    viewable = _viewable_video_url(vid)
                    lines.append(f"    - 🎥 [Video {i}]({viewable})")
            chat_display[-1] = {"role": "assistant", "content": accumulated + "\n".join(lines)}
            yield {"text": "", "files": []}, "", chat_display, chat_display, conversation_id, student_id

    except Exception as e:
        chat_display.append({"role": "user", "content": message["text"]})
        chat_display.append({"role": "assistant", "content": f"Error: {str(e)}"})
        yield {"text": "", "files": []}, "", chat_display, chat_display, conversation_id, student_id


# Use Gradio for the demo as the front end - TODO: change later
CHATBOT_CSS = """
#tutor-chatbot img {
    max-width: 180px !important;
    max-height: 180px !important;
    object-fit: contain;
    border-radius: 6px;
}
"""

with gr.Blocks(css=CHATBOT_CSS) as demo:
    gr.Markdown("# 🤖 Zebra Robotics AI Tutor")

    chat_display = gr.State([])
    conversation_id = gr.State()

    student_id = gr.Dropdown(
        choices=STUDENT_CHOICES,
        value=STUDENT_CHOICES[0][1],
        label="Pretend to be student",
        interactive=True,
    )

    chatbot = gr.Chatbot(height=500, show_label=False, elem_id="tutor-chatbot")

    # C++ paste box — only visible for cpp-track students. Initial visibility
    # is set on demo.load below so it matches the default-selected student.
    code_box = gr.Code(
        language="cpp",
        label="Paste your C++ code (optional)",
        visible=False,
        lines=10,
    )

    chat_input = gr.MultimodalTextbox(
        placeholder="Describe your problem and optionally attach a screenshot or .cpp file...",
        file_types=[".png", ".jpg", ".jpeg", ".webp", ".cpp"],
        show_label=False
    )

    # Fresh conversation_id per browser session (each new tab). The selected
    # student_id comes from the dropdown above, populated from the `students`
    # table at startup. Initial code-box visibility tracks that student.
    def _on_load():
        default_sid = STUDENT_CHOICES[0][1]
        is_cpp = STUDENT_TRACKS.get(default_sid) == "cpp"
        return str(uuid.uuid4()), gr.update(visible=is_cpp, value="")

    demo.load(
        fn=_on_load,
        outputs=[conversation_id, code_box],
    )

    # Toggle the code box when the active student changes. Clear the value on
    # switch so one student's paste doesn't leak into another's session.
    def _toggle_code_box(sid):
        is_cpp = STUDENT_TRACKS.get(sid) == "cpp"
        return gr.update(visible=is_cpp, value="")

    student_id.change(
        fn=_toggle_code_box,
        inputs=[student_id],
        outputs=[code_box],
    )

    chat_input.submit(
        fn=handle_request,
        inputs=[chat_input, code_box, chat_display, conversation_id, student_id],
        outputs=[chat_input, code_box, chatbot, chat_display, conversation_id, student_id]
    )

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())

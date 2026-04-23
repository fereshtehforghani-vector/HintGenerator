"""
Student upload handling for query_rag.

Receives a multipart/form-data request, detects whether the attached file is
an image (block-code screenshot) or a C++ source file, and for images uploads
the bytes to the ``zebra-robotics-images`` bucket and returns a V4 signed URL
so downstream vision LLMs (and the frontend) can read the object without
needing to grant them direct bucket access.

Ported from core_runtime_loop/file_handler.py with two changes:
  * Bucket name comes from shared.config so there is one source of truth.
  * Image bytes are returned alongside the signed URL so analyse_image()
    can embed the image directly into the LLM prompt (no extra fetch).
"""

import datetime
import mimetypes
import uuid

import google.auth
from google.auth.transport import requests as google_requests
from google.cloud import storage

from shared.config import UPLOAD_BUCKET_NAME


_storage_client = None


def _client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client


def _guess_content_type(filename: str) -> str:
    ctype, _ = mimetypes.guess_type(filename)
    return ctype or "application/octet-stream"


def _upload_image_and_sign(file_to_store) -> tuple[bytes, str]:
    """Upload the image to GCS and return (bytes, signed_url).

    The signed URL is valid for 30 minutes — long enough for the LLM call
    and for the frontend to re-render the image in the chat transcript.
    """
    file_to_store.stream.seek(0)
    img_bytes = file_to_store.stream.read()

    bucket      = _client().bucket(UPLOAD_BUCKET_NAME)
    object_name = (
        f"uploads/{datetime.datetime.utcnow().strftime('%Y/%m/%d')}/"
        f"{uuid.uuid4()}_{file_to_store.filename}"
    )
    blob = bucket.blob(object_name)
    blob.upload_from_string(
        img_bytes,
        content_type=file_to_store.mimetype or _guess_content_type(file_to_store.filename),
    )

    # Cloud Run's default credentials can't sign blobs directly — refresh
    # them first so generate_signed_url has a usable token.
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(google_requests.Request())

    signed_url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=30),
        method="GET",
        credentials=credentials,
    )
    return img_bytes, signed_url


def process_file(request) -> tuple[str | None, object, str | None]:
    """Inspect the incoming request and return (file_type, file_data, stored_file_url).

    Returns:
        ("image", <bytes>, <signed_url>)  — image upload
        ("cpp",   <str>,   None)          — C++ source file upload
        (None,    None,    None)          — no file attached (pure JSON request)
    """
    uploaded = request.files.get("file") if request.files else None
    if uploaded is None:
        return None, None, None

    name = (uploaded.filename or "").lower()
    if name.endswith((".png", ".jpg", ".jpeg", ".webp")):
        img_bytes, signed_url = _upload_image_and_sign(uploaded)
        return "image", img_bytes, signed_url
    if name.endswith(".cpp"):
        code = uploaded.read().decode("utf-8")
        return "cpp", code, None

    raise ValueError("Unsupported file type. Only image and .cpp files are allowed.")

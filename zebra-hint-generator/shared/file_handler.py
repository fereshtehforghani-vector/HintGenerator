"""
Student upload handling for query_rag.
Ported from core_runtime_loop/file_handler.py — uses base64 instead of
signed URLs to avoid Service Account Token Creator permission requirement.
"""

import base64
import datetime
import io
import mimetypes
import uuid

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


def _upload_image_and_get_base64(file_to_store) -> tuple[bytes, str]:
    """Upload image to GCS and return (bytes, object_name).
    
    The raw bytes are returned so analyse_image() can embed them directly
    into the LLM prompt without needing a public URL.
    The object_name is the GCS path stored in the conversation history DB.
    """
    file_to_store.stream.seek(0)
    img_bytes = file_to_store.stream.read()

    bucket = _client().bucket(UPLOAD_BUCKET_NAME)
    object_name = (
        f"uploads/{datetime.datetime.utcnow().strftime('%Y/%m/%d')}/"
        f"{uuid.uuid4()}_{file_to_store.filename}"
    )
    blob = bucket.blob(object_name)
    blob.upload_from_file(
        io.BytesIO(img_bytes),
        content_type=file_to_store.mimetype or _guess_content_type(file_to_store.filename),
    )

    # Return raw bytes for LLM and object_name for DB storage
    return img_bytes, object_name


def process_file(request) -> tuple[str | None, object, str | None]:
    """Inspect the incoming request and return (file_type, file_data, stored_file_url).

    Returns:
        ("image", <bytes>, <gcs_object_name>)  — image upload
        ("cpp",   <str>,   None)               — C++ source file upload
        (None,    None,    None)               — no file attached
    """
    uploaded = request.files.get("file") if request.files else None
    if uploaded is None:
        return None, None, None

    name = (uploaded.filename or "").lower()
    if name.endswith((".png", ".jpg", ".jpeg", ".webp")):
        img_bytes, object_name = _upload_image_and_get_base64(uploaded)
        return "image", img_bytes, object_name
    if name.endswith(".cpp"):
        code = uploaded.read().decode("utf-8")
        return "cpp", code, None

    raise ValueError("Unsupported file type. Only image and .cpp files are allowed.")
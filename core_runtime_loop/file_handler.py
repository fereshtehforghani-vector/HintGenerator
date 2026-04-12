""" 
This file handles the uploaded files from the user interface. It detects the file type, stores images in Cloud Storage, and returns the processed payload that the model.py file should use.
"""

import datetime  # Used to generate timestamps for organizing files (e.g., by date folders)
import mimetypes  # Used to guess file types (e.g., image/jpeg) from filenames
import uuid  # Used to generate unique IDs so filenames don’t collide
from google.cloud import storage  # GCP library for interacting with Cloud Storage
import google.auth
from google.auth.transport import requests as google_requests

# Create a global Cloud Storage client (used to interact with buckets)
storage_client = storage.Client()

BUCKET_NAME = "zebra-robotics-images"  # The name of your Cloud Storage bucket


# Helper function to guess the content type of a file based on its filename
def _guess_content_type(filename: str) -> str:
    content_type, _ = mimetypes.guess_type(filename)  # Try to infer MIME type
    return content_type or "application/octet-stream"  # Fallback if unknown


# Helper function that:
# 1. Uploads the image to Cloud Storage
# 2. Generates a signed URL so it can be accessed temporarily
def _upload_image_and_get_signed_url(file_to_store):
    # Get the bucket object
    bucket = storage_client.bucket(BUCKET_NAME)

    # Create a unique object path - Example: uploads/2026/04/03/uuid_filename.jpg
    object_name = f"uploads/{datetime.datetime.utcnow().strftime('%Y/%m/%d')}/{uuid.uuid4()}_{file_to_store.filename}"

    # Create a blob (file object in GC storage) with the unique object name
    blob = bucket.blob(object_name)

    # Reset file pointer to the beginning, to ensure it will be read from the beginning
    file_to_store.stream.seek(0)

    # Upload the file stream to GC storage
    blob.upload_from_file(
        file_to_store.stream, # This is the actual file content being uploaded
        content_type=file_to_store.mimetype or _guess_content_type(file_to_store.filename)
    )

    # Get the default credentials from the Cloud Run environment
    # On Cloud Run, google.auth.default() automatically retrieves the service account credentials that the Cloud Function is running as - no key file needed
    credentials, project = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])

    # Refresh the credentials to make sure they are not expired
    # Cloud Run credentials expire periodically, so we refresh them before signing
    credentials.refresh(google_requests.Request())

    # Generate a signed URL (temporary public access link)
    # This now works on Cloud Run because we are explicitly passing in the refreshed credentials
    # instead of relying on a local key file
    signed_url = blob.generate_signed_url(
        version="v4",  # modern secure signing method
        expiration=datetime.timedelta(minutes=30),  # URL valid for 30 minutes
        method="GET",  # allows read access
        credentials=credentials  # explicitly pass the refreshed service account credentials
    )

    # Return the URL that can be passed to the model
    return signed_url


# This function handles the incoming file type - It detects the file type, stores images in Cloud Storage, and returns the processed payload that the model.py file should use.
def process_file(request):

    # Try to get the uploaded file from the request (multipart/form-data)
    uploaded_file = request.files.get("file")

    # CASE 1: No file was uploaded (fallback to JSON-based input)
    if uploaded_file is None:
        request_json = request.get_json(silent=True) or {}  # parse JSON safely

        # Return: file_type (if provided, else None), file_data (if provided, else None), and None for image_url
        return request_json.get("file_type", None), request_json.get("file_data", None), None

    # Get filename and normalize to lowercase for easier checking
    filename = uploaded_file.filename or ""
    lowered_filename = filename.lower()

    # CASE 2: Image file
    if lowered_filename.endswith((".png", ".jpg", ".jpeg", ".webp")):
        file_type = "image"

        # Upload image to Cloud Storage + get signed URL
        file_data = _upload_image_and_get_signed_url(uploaded_file)

        # Return:
        # file_type → "image"
        # file_data → signed URL (used by model)
        # third value → also URL (for storing in DB if needed)
        return file_type, file_data, file_data

    # CASE 3: C++ file
    if lowered_filename.endswith(".cpp"):
        file_type = "cpp"

        # Read file contents as text (decode from bytes to string)
        file_data = uploaded_file.read().decode("utf-8")

        # Return:
        # file_type → "cpp"
        # file_data → raw code string
        # None → no image URL to store
        return file_type, file_data, None

    # CASE 4: Unsupported file type
    raise ValueError("Unsupported file type. Only image files and .cpp files are allowed.")
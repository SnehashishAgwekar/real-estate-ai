"""Filesystem locations and helpers for user-uploaded files."""
import os
import shutil
import uuid

from fastapi import UploadFile

# .../backend  (this file is at .../backend/app/core/storage.py)
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# On-disk: backend/static  and  backend/static/uploads
STATIC_DIR = os.path.join(BACKEND_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")

# URL prefix the uploads are served under (see StaticFiles mount in main.py)
UPLOAD_URL_PREFIX = "/static/uploads"

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_EXT_BY_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def save_upload_image(upload: UploadFile) -> str:
    """
    Persist one uploaded image to backend/static/uploads/ under a random name
    and return its server-relative URL (e.g. "/static/uploads/ab12cd34.jpg").
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    ext = _EXT_BY_TYPE.get(upload.content_type or "")
    if ext is None:
        # fall back to the original extension when the content type is unknown
        _, orig_ext = os.path.splitext(upload.filename or "")
        ext = orig_ext.lower() or ".jpg"

    filename = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(UPLOAD_DIR, filename)

    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)
    finally:
        upload.file.close()

    return f"{UPLOAD_URL_PREFIX}/{filename}"

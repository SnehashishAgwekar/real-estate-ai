"""Storage for user-uploaded files: Supabase Storage when configured, local
disk otherwise.

Local disk only ever puts the file on whichever machine's backend happens to
receive the upload — fine for one person's own dev setup, but broken the
moment a second person's frontend needs to see the same photo (their
backend never had the file). Supabase Storage fixes that: every broker's
uploads land in the same shared bucket, so the returned URL works for
anyone, not just the machine that received the request.
"""
import os
import uuid

import requests
from dotenv import load_dotenv
from fastapi import UploadFile

load_dotenv()

# .../backend  (this file is at .../backend/app/core/storage.py)
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# On-disk: backend/static  and  backend/static/uploads
STATIC_DIR = os.path.join(BACKEND_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")

# URL prefix the local-disk fallback is served under (see StaticFiles mount
# in main.py) — irrelevant once Supabase Storage is configured.
UPLOAD_URL_PREFIX = "/static/uploads"

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_EXT_BY_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "property-images")


def _supabase_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SECRET_KEY)


def _resolve_extension(upload: UploadFile) -> str:
    ext = _EXT_BY_TYPE.get(upload.content_type or "")
    if ext:
        return ext
    # fall back to the original extension when the content type is unknown
    _, orig_ext = os.path.splitext(upload.filename or "")
    return orig_ext.lower() or ".jpg"


def _upload_to_supabase(data: bytes, filename: str, content_type: str) -> str:
    url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{filename}"
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
            "apikey": SUPABASE_SECRET_KEY,
            "Content-Type": content_type or "application/octet-stream",
        },
        data=data,
        timeout=30,
    )
    resp.raise_for_status()
    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/{filename}"


def _save_to_local_disk(data: bytes, filename: str) -> str:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    dest_path = os.path.join(UPLOAD_DIR, filename)
    with open(dest_path, "wb") as buffer:
        buffer.write(data)
    return f"{UPLOAD_URL_PREFIX}/{filename}"


def save_upload_image(upload: UploadFile) -> str:
    """
    Persist one uploaded image and return the URL it's reachable at —
    Supabase Storage's public URL when SUPABASE_URL/SUPABASE_SECRET_KEY are
    set, otherwise a server-relative backend/static/uploads/ path (works
    only for whoever's own backend received the upload).
    """
    filename = f"{uuid.uuid4().hex}{_resolve_extension(upload)}"

    try:
        data = upload.file.read()
    finally:
        upload.file.close()

    if _supabase_configured():
        return _upload_to_supabase(data, filename, upload.content_type)

    return _save_to_local_disk(data, filename)


def delete_uploaded_image(url: str) -> None:
    """
    Best-effort delete of a previously-uploaded image, whichever backend
    stored it — used when a broker removes a photo from a listing or
    deletes the listing entirely. Silently no-ops for URLs we don't own
    (e.g. the seed data's external stock photos), and never raises: a
    failed cleanup shouldn't block the edit/delete the user asked for.
    """
    if not url:
        return

    supabase_prefix = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/"
    if _supabase_configured() and url.startswith(supabase_prefix):
        filename = url[len(supabase_prefix):]
        try:
            requests.delete(
                f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{filename}",
                headers={"Authorization": f"Bearer {SUPABASE_SECRET_KEY}", "apikey": SUPABASE_SECRET_KEY},
                timeout=15,
            )
        except requests.RequestException:
            pass
        return

    if url.startswith(f"{UPLOAD_URL_PREFIX}/"):
        filename = url[len(UPLOAD_URL_PREFIX) + 1:]
        path = os.path.join(UPLOAD_DIR, filename)
        try:
            if os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass

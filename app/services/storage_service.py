import mimetypes
import uuid
from pathlib import Path

import httpx
from fastapi import HTTPException, UploadFile

from app.core.config import settings

ALLOWED_EXTENSIONS = {
    "profile": {".jpg", ".jpeg", ".png", ".webp"},
    "resume": {".pdf", ".doc", ".docx"},
    "certificate": {".pdf", ".jpg", ".jpeg", ".png"},
    "license": {".pdf", ".jpg", ".jpeg", ".png"},
    "identity": {".pdf", ".jpg", ".jpeg", ".png"},
    "company": {".pdf", ".jpg", ".jpeg", ".png"},
    "portfolio": {".pdf", ".jpg", ".jpeg", ".png", ".webp"},
}


def _validate_file(file: UploadFile, category: str) -> None:
    ext = Path(file.filename or "").suffix.lower()
    allowed = ALLOWED_EXTENSIONS.get(category, ALLOWED_EXTENSIONS["profile"])
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"File type {ext} not allowed for category '{category}'",
        )


async def upload_file(
    file: UploadFile,
    category: str,
    user_id: uuid.UUID,
) -> str:
    _validate_file(file, category)
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds maximum upload size")

    ext = Path(file.filename or "file.bin").suffix.lower() or ".bin"
    object_path = f"{category}/{user_id}/{uuid.uuid4()}{ext}"
    content_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"

    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        return _upload_supabase(object_path, content, content_type)

    return _upload_local(object_path, content)


def _upload_supabase(object_path: str, content: bytes, content_type: str) -> str:
    bucket = settings.SUPABASE_STORAGE_BUCKET
    base = settings.SUPABASE_URL.rstrip("/")
    url = f"{base}/storage/v1/object/{bucket}/{object_path}"

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            url,
            content=content,
            headers={
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                "Content-Type": content_type,
                "x-upsert": "true",
            },
        )
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail="Storage upload failed")

    return f"{base}/storage/v1/object/public/{bucket}/{object_path}"


def _upload_local(object_path: str, content: bytes) -> str:
    dest = Path(settings.UPLOAD_DIR) / object_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    return f"/uploads/{object_path.replace(chr(92), '/')}"

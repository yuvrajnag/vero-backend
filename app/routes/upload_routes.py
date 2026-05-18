from fastapi import APIRouter, Depends, File, UploadFile

from app.core.dependencies import get_current_user
from app.models.user import User
from app.services import storage_service

# Prefix must NOT be "/uploads" — that path is mounted for StaticFiles (GET only).
router = APIRouter(prefix="/api/uploads", tags=["Uploads"])


@router.post("/{category}")
async def upload_document(
    category: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload profile, resume, certificate, license, identity, or company documents."""
    allowed = set(storage_service.ALLOWED_EXTENSIONS.keys())
    if category not in allowed:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=f"Unknown category. Allowed: {sorted(allowed)}")

    url = await storage_service.upload_file(file, category, current_user.id)
    return {"url": url, "category": category}

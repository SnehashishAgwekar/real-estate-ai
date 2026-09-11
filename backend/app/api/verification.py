from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from starlette.concurrency import run_in_threadpool
from app.services.gemini_verifier import verify_property_with_gemini

router = APIRouter(prefix="/api/v1", tags=["Verification"])


@router.post("/verify-property")
async def verify_property(
    claimed_bhk: int = Form(...),
    images: list[UploadFile] = File(...)
):
    if not images:
        raise HTTPException(status_code=400, detail="No images provided.")
    if len(images) > 8:
        raise HTTPException(status_code=400, detail="Maximum limit of 8 images exceeded.")

    prepared = []
    for idx, img in enumerate(images):
        if not img.content_type or not img.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"File {img.filename} is not a valid image.")
        image_bytes = await img.read()
        prepared.append({
            "photo_index": idx + 1,
            "image_bytes": image_bytes,
            "mime_type": img.content_type,
        })

    try:
        verdict = await run_in_threadpool(verify_property_with_gemini, prepared, claimed_bhk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini verification failed: {str(e)}")

    return {
        "verdict": verdict,
        "images_analyzed": len(images)
    }

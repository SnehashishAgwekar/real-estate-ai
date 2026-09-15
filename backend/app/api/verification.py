from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from starlette.concurrency import run_in_threadpool
from app.services.room_classifier import classify_room
from app.services.bhk_verifier import verify_bhk

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

    classified_results = []

    for idx, img in enumerate(images):
        if not img.content_type or not img.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"File {img.filename} is not a valid image.")

        image_bytes = await img.read()

        try:
            result = await run_in_threadpool(classify_room, image_bytes)
            # Inject bytes and index for the downstream deduplicator pipeline
            result["image_bytes"] = image_bytes
            result["photo_index"] = idx + 1
            classified_results.append(result)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing image {img.filename}: {str(e)}")

    verdict = await run_in_threadpool(verify_bhk, classified_results, claimed_bhk)

    # Clear heavy image bytes from memory before returning the JSON response
    for room in verdict.get("all_detected_rooms", []):
        room.pop("image_bytes", None)

    return {
        "verdict": verdict,
        "images_analyzed": len(images)
    }

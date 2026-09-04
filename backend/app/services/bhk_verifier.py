from app.services.room_deduplicator import deduplicate_rooms

def verify_bhk(classified_results: list, claimed_bhk: int) -> dict:
    all_detected_rooms = []
    bedroom_images = []
    
    for res in classified_results:
        room_type = res.get("room_type")
        photo_index = res.get("photo_index")
        
        all_detected_rooms.append({
            "image_index": photo_index,
            "room_type": room_type,
            "confidence": res.get("confidence"),
            "raw_category": res.get("raw_category")
        })
        
        if room_type == "bedroom":
            bedroom_images.append({
                "image_bytes": res.get("image_bytes"),
                "room_type": room_type,
                "photo_index": photo_index
            })

    # Run CLIP deduplication on the bedroom group
    dedup_result = deduplicate_rooms(bedroom_images)
    unique_bedrooms = dedup_result["unique_room_count"]
    raw_bedrooms = dedup_result["total_photos_in_group"]
    duplicate_groups = dedup_result["duplicate_groups"]

    # Build a separate warning when similarity scores are too close to the
    # threshold to be a confident merge/no-merge decision
    ambiguity_warning = ""
    if dedup_result["ambiguous_pairs"]:
        pairs_text = ", ".join(
            f"#{p['photo_indices'][0]} & #{p['photo_indices'][1]} ({p['similarity']*100:.1f}% similar)"
            for p in dedup_result["ambiguous_pairs"]
        )
        ambiguity_warning = (
            f"⚠️ Low confidence on some photos: {pairs_text}. "
            f"These may or may not be the same room — please verify manually."
        )

    matches = unique_bedrooms >= claimed_bhk

    confidence_note = f"Detected {raw_bedrooms} total bedroom photo(s). After visual deduplication, found {unique_bedrooms} distinct bedroom(s)."

    return {
        "claimed_bhk": claimed_bhk,
        "raw_bedroom_photos": raw_bedrooms,
        "unique_bedrooms_detected": unique_bedrooms,
        "duplicate_groups": duplicate_groups,
        "matches": matches,
        "confidence_note": confidence_note,
        "low_confidence_warning": ambiguity_warning,
        "all_detected_rooms": all_detected_rooms
    }
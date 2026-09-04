import torch
import torch.nn.functional as F
from PIL import Image
import io
from sentence_transformers import SentenceTransformer

# SIMILARITY_THRESHOLD controls how aggressive the deduplication is.
# 0.90 is a good starting point for CLIP visual embeddings.
# Raise it (e.g., 0.95) if it incorrectly groups completely distinct rooms.
# Lower it (e.g., 0.85) if it fails to catch photos of the same room from different angles.
SIMILARITY_THRESHOLD = 0.90

AMBIGUITY_MARGIN = 0.03

# Load CLIP model once at module import.
# ViT-B-32 is lightweight (~600MB) and optimized for fast CPU inference.
MODEL = SentenceTransformer('clip-ViT-L-14')

def get_image_embedding(image_bytes: bytes) -> torch.Tensor:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    # sentence-transformers handles the CLIP image preprocessing internally
    embedding = MODEL.encode(image, convert_to_tensor=True)
    return embedding

def deduplicate_rooms(images_with_labels: list[dict]) -> dict:
    if not images_with_labels:
        return {"unique_room_count": 0, "duplicate_groups": [], "total_photos_in_group": 0, "ambiguous_pairs": []}

    embeddings = []
    for img_dict in images_with_labels:
        emb = get_image_embedding(img_dict["image_bytes"])
        embeddings.append(emb)

    embeddings_tensor = torch.stack(embeddings)
    cos_sim_matrix = F.cosine_similarity(embeddings_tensor.unsqueeze(1), embeddings_tensor.unsqueeze(0), dim=-1)

    N = len(images_with_labels)

    # Track pairs whose similarity is close to the threshold — these decisions
    # (merge vs. don't merge) are not confident and should be flagged to the user.
    ambiguous_pairs = []
    for i in range(N):
        for j in range(i + 1, N):
            score = cos_sim_matrix[i][j].item()
            if abs(score - SIMILARITY_THRESHOLD) <= AMBIGUITY_MARGIN:
                ambiguous_pairs.append({
                    "photo_indices": [images_with_labels[i]["photo_index"], images_with_labels[j]["photo_index"]],
                    "similarity": round(score, 4)
                })

    visited = [False] * N
    clusters = []

    for i in range(N):
        if visited[i]:
            continue
        current_cluster_indices = [i]
        visited[i] = True
        for j in range(i + 1, N):
            if not visited[j] and cos_sim_matrix[i][j].item() >= SIMILARITY_THRESHOLD:
                current_cluster_indices.append(j)
                visited[j] = True

        if len(current_cluster_indices) > 1:
            clusters.append({
                "photo_indices": [images_with_labels[idx]["photo_index"] for idx in current_cluster_indices],
                "similarity": round(cos_sim_matrix[i][current_cluster_indices[1]].item(), 4)
            })
        else:
            clusters.append({
                "photo_indices": [images_with_labels[i]["photo_index"]],
                "similarity": None
            })

    unique_count = len(clusters)
    duplicate_groups = [c for c in clusters if len(c["photo_indices"]) > 1]

    return {
        "unique_room_count": unique_count,
        "duplicate_groups": duplicate_groups,
        "total_photos_in_group": N,
        "ambiguous_pairs": ambiguous_pairs   # naya field
    }
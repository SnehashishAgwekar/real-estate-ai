import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from dotenv import load_dotenv

load_dotenv()

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = "real_estate_docs"

# Initialize Qdrant Client connection
qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

def init_qdrant_collection():
    """
    Creates the vector collection in Qdrant if it does not already exist.
    """
    collections = qdrant_client.get_collections().collections
    collection_names = [col.name for col in collections]

    if COLLECTION_NAME not in collection_names:
        # FastEmbed bge-small-en-v1.5 model produces 384-dimensional vectors
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
        print(f"Collection '{COLLECTION_NAME}' created successfully.")
    else:
        print(f"Collection '{COLLECTION_NAME}' already exists.")
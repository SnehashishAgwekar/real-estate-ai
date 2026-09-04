import sys
import os

# Add parent directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag.vector_db import init_qdrant_collection, qdrant_client, COLLECTION_NAME
from fastembed import TextEmbedding

def test_vector_storage():
    # Step 1: Initialize the collection
    init_qdrant_collection()
    
    # Step 2: Initialize local embedding model
    print("Loading embedding model...")
    embedding_model = TextEmbedding()
    
    sample_text = "Luxury 3 BHK apartment in Vijay Nagar, Indore with modern amenities and pool view."
    
    # Step 3: Convert raw text to vector float array
    embeddings = list(embedding_model.embed([sample_text]))
    vector = embeddings[0].tolist()
    
    # Step 4: Upsert vector + payload metadata into Qdrant
    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            {
                "id": 1,
                "vector": vector,
                "payload": {
                    "document": sample_text,
                    "city": "Indore",
                    "source": "Sample Brochure"
                }
            }
        ]
    )
    print("Sample vector inserted successfully into Qdrant!")

if __name__ == "__main__":
    test_vector_storage()
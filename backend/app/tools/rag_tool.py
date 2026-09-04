from typing import List, Dict, Any
from app.rag.vector_db import qdrant_client, COLLECTION_NAME
from fastembed import TextEmbedding

# Load embedding model instance
_embedding_model = TextEmbedding()

def query_unstructured_rag(query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Embeds the user search query and retrieves semantically similar document chunks from Qdrant.
    Includes safe error handling to prevent server crashes if the collection doesn't exist yet.
    """
    try:
        # Convert natural language query into vector space embedding
        query_vector = list(_embedding_model.embed([query_text]))[0].tolist()

        # Search vector collection
        search_results = qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=top_k
        )

        retrieved_chunks = []
        for point in search_results:
            retrieved_chunks.append({
                "score": round(point.score, 4),
                "document": point.payload.get("document", ""),
                "source": point.payload.get("source", "Unknown Document")
            })

        return retrieved_chunks

    except Exception as e:
        print(f"\n[WARNING] RAG Search failed safely: {e}\n")
        # Return an empty list so LangGraph doesn't crash with an Internal Server Error
        return []
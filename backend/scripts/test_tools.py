import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import SessionLocal
from app.tools.sql_tool import query_structured_properties
from app.tools.rag_tool import query_unstructured_rag

def test_sql_tool():
    db = SessionLocal()
    try:
        print("\n--- Testing SQL Retrieval Tool ---")
        results = query_structured_properties(
            db=db,
            city="Indore",
            max_price=10000000, # Under 1 Crore
            min_bhk=3
        )
        print(f"Found {len(results)} structured property matches:")
        for prop in results:
            print(f" - {prop['property_name']} in {prop['location']}: ₹{prop['price_in_inr']:,.0f} ({prop['bhk']} BHK)")
    finally:
        db.close()

def test_rag_tool():
    print("\n--- Testing RAG Retrieval Tool ---")
    query = "What amenities are available near Vijay Nagar apartments?"
    results = query_unstructured_rag(query_text=query, top_k=2)
    print(f"Found {len(results)} relevant brochure excerpts:")
    for res in results:
        print(f" - [Score: {res['score']}] Source: {res['source']}")
        print(f"   Excerpt: {res['document'][:150]}...")

if __name__ == "__main__":
    test_sql_tool()
    test_rag_tool()
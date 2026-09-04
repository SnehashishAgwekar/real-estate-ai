import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.graph import real_estate_agent

def test_queries():
    queries = [
        "Find 3 BHK apartments in Indore under 90 Lakhs",
        "What amenities are in the ABC Residency brochure?",
        "Indore metro real estate impact updates"
    ]

    for q in queries:
        print(f"\n==========================================")
        print(f"User Query: '{q}'")
        print(f"==========================================")
        initial_state = {
            "user_query": q,
            "intent": None,
            "parsed_filters": {},
            "sql_results": [],
            "rag_results": [],
            "web_results": [],
            "final_response": ""
        }
        result = real_estate_agent.invoke(initial_state)
        print(result["final_response"])

if __name__ == "__main__":
    test_queries()
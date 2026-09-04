import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools.web_search_tool import query_web_search

def test_web_search():
    print("\n--- Testing Tavily Web Search Tool ---")
    query = "Indore metro corridor construction update real estate impact"
    
    results = query_web_search(query=query, max_results=2)
    
    for idx, item in enumerate(results, 1):
        if "error" in item:
            print(f"Error: {item['error']}")
            break
        print(f"\nResult #{idx}: {item['title']}")
        print(f"URL: {item['url']}")
        print(f"Snippet: {item['snippet'][:200]}...")

if __name__ == "__main__":
    test_web_search()
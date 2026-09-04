import os
from typing import List, Dict, Any
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

def query_web_search(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Executes a real-time web search via Tavily API for current real estate market context.
    """
    if not TAVILY_API_KEY or TAVILY_API_KEY == "your_tavily_api_key_here":
        return [{"error": "Tavily API key is missing. Please set TAVILY_API_KEY in .env"}]

    client = TavilyClient(api_key=TAVILY_API_KEY)
    
    try:
        # Search web with real-estate specific context filter
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=max_results
        )
        
        results = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title"),
                "url": item.get("url"),
                "snippet": item.get("content")
            })
        return results

    except Exception as e:
        return [{"error": f"Failed to perform web search: {str(e)}"}]
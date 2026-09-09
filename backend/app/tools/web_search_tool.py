import os
from typing import List, Dict, Any
from urllib.parse import urlparse
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
        # "advanced" depth returns longer, more detailed content snippets
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
        )

        results = []
        seen_domains = {}
        for item in response.get("results", []):
            url = item.get("url") or ""
            # collapse many results from the same portal down to the best 2
            domain = urlparse(url).netloc.replace("www.", "")
            seen_domains[domain] = seen_domains.get(domain, 0) + 1
            if seen_domains[domain] > 2:
                continue
            results.append({
                "title": item.get("title"),
                "url": url,
                "snippet": item.get("content"),
                "score": item.get("score"),
            })
        return results

    except Exception as e:
        return [{"error": f"Failed to perform web search: {str(e)}"}]
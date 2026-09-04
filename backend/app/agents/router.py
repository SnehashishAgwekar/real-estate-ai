import os
from typing import Tuple, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class QueryExtraction(BaseModel):
    intent: str = Field(description="Must be one of: 'sql_search', 'rag_search', 'web_search', 'general'")
    city: str = Field(default="Indore")
    min_price: float = Field(default=0.0)
    max_price: float = Field(default=30000000.0)
    min_bhk: int = Field(default=1)

llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", api_key=os.getenv("GOOGLE_API_KEY"))

def classify_intent_and_extract_params(query: str) -> Tuple[str, Dict[str, Any]]:
    query_lower = query.lower()
    
    # 🚨 BULLETPROOF OVERRIDE: LLM ko bypass karke direct SQL par bhejo agar property ki baat hai
    if any(keyword in query_lower for keyword in ["bhk", "flat", "apartment", "property", "villa", "plot", "house", "indore"]):
        print(f"\n--- [DEBUG] Hardcoded Keyword Override -> Forcing sql_search ---")
        return "sql_search", {
            "city": "Indore",
            "max_price": 30000000,
            "min_bhk": 3 if "3" in query_lower else 1
        }

    system_instruction = """You are a strict database router. Classify as 'sql_search' for any property or flat queries."""
    
    structured_llm = llm.with_structured_output(QueryExtraction)
    prompt = f"{system_instruction}\n\nUser Query: {query}"
    
    try:
        result = structured_llm.invoke(prompt)
        filters = {
            "city": result.city or "Indore",
            "min_price": result.min_price,
            "max_price": result.max_price,
            "min_bhk": result.min_bhk
        }
        filters = {k: v for k, v in filters.items() if v is not None}
        print(f"\n--- [DEBUG] LLM Router Extracted: {result.intent} | Filters: {filters} ---\n")
        
        # Agar LLM galti se web_search de de, tab bhi property query ke liye sql_search hi rakho
        intent = "sql_search" if result.intent in ["web_search", "general"] and any(w in query_lower for w in ["bhk", "flat", "indore"]) else result.intent
        return intent, filters

    except Exception as e:
        print(f"\n--- [DEBUG] Router LLM Error: {e} ---\n")
        # Fallback to sql_search instead of web_search
        return "sql_search", {"city": "Indore", "max_price": 30000000, "min_bhk": 3}
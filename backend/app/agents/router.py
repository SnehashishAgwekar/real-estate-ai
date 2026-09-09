import os
import re
from typing import Tuple, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class QueryExtraction(BaseModel):
    intent: str = Field(
        description="One of: 'sql_search' (looking for properties/flats/plots), "
        "'rag_search' (asking about a brochure/document), 'web_search' "
        "(explicitly wants live web/market info), 'general' (greeting or "
        "general real-estate question)."
    )
    city: Optional[str] = Field(
        default=None, description="City name if mentioned, else null"
    )
    location: Optional[str] = Field(
        default=None,
        description="Specific locality / area / sector / road within the city "
        "if mentioned (e.g. 'Super Corridor', 'Vijay Nagar', 'Rau'), else null",
    )
    min_price: Optional[float] = Field(
        default=None, description="Minimum price in absolute INR rupees, else null"
    )
    max_price: Optional[float] = Field(
        default=None,
        description="Maximum price in absolute INR rupees. Convert units: "
        "'1.25 cr' or '1.25 crore' = 12500000; '80 lakh' = 8000000. Null if none.",
    )
    min_bhk: Optional[int] = Field(
        default=None, description="Number of bedrooms (BHK) if mentioned, else null"
    )
    property_type: Optional[str] = Field(
        default=None,
        description="One of Apartment/Villa/Plot/Commercial/Independent House if "
        "clearly implied, else null",
    )


llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", api_key=os.getenv("GOOGLE_API_KEY"))

_PROPERTY_WORDS = ("bhk", "flat", "apartment", "property", "properties", "villa",
                   "plot", "house", "home", "listing", "buy", "rent", "sq ft",
                   "sqft", "budget", "crore", " cr", "lakh")

# crude "1.25 cr" / "80 lakh" -> rupees, used only in the offline fallback
_UNIT = {"cr": 1_00_00_000, "crore": 1_00_00_000, "lakh": 1_00_000, "lac": 1_00_000}


def _fallback_extract(query: str) -> Tuple[str, Dict[str, Any]]:
    """No-LLM heuristic: keep it minimal, never invent a city or budget."""
    q = query.lower()
    filters: Dict[str, Any] = {}

    m = re.search(r"(\d+)\s*bhk", q)
    if m:
        filters["min_bhk"] = int(m.group(1))

    m = re.search(r"(\d+(?:\.\d+)?)\s*(crore|cr|lakh|lac)\b", q)
    if m:
        filters["max_price"] = float(m.group(1)) * _UNIT[m.group(2)]

    intent = "sql_search" if any(w in q for w in _PROPERTY_WORDS) else "general"
    return intent, filters


def classify_intent_and_extract_params(query: str) -> Tuple[str, Dict[str, Any]]:
    structured_llm = llm.with_structured_output(QueryExtraction)
    prompt = (
        "You are a routing + extraction engine for a real-estate assistant. "
        "Classify the intent and extract ONLY what the user actually stated. "
        "Do NOT guess a city, locality or budget that the user did not mention.\n\n"
        f"User query: {query}"
    )

    try:
        result: QueryExtraction = structured_llm.invoke(prompt)
        filters = {
            "city": result.city,
            "location": result.location,
            "min_price": result.min_price,
            "max_price": result.max_price,
            "min_bhk": result.min_bhk,
            "property_type": result.property_type,
        }
        filters = {k: v for k, v in filters.items() if v not in (None, "", 0)}

        intent = result.intent
        # A concrete property search must go through our DB first, even if the
        # model labelled it web_search / general.
        if any(w in query.lower() for w in _PROPERTY_WORDS) and intent in ("web_search", "general"):
            intent = "sql_search"

        print(f"\n--- [DEBUG] Router: {intent} | Filters: {filters} ---\n")
        return intent, filters

    except Exception as e:
        print(f"\n--- [DEBUG] Router LLM failed, using fallback: {e} ---\n")
        return _fallback_extract(query)

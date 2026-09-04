from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class ChatRequest(BaseModel):
    user_query: str = Field(
        ..., 
        example="Find 3 BHK apartments in Indore under 90 Lakhs",
        description="Natural language query from the user"
    )

class ChatResponse(BaseModel):
    user_query: str
    intent: str
    parsed_filters: Dict[str, Any]
    final_response: str
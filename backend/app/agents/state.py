# app/agents/state.py
from typing import List, Dict, Any, Optional, Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # This specific line tells LangGraph to APPEND to the list, giving us memory!
    messages: Annotated[list, add_messages]
    
    user_query: str
    intent: Optional[str]            
    parsed_filters: Dict[str, Any]   
    sql_results: List[Dict[str, Any]]
    rag_results: List[Dict[str, Any]]
    web_results: List[Dict[str, Any]]
    final_response: str
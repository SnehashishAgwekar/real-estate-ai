import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.router import classify_intent_and_extract_params
from app.database.connection import SessionLocal
from app.tools.sql_tool import query_structured_properties
from app.tools.rag_tool import query_unstructured_rag
from app.tools.web_search_tool import query_web_search
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-3.6-flash",
    api_key=os.getenv("GOOGLE_API_KEY")
)
memory = MemorySaver()

# ---------------------------------------------------------
def classify_intent_node(state: AgentState) -> AgentState:
    try:
        user_q = state.get("user_query") or (state["messages"][-1].content if "messages" in state else "")
        intent, filters = classify_intent_and_extract_params(user_q)
        print(f"\n--- [DEBUG] Router Intent: {intent} | Filters: {filters} ---\n")
        return {**state, "user_query": user_q, "intent": intent, "parsed_filters": filters}
    except Exception as e:
        print(f"\n[WARNING] Router LLM failed/rate limited: {e}\n")
        # Fallback to sql_search instead of general for property keywords
        return {**state, "intent": "sql_search", "parsed_filters": {"city": "Indore", "max_price": 30000000, "min_bhk": 3}}

def sql_execution_node(state: AgentState) -> AgentState:
    db = SessionLocal()
    try:
        filters = state.get("parsed_filters", {})
        results = query_structured_properties(
            db=db,
            city=filters.get("city", "Indore"),
            max_price=filters.get("max_price", 30000000),
            min_bhk=filters.get("min_bhk", 3),
        )
        print(f"\n--- [DEBUG] SQL Execution Results Count: {len(results) if results else 0} ---\n")
        return {**state, "sql_results": results}
    except Exception as e:
        print(f"\n[ERROR] SQL Execution Failed: {e}\n")
        return {**state, "sql_results": []}
    finally:
        db.close()

# Routing function: Forcefully handle routing without breaking to web search if it's a property query
def route_after_sql(state: AgentState) -> str:
    sql_results = state.get("sql_results", [])
    if sql_results and len(sql_results) > 0:
        print("\n--- [DEBUG] SQL found properties! Routing directly to Synthesizer. ---\n")
        return "synthesizer"
    else:
        print("\n--- [DEBUG] SQL returned 0 results! Falling back to Web Search. ---\n")
        return "web_search_execution"

def rag_execution_node(state: AgentState) -> AgentState:
    query = state.get("user_query", "real estate")
    results = query_unstructured_rag(query_text=query, top_k=2)
    return {**state, "rag_results": results}

def web_search_node(state: AgentState) -> AgentState:
    query = state.get("user_query", "real estate properties")
    results = query_web_search(query=query, max_results=3)
    return {**state, "web_results": results}

def general_knowledge_node(state: AgentState) -> AgentState:
    print("\n--- [DEBUG] Executing General Knowledge LLM Node! ---\n")
    query = state.get("user_query", "")
    
    prompt = f"""You are strictly a Real Estate AI Assistant.

USER QUERY: "{query}"

INSTRUCTIONS & DOMAIN GUARDRAILS:
1. ALLOWED TOPICS: Real estate properties, pricing, locations, RERA acts, builder regulations, home loans/EMIs, stamp duty, property tax, and polite greetings.
2. FORBIDDEN TOPICS: Anything unrelated to real estate.

CRITICAL RULE:
- If the user query is about ANY forbidden or out-of-scope topic, reply ONLY with this exact sentence:
  "I am specialized strictly in real estate and property assistance. I can help you find properties, calculate EMIs, or understand RERA guidelines, but I cannot answer questions outside of real estate."

Provide your response below:"""

    try:
        response = llm.invoke(prompt)
        content = response.content
    except Exception as e:
        print(f"\n[WARNING] LLM Quota/Rate Limit hit: {e}\n")
        content = "I am experiencing high traffic right now. Please wait a few seconds and try again!"
    
    return {
        **state, 
        "final_response": content,
        "messages": [("assistant", content)]
    }

def synthesizer_node(state: AgentState) -> AgentState:
    print("\n--- [DEBUG] Executing LLM Synthesizer Node! ---\n")
    intent = state.get("intent")
    query = state.get("user_query", "")
    sql_results = state.get("sql_results", [])
    
    # 1. Gather raw data found by the tools
    context_data = ""
    if sql_results:
        context_data = f"Database Results: {sql_results}"
    elif state.get("rag_results"):
        context_data = f"Document Snippets: {state['rag_results']}"
    elif state.get("web_results"):
        context_data = f"Web Results: {state['web_results']}"
    else:
        context_data = "No specific database rows matched, providing general verified property context."

    # 2. Dynamic prompt for formatting multiple options + clickable markdown links
    prompt = f"""
You are a professional real estate assistant. The user is searching based on this query: "{query}"

Here is the raw data fetched from the database / search:
{context_data}

TASK:
1. Extract multiple distinct property options matching the user's requirements.
2. For each option, clearly display:
   - Property Name / Type
   - Location
   - Estimated Price
   - Configuration (e.g., 3 BHK)
3. **CRITICAL (Clickable Links):** Include the exact source URL from the raw data as a Markdown clickable link for each property using this format: 
   👉 [View Original Listing](URL_HERE)
4. Do not make up fake links. Use only the valid URLs present in the raw data above. If no URL is available, omit the link cleanly.
"""

    try:
        response = llm.invoke(prompt)
        content = response.content
    except Exception as e:
        print(f"\n[WARNING] Synthesizer LLM Quota hit: {e}\n")
        if sql_results:
            content = f"I found matching properties in the database:\n{sql_results}"
        else:
            content = "I'm currently experiencing high traffic. Please wait a moment and try your query again."

    return {
        **state, 
        "final_response": content,
        "messages": [("assistant", content)]
    }

# ---------------------------------------------------------
def route_next_step(state: AgentState) -> str:
    intent = state.get("intent")
    if intent == "sql_search": return "sql_execution"
    elif intent == "rag_search": return "rag_execution"
    elif intent == "web_search": return "web_search_execution"
    elif intent == "general": return "general_knowledge"
    return "sql_execution" # Default fallback to sql instead of synthesizer

builder = StateGraph(AgentState)
builder.add_node("classifier", classify_intent_node)
builder.add_node("sql_execution", sql_execution_node)
builder.add_node("rag_execution", rag_execution_node)
builder.add_node("web_search_execution", web_search_node)
builder.add_node("general_knowledge", general_knowledge_node)
builder.add_node("synthesizer", synthesizer_node)

builder.set_entry_point("classifier")

builder.add_conditional_edges(
    "classifier", route_next_step,
    {
        "sql_execution": "sql_execution",
        "rag_execution": "rag_execution",
        "web_search_execution": "web_search_execution",
        "general_knowledge": "general_knowledge",
        "synthesizer": "synthesizer"
    }
)

# FIXED: SQL execution ke baad seedha synthesizer par jayega, web search par nahi bhatkega
builder.add_conditional_edges(
    "sql_execution",
    route_after_sql,
    {
        "synthesizer": "synthesizer",
        "web_search_execution": "web_search_execution"
    }
)

builder.add_edge("rag_execution", "synthesizer")
builder.add_edge("web_search_execution", "synthesizer")

builder.add_edge("general_knowledge", END)
builder.add_edge("synthesizer", END)

app = builder.compile(checkpointer=memory)
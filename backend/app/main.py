import traceback
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.agents.graph import app as agent_app
from app.api.verification import router as verification_router

app = FastAPI(title="Real Estate AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(verification_router)

class ChatRequest(BaseModel):
    user_query: str
    thread_id: str

@app.get("/")
async def root_health_check():
    return {
        "status": "online",
        "message": "Real Estate AI Backend is running smoothly!"
    }

@app.post("/api/v1/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        config = {"configurable": {"thread_id": request.thread_id}}
        
        state = {
            "user_query": request.user_query,
            "messages": [("user", request.user_query)]
        }
        
        result = agent_app.invoke(state, config=config)
        
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            ai_message = getattr(last_message, "content", str(last_message))
        else:
            ai_message = result.get("final_response", "No response generated.")
            
        intent = result.get("next_agent", result.get("intent", "unknown"))
        filters = result.get("extracted_filters", result.get("parsed_filters", {}))
        
        return {
            "final_response": ai_message,
            "intent": intent,
            "parsed_filters": filters
        }
        
    except Exception as e:
        print("\n--- AGENT CRASH TRACEBACK ---")
        traceback.print_exc()
        print("-----------------------------\n")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/chat-stream")
async def chat_stream(payload: dict):
    user_query = payload.get("user_query")
    thread_id = payload.get("thread_id", "default_thread")
    
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {
        "user_query": user_query,
        "messages": [("user", user_query)]
    }

    async def event_generator():
        try:
            async for event in agent_app.astream(inputs, config=config, stream_mode="updates"):
                for node_name, state_update in event.items():
                    # FIX: Sirf zaroori data extract karo taaki JSON payload chota rahe aur break na ho
                    clean_update = {}
                    if "intent" in state_update:
                        clean_update["intent"] = state_update["intent"]
                    if "parsed_filters" in state_update:
                        clean_update["parsed_filters"] = state_update["parsed_filters"]
                    if "final_response" in state_update:
                        clean_update["final_response"] = state_update["final_response"]

                    # Ab yeh light-weight JSON safely frontend tak jayega
                    yield f"data: {json.dumps({'node': node_name, 'update': clean_update}, default=str)}\n\n"
            
            yield f"data: {json.dumps({'status': 'completed'})}\n\n"
        except Exception as e:
            print(f"\n[STREAM ERROR] {e}\n")
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)}, default=str)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
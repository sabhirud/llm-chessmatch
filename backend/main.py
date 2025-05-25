from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import random
import os
from typing import List, Dict, Any
from openai import OpenAI
from anthropic import Anthropic
from google import genai

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/random-number")
async def get_random_number():
    return {"number": random.randint(1, 100)}

@app.post("/get_move")
async def get_move(request: Dict[str, Any]):
    # Validate required fields
    if "model" not in request:
        raise HTTPException(status_code=400, detail="Field 'model' is required")
    if "game_state" not in request:
        raise HTTPException(status_code=400, detail="Field 'game_state' is required")
    if "move_history" not in request:
        raise HTTPException(status_code=400, detail="Field 'move_history' is required")
    
    # Validate model
    allowed_models = ["claude-opus-4-20250514", "o3", "gemini-2.5-pro-preview-05-06", "grok-3-mini"]
    if request["model"] not in allowed_models:
        raise HTTPException(status_code=400, detail=f"Only {', '.join(allowed_models)} models are allowed")
    
    # Validate types
    if not isinstance(request["game_state"], str):
        raise HTTPException(status_code=400, detail="Field 'game_state' must be a string")
    if not isinstance(request["move_history"], list):
        raise HTTPException(status_code=400, detail="Field 'move_history' must be a list")
    
    move_history_str = ", ".join(request["move_history"]) if request["move_history"] else "No moves yet"
    
    prompt = f"""You are a chess AI. Given the current game state and move history, provide the next best move.

Game State (FEN): {request["game_state"]}
Move History: {move_history_str}

Please respond with only the move in standard algebraic notation (e.g., "e4", "Nf3", "O-O", etc.)."""

    if request["model"] == "claude-opus-4-20250514":
        return await call_anthropic_api(request["model"], prompt)
    elif request["model"] == "o3":
        return await call_openai_api(request["model"], prompt)
    elif request["model"] == "gemini-2.5-pro-preview-05-06":
        return await call_gemini_api(request["model"], prompt)
    elif request["model"] == "grok-3-mini":
        return await call_xai_api(request["model"], prompt)

async def call_anthropic_api(model: str, prompt: str):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    try:
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=1100,
            thinking={
                "type": "enabled",
                "budget_tokens": 1024
            },
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Find the text content (skip thinking blocks)
        move = None
        for content_block in response.content:
            if hasattr(content_block, 'type') and content_block.type == 'text':
                move = content_block.text.strip()
                break
        
        if not move:
            # Fallback to first content block if no text type found
            move = response.content[0].text.strip()
        
        return {"move": move}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling Anthropic API: {str(e)}")

async def call_openai_api(model: str, prompt: str):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=model,
            input=prompt,
            reasoning={
                "effort": "low"
            }
        )
        
        # Find the message output (skip reasoning items)
        message_output = None
        for item in response.output:
            if item.type == 'message':
                message_output = item
                break
        
        if message_output and message_output.content:
            move = message_output.content[0].text.strip()
            return {"move": move}
        else:
            raise HTTPException(status_code=500, detail="No message content found in OpenAI response")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling OpenAI API: {str(e)}")

async def call_gemini_api(model: str, prompt: str):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt
        )
        
        move = response.text.strip()
        return {"move": move}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling Google Gemini API: {str(e)}")

async def call_xai_api(model: str, prompt: str):
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="XAI_API_KEY not configured")

    try:
        client = OpenAI(
            base_url="https://api.x.ai/v1",
            api_key=api_key
        )
        
        response = client.chat.completions.create(
            model=model,
            reasoning_effort="high",
            messages=[
                {
                    "role": "system",
                    "content": "You are a chess AI. Provide only the move in standard algebraic notation."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.7
        )
        
        move = response.choices[0].message.content.strip()
        return {"move": move}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling X.AI API: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
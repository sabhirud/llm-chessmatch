from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, validator
import os
import json
import asyncio
from typing import List, AsyncGenerator
from openai import OpenAI
from anthropic import Anthropic
from google import genai
from google.genai import types

CHESS_MOVE_PROMPT_TEMPLATE = """You are a chess engine tasked with finding the best valid move given a current board position and move history.

<game_state_fen>
{game_state}
</game_state_fen>

<move_history>
{move_history}
</move_history>

Your task is to analyze the given board state and move history, then return either:
1. The best valid move in standard chess notation (e.g., "e4", "Nf3", "O-O")
2. The word "DRAW" to offer a draw
3. The word "RESIGN" to resign the game

Follow these steps to complete the task:

1. Analyze the board state given in FEN notation. Consider the position of all pieces, potential threats, and opportunities.

2. Review the move history to understand the flow of the game and any recurring patterns or strategies.

3. Generate a list of possible legal moves, considering:
- Piece mobility and potential captures
- Defensive moves to protect vulnerable pieces
- Attacking moves to threaten the opponent's pieces or king
- Positional improvements and control of key squares

4. Evaluate each possible move based on:
- Material balance
- Piece activity and coordination
- King safety
- Pawn structure
- Control of the center
- Potential for future tactics or combinations

5. Consider offering a draw if:
- The position is clearly equal with no winning chances for either side
- There has been no progress in the last several moves
- The material on the board is insufficient for either side to force a win

6. Consider resigning if:
- There is a significant material disadvantage with no compensation
- The position is hopeless, with no reasonable defensive resources
- Checkmate is unavoidable within a few moves

7. If neither a draw offer nor resignation is appropriate, determine the best move based on your analysis.

Respond with either a move, "RESIGN", or "DRAW_OFFER". Do not respond with any other justification or commentary.
"""

# Allowed models for both move generation and draw responses
ALLOWED_MODELS = [
    "claude-opus-4-20250514",
    "claude-sonnet-4-20250514",
    "o4-mini",
    "gemini-2.5-pro-preview-05-06",
    "gemini-2.5-flash-preview-05-20",
    "grok-3-mini",
]


class MoveRequest(BaseModel):
    model: str
    game_state: str
    move_history: List[str]

    @validator("model")
    def validate_model(cls, value: str) -> str:
        if value not in ALLOWED_MODELS:
            raise ValueError(f"Only {', '.join(ALLOWED_MODELS)} models are allowed")
        return value

app = FastAPI()
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is operational"}

@app.post("/draw_response")
async def draw_response(request: MoveRequest):
    move_history_str = ", ".join(request.move_history) if request.move_history else "No moves yet"
    
    prompt = f"""You are a chess AI. Your opponent has offered you a draw.

    Game State (FEN): {request.game_state}
    Move History: {move_history_str}

    Respond with either "ACCEPT" to accept the draw offer or "DECLINE" to decline and continue playing."""

    if request.model in ["claude-opus-4-20250514", "claude-sonnet-4-20250514"]:
        response = await call_anthropic_api(request.model, prompt)
    elif request.model == "o4-mini":
        response = await call_openai_api(request.model, prompt)
    elif request.model in ["gemini-2.5-pro-preview-05-06", "gemini-2.5-flash-preview-05-20"]:
        response = await call_gemini_api(request.model, prompt)
    elif request.model == "grok-3-mini":
        response = await call_xai_api(request.model, prompt)
    
    # Handle draw response
    if "move" in response:
        decision = response["move"].upper()
        if decision == "ACCEPT":
            return {"action": "draw_accept", "thinking_tokens": response.get("thinking_tokens", 0)}
        elif decision == "DECLINE":
            return {"action": "draw_decline", "thinking_tokens": response.get("thinking_tokens", 0)}
        else:
            # Default to decline if unclear
            return {"action": "draw_decline", "thinking_tokens": response.get("thinking_tokens", 0)}
    elif "action" in response:
        # Handle if the model returned an action directly
        if response["action"] in ["draw_accept", "draw_decline"]:
            return response
        else:
            return {"action": "draw_decline", "thinking_tokens": response.get("thinking_tokens", 0)}
    else:
        return {"action": "draw_decline", "thinking_tokens": response.get("thinking_tokens", 0)}

@app.post("/get_move_stream")
async def get_move_stream(request: MoveRequest):
    move_history_str = ", ".join(request.move_history) if request.move_history else "No moves yet"

    prompt = CHESS_MOVE_PROMPT_TEMPLATE.format(
        game_state=request.game_state,
        move_history=move_history_str
    )

    if request.model in ["claude-opus-4-20250514", "claude-sonnet-4-20250514"]:
        return StreamingResponse(
            stream_anthropic_move(request.model, prompt),
            media_type="text/event-stream"
        )
    elif request.model in ["gemini-2.5-pro-preview-05-06", "gemini-2.5-flash-preview-05-20"]:
        return StreamingResponse(
            stream_gemini_move(request.model, prompt),
            media_type="text/event-stream"
        )
    elif request.model == "grok-3-mini":
        return StreamingResponse(
            stream_grok_move(request.model, prompt),
            media_type="text/event-stream"
        )
    elif request.model == "o4-mini":
        return StreamingResponse(
            stream_openai_move(request.model, prompt),
            media_type="text/event-stream"
        )

@app.post("/get_move")
async def get_move(request: MoveRequest):
    move_history_str = ", ".join(request.move_history) if request.move_history else "No moves yet"

    prompt = CHESS_MOVE_PROMPT_TEMPLATE.format(
        game_state=request.game_state,
        move_history=move_history_str
    )

    if request.model in ["claude-opus-4-20250514", "claude-sonnet-4-20250514"]:
        return await call_anthropic_api(request.model, prompt)
    elif request.model == "o4-mini":
        return await call_openai_api(request.model, prompt)
    elif request.model in ["gemini-2.5-pro-preview-05-06", "gemini-2.5-flash-preview-05-20"]:
        return await call_gemini_api(request.model, prompt)
    elif request.model == "grok-3-mini":
        return await call_xai_api(request.model, prompt)

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
        
        # Extract thinking tokens
        # For Anthropic API, thinking tokens aren't separately reported in usage
        # We need to count them from the thinking content blocks
        thinking_tokens = 0
        for content_block in response.content:
            if hasattr(content_block, 'type') and content_block.type == 'thinking':
                if hasattr(content_block, 'text'):
                    # Rough word count estimation for tokens
                    thinking_tokens = len(content_block.text.split())
        
        # Check for special actions
        if move.upper() == "RESIGN":
            return {"action": "resign", "thinking_tokens": thinking_tokens}
        elif move.upper() == "DRAW_OFFER":
            return {"action": "draw_offer", "thinking_tokens": thinking_tokens}
        else:
            return {"move": move, "thinking_tokens": thinking_tokens}
        
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
            
            # Extract thinking tokens
            thinking_tokens = 0
            if hasattr(response, 'usage') and hasattr(response.usage, 'output_tokens_details') and hasattr(response.usage.output_tokens_details, 'reasoning_tokens'):
                thinking_tokens = response.usage.output_tokens_details.reasoning_tokens
            
            # Check for special actions
            if move.upper() == "RESIGN":
                return {"action": "resign", "thinking_tokens": thinking_tokens}
            elif move.upper() == "DRAW_OFFER":
                return {"action": "draw_offer", "thinking_tokens": thinking_tokens}
            else:
                return {"move": move, "thinking_tokens": thinking_tokens}
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
        
        # Add thinking config for both Gemini models
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    include_thoughts=True
                )
            )
        )
        
        move = response.text.strip()
        
        # Extract thinking tokens
        thinking_tokens = 0
        if hasattr(response, 'usage_metadata') and hasattr(response.usage_metadata, 'thoughts_token_count'):
            thinking_tokens = response.usage_metadata.thoughts_token_count
        
        # Check for special actions
        if move.upper() == "RESIGN":
            return {"action": "resign", "thinking_tokens": thinking_tokens}
        elif move.upper() == "DRAW_OFFER":
            return {"action": "draw_offer", "thinking_tokens": thinking_tokens}
        else:
            return {"move": move, "thinking_tokens": thinking_tokens}
        
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
            reasoning_effort="low",
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
        
        # Extract thinking tokens
        thinking_tokens = 0
        if hasattr(response, 'usage') and hasattr(response.usage, 'completion_tokens_details') and hasattr(response.usage.completion_tokens_details, 'reasoning_tokens'):
            thinking_tokens = response.usage.completion_tokens_details.reasoning_tokens
        
        # Check for special actions
        if move.upper() == "RESIGN":
            return {"action": "resign", "thinking_tokens": thinking_tokens}
        elif move.upper() == "DRAW_OFFER":
            return {"action": "draw_offer", "thinking_tokens": thinking_tokens}
        else:
            return {"move": move, "thinking_tokens": thinking_tokens}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling X.AI API: {str(e)}")

async def stream_gemini_move(model: str, prompt: str) -> AsyncGenerator[str, None]:
    """Stream Gemini API response with thinking outputs."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        yield f"data: {json.dumps({'type': 'error', 'message': 'GEMINI_API_KEY not configured'})}\n\n"
        return

    try:
        client = genai.Client(api_key=api_key)
        thinking_content = ""
        final_response = ""
        thinking_tokens = 0
        
        # Configure thinking for both models
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                include_thoughts=True
            )
        )
        
        # Indicate we're starting to think
        yield f"data: {json.dumps({'type': 'thinking_start'})}\n\n"
        
        # Stream the response
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=prompt,
            config=config
        ):
            if hasattr(chunk, 'candidates') and chunk.candidates:
                for candidate in chunk.candidates:
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            # Skip if no text
                            if not hasattr(part, 'text') or not part.text:
                                continue
                                
                            # Check if this is a thought
                            if hasattr(part, 'thought') and part.thought:
                                # This is thinking content
                                thinking_content += part.text
                                yield f"data: {json.dumps({'type': 'thinking_delta', 'content': part.text})}\n\n"
                                await asyncio.sleep(0)  # Allow event loop to process
                            else:
                                # This is the actual response
                                if thinking_content and not final_response:
                                    # First response text after thinking
                                    yield f"data: {json.dumps({'type': 'thinking_end'})}\n\n"
                                    yield f"data: {json.dumps({'type': 'response_start'})}\n\n"
                                final_response += part.text
                                yield f"data: {json.dumps({'type': 'response_delta', 'content': part.text})}\n\n"
            
            # Check for usage metadata
            if hasattr(chunk, 'usage_metadata'):
                if hasattr(chunk.usage_metadata, 'thoughts_token_count'):
                    thinking_tokens = chunk.usage_metadata.thoughts_token_count
        
        # End response if we have one
        if final_response:
            yield f"data: {json.dumps({'type': 'response_end'})}\n\n"
        
        # Process the final response
        move = final_response.strip()
        result = {}
        
        # Check for special actions
        if move.upper() == "RESIGN":
            result = {"action": "resign", "thinking_tokens": thinking_tokens}
        elif move.upper() == "DRAW_OFFER":
            result = {"action": "draw_offer", "thinking_tokens": thinking_tokens}
        else:
            result = {"move": move, "thinking_tokens": thinking_tokens}
        
        # Send the final result
        yield f"data: {json.dumps({'type': 'result', 'data': result})}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

async def stream_anthropic_move(model: str, prompt: str) -> AsyncGenerator[str, None]:
    """Stream Anthropic API response with thinking outputs."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        yield f"data: {json.dumps({'type': 'error', 'message': 'ANTHROPIC_API_KEY not configured'})}\n\n"
        return

    try:
        client = Anthropic(api_key=api_key)
        thinking_content = ""
        final_response = ""
        thinking_tokens = 0
        
        with client.messages.stream(
            model=model,
            max_tokens=1100,
            thinking={
                "type": "enabled",
                "budget_tokens": 1024
            },
            system="You are a chess AI. When thinking is enabled, use your thinking to analyze the position thoroughly, then provide only the chess move (or RESIGN/DRAW_OFFER) in your response without any explanation.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        ) as stream:
            block_types = {}
            
            for event in stream:
                if event.type == "content_block_start":
                    block_types[event.index] = event.content_block.type
                    
                    if event.content_block.type == "thinking":
                        yield f"data: {json.dumps({'type': 'thinking_start'})}\n\n"
                    elif event.content_block.type == "text":
                        yield f"data: {json.dumps({'type': 'response_start'})}\n\n"
                        
                elif event.type == "content_block_delta":
                    if hasattr(event, 'index') and event.index in block_types:
                        block_type = block_types[event.index]
                        
                        # Handle thinking_delta events
                        if event.delta.type == "thinking_delta":
                            text_content = None
                            if hasattr(event.delta, 'thinking'):
                                text_content = event.delta.thinking
                            elif hasattr(event.delta, 'text'):
                                text_content = event.delta.text
                            
                            if text_content:
                                thinking_content += text_content
                                yield f"data: {json.dumps({'type': 'thinking_delta', 'content': text_content})}\n\n"
                                await asyncio.sleep(0)  # Allow the event loop to process
                                
                        elif event.delta.type == "text_delta" and hasattr(event.delta, 'text'):
                            if block_type == "thinking":
                                # Fallback for any text_delta in thinking blocks
                                thinking_content += event.delta.text
                                yield f"data: {json.dumps({'type': 'thinking_delta', 'content': event.delta.text})}\n\n"
                            else:
                                final_response += event.delta.text
                                yield f"data: {json.dumps({'type': 'response_delta', 'content': event.delta.text})}\n\n"
                                
                elif event.type == "content_block_stop":
                    if hasattr(event, 'index') and event.index in block_types:
                        block_type = block_types[event.index]
                        if block_type == "thinking":
                            yield f"data: {json.dumps({'type': 'thinking_end'})}\n\n"
                        else:
                            yield f"data: {json.dumps({'type': 'response_end'})}\n\n"
                            
                elif event.type == "message_stop":
                    # For Anthropic streaming, thinking tokens aren't reported in usage
                    # Count from the captured thinking content
                    if thinking_content:
                        thinking_tokens = len(thinking_content.split())
                    break
        
        # Process the final response - our prompt instructs Claude to return only the move
        move = final_response.strip()
        result = {}
        
        # Check for special actions
        if move.upper() == "RESIGN":
            result = {"action": "resign", "thinking_tokens": thinking_tokens}
        elif move.upper() == "DRAW_OFFER":
            result = {"action": "draw_offer", "thinking_tokens": thinking_tokens}
        else:
            result = {"move": move, "thinking_tokens": thinking_tokens}
        
        # Send the final result
        yield f"data: {json.dumps({'type': 'result', 'data': result})}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

async def stream_grok_move(model: str, prompt: str) -> AsyncGenerator[str, None]:
    """Stream Grok API response with thinking outputs."""
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        yield f"data: {json.dumps({'type': 'error', 'message': 'XAI_API_KEY not configured'})}\n\n"
        return

    try:
        client = OpenAI(
            base_url="https://api.x.ai/v1",
            api_key=api_key
        )
        
        thinking_content = ""
        final_response = ""
        thinking_tokens = 0
        
        # Indicate we're starting
        yield f"data: {json.dumps({'type': 'thinking_start'})}\n\n"
        
        # Create streaming response
        stream = client.chat.completions.create(
            model=model,
            reasoning_effort="low",
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
            temperature=0.7,
            stream=True
        )
        
        in_thinking = True
        
        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                choice = chunk.choices[0]
                
                # Handle reasoning content
                if hasattr(choice.delta, 'reasoning_content') and choice.delta.reasoning_content:
                    thinking_content += choice.delta.reasoning_content
                    yield f"data: {json.dumps({'type': 'thinking_delta', 'content': choice.delta.reasoning_content})}\n\n"
                    await asyncio.sleep(0)  # Allow event loop to process
                
                # Handle final response content
                if hasattr(choice.delta, 'content') and choice.delta.content:
                    # If we were showing reasoning, transition to response
                    if thinking_content and not final_response and in_thinking:
                        yield f"data: {json.dumps({'type': 'thinking_end'})}\n\n"
                        yield f"data: {json.dumps({'type': 'response_start'})}\n\n"
                        in_thinking = False
                    
                    final_response += choice.delta.content
                    yield f"data: {json.dumps({'type': 'response_delta', 'content': choice.delta.content})}\n\n"
        
        # End response if we have one
        if final_response:
            yield f"data: {json.dumps({'type': 'response_end'})}\n\n"
        
        # Extract thinking tokens if available (this might need adjustment based on actual API response)
        # The usage data is typically available after streaming completes
        thinking_tokens = len(thinking_content.split()) if thinking_content else 0
        
        # Process the final response
        move = final_response.strip()
        result = {}
        
        # Check for special actions
        if move.upper() == "RESIGN":
            result = {"action": "resign", "thinking_tokens": thinking_tokens}
        elif move.upper() == "DRAW_OFFER":
            result = {"action": "draw_offer", "thinking_tokens": thinking_tokens}
        else:
            result = {"move": move, "thinking_tokens": thinking_tokens}
        
        # Send the final result
        yield f"data: {json.dumps({'type': 'result', 'data': result})}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

async def stream_openai_move(model: str, prompt: str) -> AsyncGenerator[str, None]:
    """Stream OpenAI o4-mini API response with thinking outputs."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        yield f"data: {json.dumps({'type': 'error', 'message': 'OPENAI_API_KEY not configured'})}\n\n"
        return

    try:
        client = OpenAI(api_key=api_key)
        
        reasoning_content = ""
        final_response = ""
        thinking_tokens = 0
        reasoning_started = False
        answer_started = False
        
        # Create streaming response for o4-mini
        response = client.responses.create(
            model=model,
            input=prompt,
            reasoning={
                "summary": "detailed", 
                "effort": "low"
            },
            stream=True
        )
        
        # Process the stream events
        for event in response:
            if event.type == 'response.reasoning_summary_text.delta':
                # Stream reasoning text in real time
                if not reasoning_started:
                    yield f"data: {json.dumps({'type': 'thinking_start'})}\n\n"
                    reasoning_started = True
                
                reasoning_content += event.delta
                yield f"data: {json.dumps({'type': 'thinking_delta', 'content': event.delta})}\n\n"
                await asyncio.sleep(0)  # Allow event loop to process
                
            elif event.type == 'response.reasoning_summary_text.done':
                # Reasoning is complete
                yield f"data: {json.dumps({'type': 'thinking_end'})}\n\n"
                
            elif event.type == 'response.output_text.delta':
                # Stream answer text in real time
                if not answer_started:
                    yield f"data: {json.dumps({'type': 'response_start'})}\n\n"
                    answer_started = True
                    
                final_response += event.delta
                yield f"data: {json.dumps({'type': 'response_delta', 'content': event.delta})}\n\n"
            
            elif event.type == 'response.output_text.done':
                # Final answer is complete
                yield f"data: {json.dumps({'type': 'response_end'})}\n\n"
                
            elif event.type == 'response.completed':
                # Extract thinking tokens from usage
                if hasattr(event, 'response') and hasattr(event.response, 'usage'):
                    if hasattr(event.response.usage, 'output_tokens_details') and hasattr(event.response.usage.output_tokens_details, 'reasoning_tokens'):
                        thinking_tokens = event.response.usage.output_tokens_details.reasoning_tokens
                
                # Workaround: If OpenAI streaming doesn't report thinking tokens correctly,
                # estimate them from reasoning content length (roughly 4 chars per token)
                if thinking_tokens == 0 and reasoning_content:
                    thinking_tokens = max(1, len(reasoning_content) // 4)
                break
        
        # Process the final response
        move = final_response.strip()
        result = {}
        
        # Check for special actions
        if move.upper() == "RESIGN":
            result = {"action": "resign", "thinking_tokens": thinking_tokens}
        elif move.upper() == "DRAW_OFFER":
            result = {"action": "draw_offer", "thinking_tokens": thinking_tokens}
        else:
            result = {"move": move, "thinking_tokens": thinking_tokens}
        
        # Send the final result
        yield f"data: {json.dumps({'type': 'result', 'data': result})}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

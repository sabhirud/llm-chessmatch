#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test server for Anthropic streaming with thinking outputs.
Run with: python test.py
"""

import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from anthropic import Anthropic
from typing import Dict, Any

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Anthropic Streaming Test Server", "endpoints": ["/test-stream"]}

@app.get("/test-stream")
async def test_stream(prompt: str = "Why is division by zero (1/0) not possible mathematically? Please explain."):
    """Test endpoint for Anthropic streaming with thinking enabled."""
    
    return StreamingResponse(
        stream_anthropic_thinking(prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "X-Accel-Buffering": "no",
        }
    )

async def stream_anthropic_thinking(prompt: str):
    """Stream Anthropic API response with thinking enabled."""
    
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        yield f"data: {json.dumps({'error': 'ANTHROPIC_API_KEY environment variable not set'})}\n\n"
        return
    
    try:
        client = Anthropic(api_key=api_key)
        thinking_content = ""
        final_response = ""
        
        # Send initial info
        yield f"data: {json.dumps({'type': 'info', 'message': 'Starting Anthropic streaming test'})}\n\n"
        yield f"data: {json.dumps({'type': 'info', 'prompt': prompt[:100] + '...' if len(prompt) > 100 else prompt})}\n\n"
        
        with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=1100,
            thinking={
                "type": "enabled",
                "budget_tokens": 1024
            },
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
                                yield f"data: {json.dumps({'type': 'thinking_delta', 'text': text_content})}\n\n"
                                
                        elif event.delta.type == "text_delta" and hasattr(event.delta, 'text'):
                            if block_type == "thinking":
                                # Fallback for any text_delta in thinking blocks
                                thinking_content += event.delta.text
                                yield f"data: {json.dumps({'type': 'thinking_delta', 'text': event.delta.text})}\n\n"
                            else:
                                final_response += event.delta.text
                                yield f"data: {json.dumps({'type': 'response_delta', 'text': event.delta.text})}\n\n"
                                
                elif event.type == "content_block_stop":
                    if hasattr(event, 'index') and event.index in block_types:
                        block_type = block_types[event.index]
                        if block_type == "thinking":
                            yield f"data: {json.dumps({'type': 'thinking_end'})}\n\n"
                        else:
                            yield f"data: {json.dumps({'type': 'response_end'})}\n\n"
                            
                elif event.type == "message_stop":
                    break
        
        # Send summary
        yield f"data: {json.dumps({'type': 'summary', 'thinking_tokens': len(thinking_content.split()) if thinking_content else 0, 'final_response': final_response.strip(), 'thinking_chars': len(thinking_content)})}\n\n"
        
        if not thinking_content:
            yield f"data: {json.dumps({'type': 'warning', 'message': 'No thinking content received!'})}\n\n"
        
        if not final_response:
            yield f"data: {json.dumps({'type': 'warning', 'message': 'No final response received!'})}\n\n"
            
        yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

if __name__ == "__main__":
    import uvicorn
    print("Starting Anthropic Streaming Test Server")
    print("Test endpoint: GET http://localhost:8001/test-stream")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8001)
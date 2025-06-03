#!/usr/bin/env python3
"""Test script to verify Grok streaming for chess moves."""

import asyncio
import json
import os
from openai import OpenAI

async def test_grok_chess_streaming():
    """Test Grok streaming with chess-specific prompt."""
    
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        print("ERROR: XAI_API_KEY environment variable not set")
        return
    
    client = OpenAI(
        base_url="https://api.x.ai/v1",
        api_key=api_key
    )
    
    prompt = """You are a chess AI. Given the current game state and move history, you can either:
1. Make a chess move in standard algebraic notation (e.g., "e4", "Nf3", "O-O")
2. Resign by responding with exactly "RESIGN"
3. Offer a draw by responding with exactly "DRAW_OFFER"

Game State (FEN): rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
Move History: No moves yet

Respond with either a move, "RESIGN", or "DRAW_OFFER"."""
    
    print("🎯 Testing Grok Chess Streaming")
    print("=" * 60)
    print(f"Prompt: {prompt[:100]}...")
    print("=" * 60)
    
    thinking_content = ""
    final_response = ""
    
    try:
        stream = client.chat.completions.create(
            model="grok-3-mini",
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
        
        print("\n🧠 Reasoning Process:")
        print("-" * 50)
        
        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                choice = chunk.choices[0]
                
                # Handle reasoning content
                if hasattr(choice.delta, 'reasoning_content') and choice.delta.reasoning_content:
                    thinking_content += choice.delta.reasoning_content
                    print(choice.delta.reasoning_content, end="", flush=True)
                
                # Handle final response content
                if hasattr(choice.delta, 'content') and choice.delta.content:
                    # If we were showing reasoning, add some separation
                    if thinking_content and not final_response:
                        print("\n" + "=" * 50)
                        print("💡 Final Move:")
                        print("-" * 50)
                    
                    final_response += choice.delta.content
                    print(choice.delta.content, end="", flush=True)
        
        print("\n" + "=" * 60)
        print("✅ Streaming Test Complete!")
        print(f"Thinking tokens: ~{len(thinking_content.split())}")
        print(f"Final move: {final_response.strip()}")
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_grok_chess_streaming())
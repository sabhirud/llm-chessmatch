#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Anthropic streaming with thinking outputs.
Run with: python streaming.py [prompt]
"""

import os
import json
import asyncio
import argparse
import time
from anthropic import Anthropic

async def stream_anthropic_thinking(prompt: str):
    """Stream Anthropic API response with thinking enabled."""
    
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        return
    
    try:
        client = Anthropic(api_key=api_key)
        thinking_content = ""
        final_response = ""
        
        # Timing variables
        start_time = time.time()
        thinking_start_time = None
        thinking_end_time = None
        response_start_time = None
        response_end_time = None
        
        # Send initial info
        print("=" * 60)
        print("Starting Anthropic streaming test")
        print(f"Prompt: {prompt[:100] + '...' if len(prompt) > 100 else prompt}")
        print("=" * 60)
        
        with client.messages.stream(
            model="claude-opus-4-20250514",
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
                        thinking_start_time = time.time()
                        print("\n🤔 THINKING:")
                        print("-" * 40)
                    elif event.content_block.type == "text":
                        response_start_time = time.time()
                        print("\n💬 RESPONSE:")
                        print("-" * 40)
                        
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
                                print(text_content, end='', flush=True)
                                
                        elif event.delta.type == "text_delta" and hasattr(event.delta, 'text'):
                            if block_type == "thinking":
                                # Fallback for any text_delta in thinking blocks
                                thinking_content += event.delta.text
                                print(event.delta.text, end='', flush=True)
                            else:
                                final_response += event.delta.text
                                print(event.delta.text, end='', flush=True)
                                
                elif event.type == "content_block_stop":
                    if hasattr(event, 'index') and event.index in block_types:
                        block_type = block_types[event.index]
                        if block_type == "thinking":
                            thinking_end_time = time.time()
                            print("\n" + "-" * 40)
                        else:
                            response_end_time = time.time()
                            print("\n" + "-" * 40)
                            
                elif event.type == "message_stop":
                    break
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Calculate phase durations
        thinking_duration = None
        response_duration = None
        
        if thinking_start_time and thinking_end_time:
            thinking_duration = thinking_end_time - thinking_start_time
            
        if response_start_time and response_end_time:
            response_duration = response_end_time - response_start_time
        
        # Send summary
        print("\n" + "=" * 60)
        print("SUMMARY:")
        print(f"Total time: {total_time:.2f} seconds")
        
        if thinking_duration:
            print(f"Thinking time: {thinking_duration:.2f} seconds")
        if response_duration:
            print(f"Response time: {response_duration:.2f} seconds")
            
        print(f"Thinking tokens: {len(thinking_content.split()) if thinking_content else 0}")
        print(f"Thinking characters: {len(thinking_content)}")
        print(f"Final response length: {len(final_response.strip())} characters")
        
        # Calculate tokens/characters per second if we have timing data
        if thinking_duration and thinking_content:
            thinking_chars_per_sec = len(thinking_content) / thinking_duration
            print(f"Thinking speed: {thinking_chars_per_sec:.1f} chars/sec")
            
        if response_duration and final_response:
            response_chars_per_sec = len(final_response) / response_duration
            print(f"Response speed: {response_chars_per_sec:.1f} chars/sec")
        
        if not thinking_content:
            print("⚠️  WARNING: No thinking content received!")
        
        if not final_response:
            print("⚠️  WARNING: No final response received!")
            
        print("✅ Complete!")
        print("=" * 60)
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

async def main():
    parser = argparse.ArgumentParser(description="Test Anthropic streaming with thinking outputs")
    parser.add_argument(
        "prompt", 
        nargs='?', 
        default="Why is division by zero (1/0) not possible mathematically? Please explain.",
        help="The prompt to send to Claude (default: division by zero explanation)"
    )
    
    args = parser.parse_args()
    
    await stream_anthropic_thinking(args.prompt)

if __name__ == "__main__":
    asyncio.run(main())
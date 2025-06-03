from openai import OpenAI

client = OpenAI()

response = client.responses.create(
    model="o4-mini", 
    input="""You are a chess AI. Given the current game state, you can either:
    1. Make a chess move in standard algebraic notation (e.g., "e4", "Nf3", "O-O")
    2. Resign by responding with exactly "RESIGN"
    3. Offer a draw by responding with exactly "DRAW_OFFER"

    Game State (FEN): rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1

    Respond with either a move, "RESIGN", or "DRAW_OFFER".""",
    reasoning={"summary": "detailed", "effort": "high"},
    stream=True
)

reasoning_text = ""
answer_text = ""
reasoning_started = False
answer_started = False

# Process the stream events
for event in response:
    if event.type == 'response.reasoning_summary_text.delta':
        # Stream reasoning text in real time
        if not reasoning_started:
            print("\n🧠 REASONING:")
            print("-" * 50)
            reasoning_started = True
        
        reasoning_text += event.delta
        print(event.delta, end='', flush=True)
        
    elif event.type == 'response.reasoning_summary_text.done':
        # Reasoning is complete
        print("\n" + "-" * 50)
        print("✅ Reasoning complete\n")
        
    elif event.type == 'response.output_text.delta':
        # Stream answer text in real time
        if not answer_started:
            print("💡 FINAL ANSWER:")
            print("=" * 50)
            answer_started = True
            
        answer_text += event.delta
        print(event.delta, end='', flush=True)
    
    elif event.type == 'response.output_text.done':
        # Final answer is complete
        print("\n" + "=" * 50)
        print("✅ Answer complete")

print(f"\n\nFinal reasoning length: {len(reasoning_text)} characters")
print(f"Final answer length: {len(answer_text)} characters")
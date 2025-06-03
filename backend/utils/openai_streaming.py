from openai import OpenAI

client = OpenAI()

response = client.responses.create(
    model="o4-mini", 
    input="What is the meaning of life?",
    reasoning={"summary": "detailed"},
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
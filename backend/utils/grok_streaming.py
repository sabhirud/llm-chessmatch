import os
from openai import OpenAI

messages = [
    {
        "role": "system",
        "content": "You are a highly intelligent AI assistant.",
    },
    {
        "role": "user",
        "content": "How many characters are in your response to this message?",
    },
]

client = OpenAI(
    base_url="https://api.x.ai/v1",
    api_key=os.getenv("XAI_API_KEY"),
)

stream = client.chat.completions.create(
    model="grok-3-mini",
    reasoning_effort="low",
    messages=messages,
    temperature=0.7,
    stream=True
)

print("🧠 Reasoning Process:")
print("-" * 50)

reasoning_content = ""
final_content = ""

for chunk in stream:
    if chunk.choices and len(chunk.choices) > 0:
        choice = chunk.choices[0]
        
        # Handle reasoning content
        if hasattr(choice.delta, 'reasoning_content') and choice.delta.reasoning_content:
            reasoning_content += choice.delta.reasoning_content
            print(choice.delta.reasoning_content, end="", flush=True)
        
        # Handle final response content
        if hasattr(choice.delta, 'content') and choice.delta.content:
            # If we were showing reasoning, add some separation
            if reasoning_content and not final_content:
                print("\n" + "=" * 50)
                print("💡 Final Answer:")
                print("-" * 50)
            
            final_content += choice.delta.content
            print(choice.delta.content, end="", flush=True)

print("\n" + "=" * 50)
print("✅ Complete!")

# print("Reasoning Content:")
# print(completion.choices[0].message.reasoning_content)

# print("\nFinal Response:")
# print(completion.choices[0].message.content)

# print("\nNumber of completion tokens (input):")
# print(completion.usage.completion_tokens)

# print("\nNumber of reasoning tokens (input):")
# print(completion.usage.completion_tokens_details.reasoning_tokens)
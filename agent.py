import os
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def create_agent():
    """
    Creates and runs a simple AI agent using the Groq API (Llama 3).
    """
    
    # 1. Get API Key
    # We look for the key in the environment variables.
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("Error: GROQ_API_KEY not found.")
        print("Please create a .env file in this folder with: GROQ_API_KEY=your_key_here")
        print("You can get a free key at: https://console.groq.com/keys")
        return

    # 2. Initialize the Client
    # This connects to the Groq servers which host the Llama models.
    client = Groq(api_key=api_key)
    
    print("--------------------------------------------------")
    print("🤖 Llama 3 Agent Initialized! (Type 'quit' to exit)")
    print("--------------------------------------------------")

    # 3. The Conversation Loop
    # We keep a history of messages so the AI remembers the context.
    messages = [
        {
            "role": "system",
            "content": "You are a helpful and intelligent AI assistant powered by Llama 3."
        }
    ]

    while True:
        # Get user input
        user_input = input("\nYou: ")
        
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("Goodbye! 👋")
            break

        # Add user message to history
        messages.append({"role": "user", "content": user_input})

        try:
            # 4. Call the Model
            # We send the entire conversation history to the model.
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile", # Latest powerful model
                messages=messages,
                temperature=0.7,        # Controls creativity (0.0 = strict, 1.0 = creative)
                max_tokens=1024,        # Maximum length of response
                stream=True,            # Stream the response so it looks like it's typing
            )

            print("Agent: ", end="", flush=True)
            
            full_response = ""
            
            # 5. Stream the Response
            for chunk in completion:
                content = chunk.choices[0].delta.content
                if content:
                    print(content, end="", flush=True)
                    full_response += content
            
            print() # Newline after response

            # Add AI response to history so it remembers it next time
            messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            print(f"\nError calling API: {e}")

if __name__ == "__main__":
    create_agent()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
import os
from typing import List, Optional

# Load environment variables from the parent directory
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

app = FastAPI()

# Enable CORS so our HTML file can talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Groq Client
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    agent_id: str
    message: str
    history: List[Message]

# Define our Agents' Personalities
AGENTS = {
    "agent_1": {
        "name": "Nova",
        "system_prompt": "You are Nova, a futuristic, highly logical, and precise AI assistant. You love technology, space, and science. Your tone is professional but enthusiastic about the future. Keep responses concise and insightful."
    },
    "agent_2": {
        "name": "Blaze",
        "system_prompt": "You are Blaze, a creative, rebellious, and artistic AI. You love poetry, design, and thinking outside the box. Your tone is casual, colorful, and sometimes a bit dramatic. You use emojis often."
    }
}

@app.post("/chat")
async def chat(request: ChatRequest):
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not found in .env")
    
    agent = AGENTS.get(request.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Construct the message history
    messages = [{"role": "system", "content": agent["system_prompt"]}]
    
    # Add previous history
    for msg in request.history:
        messages.append({"role": msg.role, "content": msg.content})
    
    # Add the new user message
    messages.append({"role": "user", "content": request.message})

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
            stream=False
        )
        
        response_text = completion.choices[0].message.content
        return {"response": response_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

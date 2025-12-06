from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
import os
import json
import asyncio
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager, AsyncExitStack

# MCP Imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

# --- MCP Client Setup ---
# We need a global session to keep the connection open
mcp_session: Optional[ClientSession] = None
mcp_tools: List[Dict[str, Any]] = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for the FastAPI app.
    Starts the MCP Client when the server starts, and closes it when it stops.
    """
    global mcp_session, mcp_tools
    
    # Path to local mcp_server.py
    server_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "mcp_server.py"))
    
    print(f"🔌 Connecting to MCP Server at: {server_script}")
    
    server_params = StdioServerParameters(
        command="python3",
        args=[server_script],
    )

    # Start the MCP Client
    # We use an ExitStack to manage the nested context managers manually but safely
    
    async with AsyncExitStack() as stack:
        try:
            transport = await stack.enter_async_context(stdio_client(server_params))
            read, write = transport
            
            mcp_session = await stack.enter_async_context(ClientSession(read, write))
            await mcp_session.initialize()
            
            # Fetch available tools
            tools_result = await mcp_session.list_tools()
            
            # Convert MCP tools to Groq/OpenAI Tool Format
            mcp_tools = []
            for tool in tools_result.tools:
                mcp_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema
                    }
                })
                
            print(f"✅ MCP Connected! Loaded {len(mcp_tools)} tools: {[t['function']['name'] for t in mcp_tools]}")
            
            # Yield control back to FastAPI to run the app
            yield
            
        except Exception as e:
            print(f"❌ Error during MCP startup: {e}")
            # If startup fails, we still yield so the app can crash gracefully or show error
            yield
        finally:
            print("🔌 Closing MCP Connection...")
            # The AsyncExitStack will automatically close session and transport here


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

class Message(BaseModel):
    role: str
    content: str
    tool_calls: Optional[List[Any]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

class ChatRequest(BaseModel):
    agent_id: str
    system_prompt: str  # New field: Frontend sends the prompt
    message: str
    history: List[Message]

@app.post("/chat")
async def chat(request: ChatRequest):
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not found")
    
    # We no longer look up hardcoded agents. 
    # We use the system_prompt provided by the frontend.

    # Prepare messages
    messages = [{"role": "system", "content": request.system_prompt}]
    for msg in request.history:
        # Filter out fields that Groq might not like if they are None
        m = {"role": msg.role, "content": msg.content}
        if msg.tool_calls:
            m["tool_calls"] = msg.tool_calls
        if msg.tool_call_id:
            m["tool_call_id"] = msg.tool_call_id
        if msg.name:
            m["name"] = msg.name
        messages.append(m)
        
    messages.append({"role": "user", "content": request.message})

    try:
        # 1. First Call to LLM (with tools)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=mcp_tools if mcp_tools else None,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=1024
        )
        
        response_message = completion.choices[0].message
        
        # 2. Check if LLM wants to use a tool
        if response_message.tool_calls:
            print(f"🛠️ Agent wants to use tools: {len(response_message.tool_calls)}")
            
            # Add the assistant's "thought" (tool call request) to history
            messages.append(response_message)
            
            # Execute each tool
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                print(f"   👉 Executing {function_name} with {function_args}")
                
                # Call MCP Server
                if mcp_session:
                    result = await mcp_session.call_tool(function_name, arguments=function_args)
                    tool_output = result.content[0].text
                else:
                    tool_output = "Error: MCP Session not active."
                
                print(f"   ✅ Result: {tool_output}")

                # Add result to history
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": tool_output
                })
            
            # 3. Second Call to LLM (to generate final answer based on tool results)
            second_completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages
            )
            return {"response": second_completion.choices[0].message.content}
            
        else:
            # No tool used, just return text
            return {"response": response_message.content}

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

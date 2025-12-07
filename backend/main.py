from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from groq import Groq
import os
import json
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager, AsyncExitStack

# MCP Imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Local Imports (using relative imports within package)
from backend.rag import vector_store, document_processor
from backend.config import GROQ_API_KEY, MCP_SERVER_PATH, FRONTEND_DIR

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
    
    print(f"🔌 Connecting to MCP Server at: {MCP_SERVER_PATH}")
    
    server_params = StdioServerParameters(
        command="python3",
        args=[MCP_SERVER_PATH],
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
            
            # Initialize Vector Store for RAG
            print("🧠 Initializing Vector Store...")
            vector_store.init()
            
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

# Serve frontend static files
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Groq Client
client = Groq(api_key=GROQ_API_KEY)

class Message(BaseModel):
    role: str
    content: str
    tool_calls: Optional[List[Any]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

class ChatRequest(BaseModel):
    agent_id: str
    system_prompt: str
    model: str = "llama-3.3-70b-versatile" # Default model
    message: str
    history: List[Message]
    use_rag: bool = True  # Enable RAG by default

class UrlUploadRequest(BaseModel):
    agent_id: str
    url: str

@app.post("/chat")
async def chat(request: ChatRequest):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not found")
    
    # --- RAG: Retrieve relevant context ---
    rag_context = ""
    sources = []
    
    if request.use_rag:
        try:
            results = vector_store.search(request.agent_id, request.message, top_k=5)
            if results:
                print(f"🔍 RAG: Found {len(results)} relevant chunks")
                context_parts = []
                for r in results:
                    context_parts.append(r["text"])
                    sources.append({
                        "document_id": r["document_id"],
                        "score": round(r["score"], 3),
                        "metadata": r["metadata"]
                    })
                rag_context = "\n\n".join(context_parts)
        except Exception as e:
            print(f"⚠️ RAG search error: {e}")
    
    # Build system prompt with RAG context
    enhanced_prompt = request.system_prompt
    if rag_context:
        enhanced_prompt += f"""

---
KNOWLEDGE BASE CONTEXT:
Use the following information to help answer the user's question. If the information is relevant, cite it in your response.

{rag_context}
---
"""
    
    # Prepare messages
    messages = [{"role": "system", "content": enhanced_prompt}]
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
            model=request.model, # Use the model requested by frontend
            messages=messages,
            tools=mcp_tools if mcp_tools else None,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=1024
        )
        
        response_message = completion.choices[0].message
        reasoning_parts = []
        
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
                reasoning_parts.append(f"🔧 Calling {function_name}({function_args})")
                
                # Call MCP Server
                if mcp_session:
                    result = await mcp_session.call_tool(function_name, arguments=function_args)
                    tool_output = result.content[0].text
                else:
                    tool_output = "Error: MCP Session not active."
                
                print(f"   ✅ Result: {tool_output}")
                reasoning_parts.append(f"📤 Result: {tool_output}")

                # Add result to history
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": tool_output
                })
            
            # 3. Second Call to LLM (to generate final answer based on tool results)
            second_completion = client.chat.completions.create(
                model=request.model,
                messages=messages
            )
            return {
                "response": second_completion.choices[0].message.content,
                "reasoning": "\n".join(reasoning_parts) if reasoning_parts else None,
                "sources": sources if sources else None
            }
            
        else:
            # No tool used, just return text
            return {
                "response": response_message.content,
                "reasoning": None,
                "sources": sources if sources else None
            }

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Document Upload Endpoints ---

@app.post("/documents/upload")
async def upload_document(
    agent_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload a document (TXT, PDF, DOCX, CSV) to an agent's knowledge base."""
    try:
        content = await file.read()
        
        # Process the document
        document_id, chunks, metadata = document_processor.process_document(
            content=content,
            filename=file.filename
        )
        
        # Add to vector store
        chunk_count = vector_store.add_chunks(
            agent_id=agent_id,
            document_id=document_id,
            chunks=chunks,
            metadata=metadata
        )
        
        return {
            "success": True,
            "document_id": document_id,
            "filename": file.filename,
            "chunks": chunk_count,
            "metadata": metadata
        }
        
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/documents/url")
async def upload_url(request: UrlUploadRequest):
    """Add a web URL to an agent's knowledge base."""
    try:
        # Process the URL
        document_id, chunks, metadata = document_processor.process_document(
            url=request.url
        )
        
        # Add to vector store
        chunk_count = vector_store.add_chunks(
            agent_id=request.agent_id,
            document_id=document_id,
            chunks=chunks,
            metadata=metadata
        )
        
        return {
            "success": True,
            "document_id": document_id,
            "url": request.url,
            "chunks": chunk_count,
            "metadata": metadata
        }
        
    except Exception as e:
        print(f"URL upload error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/documents/{agent_id}")
async def list_documents(agent_id: str):
    """List all documents in an agent's knowledge base."""
    try:
        documents = vector_store.list_documents(agent_id)
        return {
            "agent_id": agent_id,
            "documents": documents,
            "count": len(documents)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{agent_id}/{document_id}")
async def delete_document(agent_id: str, document_id: str):
    """Delete a document from an agent's knowledge base."""
    try:
        deleted = vector_store.delete_document(agent_id, document_id)
        return {
            "success": True,
            "document_id": document_id,
            "deleted_chunks": deleted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/stats")
async def get_stats():
    """Get vector store statistics."""
    return vector_store.get_stats()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


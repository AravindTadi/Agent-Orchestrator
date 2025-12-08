from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from groq import Groq
import os
import json
import uuid
import logging
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager, AsyncExitStack

# MCP Imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Local Imports
from backend.rag import vector_store, document_processor
from backend.config import GROQ_API_KEY, MCP_SERVER_PATH, FRONTEND_DIR
from backend import database

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            
            # Initialize Database
            print("💾 Initializing Database...")
            database.init_db()
            
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


# --- Agent CRUD Endpoints ---

class AgentCreate(BaseModel):
    name: str
    description: str = ""
    system_prompt: str = "You are a helpful AI assistant."

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None


@app.get("/agents")
async def list_agents():
    """List all agents."""
    agents = database.get_all_agents()
    return {"agents": agents, "count": len(agents)}


@app.post("/agents")
async def create_agent(agent: AgentCreate):
    """Create a new agent."""
    agent_id = f"agent_{uuid.uuid4().hex[:8]}"
    try:
        new_agent = database.create_agent(
            agent_id=agent_id,
            name=agent.name,
            description=agent.description,
            system_prompt=agent.system_prompt
        )
        logger.info(f"Created agent: {agent_id}")
        return {"success": True, "agent": new_agent}
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get an agent by ID."""
    agent = database.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@app.put("/agents/{agent_id}")
async def update_agent(agent_id: str, agent: AgentUpdate):
    """Update an agent."""
    existing = database.get_agent(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    updates = {k: v for k, v in agent.dict().items() if v is not None}
    updated = database.update_agent(agent_id, **updates)
    logger.info(f"Updated agent: {agent_id}")
    return {"success": True, "agent": updated}


@app.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete an agent and all its knowledge base documents."""
    if agent_id == "agent_default":
        raise HTTPException(status_code=400, detail="Cannot delete default agent")
    
    # First, delete all knowledge base documents for this agent
    try:
        deleted_chunks = vector_store.delete_all_agent_documents(agent_id)
        logger.info(f"Deleted {deleted_chunks} knowledge base chunks for agent: {agent_id}")
    except Exception as e:
        logger.warning(f"Error deleting knowledge base for agent {agent_id}: {e}")
    
    # Then delete the agent from database
    success = database.delete_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    logger.info(f"Deleted agent: {agent_id}")
    return {"success": True, "agent_id": agent_id, "deleted_chunks": deleted_chunks if 'deleted_chunks' in dir() else 0}


# --- Health Check ---

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "mcp_connected": mcp_session is not None,
        "tools_loaded": len(mcp_tools),
        "groq_configured": GROQ_API_KEY is not None
    }


# --- Global Error Handler ---

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG") else "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

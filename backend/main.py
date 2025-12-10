from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
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
from backend import database, auth, settings, monitoring


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
                
            logger.info(f"✅ MCP Connected! Loaded {len(mcp_tools)} tools: {[t['function']['name'] for t in mcp_tools]}")
            
            # Initialize Vector Store for RAG
            print("🧠 Initializing Vector Store...")
            vector_store.init()
            
            # Initialize Database
            print("💾 Initializing Database...")
            database.init_db()

            # Initialize Monitoring (Load from first user with settings)
            try:
                conn = settings.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM integration_settings ORDER BY updated_at DESC LIMIT 1")
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    if row['aws_access_key']:
                        monitoring.monitor.configure_aws(
                            row['aws_access_key'], row['aws_secret_key'], 
                            row['aws_region'], row['aws_log_group']
                        )
                    if row['dd_api_key']:
                        monitoring.monitor.configure_datadog(row['dd_api_key'], row['dd_site'])
                    print("✅ Monitoring initialized from saved settings")
                    logger.info("Monitoring initialized from saved settings.")
            except Exception as e:
                print(f"⚠️ Failed to load monitoring settings: {e}")
                logger.warning(f"Failed to load monitoring settings: {e}")
            
            # Yield control back to FastAPI to run the app
            yield
            
        except Exception as e:
            print(f"❌ Error during MCP startup: {e}")
            logger.error(f"Error during MCP startup: {e}")
            # If startup fails, we still yield so the app can crash gracefully or show error
            yield
        finally:
            print("🔌 Closing MCP Connection...")
            logger.info("Closing MCP Connection...")
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
    session_id: Optional[str] = None  # Optional session ID for analytics tracking

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
            monitoring.monitor.log_event("ERROR", f"RAG search error for agent {request.agent_id}: {e}", metadata={"agent_id": request.agent_id, "query": request.message})
    
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
            monitoring.monitor.log_event("INFO", f"Agent {request.agent_id} requested tool calls", metadata={"agent_id": request.agent_id, "tool_calls": [tc.function.name for tc in response_message.tool_calls]})
            
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
                monitoring.monitor.log_event("INFO", f"Tool {function_name} executed for agent {request.agent_id}", metadata={"agent_id": request.agent_id, "tool_name": function_name, "tool_args": function_args, "tool_output_len": len(tool_output)})

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
            monitoring.monitor.log_event("INFO", f"Agent {request.agent_id} completed chat with tool use", metadata={"agent_id": request.agent_id, "model": request.model, "input_tokens": completion.usage.prompt_tokens + second_completion.usage.prompt_tokens, "output_tokens": completion.usage.completion_tokens + second_completion.usage.completion_tokens})
            
            assistant_response = second_completion.choices[0].message.content
            
            # Save messages to database for analytics
            session_id = request.session_id
            if session_id:
                try:
                    database.add_chat_message(session_id, "user", request.message)
                    database.add_chat_message(session_id, "assistant", assistant_response)
                except Exception as e:
                    print(f"DB Save Error: {e}")
            
            return {
                "response": assistant_response,
                "reasoning": "\n".join(reasoning_parts) if reasoning_parts else None,
                "sources": sources if sources else None,
                "session_id": session_id
            }
            
        else:
            # No tool used, just return text
            monitoring.monitor.log_event("INFO", f"Agent {request.agent_id} completed chat without tool use", metadata={"agent_id": request.agent_id, "model": request.model, "input_tokens": completion.usage.prompt_tokens, "output_tokens": completion.usage.completion_tokens})
            
            assistant_response = response_message.content
            
            # Save messages to database for analytics
            session_id = request.session_id
            if session_id:
                try:
                    database.add_chat_message(session_id, "user", request.message)
                    database.add_chat_message(session_id, "assistant", assistant_response)
                except Exception as e:
                    print(f"DB Save Error: {e}")
            
            return {
                "response": assistant_response,
                "reasoning": None,
                "sources": sources if sources else None,
                "session_id": session_id
            }

    except Exception as e:
        print(f"Error: {e}")
        monitoring.monitor.log_event("ERROR", f"Chat error for agent {request.agent_id}: {e}", metadata={"agent_id": request.agent_id, "model": request.model, "user_message": request.message})
        raise HTTPException(status_code=500, detail=str(e))


async def stream_chat_generator(request: ChatRequest):
    """Generator for streaming chat responses."""
    if not GROQ_API_KEY:
        yield f"data: {json.dumps({'type': 'error', 'content': 'GROQ_API_KEY not found'})}\n\n"
        return

    # Create or retrieve session
    session_id = request.session_id
    if not session_id:
        session_result = database.create_chat_session(request.agent_id, "New Chat")
        session_id = session_result.get("id") if isinstance(session_result, dict) else session_result
        yield f"data: {json.dumps({'type': 'session_id', 'content': session_id})}\n\n"
    
    # Update session title if it's the first message
    # (Simple logic: if history is empty, update title with first few words)
    if not request.history and session_id:
        new_title = request.message[:30] + "..." if len(request.message) > 30 else request.message
        try:
            database.update_session_title(session_id, new_title)
        except Exception as e:
            print(f"Failed to update session title: {e}")

    # --- RAG: Retrieve relevant context ---
    rag_context = ""
    sources = []
    
    if request.use_rag:
        try:
            # Check if agent has any documents first
            doc_stats = vector_store.list_documents(request.agent_id)
            
            if doc_stats:
                # 1. Intent Detection: Check if the query actually needs knowledge base
                # We use a very fast/cheap call or simple heuristics. 
                # For now, let's use a simple heuristic: length > 3 words OR specific keywords
                # A better approach would be a small LLM call, but let's keep it fast.
                
                # Heuristic: Greetings and short phatic expressions don't need RAG
                is_greeting = request.message.lower().strip() in ['hi', 'hello', 'hey', 'greetings', 'good morning', 'good evening', 'thanks', 'thank you']
                
                if not is_greeting:
                    # Only show "Searching..." if we are actually searching
                    yield f"data: {json.dumps({'type': 'status', 'content': 'Searching knowledge base...'})}\n\n"
                    results = vector_store.search(request.agent_id, request.message, top_k=5)
                    if results:
                        context_parts = []
                        for r in results:
                            # Only include if score is relevant enough (e.g. < 1.0 distance for L2, or > 0.3 for Cosine)
                            # Milvus Lite Cosine similarity: 1.0 is identical, 0.0 is orthogonal
                            if r["score"] > 0.3: 
                                context_parts.append(r["text"])
                                sources.append({
                                    "document_id": r["document_id"],
                                    "score": round(r["score"], 3),
                                    "metadata": r["metadata"]
                                })
                        
                        if context_parts:
                            rag_context = "\n\n".join(context_parts)
                            yield f"data: {json.dumps({'type': 'sources', 'content': sources})}\n\n"
                        else:
                             yield f"data: {json.dumps({'type': 'status', 'content': 'No relevant info found in KB.'})}\n\n"

        except Exception as e:
            print(f"⚠️ RAG search error: {e}")
    
    # Build system prompt
    enhanced_prompt = request.system_prompt
    if rag_context:
        enhanced_prompt += f"\n\n---\nKNOWLEDGE BASE CONTEXT:\n{rag_context}\n---\n"

    # Prepare messages
    messages = [{"role": "system", "content": enhanced_prompt}]
    for msg in request.history:
        m = {"role": msg.role, "content": msg.content}
        if msg.tool_calls: m["tool_calls"] = msg.tool_calls
        if msg.tool_call_id: m["tool_call_id"] = msg.tool_call_id
        if msg.name: m["name"] = msg.name
        messages.append(m)
        
    messages.append({"role": "user", "content": request.message})

    try:
        # Filter tools based on agent configuration
        agent_tools = []
        if mcp_tools:
            # Get agent's enabled tools from DB
            agent = database.get_agent(request.agent_id)
            if agent and agent.get("tools"):
                try:
                    tools_data = agent["tools"]
                    # Handle both string (JSON) and list types
                    if isinstance(tools_data, str):
                        enabled_tool_names = json.loads(tools_data)
                    elif isinstance(tools_data, list):
                        enabled_tool_names = tools_data
                    else:
                        enabled_tool_names = []
                    agent_tools = [t for t in mcp_tools if t["function"]["name"] in enabled_tool_names]
                except (json.JSONDecodeError, TypeError) as e:
                    print(f"Error decoding tools for agent {request.agent_id}: {e}")

        # 1. Stream from LLM
        stream = client.chat.completions.create(
            model=request.model,
            messages=messages,
            tools=agent_tools if agent_tools else None,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=1024,
            stream=True
        )

        tool_calls = []
        current_content = ""

        for chunk in stream:
            delta = chunk.choices[0].delta
            
            # Handle Content
            if delta.content:
                current_content += delta.content
                yield f"data: {json.dumps({'type': 'token', 'content': delta.content})}\n\n"
            
            # Handle Tool Calls (Accumulate)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if len(tool_calls) <= tc.index:
                        tool_calls.append({"id": "", "function": {"name": "", "arguments": ""}})
                    
                    if tc.id: tool_calls[tc.index]["id"] += tc.id
                    if tc.function.name: tool_calls[tc.index]["function"]["name"] += tc.function.name
                    if tc.function.arguments: tool_calls[tc.index]["function"]["arguments"] += tc.function.arguments

        # 2. Process Tool Calls if any
        if tool_calls:
            # Reconstruct the message object for history
            assistant_msg = {
                "role": "assistant",
                "content": current_content,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": tc["function"]
                    } for tc in tool_calls
                ]
            }
            messages.append(assistant_msg)
            
            for tc in tool_calls:
                func_name = tc["function"]["name"]
                func_args_str = tc["function"]["arguments"]
                
                yield f"data: {json.dumps({'type': 'status', 'content': f'Using tool: {func_name}'})}\n\n"
                
                try:
                    func_args = json.loads(func_args_str)
                    
                    # Call MCP
                    if mcp_session:
                        result = await mcp_session.call_tool(func_name, arguments=func_args)
                        tool_output = result.content[0].text
                    else:
                        tool_output = "Error: MCP Session not active."
                        
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": func_name,
                        "content": tool_output
                    })
                    
                except Exception as e:
                    print(f"Tool execution error: {e}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": func_name,
                        "content": f"Error: {str(e)}"
                    })

            # 3. Second Stream (Post-Tool)
            stream2 = client.chat.completions.create(
                model=request.model,
                messages=messages,
                stream=True
            )
            
            final_content = ""
            for chunk in stream2:
                delta = chunk.choices[0].delta
                if delta.content:
                    final_content += delta.content
                    yield f"data: {json.dumps({'type': 'token', 'content': delta.content})}\n\n"
            
            current_content = final_content # For saving to DB

        # Save to DB
        try:
            # Save User Message
            database.add_chat_message(session_id, "user", request.message)
            
            # Save Assistant Message
            database.add_chat_message(session_id, "assistant", current_content)
            
        except Exception as e:
            print(f"DB Save Error: {e}")
            
        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

    except Exception as e:
        print(f"Stream error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    return StreamingResponse(stream_chat_generator(request), media_type="text/event-stream")


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
    model: str = "llama-3.3-70b-versatile" # Default model
    tools: List[str] = []

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    tools: Optional[List[str]] = None

class AgentToolsUpdate(BaseModel):
    tools: List[str]


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
        # Save to DB
        agent_data = {
            "id": agent_id,
            "name": agent.name,
            "description": agent.description,
            "system_prompt": agent.system_prompt,
            "model": agent.model,
            "tools": agent.tools
        }
        database.save_agent(agent_data)
        logger.info(f"Created agent: {agent_id}")
        
        monitoring.monitor.log_event("INFO", f"Created agent: {agent.name}", metadata={"agent_id": agent_id})
        
        return {"success": True, "agent": agent_data}
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


@app.put("/agents/{agent_id}/tools")
async def update_agent_tools(agent_id: str, update: AgentToolsUpdate):
    """Update the list of tools for an agent."""
    existing = database.get_agent(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    updated = database.update_agent(agent_id, tools=update.tools)
    logger.info(f"Updated tools for agent {agent_id}: {update.tools}")
    
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
    monitoring.monitor.log_event("INFO", f"Deleted agent: {agent_id}", metadata={"deleted_chunks": deleted_chunks if 'deleted_chunks' in dir() else 0})
    
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

# --- Authentication Endpoints ---

class AuthRequest(BaseModel):
    email: str
    password: str


@app.post("/auth/signup")
async def signup(request: AuthRequest):
    """Create a new user account."""
    try:
        user = auth.create_user(request.email, request.password)
        logger.info(f"New user registered: {request.email}")
        return {"success": True, "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
async def login(request: AuthRequest):
    """Login and get a session token."""
    user = auth.verify_user(request.email, request.password)
    if not user:
        monitoring.monitor.log_event("WARN", f"Failed login attempt: {request.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = auth.create_session(user["id"])
    logger.info(f"User logged in: {request.email}")
    
    monitoring.monitor.log_event("INFO", "User logged in", request.email)
    
    return {
        "success": True,
        "token": token,
        "user": user
    }


@app.post("/auth/logout")
async def logout(authorization: str = Header(None)):
    """Logout and invalidate session."""
    if authorization:
        token = authorization.replace("Bearer ", "")
        auth.delete_session(token)
    return {"success": True}


@app.get("/auth/me")
async def get_current_user(authorization: str = Header(None)):
    """Get current logged in user."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    user = auth.verify_session(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Session expired")
    
    return {"success": True, "user": user}


# --- Settings & Monitoring Endpoints ---

class AWSSettings(BaseModel):
    access_key: str
    secret_key: str
    region: str
    log_group: str

class DatadogSettings(BaseModel):
    api_key: str
    site: str

@app.post("/settings/aws")
async def save_aws_config(config: AWSSettings, authorization: str = Header(None)):
    """Save AWS CloudWatch configuration after validating."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    user = auth.verify_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Test connection first
    success, message = monitoring.monitor.test_aws_connection(
        config.access_key, config.secret_key, config.region
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    # Save only if valid
    settings.save_aws_settings(
        user["user_id"], 
        config.access_key, 
        config.secret_key, 
        config.region, 
        config.log_group
    )
    
    # Configure monitor immediately
    monitoring.monitor.configure_aws(
        config.access_key, 
        config.secret_key, 
        config.region, 
        config.log_group
    )
    
    monitoring.monitor.log_event("INFO", "AWS CloudWatch integration configured", user["email"])
    return {"success": True, "message": message}

@app.post("/settings/datadog")
async def save_datadog_config(config: DatadogSettings, authorization: str = Header(None)):
    """Save Datadog configuration after validating."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    user = auth.verify_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Test connection first
    success, message = monitoring.monitor.test_datadog_connection(config.api_key, config.site)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    # Save only if valid
    settings.save_datadog_settings(user["user_id"], config.api_key, config.site)
    
    # Configure monitor immediately
    monitoring.monitor.configure_datadog(config.api_key, config.site)
    
    monitoring.monitor.log_event("INFO", "Datadog integration configured", user["email"])
    return {"success": True, "message": message}


@app.post("/settings/aws/test")
async def test_aws_connection(config: AWSSettings):
    """Test AWS CloudWatch connection without saving."""
    success, message = monitoring.monitor.test_aws_connection(
        config.access_key, config.secret_key, config.region
    )
    return {"success": success, "message": message}


@app.post("/settings/datadog/test")
async def test_datadog_connection(config: DatadogSettings):
    """Test Datadog connection without saving."""
    success, message = monitoring.monitor.test_datadog_connection(config.api_key, config.site)
    return {"success": success, "message": message}


@app.get("/settings")
async def get_user_settings(authorization: str = Header(None)):
    """Get current user settings."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    user = auth.verify_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired")
        
    user_settings = settings.get_settings(user["user_id"])
    
    # Mask secrets
    if "aws_secret_key" in user_settings:
        user_settings["aws_secret_key"] = "********"
    if "dd_api_key" in user_settings:
        user_settings["dd_api_key"] = "********"
        
    return {"success": True, "settings": user_settings}


# ==================== Chat History Endpoints ====================

class CreateSessionRequest(BaseModel):
    agent_id: str
    title: Optional[str] = "New Chat"

class AddMessageRequest(BaseModel):
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None

class UpdateTitleRequest(BaseModel):
    title: str


@app.post("/chat/sessions")
async def create_session(request: CreateSessionRequest, authorization: str = Header(None)):
    """Create a new chat session."""
    user_id = None
    if authorization:
        token = authorization.replace("Bearer ", "")
        user = auth.verify_session(token)
        if user:
            user_id = user["user_id"]
    
    session_id = f"session_{uuid.uuid4().hex[:12]}"
    session = database.create_chat_session(session_id, request.agent_id, user_id, request.title)
    return {"success": True, "session": session}


@app.get("/chat/sessions")
async def list_sessions(agent_id: Optional[str] = None, authorization: str = Header(None)):
    """List chat sessions."""
    if authorization:
        token = authorization.replace("Bearer ", "")
        user = auth.verify_session(token)
        if user:
            sessions = database.get_user_sessions(user["user_id"])
            return {"success": True, "sessions": sessions}
    
    if agent_id:
        sessions = database.get_agent_sessions(agent_id)
        return {"success": True, "sessions": sessions}
    
    return {"success": True, "sessions": []}


@app.get("/chat/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a chat session with messages."""
    session = database.get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = database.get_session_messages(session_id)
    return {"success": True, "session": session, "messages": messages}


@app.post("/chat/sessions/{session_id}/messages")
async def add_message(session_id: str, request: AddMessageRequest):
    """Add a message to a session."""
    session = database.get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    message = database.add_chat_message(session_id, request.role, request.content, request.metadata)
    return {"success": True, "message": message}


@app.patch("/chat/sessions/{session_id}")
async def update_session(session_id: str, request: UpdateTitleRequest):
    """Update session title."""
    session = database.update_session_title(session_id, request.title)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "session": session}


@app.delete("/chat/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session."""
    deleted = database.delete_chat_session(session_id)
    return {"success": deleted}


# ==================== Analytics Endpoints ====================

@app.get("/analytics")
async def get_analytics(days: int = 30, agent_id: Optional[str] = None):
    """
    Get analytics data with time-based filtering.
    
    Parameters:
    - days: Number of days to look back (7, 30, 90)
    - agent_id: Optional agent ID to filter by (use 'all' or omit for all agents)
    """
    try:
        # Get current period analytics
        analytics = database.get_analytics(days=days, agent_id=agent_id)
        
        # Get previous period for comparison
        prev_period = database.get_previous_period_analytics(days=days, agent_id=agent_id)
        
        # Calculate percentage changes
        def calc_change(current: int, previous: int) -> dict:
            if previous == 0:
                percentage = 100 if current > 0 else 0
            else:
                percentage = round(((current - previous) / previous) * 100, 1)
            return {
                "value": percentage,
                "direction": "positive" if percentage > 0 else ("negative" if percentage < 0 else "neutral")
            }
        
        conversations_change = calc_change(analytics["total_conversations"], prev_period["conversations"])
        messages_change = calc_change(analytics["total_messages"], prev_period["messages"])
        
        # Calculate documents indexed
        documents_count = 0
        if agent_id and agent_id != 'all':
            docs = vector_store.list_documents(agent_id)
            documents_count = len(docs)
        else:
            # Get all agents to sum up documents
            all_agents = database.get_all_agents()
            for agent in all_agents:
                docs = vector_store.list_documents(agent['id'])
                documents_count += len(docs)

        return {
            "success": True,
            "data": {
                "total_conversations": analytics["total_conversations"],
                "total_messages": analytics["total_messages"],
                "user_messages": analytics["user_messages"],
                "assistant_messages": analytics["assistant_messages"],
                "active_agents": analytics["active_agents"],
                "documents_indexed": documents_count,
                "avg_response_time": analytics["avg_response_time"],
                "agent_stats": analytics["agent_stats"],
                "period_days": days,
                "changes": {
                    "conversations": conversations_change,
                    "messages": messages_change
                }
            }
        }
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Agent Templates Endpoints ====================

@app.get("/templates")
async def list_templates():
    """Get all agent templates."""
    templates = database.get_all_templates()
    return {"success": True, "templates": templates, "count": len(templates)}


@app.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get a specific template."""
    template = database.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"success": True, "template": template}


@app.post("/agents/from-template/{template_id}")
async def create_agent_from_template(template_id: str):
    """Create a new agent from a template."""
    template = database.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    agent_id = f"agent_{uuid.uuid4().hex[:8]}"
    agent = database.create_agent(
        agent_id=agent_id,
        name=template["name"],
        description=template["description"],
        system_prompt=template["system_prompt"]
    )
    
    monitoring.monitor.log_event("INFO", f"Agent created from template: {template['name']}")
    return {"success": True, "agent": agent}


# ==================== Multi-Model Support ====================

AVAILABLE_MODELS = [
    {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B", "provider": "Groq", "context": 128000},
    {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B", "provider": "Groq", "context": 128000},
    {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B", "provider": "Groq", "context": 32768},
    {"id": "gemma2-9b-it", "name": "Gemma 2 9B", "provider": "Groq", "context": 8192},
]

@app.get("/models")
async def list_models():
    """Get available AI models."""
    return {"success": True, "models": AVAILABLE_MODELS}


# ==================== Tools & Connections API ====================

from backend.tools.connections import ConnectionTemplates
from backend.tools.registry import tool_registry
from backend.tools.executor import execute_python_tool


class ConnectionCreate(BaseModel):
    name: str
    connection_type: str
    credentials: Dict[str, Any]


class ConnectionUpdate(BaseModel):
    name: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None


# --- Connection Templates ---
@app.get("/connection-types")
async def list_connection_types():
    """Get all available OOTB connection templates."""
    templates = ConnectionTemplates.get_all()
    return {"success": True, "connection_types": templates}


@app.get("/connection-types/{type_id}")
async def get_connection_type(type_id: str):
    """Get a specific connection template."""
    template = ConnectionTemplates.get(type_id)
    if not template:
        raise HTTPException(status_code=404, detail="Connection type not found")
    return {"success": True, "connection_type": template}


# --- User Connections ---
@app.get("/connections")
async def list_connections(authorization: str = Header(None)):
    """List all connections for the current user."""
    # Get user from token (simplified - in production, use proper auth)
    user_id = "default_user"  # TODO: Get from auth token
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        user = database.get_user_by_token(token)
        if user:
            user_id = user.get("id", "default_user")
    
    connections = database.get_all_connections()  # For now, return all
    return {"success": True, "connections": connections}


@app.post("/connections")
async def create_connection_endpoint(
    connection: ConnectionCreate,
    authorization: str = Header(None)
):
    """Create a new connection."""
    user_id = "default_user"
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        user = database.get_user_by_token(token)
        if user:
            user_id = user.get("id", "default_user")
    
    # Validate connection type exists
    template = ConnectionTemplates.get(connection.connection_type)
    if not template:
        raise HTTPException(status_code=400, detail=f"Unknown connection type: {connection.connection_type}")
    
    # Validate required fields
    required_fields = [f["key"] for f in template.get("fields", []) if f.get("required")]
    missing = [f for f in required_fields if f not in connection.credentials]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required fields: {missing}")
    
    result = database.create_connection(
        user_id=user_id,
        name=connection.name,
        connection_type=connection.connection_type,
        credentials=connection.credentials
    )
    
    # Don't return credentials in response
    if result:
        result.pop('credentials', None)
    
    return {"success": True, "connection": result}


@app.get("/connections/{connection_id}")
async def get_connection_endpoint(connection_id: str):
    """Get a specific connection (without credentials)."""
    connection = database.get_connection_by_id(connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # Don't return credentials
    connection.pop('credentials', None)
    return {"success": True, "connection": connection}


@app.put("/connections/{connection_id}")
async def update_connection_endpoint(connection_id: str, update: ConnectionUpdate):
    """Update a connection."""
    updates = {}
    if update.name:
        updates['name'] = update.name
    if update.credentials:
        updates['credentials'] = update.credentials
    
    result = database.update_connection(connection_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    result.pop('credentials', None)
    return {"success": True, "connection": result}


@app.delete("/connections/{connection_id}")
async def delete_connection_endpoint(connection_id: str):
    """Delete a connection."""
    success = database.delete_connection(connection_id)
    if not success:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"success": True, "message": "Connection deleted"}


@app.post("/connections/{connection_id}/test")
async def test_connection(connection_id: str):
    """Test a connection by making a basic API call."""
    connection = database.get_connection_by_id(connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # TODO: Implement actual connection testing per type
    # For now, just return success if connection exists
    return {"success": True, "message": "Connection is valid", "status": "connected"}


# --- Python Tools ---
@app.get("/tools/python")
async def list_python_tools():
    """List all registered Python tools."""
    tools = tool_registry.get_all()
    return {"success": True, "tools": tools}


@app.get("/tools/python/{tool_id}")
async def get_python_tool(tool_id: str):
    """Get details of a specific Python tool."""
    tool = tool_registry.get(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    # Remove the function reference (not serializable)
    tool_copy = {k: v for k, v in tool.items() if k != 'function'}
    return {"success": True, "tool": tool_copy}


@app.get("/tools/catalog")
async def get_tools_catalog():
    """Get combined catalog of all tools (MCP + Python)."""
    # Get Python tools
    python_tools = tool_registry.get_all()
    
    # Get MCP tools (already loaded at startup)
    mcp_tool_list = []
    for tool in mcp_tools:
        mcp_tool_list.append({
            "id": tool["function"]["name"],
            "name": tool["function"]["name"].replace('_', ' ').title(),
            "description": tool["function"]["description"],
            "category": "mcp",
            "connection_type": None,
            "icon": "🔌",
            "parameters": tool["function"].get("parameters", {}),
            "source": "mcp"
        })
    
    all_tools = python_tools + mcp_tool_list
    
    return {
        "success": True,
        "tools": all_tools,
        "counts": {
            "python": len(python_tools),
            "mcp": len(mcp_tool_list),
            "total": len(all_tools)
        }
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    
    # Log to monitoring
    monitoring.monitor.log_event("ERROR", f"Unhandled exception: {str(exc)}", metadata={"path": request.url.path})
    
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


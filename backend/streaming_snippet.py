
async def stream_chat_generator(request: ChatRequest):
    """Generator for streaming chat responses."""
    if not GROQ_API_KEY:
        yield f"data: {json.dumps({'type': 'error', 'content': 'GROQ_API_KEY not found'})}\n\n"
        return

    # --- RAG: Retrieve relevant context ---
    rag_context = ""
    sources = []
    
    if request.use_rag:
        try:
            yield f"data: {json.dumps({'type': 'status', 'content': 'Searching knowledge base...'})}\n\n"
            results = vector_store.search(request.agent_id, request.message, top_k=5)
            if results:
                context_parts = []
                for r in results:
                    context_parts.append(r["text"])
                    sources.append({
                        "document_id": r["document_id"],
                        "score": round(r["score"], 3),
                        "metadata": r["metadata"]
                    })
                rag_context = "\n\n".join(context_parts)
                yield f"data: {json.dumps({'type': 'sources', 'content': sources})}\n\n"
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
        # 1. Stream from LLM
        stream = client.chat.completions.create(
            model=request.model,
            messages=messages,
            tools=mcp_tools if mcp_tools else None,
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
        session_id = request.session_id
        if session_id:
            database.add_chat_message(session_id, "user", request.message)
            database.add_chat_message(session_id, "assistant", current_content)
            
        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

    except Exception as e:
        print(f"Stream error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    return StreamingResponse(stream_chat_generator(request), media_type="text/event-stream")

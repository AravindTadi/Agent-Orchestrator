from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional
import uuid
import logging

# ... existing imports ...

# Add this class near other Pydantic models
class AgentToolsUpdate(BaseModel):
    tools: List[str]

# ... inside the app ...

@app.put("/agents/{agent_id}/tools")
async def update_agent_tools(agent_id: str, update: AgentToolsUpdate):
    """Update the list of tools for an agent."""
    existing = database.get_agent(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update tools in database
    # Assuming database.update_agent supports arbitrary kwargs or we need to add 'tools' support
    updated = database.update_agent(agent_id, tools=update.tools)
    logger.info(f"Updated tools for agent {agent_id}: {update.tools}")
    
    return {"success": True, "agent": updated}

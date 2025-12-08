"""
Database module for persistent storage.
Uses SQLite for agent configurations.
"""
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

from backend.config import DATA_DIR

DATABASE_PATH = DATA_DIR / "agents.db"


def get_connection():
    """Get database connection."""
    return sqlite3.connect(DATABASE_PATH, check_same_thread=False)


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database tables."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Agents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                system_prompt TEXT,
                model TEXT DEFAULT 'llama-3.3-70b-versatile',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # API Keys table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                key TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Chat Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                user_id TEXT,
                title TEXT DEFAULT 'New Chat',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            )
        """)
        
        # Chat Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
            )
        """)
        
        # Agent Templates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                system_prompt TEXT,
                category TEXT,
                icon TEXT
            )
        """)
        
        # Insert default agent if none exist
        cursor.execute("SELECT COUNT(*) FROM agents")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO agents (id, name, description, system_prompt)
                VALUES (?, ?, ?, ?)
            """, (
                "agent_default",
                "My First Agent",
                "A helpful AI assistant ready to be configured.",
                "You are a helpful AI assistant."
            ))
        
        # Insert agent templates if none exist
        cursor.execute("SELECT COUNT(*) FROM agent_templates")
        if cursor.fetchone()[0] == 0:
            templates = [
                ("tpl_coding", "Code Assistant", "Expert programmer that helps with coding tasks", 
                 "You are an expert software engineer. Help users write clean, efficient code. Explain your reasoning and suggest best practices.", "Development", "💻"),
                ("tpl_writer", "Creative Writer", "Helps with writing, editing, and content creation",
                 "You are a creative writing assistant. Help users craft compelling stories, articles, and content. Focus on clarity, engagement, and style.", "Content", "✍️"),
                ("tpl_analyst", "Data Analyst", "Analyzes data and provides insights",
                 "You are a data analyst expert. Help users understand data, create visualizations, and derive actionable insights. Be precise and thorough.", "Analytics", "📊"),
                ("tpl_support", "Customer Support", "Friendly customer service agent",
                 "You are a friendly and helpful customer support agent. Resolve issues efficiently, maintain a positive tone, and ensure customer satisfaction.", "Support", "🎧"),
                ("tpl_researcher", "Research Assistant", "Helps with research and information gathering",
                 "You are a research assistant. Help users find, synthesize, and summarize information. Cite sources when possible and be thorough.", "Research", "🔍"),
                ("tpl_aws", "AWS Expert", "Amazon Web Services specialist",
                 "You are an AWS cloud computing expert. Help users with AWS services, architecture decisions, cost optimization, and best practices. You have access to S3 bucket management tools.", "Cloud", "☁️"),
            ]
            cursor.executemany("""
                INSERT INTO agent_templates (id, name, description, system_prompt, category, icon)
                VALUES (?, ?, ?, ?, ?, ?)
            """, templates)
        
        print("✅ Database initialized!")


# --- Agent CRUD Operations ---

def create_agent(agent_id: str, name: str, description: str = "", system_prompt: str = "", model: str = "llama-3.3-70b-versatile") -> Dict:
    """Create a new agent."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO agents (id, name, description, system_prompt, model)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_id, name, description, system_prompt, model))
        
    return get_agent(agent_id)


def save_agent(agent_data: Dict[str, Any]) -> Dict:
    """Save (Upsert) an agent."""
    agent_id = agent_data.get("id")
    name = agent_data.get("name")
    description = agent_data.get("description", "")
    system_prompt = agent_data.get("system_prompt", "")
    model = agent_data.get("model", "llama-3.3-70b-versatile")
    
    with get_db() as conn:
        cursor = conn.cursor()
        # Check if exists
        cursor.execute("SELECT id FROM agents WHERE id = ?", (agent_id,))
        if cursor.fetchone():
            cursor.execute("""
                UPDATE agents 
                SET name = ?, description = ?, system_prompt = ?, model = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (name, description, system_prompt, model, agent_id))
        else:
            cursor.execute("""
                INSERT INTO agents (id, name, description, system_prompt, model)
                VALUES (?, ?, ?, ?, ?)
            """, (agent_id, name, description, system_prompt, model))
            
    return get_agent(agent_id)


def get_agent(agent_id: str) -> Optional[Dict]:
    """Get an agent by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None


def get_all_agents() -> List[Dict]:
    """Get all agents."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agents ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]


def update_agent(agent_id: str, **kwargs) -> Optional[Dict]:
    """Update an agent."""
    allowed_fields = ['name', 'description', 'system_prompt', 'model']
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not updates:
        return get_agent(agent_id)
    
    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [agent_id]
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            UPDATE agents 
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, values)
    
    return get_agent(agent_id)


def delete_agent(agent_id: str) -> bool:
    """Delete an agent."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
        return cursor.rowcount > 0


# --- API Key Operations ---

def create_api_key(key: str, name: str) -> Dict:
    """Create a new API key."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO api_keys (key, name)
            VALUES (?, ?)
        """, (key, name))
    
    return {"key": key, "name": name}


def validate_api_key(key: str) -> bool:
    """Check if an API key is valid."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT key FROM api_keys 
            WHERE key = ? AND is_active = 1
        """, (key,))
        return cursor.fetchone() is not None


def list_api_keys() -> List[Dict]:
    """List all API keys (without exposing full key)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, created_at, is_active FROM api_keys")
        return [dict(row) for row in cursor.fetchall()]


# --- Chat Session Operations ---

def create_chat_session(session_id: str, agent_id: str, user_id: str = None, title: str = "New Chat") -> Dict:
    """Create a new chat session."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_sessions (id, agent_id, user_id, title)
            VALUES (?, ?, ?, ?)
        """, (session_id, agent_id, user_id, title))
    
    return get_chat_session(session_id)


def get_chat_session(session_id: str) -> Optional[Dict]:
    """Get a chat session by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_agent_sessions(agent_id: str, limit: int = 50) -> List[Dict]:
    """Get all chat sessions for an agent."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM chat_sessions 
            WHERE agent_id = ? 
            ORDER BY updated_at DESC
            LIMIT ?
        """, (agent_id, limit))
        return [dict(row) for row in cursor.fetchall()]


def get_user_sessions(user_id: str, limit: int = 50) -> List[Dict]:
    """Get all chat sessions for a user."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cs.*, a.name as agent_name
            FROM chat_sessions cs
            LEFT JOIN agents a ON cs.agent_id = a.id
            WHERE cs.user_id = ? 
            ORDER BY cs.updated_at DESC
            LIMIT ?
        """, (user_id, limit))
        return [dict(row) for row in cursor.fetchall()]


def update_session_title(session_id: str, title: str) -> Optional[Dict]:
    """Update chat session title."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE chat_sessions 
            SET title = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (title, session_id))
    return get_chat_session(session_id)


def delete_chat_session(session_id: str) -> bool:
    """Delete a chat session and its messages."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        return cursor.rowcount > 0


# --- Chat Message Operations ---

def add_chat_message(session_id: str, role: str, content: str, metadata: dict = None) -> Dict:
    """Add a message to a chat session."""
    import json
    metadata_json = json.dumps(metadata) if metadata else None
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_messages (session_id, role, content, metadata)
            VALUES (?, ?, ?, ?)
        """, (session_id, role, content, metadata_json))
        
        # Update session timestamp
        cursor.execute("""
            UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
        """, (session_id,))
        
        return {"id": cursor.lastrowid, "session_id": session_id, "role": role, "content": content}


def get_session_messages(session_id: str, limit: int = 100) -> List[Dict]:
    """Get all messages in a chat session."""
    import json
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM chat_messages 
            WHERE session_id = ? 
            ORDER BY created_at ASC
            LIMIT ?
        """, (session_id, limit))
        
        messages = []
        for row in cursor.fetchall():
            msg = dict(row)
            if msg.get('metadata'):
                msg['metadata'] = json.loads(msg['metadata'])
            messages.append(msg)
        return messages


# --- Agent Template Operations ---

def get_all_templates() -> List[Dict]:
    """Get all agent templates."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agent_templates ORDER BY category, name")
        return [dict(row) for row in cursor.fetchall()]


def get_template(template_id: str) -> Optional[Dict]:
    """Get a template by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agent_templates WHERE id = ?", (template_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


if __name__ == "__main__":
    # Test the database
    init_db()
    
    print("\n📋 All agents:")
    for agent in get_all_agents():
        print(f"  - {agent['name']} ({agent['id']})")
    
    print("\n📦 Agent templates:")
    for tpl in get_all_templates():
        print(f"  - {tpl['icon']} {tpl['name']}")


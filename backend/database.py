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
        
        print("✅ Database initialized!")


# --- Agent CRUD Operations ---

def create_agent(agent_id: str, name: str, description: str = "", system_prompt: str = "") -> Dict:
    """Create a new agent."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO agents (id, name, description, system_prompt)
            VALUES (?, ?, ?, ?)
        """, (agent_id, name, description, system_prompt))
        
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


if __name__ == "__main__":
    # Test the database
    init_db()
    
    print("\n📋 All agents:")
    for agent in get_all_agents():
        print(f"  - {agent['name']} ({agent['id']})")

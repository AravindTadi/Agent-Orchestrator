"""
Database module for persistent storage.
Uses SQLite for agent configurations.
"""
import sqlite3
import json
from datetime import datetime
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
                tools TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Check if tools column exists (migration)
        try:
            cursor.execute("SELECT tools FROM agents LIMIT 1")
        except sqlite3.OperationalError:
            print("⚠️ Migrating database: Adding tools column to agents table...")
            cursor.execute("ALTER TABLE agents ADD COLUMN tools TEXT DEFAULT '[]'")

        # API Keys table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                key TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Connections table (for tool credentials)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connections (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                name TEXT NOT NULL,
                connection_type TEXT NOT NULL,
                credentials TEXT,
                status TEXT DEFAULT 'active',
                last_used TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tool-Connection mapping
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_connections (
                tool_id TEXT NOT NULL,
                connection_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (tool_id, connection_id),
                FOREIGN KEY (connection_id) REFERENCES connections(id) ON DELETE CASCADE
            )
        """)
        
        # ... (rest of init_db) ...

# ...

def create_agent(agent_id: str, name: str, description: str = "", system_prompt: str = "", model: str = "llama-3.3-70b-versatile", tools: List[str] = None) -> Dict:
    """Create a new agent."""
    if tools is None:
        tools = []
    
    tools_json = json.dumps(tools)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO agents (id, name, description, system_prompt, model, tools)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (agent_id, name, description, system_prompt, model, tools_json))
        
    return get_agent(agent_id)


def save_agent(agent_data: Dict[str, Any]) -> Dict:
    """Save (Upsert) an agent."""
    agent_id = agent_data.get("id")
    name = agent_data.get("name")
    description = agent_data.get("description", "")
    system_prompt = agent_data.get("system_prompt", "")
    model = agent_data.get("model", "llama-3.3-70b-versatile")
    tools = agent_data.get("tools", [])
    
    tools_json = json.dumps(tools)
    
    with get_db() as conn:
        cursor = conn.cursor()
        # Check if exists
        cursor.execute("SELECT id FROM agents WHERE id = ?", (agent_id,))
        if cursor.fetchone():
            cursor.execute("""
                UPDATE agents 
                SET name = ?, description = ?, system_prompt = ?, model = ?, tools = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (name, description, system_prompt, model, tools_json, agent_id))
        else:
            cursor.execute("""
                INSERT INTO agents (id, name, description, system_prompt, model, tools)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (agent_id, name, description, system_prompt, model, tools_json))
            
    return get_agent(agent_id)


def get_agent(agent_id: str) -> Optional[Dict]:
    """Get an agent by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
        row = cursor.fetchone()
        
        if row:
            agent = dict(row)
            if agent.get('tools'):
                try:
                    agent['tools'] = json.loads(agent['tools'])
                except:
                    agent['tools'] = []
            else:
                agent['tools'] = []
            return agent
        return None


def get_all_agents() -> List[Dict]:
    """Get all agents."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agents ORDER BY created_at DESC")
        agents = []
        for row in cursor.fetchall():
            agent = dict(row)
            if agent.get('tools'):
                try:
                    agent['tools'] = json.loads(agent['tools'])
                except:
                    agent['tools'] = []
            else:
                agent['tools'] = []
            agents.append(agent)
        return agents


def update_agent(agent_id: str, **kwargs) -> Optional[Dict]:
    """Update an agent."""
    allowed_fields = ['name', 'description', 'system_prompt', 'model', 'tools']
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not updates:
        return get_agent(agent_id)
    
    # Handle tools serialization
    if 'tools' in updates:
        updates['tools'] = json.dumps(updates['tools'])
    
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


# ==================== Analytics Functions ====================

def get_analytics(days: int = 30, agent_id: Optional[str] = None) -> Dict[str, Any]:
    """Get analytics data with time-based filtering."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Build date filter
        date_filter = f"datetime('now', '-{days} days')"
        
        # Base conditions
        session_conditions = f"created_at >= {date_filter}"
        message_conditions = f"created_at >= {date_filter}"
        
        if agent_id and agent_id != 'all':
            session_conditions += f" AND agent_id = '{agent_id}'"
        
        # Total conversations
        cursor.execute(f"""
            SELECT COUNT(*) as count FROM chat_sessions 
            WHERE {session_conditions}
        """)
        total_conversations = cursor.fetchone()['count']
        
        # Total messages
        if agent_id and agent_id != 'all':
            cursor.execute(f"""
                SELECT COUNT(*) as count FROM chat_messages m
                JOIN chat_sessions s ON m.session_id = s.id
                WHERE m.created_at >= {date_filter} AND s.agent_id = ?
            """, (agent_id,))
        else:
            cursor.execute(f"""
                SELECT COUNT(*) as count FROM chat_messages 
                WHERE {message_conditions}
            """)
        total_messages = cursor.fetchone()['count']
        
        # User vs Assistant messages
        if agent_id and agent_id != 'all':
            cursor.execute(f"""
                SELECT 
                    SUM(CASE WHEN m.role = 'user' THEN 1 ELSE 0 END) as user_count,
                    SUM(CASE WHEN m.role = 'assistant' THEN 1 ELSE 0 END) as assistant_count
                FROM chat_messages m
                JOIN chat_sessions s ON m.session_id = s.id
                WHERE m.created_at >= {date_filter} AND s.agent_id = ?
            """, (agent_id,))
        else:
            cursor.execute(f"""
                SELECT 
                    SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) as user_count,
                    SUM(CASE WHEN role = 'assistant' THEN 1 ELSE 0 END) as assistant_count
                FROM chat_messages
                WHERE {message_conditions}
            """)
        msg_breakdown = cursor.fetchone()
        user_messages = msg_breakdown['user_count'] or 0
        assistant_messages = msg_breakdown['assistant_count'] or 0
        
        # Per-agent breakdown
        cursor.execute(f"""
            SELECT 
                s.agent_id,
                a.name as agent_name,
                COUNT(DISTINCT s.id) as conversations,
                COUNT(m.id) as messages
            FROM chat_sessions s
            LEFT JOIN chat_messages m ON s.id = m.session_id
            LEFT JOIN agents a ON s.agent_id = a.id
            WHERE s.created_at >= {date_filter}
            GROUP BY s.agent_id
            ORDER BY messages DESC
        """)
        
        agent_stats = []
        for row in cursor.fetchall():
            agent_stats.append({
                "agent_id": row['agent_id'],
                "agent_name": row['agent_name'] or 'Unknown Agent',
                "conversations": row['conversations'],
                "messages": row['messages']
            })
        
        # Active agents count
        cursor.execute("SELECT COUNT(*) as count FROM agents")
        active_agents = cursor.fetchone()['count']
        
        # Documents count (placeholder, updated in main.py)
        documents_indexed = 0
        
        # Calculate Average Response Time
        cursor.execute(f"""
            SELECT m.session_id, m.role, m.created_at, s.agent_id
            FROM chat_messages m
            JOIN chat_sessions s ON m.session_id = s.id
            WHERE m.created_at >= {date_filter}
            ORDER BY m.session_id, m.created_at
        """)
        
        all_messages = cursor.fetchall()
        
        agent_response_times = {} # agent_id -> [times]
        global_response_times = []
        
        for i in range(len(all_messages) - 1):
            curr = all_messages[i]
            next_msg = all_messages[i+1]
            
            if curr['session_id'] == next_msg['session_id']:
                if curr['role'] == 'user' and next_msg['role'] == 'assistant':
                    try:
                        # Handle potential different datetime formats
                        t1_str = curr['created_at']
                        t2_str = next_msg['created_at']
                        
                        # Simple ISO format check (replace 'T' with space if needed)
                        # Handle Z for UTC
                        t1_str = t1_str.replace('Z', '+00:00')
                        t2_str = t2_str.replace('Z', '+00:00')
                        
                        t1 = datetime.fromisoformat(t1_str)
                        t2 = datetime.fromisoformat(t2_str)
                        
                        diff = (t2 - t1).total_seconds()
                        
                        if 0 < diff < 600: # Filter out > 10 mins
                            global_response_times.append(diff)
                            agent_id_val = curr['agent_id']
                            if agent_id_val not in agent_response_times:
                                agent_response_times[agent_id_val] = []
                            agent_response_times[agent_id_val].append(diff)
                    except Exception:
                        pass
        
        avg_response_time = round(sum(global_response_times) / len(global_response_times), 2) if global_response_times else 0
        
        # Update agent_stats with avg response time
        for stat in agent_stats:
            a_id = stat['agent_id']
            times = agent_response_times.get(a_id, [])
            stat['avg_response_time'] = round(sum(times) / len(times), 2) if times else 0

        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "active_agents": active_agents,
            "documents_indexed": documents_indexed,
            "avg_response_time": avg_response_time,
            "agent_stats": agent_stats,
            "period_days": days
        }


def get_previous_period_analytics(days: int = 30, agent_id: Optional[str] = None) -> Dict[str, int]:
    """Get analytics for the previous period (for comparison)."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Previous period: from 2*days ago to days ago
        start_date = f"datetime('now', '-{days*2} days')"
        end_date = f"datetime('now', '-{days} days')"
        
        session_conditions = f"created_at >= {start_date} AND created_at < {end_date}"
        
        if agent_id and agent_id != 'all':
            session_conditions += f" AND agent_id = '{agent_id}'"
        
        cursor.execute(f"""
            SELECT COUNT(*) as count FROM chat_sessions 
            WHERE {session_conditions}
        """)
        prev_conversations = cursor.fetchone()['count']
        
        if agent_id and agent_id != 'all':
            cursor.execute(f"""
                SELECT COUNT(*) as count FROM chat_messages m
                JOIN chat_sessions s ON m.session_id = s.id
                WHERE m.created_at >= {start_date} AND m.created_at < {end_date}
                AND s.agent_id = ?
            """, (agent_id,))
        else:
            cursor.execute(f"""
                SELECT COUNT(*) as count FROM chat_messages 
                WHERE created_at >= {start_date} AND created_at < {end_date}
            """)
        prev_messages = cursor.fetchone()['count']
        
        return {
            "conversations": prev_conversations,
            "messages": prev_messages
        }


# ==================== Connection Management ====================

def create_connection(
    user_id: str,
    name: str,
    connection_type: str,
    credentials: Dict[str, Any]
) -> Dict:
    """Create a new connection."""
    import secrets
    connection_id = f"conn_{secrets.token_hex(6)}"
    credentials_json = json.dumps(credentials)  # TODO: Encrypt this
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO connections (id, user_id, name, connection_type, credentials)
            VALUES (?, ?, ?, ?, ?)
        """, (connection_id, user_id, name, connection_type, credentials_json))
    
    return get_connection_by_id(connection_id)


def get_connection_by_id(connection_id: str) -> Optional[Dict]:
    """Get a connection by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM connections WHERE id = ?", (connection_id,))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            # Don't return raw credentials in list views - only decrypt when executing
            return result
        return None


def get_user_connections(user_id: str) -> List[Dict]:
    """Get all connections for a user."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, name, connection_type, status, last_used, created_at, updated_at
            FROM connections 
            WHERE user_id = ? AND status = 'active'
            ORDER BY created_at DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_all_connections() -> List[Dict]:
    """Get all connections (admin view)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, name, connection_type, status, last_used, created_at, updated_at
            FROM connections 
            WHERE status = 'active'
            ORDER BY created_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]


def get_user_connection_by_type(user_id: str, connection_type: str) -> Optional[Dict]:
    """Get a user's connection for a specific type."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM connections 
            WHERE user_id = ? AND connection_type = ? AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id, connection_type))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            if result.get('credentials'):
                try:
                    result['credentials'] = json.loads(result['credentials'])
                except:
                    result['credentials'] = {}
            return result
        return None


def get_connection_by_type(connection_type: str) -> Optional[Dict]:
    """Get the first active connection of a specific type (for shared/system connections)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM connections 
            WHERE connection_type = ? AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
        """, (connection_type,))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            if result.get('credentials'):
                try:
                    result['credentials'] = json.loads(result['credentials'])
                except:
                    result['credentials'] = {}
            return result
        return None


def update_connection(connection_id: str, updates: Dict[str, Any]) -> Optional[Dict]:
    """Update a connection."""
    allowed_fields = ['name', 'credentials', 'status']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        for field, value in updates.items():
            if field in allowed_fields:
                if field == 'credentials':
                    value = json.dumps(value)  # TODO: Encrypt
                cursor.execute(f"""
                    UPDATE connections 
                    SET {field} = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (value, connection_id))
    
    return get_connection_by_id(connection_id)


def delete_connection(connection_id: str) -> bool:
    """Delete (soft) a connection."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE connections SET status = 'deleted', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (connection_id,))
        return cursor.rowcount > 0


def update_connection_last_used(connection_id: str):
    """Update the last_used timestamp for a connection."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE connections SET last_used = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (connection_id,))


if __name__ == "__main__":
    # Test the database
    init_db()
    
    print("\n📋 All agents:")
    for agent in get_all_agents():
        print(f"  - {agent['name']} ({agent['id']})")
    
    print("\n📦 Agent templates:")
    for tpl in get_all_templates():
        print(f"  - {tpl['icon']} {tpl['name']}")


"""
Authentication module for user management.
Uses SQLite for user storage with password hashing.
"""

import sqlite3
import hashlib
import secrets
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Database path
AUTH_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'users.db')

def get_connection():
    """Get database connection."""
    os.makedirs(os.path.dirname(AUTH_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(AUTH_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the users database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Auth database initialized!")


def hash_password(password: str, salt: str = None) -> tuple:
    """Hash a password with salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Use SHA-256 with salt
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return password_hash, salt


def create_user(email: str, password: str) -> Dict[str, Any]:
    """Create a new user."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
    if cursor.fetchone():
        conn.close()
        raise ValueError("Email already registered")
    
    # Hash password
    password_hash, salt = hash_password(password)
    
    # Insert user
    cursor.execute('''
        INSERT INTO users (email, password_hash, salt)
        VALUES (?, ?, ?)
    ''', (email, password_hash, salt))
    
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        "id": user_id,
        "email": email,
        "created_at": datetime.now().isoformat()
    }


def verify_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Verify user credentials."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, email, password_hash, salt FROM users WHERE email = ?', (email,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return None
    
    # Verify password
    expected_hash, _ = hash_password(password, row['salt'])
    
    if expected_hash != row['password_hash']:
        conn.close()
        return None
    
    # Update last login
    cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', (datetime.now(), row['id']))
    conn.commit()
    conn.close()
    
    return {
        "id": row['id'],
        "email": row['email']
    }


def create_session(user_id: int) -> str:
    """Create a session token for user."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Generate token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=7)
    
    # Clean old sessions for this user
    cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
    
    # Create new session
    cursor.execute('''
        INSERT INTO sessions (user_id, token, expires_at)
        VALUES (?, ?, ?)
    ''', (user_id, token, expires_at))
    
    conn.commit()
    conn.close()
    
    return token


def verify_session(token: str) -> Optional[Dict[str, Any]]:
    """Verify a session token."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT s.user_id, s.expires_at, u.email
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ?
    ''', (token,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    # Check expiration
    expires_at = datetime.fromisoformat(row['expires_at'])
    if datetime.now() > expires_at:
        return None
    
    return {
        "user_id": row['user_id'],
        "email": row['email']
    }


def delete_session(token: str):
    """Delete a session (logout)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sessions WHERE token = ?', (token,))
    conn.commit()
    conn.close()


# Initialize on import
init_db()

"""
Settings module for managing application configuration and integrations.
Stores API keys and preferences in the database.
"""

import sqlite3
import os
import json
from typing import Dict, Any, Optional

# Reuse the same DB path as auth for simplicity, or separate
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'users.db')

def get_connection():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_settings_table():
    """Initialize settings table."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS integration_settings (
            user_id INTEGER PRIMARY KEY,
            aws_access_key TEXT,
            aws_secret_key TEXT,
            aws_region TEXT,
            aws_log_group TEXT,
            dd_api_key TEXT,
            dd_site TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def save_aws_settings(user_id: int, access_key: str, secret_key: str, region: str, log_group: str):
    """Save AWS CloudWatch settings."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if exists
    cursor.execute('SELECT user_id FROM integration_settings WHERE user_id = ?', (user_id,))
    exists = cursor.fetchone()
    
    if exists:
        cursor.execute('''
            UPDATE integration_settings 
            SET aws_access_key = ?, aws_secret_key = ?, aws_region = ?, aws_log_group = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (access_key, secret_key, region, log_group, user_id))
    else:
        cursor.execute('''
            INSERT INTO integration_settings (user_id, aws_access_key, aws_secret_key, aws_region, aws_log_group)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, access_key, secret_key, region, log_group))
        
    conn.commit()
    conn.close()

def save_datadog_settings(user_id: int, api_key: str, site: str):
    """Save Datadog settings."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id FROM integration_settings WHERE user_id = ?', (user_id,))
    exists = cursor.fetchone()
    
    if exists:
        cursor.execute('''
            UPDATE integration_settings 
            SET dd_api_key = ?, dd_site = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (api_key, site, user_id))
    else:
        cursor.execute('''
            INSERT INTO integration_settings (user_id, dd_api_key, dd_site)
            VALUES (?, ?, ?)
        ''', (user_id, api_key, site))
        
    conn.commit()
    conn.close()

def get_settings(user_id: int) -> Dict[str, Any]:
    """Get all settings for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM integration_settings WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return {}

# Initialize on import
init_settings_table()

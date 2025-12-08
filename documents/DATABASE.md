# AgentHub Database Schema

## Overview

AgentHub uses SQLite for local development and can be configured for PostgreSQL in production (SaaS deployment).

---

## Database Files

| File | Purpose |
|------|---------|
| `data/agents.db` | Agent data, chat sessions, templates |
| `data/users.db` | User accounts, sessions, settings |
| `data/milvus_data.db` | Vector embeddings (Milvus Lite) |

---

## Schema Diagrams

### agents.db

```
┌─────────────────────────────────────────────────────────────────┐
│                           agents                                 │
├─────────────────────────────────────────────────────────────────┤
│ id              TEXT PRIMARY KEY                                │
│ name            TEXT NOT NULL                                   │
│ description     TEXT                                            │
│ system_prompt   TEXT                                            │
│ model           TEXT DEFAULT 'llama-3.3-70b-versatile'         │
│ created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP             │
│ updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP             │
└─────────────────────────────────────────────────────────────────┘
        │
        │ 1:N
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                       chat_sessions                              │
├─────────────────────────────────────────────────────────────────┤
│ id              TEXT PRIMARY KEY                                │
│ agent_id        TEXT NOT NULL (FK → agents.id)                  │
│ user_id         TEXT                                            │
│ title           TEXT DEFAULT 'New Chat'                         │
│ created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP             │
│ updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP             │
└─────────────────────────────────────────────────────────────────┘
        │
        │ 1:N
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                       chat_messages                              │
├─────────────────────────────────────────────────────────────────┤
│ id              INTEGER PRIMARY KEY AUTOINCREMENT               │
│ session_id      TEXT NOT NULL (FK → chat_sessions.id)           │
│ role            TEXT NOT NULL ('user' | 'assistant')            │
│ content         TEXT NOT NULL                                   │
│ metadata        TEXT (JSON)                                     │
│ created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      agent_templates                             │
├─────────────────────────────────────────────────────────────────┤
│ id              TEXT PRIMARY KEY                                │
│ name            TEXT NOT NULL                                   │
│ description     TEXT                                            │
│ system_prompt   TEXT                                            │
│ category        TEXT                                            │
│ icon            TEXT                                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         api_keys                                 │
├─────────────────────────────────────────────────────────────────┤
│ key             TEXT PRIMARY KEY                                │
│ name            TEXT NOT NULL                                   │
│ created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP             │
│ is_active       BOOLEAN DEFAULT 1                               │
└─────────────────────────────────────────────────────────────────┘
```

### users.db

```
┌─────────────────────────────────────────────────────────────────┐
│                           users                                  │
├─────────────────────────────────────────────────────────────────┤
│ id              TEXT PRIMARY KEY                                │
│ email           TEXT UNIQUE NOT NULL                            │
│ password_hash   TEXT NOT NULL                                   │
│ created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP             │
└─────────────────────────────────────────────────────────────────┘
        │
        │ 1:N
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                         sessions                                 │
├─────────────────────────────────────────────────────────────────┤
│ token           TEXT PRIMARY KEY                                │
│ user_id         TEXT NOT NULL (FK → users.id)                   │
│ created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP             │
│ expires_at      TIMESTAMP                                       │
└─────────────────────────────────────────────────────────────────┘
        │
        │ 1:1
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                   integration_settings                           │
├─────────────────────────────────────────────────────────────────┤
│ user_id         TEXT PRIMARY KEY (FK → users.id)                │
│ aws_access_key  TEXT                                            │
│ aws_secret_key  TEXT                                            │
│ aws_region      TEXT                                            │
│ aws_log_group   TEXT                                            │
│ dd_api_key      TEXT                                            │
│ dd_site         TEXT                                            │
│ updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Table Details

### agents

Stores all AI agent configurations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | TEXT | PRIMARY KEY | Unique identifier (e.g., `agent_abc123`) |
| name | TEXT | NOT NULL | Display name |
| description | TEXT | | Short description |
| system_prompt | TEXT | | System instructions for the LLM |
| model | TEXT | DEFAULT | LLM model ID |
| created_at | TIMESTAMP | DEFAULT | Creation timestamp |
| updated_at | TIMESTAMP | DEFAULT | Last update timestamp |

---

### chat_sessions

Stores conversation sessions between users and agents.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | TEXT | PRIMARY KEY | Session ID (e.g., `session_xyz789`) |
| agent_id | TEXT | NOT NULL, FK | Reference to agent |
| user_id | TEXT | | Reference to user (optional for anonymous) |
| title | TEXT | DEFAULT | Session title |
| created_at | TIMESTAMP | DEFAULT | Creation timestamp |
| updated_at | TIMESTAMP | DEFAULT | Last activity timestamp |

---

### chat_messages

Stores individual messages within chat sessions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, AUTO | Message ID |
| session_id | TEXT | NOT NULL, FK | Reference to session |
| role | TEXT | NOT NULL | `user` or `assistant` |
| content | TEXT | NOT NULL | Message content |
| metadata | TEXT | | JSON metadata (sources, tool calls) |
| created_at | TIMESTAMP | DEFAULT | Message timestamp |

---

### agent_templates

Pre-built agent templates for quick agent creation.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | TEXT | PRIMARY KEY | Template ID (e.g., `tpl_coding`) |
| name | TEXT | NOT NULL | Template name |
| description | TEXT | | Short description |
| system_prompt | TEXT | | Pre-configured system prompt |
| category | TEXT | | Category (Development, Content, etc.) |
| icon | TEXT | | Emoji icon |

**Pre-seeded Templates:**

| ID | Name | Category | Icon |
|----|------|----------|------|
| tpl_coding | Code Assistant | Development | 💻 |
| tpl_writer | Creative Writer | Content | ✍️ |
| tpl_analyst | Data Analyst | Analytics | 📊 |
| tpl_support | Customer Support | Support | 🎧 |
| tpl_researcher | Research Assistant | Research | 🔍 |
| tpl_aws | AWS Expert | Cloud | ☁️ |

---

### api_keys

Stores API keys for programmatic access.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| key | TEXT | PRIMARY KEY | API key (e.g., `ah_xxxxx`) |
| name | TEXT | NOT NULL | Key name/label |
| created_at | TIMESTAMP | DEFAULT | Creation timestamp |
| is_active | BOOLEAN | DEFAULT 1 | Whether key is active |

---

### users

User accounts for authentication.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | TEXT | PRIMARY KEY | User ID (e.g., `user_abc123`) |
| email | TEXT | UNIQUE, NOT NULL | User email |
| password_hash | TEXT | NOT NULL | bcrypt hashed password |
| created_at | TIMESTAMP | DEFAULT | Registration timestamp |

---

### sessions

Authentication sessions (tokens).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| token | TEXT | PRIMARY KEY | Session token |
| user_id | TEXT | NOT NULL, FK | Reference to user |
| created_at | TIMESTAMP | DEFAULT | Session start |
| expires_at | TIMESTAMP | | Session expiry |

---

### integration_settings

User-specific external service configurations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| user_id | TEXT | PRIMARY KEY, FK | Reference to user |
| aws_access_key | TEXT | | AWS Access Key ID |
| aws_secret_key | TEXT | | AWS Secret Access Key |
| aws_region | TEXT | | AWS Region |
| aws_log_group | TEXT | | CloudWatch Log Group |
| dd_api_key | TEXT | | Datadog API Key |
| dd_site | TEXT | | Datadog site (e.g., datadoghq.com) |
| updated_at | TIMESTAMP | DEFAULT | Last update |

---

## Vector Database (Milvus Lite)

### Collection: agent_knowledge

Stores document embeddings for RAG.

| Field | Type | Description |
|-------|------|-------------|
| id | INT64 | Auto-generated ID |
| agent_id | VARCHAR(64) | Agent this knowledge belongs to |
| content | VARCHAR(65535) | Text chunk content |
| filename | VARCHAR(256) | Source filename |
| chunk_index | INT64 | Position in document |
| embedding | FLOAT_VECTOR(384) | all-MiniLM-L6-v2 embedding |

**Index:** IVF_FLAT on embedding field

---

## Migrations

### Future Migration to PostgreSQL (SaaS)

```sql
-- Example PostgreSQL schema adjustments
CREATE TABLE agents (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    system_prompt TEXT,
    model VARCHAR(64) DEFAULT 'llama-3.3-70b-versatile',
    tenant_id VARCHAR(64),  -- Multi-tenancy
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add tenant_id to all tables for multi-tenancy
-- Add indexes on frequently queried columns
CREATE INDEX idx_agents_tenant ON agents(tenant_id);
CREATE INDEX idx_sessions_user ON chat_sessions(user_id);
CREATE INDEX idx_messages_session ON chat_messages(session_id);
```

---

## Backup & Recovery

### SQLite Backup
```bash
# Backup all databases
cp data/*.db backup/

# Or use SQLite backup command
sqlite3 data/agents.db ".backup backup/agents.db"
```

### Restore
```bash
cp backup/*.db data/
```

---

*Last Updated: December 7, 2024*

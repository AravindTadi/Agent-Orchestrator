# AgentHub Architecture

## Overview

AgentHub is a full-stack AI agent orchestration platform that enables users to create, configure, and interact with AI agents. The platform integrates with external services for enhanced capabilities.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (HTML/CSS/JS)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  index.html  │  │orchestrator. │  │  chat.html   │  │integrations. │    │
│  │  (Dashboard) │  │    html      │  │  (Chat UI)   │  │    html      │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                              │                                              │
│                         js/script.js                                        │
│                         css/style.css                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP/REST API
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI - Python)                          │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                           main.py (API Router)                       │   │
│  │  /agents  /chat  /knowledge  /auth  /settings  /templates  /models  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  database.py │  │   auth.py    │  │  settings.py │  │ monitoring.py│   │
│  │  (SQLite)    │  │  (Sessions)  │  │(Integrations)│  │(CloudWatch/DD)│  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                          RAG Module                                   │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │  │
│  │  │ vector_store.py │  │document_process.│  │ sentence-transformers│  │  │
│  │  │   (Milvus)      │  │     py          │  │  (Embeddings)       │  │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                          MCP Module                                   │  │
│  │  ┌─────────────────┐  ┌─────────────────┐                            │  │
│  │  │   mcp/server.py │←→│  AWS S3 SDK     │                            │  │
│  │  │  (Tool Server)  │  │  (boto3)        │                            │  │
│  │  └─────────────────┘  └─────────────────┘                            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                    │                           │
                    ▼                           ▼
┌──────────────────────────────┐  ┌──────────────────────────────────────────┐
│        LOCAL STORAGE         │  │           EXTERNAL SERVICES               │
│  ┌────────────────────────┐  │  │  ┌─────────────┐  ┌─────────────────┐   │
│  │  data/agents.db        │  │  │  │   Groq API  │  │  AWS CloudWatch │   │
│  │  (SQLite Database)     │  │  │  │   (LLM)     │  │  (Monitoring)   │   │
│  ├────────────────────────┤  │  │  └─────────────┘  └─────────────────┘   │
│  │  data/users.db         │  │  │  ┌─────────────┐  ┌─────────────────┐   │
│  │  (Auth & Settings)     │  │  │  │  AWS S3     │  │    Datadog      │   │
│  ├────────────────────────┤  │  │  │  (Storage)  │  │  (Monitoring)   │   │
│  │  data/milvus_data.db   │  │  │  └─────────────┘  └─────────────────┘   │
│  │  (Vector Database)     │  │  └──────────────────────────────────────────┘
│  ├────────────────────────┤  │
│  │  data/knowledge/*.pdf  │  │
│  │  (Uploaded Documents)  │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
```

---

## Component Details

### Frontend Layer

| Component | File | Purpose |
|-----------|------|---------|
| Dashboard | `index.html` | Agent cards overview |
| Orchestrator | `orchestrator.html` | Agent configuration & chat |
| Chat | `chat.html` | Standalone chat interface |
| Integrations | `integrations.html` | External service settings |
| Login | `login.html` | Authentication UI |
| Scripts | `js/script.js` | All JavaScript logic |
| Styles | `css/style.css` | All CSS styling |

### Backend Layer

| Module | File | Responsibility |
|--------|------|----------------|
| API Router | `main.py` | FastAPI endpoints, request handling |
| Database | `database.py` | SQLite CRUD operations |
| Auth | `auth.py` | User authentication, sessions |
| Settings | `settings.py` | User preferences, integrations |
| Monitoring | `monitoring.py` | CloudWatch & Datadog logging |
| Config | `config.py` | Environment variables |

### RAG Module

| Component | File | Purpose |
|-----------|------|---------|
| Vector Store | `rag/vector_store.py` | Milvus Lite vector database |
| Document Processor | `rag/document_processor.py` | PDF parsing, chunking |
| Embeddings | sentence-transformers | all-MiniLM-L6-v2 model |

### MCP Module

| Component | File | Purpose |
|-----------|------|---------|
| Tool Server | `mcp/server.py` | MCP protocol implementation |
| AWS Tools | boto3 | S3 bucket operations |

---

## Data Flow

### Chat Message Flow
```
User Input → Frontend → POST /chat → Backend
                                        │
                                        ▼
                              ┌─────────────────┐
                              │ Load Agent Data │
                              │ (System Prompt) │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │ RAG: Semantic   │
                              │ Search Context  │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │ Groq API Call   │
                              │ (LLM Inference) │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │ MCP Tool Call?  │──Yes──→ Execute Tool
                              │                 │              │
                              └────────┬────────┘              │
                                       │                       │
                                       ▼                       ▼
                              Response ← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘
```

### Authentication Flow
```
Login Form → POST /auth/login → Verify Password (bcrypt)
                                        │
                              ┌─────────▼─────────┐
                              │ Create Session    │
                              │ Store in users.db │
                              └─────────┬─────────┘
                                        │
                              ┌─────────▼─────────┐
                              │ Return Token      │
                              │ Store in localStorage│
                              └───────────────────┘
```

---

## Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Frontend | HTML5, CSS3, Vanilla JS | - |
| Backend | FastAPI | 0.104+ |
| Database | SQLite | 3.x |
| Vector DB | Milvus Lite | 2.x |
| Embeddings | sentence-transformers | 2.x |
| LLM | Groq API (Llama 3.3 70B) | - |
| MCP | Model Context Protocol | 1.x |
| Cloud | AWS (S3, CloudWatch) | - |
| Monitoring | Datadog (optional) | - |

---

## Directory Structure

```
Agents/
├── backend/
│   ├── main.py              # FastAPI app & routes
│   ├── database.py          # SQLite operations
│   ├── auth.py              # Authentication
│   ├── settings.py          # User settings
│   ├── monitoring.py        # External monitoring
│   ├── config.py            # Environment config
│   ├── mcp/
│   │   └── server.py        # MCP tool server
│   └── rag/
│       ├── vector_store.py  # Milvus operations
│       └── document_processor.py
├── frontend/
│   ├── index.html           # Dashboard
│   ├── orchestrator.html    # Agent config
│   ├── chat.html            # Chat UI
│   ├── integrations.html    # Settings
│   ├── login.html           # Auth
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── script.js
├── data/
│   ├── agents.db            # Agent data
│   ├── users.db             # Auth & settings
│   ├── milvus_data.db       # Vector store
│   └── knowledge/           # Uploaded files
├── documents/               # Documentation
└── ROADMAP.md              # Product roadmap
```

---

## Deployment Modes

### SaaS (AWS)
- ECS/EKS for container orchestration
- RDS PostgreSQL (instead of SQLite)
- ElastiCache Redis for sessions
- S3 for file storage
- CloudWatch for monitoring

### On-Premises
- Docker Compose deployment
- SQLite or PostgreSQL
- Local file storage
- Optional external monitoring

---

*Last Updated: December 7, 2024*

# AgentHub User Flows

## Overview

This document describes the key user flows and data flows within the AgentHub platform.

---

## User Flows

### 1. User Registration & Login

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           REGISTRATION FLOW                                  │
└─────────────────────────────────────────────────────────────────────────────┘

    User                    Frontend                    Backend
     │                         │                           │
     │  1. Open login.html     │                           │
     │ ────────────────────────>                           │
     │                         │                           │
     │  2. Switch to Signup    │                           │
     │ ────────────────────────>                           │
     │                         │                           │
     │  3. Enter email/password│                           │
     │ ────────────────────────>                           │
     │                         │                           │
     │                         │  4. POST /auth/signup     │
     │                         │ ──────────────────────────>
     │                         │                           │
     │                         │                    5. Validate email
     │                         │                    6. Hash password (bcrypt)
     │                         │                    7. Store in users.db
     │                         │                           │
     │                         │  8. {success: true}       │
     │                         │ <──────────────────────────
     │                         │                           │
     │  9. Show success toast  │                           │
     │ <────────────────────────                           │
     │                         │                           │
     │  10. Switch to login    │                           │
     │ ────────────────────────>                           │


┌─────────────────────────────────────────────────────────────────────────────┐
│                             LOGIN FLOW                                       │
└─────────────────────────────────────────────────────────────────────────────┘

    User                    Frontend                    Backend
     │                         │                           │
     │  1. Enter credentials   │                           │
     │ ────────────────────────>                           │
     │                         │                           │
     │                         │  2. POST /auth/login      │
     │                         │ ──────────────────────────>
     │                         │                           │
     │                         │                    3. Lookup user by email
     │                         │                    4. Verify password hash
     │                         │                    5. Create session token
     │                         │                    6. Store in sessions table
     │                         │                           │
     │                         │  7. {token, email}        │
     │                         │ <──────────────────────────
     │                         │                           │
     │                    8. Store token in localStorage   │
     │                         │                           │
     │  9. Redirect to         │                           │
     │     orchestrator.html   │                           │
     │ <────────────────────────                           │
```

---

### 2. Agent Creation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AGENT CREATION FLOW                                  │
└─────────────────────────────────────────────────────────────────────────────┘

    User                    Frontend                    Backend
     │                         │                           │
     │  1. Click "+ New Agent" │                           │
     │ ────────────────────────>                           │
     │                         │                           │
     │                    2. Open template modal           │
     │                         │                           │
     │                         │  3. GET /templates        │
     │                         │ ──────────────────────────>
     │                         │                           │
     │                         │  4. Return templates      │
     │                         │ <──────────────────────────
     │                         │                           │
     │  5. Display template    │                           │
     │     cards               │                           │
     │ <────────────────────────                           │
     │                         │                           │
     │  6. Select template     │                           │
     │     (or "Blank Agent")  │                           │
     │ ────────────────────────>                           │
     │                         │                           │
     │                         │  7a. POST /agents/from-   │
     │                         │      template/{id}        │
     │                         │  -- OR --                 │
     │                         │  7b. Navigate to          │
     │                         │      orchestrator.html    │
     │                         │      ?mode=create         │
     │                         │ ──────────────────────────>
     │                         │                           │
     │                         │                    8. Create agent in DB
     │                         │                    9. Return agent data
     │                         │ <──────────────────────────
     │                         │                           │
     │  10. Show agent config  │                           │
     │      panel              │                           │
     │ <────────────────────────                           │
```

---

### 3. Chat Conversation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CHAT FLOW                                          │
└─────────────────────────────────────────────────────────────────────────────┘

    User                    Frontend                    Backend                 External
     │                         │                           │                       │
     │  1. Type message        │                           │                       │
     │ ────────────────────────>                           │                       │
     │                         │                           │                       │
     │  2. Press Enter/Send    │                           │                       │
     │ ────────────────────────>                           │                       │
     │                         │                           │                       │
     │                    3. Add user msg to UI            │                       │
     │                    4. Show "typing..."              │                       │
     │                         │                           │                       │
     │                         │  5. POST /chat            │                       │
     │                         │  {agent_id, message,      │                       │
     │                         │   history}                │                       │
     │                         │ ──────────────────────────>                       │
     │                         │                           │                       │
     │                         │                    6. Load agent config          │
     │                         │                    7. Check if MCP              │
     │                         │                       tools enabled              │
     │                         │                           │                       │
     │                         │                    8. RAG: Semantic search       │
     │                         │                       in vector DB               │
     │                         │                           │                       │
     │                         │                    9. Build prompt:              │
     │                         │                       - System prompt            │
     │                         │                       - RAG context              │
     │                         │                       - Tool descriptions        │
     │                         │                       - History                  │
     │                         │                       - User message             │
     │                         │                           │                       │
     │                         │                           │  10. Groq API         │
     │                         │                           │ ─────────────────────>
     │                         │                           │                       │
     │                         │                           │  11. LLM Response     │
     │                         │                           │ <─────────────────────
     │                         │                           │                       │
     │                         │                    12. Check for tool calls      │
     │                         │                           │                       │
     │                         │                    [If tool call detected]       │
     │                         │                           │                       │
     │                         │                           │  13. MCP Tool Call    │
     │                         │                           │ ─────────────────────>
     │                         │                           │        (e.g., S3)     │
     │                         │                           │                       │
     │                         │                           │  14. Tool Result      │
     │                         │                           │ <─────────────────────
     │                         │                           │                       │
     │                         │                    15. Include tool result       │
     │                         │                        in response               │
     │                         │                           │                       │
     │                         │  16. Return response      │                       │
     │                         │ <──────────────────────────                       │
     │                         │                           │                       │
     │                    17. Remove "typing..."           │                       │
     │                    18. Display assistant msg        │                       │
     │                         │                           │                       │
     │  19. See response       │                           │                       │
     │ <────────────────────────                           │                       │
```

---

### 4. Document Upload (RAG)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DOCUMENT UPLOAD FLOW                                 │
└─────────────────────────────────────────────────────────────────────────────┘

    User                    Frontend                    Backend
     │                         │                           │
     │  1. Click "Upload       │                           │
     │     Knowledge"          │                           │
     │ ────────────────────────>                           │
     │                         │                           │
     │  2. Select PDF file     │                           │
     │ ────────────────────────>                           │
     │                         │                           │
     │                         │  3. POST /knowledge/upload│
     │                         │  (multipart/form-data)    │
     │                         │ ──────────────────────────>
     │                         │                           │
     │                         │                    4. Save file to disk
     │                         │                    5. Extract text (PyPDF)
     │                         │                    6. Split into chunks
     │                         │                    7. Generate embeddings
     │                         │                    8. Store in Milvus
     │                         │                           │
     │                         │  9. {chunks: 15}          │
     │                         │ <──────────────────────────
     │                         │                           │
     │  10. Show success       │                           │
     │      "15 chunks indexed"│                           │
     │ <────────────────────────                           │
```

---

### 5. Integration Setup (CloudWatch/Datadog)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      INTEGRATION SETUP FLOW                                  │
└─────────────────────────────────────────────────────────────────────────────┘

    User                    Frontend                    Backend                 AWS/Datadog
     │                         │                           │                       │
     │  1. Open Integrations   │                           │                       │
     │     page                │                           │                       │
     │ ────────────────────────>                           │                       │
     │                         │                           │                       │
     │  2. Enter AWS creds     │                           │                       │
     │ ────────────────────────>                           │                       │
     │                         │                           │                       │
     │  3. Click "Connect"     │                           │                       │
     │ ────────────────────────>                           │                       │
     │                         │                           │                       │
     │                         │  4. POST /settings/aws    │                       │
     │                         │ ──────────────────────────>                       │
     │                         │                           │                       │
     │                         │                           │  5. describe_log_     │
     │                         │                           │     groups (validate) │
     │                         │                           │ ─────────────────────>
     │                         │                           │                       │
     │                         │                           │  6. Success/Error     │
     │                         │                           │ <─────────────────────
     │                         │                           │                       │
     │                         │                    [If valid]                     │
     │                         │                    7. Store in settings DB        │
     │                         │                    8. Configure monitor           │
     │                         │                           │                       │
     │                         │  9. {success, message}    │                       │
     │                         │ <──────────────────────────                       │
     │                         │                           │                       │
     │  10. Show "Connected"   │                           │                       │
     │      status badge       │                           │                       │
     │ <────────────────────────                           │                       │
```

---

## Data Flows

### Request Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         REQUEST LIFECYCLE                                    │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │   HTTP Request   │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   CORS Check     │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Auth Middleware  │──── Verify Bearer token
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Route Handler   │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ Database │  │ External │  │ Vector   │
        │  Query   │  │   API    │  │  Search  │
        └────┬─────┘  └────┬─────┘  └────┬─────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │    Response      │
                    │   Serialization  │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   Monitoring     │──── Log to CloudWatch/Datadog
                    │   (if enabled)   │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  HTTP Response   │
                    └──────────────────┘
```

---

### RAG Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RAG PIPELINE                                       │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │  PDF Document    │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Text Extraction │  (PyPDF)
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │    Chunking      │  (512 chars, 50 overlap)
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Embedding Model  │  (all-MiniLM-L6-v2)
                    │   384 dims       │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Vector Storage  │  (Milvus Lite)
                    └──────────────────┘


                         QUERY TIME
                    
                    ┌──────────────────┐
                    │    User Query    │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Query Embedding │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Similarity      │  (Cosine similarity, top_k=3)
                    │    Search        │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Relevant Chunks  │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Add to Prompt   │
                    │  as Context      │
                    └──────────────────┘
```

---

### MCP Tool Execution

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MCP TOOL EXECUTION                                    │
└─────────────────────────────────────────────────────────────────────────────┘

    Backend                 MCP Server              AWS SDK
       │                         │                     │
       │  1. Start subprocess    │                     │
       │ ────────────────────────>                     │
       │                         │                     │
       │  2. Initialize session  │                     │
       │ ────────────────────────>                     │
       │                         │                     │
       │  3. List tools          │                     │
       │ ────────────────────────>                     │
       │                         │                     │
       │  4. Return tool list    │                     │
       │ <────────────────────────                     │
       │                         │                     │
       │  Include tools in       │                     │
       │  LLM prompt             │                     │
       │                         │                     │
       │  ... LLM decides to     │                     │
       │  call a tool ...        │                     │
       │                         │                     │
       │  5. call_tool(name,     │                     │
       │     arguments)          │                     │
       │ ────────────────────────>                     │
       │                         │                     │
       │                         │  6. boto3 call      │
       │                         │ ───────────────────>
       │                         │                     │
       │                         │  7. AWS Response    │
       │                         │ <───────────────────
       │                         │                     │
       │  8. Tool result         │                     │
       │ <────────────────────────                     │
       │                         │                     │
       │  Include result in      │                     │
       │  final response         │                     │
```

---

## State Management

### Frontend State (JavaScript)

```javascript
// Global state in script.js
let agents = {};              // Agent ID → Agent data
let currentAgentId = null;    // Currently selected agent
let chatHistory = [];         // Current chat messages

// LocalStorage
localStorage.auth_token       // Session token
localStorage.theme            // 'light' | 'dark'
localStorage.selected_region  // AWS region
localStorage.agenthub_api_key // User's API key
```

### Backend State (Python)

```python
# Global state in main.py
mcp_session: ClientSession    # MCP connection
mcp_tools: List[Dict]         # Available tools

# Global state in monitoring.py
monitor = MonitoringService() # Singleton
```

---

*Last Updated: December 7, 2024*

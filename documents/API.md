# AgentHub API Reference

## Base URL
```
http://localhost:8000
```

## Authentication
Most endpoints require a Bearer token in the `Authorization` header:
```
Authorization: Bearer <session_token>
```

---

## Endpoints

### 🔐 Authentication

#### POST /auth/signup
Create a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "User created successfully"
}
```

---

#### POST /auth/login
Authenticate and get a session token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "success": true,
  "token": "sess_abc123...",
  "email": "user@example.com"
}
```

---

#### POST /auth/logout
End the current session.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

#### GET /auth/me
Get current user info.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "user_id": "user_abc123",
  "email": "user@example.com"
}
```

---

### 🤖 Agents

#### GET /agents
List all agents.

**Response:**
```json
{
  "agents": [
    {
      "id": "agent_abc123",
      "name": "My Agent",
      "description": "A helpful assistant",
      "system_prompt": "You are a helpful AI...",
      "model": "llama-3.3-70b-versatile",
      "created_at": "2024-12-07T12:00:00",
      "updated_at": "2024-12-07T12:00:00"
    }
  ],
  "count": 1
}
```

---

#### GET /agents/{agent_id}
Get a specific agent.

**Response:**
```json
{
  "id": "agent_abc123",
  "name": "My Agent",
  "description": "A helpful assistant",
  "system_prompt": "You are a helpful AI...",
  "model": "llama-3.3-70b-versatile"
}
```

---

#### POST /agents
Create a new agent.

**Request Body:**
```json
{
  "id": "agent_newid",
  "name": "New Agent",
  "description": "Description here",
  "system_prompt": "You are a...",
  "model": "llama-3.3-70b-versatile"
}
```

**Response:**
```json
{
  "success": true,
  "agent": { ... }
}
```

---

#### PUT /agents/{agent_id}
Update an agent.

**Request Body:**
```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "system_prompt": "Updated prompt...",
  "model": "mixtral-8x7b-32768"
}
```

**Response:**
```json
{
  "success": true,
  "agent": { ... }
}
```

---

#### DELETE /agents/{agent_id}
Delete an agent.

**Response:**
```json
{
  "success": true
}
```

---

### 💬 Chat

#### POST /chat
Send a message to an agent and get a response.

**Request Body:**
```json
{
  "agent_id": "agent_abc123",
  "message": "Hello, how are you?",
  "history": [
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello! How can I help?"}
  ]
}
```

**Response:**
```json
{
  "response": "I'm doing well, thank you for asking!",
  "tool_calls": [],
  "sources": []
}
```

---

### 📝 Chat Sessions

#### POST /chat/sessions
Create a new chat session.

**Request Body:**
```json
{
  "agent_id": "agent_abc123",
  "title": "My Chat Session"
}
```

**Response:**
```json
{
  "success": true,
  "session": {
    "id": "session_xyz789",
    "agent_id": "agent_abc123",
    "user_id": "user_abc123",
    "title": "My Chat Session",
    "created_at": "2024-12-07T12:00:00",
    "updated_at": "2024-12-07T12:00:00"
  }
}
```

---

#### GET /chat/sessions
List chat sessions.

**Query Parameters:**
- `agent_id` (optional): Filter by agent

**Headers:** `Authorization: Bearer <token>` (returns user's sessions)

**Response:**
```json
{
  "success": true,
  "sessions": [
    {
      "id": "session_xyz789",
      "agent_id": "agent_abc123",
      "title": "My Chat Session",
      "updated_at": "2024-12-07T12:00:00"
    }
  ]
}
```

---

#### GET /chat/sessions/{session_id}
Get a session with all messages.

**Response:**
```json
{
  "success": true,
  "session": {
    "id": "session_xyz789",
    "agent_id": "agent_abc123",
    "title": "My Chat Session"
  },
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "Hello",
      "created_at": "2024-12-07T12:00:00"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "Hi there!",
      "created_at": "2024-12-07T12:00:01"
    }
  ]
}
```

---

#### POST /chat/sessions/{session_id}/messages
Add a message to a session.

**Request Body:**
```json
{
  "role": "user",
  "content": "What's the weather?",
  "metadata": {"source": "web"}
}
```

**Response:**
```json
{
  "success": true,
  "message": {
    "id": 3,
    "session_id": "session_xyz789",
    "role": "user",
    "content": "What's the weather?"
  }
}
```

---

#### PATCH /chat/sessions/{session_id}
Update session title.

**Request Body:**
```json
{
  "title": "New Title"
}
```

**Response:**
```json
{
  "success": true,
  "session": { ... }
}
```

---

#### DELETE /chat/sessions/{session_id}
Delete a session and all its messages.

**Response:**
```json
{
  "success": true
}
```

---

### 📦 Agent Templates

#### GET /templates
List all agent templates.

**Response:**
```json
{
  "success": true,
  "templates": [
    {
      "id": "tpl_coding",
      "name": "Code Assistant",
      "description": "Expert programmer that helps with coding tasks",
      "system_prompt": "You are an expert software engineer...",
      "category": "Development",
      "icon": "💻"
    }
  ],
  "count": 6
}
```

---

#### GET /templates/{template_id}
Get a specific template.

**Response:**
```json
{
  "success": true,
  "template": {
    "id": "tpl_coding",
    "name": "Code Assistant",
    "description": "Expert programmer...",
    "system_prompt": "You are an expert...",
    "category": "Development",
    "icon": "💻"
  }
}
```

---

#### POST /agents/from-template/{template_id}
Create an agent from a template.

**Response:**
```json
{
  "success": true,
  "agent": {
    "id": "agent_newid",
    "name": "Code Assistant",
    "description": "Expert programmer...",
    "system_prompt": "You are an expert..."
  }
}
```

---

### 🧠 AI Models

#### GET /models
List available AI models.

**Response:**
```json
{
  "success": true,
  "models": [
    {
      "id": "llama-3.3-70b-versatile",
      "name": "Llama 3.3 70B",
      "provider": "Groq",
      "context": 128000
    },
    {
      "id": "llama-3.1-8b-instant",
      "name": "Llama 3.1 8B",
      "provider": "Groq",
      "context": 128000
    },
    {
      "id": "mixtral-8x7b-32768",
      "name": "Mixtral 8x7B",
      "provider": "Groq",
      "context": 32768
    },
    {
      "id": "gemma2-9b-it",
      "name": "Gemma 2 9B",
      "provider": "Groq",
      "context": 8192
    }
  ]
}
```

---

### 📚 Knowledge Base (RAG)

#### POST /knowledge/upload
Upload a document to the knowledge base.

**Request:** `multipart/form-data`
- `file`: PDF file
- `agent_id`: Agent ID to associate with

**Response:**
```json
{
  "success": true,
  "filename": "document.pdf",
  "chunks": 15,
  "message": "Document processed and indexed"
}
```

---

#### GET /knowledge/{agent_id}
List documents for an agent.

**Response:**
```json
{
  "success": true,
  "documents": [
    {
      "filename": "document.pdf",
      "chunks": 15,
      "uploaded_at": "2024-12-07T12:00:00"
    }
  ]
}
```

---

#### DELETE /knowledge/{agent_id}/{filename}
Delete a document from knowledge base.

**Response:**
```json
{
  "success": true
}
```

---

### ⚙️ Settings & Integrations

#### GET /settings
Get user settings.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "settings": {
    "aws_access_key": "AKIA...",
    "aws_secret_key": "********",
    "aws_region": "us-east-1",
    "aws_log_group": "/agenthub/logs",
    "dd_api_key": "********",
    "dd_site": "datadoghq.com"
  }
}
```

---

#### POST /settings/aws
Save AWS CloudWatch settings.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "access_key": "AKIA...",
  "secret_key": "wJalrXU...",
  "region": "us-east-1",
  "log_group": "/agenthub/logs"
}
```

**Response:**
```json
{
  "success": true,
  "message": "AWS CloudWatch connection successful"
}
```

**Error Response (400):**
```json
{
  "detail": "Invalid Access Key ID"
}
```

---

#### POST /settings/aws/test
Test AWS connection without saving.

**Request Body:**
```json
{
  "access_key": "AKIA...",
  "secret_key": "wJalrXU...",
  "region": "us-east-1",
  "log_group": "/test"
}
```

**Response:**
```json
{
  "success": true,
  "message": "AWS CloudWatch connection successful"
}
```

---

#### POST /settings/datadog
Save Datadog settings.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "api_key": "dd_api_key_here",
  "site": "datadoghq.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Datadog connection successful"
}
```

---

#### POST /settings/datadog/test
Test Datadog connection without saving.

**Request Body:**
```json
{
  "api_key": "dd_api_key_here",
  "site": "datadoghq.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Datadog connection successful"
}
```

---

### 🔧 MCP Tools

#### GET /mcp/tools
List available MCP tools.

**Response:**
```json
{
  "tools": [
    {
      "name": "list_buckets",
      "description": "List all S3 buckets in the AWS account"
    },
    {
      "name": "create_bucket",
      "description": "Create a new S3 bucket"
    },
    {
      "name": "delete_bucket",
      "description": "Delete an S3 bucket"
    }
  ]
}
```

---

## Error Responses

All endpoints return consistent error responses:

**400 Bad Request:**
```json
{
  "detail": "Validation error message"
}
```

**401 Unauthorized:**
```json
{
  "detail": "Not authenticated"
}
```

**404 Not Found:**
```json
{
  "detail": "Resource not found"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Internal server error",
  "detail": "Error message (in debug mode)"
}
```

---

## Rate Limits

Currently no rate limiting is enforced. This will be added in Phase 2 (SaaS Readiness).

---

## Webhooks

*Coming in Phase 5 (Developer Experience)*

---

*Last Updated: December 7, 2024*

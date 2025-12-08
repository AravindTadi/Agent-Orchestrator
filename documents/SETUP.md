# AgentHub Setup Guide

## Prerequisites

- Python 3.11+
- Node.js 18+ (optional, for development tools)
- Git
- AWS credentials (optional, for S3 tools)

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/AravindTadi/Agnet-aws-mcp.git
cd Agnet-aws-mcp/Agents
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Environment Variables

Create a `.env` file in the project root:

```env
# Required
GROQ_API_KEY=gsk_your_groq_api_key_here

# Optional - AWS for MCP tools
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1

# Optional - Debugging
DEBUG=true
```

Or set them in your shell:

```bash
export GROQ_API_KEY="gsk_your_groq_api_key_here"
```

### 5. Start the Backend Server

```bash
python3 -m backend.main
```

You should see:
```
🔌 Connecting to MCP Server...
✅ MCP Connected! Loaded 3 tools
🧠 Initializing Vector Store...
✅ Vector Store initialized!
💾 Initializing Database...
✅ Database initialized!
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 6. Open the Frontend

Open `frontend/index.html` in your browser, or start a simple HTTP server:

```bash
# Option 1: Python HTTP server
cd frontend
python3 -m http.server 3000

# Option 2: Use the backend static files
# Navigate to http://localhost:8000
```

---

## Detailed Configuration

### Groq API Key

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key
5. Copy and paste into `.env` file

### AWS Credentials (Optional)

For MCP S3 tools to work:

1. Go to AWS Console → IAM → Users
2. Create a user with S3 permissions
3. Generate access keys
4. Add to `~/.aws/credentials`:

```ini
[default]
aws_access_key_id = AKIA...
aws_secret_access_key = your_secret_key
region = us-east-1
```

Or set environment variables:
```bash
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="your_secret_key"
export AWS_DEFAULT_REGION="us-east-1"
```

---

## Requirements

### Python Dependencies (requirements.txt)

```
fastapi>=0.104.0
uvicorn>=0.24.0
groq>=0.4.0
boto3>=1.33.0
mcp>=1.0.0
pymilvus>=2.3.0
milvus-lite>=2.4.0
sentence-transformers>=2.2.0
pypdf>=3.17.0
bcrypt>=4.1.0
requests>=2.31.0
python-multipart>=0.0.6
```

Install with:
```bash
pip install -r requirements.txt
```

---

## Directory Structure After Setup

```
Agents/
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── auth.py
│   ├── settings.py
│   ├── monitoring.py
│   ├── config.py
│   ├── mcp/
│   │   └── server.py
│   └── rag/
│       ├── vector_store.py
│       └── document_processor.py
├── frontend/
│   ├── index.html
│   ├── orchestrator.html
│   ├── chat.html
│   ├── integrations.html
│   ├── login.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── script.js
├── data/                    # Created automatically
│   ├── agents.db
│   ├── users.db
│   ├── milvus_data.db
│   └── knowledge/
├── documents/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── DATABASE.md
│   └── SETUP.md
├── .env                     # Create this
├── requirements.txt
└── ROADMAP.md
```

---

## Running in Development

### Backend (with auto-reload)

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (with live reload)

Use any HTTP server with live reload:

```bash
# Using npx
npx live-server frontend

# Using Python
cd frontend && python3 -m http.server 3000
```

---

## Testing

### Test Backend API

```bash
# Health check
curl http://localhost:8000/health

# List agents
curl http://localhost:8000/agents

# List templates
curl http://localhost:8000/templates

# List models
curl http://localhost:8000/models
```

### Test Authentication

```bash
# Signup
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

### Test Chat

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_default",
    "message": "Hello, how are you?",
    "history": []
  }'
```

---

## Troubleshooting

### Issue: MCP Server not connecting

**Symptom:** `MCP connection error`

**Solution:**
1. Check that `boto3` is installed
2. Verify AWS credentials are set
3. Check the MCP server path in `config.py`

### Issue: Vector store initialization fails

**Symptom:** `Milvus error`

**Solution:**
1. Delete `data/milvus_data.db` and restart
2. Ensure `pymilvus` and `milvus-lite` are installed

### Issue: Groq API errors

**Symptom:** `Authentication error`

**Solution:**
1. Verify `GROQ_API_KEY` is set correctly
2. Check API key is valid at console.groq.com

### Issue: Database locked

**Symptom:** `database is locked`

**Solution:**
1. Close any other processes using the database
2. Delete `data/*.db` files and restart (will reinitialize)

---

## Docker Deployment (Coming Soon)

### docker-compose.yml

```yaml
version: '3.8'
services:
  agenthub:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
    volumes:
      - ./data:/app/data
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Production Deployment

### AWS ECS (SaaS)

1. Build Docker image
2. Push to ECR
3. Create ECS task definition
4. Set up ALB load balancer
5. Configure RDS PostgreSQL
6. Set up ElastiCache Redis

### On-Premises

1. Use Docker Compose
2. Configure reverse proxy (nginx)
3. Set up SSL certificates
4. Configure backup strategy

---

*Last Updated: December 7, 2024*

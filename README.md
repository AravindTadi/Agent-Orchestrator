# 🤖 AgentHub - AI Agent Orchestrator

A full-stack AI Agent platform with RAG (Retrieval Augmented Generation), MCP tools integration, and a beautiful modern UI.

## 📁 Project Structure

```
Agents/
├── .env                    # Environment variables (API keys)
├── requirements.txt        # Python dependencies
├── README.md              
│
├── backend/                # Backend API Server
│   ├── __init__.py
│   ├── main.py             # FastAPI application entry point
│   ├── config.py           # Centralized configuration
│   │
│   ├── mcp/                # MCP (Model Context Protocol) Tools
│   │   ├── __init__.py
│   │   └── server.py       # AWS S3 tools server
│   │
│   └── rag/                # RAG (Retrieval Augmented Generation)
│       ├── __init__.py
│       ├── vector_store.py # Milvus Lite vector database
│       └── document_processor.py  # TXT, PDF, DOCX, CSV, URL parsing
│
├── frontend/               # Frontend Static Files
│   ├── index.html          # Agent Dashboard
│   ├── orchestrator.html   # Agent Configuration
│   ├── chat.html           # Standalone Chat
│   ├── css/
│   │   └── style.css       # Global styles (dark mode support)
│   └── js/
│       └── script.js       # Frontend logic
│
└── data/                   # Data Storage
    └── milvus_data.db      # Vector database file
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment
Create a `.env` file:
```
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Run the Backend
```bash
cd /path/to/Agents
python -m backend.main
```

### 4. Open the Frontend
Open `frontend/index.html` in your browser, or use a local server:
```bash
python -m http.server 5500 --directory frontend
```

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Send message to agent (with RAG context) |
| `/documents/upload` | POST | Upload file to knowledge base |
| `/documents/url` | POST | Add web URL to knowledge base |
| `/documents/{agent_id}` | GET | List agent's documents |
| `/documents/{agent_id}/{doc_id}` | DELETE | Delete a document |
| `/documents/stats` | GET | Get vector DB statistics |

## 🎨 Features

- ✅ **Multi-Agent Management** - Create and configure multiple agents
- ✅ **RAG Integration** - Upload documents to create knowledge bases
- ✅ **MCP Tools** - AWS S3 management capabilities
- ✅ **Dark Mode** - Beautiful theming with light/dark toggle
- ✅ **Watsonx-style Chat** - Professional chat interface with reasoning
- ✅ **Autosave** - Configuration saves automatically
- ✅ **Document Support** - TXT, PDF, DOCX, CSV, and Web URLs

## 🛠 Tech Stack

- **Backend**: FastAPI, Groq (Llama 3.3), Milvus Lite
- **Frontend**: Vanilla HTML/CSS/JS, IBM Carbon Design inspired
- **Vector DB**: Milvus Lite (embedded)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Tools**: MCP (Model Context Protocol) for AWS integration

## 📄 License

MIT License

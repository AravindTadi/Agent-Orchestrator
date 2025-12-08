# AgentHub Documentation Index

Welcome to the AgentHub documentation. This folder contains comprehensive documentation for understanding, setting up, and extending the AgentHub platform.

---

## 📚 Documentation Files

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System architecture, component overview, and technology stack |
| [API.md](./API.md) | Complete API reference with all endpoints |
| [DATABASE.md](./DATABASE.md) | Database schema, tables, and relationships |
| [FLOWS.md](./FLOWS.md) | User flows, data flows, and state management |
| [SETUP.md](./SETUP.md) | Installation and configuration guide |

---

## 🗺️ Quick Navigation

### For Developers

1. Start with [SETUP.md](./SETUP.md) to get the project running
2. Review [ARCHITECTURE.md](./ARCHITECTURE.md) to understand the system
3. Use [API.md](./API.md) as a reference when building features
4. Check [DATABASE.md](./DATABASE.md) when adding new tables

### For DevOps

1. [SETUP.md](./SETUP.md) - Deployment instructions
2. [ARCHITECTURE.md](./ARCHITECTURE.md) - Infrastructure requirements

### For Product

1. [FLOWS.md](./FLOWS.md) - User journeys and interactions
2. [../ROADMAP.md](../ROADMAP.md) - Product roadmap and priorities

---

## 🚀 Getting Started

```bash
# 1. Clone the repository
git clone https://github.com/AravindTadi/Agnet-aws-mcp.git
cd Agnet-aws-mcp/Agents

# 2. Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
export GROQ_API_KEY="your_api_key"

# 5. Start the server
python3 -m backend.main
```

---

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│              HTML / CSS / Vanilla JavaScript                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ REST API (HTTP)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND                                  │
│                    FastAPI (Python)                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────────┐ │
│  │  Auth   │  │ Agents  │  │  RAG    │  │   MCP (Tools)       │ │
│  └─────────┘  └─────────┘  └─────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
         │            │            │                    │
         ▼            ▼            ▼                    ▼
┌─────────────┐ ┌───────────┐ ┌──────────┐    ┌──────────────────┐
│ SQLite DBs  │ │ Groq API  │ │ Milvus   │    │     AWS S3       │
│ (users,     │ │ (LLM)     │ │ (Vectors)│    │   CloudWatch     │
│  agents)    │ │           │ │          │    │   Datadog        │
└─────────────┘ └───────────┘ └──────────┘    └──────────────────┘
```

---

## 🔧 Key Technologies

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | HTML/CSS/JS | User interface |
| Backend | FastAPI | REST API server |
| LLM | Groq (Llama 3.3) | AI inference |
| Database | SQLite | Persistent storage |
| Vectors | Milvus Lite | RAG embeddings |
| Tools | MCP Protocol | External integrations |

---

## 📝 Contributing

When contributing to the documentation:

1. Keep diagrams in ASCII art for portability
2. Update "Last Updated" date when making changes
3. Add API endpoints to API.md when creating new routes
4. Update DATABASE.md when adding new tables
5. Document new flows in FLOWS.md

---

## 📫 Support

- GitHub Issues: For bugs and feature requests
- Documentation: This folder
- Product Roadmap: [ROADMAP.md](../ROADMAP.md)

---

*Last Updated: December 7, 2024*

"""
Backend Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Paths
BASE_DIR = Path(__file__).parent.parent
BACKEND_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Vector Store Config
MILVUS_DB_PATH = str(DATA_DIR / "milvus_data.db")
COLLECTION_NAME = "agent_knowledge"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# MCP Server
MCP_SERVER_PATH = str(BACKEND_DIR / "mcp" / "server.py")

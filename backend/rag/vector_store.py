"""
Milvus Lite Vector Store for RAG
Handles embedding storage and similarity search per agent.
"""

from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional

# Import configuration
from backend.config import MILVUS_DB_PATH, COLLECTION_NAME, EMBEDDING_MODEL, EMBEDDING_DIM

TOP_K = 5  # Number of results to return

# Global instances
_client: Optional[MilvusClient] = None
_embedder: Optional[SentenceTransformer] = None


def get_client() -> MilvusClient:
    """Get or create Milvus Lite client."""
    global _client
    if _client is None:
        print(f"🔌 Connecting to Milvus Lite at: {MILVUS_DB_PATH}")
        _client = MilvusClient(MILVUS_DB_PATH)
        _ensure_collection_exists()
    return _client


def get_embedder() -> SentenceTransformer:
    """Get or create embedding model."""
    global _embedder
    if _embedder is None:
        print(f"🧠 Loading embedding model: {EMBEDDING_MODEL}")
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
        print("✅ Embedding model loaded!")
    return _embedder


def _ensure_collection_exists():
    """Create the collection if it doesn't exist."""
    client = _client
    
    if not client.has_collection(COLLECTION_NAME):
        print(f"📦 Creating collection: {COLLECTION_NAME}")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            dimension=EMBEDDING_DIM,
            metric_type="COSINE",
            auto_id=False,
            id_type="string",
            max_length=64
        )
        print(f"✅ Collection '{COLLECTION_NAME}' created!")
    else:
        print(f"✅ Collection '{COLLECTION_NAME}' already exists.")


def embed_text(text: str) -> List[float]:
    """Generate embedding for a single text."""
    embedder = get_embedder()
    embedding = embedder.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts."""
    embedder = get_embedder()
    embeddings = embedder.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()


def add_chunks(
    agent_id: str,
    document_id: str,
    chunks: List[str],
    metadata: Dict[str, Any] = None
) -> int:
    """
    Add document chunks to the vector store.
    
    Args:
        agent_id: The agent this document belongs to
        document_id: Unique identifier for the document
        chunks: List of text chunks
        metadata: Additional metadata (filename, source, etc.)
    
    Returns:
        Number of chunks added
    """
    if not chunks:
        return 0
    
    client = get_client()
    
    # Generate embeddings
    print(f"🔄 Generating embeddings for {len(chunks)} chunks...")
    embeddings = embed_texts(chunks)
    
    # Prepare data for insertion
    data = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_id = f"{document_id}_{i}"
        data.append({
            "id": chunk_id,
            "vector": embedding,
            "agent_id": agent_id,
            "document_id": document_id,
            "chunk_index": i,
            "text": chunk[:8000],  # Milvus has field size limits
            "metadata": metadata or {}
        })
    
    # Insert into Milvus
    client.insert(collection_name=COLLECTION_NAME, data=data)
    print(f"✅ Added {len(data)} chunks for document {document_id}")
    
    return len(data)


def search(
    agent_id: str,
    query: str,
    top_k: int = TOP_K
) -> List[Dict[str, Any]]:
    """
    Search for similar chunks in an agent's knowledge base.
    
    Args:
        agent_id: The agent to search within
        query: The search query
        top_k: Number of results to return
    
    Returns:
        List of matching chunks with metadata
    """
    client = get_client()
    
    # Generate query embedding
    query_embedding = embed_text(query)
    
    # Search with filter for agent_id
    results = client.search(
        collection_name=COLLECTION_NAME,
        data=[query_embedding],
        filter=f'agent_id == "{agent_id}"',
        limit=top_k,
        output_fields=["text", "document_id", "chunk_index", "metadata"]
    )
    
    # Format results
    formatted = []
    if results and len(results) > 0:
        for hit in results[0]:
            formatted.append({
                "id": hit["id"],
                "score": hit["distance"],
                "text": hit["entity"].get("text", ""),
                "document_id": hit["entity"].get("document_id", ""),
                "chunk_index": hit["entity"].get("chunk_index", 0),
                "metadata": hit["entity"].get("metadata", {})
            })
    
    return formatted


def delete_document(agent_id: str, document_id: str) -> int:
    """
    Delete all chunks for a specific document.
    
    Returns:
        Number of chunks deleted (approximate)
    """
    client = get_client()
    
    # Delete by filter
    result = client.delete(
        collection_name=COLLECTION_NAME,
        filter=f'agent_id == "{agent_id}" and document_id == "{document_id}"'
    )
    
    print(f"🗑️ Deleted chunks for document {document_id}")
    return result.get("delete_count", 0) if isinstance(result, dict) else 0


def delete_all_agent_documents(agent_id: str) -> int:
    """
    Delete ALL documents/chunks for an agent.
    Used when deleting an agent.
    
    Returns:
        Number of chunks deleted (approximate)
    """
    client = get_client()
    
    # Delete all chunks for this agent
    result = client.delete(
        collection_name=COLLECTION_NAME,
        filter=f'agent_id == "{agent_id}"'
    )
    
    print(f"🗑️ Deleted ALL chunks for agent {agent_id}")
    return result.get("delete_count", 0) if isinstance(result, dict) else 0


def list_documents(agent_id: str) -> List[Dict[str, Any]]:
    """
    List all documents for an agent.
    
    Returns:
        List of unique documents with metadata
    """
    client = get_client()
    
    # Query to get unique document_ids
    results = client.query(
        collection_name=COLLECTION_NAME,
        filter=f'agent_id == "{agent_id}"',
        output_fields=["document_id", "metadata"],
        limit=1000
    )
    
    # Deduplicate by document_id
    seen = set()
    documents = []
    for item in results:
        doc_id = item.get("document_id")
        if doc_id and doc_id not in seen:
            seen.add(doc_id)
            documents.append({
                "document_id": doc_id,
                "metadata": item.get("metadata", {})
            })
    
    return documents


def get_stats() -> Dict[str, Any]:
    """Get collection statistics."""
    client = get_client()
    
    try:
        stats = client.get_collection_stats(COLLECTION_NAME)
        return {
            "collection": COLLECTION_NAME,
            "row_count": stats.get("row_count", 0)
        }
    except Exception as e:
        return {"error": str(e)}


# Initialize on import (lazy loading)
def init():
    """Initialize the vector store."""
    get_client()
    get_embedder()
    print("🚀 Vector Store initialized!")


if __name__ == "__main__":
    # Test the vector store
    init()
    
    # Test adding chunks
    test_chunks = [
        "Milvus is a vector database for AI applications.",
        "RAG combines retrieval with generation for better answers.",
        "Embeddings convert text into numerical vectors."
    ]
    
    add_chunks(
        agent_id="test_agent",
        document_id="test_doc_1",
        chunks=test_chunks,
        metadata={"filename": "test.txt", "source": "manual"}
    )
    
    # Test search
    results = search("test_agent", "What is Milvus?")
    print("\n🔍 Search Results:")
    for r in results:
        print(f"  Score: {r['score']:.4f} | {r['text'][:50]}...")
    
    # Test list documents
    docs = list_documents("test_agent")
    print(f"\n📄 Documents: {docs}")
    
    # Test stats
    stats = get_stats()
    print(f"\n📊 Stats: {stats}")

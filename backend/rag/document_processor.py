"""
Document Processor for RAG
Handles parsing and chunking of various document types.
"""

import os
import re
import uuid
import requests
from typing import List, Dict, Any, Tuple
from bs4 import BeautifulSoup
import csv
from io import StringIO

# Chunk configuration
CHUNK_SIZE = 500  # Target characters per chunk
CHUNK_OVERLAP = 50  # Overlap between chunks


def generate_document_id() -> str:
    """Generate a unique document ID."""
    return f"doc_{uuid.uuid4().hex[:12]}"


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Uses sentence boundaries when possible for cleaner chunks.
    """
    if not text or not text.strip():
        return []
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Try to split by sentences first
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        # If adding this sentence would exceed chunk size
        if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            # Keep overlap from end of previous chunk
            if overlap > 0 and len(current_chunk) > overlap:
                current_chunk = current_chunk[-overlap:] + " " + sentence
            else:
                current_chunk = sentence
        else:
            current_chunk += " " + sentence if current_chunk else sentence
    
    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


def process_txt(content: bytes, filename: str) -> Tuple[List[str], Dict[str, Any]]:
    """Process a TXT file."""
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')
    
    chunks = chunk_text(text)
    metadata = {
        "filename": filename,
        "type": "txt",
        "size": len(content),
        "chunks": len(chunks)
    }
    
    return chunks, metadata


def process_pdf(content: bytes, filename: str) -> Tuple[List[str], Dict[str, Any]]:
    """Process a PDF file."""
    try:
        import pypdf
        from io import BytesIO
        
        reader = pypdf.PdfReader(BytesIO(content))
        text_parts = []
        
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"[Page {i+1}]\n{page_text}")
        
        full_text = "\n\n".join(text_parts)
        chunks = chunk_text(full_text)
        
        metadata = {
            "filename": filename,
            "type": "pdf",
            "pages": len(reader.pages),
            "size": len(content),
            "chunks": len(chunks)
        }
        
        return chunks, metadata
        
    except ImportError:
        raise ValueError("pypdf is required for PDF processing. Install with: pip install pypdf")
    except Exception as e:
        raise ValueError(f"Error processing PDF: {str(e)}")


def process_docx(content: bytes, filename: str) -> Tuple[List[str], Dict[str, Any]]:
    """Process a DOCX file."""
    try:
        from docx import Document
        from io import BytesIO
        
        doc = Document(BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        
        full_text = "\n\n".join(paragraphs)
        chunks = chunk_text(full_text)
        
        metadata = {
            "filename": filename,
            "type": "docx",
            "paragraphs": len(paragraphs),
            "size": len(content),
            "chunks": len(chunks)
        }
        
        return chunks, metadata
        
    except ImportError:
        raise ValueError("python-docx is required for DOCX processing. Install with: pip install python-docx")
    except Exception as e:
        raise ValueError(f"Error processing DOCX: {str(e)}")


def process_csv(content: bytes, filename: str) -> Tuple[List[str], Dict[str, Any]]:
    """Process a CSV file - each row becomes a chunk."""
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')
    
    reader = csv.DictReader(StringIO(text))
    chunks = []
    
    for row in reader:
        # Convert each row to a readable text format
        row_text = " | ".join(f"{k}: {v}" for k, v in row.items() if v)
        if row_text.strip():
            chunks.append(row_text)
    
    metadata = {
        "filename": filename,
        "type": "csv",
        "rows": len(chunks),
        "size": len(content),
        "chunks": len(chunks)
    }
    
    return chunks, metadata


def process_url(url: str) -> Tuple[List[str], Dict[str, Any]]:
    """Process a web URL - extracts main content."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get title
        title = soup.title.string.strip() if soup.title else url
        
        # Get meta description
        meta_desc = ""
        meta_tag = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
        if meta_tag:
            meta_desc = meta_tag.get('content', '').strip()

        # Remove script and style elements
        for script in soup(["script", "style", "noscript", "iframe", "svg"]):
            script.decompose()
        
        # Get text
        # Use get_text with separator to preserve some structure
        text = soup.get_text(separator='\n\n')
        
        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned_text = '\n'.join(lines)
        
        # If text is too short, try to use meta description
        if len(cleaned_text) < 100 and meta_desc:
            cleaned_text = f"{title}\n\n{meta_desc}\n\n{cleaned_text}"
        elif meta_desc:
             # Prepend title and description for better context
            cleaned_text = f"Title: {title}\nDescription: {meta_desc}\n\n{cleaned_text}"
        else:
            cleaned_text = f"Title: {title}\n\n{cleaned_text}"

        chunks = chunk_text(cleaned_text)
        
        # If still no chunks, create at least one from title/url to avoid empty errors
        if not chunks:
            chunks = [f"Title: {title}\nURL: {url}\n(No readable content found)"]
        
        metadata = {
            "url": url,
            "title": title,
            "type": "web",
            "size": len(response.content),
            "chunks": len(chunks)
        }
        
        return chunks, metadata
        
    except requests.RequestException as e:
        raise ValueError(f"Error fetching URL: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error processing URL: {str(e)}")


def process_document(
    content: bytes = None,
    filename: str = None,
    url: str = None
) -> Tuple[str, List[str], Dict[str, Any]]:
    """
    Process a document and return chunks.
    
    Args:
        content: File content as bytes (for file uploads)
        filename: Original filename (for file uploads)
        url: Web URL (for URL processing)
    
    Returns:
        Tuple of (document_id, chunks, metadata)
    """
    document_id = generate_document_id()
    
    if url:
        chunks, metadata = process_url(url)
        metadata["source"] = "url"
    elif content and filename:
        ext = os.path.splitext(filename.lower())[1]
        
        if ext == '.txt':
            chunks, metadata = process_txt(content, filename)
        elif ext == '.pdf':
            chunks, metadata = process_pdf(content, filename)
        elif ext in ['.docx', '.doc']:
            chunks, metadata = process_docx(content, filename)
        elif ext == '.csv':
            chunks, metadata = process_csv(content, filename)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
        
        metadata["source"] = "upload"
    else:
        raise ValueError("Either content+filename or url must be provided")
    
    metadata["document_id"] = document_id
    
    print(f"📄 Processed document: {metadata.get('filename') or metadata.get('url')}")
    print(f"   📊 {len(chunks)} chunks created")
    
    return document_id, chunks, metadata


if __name__ == "__main__":
    # Test the document processor
    
    # Test TXT
    test_txt = b"This is a test document. It has multiple sentences. Each sentence should be processed correctly."
    doc_id, chunks, meta = process_document(content=test_txt, filename="test.txt")
    print(f"\nTXT Test: {len(chunks)} chunks")
    print(f"Metadata: {meta}")
    
    # Test URL
    try:
        doc_id, chunks, meta = process_document(url="https://example.com")
        print(f"\nURL Test: {len(chunks)} chunks")
        print(f"Metadata: {meta}")
    except Exception as e:
        print(f"\nURL Test Error: {e}")

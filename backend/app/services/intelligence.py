import os
import ast
import re
import httpx
import logging
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.extensions import CodeSearchIndex
from app.services.vector_store import get_vector_store
from app.core.config import settings

logger = logging.getLogger(__name__)

# Regular expressions for symbol extraction in non-Python languages
JS_TS_CLASS_RE = re.compile(r'(?:export\s+)?class\s+([a-zA-Z0-9_$]+)')
JS_TS_FUNC_RE = re.compile(r'(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\(')
GO_FUNC_RE = re.compile(r'^func\s+(?:\([^)]+\)\s+)?([a-zA-Z0-9_]+)\s*\(')
JAVA_CLASS_RE = re.compile(r'(?:public\s+)?class\s+([a-zA-Z0-9_]+)')
JAVA_METHOD_RE = re.compile(r'(?:public|protected|private|static|\s)+[a-zA-Z0-9_<>]+\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*\{')

def scan_and_index_repository(repo_id: str, workspace_path: str) -> None:
    """
    Scans repository directory, extracts AST/regex symbols into CodeSearchIndex,
    generates semantic embeddings, and indexes them in the Vector Database.
    """
    db: Session = SessionLocal()
    vector_store = get_vector_store()
    
    exclude_dirs = {".git", "node_modules", "venv", ".venv", "build", "target", "dist", "__pycache__", ".gemini"}
    include_extensions = {".py", ".js", ".ts", ".tsx", ".go", ".java", ".rs", ".css", ".scss", ".html", ".vue", ".svelte", ".jsx"}
    
    # 1. Clear old indexes for this repository
    try:
        db.query(CodeSearchIndex).filter(CodeSearchIndex.repository_id == repo_id).delete()
        db.commit()
    except Exception as e:
        logger.error(f"Error clearing old indexes: {e}")
        db.rollback()
        
    logger.info(f"Scanning codebase for indexing symbols: {workspace_path}...")
    indexed_symbols_count = 0
    embedded_chunks_count = 0
    
    for root, dirs, files in os.walk(workspace_path):
        # Exclude directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in include_extensions:
                continue
                
            abs_path = os.path.join(root, file)
            rel_path = os.path.relpath(abs_path, workspace_path)
            
            try:
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    
                if not content.strip():
                    continue

                # 2. Extract AST Symbols
                symbols = _extract_symbols(rel_path, content)
                
                # Save symbols in SQL Search Index
                for sym_name, sym_type, start, end, sym_content in symbols:
                    record = CodeSearchIndex(
                        repository_id=repo_id,
                        filepath=rel_path,
                        symbol_name=sym_name,
                        symbol_type=sym_type,
                        start_line=start,
                        end_line=end,
                        content=sym_content
                    )
                    db.add(record)
                    indexed_symbols_count += 1
                    
                # 3. Generate Semantic Embeddings for Chunks
                # Split content into ~1000-character logical chunks for vector index
                chunks = _chunk_code(rel_path, content, symbols)
                for chunk_text, chunk_symbol in chunks:
                    embedding = get_text_embedding(chunk_text)
                    vector_store.add_embedding(
                        repository_id=repo_id,
                        filepath=rel_path,
                        symbol=chunk_symbol,
                        content=chunk_text,
                        embedding=embedding
                    )
                    embedded_chunks_count += 1

            except Exception as file_err:
                logger.error(f"Error indexing file {rel_path}: {file_err}")

    db.commit()
    db.close()
    logger.info(f"Finished indexing repo {repo_id}. Symbols stored: {indexed_symbols_count}. Chunks embedded: {embedded_chunks_count}.")


def _extract_symbols(filepath: str, content: str) -> List[Tuple[str, str, int, int, str]]:
    """
    Helper returning list of Tuples: (symbol_name, symbol_type, start_line, end_line, content)
    Supports native AST for Python, and regular expression fallbacks for others.
    """
    symbols = []
    lines = content.splitlines()
    ext = os.path.splitext(filepath)[1].lower()
    
    # Python Native AST Parsing
    if ext == ".py":
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                    start = node.lineno
                    # Find end line
                    end = getattr(node, "end_lineno", len(lines))
                    sym_type = "class" if isinstance(node, ast.ClassDef) else "function"
                    sym_content = "\n".join(lines[start - 1 : end])
                    symbols.append((node.name, sym_type, start, end, sym_content))
            return symbols
        except SyntaxError:
            logger.warning(f"Syntax error parsing Python file AST: {filepath}. Falling back to regex.")

    # Regex Parsing Fallback (TS/JS/Go/Java/Rust)
    for idx, line in enumerate(lines, 1):
        line_strip = line.strip()
        if not line_strip:
            continue
            
        # JS / TS Check
        if ext in [".js", ".ts", ".tsx"]:
            class_match = JS_TS_CLASS_RE.search(line_strip)
            if class_match:
                symbols.append((class_match.group(1), "class", idx, idx + 10, line))
                continue
            func_match = JS_TS_FUNC_RE.search(line_strip)
            if func_match:
                symbols.append((func_match.group(1), "function", idx, idx + 5, line))
                continue
                
        # Go check
        elif ext == ".go":
            go_match = GO_FUNC_RE.search(line_strip)
            if go_match:
                symbols.append((go_match.group(1), "function", idx, idx + 8, line))
                
        # Java check
        elif ext == ".java":
            c_match = JAVA_CLASS_RE.search(line_strip)
            if c_match:
                symbols.append((c_match.group(1), "class", idx, idx + 15, line))
                continue
            m_match = JAVA_METHOD_RE.search(line_strip)
            if m_match:
                symbols.append((m_match.group(1), "function", idx, idx + 8, line))

    return symbols


def _chunk_code(filepath: str, content: str, symbols: List[Tuple[str, str, int, int, str]]) -> List[Tuple[str, str]]:
    """Splits code files into overlapping text chunks, annotated with related symbols."""
    chunks = []
    lines = content.splitlines()
    
    # If file has symbols, add symbols content directly as chunks
    for sym_name, sym_type, start, end, sym_content in symbols:
        chunks.append((
            f"File: {filepath}\nSymbol: {sym_name} ({sym_type})\nLines {start}-{end}\n{sym_content}",
            sym_name
        ))
        
    # Also chunk the entire file by lines block to cover unparsed sections
    chunk_size = 40
    overlap = 10
    
    for i in range(0, len(lines), chunk_size - overlap):
        block = lines[i : i + chunk_size]
        if not block:
            break
        block_text = "\n".join(block)
        if len(block_text.strip()) > 100:
            chunks.append((
                f"File: {filepath}\nLines {i+1}-{i+len(block)}\n{block_text}",
                None
            ))
            
    return chunks


_gemini_api_working = True

def get_text_embedding(text: str) -> List[float]:
    """
    Generates a 768-dimension vector embedding using Google Gemini Embeddings API.
    Returns a hash-derived fallback vector if the API key is not configured or fails.
    """
    global _gemini_api_working
    api_key = settings.GEMINI_API_KEY
    if api_key and _gemini_api_working:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={api_key}"
            payload = {
                "content": {
                    "parts": [{"text": text[:2000]}]  # Cap size to avoid bloating
                }
            }
            res = httpx.post(url, json=payload, timeout=5.0)
            if res.status_code == 200:
                data = res.json()
                return data["embedding"]["values"]
            else:
                logger.warning(f"Gemini API returned status {res.status_code} for embeddings. Disabling remote API for this session.")
                _gemini_api_working = False
        except Exception as e:
            logger.warning(f"Failed to fetch real vector embedding from Gemini: {e}. Disabling remote API.")
            _gemini_api_working = False

    # Fallback deterministic vector hash (length 768)
    vector = []
    # Seed value based on text content
    seed = sum(ord(char) for char in text[:100])
    np.random.seed(seed)
    return np.random.randn(768).tolist()


def _local_tfidf_search(repo_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
    import math
    from collections import Counter
    db: Session = SessionLocal()
    try:
        from app.models.extensions import RepositoryEmbedding
        records = db.query(RepositoryEmbedding).filter(
            RepositoryEmbedding.repository_id == repo_id
        ).all()
        if not records:
            return []
            
        def tokenize(text: str) -> List[str]:
            return re.findall(r'[a-zA-Z0-9_]+', text.lower())
            
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
            
        docs_tokens = [tokenize(rec.content) for rec in records]
        
        df = Counter()
        for doc in docs_tokens:
            unique_terms = set(doc)
            for term in query_tokens:
                if term in unique_terms:
                    df[term] += 1
                    
        num_docs = len(records)
        idf = {}
        for term in query_tokens:
            idf[term] = math.log((1 + num_docs) / (1 + df[term])) + 1.0
            
        query_tf = Counter(query_tokens)
        query_vec = {}
        query_norm_sq = 0.0
        for term in query_tokens:
            query_vec[term] = (query_tf[term] / len(query_tokens)) * idf[term]
            query_norm_sq += query_vec[term] ** 2
        query_norm = math.sqrt(query_norm_sq)
        
        if query_norm == 0:
            return []
            
        results = []
        for idx, rec in enumerate(records):
            doc = docs_tokens[idx]
            if not doc:
                continue
                
            doc_tf = Counter(doc)
            doc_vec = {}
            doc_norm_sq = 0.0
            
            dot_product = 0.0
            for term in query_tokens:
                tf_val = doc_tf.get(term, 0) / len(doc)
                doc_vec[term] = tf_val * idf[term]
                dot_product += query_vec[term] * doc_vec[term]
                
            for term, val in doc_tf.items():
                term_idf = idf.get(term, 1.0)
                doc_norm_sq += (val / len(doc) * term_idf) ** 2
            doc_norm = math.sqrt(doc_norm_sq)
            
            similarity = 0.0
            if doc_norm > 0:
                similarity = dot_product / (query_norm * doc_norm)
                
            similarity = max(0.0, min(1.0, similarity))
            
            results.append({
                "filepath": rec.filepath,
                "symbol": rec.symbol,
                "content": rec.content,
                "similarity": float(similarity)
            })
            
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]
        
    except Exception as e:
        logger.error(f"Error performing local TF-IDF fallback search: {e}")
        return []
    finally:
        db.close()


def query_semantic_code_search(repo_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Embeds the user search query and executes similarity search against
    the indexed codebase vector blocks.
    Falls back to high-fidelity local TF-IDF cosine similarity search if Gemini key fails.
    """
    global _gemini_api_working
    if not _gemini_api_working or not settings.GEMINI_API_KEY:
        logger.info("Using local high-fidelity TF-IDF fallback search engine.")
        return _local_tfidf_search(repo_id, query, limit)
        
    try:
        query_vector = get_text_embedding(query)
        vector_store = get_vector_store()
        results = vector_store.search(repo_id, query_vector, limit)
        if results:
            return results
    except Exception as e:
        logger.warning(f"Semantic vector search failed: {e}. Falling back to TF-IDF.")
        
    return _local_tfidf_search(repo_id, query, limit)


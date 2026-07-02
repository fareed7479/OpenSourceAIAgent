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

import hashlib

def get_file_md5(filepath: str) -> str:
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
    except Exception:
        pass
    return hash_md5.hexdigest()

def scan_and_index_repository(repo_id: str, workspace_path: str) -> None:
    """
    Scans repository directory, extracts AST/regex symbols into CodeSearchIndex,
    generates semantic embeddings, and indexes them in the Vector Database.
    Implements production-grade incremental indexing using file hashing.
    """
    db: Session = SessionLocal()
    vector_store = get_vector_store()
    
    from app.models.repository import Repository
    from app.models.extensions import CodeSymbol, CodeRelation, RepositoryEmbedding
    
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        logger.error(f"Repository {repo_id} not found for indexing.")
        db.close()
        return
        
    meta_info = dict(repo.meta_info or {})
    cached_hashes = dict(meta_info.get("file_hashes", {}))
    
    exclude_dirs = {".git", "node_modules", "venv", ".venv", "build", "target", "dist", "__pycache__", ".gemini"}
    include_extensions = {".py", ".js", ".ts", ".tsx", ".go", ".java", ".rs", ".css", ".scss", ".html", ".vue", ".svelte", ".jsx"}
    
    # Track files currently present in workspace
    current_workspace_files = {}
    all_files_map = {}
    
    # First pass: map all codebase files and compute hashes
    for r, ds, fs in os.walk(workspace_path):
        ds[:] = [d for d in ds if d not in exclude_dirs]
        for f in fs:
            ext = os.path.splitext(f)[1].lower()
            if ext in include_extensions:
                abs_p = os.path.join(r, f)
                rel_p = os.path.relpath(abs_p, workspace_path)
                current_workspace_files[rel_p] = get_file_md5(abs_p)
                all_files_map[os.path.splitext(f)[0]] = rel_p

    # Identify modified, new, and deleted files
    new_or_modified = []
    for rel_path, file_hash in current_workspace_files.items():
        if cached_hashes.get(rel_path) != file_hash:
            new_or_modified.append(rel_path)
            
    deleted_files = [f for f in cached_hashes.keys() if f not in current_workspace_files]
    
    if not new_or_modified and not deleted_files:
        logger.info(f"Incremental scan: No files changed in repo {repo.owner}/{repo.name}. Skipping indexing.")
        db.close()
        return
        
    logger.info(f"Incremental indexing {repo.owner}/{repo.name}: {len(new_or_modified)} updated, {len(deleted_files)} deleted.")
    
    # 1. Clear database entries for deleted and modified files
    files_to_clear = new_or_modified + deleted_files
    for filepath in files_to_clear:
        try:
            db.query(CodeSearchIndex).filter(
                CodeSearchIndex.repository_id == repo_id,
                CodeSearchIndex.filepath == filepath
            ).delete()
            db.query(CodeSymbol).filter(
                CodeSymbol.repository_id == repo_id,
                CodeSymbol.filepath == filepath
            ).delete()
            db.query(CodeRelation).filter(
                CodeRelation.repository_id == repo_id,
                (CodeRelation.source_file.startswith(filepath) | CodeRelation.target_file.startswith(filepath))
            ).delete()
            db.query(RepositoryEmbedding).filter(
                RepositoryEmbedding.repository_id == repo_id,
                RepositoryEmbedding.filepath == filepath
            ).delete()
        except Exception as clear_err:
            logger.error(f"Error clearing old indexes for file {filepath}: {clear_err}")
    db.commit()

    # 2. Index new and modified files
    indexed_symbols_count = 0
    embedded_chunks_count = 0
    
    for rel_path in new_or_modified:
        abs_path = os.path.join(workspace_path, rel_path)
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
            if not content.strip():
                cached_hashes[rel_path] = current_workspace_files[rel_path]
                continue

            # Extract AST Symbols & Imports
            from app.services.ast_parser import ASTParser
            from app.services.knowledge_graph import KnowledgeGraphManager
            
            parsed_data = ASTParser.parse_file(rel_path, content)
            symbols = []
            lines = content.splitlines()
            
            # Save symbols in SQL Search Index
            for sym in parsed_data["symbols"]:
                sym_content = "\n".join(lines[sym["start_line"] - 1 : sym["end_line"]])
                symbols.append((sym["name"], sym["type"], sym["start_line"], sym["end_line"], sym_content))
                
                record = CodeSearchIndex(
                    repository_id=repo_id,
                    filepath=rel_path,
                    symbol_name=sym["name"],
                    symbol_type=sym["type"],
                    start_line=sym["start_line"],
                    end_line=sym["end_line"],
                    content=sym_content
                )
                db.add(record)
                indexed_symbols_count += 1
                
                KnowledgeGraphManager.add_symbol(
                    db, repo_id, rel_path, sym["name"], sym["type"], sym["start_line"], sym["end_line"]
                )
                
            # Save API routes
            for route in parsed_data["routes"]:
                KnowledgeGraphManager.add_symbol(
                    db, repo_id, rel_path, f"{route['method']} {route['path']}", "route", 1, 1
                )
                
            # Resolve import paths to build Knowledge Graph edges
            for imp in parsed_data["imports"]:
                imp_base = os.path.splitext(os.path.basename(imp))[0]
                if imp_base in all_files_map:
                    target_file = all_files_map[imp_base]
                    if target_file != rel_path:
                        KnowledgeGraphManager.add_relation(db, repo_id, rel_path, target_file, "imports")
                        
            # Save call relationships
            for call in parsed_data.get("calls", []):
                KnowledgeGraphManager.add_relation(
                    db, repo_id, f"{rel_path}::{call['caller']}", f"{rel_path}::{call['callee']}", "calls"
                )
                
            # Generate Semantic Embeddings for Chunks
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
                
            # Update cache hash
            cached_hashes[rel_path] = current_workspace_files[rel_path]

        except Exception as file_err:
            logger.error(f"Error indexing file {rel_path}: {file_err}")

    # Remove deleted files from hash cache
    for f in deleted_files:
        cached_hashes.pop(f, None)
        
    meta_info["file_hashes"] = cached_hashes
    repo.meta_info = meta_info
    
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


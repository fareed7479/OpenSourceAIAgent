import os
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.extensions import RepositoryEmbedding

logger = logging.getLogger(__name__)

class BaseVectorStore(ABC):
    @abstractmethod
    def add_embedding(
        self,
        repository_id: str,
        filepath: str,
        symbol: Optional[str],
        content: str,
        embedding: List[float]
    ) -> None:
        """Add a text chunk with its vector embedding to the index."""
        pass

    @abstractmethod
    def search(
        self,
        repository_id: str,
        query_embedding: List[float],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Perform similarity search and return closest matching code blocks."""
        pass


class SQLiteVectorStore(BaseVectorStore):
    """
    Default vector store using SQLite database storage and NumPy for
    calculating cosine similarity in memory. Extremely robust and zero-dependency.
    """
    def add_embedding(
        self,
        repository_id: str,
        filepath: str,
        symbol: Optional[str],
        content: str,
        embedding: List[float]
    ) -> None:
        db: Session = SessionLocal()
        try:
            record = RepositoryEmbedding(
                repository_id=repository_id,
                filepath=filepath,
                symbol=symbol,
                content=content,
                embedding=embedding
            )
            db.add(record)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to add embedding to SQLite: {e}")
            db.rollback()
        finally:
            db.close()

    def search(
        self,
        repository_id: str,
        query_embedding: List[float],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        db: Session = SessionLocal()
        try:
            # Load all embeddings for the target repository
            records = db.query(RepositoryEmbedding).filter(
                RepositoryEmbedding.repository_id == repository_id
            ).all()
            
            if not records:
                return []

            query_vector = np.array(query_embedding, dtype=np.float32)
            query_norm = np.linalg.norm(query_vector)
            
            if query_norm == 0:
                return []

            results = []
            for record in records:
                db_vector = np.array(record.embedding, dtype=np.float32)
                db_norm = np.linalg.norm(db_vector)
                
                if db_norm == 0:
                    continue
                    
                # Cosine Similarity: A . B / (|A| * |B|)
                similarity = np.dot(query_vector, db_vector) / (query_norm * db_norm)
                
                results.append({
                    "id": record.id,
                    "filepath": record.filepath,
                    "symbol": record.symbol,
                    "content": record.content,
                    "similarity": float(similarity)
                })

            # Sort by similarity descending
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching SQLite vector embeddings: {e}")
            return []
        finally:
            db.close()


class ChromaDBVectorStore(BaseVectorStore):
    """
    Optional ChromaDB vector store.
    Falls back to SQLiteVectorStore if chromadb is not installed.
    """
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        self.client = None
        self.fallback = SQLiteVectorStore()
        
        try:
            import chromadb
            # Initialize persistent client
            self.client = chromadb.PersistentClient(path=persist_directory)
            logger.info("ChromaDB persistent client loaded successfully.")
        except ImportError:
            logger.warning("chromadb package not found. ChromaDB provider falling back to SQLite vector search.")

    def add_embedding(
        self,
        repository_id: str,
        filepath: str,
        symbol: Optional[str],
        content: str,
        embedding: List[float]
    ) -> None:
        if not self.client:
            self.fallback.add_embedding(repository_id, filepath, symbol, content, embedding)
            return

        try:
            collection = self.client.get_or_create_collection(name=f"repo_{repository_id}")
            # Generate unique document ID
            doc_id = f"{filepath}_{symbol or 'code'}_{hash(content)}"
            
            collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[{
                    "filepath": filepath,
                    "symbol": symbol or ""
                }],
                documents=[content]
            )
        except Exception as e:
            logger.error(f"Error inserting into ChromaDB: {e}. Falling back to SQLite.")
            self.fallback.add_embedding(repository_id, filepath, symbol, content, embedding)

    def search(
        self,
        repository_id: str,
        query_embedding: List[float],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        if not self.client:
            return self.fallback.search(repository_id, query_embedding, limit)

        try:
            # Query collection
            collection = self.client.get_collection(name=f"repo_{repository_id}")
            res = collection.query(
                query_embeddings=[query_embedding],
                n_results=limit
            )
            
            results = []
            if res and res["documents"] and len(res["documents"][0]) > 0:
                for i in range(len(res["documents"][0])):
                    metadata = res["metadatas"][0][i]
                    # Convert distance to a similarity score (distance is L2 by default in Chroma)
                    distance = res["distances"][0][i] if "distances" in res else 0.0
                    similarity = 1.0 / (1.0 + distance)
                    
                    results.append({
                        "filepath": metadata.get("filepath", ""),
                        "symbol": metadata.get("symbol", ""),
                        "content": res["documents"][0][i],
                        "similarity": similarity
                    })
            return results
        except Exception as e:
            logger.warning(f"ChromaDB search failed or collection not found: {e}. Searching SQLite fallback.")
            return self.fallback.search(repository_id, query_embedding, limit)


class PGVectorStore(BaseVectorStore):
    """
    Optional PGVector vector store.
    Falls back to SQLiteVectorStore if pgvector or psycopg2 is not configured/installed.
    """
    def __init__(self):
        self.fallback = SQLiteVectorStore()
        logger.info("PGVector provider registered (future compatibility mode).")

    def add_embedding(
        self,
        repository_id: str,
        filepath: str,
        symbol: Optional[str],
        content: str,
        embedding: List[float]
    ) -> None:
        # Fall back to SQLite vector database for current Phase
        self.fallback.add_embedding(repository_id, filepath, symbol, content, embedding)

    def search(
        self,
        repository_id: str,
        query_embedding: List[float],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        return self.fallback.search(repository_id, query_embedding, limit)


def get_vector_store() -> BaseVectorStore:
    """Factory retrieving configured vector store based on environment settings."""
    store_type = os.getenv("VECTOR_STORE_PROVIDER", "sqlite").lower()
    if store_type == "chromadb":
        return ChromaDBVectorStore()
    elif store_type == "pgvector":
        return PGVectorStore()
    return SQLiteVectorStore()

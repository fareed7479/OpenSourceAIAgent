import logging
from typing import List, Dict, Set, Any
from sqlalchemy.orm import Session
from app.models.extensions import CodeRelation, CodeSymbol

logger = logging.getLogger(__name__)

class KnowledgeGraphManager:
    @staticmethod
    def add_relation(db: Session, repo_id: str, source_file: str, target_file: str, relation_type: str) -> None:
        """Stores a codebase relationship node edge in the database."""
        try:
            # Check if relation already exists to avoid duplication
            exists = db.query(CodeRelation).filter(
                CodeRelation.repository_id == repo_id,
                CodeRelation.source_file == source_file,
                CodeRelation.target_file == target_file,
                CodeRelation.relation_type == relation_type
            ).first()
            if not exists:
                rel = CodeRelation(
                    repository_id=repo_id,
                    source_file=source_file,
                    target_file=target_file,
                    relation_type=relation_type
                )
                db.add(rel)
                db.commit()
        except Exception as e:
            logger.error(f"Failed to add relation: {e}")
            db.rollback()

    @staticmethod
    def add_symbol(db: Session, repo_id: str, filepath: str, name: str, symbol_type: str, start_line: int, end_line: int) -> None:
        """Stores an extracted code symbol definition in the database."""
        try:
            # Check if symbol already exists
            exists = db.query(CodeSymbol).filter(
                CodeSymbol.repository_id == repo_id,
                CodeSymbol.filepath == filepath,
                CodeSymbol.name == name,
                CodeSymbol.symbol_type == symbol_type
            ).first()
            if not exists:
                sym = CodeSymbol(
                    repository_id=repo_id,
                    filepath=filepath,
                    name=name,
                    symbol_type=symbol_type,
                    start_line=start_line,
                    end_line=end_line
                )
                db.add(sym)
                db.commit()
        except Exception as e:
            logger.error(f"Failed to add symbol: {e}")
            db.rollback()

    @staticmethod
    def get_neighbors(db: Session, repo_id: str, filepaths: List[str]) -> List[str]:
        """Finds files directly linked (via imports or depend_on relations) in the graph."""
        if not filepaths:
            return []
        
        neighbors = set()
        try:
            # Find files that import target filepaths, or are imported by target filepaths
            relations = db.query(CodeRelation).filter(
                CodeRelation.repository_id == repo_id,
                (CodeRelation.source_file.in_(filepaths) | CodeRelation.target_file.in_(filepaths))
            ).all()
            
            for rel in relations:
                if rel.source_file not in filepaths:
                    neighbors.add(rel.source_file)
                if rel.target_file not in filepaths:
                    neighbors.add(rel.target_file)
        except Exception as e:
            logger.error(f"Error querying graph neighbors: {e}")
            
        return list(neighbors)

    @staticmethod
    def expand_context(db: Session, repo_id: str, seed_files: List[str], max_depth: int = 1) -> List[str]:
        """
        Traverses the codebase Knowledge Graph starting from seed files,
        expanding outwards to find related dependent files.
        """
        expanded = set(seed_files)
        current_layer = list(seed_files)
        
        for depth in range(max_depth):
            if not current_layer:
                break
            neighbors = KnowledgeGraphManager.get_neighbors(db, repo_id, current_layer)
            
            # Filter out already visited nodes
            next_layer = []
            for n in neighbors:
                if n not in expanded:
                    expanded.add(n)
                    next_layer.append(n)
            current_layer = next_layer
            
        return [f for f in expanded if f not in seed_files]

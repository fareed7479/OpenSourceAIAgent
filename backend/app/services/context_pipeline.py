import os
import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.repository import Repository
from app.models.issue import Issue
from app.models.run import AgentRun
from app.models.extensions import CodeSearchIndex, RepositoryMemory
from app.services.intelligence import query_semantic_code_search
from app.services.knowledge_graph import KnowledgeGraphManager
from app.services.test_discovery import TestDiscoveryManager
from app.services.workspace import WorkspaceManager

logger = logging.getLogger(__name__)

class ContextAssemblyPipeline:
    @staticmethod
    def assemble_context_package(
        db: Session,
        repo_id: str,
        issue_id: str,
        run_id: str,
        max_char_budget: int = 150000
    ) -> Dict[str, Any]:
        """
        Runs the complete repository intelligence context retrieval pipeline:
        1. Semantic Search (Top files)
        2. Knowledge Graph expansion (Dependent files)
        3. Test Discovery (Related tests)
        4. Historical Fixes (Memory matching)
        5. Architecture/Readme loading
        6. Quality Scoring (0-100)
        7. Token budget enforcement
        """
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        issue = db.query(Issue).filter(Issue.id == issue_id).first()
        repo_path = WorkspaceManager.get_repo_dir(repo_id)
        
        # 1. Semantic Search
        query_text = f"{issue.title} {issue.description or ''}"
        semantic_results = query_semantic_code_search(repo_id, query_text, limit=6)
        
        semantic_files = []
        semantic_scores = {}
        for doc in semantic_results:
            filepath = doc["filepath"]
            if filepath not in semantic_files:
                semantic_files.append(filepath)
                semantic_scores[filepath] = doc.get("similarity", 0.8)
                
        # 2. Knowledge Graph Expansion
        graph_expanded_files = KnowledgeGraphManager.expand_context(db, repo_id, semantic_files, max_depth=1)
        
        # 3. Test Discovery
        discovered_tests = TestDiscoveryManager.discover_related_tests(repo_path, semantic_files)
        
        # 4. Historical Fixes Retrieval
        historical_fixes = []
        try:
            # Query successful runs memory
            memories = db.query(RepositoryMemory).filter(
                RepositoryMemory.repository_id == repo_id,
                RepositoryMemory.memory_type == "past_fix"
            ).all()
            
            # Simple keyword matching score
            issue_words = set(query_text.lower().split())
            for m in memories:
                val_lower = m.value.lower()
                matching_words = sum(1 for w in issue_words if w in val_lower)
                if matching_words > 0:
                    historical_fixes.append({
                        "key": m.key,
                        "fix_summary": m.value,
                        "relevance": matching_words
                    })
            historical_fixes.sort(key=lambda x: x["relevance"], reverse=True)
            historical_fixes = historical_fixes[:2]  # top 2 matches
        except Exception as e:
            logger.error(f"Error fetching historical fixes: {e}")
            
        # 5. Architectural / Readme Loading
        readme_content = ""
        readme_path = None
        for name in os.listdir(repo_path):
            if name.upper() in ["README.MD", "README", "ARCHITECTURE.MD"]:
                readme_path = name
                break
        if readme_path:
            try:
                with open(os.path.join(repo_path, readme_path), "r", encoding="utf-8", errors="ignore") as f:
                    readme_content = f.read(1500)  # load summary
            except Exception:
                pass
                
        # 6. Read contents & enforce budget
        relevant_files = []
        file_contents = {}
        total_chars = 0
        retrieval_details = []
        
        # Priority 1: Semantic Files
        for f in semantic_files:
            abs_path = os.path.join(repo_path, f)
            if os.path.exists(abs_path):
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as file_io:
                    content = file_io.read(30000)
                if total_chars + len(content) <= max_char_budget:
                    relevant_files.append(f)
                    file_contents[f] = content
                    total_chars += len(content)
                    retrieval_details.append({
                        "filepath": f,
                        "score": round(semantic_scores.get(f, 0.8), 4),
                        "reason": "Primary semantic similarity match."
                    })
                    
        # Priority 2: Dependency Expanded Files
        for f in graph_expanded_files:
            if f in file_contents:
                continue
            abs_path = os.path.join(repo_path, f)
            if os.path.exists(abs_path):
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as file_io:
                    content = file_io.read(20000)
                if total_chars + len(content) <= max_char_budget:
                    relevant_files.append(f)
                    file_contents[f] = content
                    total_chars += len(content)
                    retrieval_details.append({
                        "filepath": f,
                        "score": 0.75,
                        "reason": "Dependency graph neighbor expansion."
                    })

        # Priority 3: Related Tests
        for f in discovered_tests:
            if f in file_contents:
                continue
            abs_path = os.path.join(repo_path, f)
            if os.path.exists(abs_path):
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as file_io:
                    content = file_io.read(15000)
                if total_chars + len(content) <= max_char_budget:
                    relevant_files.append(f)
                    file_contents[f] = content
                    total_chars += len(content)
                    retrieval_details.append({
                        "filepath": f,
                        "score": 0.7,
                        "reason": "Discovered related test suite."
                    })
                    
        # 7. Context Quality Scoring (0-100)
        # Metrics weights:
        # Semantic Relevance: max 30 (based on having semantic files with score > 0.5)
        # Dependency Coverage: max 20 (based on expanding graph neighbors)
        # Test Coverage: max 20 (based on finding and loading related tests)
        # Historical Coverage: max 15 (based on finding historical memory fixes)
        # Architecture Coverage: max 15 (based on readme/architecture file match)
        
        semantic_score = min(30, len(semantic_files) * 8)
        dependency_score = min(20, len(graph_expanded_files) * 10)
        test_score = 20 if len(discovered_tests) > 0 else 0
        historical_score = 15 if len(historical_fixes) > 0 else 0
        architecture_score = 15 if readme_content else 0
        
        overall_score = semantic_score + dependency_score + test_score + historical_score + architecture_score
        
        quality_metrics = {
            "semantic_relevance": semantic_score,
            "dependency_coverage": dependency_score,
            "test_coverage": test_score,
            "historical_coverage": historical_score,
            "architecture_coverage": architecture_score,
            "overall_score": overall_score
        }
        
        # Save metrics to QualityMetric DB table
        from app.models.extensions import QualityMetric
        try:
            # Clear old metrics for this run first
            db.query(QualityMetric).filter(QualityMetric.run_id == run_id).delete()
            metric = QualityMetric(
                run_id=run_id,
                security_score=80, # default placeholder review metrics
                performance_score=80,
                maintainability_score=80,
                style_score=80,
                overall_score=overall_score
            )
            db.add(metric)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to save context quality metrics: {e}")
            db.rollback()
            
        return {
            "relevant_files": relevant_files,
            "file_contents": file_contents,
            "retrieval_details": retrieval_details,
            "quality_metrics": quality_metrics,
            "historical_fixes": historical_fixes,
            "framework": repo.framework or "unknown",
            "language": repo.language or "unknown",
            "readme_summary": readme_content
        }

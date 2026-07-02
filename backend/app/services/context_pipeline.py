import os
import re
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
        semantic_results = query_semantic_code_search(repo_id, query_text, limit=10)
        
        semantic_files = []
        semantic_scores = {}
        for doc in semantic_results:
            filepath = doc["filepath"]
            if filepath not in semantic_files:
                semantic_files.append(filepath)
                semantic_scores[filepath] = doc.get("similarity", 0.5)
                
        # 2. Knowledge Graph Expansion
        graph_expanded_files = KnowledgeGraphManager.expand_context(db, repo_id, semantic_files, max_depth=1)
        
        # 3. Test Discovery
        discovered_tests = TestDiscoveryManager.discover_related_tests(repo_path, semantic_files)
        
        # 4. Historical Fixes & Memory Analysis
        historical_fixes = []
        historical_files_boost = set()
        conventions = []
        try:
            memories = db.query(RepositoryMemory).filter(
                RepositoryMemory.repository_id == repo_id
            ).all()
            
            issue_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', query_text.lower()))
            
            for m in memories:
                if m.memory_type == "past_fix":
                    val_lower = m.value.lower()
                    matching_words = sum(1 for w in issue_words if w in val_lower)
                    if matching_words > 0:
                        historical_fixes.append({
                            "key": m.key,
                            "fix_summary": m.value,
                            "relevance": matching_words
                        })
                        # Extract potential file paths mentioned in past fixes
                        found_files = re.findall(r'\b[a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]{2,4}\b', m.value)
                        for ff in found_files:
                            historical_files_boost.add(ff)
                elif m.memory_type in ["convention", "preference", "style"]:
                    conventions.append(f"{m.key}: {m.value}")
                    
            historical_fixes.sort(key=lambda x: x["relevance"], reverse=True)
            historical_fixes = historical_fixes[:3]
        except Exception as e:
            logger.error(f"Error fetching historical fixes: {e}")
            
        # 5. Call Graph Analysis
        caller_callee_files = set()
        try:
            from app.models.extensions import CodeRelation
            # Query calls relations for the repo
            call_relations = db.query(CodeRelation).filter(
                CodeRelation.repository_id == repo_id,
                CodeRelation.relation_type == "calls"
            ).all()
            
            # If a relation links to/from a semantic file, boost the other side
            for rel in call_relations:
                src_file = rel.source_file.split("::")[0]
                tgt_file = rel.target_file.split("::")[0]
                if src_file in semantic_files and tgt_file not in semantic_files:
                    caller_callee_files.add(tgt_file)
                elif tgt_file in semantic_files and src_file not in semantic_files:
                    caller_callee_files.add(src_file)
        except Exception as call_err:
            logger.error(f"Error parsing call graph relations: {call_err}")

        # 6. Read Architectural / Readme Loading
        readme_content = ""
        readme_path = None
        if os.path.exists(repo_path):
            for name in os.listdir(repo_path):
                if name.upper() in ["README.MD", "README", "ARCHITECTURE.MD"]:
                    readme_path = name
                    break
            if readme_path:
                try:
                    with open(os.path.join(repo_path, readme_path), "r", encoding="utf-8", errors="ignore") as f:
                        readme_content = f.read(2000)
                except Exception:
                    pass

        # 7. Relevance Scoring Model
        # Collect all unique files encountered in analysis
        all_candidate_files = set(
            semantic_files + 
            graph_expanded_files + 
            discovered_tests + 
            list(historical_files_boost) + 
            list(caller_callee_files)
        )
        
        file_relevance_details = []
        
        for filepath in all_candidate_files:
            semantic_weight = 0.40
            dependency_weight = 0.20
            history_weight = 0.15
            test_weight = 0.15
            call_graph_weight = 0.10
            
            # Calculate component scores
            s_score = semantic_scores.get(filepath, 0.0)
            
            dep_score = 0.0
            if filepath in semantic_files:
                dep_score = 1.0
            elif filepath in graph_expanded_files:
                dep_score = 0.8
                
            hist_score = 1.0 if filepath in historical_files_boost else 0.0
            t_score = 1.0 if filepath in discovered_tests else 0.0
            cg_score = 1.0 if filepath in caller_callee_files else 0.0
            
            # Weighted average
            total_relevance = (
                (s_score * semantic_weight) +
                (dep_score * dependency_weight) +
                (hist_score * history_weight) +
                (t_score * test_weight) +
                (cg_score * call_graph_weight)
            )
            
            # Format reasons
            reasons = []
            if s_score > 0:
                reasons.append(f"Semantic match ({round(s_score, 2)})")
            if dep_score > 0:
                reasons.append("Dependency link")
            if hist_score > 0:
                reasons.append("Matched past fix history")
            if t_score > 0:
                reasons.append("Discovered unit test file")
            if cg_score > 0:
                reasons.append("Linked in symbol call-graph")
                
            reason_str = ", ".join(reasons) or "Indirect codebase relevance"
            
            file_relevance_details.append({
                "filepath": filepath,
                "score": round(total_relevance, 4),
                "reason": reason_str
            })

        # Sort files by relevance score descending
        file_relevance_details.sort(key=lambda x: x["score"], reverse=True)

        # 8. Load file contents & enforce token/character budget
        relevant_files = []
        file_contents = {}
        total_chars = 0
        retrieval_details = []
        
        for item in file_relevance_details:
            f = item["filepath"]
            abs_path = os.path.join(repo_path, f)
            if os.path.exists(abs_path):
                try:
                    with open(abs_path, "r", encoding="utf-8", errors="ignore") as file_io:
                        content = file_io.read(40000) # Read up to 40k chars
                    if total_chars + len(content) <= max_char_budget:
                        relevant_files.append(f)
                        file_contents[f] = content
                        total_chars += len(content)
                        retrieval_details.append(item)
                except Exception as read_err:
                    logger.error(f"Failed to read file {f} for context: {read_err}")

        # 9. Context Quality Scoring (0-100)
        semantic_score = min(30, len(semantic_files) * 8)
        dependency_score = min(20, len(graph_expanded_files) * 5)
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
            db.query(QualityMetric).filter(QualityMetric.run_id == run_id).delete()
            metric = QualityMetric(
                run_id=run_id,
                security_score=85,
                performance_score=85,
                maintainability_score=85,
                style_score=85,
                overall_score=overall_score
            )
            db.add(metric)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to save context quality metrics: {e}")
            db.rollback()

        # 10. Generate structured context package summary string for Planning/Coding Agent
        package_lines = [
            "==================================================",
            "REPOSITORY INTELLIGENCE CONTEXT PACKAGE SUMMARY",
            "==================================================",
            f"Repository: {repo.owner}/{repo.name}",
            f"Language: {repo.language or 'unknown'} | Framework: {repo.framework or 'unknown'}",
            f"Architecture Pattern: {repo.meta_info.get('architecture', 'Monolithic Layout') if repo.meta_info else 'Monolithic Layout'}",
            f"Confidence Score: {overall_score}/100",
            "",
            "--- RELEVANT FILES & SYMBOLS ---"
        ]
        
        for det in retrieval_details[:8]:
            package_lines.append(f"- File: {det['filepath']} (Relevance Score: {det['score']})")
            package_lines.append(f"  Reason: {det['reason']}")
            
        if discovered_tests:
            package_lines.append("")
            package_lines.append("--- DISCOVERED RELATED TESTS ---")
            for t in discovered_tests[:3]:
                package_lines.append(f"- Test File: {t}")
                
        if historical_fixes:
            package_lines.append("")
            package_lines.append("--- RELEVANT HISTORICAL FIXES ---")
            for h in historical_fixes[:2]:
                package_lines.append(f"- Fix Summary: {h['fix_summary']}")
                
        if conventions:
            package_lines.append("")
            package_lines.append("--- CODING CONVENTIONS & STYLES ---")
            for c in conventions[:3]:
                package_lines.append(f"- {c}")
                
        package_lines.append("==================================================")
        context_package_str = "\n".join(package_lines)

        return {
            "relevant_files": relevant_files,
            "file_contents": file_contents,
            "retrieval_details": retrieval_details,
            "quality_metrics": quality_metrics,
            "historical_fixes": historical_fixes,
            "framework": repo.framework or "unknown",
            "language": repo.language or "unknown",
            "readme_summary": readme_content,
            "context_package_str": context_package_str
        }


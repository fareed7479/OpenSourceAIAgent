import re
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def evaluate_issue_difficulty_and_score(
    title: str,
    body: str,
    labels: List[str],
    repo_language: str,
    user_preferred_languages: List[str] = None,
    comments_count: int = 0,
    github_created_at: datetime = None,
    assignment_status: str = "unassigned"
) -> Dict[str, Any]:
    """
    Calculates difficulty ("easy", "medium", "hard") and a suitability score (0-100)
    for a given issue based on title, description, labels, language matches,
    comments count, issue age, and assignment status.
    """
    body_text = body or ""
    title_text = title or ""
    
    # 1. Determine Difficulty
    difficulty = "medium"  # default
    
    # Easy indicators
    easy_labels = {"good-first-issue", "good first issue", "easy", "documentation", "docs", "chore", "simple", "beginner", "help wanted", "help-wanted"}
    has_easy_label = any(label.lower() in easy_labels for label in labels)
    
    # Hard indicators
    hard_labels = {"architectural", "performance", "security", "refactor", "complex", "epic"}
    has_hard_label = any(label.lower() in hard_labels for label in labels)
    
    # Check text lengths and keyword counts
    text_len = len(body_text) + len(title_text)
    
    if has_easy_label or (text_len < 400 and not has_hard_label):
        difficulty = "easy"
    elif has_hard_label or text_len > 3000 or "refactor" in body_text.lower() or "rewrite" in body_text.lower():
        difficulty = "hard"

    # 2. Compute Ranking Score (0-100)
    score = 50  # starting baseline
    reasons = []

    # Difficulty adjustment
    if difficulty == "easy":
        score += 15
        reasons.append("Easy/Good-First-Issue suitability boost (+15)")
    elif difficulty == "hard":
        score -= 10
        reasons.append("High complexity penalty (-10)")

    # Label-specific adjustments
    labels_lower = [l.lower() for l in labels]
    
    # ELUSOC / Bounty
    if any("elusoc" in l or "bounty" in l for l in labels_lower):
        score += 20
        reasons.append("ELUSOC bounty target boost (+20)")
        
    # Beginner / Help Wanted
    if any(l in {"beginner", "help wanted", "help-wanted"} for l in labels_lower):
        score += 10
        reasons.append("Beginner-friendly label boost (+10)")
        
    # Bug
    if any("bug" in l for l in labels_lower):
        score += 10
        reasons.append("Bugfix contribution priority boost (+10)")
        
    # Documentation
    if any("doc" in l for l in labels_lower):
        score += 5
        reasons.append("Documentation contribution boost (+5)")
        
    # Enhancement / Feature
    if any(l in {"enhancement", "feature", "feat"} for l in labels_lower):
        score += 5
        reasons.append("Feature/Enhancement contribution boost (+5)")

    # Clarity evaluation
    has_code_block = "```" in body_text
    has_markdown_headers = bool(re.search(r"^#+\s", body_text, re.MULTILINE))
    has_checklist = "- [ ]" in body_text or "- [x]" in body_text

    if has_code_block:
        score += 10
        reasons.append("Contains code blocks/reproducers (+10)")
    if has_markdown_headers:
        score += 5
        reasons.append("Structured Markdown headers (+5)")
    if has_checklist:
        score += 5
        reasons.append("Contains checklists (+5)")
        
    if len(body_text) < 100:
        score -= 20
        reasons.append("Vague/short description penalty (-20)")
    elif len(body_text) > 1000:
        score += 10
        reasons.append("Detailed description boost (+10)")

    # Language/Framework alignment
    if repo_language and repo_language != "unknown":
        if user_preferred_languages and repo_language.lower() in [l.lower() for l in user_preferred_languages]:
            score += 20
            reasons.append(f"Tech stack match on language '{repo_language}' (+20)")
        else:
            score += 5
            reasons.append(f"Language '{repo_language}' match (+5)")

    # Comments Count signals
    if comments_count > 20:
        score -= 5
        reasons.append("High discussion volume suggests high complexity (-5)")
    elif comments_count > 0:
        boost = min(10, comments_count * 1)
        score += boost
        reasons.append(f"Active discussion volume boost (+{boost})")

    # Issue Age signals
    if github_created_at:
        try:
            # Ensure timezone compatibility
            tz = github_created_at.tzinfo or timezone.utc
            now = datetime.now(tz)
            age_days = (now - github_created_at).days
            if age_days < 30:
                score += 10
                reasons.append("Fresh issue (< 30 days old) boost (+10)")
            elif age_days > 180:
                score -= 10
                reasons.append("Stale issue (> 180 days old) penalty (-10)")
        except Exception as e:
            logger.warning(f"Failed to calculate issue age for score: {e}")

    # Assignment status signals (extremely important - taken issues are heavily penalized)
    if assignment_status != "unassigned":
        score -= 50
        reasons.append(f"Issue already in progress/assigned ({assignment_status}) (-50)")

    # Bound score between 0 and 100
    score = max(0, min(100, score))
    ranking_reason = "; ".join(reasons) if reasons else "Standard baseline score."

    return {
        "difficulty": difficulty,
        "score": score,
        "ranking_reason": ranking_reason
    }

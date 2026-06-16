# Implementation Plan - Phase 3 Audit, Debugging, and Production Completion

This plan outlines the steps to audit, verify, debug, repair, and complete the Issue Discovery, Storage, Ranking, Filtering, and Dashboard workflows.

## Problem Description

1. **Missing Schema Fields**: The `Issue` database model is missing fields requested by the user: `author_username` (Author), `github_created_at` (Created Date), `github_updated_at` (Updated Date), `comments_count` (Comments Count), and `meta_info` (for flexible JSON metadata).
2. **Incomplete Sync & Fork Redirection**:
   - Issue tracker settings on forks are often disabled, redirecting to the parent/upstream repo. Currently, the sync fetches from the fork regardless, returning empty lists or failing.
   - Assigned issues are ignored during sync instead of being stored with `assigned_to_other` status.
3. **Missing Filters**: The frontend is missing selectors to filter by label and status (open/closed).
4. **Missing Issue Details Modal**: The frontend lacks a details modal to view full descriptions, ranking reasoning breakdowns, author info, comment counts, and assignment controls.
5. **Baseline Ranking Engine**: The ranking engine only uses description clarity and basic language match, missing signals like ELUSOC labels, comments counts, issue age, and assignment status.

---

## Proposed Changes

### Database & Schema Migration

#### [MODIFY] [issue.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/models/issue.py)
- Add columns:
  - `author_username` (String, nullable=True)
  - `github_created_at` (DateTime, nullable=True)
  - `github_updated_at` (DateTime, nullable=True)
  - `comments_count` (Integer, default=0)
  - `meta_info` (JSON, nullable=True)

#### [MODIFY] [init_db.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/db/init_db.py)
- Implement an automated `run_migrations` function on database startup to check if the new columns exist on the `issues` table and run `ALTER TABLE issues ADD COLUMN ...` statements if they are missing.

---

### Backend Logic & Services

#### [MODIFY] [issue.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/schemas/issue.py)
- Update `IssueResponse` to include the new fields: `author_username`, `github_created_at`, `github_updated_at`, `comments_count`, and `meta_info`.

#### [MODIFY] [repositories.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/api/repositories.py)
- Fetch and store `"has_issues"` (boolean) and `"parent"` (dict) in the repository's `meta_info["github_metadata"]` upon registration and sync.

#### [MODIFY] [discovery.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/services/discovery.py)
- Modify `discover_repository_issues_task`:
  - Retrieve `has_issues` and `parent` from the repository metadata. If `has_issues` is False and it's a fork, redirect the issues API query to the parent/upstream repository.
  - Set request param `"state": "all"` to fetch both open and closed issues.
  - Do not discard assigned issues. Map their assignment status correctly.
  - Parse and store: `author_username`, `github_created_at`, `github_updated_at`, `comments_count`, and `meta_info` for each issue.
- Update `_seed_mock_issues` to seed mock issues with the new fields.

#### [MODIFY] [ranking.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/services/ranking.py)
- Expand `evaluate_issue_difficulty_and_score` to incorporate:
  - **ELUSOC / Bounty** labels (+20 points)
  - **Beginner / Help Wanted** labels (+10 points)
  - **Bug / Documentation / Enhancement** labels
  - **Comments count** (+2 points per comment up to +10, penalty if > 20)
  - **Issue age** (+10 if < 30 days, -10 if > 180 days)
  - **Assignment status** (reduction of 50 points if assigned to other/in progress)

#### [MODIFY] [issues.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/api/issues.py)
- Update `list_issues` route:
  - Add `state: Optional[str] = Query(None)` to support filtering by state (`open`, `closed`, `all`). Default to `open` if omitted.
  - Add `label: Optional[str] = Query(None)` to support filtering by label.

---

### Frontend Enhancements

#### [MODIFY] [Issues.tsx](file:///d:/PROJECTS/OpenSource%20Agent%20Project/frontend/src/pages/Issues.tsx)
- Add UI controls:
  - **Label dropdown/input** to filter issues by labels.
  - **State selector tab/dropdown** to filter by Open, Closed, or All.
- Update issue lists to display comments count, author username, and GitHub updated date.
- Implement a modal dialog for **Issue Details**:
  - Displays title, description (scrollable), labels, author, comments, parent repository, and assignment status.
  - Renders a visual breakdown of the **AI Suitability Score** with ranking reasoning.
  - Provides assignment controls ("Request Assignment") from inside the modal.

---

## Verification Plan

### Automated Tests
Create a new automated test file:
#### [NEW] [test_phase3.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/tests/test_phase3.py)
Verify:
1. Database migrations run and columns are created successfully.
2. Fork redirection fetches from parent if issues tracker is disabled on fork.
3. Ranking engine scores correctly according to comments count, age, and label signals.
4. `/issues` endpoint filters correctly by state, label, search keywords, and repository.

To run:
```bash
& "d:\PROJECTS\OpenSource Agent Project\venv\Scripts\python.exe" -m unittest tests.test_phase3
```

### Manual Verification
1. Log in, sync `fareed7479/College_Companion`.
2. Verify that if issues tracker is disabled on the fork, the issues from parent are synced.
3. Open Issues page. Try filters (State, Label, Repo, Search) and verify results.
4. Click on an issue to open the details modal. Verify all details, score breakdown, and comments are visible.

# Implementation Plan - Phase 2 Audit, Debugging, and Production Completion

This plan outlines the steps to audit, verify, debug, repair, and complete the Repository Registration and Repository Discovery/Sync workflows.

## Problem Description

1. **GitHub API Suffix Sensitivity (404 Error)**: When registering a repository, if the user enters a URL ending with `.git` (e.g., `https://github.com/owner/repo.git`), the backend parses the repository name as `repo.git`. The subsequent GitHub API query to `https://api.github.com/repos/owner/repo.git` returns `404 Not Found`. This causes registration to fail with: *"Repository not found on GitHub. Verify ownership and visibility settings."*
2. **Missing Discovery Interface**: There is no UI or backend endpoint to fetch and list the user's actual GitHub repositories. The frontend dashboard only has a raw URL input text box, violating the Acceptance Criteria which require viewing, searching, filtering, and selecting from the user's GitHub repositories.
3. **Missing Sync/Refresh Action**: No sync/refresh mechanism exists to update the repository's metadata (fork status, visibility, topics, description, default branch, etc.) and discover issues on-demand.

---

## User Review Required

> [!IMPORTANT]
> - **URL Cleaning**: The backend will automatically strip the `.git` suffix and any trailing slashes from entered URLs before calling the GitHub API and before saving the repository record.
> - **Metadata Storage**: Since migrating the database schema is not desirable at this stage, all extra GitHub metadata (e.g., Description, Fork Status, Visibility, Owner, Language, Topics, Clone URL, GitHub URL, and Last Updated) will be structured and stored within the existing `meta_info` JSON column.
> - **Mock Bypass Support**: For developer mode or mock users, both the discovery endpoint and sync endpoint will return high-fidelity mock data to ensure local test suites and sandbox demos run successfully.

---

## Open Questions

> [!NOTE]
> We will implement the GitHub Repository list directly in the dashboard UI as a toggled tab ("Discover Repositories") next to the "My Registered Repositories" tab. If you prefer a different layout (e.g. side-by-side columns or a separate page), let us know, but a tabbed layout is typically clean and mobile-friendly.

---

## Proposed Changes

### Backend Components

#### [MODIFY] [repositories.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/api/repositories.py)
- Import `parse_github_url` utility or add inline parsing logic to strip `.git` and trailing slashes.
- Retrieve full repository metadata (Name, Description, default branch, fork status, visibility, owner, language, topics, clone URL, html URL, updated_at) from the GitHub API response during registration and store it in `meta_info["github_metadata"]`.
- `[NEW]` Add `GET /api/v1/repositories/github` route to fetch the authenticated user's repositories (forks and originals) from GitHub.
- `[NEW]` Add `POST /api/v1/repositories/{repo_id}/sync` route to refresh repository metadata from the GitHub API and trigger issue discovery.
- Ensure proper routing order so that `/github` does not conflict with `/{repo_id}`.

---

### Frontend Components

#### [MODIFY] [Dashboard.tsx](file:///d:/PROJECTS/OpenSource%20Agent%20Project/frontend/src/pages/Dashboard.tsx)
- Add a tab selection menu at the top: **My Registered Repositories** and **Discover GitHub Repositories**.
- In **Discover GitHub Repositories**:
  - Fetch available repositories from the backend `GET /repositories/github` endpoint.
  - Render a search filter input (filter by repository name).
  - Add quick filter buttons: **All**, **Forks**, **Original**.
  - Show description, fork status (with icon), visibility status, and primary language for each repo.
  - Render a **Register** button for each repository. Disable or show "Registered" if the repository is already in the local database.
- In **My Registered Repositories**:
  - Show full metadata details if available in `meta_info.github_metadata`.
  - Add a **Sync Now** button next to each repository that triggers `POST /repositories/{repo_id}/sync` and displays a loading spinner.

---

## Verification Plan

### Automated Tests
We will write a suite of tests in:
#### [NEW] [test_phase2.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/tests/test_phase2.py)
This test suite will verify:
1. Registration cleaning logic (correctly parsing `https://github.com/owner/repo.git` and `https://github.com/owner/repo/` to `owner` and `repo`).
2. Registering a repo fetches metadata and stores it in `meta_info`.
3. The new `/repositories/github` endpoint returns the list of GitHub repositories (verified under mock mode).
4. The `/repositories/{repo_id}/sync` endpoint updates metadata and triggers issue discovery.

To run tests:
```bash
& "d:\PROJECTS\OpenSource Agent Project\venv\Scripts\python.exe" -m unittest backend/tests/test_phase2.py
```

### Manual Verification
1. Run backend: `python -m uvicorn app.main:app --reload`
2. Run frontend: `npm run dev`
3. Log in via GitHub OAuth.
4. On the Dashboard:
   - Verify that all repositories (including forks) are loaded under the "Discover GitHub Repositories" tab.
   - Type in the search box to filter by name.
   - Toggle filters between "All", "Forks", and "Original".
   - Select a fork and click "Register". Verify registration succeeds and transitions to "Cloning" state.
   - Click "Sync Now" on a registered repository and verify that metadata and issues are refreshed.

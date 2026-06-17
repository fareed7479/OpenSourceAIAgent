# Implementation Plan - Phase 5.5 Observability Cockpit & Agent Monitoring

This implementation plan outlines the steps to audit, debug, repair, and complete all observability, agent monitoring, provider transparency, and real-time cockpit features for the autonomous coding workflow.

---

## 🔍 1. Discovered Issues & Root Causes

1. **Timeline State Synchronization Failure (Issue 1)**:
   - *Root Cause*: The `/intelligence/run/{run_id}/timeline` API endpoint was crashing with a `500 NameError` because `ImplementationIteration`, `QualityMetric`, and `RepairAttempt` were not imported in `intelligence.py`. Since `Promise.all` in the frontend page rejected, the state variables `selectedRun` and `monitorData` were never set, leaving all timeline steps in "Pending" and all panels empty.

2. **Empty Live Console & Code Diffs (Issues 2 & 3)**:
   - *Root Cause*: Due to the aforementioned `Promise.all` crash, logs were never successfully fetched. Additionally, the `/runs/{run_id}/diff` API endpoint returned a 404 because the dev server was running stale code. After server restart, the API returns 200 OK.

3. **Missing Provider Transparency (Issue 5)**:
   - *Root Cause*: Although `AgentRun` has database columns for `actual_provider`, `fallback_provider`, and `fallback_reason`, the Orchestrator's `CodingAgent._run_logic` never extracted `provider_metadata` from the coding agents and never saved these details to the database. Coding providers (OpenHands, ClaudeCode, Aider) did not populate `provider_metadata` on fallback.

4. **Incomplete Context Retrieval Audit (Issue 7)**:
   - *Root Cause*: Codebase indexing in `intelligence.py` restricted extensions to `{".py", ".js", ".ts", ".tsx", ".go", ".java", ".rs"}`. Crucially, `.css`, `.scss`, `.html`, `.vue`, `.svelte`, and `.jsx` were completely omitted from indexing. Thus, styling or layout tasks (e.g. CSS files) were never semantically matched. Furthermore, no retrieval metrics (scores/reasons) were generated or exposed via API.

---

## 🛠️ 2. Proposed Changes

### Backend Components

#### [MODIFY] [schemas/run.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/schemas/run.py)
- Define `RepositorySummary` and `IssueSummary` Pydantic models.
- Add `repository` and `issue` as nested optional models in `AgentRunResponse` to provide complete workspace/issue information to the cockpit.

#### [MODIFY] [services/agent_provider.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/services/agent_provider.py)
- Update `OpenHandsCodingAgent`, `ClaudeCodeCodingAgent`, and `AiderCodingAgent` to correctly structure and return `provider_metadata` on success and LLM fallback execution, ensuring requested provider, actual provider, fallback provider, and fallback reason are fully tracked.

#### [MODIFY] [services/agent_orchestrator.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/services/agent_orchestrator.py)
- **CodingAgent**: Extract `provider_metadata` from the coding agent return dictionary. Write `actual_provider`, `fallback_provider`, and `fallback_reason` to the `AgentRun` record and commit changes.
- **ContextAgent**:
  - Increase semantic search query limit to 10.
  - Calculate `retrieval_details` (filepath, cosine similarity score, and selection reason).
  - Load only the top 4 files into the agent context window to optimize size.
  - Save `retrieval_details` inside the `AgentLog` log data.
  - In the fallback logic, add default files to the `retrieval_details` map with a score of `1.0`.

#### [MODIFY] [services/intelligence.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/services/intelligence.py)
- Add `.css`, `.scss`, `.html`, `.vue`, `.svelte`, and `.jsx` to the indexed file extensions set in `scan_and_index_repository`.

#### [MODIFY] [api/runs.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/api/runs.py)
- Add a new route `GET /runs/{run_id}/context-metrics` that extracts the `retrieval_details` list from the context stage log and returns it.

---

### Frontend Components

#### [MODIFY] [pages/AgentMonitor.tsx](file:///d:/PROJECTS/OpenSource%20Agent%20Project/frontend/src/pages/AgentMonitor.tsx)
- Add a **Real-Time Execution Details Panel** displaying:
  - Run Status, active agent name, target branch, and run duration.
  - Workspace details: repository owner/name, associated issue URL/title.
  - Provider transparency: Requested provider, actual provider, fallback provider, and fallback reason (with a warning badge if Gemini fallback occurred).
- Add a **Context Retrieval Quality Panel** (rendered inside the right-hand panel or a dedicated tab):
  - Displays a clean table of the Top 10 retrieved files.
  - Shows similarity scores formatted as percentage matches.
  - Renders the exact selection reasoning (e.g. "Loaded into context window", "CSS styling matches UI enhancement intent").
- Refine dashboard UX styling with high-contrast, premium, dark-mode elements (harmonious colors, borders, and animations).

---

## 🔬 3. Verification Plan

### Automated Tests
- Run the API test script to verify that `/runs/{run_id}` contains repository/issue summaries, and that `/runs/{run_id}/context-metrics` returns retrieval details:
  ```powershell
  & "d:\PROJECTS\OpenSource Agent Project\venv\Scripts\python.exe" C:\Users\User\.gemini\antigravity\brain\7afae6a6-5c7f-44d5-b931-958efb4cc502\scratch\test_apis.py
  ```

### Manual Verification
- Access the Agent Monitor frontend cockpit.
- Trigger/select a run and verify:
  1. Timeline stages update their states successfully.
  2. Live console streams log output dynamically.
  3. Diffs populate correctly with lines added/removed.
  4. The Execution Details panel shows complete provider metadata and repository details.
  5. The Context Retrieval Quality panel displays top files, scores, and selection reasons.

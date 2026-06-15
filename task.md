# Project TODO List: Open Source OS Contribution Agent (Phases 11-22)

## Phase 11: Real Autonomous Coding Agent (Jules & OpenHands)
- [x] Refactor `agent_provider.py` to support provider-based abstractions
- [x] Implement Jules (Primary) and OpenHands (First-class) provider classes
- [x] Add stubs/configurations for Aider, Claude Code, and Gemini (fallback)
- [x] Create frontend Agent Execution Viewer showing analyzed files and active steps
- [x] Create agent database tables (`agent_states`, `agent_tasks`, `agent_plans`)

## Phase 12: Repository Intelligence Layer
- [x] Implement AST parsing codebase scanner for Python/TS/JS/Go (indexing files & symbols)
- [x] Implement provider-based Vector Database Abstraction Layer
- [x] Implement SQLite + NumPy cosine similarity default vector store provider
- [x] Implement ChromaDB optional vector store provider
- [x] Create frontend Repository Intelligence page visualizing codebase symbol maps

## Phase 13: Multi-Agent Architecture
- [x] Implement custom State Machine orchestrator managing 9 specific agent nodes
- [x] Integrate DB tracing, shared memory, and failure recovery state machines
- [x] Create frontend Agent Monitor visualizing active states and timeline queues

## Phase 14: Planning Agent
- [x] Implement Planning Agent generating strategies stored in database
- [x] Pause workflow and add approval gateway endpoints (`/runs/{run_id}/approve-plan`)
- [x] Create frontend Planning Center showing plans and enabling modification/approval

## Phase 15: Intelligent Code Search Agent
- [x] Integrate AST symbol index and vector semantic search into the Context Agent
- [x] Save code search traces to database (`code_search_index`)

## Phase 16: Self-Healing Implementation Loop
- [x] Implement autonomous repair cycle: capture test errors, prompt agent, retry up to 3 times
- [x] Store repair details in `repair_attempts` and `implementation_iterations`
- [x] Create frontend Self-Healing Viewer showing attempts history

## Phase 17: Active AI Review Loop
- [x] Implement review-driven improvement loop (Quality review -> quality score -> patch fix -> re-review)
- [x] Store review comments in `agent_reviews` and `quality_metrics`

## Phase 18: GitHub Webhook Architecture
- [x] Create `/api/v1/webhooks/github` POST handler with HMAC-SHA256 signature verification
- [x] Implement webhook event processors for Issues, PRs, and Comments with queue logs
- [x] Integrate background Celery task triggering

## Phase 19: ELUSOC Intelligence Layer
- [x] Implement ELUSOC issue classification and suitability scoring logic
- [x] Create frontend ELUSOC Dashboard tracking contributions, eligibility, and progress

## Phase 20: Repository Memory System
- [x] Implement memory engine extracting coding patterns, review feedback, and failures
- [x] Store memories in `repository_memory` and retrieve them to steer Planning/Coding agents

## Phase 21: Human Feedback Learning System
- [x] Capture user PR reviews/rejections and save them to `feedback_history`
- [x] Convert feedback into `learning_signals` to steer future plans

## Phase 22: Advanced Draft PR Workspace
- [x] Create frontend GitHub-style PR review workspace with side-by-side/unified diff viewer
- [x] Integrate file explorer, execution logs, planning history, and AI review tabs
- [x] Add user actions (Request Re-Implementation, Edit PR title/desc, Edit Commit message)

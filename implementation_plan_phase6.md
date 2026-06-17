# Implementation Plan - Phase 6: Repository Intelligence & Context Quality Engine

This phase audits, repairs, and productionizes the codebase context retrieval layer, moving from shallow single-file queries to a deep Repository Intelligence Engine that understands dependency graphs, tests, frameworks, symbols, and historical fixes.

---

## 🚀 Proposed Changes

### 1. Database Migrations & Symbol Storage
- **[NEW] Table `code_symbols`**: Stores extracted class, method, function, route, and interface details (filepath, start/end line, symbol type).
- **[NEW] Table `code_relations`**: Stores directed edges between files/symbols representing relationships (`imports`, `defines`, `calls`, `depends_on`).
- Declare these models in [extensions.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/models/extensions.py) and expose them in `__init__.py` so SQLite creates them.
- Add migration check scripts inside [init_db.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/db/init_db.py).

### 2. AST Code Intelligence & Symbol Parser
- **[NEW] [ast_parser.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/services/ast_parser.py)**: Extracts functions, classes, methods, interfaces, imports/exports, API handlers, and routes from files using Python `ast` (for Python) and robust Regex parser (for TypeScript, JavaScript, Go, Java, Rust).
- Update [intelligence.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/services/intelligence.py) to invoke the symbol parser during codebase scans and persist nodes/edges in SQLite.

### 3. Knowledge Graph Traverse Service
- **[NEW] [knowledge_graph.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/services/knowledge_graph.py)**: Implements graph representation of repositories and defines traversal functions to expand file context (e.g. if `Navbar.tsx` is target, automatically traverse imports/exports to pull in `MobileMenu.tsx`, `ThemeContext.tsx`, etc.).

### 4. High-Fidelity Local Embedding & Search Fallback
- Audit Gemini Embedding quota failures. When Gemini API returns `429/RESOURCE_EXHAUSTED`, fall back to a high-fidelity native Python TF-IDF lexical search engine inside [vector_store.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/services/vector_store.py) to score and retrieve codebase chunks deterministically without API request failures.

### 5. Context Pipeline, Test Discovery & Historical Memory
- **[NEW] [test_discovery.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/services/test_discovery.py)**: Scans workspaces to map source code files to matching unit/integration/E2E test files based on standard naming patterns (`test_*.py`, `*.test.ts`, etc.).
- Update [analyzer.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/services/analyzer.py) to store framework profiles (React, Vue, Next.js, Express, FastAPI, Django, Flask, etc.) in the `Repository` record.
- **[NEW] [context_pipeline.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/services/context_pipeline.py)**:
  - Implements the complete Context Assembly pipeline (Semantic Search -> Graph Expansion -> Test Discovery -> Historical Fixes -> Framework Profiling -> Context Bundle).
  - Calculates a **Context Quality Score (0-100)** based on metric weights (Semantic Relevance, Dependency Coverage, Test Coverage, Historical Coverage, Architecture Coverage).
  - Enforces a strict maximum configurable token budget.

### 6. API Endpoints & Frontend Dashboard Redesign
- Expose detailed health stats in `GET /api/v1/repositories/{repo_id}/intelligence` inside [repositories.py](file:///d:/PROJECTS/OpenSource%20Agent%20Project/backend/app/repositories.py).
- Redesign the **Repository Intelligence** page [Intelligence.tsx](file:///d:/PROJECTS/OpenSource%20Agent%20Project/frontend/src/pages/Intelligence.tsx) to render framework profiles, indexed symbol/relation counts, a list of discovered tests, and active memories.
- Update the **Agent Monitor** page [AgentMonitor.tsx](file:///d:/PROJECTS/OpenSource%20Agent%20Project/frontend/src/pages/AgentMonitor.tsx) to query and render the Context Quality Score metrics card.

---

## 🛠️ Verification Plan

### Automated Verification
- Run E2E test triggers using a real repository (e.g. `Hussen---portfolio`) with a target styling or code issue.
- Verify that repository indexing builds the Knowledge Graph, extracts AST symbols, performs TF-IDF fallbacks, maps tests, scores quality metrics, and feeds this structured context bundle directly to the Coding Agent.

### Manual Verification
- Deploy and verify the Repository Intelligence dashboard tab in the browser, checking framework detection details, nodes/edges metrics, and search query results.

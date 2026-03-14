# AGENTS.md

This file provides guidance to Qoder (qoder.com) when working with code in this repository.

## Build & Run Commands

### Quick start (both services)
```bash
./start.sh
```

### Backend (FastAPI, Python 3.12+)
```bash
# Install dependencies (uses uv package manager)
uv sync

# Run server on :8000
uv run python -m server.main

# Or with uvicorn directly from venv
.venv/bin/python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

### Frontend (React 19, Vite 7, TypeScript 5.9)
```bash
cd web
npm install
npm run dev          # Dev server on :5173, proxies /api -> :8000
npm run build        # tsc -b && vite build
npm run lint         # ESLint
```

### Type checking
```bash
cd web && npx tsc --noEmit    # Frontend TypeScript check
```

There is no backend linter or test framework configured yet. No pytest, ruff, or flake8.

## Architecture

This is a modular AI assistant with a **chat-driven LangGraph agent backend** and a **React SPA frontend**. The user chats in a left panel; the right panel renders module-specific UI (charts, tables) triggered by `ui_command` events from the agent.

### Agent Flow (LangGraph)

```
User message -> POST /api/chat/stream (SSE)
  -> LangGraph StateGraph:
       START -> router_node (LLM classifies intent: "stock" | "general")
             -> conditional edge:
                  "stock"   -> stock_agent_node (ReAct loop, max 5 tool calls)
                  "general" -> chat_agent_node  (direct LLM response)
             -> END
  -> SSE events streamed back: progress, ui_command, message, error, done
```

**AgentState** (`server/agent/state.py`): `messages` (accumulated), `intent`, `current_module`, `ui_commands`.

**Progress system** (`server/agent/progress.py`): Uses `contextvars.ContextVar` to pass a `queue.Queue` from the async SSE endpoint into synchronous LangGraph nodes. Nodes call `emit_progress(step, detail)` which the SSE endpoint drains concurrently via `asyncio.to_thread`.

### Plugin Module System

Modules inherit `BaseModule` (`server/modules/base.py`) and implement:
- `get_tools() -> list[BaseTool]` — LangChain tools the agent can call
- `get_system_prompt() -> str` — system prompt for the sub-agent

`ModuleRegistry` (`server/modules/registry.py`) handles discovery, enable/disable, and config persistence. Currently only one module exists: **stock** (Futu API + yfinance).

Stock tools return `_ui_command` dicts in their results. The agent node extracts these into `AgentState.ui_commands`, which the SSE endpoint sends as `event: ui_command` for the frontend to render module-specific views.

### LLM Multi-Provider & Scope Resolution

`server/core/llm.py` provides `create_llm_for_scope(scope, temperature=None)` which:
1. Calls `LLMService.resolve_model_for_scope(scope)` with cascading lookup:
   `module.stock.agent` -> `module.stock` -> `global` -> `.env` fallback
2. Creates the appropriate LangChain chat model based on provider: `deepseek`/`openai`/`qwen` (ChatOpenAI), `anthropic` (ChatAnthropic), `google` (ChatGoogleGenerativeAI)

Scopes used in codebase: `agent.router`, `agent.chat`, `module.stock.agent`, `module.stock.options_wall`, `module.stock.recommendations`.

### Database (SQLite + SQLAlchemy)

Database file: `data/app.db`. Three tables:
- `llm_models` — model definitions with Fernet-encrypted API keys
- `model_assignments` — scope-to-model mappings with temperature overrides
- `module_configs` — module enable/disable state and JSON config

On first startup, `server/db/migration.py` migrates `.env` LLM settings and `data/modules_config.json` into SQLite.

Repository pattern in `server/db/repositories.py`, business logic in `server/db/service.py`. Sessions via `get_session()` context manager in `server/db/session.py`.

### Frontend State Management

Three Zustand stores:
- `chatStore` — messages array, streaming state, `progressMessage`, SSE `sendMessage()` with handlers for progress/ui_command/message/error/done events
- `moduleStore` — tracks active module and action, dispatches `ui_command` to set which module view to render
- `stockStore` — portfolio positions, trend data, options chain, analysis data

`api/client.ts` provides `fetchSSE()` for streaming and `fetchJSON()`/`putJSON()`/`deleteJSON()` for REST calls. Vite proxies `/api` to the backend at `:8000`.

### Key Routes

| Frontend Route | Page |
|---|---|
| `/` | Main chat + module panel (AppLayout) |
| `/admin` | Module management + logs |
| `/admin/models` | LLM model CRUD + scope assignments |
| `/admin/modules/:moduleId` | Individual module config |

| Backend Endpoint | Purpose |
|---|---|
| `POST /api/chat/stream` | SSE chat endpoint |
| `GET/POST/PUT/DELETE /api/admin/llm/models` | Model CRUD |
| `GET/PUT/DELETE /api/admin/llm/assignments` | Scope assignments |
| `GET /api/admin/llm/scopes` | Available scope definitions |
| `GET/PUT /api/admin/modules` | Module list and config |

### Adding a New Module

1. Create `server/modules/<name>/module.py` — subclass `BaseModule`, set `module_id`, implement `get_tools()` and `get_system_prompt()`
2. Create `server/modules/<name>/tools.py` — define `@tool` functions, return `_ui_command` dicts for frontend rendering
3. Register in `server/main.py` lifespan
4. Add a conditional branch in `server/agent/graph.py` for the new intent
5. Add corresponding frontend module view in `web/src/modules/<name>/`
6. Add a new scope like `module.<name>.agent` to `LLMService.get_available_scopes()`

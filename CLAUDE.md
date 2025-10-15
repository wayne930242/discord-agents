# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Discord bot management platform built with FastAPI (backend) and React (frontend). The system allows creating and managing multiple AI-powered Discord bots with different agents, tools, and configurations. It uses Redis for bot state management, PostgreSQL for data persistence, and Google ADK for AI agent functionality.

## Common Commands

### Development Commands

```bash
# Start both backend and frontend (development mode)
python start.py

# Start backend only
python start_dev.py

# Start frontend only (from frontend directory)
cd frontend && pnpm dev

# Build frontend for production
cd frontend && pnpm build
```

### Testing Commands

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test files
python -m pytest tests/test_e2e.py -v              # End-to-end tests
python -m pytest tests/test_tools.py -v            # Tool tests
python -m pytest tests/test_fastapi.py -v          # FastAPI tests
python -m pytest tests/test_token_usage_api.py -v  # Token usage API tests

# Run tests with coverage report
python -m pytest tests/ --cov=discord_agents --cov-report=html
```

### Database Commands

```bash
# Run database migrations (creates tables and applies schema changes)
python migrate.py

# Check database schema
python check_db_schema.py
```

### Production Commands

```bash
# Start with production configuration
python start_prod.py

# Using Docker
docker build -t discord-agents .
docker run -p 8080:8080 --env-file .env discord-agents
```

## High-Level Architecture

### Bot Lifecycle Management (Critical)

The system uses a **Redis-based state machine** for bot lifecycle management, implemented across three key components:

1. **BotRedisClient** (`discord_agents/scheduler/broker.py`): Manages bot states in Redis
   - States: `idle`, `should_start`, `starting`, `running`, `should_stop`, `stopping`, `should_restart`
   - Stores bot init/setup configs in Redis
   - Uses distributed locks (Redlock) to prevent race conditions during state transitions
   - Key methods: `set_should_start()`, `set_should_stop()`, `set_should_restart()`

2. **BotManager** (`discord_agents/scheduler/worker.py`): Singleton that manages bot instances
   - Maintains `_bot_map` (bot_id -> MyBot instance) and `_thread_map` (bot_id -> Thread)
   - Runs a monitor loop every 3 seconds that calls `listen_bots_task()` for each bot
   - Each bot runs in its own thread with its own event loop

3. **listen_bots_task** (`discord_agents/scheduler/tasks.py`): The state machine executor
   - Checks Redis state and takes action:
     - `should_start` + lock → create MyBot, setup agent, add to manager → `running`
     - `should_stop`/`should_restart` + lock → remove from manager → `idle` or restart
   - This is called continuously by BotManager's monitor loop

**Critical flow**: When you update a bot in the database (e.g., via API), you must:
1. Update configs in Redis using `redis_client.set()` with `BOT_INIT_CONFIG_KEY` and `BOT_SETUP_CONFIG_KEY`
2. Set state to `should_restart` using `redis_client.set_should_restart()`
3. The monitor loop will pick this up and restart the bot with new configs

### Agent Message Processing Flow

1. **Message Reception** (`discord_agents/cogs/base_cog.py`):
   - `_on_message()` listener receives Discord messages
   - Checks DM/server whitelists and bot mentions
   - Formats user context info (User ID, Username, Display Names, Channel/Server info)
   - User info is **prepended to every message** sent to the agent

2. **Session Management**:
   - Uses Google ADK's `DatabaseSessionService` for conversation persistence
   - Each user/channel gets a unique session ID stored in Redis
   - Sessions are cached in memory (`self.user_sessions`) for performance
   - `_ensure_session()` creates or retrieves session for each interaction

3. **Agent Invocation** (`discord_agents/utils/call_agent.py`):
   - `stream_agent_responses()` streams responses from Google ADK Agent
   - Enforces rate limiting based on model's `interval_seconds` and `max_tokens`
   - Tracks message history in Redis for rate limiting calculations
   - Returns results incrementally for real-time Discord responses

4. **Token Usage Tracking**:
   - Input/output tokens are counted using tiktoken
   - Recorded to database via `TokenUsageService` after each interaction
   - Linked to agent_id for analytics and cost tracking

### Tool System Architecture

Tools are modular extensions that give agents capabilities. The system is designed for easy tool addition:

1. **Tool Definition** (`discord_agents/domain/tool_def/`):
   - Each tool is a separate file (e.g., `search_tool.py`, `math_tool.py`)
   - Tools use Google ADK patterns: `FunctionTool`, `AgentTool`, or custom implementations
   - Example: `search_tool.py` uses Tavily API for web search

2. **Tool Registry** (`discord_agents/domain/tools.py`):
   - `TOOLS_DICT` maps tool names to tool instances
   - `Tools.get_tools(tool_names)` retrieves tool instances by name
   - Tools are loaded when agent is created based on agent config

3. **Tool Integration**:
   - Tools are passed to Google ADK Agent during initialization
   - Agent automatically handles tool invocation during conversations
   - Tool results are seamlessly integrated into conversation flow

### Database Models and Relationships

- **BotModel** (`discord_agents/models/bot.py`): Stores bot configuration
  - Fields: `token`, `command_prefix`, `dm_whitelist`, `srv_whitelist`, `use_function_map`
  - Has one `AgentModel` (via `agent_id` foreign key)
  - Methods: `bot_id()` returns "bot_{id}", `to_init_config()` and `to_setup_agent_config()` convert to config dicts

- **AgentModel**: Stores agent configuration
  - Fields: `name`, `description`, `role_instructions`, `tool_instructions`, `agent_model`, `tools` (list)
  - One agent can be used by multiple bots
  - Updating an agent triggers restart of all bots using it

- **TokenUsageModel**: Tracks token consumption per agent
  - Fields: `agent_id`, `agent_name`, `model_name`, `input_tokens`, `output_tokens`, `timestamp`
  - Used for cost tracking and usage analytics

### Frontend-Backend Communication

- **API Layer** (`discord_agents/api/`):
  - RESTful endpoints: `/api/v1/bots`, `/api/v1/admin`, `/api/v1/auth`, `/api/v1/token-usage`
  - JWT authentication for protected endpoints
  - CORS configured for frontend origin

- **React Frontend** (`frontend/src/`):
  - Uses TanStack Query for server state management
  - API client in `lib/api.ts` handles all backend communication
  - Pages: Dashboard, BotManagement, AgentManagement, UsageAnalytics

- **Static File Serving**:
  - Production: FastAPI serves built React app from `frontend/dist`
  - Development: Vite dev server on port 5173, FastAPI on port 8080

## Key Development Patterns

### Adding a New Tool

1. Create tool file in `discord_agents/domain/tool_def/my_new_tool.py`:
```python
from google.adk.tools import FunctionTool

def my_function(param: str) -> str:
    """Description of what the tool does"""
    # Implementation
    return result

my_tool = FunctionTool(func=my_function)
```

2. Register in `discord_agents/domain/tools.py`:
```python
TOOLS_DICT = {
    # ... existing tools
    "my_tool": my_tool,
}
```

3. Tool is now available for agents to use via admin interface

### Testing with Mock Google ADK

Tests use comprehensive stub modules since Google ADK has import restrictions:
- Stub modules in `tests/` directory mock Google ADK components
- Use `sys.modules` manipulation to inject stubs before imports
- Example pattern in `tests/test_e2e.py`

### Error Handling Pattern

Use `Result[T, E]` pattern throughout codebase:
```python
from result import Result, Ok, Err

def risky_operation() -> Result[str, str]:
    try:
        # Operation
        return Ok("success")
    except Exception as e:
        return Err(str(e))

# Usage
result = risky_operation()
if result.is_err():
    logger.error(f"Error: {result.err()}")
    return
value = result.ok()
```

### Logging

- Use centralized logger: `logger = get_logger("module_name")`
- Log important state transitions, especially in bot lifecycle
- Include context: `logger.info(f"Bot {bot_id} transitioned to {state}")`

## Configuration Management

### Environment Variables (`.env`)

Required variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `GOOGLE_API_KEY`: For Gemini models
- `TAVILY_API_KEY`: For search tool
- `SECRET_KEY`: For JWT authentication
- `CORS_ORIGINS`: Allowed frontend origins (JSON array)

Configuration is loaded via Pydantic Settings in `discord_agents/core/config.py`.

### LLM Configuration

Models are defined in `discord_agents/domain/agent.py`:
- `LLMs.llm_list`: List of supported models with pricing and restrictions
- Supports Gemini, GPT, Claude, and Grok models via LiteLLM
- Each model has `max_tokens` and `interval_seconds` restrictions

## Important Implementation Notes

1. **Bot State Updates**: Always update Redis configs before changing bot state, or the bot will restart with old configs

2. **Session Management**: User sessions persist across bot restarts via Google ADK's DatabaseSessionService

3. **Thread Safety**: BotManager is a singleton with thread-safe operations using locks

4. **Discord Rate Limits**: Responses are chunked into 2000-character messages to respect Discord limits

5. **Token Counting**: Uses tiktoken for accurate token counting, critical for rate limiting and cost tracking

6. **User Context**: Every agent message automatically includes Discord user info (ID, username, display names, channel/server context)

7. **Clear Sessions Command**: When users clear sessions, it also clears Redis session data and associated notes

8. **Frontend Routing**: FastAPI serves index.html for all non-API routes to support React Router's client-side routing

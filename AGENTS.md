# Discord Agents Project Guide for AI Assistants

This AGENTS.md file provides comprehensive guidance for AI assistants working with this Discord bot codebase.

## Project Overview

This is a Discord bot platform that allows creating and managing multiple AI-powered Discord bots with different agents, tools, and configurations. The system uses Flask for web management, Redis for state management, and Google ADK for AI agent functionality.

## Project Structure for AI Navigation

```
discord-agents/
├── discord_agents/           # Main application package
│   ├── app.py               # Flask application entry point
│   ├── env.py               # Environment configuration
│   ├── cogs/                # Discord bot cogs (commands and event handlers)
│   │   └── base_cog.py      # Main agent cog with Discord interactions
│   ├── domain/              # Core business logic
│   │   ├── agent.py         # MyAgent class and LLM configurations
│   │   ├── bot.py           # MyBot class for Discord bot management
│   │   ├── bot_config.py    # Configuration type definitions
│   │   ├── tools.py         # Tool management system
│   │   └── tool_def/        # Individual tool implementations
│   ├── models/              # Database models
│   │   └── bot.py           # SQLAlchemy models for bots and agents
│   ├── scheduler/           # Background task management
│   │   ├── broker.py        # Redis-based state management
│   │   ├── tasks.py         # Bot lifecycle tasks
│   │   └── worker.py        # Bot execution management
│   ├── utils/               # Utility functions
│   └── view/                # Flask-Admin views
├── tests/                   # Test files
├── prompts/                 # Prompt templates and examples
├── data/                    # Data files
├── logs/                    # Log files
├── migrations/              # Database migrations
└── instance/                # Instance-specific files
```

## Core Architecture for AI Understanding

### 1. Bot Lifecycle Management
- **MyBot** (`discord_agents/domain/bot.py`): Main Discord bot wrapper
- **BotManager** (`discord_agents/scheduler/worker.py`): Manages multiple bot instances
- **BotRedisClient** (`discord_agents/scheduler/broker.py`): Redis-based state management

### 2. Agent System
- **MyAgent** (`discord_agents/domain/agent.py`): AI agent wrapper for Google ADK
- **AgentCog** (`discord_agents/cogs/base_cog.py`): Discord command handler with agent integration
- **Tools** (`discord_agents/domain/tools.py`): Tool management and loading system

### 3. Database Models
- **BotModel**: Stores bot configuration (token, prefixes, whitelists)
- **AgentModel**: Stores agent configuration (name, instructions, model, tools)

## Coding Conventions for AI Assistants

### General Conventions
- Use Python 3.13+ with type hints for all new code
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings for classes and complex functions
- Use `Result[T, E]` pattern for error handling where appropriate

### Import Organization
```python
# Standard library imports
import os
import sys
from typing import Optional, List, Dict

# Third-party imports
import discord
from flask import Flask
from redis import Redis

# Local imports
from discord_agents.domain.bot import MyBot
from discord_agents.utils.logger import get_logger
```

### Logging Standards
- Use the centralized logger: `logger = get_logger("module_name")`
- Log levels: INFO for normal operations, ERROR for exceptions, DEBUG for detailed tracing
- Include context in log messages: `logger.info(f"Bot {bot_id} started successfully")`

### Configuration Management
- Environment variables are managed in `discord_agents/env.py`
- Use TypedDict for configuration structures (see `bot_config.py`)
- Validate configuration before use

## Tool Development Guidelines for AI Assistants

### Creating New Tools
1. Create a new file in `discord_agents/domain/tool_def/`
2. Implement using Google ADK patterns:
   ```python
   from google.adk.tools import FunctionTool
   from google.adk.tools.agent_tool import AgentTool

   def my_function(param: str) -> str:
       """Tool function implementation"""
       return result

   my_tool = FunctionTool(func=my_function)
   ```
3. Register in `discord_agents/domain/tools.py` TOOLS_DICT
4. Add to database choices in admin interface

### Available Tools
- `search`: Web search functionality
- `life_env`: Life environment generator with dice rolling
- `rpg_dice`: RPG dice rolling tool
- `content_extractor`: Web content extraction and summarization
- `summarizer`: Text summarization
- `math`: Mathematical calculations
- `notes`: Note-taking and retrieval system

## Testing Requirements for AI Assistants

### Running Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_e2e.py -v          # End-to-end tests
python -m pytest tests/test_tools.py -v        # Tool tests
python -m pytest tests/test_content_extractor_tool.py -v  # Content extractor tests

# Run with coverage
python -m pytest tests/ --cov=discord_agents --cov-report=html
```

### Test Structure
- **E2E Tests** (`tests/test_e2e.py`): Complete system integration tests
- **Unit Tests** (`tests/test_tools.py`): Individual component tests
- **Tool Tests** (`tests/test_content_extractor_tool.py`): Specific tool functionality tests

### Mock Requirements
- Use comprehensive stub modules for `google.adk` dependencies in tests
- Mock external services (Redis, databases) for unit tests
- Include proper cleanup in test teardown methods

## Database Operations for AI Assistants

### Database Setup
```bash
# Initialize database
python manage.py db init

# Create migration
python manage.py db migrate -m "Description"

# Apply migration
python manage.py db upgrade
```

### Model Relationships
- `BotModel` has one `AgentModel` (one-to-one relationship)
- Use `bot.to_init_config()` and `bot.to_setup_agent_config()` for configuration conversion
- Access agent through `bot.agent.name`, `bot.agent.tools`, etc.

## Bot Management for AI Assistants

### Bot States (Redis-managed)
- `idle`: Bot is stopped
- `should_start`: Bot should be started
- `starting`: Bot is in startup process
- `running`: Bot is active
- `should_stop`: Bot should be stopped
- `stopping`: Bot is in shutdown process
- `should_restart`: Bot should be restarted

### Bot Operations
```python
# Start a bot
redis_broker.set_should_start(bot_id, init_config, setup_config)

# Stop a bot
redis_broker.set_should_stop(bot_id)

# Check bot state
state = redis_broker.get_state(bot_id)
```

## Development Workflow for AI Assistants

### Adding New Features
1. Create feature branch from `develop`
2. Implement changes following coding conventions
3. Add comprehensive tests
4. Update documentation if needed
5. Ensure all tests pass: `python -m pytest tests/ -v`
6. Create pull request to `develop` branch

### Environment Setup
```bash
# Install dependencies
pip install -e .

# Set up environment variables (copy from .env.example)
cp .env.example .env

# Run database migrations
python manage.py db upgrade

# Start development server
python manage.py run
```

### Common Development Tasks
```bash
# Start Flask development server
python manage.py run

# Access admin interface
# Navigate to http://localhost:5000/admin

# Monitor logs
tail -f logs/app.log

# Check Redis state
redis-cli -u $REDIS_URL
```

## Error Handling Patterns for AI Assistants

### Result Pattern Usage
```python
from result import Result, Ok, Err

def risky_operation() -> Result[str, str]:
    try:
        # Operation that might fail
        return Ok("success")
    except Exception as e:
        return Err(str(e))

# Usage
result = risky_operation()
if result.is_ok():
    value = result.ok()
else:
    error = result.err()
```

### Exception Handling
- Catch specific exceptions when possible
- Log errors with context and stack traces
- Use graceful degradation for non-critical failures
- Return meaningful error messages to users

## Security Considerations for AI Assistants

### Bot Token Management
- Store tokens securely in environment variables
- Never log or expose bot tokens
- Use token validation before bot startup

### Access Control
- Implement DM and server whitelists
- Use Flask-Admin authentication for web interface
- Validate user permissions before executing commands

### Input Validation
- Sanitize all user inputs
- Validate configuration data before storage
- Use type checking and validation decorators

## Performance Guidelines for AI Assistants

### Redis Usage
- Use connection pooling for Redis operations
- Implement proper key expiration for temporary data
- Use Redis transactions for atomic operations

### Bot Management
- Limit concurrent bot instances based on system resources
- Implement proper cleanup for stopped bots
- Monitor memory usage and implement limits

### Database Optimization
- Use database indexes for frequently queried fields
- Implement connection pooling
- Use lazy loading for relationships when appropriate

## Deployment Considerations for AI Assistants

### Production Setup
- Use environment-specific configuration
- Implement proper logging and monitoring
- Use process managers (supervisor, systemd) for bot processes
- Set up Redis persistence and backup

### Scaling
- Consider horizontal scaling for multiple bot instances
- Use load balancing for web interface
- Implement distributed locking for bot state management

## Troubleshooting Guide for AI Assistants

### Common Issues
1. **Bot won't start**: Check token validity and permissions
2. **Redis connection errors**: Verify Redis URL and connectivity
3. **Database errors**: Check migration status and connection
4. **Tool loading failures**: Verify tool registration in TOOLS_DICT
5. **Import errors**: Check stub modules in test environment

### Debug Commands
```bash
# Check bot status
python -c "from discord_agents.scheduler.broker import BotRedisClient; print(BotRedisClient().get_all_bot_status())"

# Test database connection
python -c "from discord_agents.models.bot import BotModel; print(BotModel.query.count())"

# Verify tool loading
python -c "from discord_agents.domain.tools import Tools; print(Tools.get_tool_names())"
```

This AGENTS.md file should help AI assistants understand the codebase structure, follow proper conventions, and contribute effectively to the Discord bot platform development.

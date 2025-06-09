# Discord Agents Project Guide for AI Assistants

This AGENTS.md file provides comprehensive guidance for AI assistants working with this Discord bot management system codebase.

## Project Overview

This is a modern Discord bot management platform built with FastAPI + React architecture that allows creating and managing multiple AI-powered Discord bots with different agents, tools, and configurations. The system uses FastAPI for the backend API, React for the web management interface, Redis for state management, and Google ADK for AI agent functionality.

## Project Structure for AI Navigation

```
discord-agents/
├── discord_agents/           # Main application package
│   ├── fastapi_main.py       # FastAPI application entry point
│   ├── api/                  # API routes and endpoints
│   │   ├── auth.py           # Authentication endpoints
│   │   ├── bots.py           # Bot management endpoints
│   │   ├── admin.py          # Admin endpoints
│   │   └── health.py         # Health check endpoints
│   ├── core/                 # Core application functionality
│   │   ├── config.py         # Application configuration
│   │   ├── database.py       # Database connections and setup
│   │   ├── security.py       # Security functions (JWT, password hashing)
│   │   └── migration.py      # Automatic database migrations
│   ├── models/               # SQLAlchemy database models
│   │   └── bot.py            # Bot and Agent models
│   ├── schemas/              # Pydantic models for API validation
│   ├── services/             # Business logic services
│   ├── domain/               # Core business logic
│   │   ├── agent.py          # MyAgent class and LLM configurations
│   │   ├── bot.py            # MyBot class for Discord bot management
│   │   ├── bot_config.py     # Configuration type definitions
│   │   ├── tools.py          # Tool management system
│   │   └── tool_def/         # Individual tool implementations
│   ├── scheduler/            # Background task management
│   │   ├── broker.py         # Redis-based state management
│   │   ├── tasks.py          # Bot lifecycle tasks
│   │   └── worker.py         # Bot execution management
│   ├── cogs/                 # Discord bot cogs (commands and event handlers)
│   │   └── base_cog.py       # Main agent cog with Discord interactions
│   └── utils/                # Utility functions and helpers
├── frontend/                 # React frontend application
│   ├── src/
│   │   ├── components/       # React components
│   │   │   └── ui/           # Reusable UI components
│   │   ├── pages/            # Page components
│   │   ├── lib/              # Frontend utility functions
│   │   └── assets/           # Static assets
│   ├── package.json          # Frontend dependencies
│   ├── vite.config.ts        # Vite build configuration
│   └── tailwind.config.js    # Tailwind CSS configuration
├── tests/                    # Test files
├── migrations/               # Database migration files
├── prompts/                  # Prompt templates and examples
├── data/                     # Data files
├── logs/                     # Log files
└── instance/                 # Instance-specific files
```

## Core Architecture for AI Understanding

### 1. Backend Architecture (FastAPI)
- **FastAPI Application** (`discord_agents/fastapi_main.py`): Main application entry point with lifespan management
- **API Routes** (`discord_agents/api/`): RESTful endpoints for bot management, authentication, and admin functions
- **Database Layer** (`discord_agents/core/database.py`): SQLAlchemy ORM with PostgreSQL
- **Security Layer** (`discord_agents/core/security.py`): JWT authentication and password hashing

### 2. Frontend Architecture (React)
- **React 19 + TypeScript**: Modern frontend framework with type safety
- **Vite**: Fast build tool and development server
- **Tailwind CSS**: Utility-first CSS framework
- **Radix UI**: Accessible UI component library
- **TanStack Query**: Server state management
- **React Hook Form**: Form handling with validation

### 3. Bot Management System
- **MyBot** (`discord_agents/domain/bot.py`): Main Discord bot wrapper
- **BotManager** (`discord_agents/scheduler/worker.py`): Manages multiple bot instances
- **BotRedisClient** (`discord_agents/scheduler/broker.py`): Redis-based state management

### 4. Agent System
- **MyAgent** (`discord_agents/domain/agent.py`): AI agent wrapper for Google ADK
- **AgentCog** (`discord_agents/cogs/base_cog.py`): Discord command handler with agent integration
- **Tools** (`discord_agents/domain/tools.py`): Tool management and loading system

### 5. Database Models
- **BotModel**: Stores bot configuration (token, prefixes, whitelists)
- **AgentModel**: Stores agent configuration (name, instructions, model, tools)

## Technology Stack for AI Understanding

### Backend Technologies
- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: Python SQL toolkit and ORM
- **Alembic**: Database migration tool
- **Redis**: In-memory data structure store for state management
- **Pydantic**: Data validation using Python type annotations
- **Discord.py**: Python library for Discord API
- **Google ADK**: Google's Agent Development Kit for AI functionality

### Frontend Technologies
- **React 19**: Latest version with improved hooks and concurrent features
- **TypeScript**: Typed superset of JavaScript
- **Vite**: Next generation frontend tooling
- **Tailwind CSS**: Utility-first CSS framework
- **Radix UI**: Low-level UI primitives
- **TanStack Query**: Powerful data synchronization for React
- **React Hook Form**: Performant forms with easy validation

## Coding Conventions for AI Assistants

### General Conventions
- Use Python 3.13+ with type hints for all new backend code
- Use TypeScript for all frontend code
- Follow PEP 8 style guidelines for Python
- Use ESLint and Prettier for frontend code formatting
- Use meaningful variable and function names
- Add docstrings for classes and complex functions
- Use `Result[T, E]` pattern for error handling where appropriate

### Backend Import Organization
```python
# Standard library imports
import os
import sys
from typing import Optional, List, Dict

# Third-party imports
import discord
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from redis import Redis

# Local imports
from discord_agents.domain.bot import MyBot
from discord_agents.core.database import get_db
from discord_agents.utils.logger import get_logger
```

### Frontend Import Organization
```typescript
// React and hooks
import React, { useState, useEffect } from 'react';

// Third-party libraries
import { useQuery } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';

// UI components
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

// Local utilities and types
import { BotService } from '@/lib/api';
import type { Bot } from '@/lib/types';
```

### Logging Standards
- Use the centralized logger: `logger = get_logger("module_name")`
- Log levels: INFO for normal operations, ERROR for exceptions, DEBUG for detailed tracing
- Include context in log messages: `logger.info(f"Bot {bot_id} started successfully")`

### Configuration Management
- Environment variables are managed in `discord_agents/core/config.py`
- Use Pydantic Settings for configuration validation
- Use TypedDict for configuration structures (see `bot_config.py`)
- Validate configuration before use

## API Development Guidelines for AI Assistants

### Creating New API Endpoints
1. Define Pydantic schemas in `discord_agents/schemas/`
2. Create route handlers in appropriate files in `discord_agents/api/`
3. Use dependency injection for database sessions and authentication
4. Follow RESTful conventions for URL design
5. Add proper error handling and status codes

### Example API Endpoint
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from discord_agents.core.database import get_db
from discord_agents.schemas.bot import BotCreate, BotResponse
from discord_agents.services.bot_service import BotService

router = APIRouter()

@router.post("/", response_model=BotResponse)
async def create_bot(
    bot_data: BotCreate,
    db: Session = Depends(get_db)
):
    """Create a new Discord bot"""
    try:
        bot = BotService.create_bot(db, bot_data)
        return bot
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

## Frontend Development Guidelines for AI Assistants

### Creating New Components
1. Use TypeScript for all components
2. Follow the compound component pattern for complex UI
3. Use React Hook Form for form handling
4. Use TanStack Query for server state management
5. Implement proper loading and error states

### Example React Component
```typescript
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BotService } from '@/lib/api';

interface BotListProps {
  onBotSelect: (botId: string) => void;
}

export function BotList({ onBotSelect }: BotListProps) {
  const { data: bots, isLoading, error } = useQuery({
    queryKey: ['bots'],
    queryFn: BotService.getBots
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div className="grid gap-4">
      {bots?.map((bot) => (
        <Card key={bot.id} onClick={() => onBotSelect(bot.id)}>
          <CardHeader>
            <CardTitle>{bot.name}</CardTitle>
          </CardHeader>
          <CardContent>
            <p>Status: {bot.status}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
```

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
- `search`: Web search functionality using Tavily API
- `life_env`: Life environment generator with dice rolling
- `rpg_dice`: RPG dice rolling tool
- `content_extractor`: Web content extraction and summarization using Crawl4AI
- `summarizer`: Text summarization
- `math`: Mathematical calculations using numexpr
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

### Frontend Testing
```bash
cd frontend
pnpm test       # Run Jest tests
pnpm test:e2e   # Run Playwright E2E tests (if configured)
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
# Run migrations
python migrate.py

# Check database schema
python check_db_schema.py
```

### Model Relationships
- `BotModel` has one `AgentModel` (one-to-one relationship)
- Use `bot.to_init_config()` and `bot.to_setup_agent_config()` for configuration conversion
- Access agent through `bot.agent.name`, `bot.agent.tools`, etc.

### Adding New Models
1. Create model in `discord_agents/models/`
2. Add to `__init__.py` for imports
3. Create Alembic migration: `alembic revision --autogenerate -m "Description"`
4. Apply migration: `alembic upgrade head`

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
1. Create feature branch from `main`
2. Implement changes following coding conventions
3. Add comprehensive tests (both backend and frontend if applicable)
4. Update documentation if needed
5. Ensure all tests pass: `python -m pytest tests/ -v`
6. Test frontend if changes affect UI: `cd frontend && pnpm build`
7. Create pull request

### Environment Setup
```bash
# Backend setup
uv sync
cp .env.example .env
# Edit .env with your configuration

# Frontend setup
cd frontend
pnpm install
cd ..

# Database setup
python migrate.py

# Start development servers
python start.py  # Starts both backend and frontend
```

### Common Development Tasks
```bash
# Start backend only
python start_dev.py

# Start frontend only
cd frontend && pnpm dev

# Build frontend for production
cd frontend && pnpm build

# Run database migrations
python migrate.py

# Check database schema
python check_db_schema.py

# Monitor logs
tail -f logs/app.log

# Check Redis state
redis-cli -u $REDIS_URL
```

## Error Handling Patterns for AI Assistants

### Backend Error Handling
```python
from fastapi import HTTPException
from result import Result, Ok, Err

def risky_operation() -> Result[str, str]:
    try:
        # Operation that might fail
        return Ok("success")
    except Exception as e:
        return Err(str(e))

# In API endpoints
@router.get("/")
async def get_data():
    result = risky_operation()
    if result.is_err():
        raise HTTPException(status_code=500, detail=result.err())
    return result.ok()
```

### Frontend Error Handling
```typescript
import { useQuery } from '@tanstack/react-query';

function MyComponent() {
  const { data, error, isLoading } = useQuery({
    queryKey: ['data'],
    queryFn: fetchData,
    retry: 3,
    retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000)
  });

  if (error) {
    return <ErrorComponent error={error} />;
  }

  // ... rest of component
}
```

## Security Considerations for AI Assistants

### Backend Security
- Use JWT tokens for API authentication
- Implement proper CORS configuration
- Validate all input data using Pydantic models
- Use password hashing for user credentials
- Implement rate limiting for API endpoints

### Frontend Security
- Store JWT tokens securely (httpOnly cookies preferred)
- Validate user input on both client and server side
- Implement proper error boundaries
- Use HTTPS in production

### Bot Token Management
- Store tokens securely in environment variables
- Never log or expose bot tokens
- Use token validation before bot startup
- Implement token rotation if needed

## Performance Guidelines for AI Assistants

### Backend Performance
- Use async/await for I/O operations
- Implement database connection pooling
- Use Redis for caching frequently accessed data
- Implement proper pagination for large datasets

### Frontend Performance
- Use React.lazy() for code splitting
- Implement proper memoization with useMemo and useCallback
- Use TanStack Query for efficient data fetching and caching
- Optimize bundle size with tree shaking

### Redis Usage
- Use connection pooling for Redis operations
- Implement proper key expiration for temporary data
- Use Redis transactions for atomic operations

## Deployment Considerations for AI Assistants

### Production Setup
- Use environment-specific configuration
- Implement proper logging and monitoring
- Use process managers (supervisor, systemd) for bot processes
- Set up Redis persistence and backup
- Configure reverse proxy (nginx) for static file serving

### Docker Deployment
```bash
# Build and run with Docker
docker build -t discord-agents .
docker run -p 8080:8080 --env-file .env discord-agents

# Or use docker-compose for full stack
docker-compose up -d
```

### Scaling Considerations
- Consider horizontal scaling for multiple bot instances
- Use load balancing for web interface
- Implement distributed locking for bot state management
- Use database read replicas for heavy read workloads

## Troubleshooting Guide for AI Assistants

### Common Issues
1. **Bot won't start**: Check token validity and permissions
2. **Redis connection errors**: Verify Redis URL and connectivity
3. **Database errors**: Check migration status and connection
4. **Frontend build errors**: Check Node.js version and dependencies
5. **Tool loading failures**: Verify tool registration in TOOLS_DICT
6. **Import errors**: Check stub modules in test environment

### Debug Commands
```bash
# Backend debugging
python -c "from discord_agents.scheduler.broker import BotRedisClient; print(BotRedisClient().get_all_bot_status())"
python -c "from discord_agents.models.bot import BotModel; print(BotModel.query.count())"
python -c "from discord_agents.domain.tools import Tools; print(Tools.get_tool_names())"

# Frontend debugging
cd frontend
pnpm build  # Check for build errors
pnpm lint   # Check for linting issues
```

### Logging and Monitoring
- Check application logs in `logs/` directory
- Monitor Redis state using Redis CLI
- Use database query logging for performance debugging
- Implement health checks for all services

This AGENTS.md file should help AI assistants understand the modern FastAPI + React codebase structure, follow proper conventions, and contribute effectively to the Discord bot management platform development.

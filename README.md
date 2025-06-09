# Discord Agents

A modern Discord bot management system built with FastAPI + React architecture, supporting multiple bot management and AI agent functionality.

## 🚀 Features

- 🤖 **Multi-Bot Support** - Create and manage multiple Discord bots
- 🧠 **AI Agent Integration** - Intelligent agent system based on Google ADK
- 🌐 **Modern Web UI** - React + TypeScript + Tailwind CSS management interface
- 🗄️ **PostgreSQL Database** - Persistent storage for bot configurations and data
- ⚡ **Redis-based State Management** - Real-time bot lifecycle management
- 🛠️ **Rich Tool Ecosystem** - Search, content extraction, math, notes, and more
- 🔄 **Real-time State Monitoring** - Live bot status monitoring and management
- 🧪 **Comprehensive Testing Suite** - End-to-end testing system
- 🔐 **Secure Authentication** - JWT-based authentication system
- 📊 **Modern API** - RESTful API design with OpenAPI documentation

## 📋 Prerequisites

- Python 3.13 or higher
- PostgreSQL 15+
- Redis 7+
- Node.js 20+ and pnpm
- uv (Python package manager)

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/discord-agents.git
cd discord-agents
```

### 2. Backend Setup

```bash
# Install dependencies using uv
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env with required configurations
```

### 3. Frontend Setup

```bash
cd frontend
pnpm install
cd ..
```

### 4. Database Setup

```bash
# Run database migrations
python migrate.py
```

### 5. Environment Configuration

Create a `.env` file in the root directory with the following required variables:

```env
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/discord_agents

# Redis
REDIS_URL=redis://localhost:6379/0

# API Keys
GOOGLE_API_KEY=your_google_api_key
TAVILY_API_KEY=your_tavily_api_key

# Security Settings
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS Settings
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

## 🚀 Running the Application

### Development Mode

```bash
# Start both backend and frontend
python start.py

# Or start separately
python start_dev.py  # Backend only
cd frontend && pnpm dev  # Frontend only
```

### Production Mode

```bash
# Start with production configuration
python start_prod.py
```

### Using Docker

```bash
# Build image
docker build -t discord-agents .

# Run container
docker run -p 8080:8080 --env-file .env discord-agents
```

## 🌐 Access Points

After startup, you can access the application at:

- **Main Application**: http://localhost:8080
- **API Documentation**: http://localhost:8080/api/docs
- **Development Frontend**: http://localhost:5173 (development mode only)

## 🏗️ Project Architecture

### Technology Stack

**Backend**:
- FastAPI (Web framework)
- SQLAlchemy (ORM)
- Alembic (Database migrations)
- Redis (State management)
- Google ADK (AI agents)
- Discord.py (Discord integration)

**Frontend**:
- React 19 + TypeScript
- Vite (Build tool)
- Tailwind CSS (Styling framework)
- Radix UI (UI components)
- TanStack Query (State management)
- React Hook Form (Form handling)

### Directory Structure

```
discord-agents/
├── discord_agents/          # Main application package
│   ├── fastapi_main.py      # FastAPI application entry point
│   ├── api/                 # API routes
│   │   ├── auth.py          # Authentication API
│   │   ├── bots.py          # Bot management API
│   │   ├── admin.py         # Admin API
│   │   └── health.py        # Health check API
│   ├── core/                # Core functionality
│   │   ├── config.py        # Application configuration
│   │   ├── database.py      # Database connections
│   │   ├── security.py      # Security-related functions
│   │   └── migration.py     # Auto migrations
│   ├── models/              # Database models
│   ├── schemas/             # Pydantic models
│   ├── services/            # Business logic services
│   ├── domain/              # Domain logic
│   │   ├── agent.py         # AI agent definitions
│   │   ├── bot.py           # Discord bot management
│   │   ├── tools.py         # Tool registry
│   │   └── tool_def/        # Individual tool implementations
│   ├── scheduler/           # Bot scheduling and management
│   │   ├── worker.py        # Bot manager
│   │   ├── broker.py        # Redis state management
│   │   └── tasks.py         # Background tasks
│   ├── cogs/                # Discord bot cogs
│   └── utils/               # Utility functions
├── frontend/                # React frontend application
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   ├── lib/             # Utility functions
│   │   └── assets/          # Static assets
│   ├── package.json         # Frontend dependencies
│   └── vite.config.ts       # Vite configuration
├── tests/                   # Test files
├── migrations/              # Database migration files
├── prompts/                 # AI prompt templates
├── logs/                    # Log files
└── data/                    # Data files
```

## 🛠️ Available Tools

The system includes the following built-in tools:

1. **Search Tool** (`search`) - Web search functionality
2. **Life Environment Tool** (`life_env`) - Life simulation and advice
3. **RPG Dice Tool** (`rpg_dice`) - Game dice functionality
4. **Content Extractor Tool** (`content_extractor`) - Web content extraction and analysis
5. **Summarizer Tool** (`summarizer`) - Text summarization
6. **Math Tool** (`math`) - Mathematical calculations
7. **Notes Tool** (`notes`) - Note-taking and management

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific tests
python -m pytest tests/test_e2e.py -v          # End-to-end tests
python -m pytest tests/test_tools.py -v        # Tool tests

# Run tests with coverage report
python -m pytest tests/ --cov=discord_agents --cov-report=html
```

### Test Prerequisites

Ensure PostgreSQL and Redis services are running:

```bash
# Start PostgreSQL (macOS example)
brew services start postgresql

# Start Redis (macOS example)
brew services start redis
```

## 🐳 Docker Deployment

### Build and Run

```bash
# Build image
docker build -t discord-agents .

# Run container
docker run -d \
  --name discord-agents \
  -p 8080:8080 \
  --env-file .env \
  discord-agents
```

### Docker Compose (Recommended)

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/discord_agents
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=discord_agents
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## 📝 Development Guide

### Adding New Tools

1. Create a new tool file in `discord_agents/domain/tool_def/`
2. Implement the tool following existing patterns
3. Register the tool in `discord_agents/domain/tools.py`
4. Add tests for the new tool

### API Development

- API routes are defined in the `discord_agents/api/` directory
- Use Pydantic models for data validation
- Follow RESTful API design principles

### Frontend Development

```bash
cd frontend
pnpm dev  # Start development server
pnpm build  # Build for production
pnpm lint  # Run code linting
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

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

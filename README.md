# Discord Agents

A Discord bot powered by Google's Generative AI, built with Python and Flask.

## Features

- 🤖 Support multiple Discord bots
- 🧠 Google ADK for intelligent agents
- 🌐 Web GUI for administration
- 🗄️ PostgreSQL database for storing bot configurations
- ⚡ Custom bot management system with thread-based scheduling using Redis
- 🛠️ Rich tool ecosystem (search, content extraction, math, notes, etc.)
- 🔄 Real-time bot lifecycle management
- 🧪 Comprehensive testing suite with E2E tests

## Prerequisites

- Python 3.13 or higher
- PostgreSQL
- Redis

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/discord-agents.git
cd discord-agents
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies using uv:
```bash
uv sync
```

4. Set up environment variables:

Create a `.env` file in the root directory.

Required variables:
- DATABASE_URL （PostgreSQL）
- GOOGLE_API_KEY
- TAVILY_API_KEY
- REDIS_URL

## Running the Application

### Local Development

```bash
python discord_agents/main.py
```

### Using Docker

1. Build the Docker image:
```bash
docker build -t discord-agents .
```

2. Run the container:
```bash
docker run -p 8080:8080 discord-agents
```

## Dashboard

Just visit the port 8080 (or the port you set), and you will see the dashboard.

## Testing

### Running Tests

Run all tests:
```bash
pytest
```

Run specific test files:
```bash
# Unit tests
pytest tests/test_tools.py -v
pytest tests/test_content_extractor_tool.py -v

# End-to-End tests
pytest tests/test_e2e.py -v
```

### End-to-End Testing

The project includes comprehensive E2E tests that verify the entire system functionality:

```bash
# Run E2E tests with detailed output
python tests/test_e2e.py
```

The E2E test suite covers:
- ✅ Flask application health check
- ✅ Database connectivity and data integrity
- ✅ Redis connection and operations
- ✅ Admin interface authentication
- ✅ Bot management interface
- ✅ Bot configuration interface
- ✅ Bot state management
- ✅ Tool integration (7 tools available)
- ✅ Agent configuration
- ✅ Session management
- ✅ Bot lifecycle simulation
- ✅ Error handling
- ✅ System integration

### Prerequisites for Testing

Make sure your database and Redis are running before executing E2E tests:

```bash
# Start PostgreSQL (example)
brew services start postgresql

# Start Redis (example)
brew services start redis
```

## Architecture

### System Components

- **Flask Web Application**: Admin interface and API endpoints
- **Discord Bot Manager**: Handles multiple bot instances
- **Redis Broker**: State management and session storage
- **PostgreSQL Database**: Bot configurations and persistent data
- **Tool System**: Modular tools for various functionalities
- **Agent System**: AI-powered conversation handling

### Available Tools

1. **Search Tool**: Web search capabilities
2. **Life Environment Tool**: Life simulation and advice
3. **RPG Dice Tool**: Dice rolling for games
4. **Content Extractor Tool**: Web content extraction and analysis
5. **Summarizer Tool**: Text summarization
6. **Math Tool**: Mathematical calculations
7. **Notes Tool**: Note-taking and management

## Development

### Project Structure

```
discord-agents/
├── discord_agents/          # Main application package
│   ├── app.py              # Flask application factory
│   ├── domain/             # Business logic
│   │   ├── agent.py        # Agent definitions
│   │   ├── bot.py          # Bot management
│   │   ├── tools.py        # Tool registry
│   │   └── tool_def/       # Individual tool implementations
│   ├── models/             # Database models
│   ├── scheduler/          # Bot scheduling and management
│   ├── utils/              # Utility functions
│   └── view/               # Web interface views
├── tests/                  # Test suite
│   ├── test_tools.py       # Tool tests
│   ├── test_content_extractor_tool.py  # Content extractor tests
│   └── test_e2e.py         # End-to-end tests
├── migrations/             # Database migrations
└── prompts/                # AI prompts and templates
```

### Adding New Tools

1. Create a new tool file in `discord_agents/domain/tool_def/`
2. Implement the tool following existing patterns
3. Register the tool in `discord_agents/domain/tools.py`
4. Add tests for the new tool

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Run the test suite to ensure everything works
5. Submit a pull request

# Discord Agents

A Discord bot powered by Google's Generative AI, built with Python and Flask.

## Features

- Discord bot integration with Google's Generative AI
- Flask-based web interface for administration
- PostgreSQL database support
- Docker containerization
- Custom bot management system with thread-based scheduling

## Prerequisites

- Python 3.13 or higher
- PostgreSQL database
- Google Cloud credentials
- Discord bot token

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

Create a `.env` file in the root directory with the following variables:

```env
GOOGLE_API_KEY=
AGENT_MODEL=gemini-2.5-flash-preview-04-17

TAVILY_API_KEY=

DATABASE_URL=your_postgresql_connection_string

ADMIN_USERNAME=
ADMIN_PASSWORD=

SECRET_KEY=

DM_ID_WHITE_LIST=
SERVER_ID_WHITE_LIST=
```

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

## Dependencies

- discord.py - Discord bot framework
- Flask - Web framework
- Google Cloud AI Platform - AI services
- PostgreSQL - Database
- And more (see pyproject.toml for complete list)

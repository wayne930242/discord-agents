# Discord Agents

A Discord bot powered by Google's Generative AI, built with Python and Flask.

## Features

- Support multiple Discord bots
- Google ADK for agents
- A web GUI for administration
- PostgreSQL database for storing bot configurations
- Custom bot management system with thread-based scheduling with Redis

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

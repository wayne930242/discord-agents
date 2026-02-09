from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from discord_agents.core.database import get_db
from discord_agents.core.security import get_current_user
from discord_agents.models.bot import AgentModel
from discord_agents.schemas.bot import (
    Bot,
    BotCreate,
    BotUpdate,
    Agent,
    AgentCreate,
    AgentUpdate,
)
from discord_agents.services.bot_service import BotService, AgentService
from discord_agents.scheduler.worker import bot_manager

router = APIRouter()


# Bot endpoints
@router.get("/", response_model=List[Bot])
async def get_bots(
    db: Session = Depends(get_db), current_user: str = Depends(get_current_user)
) -> List[Bot]:
    """Get all bots"""
    bots = BotService.get_bots(db)
    return [Bot.model_validate(bot) for bot in bots]


@router.get("/status")
async def get_all_bot_status(
    current_user: str = Depends(get_current_user),
) -> dict[str, str]:
    """Get status of all bots"""
    try:
        from discord_agents.scheduler.broker import BotRedisClient

        redis_client = BotRedisClient()
        return redis_client.get_all_bot_status()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get bot status: {str(e)}",
        )


@router.get("/queues")
async def get_all_bot_queue_metrics(
    current_user: str = Depends(get_current_user),
) -> dict[str, dict[str, object]]:
    """Get pending queue metrics for each running bot and channel."""
    return bot_manager.get_all_queue_metrics()


@router.post("/start-all")
async def start_all_bots(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> dict[str, int]:
    """Start all bots"""
    result = BotService.start_all_bots(db)
    return result


@router.get("/{bot_id}", response_model=Bot)
async def get_bot(
    bot_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> Bot:
    """Get a specific bot"""
    bot = BotService.get_bot(db, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return Bot.model_validate(bot)


@router.post("/", response_model=Bot)
async def create_bot(
    bot: BotCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> Bot:
    """Create a new bot"""
    db_bot = BotService.create_bot(db, bot)
    return Bot.model_validate(db_bot)


@router.put("/{bot_id}", response_model=Bot)
async def update_bot(
    bot_id: int,
    bot_update: BotUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> Bot:
    """Update a bot"""
    db_bot = BotService.update_bot(db, bot_id, bot_update)
    if not db_bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return Bot.model_validate(db_bot)


@router.delete("/{bot_id}")
async def delete_bot(
    bot_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a bot"""
    success = BotService.delete_bot(db, bot_id)
    if not success:
        raise HTTPException(status_code=404, detail="Bot not found")
    return {"message": "Bot deleted successfully"}


@router.post("/{bot_id}/start")
async def start_bot(
    bot_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> dict[str, str]:
    """Start a bot"""
    success = BotService.start_bot(db, bot_id)
    if not success:
        raise HTTPException(status_code=404, detail="Bot not found or failed to start")
    return {"message": "Bot started successfully"}


@router.post("/{bot_id}/stop")
async def stop_bot(
    bot_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> dict[str, str]:
    """Stop a bot"""
    success = BotService.stop_bot(db, bot_id)
    if not success:
        raise HTTPException(status_code=404, detail="Bot not found or failed to stop")
    return {"message": "Bot stopped successfully"}


# Agent endpoints
@router.get("/agents/", response_model=List[Agent])
async def get_agents(
    db: Session = Depends(get_db), current_user: str = Depends(get_current_user)
) -> List[Agent]:
    """Get all agents"""
    agents = AgentService.get_agents(db)
    return [Agent.model_validate(agent) for agent in agents]


@router.get("/tools/")
async def get_available_tools(
    current_user: str = Depends(get_current_user),
) -> dict[str, list[str]]:
    """Get available tools and models"""
    from discord_agents.domain.tools import Tools
    from discord_agents.domain.agent import LLMs

    return {"tools": Tools.get_tool_names(), "models": LLMs.get_model_names()}


@router.post("/agents/", response_model=Agent)
async def create_agent(
    agent: AgentCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> Agent:
    """Create a new agent"""
    db_agent = AgentService.create_agent(db, agent)
    return Agent.model_validate(db_agent)


@router.put("/agents/{agent_id}", response_model=Agent)
async def update_agent(
    agent_id: int,
    agent_update: AgentUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> Agent:
    """Update an agent"""
    db_agent = AgentService.update_agent(db, agent_id, agent_update)
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return Agent.model_validate(db_agent)

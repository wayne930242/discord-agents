from typing import List, Optional
from sqlalchemy.orm import Session
from discord_agents.models.bot import BotModel, AgentModel
from discord_agents.schemas.bot import BotCreate, BotUpdate, AgentCreate, AgentUpdate


class BotService:
    """Bot management service"""

    @staticmethod
    def get_bots(db: Session) -> List[BotModel]:
        """Get all bots"""
        return db.query(BotModel).all()

    @staticmethod
    def get_bot(db: Session, bot_id: int) -> Optional[BotModel]:
        """Get bot by ID"""
        return db.query(BotModel).filter(BotModel.id == bot_id).first()

    @staticmethod
    def create_bot(db: Session, bot: BotCreate) -> BotModel:
        """Create new bot"""
        db_bot = BotModel(
            token=bot.token,
            error_message=bot.error_message,
            command_prefix=bot.command_prefix,
            dm_whitelist=bot.dm_whitelist,
            srv_whitelist=bot.srv_whitelist,
            use_function_map=bot.use_function_map,
            agent_id=bot.agent_id,
        )
        db.add(db_bot)
        db.commit()
        db.refresh(db_bot)

        # Notify bot manager about new bot using Redis state management
        try:
            from discord_agents.scheduler.broker import BotRedisClient

            redis_client = BotRedisClient()
            bot_id = db_bot.bot_id()
            init_config = db_bot.to_init_config()
            setup_config = db_bot.to_setup_agent_config()
            redis_client.set_should_start(bot_id, init_config, setup_config)
        except Exception as e:
            print(f"Warning: Failed to start bot {db_bot.id}: {e}")

        return db_bot

    @staticmethod
    def update_bot(
        db: Session, bot_id: int, bot_update: BotUpdate
    ) -> Optional[BotModel]:
        """Update bot"""
        db_bot = db.query(BotModel).filter(BotModel.id == bot_id).first()
        if not db_bot:
            return None

        update_data = bot_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_bot, field, value)

        db.commit()
        db.refresh(db_bot)

        # Restart bot if it's running using Redis state management
        try:
            from discord_agents.scheduler.broker import BotRedisClient
            import json

            redis_client = BotRedisClient()
            bot_id_str = db_bot.bot_id()

            # First update the configs in Redis
            init_config = db_bot.to_init_config()
            setup_config = db_bot.to_setup_agent_config()

            # Store updated configs
            redis_client._client.set(
                redis_client.BOT_INIT_CONFIG_KEY.format(bot_id=bot_id_str),
                json.dumps(init_config),
            )
            redis_client._client.set(
                redis_client.BOT_SETUP_CONFIG_KEY.format(bot_id=bot_id_str),
                json.dumps(setup_config),
            )

            # Then set to restart
            redis_client.set_should_restart(bot_id_str)
        except Exception as e:
            print(f"Warning: Failed to restart bot {db_bot.id}: {e}")

        return db_bot

    @staticmethod
    def delete_bot(db: Session, bot_id: int) -> bool:
        """Delete bot"""
        db_bot = db.query(BotModel).filter(BotModel.id == bot_id).first()
        if not db_bot:
            return False

        # Stop bot if it's running using Redis state management
        try:
            from discord_agents.scheduler.broker import BotRedisClient

            redis_client = BotRedisClient()
            redis_client.set_should_stop(db_bot.bot_id())
        except Exception as e:
            print(f"Warning: Failed to stop bot {db_bot.id}: {e}")

        db.delete(db_bot)
        db.commit()
        return True

    @staticmethod
    def start_bot(db: Session, bot_id: int) -> bool:
        """Start bot using Redis state management"""
        db_bot = db.query(BotModel).filter(BotModel.id == bot_id).first()
        if not db_bot:
            return False

        try:
            from discord_agents.scheduler.broker import BotRedisClient

            redis_client = BotRedisClient()
            bot_id_str = db_bot.bot_id()
            init_config = db_bot.to_init_config()
            setup_config = db_bot.to_setup_agent_config()
            redis_client.set_should_start(bot_id_str, init_config, setup_config)
            return True
        except Exception as e:
            print(f"Error starting bot {bot_id}: {e}")
            return False

    @staticmethod
    def stop_bot(db: Session, bot_id: int) -> bool:
        """Stop bot using Redis state management"""
        db_bot = db.query(BotModel).filter(BotModel.id == bot_id).first()
        if not db_bot:
            return False

        try:
            from discord_agents.scheduler.broker import BotRedisClient

            redis_client = BotRedisClient()
            redis_client.set_should_stop(db_bot.bot_id())
            return True
        except Exception as e:
            print(f"Error stopping bot {bot_id}: {e}")
            return False

    @staticmethod
    def start_all_bots(db: Session) -> dict[str, int]:
        """Start all bots in database using Redis state management"""
        from discord_agents.scheduler.broker import BotRedisClient

        bots = db.query(BotModel).all()
        started = 0
        failed = 0
        redis_client = BotRedisClient()

        for bot in bots:
            try:
                # Check if bot has an agent
                if not bot.agent:
                    print(f"Warning: Bot {bot.id} has no agent, skipping")
                    failed += 1
                    continue

                # Use Redis state management to start bot
                bot_id = bot.bot_id()
                init_config = bot.to_init_config()
                setup_config = bot.to_setup_agent_config()

                # Set bot to should_start state with configs
                redis_client.set_should_start(bot_id, init_config, setup_config)
                print(f"✅ Set bot {bot.id} ({bot.agent.name}) to start")
                started += 1

            except Exception as e:
                print(f"❌ Failed to set bot {bot.id} to start: {e}")
                failed += 1

        return {"started": started, "failed": failed, "total": len(bots)}


class AgentService:
    """Agent management service"""

    @staticmethod
    def get_agents(db: Session) -> List[AgentModel]:
        """Get all agents"""
        return db.query(AgentModel).all()

    @staticmethod
    def get_agent(db: Session, agent_id: int) -> Optional[AgentModel]:
        """Get agent by ID"""
        return db.query(AgentModel).filter(AgentModel.id == agent_id).first()

    @staticmethod
    def create_agent(db: Session, agent: AgentCreate) -> AgentModel:
        """Create new agent"""
        db_agent = AgentModel(
            name=agent.name,
            description=agent.description,
            role_instructions=agent.role_instructions,
            tool_instructions=agent.tool_instructions,
            agent_model=agent.agent_model,
            tools=agent.tools,
        )
        db.add(db_agent)
        db.commit()
        db.refresh(db_agent)
        return db_agent

    @staticmethod
    def update_agent(
        db: Session, agent_id: int, agent_update: AgentUpdate
    ) -> Optional[AgentModel]:
        """Update agent"""
        db_agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
        if not db_agent:
            return None

        update_data = agent_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_agent, field, value)

        db.commit()
        db.refresh(db_agent)

        # Restart all bots using this agent using Redis state management
        bots_using_agent = (
            db.query(BotModel).filter(BotModel.agent_id == agent_id).all()
        )
        for bot in bots_using_agent:
            try:
                from discord_agents.scheduler.broker import BotRedisClient

                redis_client = BotRedisClient()
                redis_client.set_should_restart(bot.bot_id())
            except Exception as e:
                print(f"Warning: Failed to restart bot {bot.id}: {e}")

        return db_agent

    @staticmethod
    def delete_agent(db: Session, agent_id: int) -> bool:
        """Delete agent"""
        db_agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
        if not db_agent:
            return False

        # Check if any bots are using this agent
        bots_using_agent = (
            db.query(BotModel).filter(BotModel.agent_id == agent_id).all()
        )
        if bots_using_agent:
            return False  # Cannot delete agent that's in use

        db.delete(db_agent)
        db.commit()
        return True

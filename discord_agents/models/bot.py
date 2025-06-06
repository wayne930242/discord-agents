from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discord_agents.domain.bot import MyBot, MyBotInitConfig, MyAgentSetupConfig
else:
    from discord_agents.domain.bot import MyBot, MyBotInitConfig, MyAgentSetupConfig

db = SQLAlchemy()


class AgentModel(db.Model):  # type: ignore
    __tablename__ = "my_agents"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    role_instructions = Column(Text, nullable=False)
    tool_instructions = Column(Text, nullable=False)
    agent_model = Column(String(100), nullable=False)
    tools = Column(JSON, default=list)

    bot = relationship("BotModel", back_populates="agent", uselist=False)


class BotModel(db.Model):  # type: ignore
    __tablename__ = "my_bots"

    id = Column(Integer, primary_key=True)
    token = Column(String(100), nullable=False, unique=True)
    error_message = Column(Text, nullable=False)
    command_prefix = Column(String(10), default="!")
    dm_whitelist = Column(JSON, default=list)
    srv_whitelist = Column(JSON, default=list)
    use_function_map = Column(JSON, default=dict)

    agent_id = Column(Integer, ForeignKey("my_agents.id"))
    agent = relationship("AgentModel", back_populates="bot")

    def bot_id(self) -> str:
        return f"bot_{self.id}"

    def to_init_config(self) -> "MyBotInitConfig":
        return MyBotInitConfig(
            bot_id=self.bot_id(),
            token=str(self.token),
            command_prefix_param=str(self.command_prefix) if self.command_prefix else None,
            dm_whitelist=list(self.dm_whitelist) if self.dm_whitelist else None,
            srv_whitelist=list(self.srv_whitelist) if self.srv_whitelist else None,
        )

    def to_setup_agent_config(self) -> "MyAgentSetupConfig":
        if not self.agent:
            raise ValueError("Agent not set for this bot")
        return MyAgentSetupConfig(
            description=str(self.agent.description),
            role_instructions=str(self.agent.role_instructions),
            tool_instructions=str(self.agent.tool_instructions),
            agent_model=str(self.agent.agent_model),
            app_name=str(self.agent.name),
            use_function_map=dict(self.use_function_map) if self.use_function_map else {},
            error_message=str(self.error_message),
            tools=list(self.agent.tools) if self.agent.tools else [],
        )

    def to_bot(self) -> "MyBot":
        my_bot = MyBot(self.to_init_config())
        my_bot.setup_my_agent(self.to_setup_agent_config())

        return my_bot


class NoteModel(db.Model):  # type: ignore
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(JSON, default=list)  # Store tags list
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Create index for session_id to improve query performance
    __table_args__ = (
        Index('ix_notes_session_id', 'session_id'),
        Index('ix_notes_created_at', 'created_at'),
    )

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    JSON,
    DateTime,
    Index,
    DECIMAL,
)
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from datetime import datetime
from typing import TYPE_CHECKING
import sqlalchemy as sa
from decimal import Decimal

if TYPE_CHECKING:
    from discord_agents.domain.bot import MyBot, MyBotInitConfig, MyAgentSetupConfig
else:
    from discord_agents.domain.bot import MyBot, MyBotInitConfig, MyAgentSetupConfig


class Base(DeclarativeBase):
    pass


class AgentModel(Base):
    __tablename__ = "my_agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    role_instructions: Mapped[str] = mapped_column(Text, nullable=False)
    tool_instructions: Mapped[str] = mapped_column(Text, nullable=False)
    agent_model: Mapped[str] = mapped_column(String(100), nullable=False)
    tools: Mapped[list] = mapped_column(JSON, default=list)

    bot = relationship("BotModel", back_populates="agent", uselist=False)


class BotModel(Base):
    __tablename__ = "my_bots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    command_prefix: Mapped[str] = mapped_column(String(10), default="!")
    dm_whitelist: Mapped[list] = mapped_column(JSON, default=list)
    srv_whitelist: Mapped[list] = mapped_column(JSON, default=list)
    use_function_map: Mapped[dict] = mapped_column(JSON, default=dict)

    agent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("my_agents.id"))
    agent = relationship("AgentModel", back_populates="bot")

    def bot_id(self) -> str:
        return f"bot_{self.id}"

    def to_init_config(self) -> "MyBotInitConfig":
        return MyBotInitConfig(
            bot_id=self.bot_id(),
            token=str(self.token),
            command_prefix_param=(
                str(self.command_prefix) if self.command_prefix else None
            ),
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
            use_function_map=(
                dict(self.use_function_map) if self.use_function_map else {}
            ),
            error_message=str(self.error_message),
            tools=list(self.agent.tools) if self.agent.tools else [],
        )

    def to_bot(self) -> "MyBot":
        my_bot = MyBot(self.to_init_config())
        my_bot.setup_my_agent(self.to_setup_agent_config())

        return my_bot


class NoteModel(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list)  # Store tags list
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Create index for session_id to improve query performance
    __table_args__ = (
        Index("ix_notes_session_id", "session_id"),
        Index("ix_notes_created_at", "created_at"),
    )


class TokenUsageModel(Base):
    __tablename__ = "token_usage"

    # Using SQLAlchemy 2.0 style throughout
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("my_agents.id"), nullable=False
    )
    agent_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # Denormalized for easier querying
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Time period tracking
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-12

    # Token counts
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Cost calculations (in USD)
    input_cost: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=10, scale=6), nullable=False, default=0.0
    )
    output_cost: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=10, scale=6), nullable=False, default=0.0
    )
    total_cost: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=10, scale=6), nullable=False, default=0.0
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    agent = relationship("AgentModel", backref="token_usage_records")

    # Create composite unique constraint to prevent duplicate records for same agent/model/month
    # Create indexes for efficient querying
    __table_args__ = (
        sa.UniqueConstraint(
            "agent_id", "model_name", "year", "month", name="unique_agent_model_month"
        ),
        Index("ix_token_usage_agent_id", "agent_id"),
        Index("ix_token_usage_model_name", "model_name"),
        Index("ix_token_usage_year_month", "year", "month"),
        Index("ix_token_usage_agent_year_month", "agent_id", "year", "month"),
    )

    def __repr__(self) -> str:
        return f"<TokenUsage(agent={self.agent_name}, model={self.model_name}, {self.year}-{self.month:02d}, tokens={self.total_tokens}, cost=${self.total_cost})>"

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship


from discord_agents.domain.bot import MyBot, MyBotInitConfig, MyAgentSetupConfig

db = SQLAlchemy()


class AgentModel(db.Model):
    __tablename__ = "my_agents"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    role_instructions = Column(Text, nullable=False)
    tool_instructions = Column(Text, nullable=False)
    agent_model = Column(String(100), nullable=False)
    tools = Column(JSON, default=list)

    bot = relationship("BotModel", back_populates="agent", uselist=False)


class BotModel(db.Model):
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

    def to_init_config(self) -> MyBotInitConfig:
        return MyBotInitConfig(
            bot_id=self.bot_id(),
            token=self.token,
            command_prefix_param=self.command_prefix,
            dm_whitelist=self.dm_whitelist,
            srv_whitelist=self.srv_whitelist,
        )

    def to_setup_agent_config(self) -> MyAgentSetupConfig:
        if not self.agent:
            raise ValueError("Agent not set for this bot")
        return MyAgentSetupConfig(
            description=self.agent.description,
            role_instructions=self.agent.role_instructions,
            tool_instructions=self.agent.tool_instructions,
            agent_model=self.agent.agent_model,
            app_name=self.agent.name,
            use_function_map=self.use_function_map,
            error_message=self.error_message,
            tools=self.agent.tools,
        )

    def to_bot(self) -> MyBot:
        my_bot = MyBot(self.to_init_config)
        my_bot.setup_my_agent(self.to_setup_agent_config())

        return my_bot

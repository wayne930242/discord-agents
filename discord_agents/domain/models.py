from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
import discord


from discord_agents.domain.bot import MyBot
from discord_agents.domain.agent import MyAgent
from discord_agents.domain.tools import Tools

db = SQLAlchemy()


class Agent(db.Model):
    __tablename__ = "my_agents"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    role_instructions = Column(Text, nullable=False)
    tool_instructions = Column(Text, nullable=False)
    agent_model = Column(String(100), nullable=False)
    tools = Column(JSON, default=list)

    bot = relationship("Bot", back_populates="agent", uselist=False)


class Bot(db.Model):
    __tablename__ = "my_bots"

    id = Column(Integer, primary_key=True)
    token = Column(String(100), nullable=False, unique=True)
    error_message = Column(Text, nullable=False)
    command_prefix = Column(String(10), default="!")
    dm_whitelist = Column(JSON, default=list)
    srv_whitelist = Column(JSON, default=list)
    use_function_map = Column(JSON, default=dict)

    agent_id = Column(Integer, ForeignKey("my_agents.id"))
    agent = relationship("Agent", back_populates="bot")

    def to_bot(self) -> MyBot:
        bot = MyBot(
            token=self.token,
            command_prefix_param=self.command_prefix,
            intents=discord.Intents.default(),
            help_command=None,
            dm_whitelist=self.dm_whitelist,
            srv_whitelist=self.srv_whitelist,
        )

        if self.agent:
            agent = MyAgent(
                name=self.agent.name,
                description=self.agent.description,
                role_instructions=self.agent.role_instructions,
                tool_instructions=self.agent.tool_instructions,
                agent_model=self.agent.agent_model,
                tools=[Tools.get_tool(tool_name) for tool_name in self.agent.tools],
            )
            bot.setup_agent(
                agent=agent.get_agent(),
                app_name=f"bot_{self.id}",
                use_function_map=self.use_function_map,
                error_message=self.error_message,
            )

        return bot

from flask_admin.contrib.sqla import ModelView
from flask_admin import Admin
from discord_agents.domain.models import db, Bot, Agent
from flask import Flask
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectMultipleField
from wtforms.validators import DataRequired
import json
from .runner_view import BotManagementView
from discord_agents.domain.tools import Tools


class BotAgentForm(FlaskForm):
    # Bot fields
    token = StringField("Bot Token", validators=[DataRequired()])
    error_message = TextAreaField("Error Message", validators=[DataRequired()])
    command_prefix = StringField("Command Prefix", default="!")
    dm_whitelist = TextAreaField("DM Whitelist", default="[]")
    srv_whitelist = TextAreaField("Server Whitelist", default="[]")
    use_function_map = TextAreaField("Function Map", default="{}")

    # Agent fields
    name = StringField("Agent Name", validators=[DataRequired()])
    description = TextAreaField("Description", validators=[DataRequired()])
    role_instructions = TextAreaField("Role Instructions", validators=[DataRequired()])
    tool_instructions = TextAreaField("Tool Instructions", validators=[DataRequired()])
    agent_model = StringField("Agent Model", validators=[DataRequired()])
    tools = SelectMultipleField(
        "Tools", choices=[(name, name) for name in Tools.tool_names()]
    )


class BotAgentView(ModelView):
    form = BotAgentForm
    column_list = ["id", "token", "command_prefix", "agent"]
    column_formatters = {
        "agent": lambda v, c, m, p: (
            m.agent.name if m.agent else "No Agent"
        ),
        "token": lambda v, c, m, p: (
            f"{m.token[:8]}..." if m.token else "No Token"
        )
    }
    form_columns = [
        "token",
        "error_message",
        "command_prefix",
        "dm_whitelist",
        "srv_whitelist",
        "use_function_map",
        "name",
        "description",
        "role_instructions",
        "tool_instructions",
        "agent_model",
        "tools",
    ]

    def on_model_change(self, form: FlaskForm, model: Bot, is_created: bool) -> None:
        for field in ["dm_whitelist", "srv_whitelist", "use_function_map"]:
            value = getattr(form, field).data
            try:
                setattr(model, field, json.loads(value))
            except json.JSONDecodeError:
                setattr(model, field, [] if field != "use_function_map" else {})

        if not model.agent:
            agent = Agent(
                name=form.name.data,
                description=form.description.data,
                role_instructions=form.role_instructions.data,
                tool_instructions=form.tool_instructions.data,
                agent_model=form.agent_model.data,
                tools=form.tools.data,
            )
            db.session.add(agent)
            db.session.flush()
            model.agent = agent
        else:
            model.agent.name = form.name.data
            model.agent.description = form.description.data
            model.agent.role_instructions = form.role_instructions.data
            model.agent.tool_instructions = form.tool_instructions.data
            model.agent.agent_model = form.agent_model.data
            model.agent.tools = form.tools.data

    def on_form_prefill(self, form: FlaskForm, id: int) -> None:
        bot = self.session.query(Bot).get(id)
        if bot and bot.agent:
            form.name.data = bot.agent.name
            form.description.data = bot.agent.description
            form.role_instructions.data = bot.agent.role_instructions
            form.tool_instructions.data = bot.agent.tool_instructions
            form.agent_model.data = bot.agent.agent_model
            form.tools.data = bot.agent.tools
            form.dm_whitelist.data = json.dumps(bot.dm_whitelist)
            form.srv_whitelist.data = json.dumps(bot.srv_whitelist)
            form.use_function_map.data = json.dumps(bot.use_function_map)


def init_admin(app: Flask) -> Admin:
    admin = Admin(app, name="Discord Agents Admin", template_mode="bootstrap3")
    admin.add_view(BotAgentView(Bot, db.session))
    admin.add_view(BotManagementView(name="Runner", endpoint="botmanagement"))
    return admin

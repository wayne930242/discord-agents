from flask_admin.contrib.sqla import ModelView
from discord_agents.models.bot import db, BotModel, AgentModel
from flask import request
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SelectMultipleField
from wtforms.validators import DataRequired, ValidationError
import json
from discord_agents.domain.tools import Tools
from discord_agents.utils.logger import get_logger
from discord_agents.scheduler.tasks import should_restart_bot_task
from discord_agents.domain.agent import LLMs
from discord_agents.utils.auth import check_auth, authenticate

logger = get_logger("bot_view")


def validate_json(form, field):
    try:
        json.loads(field.data)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON format: {str(e)}")


class BotConfigForm(FlaskForm):
    # Bot fields
    token = StringField("Bot Token", validators=[DataRequired()])
    error_message = TextAreaField("Error Message", validators=[DataRequired()])
    command_prefix = StringField("Command Prefix", default="!")
    dm_whitelist = TextAreaField(
        "DM Whitelist", default="[]", validators=[validate_json]
    )
    srv_whitelist = TextAreaField(
        "Server Whitelist", default="[]", validators=[validate_json]
    )
    use_function_map = TextAreaField(
        "Function Map (deprecated)", default="{}", validators=[validate_json]
    )

    # Agent fields
    name = StringField("Agent Name", validators=[DataRequired()])
    description = TextAreaField("Description", validators=[DataRequired()])
    role_instructions = TextAreaField("Role Instructions", validators=[DataRequired()])
    tool_instructions = TextAreaField("Tool Instructions", validators=[DataRequired()])
    agent_model = SelectField(
        "Agent Model",
        choices=[(name, name) for name in LLMs.get_model_names()],
        validators=[DataRequired()],
    )
    tools = SelectMultipleField(
        "Tools", choices=[(name, name) for name in Tools.get_tool_names()]
    )


class BotConfigView(ModelView):
    form = BotConfigForm
    column_list = ["id", "token", "command_prefix", "agent"]
    column_formatters = {
        "agent": lambda v, c, m, p: (m.agent.name if m.agent else "No Agent"),
        "token": lambda v, c, m, p: (f"{m.token[:8]}..." if m.token else "No Token"),
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

    def is_accessible(self):
        """Check if the current user is authenticated"""
        auth = request.authorization
        return auth and check_auth(auth.username, auth.password)

    def inaccessible_callback(self, name, **kwargs):
        """Redirect to authentication if not accessible"""
        return authenticate()

    def on_model_change(
        self, form: FlaskForm, model: BotModel, is_created: bool
    ) -> None:
        for field in ["dm_whitelist", "srv_whitelist", "use_function_map"]:
            value = getattr(form, field).data
            try:
                setattr(model, field, json.loads(value))
            except json.JSONDecodeError:
                setattr(model, field, [] if field != "use_function_map" else {})

        if not model.agent:
            agent = AgentModel(
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

        try:
            bot_id = f"bot_{model.id}"
            db.session.commit()
            should_restart_bot_task(bot_id)
            logger.info(
                f"Bot {bot_id} settings have been updated and restarted successfully"
            )
        except Exception as e:
            logger.error(
                f"Failed to update bot {bot_id} settings: {str(e)}", exc_info=True
            )
            raise

    def on_form_prefill(self, form: FlaskForm, id: int) -> None:
        bot = self.session.query(BotModel).get(id)
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

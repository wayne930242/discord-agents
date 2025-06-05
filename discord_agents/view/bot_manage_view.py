from flask_admin import BaseView, expose
from flask import flash, redirect, url_for, request
from discord_agents.utils.logger import get_logger
from discord_agents.utils.auth import check_auth, authenticate
import json
from typing import Optional, Any
from werkzeug.wrappers import Response as WerkzeugResponse

logger = get_logger("bot_manage_view")


class BotManageView(BaseView):
    def __init__(
        self,
        name: Optional[str] = None,
        endpoint: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, endpoint=endpoint, *args, **kwargs)
        logger.info("BotManagementView initialized")

    def is_accessible(self) -> bool:
        """Check if the current user is authenticated"""
        auth = request.authorization
        if not auth or not auth.username or not auth.password:
            return False
        return check_auth(auth.username, auth.password)

    def inaccessible_callback(self, name: str, **kwargs: Any):  # type: ignore
        """Redirect to authentication if not accessible"""
        return authenticate()

    @expose("/")  # type: ignore
    def index(self) -> Any:
        logger.info("Visit Bot Management page")
        from discord_agents.scheduler.broker import BotRedisClient

        redis_broker = BotRedisClient()
        result = redis_broker.get_all_bot_status()
        logger.info(f"Bot status result: {result}")
        running_bots: list[str] = []
        not_running_bots: list[str] = []
        error_message = request.args.get("error")
        for bot_id, info in result.items():
            is_running = False
            try:
                # Try to parse as JSON first
                info_dict = json.loads(info)
                is_running = info_dict.get("running", False)
            except (json.JSONDecodeError, TypeError):
                # If not JSON, check if it's directly "running"
                if info == "running":
                    is_running = True
            if is_running:
                running_bots.append(bot_id)
            else:
                not_running_bots.append(bot_id)
        return self.render(
            "admin/bot_manage.html",
            not_running_bots=not_running_bots,
            running_bots=running_bots,
            title="Bot Manage",
            error_message=error_message,
        )

    @expose("/start/<bot_id>")  # type: ignore
    def start_bot(self, bot_id: str) -> WerkzeugResponse:
        from discord_agents.scheduler.tasks import should_start_bot_in_model_task

        logger.info(f"Receive request to start bot {bot_id}")
        try:
            should_start_bot_in_model_task(bot_id)
            logger.info(f"Bot {bot_id} started successfully (task dispatched)")
            flash(f"Bot {bot_id} start task dispatched", "success")
            return redirect(url_for(".index"))
        except Exception as e:
            logger.error(f"Error starting bot {bot_id}: {str(e)}", exc_info=True)
            return redirect(
                url_for(
                    ".index",
                    error=f"An error occurred while starting bot {bot_id}: {str(e)}",
                )
            )

    @expose("/stop/<bot_id>")  # type: ignore
    def stop_bot(self, bot_id: str) -> WerkzeugResponse:
        from discord_agents.scheduler.tasks import should_stop_bot_task

        logger.info(f"Receive request to stop bot {bot_id}")
        try:
            should_stop_bot_task(bot_id)
            logger.info(f"Bot {bot_id} stop task dispatched")
            flash(f"Bot {bot_id} stop task dispatched", "success")
            return redirect(url_for(".index"))
        except Exception as e:
            logger.error(f"Error stopping bot {bot_id}: {str(e)}", exc_info=True)
            return redirect(
                url_for(
                    ".index",
                    error=f"An error occurred while stopping bot {bot_id}: {str(e)}",
                )
            )

    @expose("/start-all")  # type: ignore
    def start_all_bots(self) -> WerkzeugResponse:
        from discord_agents.scheduler.tasks import should_start_all_bots_in_model_task

        logger.info("Receive request to start all bots")
        try:
            should_start_all_bots_in_model_task()
            logger.info("All bot start tasks dispatched")
            flash("All bot start tasks dispatched", "success")
            return redirect(url_for(".index"))
        except Exception as e:
            logger.error(f"Error starting all bots: {str(e)}", exc_info=True)
            return redirect(
                url_for(
                    ".index",
                    error=f"An error occurred while starting all bots: {str(e)}",
                )
            )

    @expose("/stop-all")  # type: ignore
    def stop_all_bots(self) -> WerkzeugResponse:
        from discord_agents.scheduler.tasks import should_stop_all_bots_task

        logger.info("Receive request to stop all bots")
        try:
            should_stop_all_bots_task()
            logger.info("All bot stop tasks dispatched")
            flash("All bot stop tasks dispatched", "success")
            return redirect(url_for(".index"))
        except Exception as e:
            logger.error(f"Error stopping all bots: {str(e)}", exc_info=True)
            return redirect(
                url_for(
                    ".index",
                    error=f"An error occurred while stopping all bots: {str(e)}",
                )
            )

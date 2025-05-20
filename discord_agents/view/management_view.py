from flask_admin import BaseView, expose
from flask import flash, redirect, url_for
from discord_agents.utils.logger import get_logger

logger = get_logger("runner_view")


class BotManagementView(BaseView):
    def __init__(self, name=None, endpoint=None, *args, **kwargs):
        super().__init__(name=name, endpoint=endpoint, *args, **kwargs)
        logger.info("BotManagementView initialized")

    @expose("/")
    def index(self):
        logger.info("Visit Bot Management page")
        try:
            from discord_agents.scheduler.tasks import get_all_bots_status

            result = get_all_bots_status.apply().get()
            logger.info(f"Bot status result: {result}")
            running_bots = [
                bot_id for bot_id, info in result.items() if info.get("running")
            ]  # running == True
            not_running_bots = [
                bot_id for bot_id, info in result.items() if not info.get("running")
            ]  # running == False
            return self.render(
                "admin/bot_management.html",
                not_running_bots=not_running_bots,
                running_bots=running_bots,
                title="Bot Management",
            )
        except Exception as e:
            logger.error(f"Error in index view: {str(e)}", exc_info=True)
            flash("Error loading bot status", "error")
            return self.render(
                "admin/bot_management.html",
                not_running_bots=[],
                running_bots=[],
                title="Bot Management",
            )

    @expose("/start/<bot_id>")
    def start_bot(self, bot_id):
        from discord_agents.scheduler.tasks import dispatch_start_bot

        logger.info(f"Receive request to start bot {bot_id}")
        try:
            dispatch_start_bot.delay(bot_id)
            logger.info(f"Bot {bot_id} started successfully (task dispatched)")
            flash(f"Bot {bot_id} start task dispatched", "success")
        except Exception as e:
            logger.error(f"Error starting bot {bot_id}: {str(e)}", exc_info=True)
            flash(f"An error occurred while starting bot {bot_id}.", "error")
        return redirect(url_for(".index"))

    @expose("/stop/<bot_id>")
    def stop_bot(self, bot_id):
        from discord_agents.scheduler.tasks import stop_bot_task

        logger.info(f"Receive request to stop bot {bot_id}")
        try:
            stop_bot_task.delay(bot_id)
            logger.info(f"Bot {bot_id} stop task dispatched")
            flash(f"Bot {bot_id} stop task dispatched", "success")
        except Exception as e:
            logger.error(f"Error stopping bot {bot_id}: {str(e)}", exc_info=True)
            flash(f"An error occurred while stopping bot {bot_id}.", "error")
        return redirect(url_for(".index"))

    @expose("/start-all")
    def start_all_bots(self):
        from discord_agents.scheduler.tasks import dispatch_start_all_bots_task

        logger.info("Receive request to start all bots")
        try:
            dispatch_start_all_bots_task.delay()
            logger.info("All bot start tasks dispatched")
            flash("All bot start tasks dispatched", "success")
        except Exception as e:
            logger.error(f"Error starting all bots: {str(e)}", exc_info=True)
            flash("An error occurred while starting all bots.", "error")
        return redirect(url_for(".index"))

    @expose("/stop-all")
    def stop_all_bots(self):
        from discord_agents.scheduler.tasks import dispatch_stop_all_bots_task

        logger.info("Receive request to stop all bots")
        try:
            dispatch_stop_all_bots_task.delay()
            logger.info("All bot stop tasks dispatched")
            flash("All bot stop tasks dispatched", "success")
        except Exception as e:
            logger.error(f"Error stopping all bots: {str(e)}", exc_info=True)
            flash("An error occurred while stopping all bots.", "error")
        return redirect(url_for(".index"))

from flask_admin import BaseView, expose
from flask import flash, redirect, url_for, current_app
from discord_agents.utils.logger import logger


class BotManagementView(BaseView):
    def __init__(self, name=None, endpoint=None, *args, **kwargs):
        super().__init__(name=name, endpoint=endpoint, *args, **kwargs)
        logger.info("BotManagementView initialized")

    @expose("/")
    def index(self):
        logger.info("Visit Bot Management page")
        try:
            registered_bots = list(current_app.bot_runner.get_registered_bots().keys())
            logger.info(f"Registered bots: {registered_bots}")

            running_bots = []
            for bot_id in registered_bots:
                try:
                    if bot_id in current_app.bot_runner.get_running_bots():
                        running_bots.append(bot_id)
                except Exception as e:
                    logger.error(f"Error checking bot {bot_id} status: {str(e)}", exc_info=True)
            logger.info(f"Running bots: {running_bots}")

            return self.render(
                "admin/bot_management.html",
                registered_bots=registered_bots,
                running_bots=running_bots,
                title="Bot Management",
            )
        except Exception as e:
            logger.error(f"Error in index view: {str(e)}", exc_info=True)
            flash("Error loading bot status", "error")
            return self.render(
                "admin/bot_management.html",
                registered_bots=[],
                running_bots=[],
                title="Bot Management",
            )

    @expose("/start/<bot_id>")
    def start_bot(self, bot_id):
        logger.info(f"Receive request to start bot {bot_id}")
        try:
            logger.info(f"Start bot {bot_id}...")
            current_app.bot_runner.start_bot(bot_id)
            logger.info(f"Bot {bot_id} started successfully")
            flash(f"Bot {bot_id} started", "success")
        except ValueError as e:
            logger.error(f"Error starting bot {bot_id}: {str(e)}")
            flash(str(e), "error")
        except Exception as e:
            logger.error(f"Error starting bot {bot_id}: {str(e)}", exc_info=True)
            flash(f"An unexpected error occurred while starting bot {bot_id}.", "error")
        return redirect(url_for(".index"))

    @expose("/stop/<bot_id>")
    def stop_bot(self, bot_id):
        logger.info(f"Receive request to stop bot {bot_id}")
        try:
            logger.info(f"Start stopping bot {bot_id}...")
            current_app.bot_runner.stop_bot(bot_id)
            logger.info(f"Bot {bot_id} stopped successfully")
            flash(f"Bot {bot_id} stopped", "success")
        except ValueError as e:
            logger.error(f"Error stopping bot {bot_id}: {str(e)}")
            flash(str(e), "error")
        except Exception as e:
            logger.error(f"Error stopping bot {bot_id}: {str(e)}", exc_info=True)
            flash(f"An unexpected error occurred while stopping bot {bot_id}.", "error")
        return redirect(url_for(".index"))

    @expose("/start-all")
    def start_all_bots(self):
        logger.info("Receive request to start all bots")
        try:
            logger.info("Start all bots...")
            current_app.bot_runner.start_all_bots()
            logger.info("All bots started successfully")
            flash("All bots started", "success")
        except Exception as e:
            logger.error(f"Error starting all bots: {str(e)}", exc_info=True)
            flash("An unexpected error occurred while starting all bots.", "error")
        return redirect(url_for(".index"))

    @expose("/stop-all")
    def stop_all_bots(self):
        logger.info("Receive request to stop all bots")
        try:
            logger.info("Start stopping all bots...")
            current_app.bot_runner.stop_all_bots()
            logger.info("All bots stopped successfully")
            flash("All bots stopped", "success")
        except Exception as e:
            logger.error(f"Error stopping all bots: {str(e)}", exc_info=True)
            flash("An unexpected error occurred while stopping all bots.", "error")
        return redirect(url_for(".index"))

from discord_agents.scheduler.broker import BotRedisClient
from discord_agents.scheduler.helpers import get_flask_app
from discord_agents.utils.logger import get_logger
from discord_agents.domain.bot import BotModel
from typing import Optional

logger = get_logger("service")


def dispatch_stop_bot(bot_id: str):
    logger.info(f"Stop bot task for {bot_id}")
    with get_flask_app().app_context():
        redis_broker = BotRedisClient()
        redis_broker.set_should_stop(bot_id)


def dispatch_start_bot(bot_id: str):
    logger.info(f"Dispatch start bot task for {bot_id}")
    with get_flask_app().app_context():
        redis_broker = BotRedisClient()
        db_id = int(bot_id.replace("bot_", ""))
        bot: Optional[BotModel] = BotModel.query.get(db_id)
        if not bot:
            logger.error(f"Bot {bot_id} not found in DB")
            return
        redis_broker.set_should_start(
            bot_id, bot.to_init_config(), bot.to_setup_agent_config()
        )


def dispatch_restart_bot(bot_id: str):
    logger.info(f"Restart bot task for {bot_id}")
    with get_flask_app().app_context():
        dispatch_stop_bot(bot_id)
        dispatch_start_bot(bot_id)


def dispatch_stop_all_bots_task():
    logger.info("Stop all bots task triggered")
    redis_broker = BotRedisClient()
    all_running_bots = redis_broker.get_all_running_bots()
    for bot_id in all_running_bots:
        dispatch_stop_bot(bot_id)


def dispatch_start_all_bots_task():
    logger.info("Start all bots task triggered")
    with get_flask_app().app_context():
        all_db_bots = [bot.bot_id() for bot in BotModel.query.all()]
        for bot_id in all_db_bots:
            dispatch_start_bot.delay(bot_id)

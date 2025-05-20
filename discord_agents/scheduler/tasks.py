from typing import Optional

from discord_agents.utils.logger import get_logger
from discord_agents.domain.bot import MyBotInitConfig, MyAgentSetupConfig, MyBot
from discord_agents.scheduler.broker import BotRedisClient
from discord_agents.models.bot import BotModel
from discord_agents.scheduler.helpers import get_flask_app

logger = get_logger("celery_tasks")
redis_broker = BotRedisClient()


def run_bot_task(
    bot_id: str, init_data: MyBotInitConfig, setup_data: MyAgentSetupConfig
):
    logger.info(f"Dispatch run bot task for {bot_id}")
    try:
        my_bot = MyBot(init_data)
        my_bot.setup_my_agent(setup_data)
        redis_broker.set_running(bot_id)
    except Exception as e:
        logger.error(f"Error running bot {bot_id}: {str(e)}", exc_info=True)
        redis_broker.set_idle(bot_id)


def bot_running_task(bot_id: str):
    logger.info(f"Dispatch bot running task for {bot_id}")
    redis_broker.set_running(bot_id)


def bot_idle_task(bot_id: str):
    logger.info(f"Dispatch bot idle task for {bot_id}")
    redis_broker.set_idle(bot_id)


def stop_bot_task(bot_id: str):
    logger.info(f"Dispatch stop bot task for {bot_id}")
    redis_broker.set_should_stop(bot_id)


def start_bot_task(bot_id: str):
    logger.info(f"Dispatch start bot task for {bot_id}")
    with get_flask_app().app_context():
        db_id = int(bot_id.replace("bot_", ""))
        bot: Optional[BotModel] = BotModel.query.get(db_id)
        if not bot:
            logger.error(f"Bot {bot_id} not found in DB")
            return
        redis_broker.set_should_start(
            bot_id, bot.to_init_config(), bot.to_setup_agent_config()
        )


def restart_bot_task(bot_id: str):
    logger.info(f"Dispatch restart bot task for {bot_id}")
    stop_bot_task(bot_id)
    start_bot_task(bot_id)


def stop_all_bots_task():
    logger.info("Dispatch stop all bots task")
    all_running_bots = redis_broker.get_all_running_bots()
    for bot_id in all_running_bots:
        stop_bot_task(bot_id)


def start_all_bots_task():
    logger.info("Dispatch start all bots task")
    with get_flask_app().app_context():
        all_db_bots = [bot.bot_id() for bot in BotModel.query.all()]
        for bot_id in all_db_bots:
            start_bot_task(bot_id)


def try_starting_bot_task(bot_id: str):
    from discord_agents.scheduler.worker import load_bot_from_redis
    from discord_agents.scheduler.worker import bot_manager

    can_start = redis_broker.lock_and_set_starting_if_should_start(bot_id)
    if can_start:
        logger.info(f"Can start: {bot_id}")
        init_data, setup_data = load_bot_from_redis(bot_id)
        if init_data and setup_data:
            bot_running_task(bot_id)
            bot = MyBot(init_data)
            bot.setup_my_agent(setup_data)
            bot_manager.add_bot(bot_id, bot)


def try_stopping_bot_task(bot_id: str):
    from discord_agents.scheduler.worker import bot_manager

    can_stop = redis_broker.lock_and_set_stopping_if_should_stop(bot_id)
    if can_stop:
        logger.info(f"Can stop: {bot_id}")
        bot_idle_task(bot_id)
        bot_manager.remove_bot(bot_id)


def listen_bots_task(bot_id: str):
    try_starting_bot_task(bot_id)
    try_stopping_bot_task(bot_id)

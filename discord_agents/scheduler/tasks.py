from typing import Optional

from discord_agents.utils.logger import get_logger
from discord_agents.domain.bot import MyBotInitConfig, MyAgentSetupConfig, MyBot
from discord_agents.scheduler.broker import BotRedisClient
from discord_agents.models.bot import BotModel
from discord_agents.scheduler.helpers import get_flask_app

logger = get_logger("tasks")
redis_broker = BotRedisClient()


def bot_run_task(bot_id: str) -> None:
    logger.info(f"Dispatch bot run task for {bot_id}")
    redis_broker.set_running(bot_id)


def bot_idle_task(bot_id: str) -> None:
    logger.info(f"Dispatch bot idle task for {bot_id}")
    redis_broker.set_idle(bot_id)


def should_start_bot_in_model_task(bot_id: str) -> None:
    with get_flask_app().app_context():
        db_id = int(bot_id.replace("bot_", ""))
        bot: Optional[BotModel] = BotModel.query.filter_by(id=db_id).first()
        if not bot:
            logger.error(f"Bot {bot_id} not found in DB")
            return
        should_start_bot_task(
            bot.bot_id(), bot.to_init_config(), bot.to_setup_agent_config()
        )


def should_start_bot_task(
    bot_id: str, init_data: MyBotInitConfig, setup_data: MyAgentSetupConfig
) -> None:
    """Set bot to should_start state and store config"""
    logger.info(f"Dispatch start bot task for {bot_id}")
    redis_broker.set_should_start(bot_id, init_data, setup_data)


def should_restart_bot_task(bot_id: str) -> None:
    """Set bot to should_restart state and clear config"""
    logger.info(f"Dispatch restart bot task for {bot_id}")
    redis_broker.set_should_restart(bot_id)
    redis_broker.clear_config(bot_id)


def should_stop_bot_task(bot_id: str) -> None:
    """Set bot to should_stop state and clear config"""
    logger.info(f"Dispatch stop bot task for {bot_id}")
    redis_broker.set_should_stop(bot_id)
    redis_broker.clear_config(bot_id)


def should_stop_all_bots_task() -> None:
    """Set all running bots to should_stop state and clear config"""
    logger.info("Dispatch stop all bots task")
    all_running_bots = redis_broker.get_all_running_bots()
    for bot_id in all_running_bots:
        should_stop_bot_task(bot_id)


def should_start_all_bots_in_model_task() -> None:
    logger.info("Dispatch start all bots task")
    with get_flask_app().app_context():
        all_db_bots = BotModel.query.all()
        for bot in all_db_bots:
            init_data = bot.to_init_config()
            setup_data = bot.to_setup_agent_config()
            if init_data and setup_data:
                should_start_bot_task(bot.bot_id(), init_data, setup_data)


def listen_bots_task(bot_id: str) -> None:
    _try_stopping_bot_task(bot_id)
    _try_starting_bot_task(bot_id)


# Only for monitoring
def _try_starting_bot_task(bot_id: str) -> None:
    """Start and run bot if it is in should_start state"""
    from discord_agents.scheduler.worker import load_bot_from_redis
    from discord_agents.scheduler.worker import bot_manager

    can_start = redis_broker.lock_and_set_starting_if_should_start(bot_id)
    if can_start:
        logger.info(f"Can start: {bot_id}")
        init_data, setup_data = load_bot_from_redis(bot_id)
        if init_data and setup_data:
            bot = MyBot(init_data)
            bot.setup_my_agent(setup_data)
            bot_manager.add_bot_and_run(bot.bot_id, bot)
            bot_run_task(bot.bot_id)


def _try_stopping_bot_task(bot_id: str) -> None:
    from discord_agents.scheduler.worker import bot_manager

    next_state = redis_broker.lock_and_set_stopping_if_should_stop(bot_id)
    if next_state is not False:
        bot_manager.remove_bot(bot_id)

    if next_state == "to_idle":
        logger.info(f"Can stop: {bot_id}")
        bot_idle_task(bot_id)
    elif next_state == "to_start":
        logger.info(f"Can restart: {bot_id}")
        should_start_bot_in_model_task(bot_id)

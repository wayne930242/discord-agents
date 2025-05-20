import asyncio
from typing import Optional
from discord_agents.models.bot import BotModel
from discord_agents.utils.logger import get_logger
from discord_agents.celery_app import celery_app
from discord_agents.domain.bot import MyBotInitConfig, MyAgentSetupConfig, MyBot
from discord_agents.scheduler.broker import BotRedisClient

logger = get_logger("celery_tasks")

flask_app = None


def get_flask_app():
    global flask_app
    if flask_app is None:
        from discord_agents.app import create_app

        flask_app = create_app()
    return flask_app


@celery_app.task
def run_bot_task(
    bot_id: str, init_data: MyBotInitConfig, setup_data: MyAgentSetupConfig
):
    logger.info(f"Run bot task for {bot_id}")
    redis_broker = BotRedisClient()
    try:
        my_bot = MyBot(init_data)
        my_bot.setup_my_agent(setup_data)

        asyncio.run(my_bot.run())
        redis_broker.set_running(bot_id)
    except Exception as e:
        logger.error(f"Error running bot {bot_id}: {str(e)}", exc_info=True)
        redis_broker.set_idle(bot_id)


@celery_app.task
def dispatch_stop_bot_task(bot: MyBot):
    bot_id = bot.bot_id
    logger.info(f"Dispatch stop bot task for {bot_id}")
    redis_broker = BotRedisClient()
    try:
        asyncio.run(bot.stop())
    except Exception as e:
        logger.error(f"Error stopping bot {bot_id}: {str(e)}", exc_info=True)
    finally:
        redis_broker.set_idle(bot_id)


@celery_app.task
def dispatch_start_bot_task(bot_id: str):
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


@celery_app.task
def dispatch_stop_bot_task(bot_id: str):
    logger.info(f"Stop bot task for {bot_id}")
    with get_flask_app().app_context():
        redis_broker = BotRedisClient()
        redis_broker.set_should_stop(bot_id)


@celery_app.task
def get_all_bots_status():
    with get_flask_app().app_context():
        redis_broker = BotRedisClient()
        all_db_bots = [bot.bot_id() for bot in BotModel.query.all()]

        status = {}
        for bot_id in all_db_bots:
            status[bot_id] = redis_broker.get_state(bot_id)
        return status


@celery_app.task
def dispatch_restart_bot_task(bot_id: str):
    logger.info(f"Restart bot task for {bot_id}")
    with get_flask_app().app_context():
        dispatch_stop_bot_task.delay(bot_id)
        dispatch_start_bot_task.delay(bot_id)


@celery_app.task
def dispatch_stop_all_bots_task():
    logger.info("Stop all bots task triggered")
    redis_broker = BotRedisClient()
    all_running_bots = redis_broker.get_all_running_bots()
    for bot_id in all_running_bots:
        dispatch_stop_bot_task.delay(bot_id)


@celery_app.task
def dispatch_start_all_bots_task():
    logger.info("Start all bots task triggered")
    with get_flask_app().app_context():
        all_db_bots = [bot.bot_id() for bot in BotModel.query.all()]
        for bot_id in all_db_bots:
            dispatch_start_bot_task.delay(bot_id)

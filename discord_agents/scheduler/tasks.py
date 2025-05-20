import asyncio
from typing import Optional
from discord_agents.models.bot import BotModel
from discord_agents.utils.logger import get_logger
from discord_agents.celery_app import celery_app
from discord_agents.domain.bot import MyBotInitConfig, MyAgentSetupConfig, MyBot
from discord_agents.scheduler.broker import BotRedisClient
from discord_agents.scheduler.helpers import get_flask_app

logger = get_logger("celery_tasks")

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
def stop_bot_task(bot: MyBot):
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
def get_all_bots_status():
    with get_flask_app().app_context():
        redis_broker = BotRedisClient()
        all_db_bots = [bot.bot_id() for bot in BotModel.query.all()]

        status = {}
        for bot_id in all_db_bots:
            status[bot_id] = redis_broker.get_state(bot_id)
        return status

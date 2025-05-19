import json
import redis
from discord_agents.env import REDIS_URL
from discord_agents.domain.models import BotModel
from discord_agents.utils.logger import get_logger
from discord_agents.celery_app import celery_app

logger = get_logger("celery_tasks")

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

flask_app = None

def get_flask_app():
    global flask_app
    if flask_app is None:
        from discord_agents.app import create_app
        flask_app = create_app()
    return flask_app


@celery_app.task
def start_bot_task(bot_id: str):
    logger.info(f"Start bot task for {bot_id}")
    with get_flask_app().app_context():
        running = redis_client.get(f"bot:{bot_id}:running")
        if running == "1":
            logger.info(f"Bot {bot_id} is already running, skip start.")
            return
        db_id = int(bot_id.replace("bot_", ""))
        bot = BotModel.query.get(db_id)
        if not bot:
            logger.error(f"Bot {bot_id} not found in DB")
            return
        redis_client.sadd("bots:all", bot_id)
        redis_client.set(f"bot:{bot_id}:init_data", json.dumps(bot.to_init_config()))
        redis_client.set(
            f"bot:{bot_id}:setup_agent_data", json.dumps(bot.to_setup_agent_config())
        )
        redis_client.set(f"bot:{bot_id}:should_run", 1)
        logger.info(f"Bot {bot_id} init/setup data written to redis")


@celery_app.task
def stop_bot_task(bot_id: str):
    logger.info(f"Stop bot task for {bot_id}")
    with get_flask_app().app_context():
        redis_client.set(f"bot:{bot_id}:stop_flag", 1)
        redis_client.set(f"bot:{bot_id}:should_run", 0)
        logger.info(f"Bot {bot_id} stop flag set")


@celery_app.task
def get_all_bots_status():
    with get_flask_app().app_context():
        all_bots = [bot.bot_id() for bot in BotModel.query.all()]
        status = {}
        for bot_id in all_bots:
            running = redis_client.get(f"bot:{bot_id}:running")
            should_run = redis_client.get(f"bot:{bot_id}:should_run")
            status[bot_id] = {"running": running == "1", "should_run": should_run == "1"}
        return status


@celery_app.task
def restart_bot_task(bot_id: str):
    stop_bot_task(bot_id)
    start_bot_task(bot_id)


@celery_app.task
def start_all_bots_task():
    logger.info("Start all bots task triggered")
    with get_flask_app().app_context():
        for bot in BotModel.query.all():
            start_bot_task.delay(bot.bot_id())
            logger.info(f"Dispatched start task for {bot.bot_id()}")

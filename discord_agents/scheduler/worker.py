import time
from discord_agents.domain.bot import MyBotInitConfig, MyAgentSetupConfig
from discord_agents.utils.logger import get_logger
from discord_agents.scheduler.broker import BotRedisClient
from discord_agents.scheduler.tasks import run_bot_task, stop_bot_task
from discord_agents.domain.bot import MyBot

logger = get_logger("bot_worker")

running_bots: dict[str, MyBot] = {}  # bot_id: MyBot


def load_bot_from_redis(bot_id: str) -> tuple[MyBotInitConfig, MyAgentSetupConfig]:
    redis_broker = BotRedisClient()
    init_data = redis_broker.get_init_config(bot_id)
    setup_data = redis_broker.get_setup_config(bot_id)
    if not init_data or not setup_data:
        logger.error(f"Bot {bot_id} init/setup data not found in redis")
        return None, None
    return init_data, setup_data


def monitor_bots() -> None:
    redis_broker = BotRedisClient()
    while True:
        bot_ids = redis_broker.get_all_bots()
        for bot_id in bot_ids:
            logger.info(
                f"[monitor_bots] bot_id={bot_id} running_bots={list(running_bots.keys())}"
            )
            # Start bot
            if redis_broker.should_run_bot(bot_id, running_bots):
                can_start = redis_broker.lock_and_set_starting_if_should_start(bot_id)
                if not can_start:
                    continue
                logger.info(
                    f"[Redlock] Acquired starting flag for {bot_id}, launching..."
                )
                init_data, setup_data = load_bot_from_redis(bot_id)
                if init_data and setup_data:
                    run_bot_task.delay(bot_id, init_data, setup_data)

            # Stop bot
            if redis_broker.lock_and_set_stopping_if_should_stop(bot_id):
                logger.info(
                    f"[monitor_bots] Detected bot {bot_id} should stop, calling stop() on BotThread..."
                )
                stop_bot_task.delay(bot_id)
                del running_bots[bot_id]
                redis_broker.set_idle(bot_id)
        time.sleep(3)

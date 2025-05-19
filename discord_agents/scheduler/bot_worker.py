import asyncio
import json
import time
import threading
import redis
import discord
from redlock import Redlock
from discord_agents.env import REDIS_URL
from discord_agents.domain.bot import MyBot, MyBotInitConfig, MyAgentSetupConfig
from discord_agents.domain.tools import Tools
from discord_agents.utils.logger import get_logger

logger = get_logger("bot_worker")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
redlock = Redlock([REDIS_URL])

running_bots = {}  # bot_id: (thread, my_bot, loop)


def load_bot_from_redis(bot_id: str) -> tuple[dict, dict]:
    init_data = redis_client.get(f"bot:{bot_id}:init_data")
    setup_data = redis_client.get(f"bot:{bot_id}:setup_agent_data")
    if not init_data or not setup_data:
        logger.error(f"Bot {bot_id} init/setup data not found in redis")
        return None, None
    return json.loads(init_data), json.loads(setup_data)


def dict_to_bot_init_config(data: dict) -> MyBotInitConfig:
    return MyBotInitConfig(
        bot_id=data["bot_id"],
        token=data["token"],
        command_prefix_param=data.get("command_prefix"),
        intents=discord.Intents.default(),
        help_command=None,
        dm_whitelist=data.get("dm_whitelist"),
        srv_whitelist=data.get("srv_whitelist"),
    )


def dict_to_agent_setup_config(data: dict) -> MyAgentSetupConfig:
    return MyAgentSetupConfig(
        description=data["description"],
        role_instructions=data["role_instructions"],
        tool_instructions=data["tool_instructions"],
        agent_model=data["agent_model"],
        app_name=data["app_name"],
        use_function_map=data["use_function_map"],
        error_message=data["error_message"],
        tools=Tools.get_tools(data["tools"]),
    )


async def run_bot_async(bot_id: str, init_data: dict, setup_data: dict) -> None:
    try:
        bot_config = dict_to_bot_init_config(bot_id, init_data)
        agent_config = dict_to_agent_setup_config(setup_data)
        my_bot = MyBot(bot_config)
        my_bot.setup_my_agent(agent_config)

        redis_client.set(f"bot:{bot_id}:running", 1)
        logger.info(f"Bot {bot_id} set running=1, start running...")
        await my_bot.run()
    except Exception as e:
        logger.error(f"Error running bot {bot_id}: {str(e)}", exc_info=True)
        redis_client.set(f"bot:{bot_id}:running", 0)


def start_bot_thread(bot_id: str, init_data: dict, setup_data: dict) -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot_config = dict_to_bot_init_config(init_data)
    agent_config = dict_to_agent_setup_config(setup_data)
    my_bot = MyBot(bot_config)
    my_bot.setup_my_agent(agent_config)
    running_bots[bot_id] = (threading.current_thread(), my_bot, loop)
    loop.run_until_complete(my_bot.run())


def monitor_bots() -> None:
    while True:
        bot_ids = redis_client.smembers("bots:all")
        for bot_id in bot_ids:
            running = redis_client.get(f"bot:{bot_id}:running")
            stop_flag = redis_client.get(f"bot:{bot_id}:stop_flag")
            should_run = redis_client.get(f"bot:{bot_id}:should_run")
            # Start bot
            if should_run == "1" and running == "0" and bot_id not in running_bots:
                lock = None
                try:
                    lock = redlock.lock(f"lock:bot:{bot_id}:start", 10000)
                    if not lock:
                        continue
                    logger.info(f"[Redlock] Acquired lock for {bot_id}, launching...")
                    redis_client.set(f"bot:{bot_id}:running", 1)
                    init_data, setup_data = load_bot_from_redis(bot_id)
                    if init_data:
                        t = threading.Thread(
                            target=start_bot_thread,
                            args=(bot_id, init_data, setup_data),
                            daemon=True,
                        )
                        t.start()
                finally:
                    if lock:
                        redlock.unlock(lock)
            # Stop bot
            if stop_flag == "1" and bot_id in running_bots:
                logger.info(f"Detected bot {bot_id} should stop, stopping...")
                thread, my_bot, loop = running_bots[bot_id]
                try:
                    if my_bot is not None:
                        asyncio.run_coroutine_threadsafe(
                            my_bot.close_bot_session(), loop
                        )
                except Exception as e:
                    logger.error(f"Error closing bot {bot_id}: {e}", exc_info=True)
                redis_client.set(f"bot:{bot_id}:running", 0)
                redis_client.set(f"bot:{bot_id}:stop_flag", 0)
                redis_client.set(f"bot:{bot_id}:should_run", 0)
                del running_bots[bot_id]
        time.sleep(3)

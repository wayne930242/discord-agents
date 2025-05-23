import time
import threading
from discord_agents.domain.bot import MyBotInitConfig, MyAgentSetupConfig, MyBot
from discord_agents.utils.logger import get_logger
from discord_agents.scheduler.broker import BotRedisClient

logger = get_logger("worker")


class BotManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._bot_map = {}
                    cls._instance._thread_map = {}
                    cls._instance._monitor_thread = None
                    cls._instance._monitor_running = False
        return cls._instance

    def add_bot_and_run(self, bot_id: str, my_bot: MyBot):
        if bot_id in self._bot_map:
            logger.warning(f"Bot {bot_id} already exists in manager.")
            return
        self._bot_map[bot_id] = my_bot
        t = threading.Thread(target=lambda: self._run_bot(bot_id, my_bot), daemon=True)
        self._thread_map[bot_id] = t
        t.start()
        logger.info(f"Bot {bot_id} started and added to manager.")

    def _run_bot(self, bot_id: str, my_bot: MyBot):
        import asyncio

        try:
            asyncio.run(my_bot.run())
        except Exception as e:
            logger.error(f"Error running bot {bot_id}: {e}")
            self.remove_bot(bot_id)

    def remove_bot(self, bot_id: str):
        my_bot = self._bot_map.get(bot_id)
        if my_bot:
            import asyncio
            import concurrent.futures

            def stop_bot():
                try:
                    if hasattr(my_bot, 'loop') and my_bot.loop.is_running() and not my_bot.loop.is_closed():
                        future = asyncio.run_coroutine_threadsafe(my_bot.stop(), my_bot.loop)
                        try:
                            future.result()
                        except concurrent.futures.CancelledError:
                            logger.error(f"Stop coroutine for bot {bot_id} was cancelled.")
                        except Exception as e:
                            logger.error(f"Exception while stopping bot {bot_id}: {e}")
                    else:
                        logger.warning(f"Event loop for bot {bot_id} is not running or already closed.")
                except Exception as e:
                    logger.error(f"Exception in stop_bot thread for bot {bot_id}: {e}")

            stop_thread = threading.Thread(target=stop_bot)
            stop_thread.start()
            logger.info(f"Bot {bot_id} stopped and removed from manager.")
            del self._bot_map[bot_id]
            if bot_id in self._thread_map:
                del self._thread_map[bot_id]
        else:
            logger.warning(f"Bot {bot_id} not found in manager.")

    def get_bot(self, bot_id: str):
        return self._bot_map.get(bot_id)

    def all_bots(self):
        return list(self._bot_map.keys())

    def start(self):
        if self._monitor_thread and self._monitor_thread.is_alive():
            logger.info("BotManager monitor thread already running.")
            return
        self._monitor_running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("BotManager monitor thread started.")

    def stop(self):
        self._monitor_running = False
        if self._monitor_thread:
            self._monitor_thread.join()
            logger.info("BotManager monitor thread stopped.")

    def _monitor_loop(self):
        from discord_agents.scheduler.broker import BotRedisClient
        from discord_agents.scheduler.tasks import listen_bots_task

        redis_broker = BotRedisClient()
        while self._monitor_running:
            all_status = redis_broker.get_all_bot_status()
            bot_ids = redis_broker.get_all_bots()
            for bot_id in bot_ids:
                listen_bots_task(bot_id)
            time.sleep(3)


bot_manager = BotManager()


def load_bot_from_redis(bot_id: str) -> tuple[MyBotInitConfig, MyAgentSetupConfig]:
    redis_broker = BotRedisClient()
    init_data = redis_broker.get_init_config(bot_id)
    setup_data = redis_broker.get_setup_config(bot_id)
    if not init_data or not setup_data:
        logger.error(f"Bot {bot_id} init/setup data not found in redis")
        return None, None
    return init_data, setup_data

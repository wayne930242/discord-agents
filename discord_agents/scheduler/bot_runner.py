from typing import Dict, Optional
import asyncio
import threading

from discord_agents.domain.bot import MyBot
from discord_agents.utils.logger import get_logger

logger = get_logger("bot_runner")


class BotRunner:
    def __init__(self) -> None:
        self._bots: Dict[str, MyBot] = {}
        self._running_tasks: Dict[str, Dict] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        self._main_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._main_loop)

    def register_bot(self, bot_id: str, bot: MyBot) -> None:
        if bot_id in self._bots:
            logger.error(f"Bot registration failed: ID {bot_id} already exists.")
            raise ValueError(f"Bot with ID {bot_id} already exists")
        self._bots[bot_id] = bot
        logger.info(f"Bot {bot_id} registered successfully.")

    def start_bot(self, bot_id: str) -> None:
        logger.info(f"Bot {bot_id} start...")

        if bot_id not in self._bots:
            logger.error(f"Bot {bot_id} not registered")
            raise ValueError(f"Bot {bot_id} not registered")

        if bot_id in self._running_tasks:
            logger.warning(f"Bot {bot_id} already running")
            raise ValueError(f"Bot {bot_id} already running")

        try:
            logger.info(f"Create stop event for bot {bot_id}")
            stop_event = threading.Event()

            logger.info(f"Create thread for bot {bot_id}")
            thread = threading.Thread(
                target=self._run_bot, args=(bot_id, stop_event), daemon=True
            )

            if bot_id in self._running_tasks:
                logger.info(f"Clean old thread for bot {bot_id}")
                old_task = self._running_tasks[bot_id]
                old_task["stop_event"].set()
                if old_task["thread"].is_alive():
                    old_task["thread"].join(timeout=5.0)

            logger.info(f"Start thread for bot {bot_id} successfully")
            thread.start()

            self._running_tasks[bot_id] = {
                "thread": thread,
                "stop_event": stop_event,
                "bot": self._bots[bot_id],
            }
            logger.info(f"Bot {bot_id} start successfully")

        except Exception as e:
            logger.error(f"Error starting bot {bot_id}: {str(e)}", exc_info=True)
            if bot_id in self._running_tasks:
                del self._running_tasks[bot_id]
            raise

    def stop_bot(self, bot_id: str) -> None:
        if bot_id not in self._running_tasks:
            logger.warning(f"Bot {bot_id} is not running")
            return

        task_info = self._running_tasks.pop(bot_id)
        stop_event = task_info["stop_event"]
        thread = task_info["thread"]

        logger.info(f"Stopping bot {bot_id}...")
        stop_event.set()
        
        try:
            if thread.is_alive():
                thread.join(timeout=5.0)
            logger.info(f"Bot {bot_id} stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping bot {bot_id}: {str(e)}", exc_info=True)

    def start_all_bots(self) -> None:
        logger.info("Attempting to start all registered bots.")
        for bot_id in list(self._bots.keys()):
            if bot_id not in self._running_tasks:
                logger.info(f"Calling start_bot for {bot_id} as part of start_all.")
                try:
                    self.start_bot(bot_id)
                except Exception as e:
                    logger.error(
                        f"Failed to start bot {bot_id} during start_all: {str(e)}",
                        exc_info=True,
                    )
            else:
                logger.info(
                    f"Bot {bot_id} is already considered running, skipped in start_all."
                )
        logger.info("Finished attempt to start all bots.")

    def stop_all_bots(self) -> None:
        for bot_id in list(self._running_tasks.keys()):
            self.stop_bot(bot_id)
        return

    def get_bot(self, bot_id: str) -> Optional[MyBot]:
        return self._bots.get(bot_id)

    def get_running_bots(self) -> Dict[str, MyBot]:
        active_running_bots = {}
        logger.info(
            f"Checking running bots. Current running tasks: {list(self._running_tasks.keys())}"
        )

        for bot_id, task_info in self._running_tasks.items():
            try:
                bot = self._bots[bot_id]
                if bot.is_running():
                    active_running_bots[bot_id] = bot
                    logger.info(f"Bot {bot_id} is running")
                else:
                    logger.info(f"Bot {bot_id} is not running")
                    if bot_id in self._running_tasks:
                        del self._running_tasks[bot_id]
                        logger.info(f"Removed bot {bot_id} from running tasks")
            except Exception as e:
                logger.error(
                    f"Error checking bot {bot_id} status: {str(e)}", exc_info=True
                )
                if bot_id in self._running_tasks:
                    del self._running_tasks[bot_id]
                    logger.info(f"Removed bot {bot_id} from running tasks due to error")

        logger.info(f"Active running bots: {list(active_running_bots.keys())}")
        return active_running_bots

    def get_registered_bots(self) -> Dict[str, MyBot]:
        return self._bots.copy()

    def _run_bot(self, bot_id: str, stop_event: threading.Event) -> None:
        logger.info(f"Start bot {bot_id} in thread")
        try:
            bot = self._bots[bot_id]

            async def run_bot():
                try:
                    logger.info(f"Start running bot {bot_id}")
                    await bot.run()
                except Exception as e:
                    logger.error(f"Error in run_bot: {str(e)}", exc_info=True)
                    raise

            async def check_stop():
                logger.info(f"Start monitoring stop signal for bot {bot_id}")
                while not stop_event.is_set():
                    await asyncio.sleep(1)
                logger.info(f"Bot {bot_id} received stop signal")
                try:
                    await bot.close_bot_session()
                except Exception as e:
                    logger.error(f"Error closing bot in check_stop: {e}", exc_info=True)

            logger.info(f"Create stop check task for bot {bot_id}")
            self._main_loop.create_task(check_stop())

            try:
                self._main_loop.run_until_complete(run_bot())
            except Exception as e:
                logger.error(f"Error running bot {bot_id}: {str(e)}", exc_info=True)
                if bot_id in self._running_tasks:
                    del self._running_tasks[bot_id]

        except Exception as e:
            logger.error(f"Error running bot {bot_id}: {str(e)}", exc_info=True)
            if bot_id in self._running_tasks:
                del self._running_tasks[bot_id]
        finally:
            logger.info(f"Bot {bot_id} thread finished")

    def __del__(self):
        try:
            if self._main_loop.is_running():
                self._main_loop.stop()
            if not self._main_loop.is_closed():
                self._main_loop.close()
        except Exception as e:
            logger.error(f"Error cleaning up main loop: {str(e)}", exc_info=True)

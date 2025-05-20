from redis import Redis
from discord_agents.env import REDIS_URL
from discord_agents.utils.logger import get_logger
from discord_agents.domain.bot import MyBot, MyBotInitConfig, MyAgentSetupConfig
from typing import Optional
import json
from redlock import Redlock

logger = get_logger("broker")


class BotRedisClient:
    _instance = None
    _redlock: Redlock = None
    _client: Redis

    BOT_STATE_KEY = "bot:{bot_id}:state"
    LOCK_STARTING_KEY = "lock:bot:{bot_id}:starting"
    LOCK_STOPPING_KEY = "lock:bot:{bot_id}:stopping"
    VALID_STATES = {
        "idle",
        "should_start",
        "starting",
        "running",
        "should_stop",
        "stopping",
    }
    BOT_INIT_CONFIG_KEY = "bot:{bot_id}:init_config"
    BOT_SETUP_CONFIG_KEY = "bot:{bot_id}:setup_config"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = Redis.from_url(REDIS_URL, decode_responses=True)
            cls._instance._redlock = Redlock([REDIS_URL])
        return cls._instance

    def get_state(self, bot_id: str) -> str:
        try:
            state = self._client.get(self.BOT_STATE_KEY.format(bot_id=bot_id))
            return state or "idle"
        except Exception as e:
            logger.error(f"[Redis Error] get_state: {e}")
            return "idle"

    def set_state(self, bot_id: str, state: str) -> None:
        if state not in self.VALID_STATES:
            logger.error(f"[State Error] Invalid state: {state}")
            return
        try:
            self._client.set(self.BOT_STATE_KEY.format(bot_id=bot_id), state)
        except Exception as e:
            logger.error(f"[Redis Error] set_state: {e}")

    def _acquire_lock(self, lock_key: str, expire_ms: int = 10000):
        lock = self._redlock.lock(lock_key, expire_ms)
        if not lock:
            logger.warning(f"[Redlock] Failed to acquire lock: {lock_key}")
        return lock

    def set_should_start(
        self,
        bot_id: str,
        init_config: Optional[MyBotInitConfig] = None,
        setup_config: Optional[MyAgentSetupConfig] = None,
    ) -> None:
        if init_config:
            self._client.set(
                self.BOT_INIT_CONFIG_KEY.format(bot_id=bot_id), json.dumps(init_config)
            )
        if setup_config:
            self._client.set(
                self.BOT_SETUP_CONFIG_KEY.format(bot_id=bot_id),
                json.dumps(setup_config),
            )
        self.set_state(bot_id, "should_start")

    def set_should_stop(self, bot_id: str) -> None:
        self.set_state(bot_id, "should_stop")

    def lock_and_set_starting_if_should_start(
        self, bot_id: str, expire_ms: int = 10000
    ) -> bool:
        lock = self._acquire_lock(
            self.LOCK_STARTING_KEY.format(bot_id=bot_id), expire_ms
        )
        if not lock:
            return False
        try:
            current = self.get_state(bot_id)
            if current == "should_start":
                self.set_state(bot_id, "starting")
                logger.info(f"[Redlock] Set state=starting for {bot_id}")
                return True
            else:
                return False
        finally:
            self._redlock.unlock(lock)

    def set_running(self, bot_id: str) -> None:
        self.set_state(bot_id, "running")

    def set_idle(self, bot_id: str) -> None:
        self.set_state(bot_id, "idle")

    def lock_and_set_stopping_if_should_stop(
        self, bot_id: str, expire_ms: int = 10000
    ) -> bool:
        lock = self._acquire_lock(
            self.LOCK_STOPPING_KEY.format(bot_id=bot_id), expire_ms
        )
        if not lock:
            return False
        try:
            current = self.get_state(bot_id)
            if current == "should_stop":
                self.set_state(bot_id, "stopping")
                logger.info(f"[Redlock] Set state=stopping for {bot_id}")
                return True
            else:
                return False
        finally:
            self._redlock.unlock(lock)

    def get_all_bots(self) -> list[str]:
        bot_ids = set()
        cursor = 0
        try:
            while True:
                cursor, keys = self._client.scan(
                    cursor=cursor, match="bot:*", count=100
                )
                for key in keys:
                    parts = key.split(":")
                    if len(parts) > 1:
                        bot_ids.add(parts[1])
                if cursor == 0:
                    break
        except Exception as e:
            logger.error(f"[Redis Error] get_all_bots: {e}")
        return list(bot_ids)

    def get_all_running_bots(self) -> list[str]:
        bot_ids = []
        cursor = 0
        try:
            while True:
                cursor, keys = self._client.scan(
                    cursor=cursor, match="bot:*:running", count=100
                )
                bot_ids.extend([key.split(":")[1] for key in keys])
                if cursor == 0:
                    break
        except Exception as e:
            logger.error(f"[Redis Error] get_all_running_bots: {e}")
        return bot_ids

    def get_all_bot_status(self) -> dict[str, dict[str, str]]:
        status = {}
        for bot_id in self.get_all_bots():
            status[bot_id] = self.get_state(bot_id)
        return status

    def reset_all_bots_status(self) -> None:
        for bot_id in self.get_all_bots():
            # Set idle
            self.set_idle(bot_id)
            # Clean up configs
            self._client.delete(self.BOT_INIT_CONFIG_KEY.format(bot_id=bot_id))
            self._client.delete(self.BOT_SETUP_CONFIG_KEY.format(bot_id=bot_id))
            # Clean up locks
            self._client.delete(self.LOCK_STARTING_KEY.format(bot_id=bot_id))
            self._client.delete(self.LOCK_STOPPING_KEY.format(bot_id=bot_id))

    def get_init_config(self, bot_id: str) -> Optional[MyBotInitConfig]:
        try:
            init_config = self._client.get(
                self.BOT_INIT_CONFIG_KEY.format(bot_id=bot_id)
            )
            return json.loads(init_config) if init_config else None
        except Exception as e:
            logger.error(f"[Redis Error] get_init_config: {e}")
            return None

    def get_setup_config(self, bot_id: str) -> Optional[MyAgentSetupConfig]:
        try:
            setup_config = self._client.get(
                self.BOT_SETUP_CONFIG_KEY.format(bot_id=bot_id)
            )
            return json.loads(setup_config) if setup_config else None
        except Exception as e:
            logger.error(f"[Redis Error] get_setup_config: {e}")
            return None

from redis import Redis
from discord_agents.core.config import settings
from discord_agents.utils.logger import get_logger
from discord_agents.domain.bot import MyBotInitConfig, MyAgentSetupConfig
from typing import Optional, Literal, Any, TypeVar, Generic, Type, Union
import json
from redlock import Redlock  # type: ignore
import time

logger = get_logger("broker")

# Type variable for generic type safety
T = TypeVar("T")


class SessionDataManager(Generic[T]):
    """Type-safe Redis-based session data manager for storing session-specific data"""

    def __init__(
        self,
        redis_client: Redis,
        key_prefix: str,
        data_type: Type[T],
        default_value: Optional[T] = None,
    ):
        self.redis_client = redis_client
        self.key_prefix = key_prefix
        self.data_type = data_type
        self.default_value = default_value

    def _get_key(self, session_id: str) -> str:
        """Generate Redis key for session data"""
        return f"{self.key_prefix}:{session_id}"

    def set(
        self, session_id: str, value: T, expire_seconds: Optional[int] = None
    ) -> None:
        """Set data for a specific session with type checking and optional expiration"""
        if not isinstance(value, self.data_type):
            raise TypeError(
                f"Expected {self.data_type.__name__}, got {type(value).__name__}"
            )

        try:
            key = self._get_key(session_id)
            serialized_value = json.dumps(value)
            if expire_seconds:
                self.redis_client.setex(key, expire_seconds, serialized_value)
            else:
                self.redis_client.set(key, serialized_value)
            logger.debug(f"📝 Set session data for {session_id}: {value}")
        except Exception as e:
            logger.error(
                f"[Redis Error] Failed to set session data for {session_id}: {e}"
            )

    def get(self, session_id: str) -> Optional[T]:
        """Get data for a specific session"""
        try:
            key = self._get_key(session_id)
            serialized_value = self.redis_client.get(key)
            if serialized_value is None:
                logger.debug(
                    f"📝 No session data for {session_id}, returning default: {self.default_value}"
                )
                return self.default_value

            value = json.loads(serialized_value)
            # Type checking: ensure the deserialized value matches expected type
            if not isinstance(value, self.data_type):
                logger.warning(
                    f"📝 Session data type mismatch for {session_id}, returning default"
                )
                return self.default_value

            logger.debug(f"📝 Get session data for {session_id}: {value}")
            return value
        except Exception as e:
            logger.error(
                f"[Redis Error] Failed to get session data for {session_id}: {e}"
            )
            return self.default_value

    def has(self, session_id: str) -> bool:
        """Check if session has data"""
        try:
            key = self._get_key(session_id)
            return self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(
                f"[Redis Error] Failed to check session data existence for {session_id}: {e}"
            )
            return False

    def clear(self, session_id: str) -> bool:
        """Clear data for a specific session. Returns True if data existed."""
        try:
            key = self._get_key(session_id)
            deleted = self.redis_client.delete(key)
            if deleted > 0:
                logger.debug(f"📝 Cleared session data for {session_id}")
                return True
            return False
        except Exception as e:
            logger.error(
                f"[Redis Error] Failed to clear session data for {session_id}: {e}"
            )
            return False

    def clear_all(self) -> int:
        """Clear all session data with this prefix. Returns number of keys deleted."""
        try:
            pattern = f"{self.key_prefix}:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.debug(
                    f"📝 Cleared {deleted} session data entries with prefix {self.key_prefix}"
                )
                return deleted
            return 0
        except Exception as e:
            logger.error(
                f"[Redis Error] Failed to clear all session data with prefix {self.key_prefix}: {e}"
            )
            return 0

    def set_expiration(self, session_id: str, expire_seconds: int) -> bool:
        """Set expiration time for existing session data"""
        try:
            key = self._get_key(session_id)
            return self.redis_client.expire(key, expire_seconds)
        except Exception as e:
            logger.error(
                f"[Redis Error] Failed to set expiration for {session_id}: {e}"
            )
            return False


class BotRedisClient:
    _instance: Optional["BotRedisClient"] = None
    _redlock: Redlock = None
    _client: Redis
    _session_data_manager: SessionDataManager[dict[str, Any]]

    BOT_STATE_KEY = "bot:{bot_id}:state"
    LOCK_STARTING_KEY = "lock:bot:{bot_id}:starting"
    LOCK_STOPPING_KEY = "lock:bot:{bot_id}:stopping"
    VALID_STATES = {
        "idle",
        "should_start",
        "starting",
        "should_restart",
        "running",
        "should_stop",
        "stopping",
    }
    BOT_INIT_CONFIG_KEY = "bot:{bot_id}:init_config"
    BOT_SETUP_CONFIG_KEY = "bot:{bot_id}:setup_config"
    HISTORY_KEY = "history:{model}"

    # Session data keys
    SESSION_DATA_KEY = "session:{session_id}:data"

    def __new__(cls) -> "BotRedisClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = Redis.from_url(
                settings.redis_url, decode_responses=True
            )
            cls._instance._redlock = Redlock([settings.redis_url])

            # Initialize session data manager
            cls._instance._session_data_manager = SessionDataManager[dict[str, Any]](
                cls._instance._client, "session_data", dict, {}
            )
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

    def _acquire_lock(self, lock_key: str, expire_ms: int = 10000) -> Any:
        """Acquire a distributed lock and return the lock object or None if failed"""
        lock = self._redlock.lock(lock_key, expire_ms)
        if not lock:
            logger.warning(f"[Redlock] Failed to acquire lock: {lock_key}")
            return None
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

    def set_should_restart(self, bot_id: str) -> None:
        self.set_state(bot_id, "should_restart")

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
    ) -> Literal["to_idle", "to_start", False]:
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
                return "to_idle"
            elif current == "should_restart":
                self.set_state(bot_id, "starting")
                logger.info(f"[Redlock] Set state=starting for {bot_id}")
                return "to_start"
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

    def get_all_bot_status(self) -> dict[str, str]:
        status: dict[str, str] = {}
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

    def clear_config(self, bot_id: str) -> None:
        self._client.delete(self.BOT_INIT_CONFIG_KEY.format(bot_id=bot_id))
        self._client.delete(self.BOT_SETUP_CONFIG_KEY.format(bot_id=bot_id))

    def add_message_history(
        self,
        model: str,
        text: str,
        tokens: int,
        interval_seconds: float = 0.0,
        timestamp: Optional[float] = None,
    ) -> None:
        if interval_seconds == 0 or timestamp is None or timestamp == float("inf"):
            return
        expire_at = timestamp + interval_seconds if interval_seconds > 0 else None
        key = self.HISTORY_KEY.format(model=model)
        item = json.dumps(
            {
                "text": text,
                "tokens": tokens,
                "timestamp": timestamp,
                "expire_at": expire_at,
            }
        )
        try:
            self._client.rpush(key, item)
        except Exception as e:
            logger.error(f"[Redis Error] add_message_history: {e}")

    def get_message_history(self, model: str) -> list[dict]:
        self.prune_message_history(model)
        key = self.HISTORY_KEY.format(model=model)
        now = time.time()
        result = []
        try:
            items = self._client.lrange(key, 0, -1)
            for item in items:
                try:
                    data = json.loads(item)
                    expire_at = data.get("expire_at")
                    if not expire_at or expire_at > now:
                        result.append(data)
                except Exception as e:
                    logger.warning(f"[History Parse Error] {e}")
        except Exception as e:
            logger.error(f"[Redis Error] get_message_history: {e}")
        return result

    def prune_message_history(self, model: str) -> None:
        key = self.HISTORY_KEY.format(model=model)
        now = time.time()
        try:
            items = self._client.lrange(key, 0, -1)
            keep_indices = []
            for idx, item in enumerate(items):
                try:
                    data = json.loads(item)
                    expire_at = data.get("expire_at")
                    if not expire_at or expire_at > now:
                        keep_indices.append(idx)
                except Exception as e:
                    logger.warning(f"[History Parse Error] {e}")
            if keep_indices:
                first, last = keep_indices[0], keep_indices[-1]
                self._client.ltrim(key, first, last)
            else:
                self._client.delete(key)
        except Exception as e:
            logger.error(f"[Redis Error] prune_message_history: {e}")

    # Session data management methods
    def get_session_data(self, session_id: str, key: str, default: Any = None) -> Any:
        """Get data for a session by key"""
        session_data = self._session_data_manager.get(session_id) or {}
        return session_data.get(key, default)

    def set_session_data(self, session_id: str, key: str, value: Any) -> None:
        """Set data for a session by key"""
        session_data = self._session_data_manager.get(session_id) or {}
        session_data[key] = value
        self._session_data_manager.set(session_id, session_data)

    def clear_session_data(self, session_id: str) -> bool:
        """Clear all data for a session"""
        return self._session_data_manager.clear(session_id)

from typing import Any, Optional, TYPE_CHECKING
from discord_agents.utils.logger import get_logger

if TYPE_CHECKING:
    from discord_agents.scheduler.broker import BotRedisClient

logger = get_logger("note_broker_service")


class NoteBrokerService:
    """Note session data management service using Redis"""

    def __init__(self) -> None:
        # Lazy import to avoid circular dependency
        from discord_agents.scheduler.broker import BotRedisClient

        self._redis_client = BotRedisClient()

    def get_session_data(self, session_id: str, key: str, default: Any = None) -> Any:
        """Get data for a session by key"""
        return self._redis_client.get_session_data(session_id, key, default)

    def set_session_data(self, session_id: str, key: str, value: Any) -> None:
        """Set data for a session by key"""
        self._redis_client.set_session_data(session_id, key, value)

    def get_session_note_ids(self, session_id: str) -> list[str]:
        """Get note IDs for a session"""
        note_ids = self.get_session_data(session_id, "note_ids", [])
        return note_ids if isinstance(note_ids, list) else []

    def add_session_note_id(self, session_id: str, note_id: str) -> None:
        """Add a note ID to a session"""
        current_ids = self.get_session_note_ids(session_id)
        if note_id not in current_ids:
            current_ids.append(note_id)
            self.set_session_data(session_id, "note_ids", current_ids)
            logger.info(f"📝 Added note ID {note_id} to session {session_id}")

    def remove_session_note_id(self, session_id: str, note_id: str) -> bool:
        """Remove a note ID from a session. Returns True if removed."""
        current_ids = self.get_session_note_ids(session_id)
        if note_id in current_ids:
            current_ids.remove(note_id)
            self.set_session_data(session_id, "note_ids", current_ids)
            logger.info(f"📝 Removed note ID {note_id} from session {session_id}")
            return True
        return False

    def clear_session_data(self, session_id: str) -> bool:
        """Clear all data for a session"""
        result = self._redis_client.clear_session_data(session_id)
        if result:
            logger.info(f"📝 Cleared session data for {session_id}")
        return result


# Singleton instance
_note_broker_service: Optional[NoteBrokerService] = None


def get_note_broker_service() -> NoteBrokerService:
    """Get the singleton note broker service instance"""
    global _note_broker_service
    if _note_broker_service is None:
        _note_broker_service = NoteBrokerService()
    return _note_broker_service

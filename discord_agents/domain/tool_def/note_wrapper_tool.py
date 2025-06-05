from typing import Any, Optional, Dict
from google.adk.tools import FunctionTool
from discord_agents.domain.tool_def.note_tool import note_tool
from discord_agents.utils.logger import get_logger

logger = get_logger("note_wrapper_tool")

# Global variable to store current session ID
_current_session_id: Optional[str] = None
_current_user_adk_id: Optional[str] = None


def set_note_session_id(session_id: str) -> None:
    """Set the current session ID for note operations"""
    global _current_session_id
    _current_session_id = session_id
    logger.info(f"📝 Set global session_id: {session_id}")


def set_note_user_adk_id(user_adk_id: str) -> None:
    """Set the current user ADK ID for session recovery"""
    global _current_user_adk_id
    _current_user_adk_id = user_adk_id
    logger.debug(f"📝 Set global user_adk_id: {user_adk_id}")


def _recover_session_id() -> Optional[str]:
    """Try to recover session_id by finding the latest session for current user"""
    global _current_user_adk_id

    if not _current_user_adk_id:
        logger.warning("📝 Cannot recover session_id: no user_adk_id available")
        return None

    try:
        # Import here to avoid circular imports
        from google.adk.sessions import DatabaseSessionService
        from discord_agents.env import DATABASE_URL

        session_service = DatabaseSessionService(DATABASE_URL)

        # Try different common app names or get from environment
        app_names_to_try = ["gm_test", "discord_agent", "agent"]

        for app_name in app_names_to_try:
            try:
                sessions_resp = session_service.list_sessions(
                    app_name=app_name,
                    user_id=_current_user_adk_id
                )
                session_list = getattr(sessions_resp, "sessions", [])

                if session_list:
                    # Get the most recent session
                    latest_session = max(session_list, key=lambda s: getattr(s, 'created_at', 0))
                    recovered_session_id = str(latest_session.id)
                    logger.info(f"📝 Recovered session_id: {recovered_session_id} for user: {_current_user_adk_id} (app: {app_name})")
                    return recovered_session_id
            except Exception as e:
                logger.debug(f"📝 No sessions found for app_name: {app_name}, trying next...")
                continue

        logger.warning(f"📝 No sessions found for user: {_current_user_adk_id} in any app")
        return None

    except Exception as e:
        logger.error(f"📝 Failed to recover session_id: {str(e)}", exc_info=True)
        return None


async def notes_function(
    action: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    note_id: Optional[str] = None,
    tags: Optional[str] = None,
    query: Optional[str] = None,
) -> str:
    """
    Note management tool - create, read, update, delete, and search notes for your current session.

    Args:
        action (str): The action to perform. Must be one of: "create", "list", "get", "update", "delete", "search"
        title (Optional[str]): Title for the note (required for create, optional for update)
        content (Optional[str]): Content for the note (required for create, optional for update)
        note_id (Optional[str]): ID of the note (required for get, update, delete)
        tags (Optional[str]): JSON string of tags (optional for create/update)
        query (Optional[str]): Search query (required for search)

    Returns:
        str: Result message

    Usage examples:
    - Create note: action="create", title="Today's Learning", content="Learned about Python"
    - View all notes: action="list"
    - Search notes: action="search", query="Python"
    - Get specific note: action="get", note_id="123"
    - Update note: action="update", note_id="123", title="New Title", content="New Content"
    - Delete note: action="delete", note_id="123"
    """
    logger.info(
        f"📝 Notes function called: action={action}, title={title[:50] if title else 'None'}..., note_id={note_id or 'None'}"
    )

    global _current_session_id

    # If no session_id, try to recover it
    if not _current_session_id:
        logger.info("📝 No current session_id, attempting to recover...")
        _current_session_id = _recover_session_id()

        if _current_session_id:
            logger.info(f"📝 Successfully recovered session_id: {_current_session_id}")
        else:
            return "❌ Error: No active session found. Please start a new conversation to create a session."

    try:
        # Map function parameters to note_tool.call kwargs
        kwargs = {}
        if title:
            kwargs["title"] = title
        if content:
            kwargs["content"] = content
        if note_id:
            kwargs["note_id"] = note_id
        if tags:
            kwargs["tags"] = tags
        if query:
            kwargs["query"] = query

        logger.info(
            f"📝 Calling note_tool with session_id={_current_session_id}, action={action}, kwargs={kwargs}"
        )
        result = await note_tool.call(_current_session_id, action, **kwargs)
        logger.info(f"📝 Note operation result: {result[:100]}...")
        return result
    except Exception as e:
        logger.error(f"❌ Note operation failed: {str(e)}", exc_info=True)
        return f"❌ Note operation failed: {str(e)}"


# Create the wrapper tool instance
logger.info("📝 Creating note_wrapper_tool as FunctionTool...")
note_wrapper_tool = FunctionTool(notes_function)
logger.info(
    f"✅ note_wrapper_tool created: {type(note_wrapper_tool).__name__} (name='{note_wrapper_tool.name}')"
)


# Export the session setter for backward compatibility
def set_session_id(session_id: str) -> None:
    """Backward compatibility function"""
    set_note_session_id(session_id)

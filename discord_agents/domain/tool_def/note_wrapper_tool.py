from typing import Any, Optional
from google.adk.tools import FunctionTool, ToolContext
from discord_agents.domain.tool_def.note_tool import note_tool
from discord_agents.utils.logger import get_logger

logger = get_logger("note_wrapper_tool")

# Note broker service for persistent session data storage (lazy loaded)
_note_broker: Any | None = None


def _get_note_broker() -> Any:
    """Get note broker service with lazy initialization"""
    global _note_broker
    if _note_broker is None:
        from discord_agents.scheduler.note_broker_service import get_note_broker_service
        _note_broker = get_note_broker_service()
    return _note_broker


# Session data management functions using Note Broker Service
def get_session_note_ids(session_id: str) -> list[str]:
    """Get note IDs for a session"""
    result = _get_note_broker().get_session_note_ids(session_id)
    return result if isinstance(result, list) else []


def add_session_note_id(note_id: str, session_id: str) -> None:
    """Add a note ID to a session"""
    _get_note_broker().add_session_note_id(session_id, note_id)


def remove_session_note_id(note_id: str, session_id: str) -> bool:
    """Remove a note ID from a session. Returns True if removed."""
    result = _get_note_broker().remove_session_note_id(session_id, note_id)
    return bool(result)


def set_session_data(key: str, value: Any, session_id: str) -> None:
    """Set data for a session by key"""
    _get_note_broker().set_session_data(session_id, key, value)


def get_session_data(key: str, default: Any, session_id: str) -> Any:
    """Get data for a session by key"""
    return _get_note_broker().get_session_data(session_id, key, default)


async def notes_function(
    action: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    note_id: Optional[str] = None,
    tags: Optional[str] = None,
    query: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
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
    # Get session ID from the Google ADK tool context
    # The ToolContext provides access to the InvocationContext which contains the Session
    session_id = None
    if tool_context and hasattr(tool_context, "_invocation_context"):
        invocation_context = tool_context._invocation_context
        if hasattr(invocation_context, "session") and hasattr(
            invocation_context.session, "id"
        ):
            session_id = invocation_context.session.id
            logger.info(f"📝 Got session ID from ADK context: {session_id}")
        else:
            logger.error("📝 No session found in invocation context")
            return "❌ Error: No session available in invocation context."
    else:
        logger.error("📝 No tool_context or invocation_context available")
        return "❌ Error: No tool context available. Please ensure this tool is called from within an agent."

    logger.info(
        f"📝 Notes function called: action={action}, session_id={session_id}, title={title[:50] if title else 'None'}..., note_id={note_id or 'None'}"
    )

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
            f"📝 Calling note_tool with session_id={session_id}, action={action}, kwargs={kwargs}"
        )
        result = await note_tool.call(session_id, action, **kwargs)
        logger.info(f"📝 Note operation result: {result[:100]}...")

        # Track note IDs for session data management
        if action == "create" and "Note ID:" in result:
            # Extract note ID from create result
            try:
                import re

                note_id_match = re.search(r"Note ID: (\w+)", result)
                if note_id_match:
                    created_note_id = note_id_match.group(1)
                    add_session_note_id(created_note_id, session_id)
                    logger.info(
                        f"📝 Added note ID {created_note_id} to session {session_id}"
                    )
            except Exception as track_error:
                logger.warning(f"📝 Failed to track created note ID: {track_error}")

        elif action == "delete" and note_id:
            # Remove note ID from session tracking
            if remove_session_note_id(note_id, session_id):
                logger.info(f"📝 Removed note ID {note_id} from session {session_id}")

        return result
    except Exception as e:
        logger.error(f"❌ Note operation failed: {str(e)}", exc_info=True)
        return f"❌ Note operation failed: {str(e)}"


# Create the wrapper tool instance
logger.info("📝 Creating note_wrapper_tool as FunctionTool...")
note_wrapper_tool: FunctionTool = FunctionTool(notes_function)
logger.info(
    f"✅ note_wrapper_tool created: {type(note_wrapper_tool).__name__} (name='{note_wrapper_tool.name}')"
)

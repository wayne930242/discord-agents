from typing import Any, Optional, Dict
from google.adk.tools import FunctionTool
from discord_agents.domain.tool_def.note_tool import note_tool
from discord_agents.utils.logger import get_logger

logger = get_logger("note_wrapper_tool")

# Global variable to store current session ID
_current_session_id: Optional[str] = None


def set_note_session_id(session_id: str) -> None:
    """Set the current session ID for note operations"""
    global _current_session_id
    _current_session_id = session_id
    logger.info(f"📝 Set global session_id: {session_id}")


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

    # Check if session_id is available
    if not _current_session_id:
        logger.error("📝 No session_id available for note operations")
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

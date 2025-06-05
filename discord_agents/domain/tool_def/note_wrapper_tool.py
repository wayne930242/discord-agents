from typing import Any, Optional
from google.adk.tools.base_tool import BaseTool
from discord_agents.domain.tool_def.note_tool import note_tool
from discord_agents.utils.logger import get_logger

logger = get_logger("note_wrapper_tool")


class NoteWrapperTool(BaseTool):
    """A wrapper tool that automatically provides session_id to the note tool"""

    def __init__(self) -> None:
        super().__init__(
            name="notes",
            description="""Note management tool - create, read, update, delete, and search notes for your current session.

Usage examples:
- Create note: "Record today's Python learning"
- View all notes: "Show my note list" or "List all my notes"
- Search notes: "Search for notes containing Python"
- Get specific note: "Show me the note with title 'Python learning'" (search first, then get by ID)
- Update note: "Update my Python note with new content" (search first, then update by ID)
- Delete note: "Delete my Python learning note" (search first, then delete by ID)

Note: For operations requiring specific note IDs, first list or search to find the note ID, then reference it.""",
        )
        self._current_session_id: Optional[str] = None

    def set_session_id(self, session_id: str) -> None:
        """Set the current session ID"""
        self._current_session_id = session_id

    async def call(self, action: str, **kwargs: Any) -> str:
        """
        Call the note tool with the current session ID

        Args:
            action: The action to perform (create, list, get, update, delete, search)
            **kwargs: Additional arguments for the action
        """
        if not self._current_session_id:
            return "Error: Unable to get current session ID"

        try:
            return await note_tool.call(self._current_session_id, action, **kwargs)
        except Exception as e:
            logger.error(f"Note wrapper tool error: {str(e)}", exc_info=True)
            return f"Note operation failed: {str(e)}"


# Create the wrapper tool instance
note_wrapper_tool = NoteWrapperTool()

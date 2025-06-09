import json
import os
from typing import Dict, Any, List, Optional, Tuple
from google.adk.tools.base_tool import BaseTool
from discord_agents.core.config import settings
from discord_agents.utils.logger import get_logger

logger = get_logger("note_tool")


class NoteTool(BaseTool):
    """A tool for managing notes using MCP Toolbox"""

    def __init__(self) -> None:
        super().__init__(
            name="note_manager",
            description="Manage notes - create, read, update, delete, search notes for the current session",
        )
        self._toolbox_client: Optional[Any] = None
        self._tools: Optional[Dict[str, Any]] = None

    def _get_db_config(self) -> Dict[str, str]:
        """Extract database configuration from DATABASE_URL"""
        # Parse DATABASE_URL (format: postgresql://user:password@host:port/database)
        if not settings.database_url:
            raise ValueError("DATABASE_URL is not configured")

        import urllib.parse

        parsed = urllib.parse.urlparse(settings.database_url)

        return {
            "DB_HOST": parsed.hostname or "localhost",
            "DB_PORT": str(parsed.port or 5432),
            "DB_NAME": parsed.path.lstrip("/") if parsed.path else "postgres",
            "DB_USER": parsed.username or "postgres",
            "DB_PASSWORD": parsed.password or "",
        }

    def _initialize_toolbox(self) -> None:
        """Initialize the MCP Toolbox client"""
        if self._toolbox_client is not None:
            return

        try:
            # Set environment variables for database connection
            db_config = self._get_db_config()
            for key, value in db_config.items():
                os.environ[key] = value

            # Initialize the toolbox client
            tools_yaml_path = os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                ),
                "data",
                "tools.yaml",
            )

            logger.info(f"Initializing MCP Toolbox with config: {tools_yaml_path}")

            # For now, we'll create a simple wrapper that simulates MCP functionality
            # until we can set up the full MCP server
            self._tools = {
                "create-note": self._create_note_direct,
                "list-notes": self._list_notes_direct,
                "get-note": self._get_note_direct,
                "update-note": self._update_note_direct,
                "delete-note": self._delete_note_direct,
                "search-notes": self._search_notes_direct,
            }

            logger.info("MCP Toolbox initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize MCP Toolbox: {str(e)}", exc_info=True)
            raise

    def _execute_sql(
        self, query: str, params: Tuple[Any, ...] = ()
    ) -> List[Dict[str, Any]]:
        """Execute SQL query directly using psycopg2"""
        import psycopg2
        import psycopg2.extras

        conn = None
        try:
            conn = psycopg2.connect(settings.database_url)
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                # Always commit the transaction
                conn.commit()

                if cursor.description:
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
                else:
                    return []
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"SQL execution error: {str(e)}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close()

    def _create_note_direct(
        self, session_id: str, title: str, content: str, tags: str = "[]"
    ) -> Dict[str, Any]:
        """Create a new note directly"""
        try:
            tags_json = json.loads(tags) if tags else []
        except json.JSONDecodeError:
            tags_json = []

        query = """
            INSERT INTO notes (session_id, title, content, tags, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            RETURNING id, title, created_at;
        """
        result = self._execute_sql(
            query, (session_id, title, content, json.dumps(tags_json))
        )
        return result[0] if result else {}

    def _list_notes_direct(self, session_id: str) -> List[Dict[str, Any]]:
        """List all notes for a session"""
        query = """
            SELECT id, title, content, tags, created_at, updated_at
            FROM notes
            WHERE session_id = %s
            ORDER BY created_at DESC;
        """
        return self._execute_sql(query, (session_id,))

    def _get_note_direct(self, session_id: str, note_id: str) -> Dict[str, Any]:
        """Get a specific note"""
        query = """
            SELECT id, title, content, tags, created_at, updated_at
            FROM notes
            WHERE session_id = %s AND id = %s;
        """
        result = self._execute_sql(query, (session_id, note_id))
        return result[0] if result else {}

    def _update_note_direct(
        self,
        session_id: str,
        note_id: str,
        title: str = "",
        content: str = "",
        tags: str = "",
    ) -> Dict[str, Any]:
        """Update an existing note"""
        # Build dynamic update query
        updates = []
        params = []

        if title:
            updates.append("title = %s")
            params.append(title)
        if content:
            updates.append("content = %s")
            params.append(content)
        if tags:
            try:
                tags_json = json.loads(tags)
                updates.append("tags = %s")
                params.append(json.dumps(tags_json))
            except json.JSONDecodeError:
                pass

        if not updates:
            return {"error": "No fields to update"}

        updates.append("updated_at = NOW()")
        params.extend([session_id, note_id])

        query = f"""
            UPDATE notes
            SET {', '.join(updates)}
            WHERE session_id = %s AND id = %s
            RETURNING id, title, updated_at;
        """
        result = self._execute_sql(query, tuple(params))
        return result[0] if result else {}

    def _delete_note_direct(self, session_id: str, note_id: str) -> Dict[str, Any]:
        """Delete a note"""
        query = """
            DELETE FROM notes
            WHERE session_id = %s AND id = %s
            RETURNING id, title;
        """
        result = self._execute_sql(query, (session_id, note_id))
        return result[0] if result else {}

    def _search_notes_direct(self, session_id: str, query: str) -> List[Dict[str, Any]]:
        """Search notes by title or content"""
        sql_query = """
            SELECT id, title, content, tags, created_at, updated_at
            FROM notes
            WHERE session_id = %s
            AND (title ILIKE %s OR content ILIKE %s)
            ORDER BY created_at DESC;
        """
        search_pattern = f"%{query}%"
        return self._execute_sql(
            sql_query, (session_id, search_pattern, search_pattern)
        )

    def _delete_notes_by_session(self, session_id: str) -> int:
        """Delete all notes for a specific session and return count of deleted notes"""
        query = """
            DELETE FROM notes
            WHERE session_id = %s
            RETURNING id;
        """
        try:
            result = self._execute_sql(query, (session_id,))
            deleted_count = len(result) if result else 0
            logger.info(f"Deleted {deleted_count} notes for session {session_id}")
            return deleted_count
        except Exception as e:
            logger.error(
                f"Failed to delete notes for session {session_id}: {str(e)}",
                exc_info=True,
            )
            return 0

    async def call(self, session_id: str, action: str, **kwargs: Any) -> str:
        """
        Main entry point for the note tool

        Args:
            session_id: The session ID for the current conversation
            action: The action to perform (create, list, get, update, delete, search)
            **kwargs: Additional arguments based on the action
        """
        try:
            self._initialize_toolbox()

            if action == "create":
                title = kwargs.get("title", "")
                content = kwargs.get("content", "")
                tags = kwargs.get("tags", "[]")

                if not title or not content:
                    return "Error: Title and content are required."

                result = self._create_note_direct(session_id, title, content, tags)
                return f"Note created! ID: {result.get('id')}, Title: {result.get('title')}"

            elif action == "list":
                results = self._list_notes_direct(session_id)
                if not results:
                    return "No notes found."

                notes_text = "📝 Your note list:\n\n"
                for note in results:
                    tags_str = (
                        ", ".join(note.get("tags", [])) if note.get("tags") else ""
                    )
                    notes_text += f"**ID {note['id']}**: {note['title']}\n"
                    if tags_str:
                        notes_text += f"    Tags: {tags_str}\n"
                    notes_text += f"    Created at: {note['created_at']}\n\n"

                return notes_text

            elif action == "get":
                note_id = kwargs.get("note_id", "")
                if not note_id:
                    return "Error: Note ID is required."

                result = self._get_note_direct(session_id, note_id)
                if not result:
                    return f"No note found with ID {note_id}."

                tags_str = (
                    ", ".join(result.get("tags", [])) if result.get("tags") else "None"
                )
                return (
                    f"📄 **Note details**\n\n"
                    f"**ID**: {result['id']}\n"
                    f"**Title**: {result['title']}\n"
                    f"**Content**: {result['content']}\n"
                    f"**Tags**: {tags_str}\n"
                    f"**Created at**: {result['created_at']}\n"
                    f"**Updated at**: {result['updated_at']}"
                )

            elif action == "update":
                note_id = kwargs.get("note_id", "")
                if not note_id:
                    return "Error: Note ID is required."

                title = kwargs.get("title", "")
                content = kwargs.get("content", "")
                tags = kwargs.get("tags", "")

                result = self._update_note_direct(
                    session_id, note_id, title, content, tags
                )
                if "error" in result:
                    return f"Error: {result['error']}"
                if not result:
                    return f"No note found with ID {note_id}."

                return f"Note updated! ID: {result.get('id')}, Title: {result.get('title')}"

            elif action == "delete":
                note_id = kwargs.get("note_id", "")
                if not note_id:
                    return "Error: Note ID is required."

                result = self._delete_note_direct(session_id, note_id)
                if not result:
                    return f"No note found with ID {note_id}."

                return f"Note deleted! ID: {result.get('id')}, Title: {result.get('title')}"

            elif action == "search":
                query = kwargs.get("query", "")
                if not query:
                    return "Error: Search query is required."

                results = self._search_notes_direct(session_id, query)
                if not results:
                    return f"No notes found containing '{query}'."

                notes_text = f"🔍 Search results (keyword: '{query}'):\n\n"
                for note in results:
                    tags_str = (
                        ", ".join(note.get("tags", [])) if note.get("tags") else ""
                    )
                    notes_text += f"**ID {note['id']}**: {note['title']}\n"
                    if tags_str:
                        notes_text += f"    Tags: {tags_str}\n"
                    notes_text += f"    Created at: {note['created_at']}\n\n"

                return notes_text

            else:
                return f"""Unsupported action: {action}. Supported actions: create, list, get, update, delete, search

                💡 Tip: To operate on specific notes, first use list or search to find the note ID, then reference it."""

        except Exception as e:
            logger.error(f"Note tool error: {str(e)}", exc_info=True)
            return f"Operation failed: {str(e)}"


# Create the tool instance
note_tool = NoteTool()

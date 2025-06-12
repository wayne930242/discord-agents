from google.genai import types
from google.adk.runners import Runner
from google.adk.events import Event
from typing import AsyncGenerator, Optional, Union, Any
from result import Result, Ok, Err
import tiktoken
import time
import json

from discord_agents.utils.logger import get_logger

logger = get_logger("call_agent")


# NOTE: From official docs, do not remove any part of this function (including comments) for reference
async def call_agent_async(
    query: str, runner: Runner, user_id: str, session_id: str
) -> str:
    """Sends a query to the agent and prints the final response."""
    logger.info(f"\n>>> User Query for user {user_id}, session {session_id}: {query}")

    # Prepare the user's message in ADK format
    content = types.Content(role="user", parts=[types.Part(text=query)])

    final_response_text = "Agent did not produce a final response."  # Default

    # Key Concept: run_async executes the agent logic and yields Events.
    # We iterate through events to find the final answer.
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content
    ):
        # You can uncomment the line below to see *all* events during execution
        # print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")

        # Key Concept: is_final_response() marks the concluding message for the turn.
        if event.is_final_response():
            if event.content and event.content.parts:
                for part in event.content.parts:
                    logger.debug(f"DEBUG part.text: {repr(part.text)}")
                # Assuming text response in the first part
                final_response_text = event.content.parts[0].text
            elif (
                event.actions and event.actions.escalate
            ):  # Handle potential errors/escalations
                final_response_text = (
                    f"Agent escalated: {event.error_message or 'No specific message.'}"
                )
            # Add more checks here if needed (e.g., specific error codes)
            break  # Stop processing events once the final response is found

    logger.info(f"<<< Agent Response: {final_response_text}")
    return final_response_text


def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken."""
    if not text:
        return 0
    try:
        enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
        return len(enc.encode(text))
    except Exception:
        return len(text)


def count_function_call_tokens(function_call: Any) -> int:
    """Count tokens in function call data."""
    if not function_call:
        return 0
    try:
        # Convert function call to JSON string for token counting
        function_call_str = json.dumps({
            "name": getattr(function_call, "name", ""),
            "args": getattr(function_call, "args", {})
        }, ensure_ascii=False)
        return count_tokens(function_call_str)
    except Exception as e:
        logger.debug(f"Error counting function call tokens: {e}")
        return 0


def count_function_response_tokens(function_response: Any) -> int:
    """Count tokens in function response data."""
    if not function_response:
        return 0
    try:
        # Convert function response to string for token counting
        if hasattr(function_response, "response"):
            response_str = str(function_response.response)
        else:
            response_str = str(function_response)
        return count_tokens(response_str)
    except Exception as e:
        logger.debug(f"Error counting function response tokens: {e}")
        return 0


class TokenTracker:
    """Track tokens for different types of content during agent execution."""

    def __init__(self) -> None:
        self.input_tokens = 0
        self.output_tokens = 0
        self.function_call_tokens = 0
        self.function_response_tokens = 0
        self.reasoning_tokens = 0

    def add_input_tokens(self, tokens: int) -> None:
        self.input_tokens += tokens

    def add_output_tokens(self, tokens: int) -> None:
        self.output_tokens += tokens

    def add_function_call_tokens(self, tokens: int) -> None:
        self.function_call_tokens += tokens

    def add_function_response_tokens(self, tokens: int) -> None:
        self.function_response_tokens += tokens

    def add_reasoning_tokens(self, tokens: int) -> None:
        self.reasoning_tokens += tokens

    def get_total_tokens(self) -> int:
        return (self.input_tokens + self.output_tokens +
                self.function_call_tokens + self.function_response_tokens +
                self.reasoning_tokens)

    def get_summary(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "function_call_tokens": self.function_call_tokens,
            "function_response_tokens": self.function_response_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "total_tokens": self.get_total_tokens()
        }


def trim_history(
    messages: list[str], max_tokens: int, model: Optional[str] = None
) -> tuple[list[str], bool]:
    RESERVED_TOKENS = 100  # Reserved tokens to avoid token limit issues
    if max_tokens == float("inf") or model is None:
        logger.info(f"Token count (no limit): {sum(count_tokens(m) for m in messages)}")
        logger.debug(f"Trimmed messages (no limit): {messages}")
        return messages, False  # New flag
    total_tokens = 0
    trimmed = []
    original_tokens = sum(count_tokens(m) for m in messages)
    logger.info(f"Token count (before trim): {original_tokens}")
    effective_max_tokens = max(0, max_tokens - RESERVED_TOKENS)
    for msg in reversed(messages):
        msg_tokens = count_tokens(msg)
        if total_tokens + msg_tokens > effective_max_tokens:
            break
        trimmed.append(msg)
        total_tokens += msg_tokens
    trimmed_msgs = list(reversed(trimmed))
    logger.debug(f"Trimmed messages: {trimmed_msgs}")
    trimmed_flag = len(trimmed_msgs) < len(messages)
    return trimmed_msgs, trimmed_flag


def _get_history_and_prompt(
    broker_client: Any, model: str, query: str, max_tokens: Union[int, float]
) -> Result[tuple[str, bool, int], str]:
    try:
        history_items = broker_client.get_message_history(model)
    except Exception as e:
        logger.warning(f"Failed to get broker history: {e}")
        history_items = []
    history = [item["text"] for item in history_items]
    total_tokens = sum(item.get("tokens", 0) for item in history_items)
    query_tokens = count_tokens(query)
    trimmed_flag = False
    if total_tokens + query_tokens > max_tokens:
        keep = []
        running_tokens = query_tokens
        for item in reversed(history_items):
            t = item.get("tokens", 0)
            if running_tokens + t > max_tokens:
                trimmed_flag = True
                break
            keep.append(item["text"])
            running_tokens += t
        history = list(reversed(keep))
    messages = history + [query]
    prompt = "\n".join(messages)
    return Ok((prompt, trimmed_flag, query_tokens))


def _handle_event(
    event: Event, only_final: bool, full_response_text: str, token_tracker: TokenTracker
) -> tuple[bool, Optional[str], str, bool]:
    try:
        logger.debug(f"Event details: {event}")
        logger.debug(f"Event type: {type(event).__name__}")

        if event.content and event.content.parts:
            for i, part in enumerate(event.content.parts):
                logger.debug(f"Part {i} details:")
                logger.debug(f"  Text: {part.text}")
                logger.debug(f"  Function call: {part.function_call}")
                logger.debug(f"  Function response: {part.function_response}")
                logger.debug(f"  Raw part: {part}")

                # Count function call tokens
                if part.function_call:
                    func_call_tokens = count_function_call_tokens(part.function_call)
                    token_tracker.add_function_call_tokens(func_call_tokens)
                    logger.debug(f"Function call tokens: {func_call_tokens}")

                # Count function response tokens
                if part.function_response:
                    func_response_tokens = count_function_response_tokens(part.function_response)
                    token_tracker.add_function_response_tokens(func_response_tokens)
                    logger.debug(f"Function response tokens: {func_response_tokens}")

        # Partial event
        if (
            getattr(event, "partial", False)
            and event.content
            and event.content.parts
            and event.content.parts[0].text
        ):
            text_content = event.content.parts[0].text
            full_response_text += text_content
            # Count partial response tokens as reasoning/output tokens
            partial_tokens = count_tokens(text_content)
            token_tracker.add_reasoning_tokens(partial_tokens)
            if not only_final:
                return True, text_content, full_response_text, False
            return True, None, full_response_text, False

        # Function call event
        if hasattr(event, "get_function_calls") and event.get_function_calls():
            function_calls = event.get_function_calls()
            for func_call in function_calls:
                func_call_tokens = count_function_call_tokens(func_call)
                token_tracker.add_function_call_tokens(func_call_tokens)
                logger.debug(f"Function call tokens: {func_call_tokens}")
            if not only_final:
                return True, "（......）", full_response_text, False

        # Final event
        if event.is_final_response():
            logger.info(f"<<< Final event received (ID: {getattr(event, 'id', 'N/A')})")
            if (
                hasattr(event, "actions")
                and event.actions
                and hasattr(event.actions, "escalate")
                and event.actions.escalate
            ):
                escalation_message = f"⚠️ Error: {getattr(event, 'error_message', None) or 'No specific message.'}"
                escalation_tokens = count_tokens(escalation_message)
                token_tracker.add_output_tokens(escalation_tokens)
                return False, escalation_message, "", True
            if event.content and event.content.parts:
                final_text = (full_response_text + event.content.parts[0].text).strip()
                final_tokens = count_tokens(event.content.parts[0].text)
                token_tracker.add_output_tokens(final_tokens)
                return False, final_text, "", True
            else:
                no_response_msg = "⚠️ No response content."
                token_tracker.add_output_tokens(count_tokens(no_response_msg))
                return False, no_response_msg, "", True

        # Non-final event full content
        if (
            event.content
            and event.content.parts
            and not getattr(event, "partial", False)
            and not event.is_final_response()
        ):
            for part in event.content.parts:
                if part.text:
                    text_tokens = count_tokens(part.text)
                    token_tracker.add_reasoning_tokens(text_tokens)
                    if not only_final:
                        return True, part.text, full_response_text, False
        return True, None, full_response_text, False

    except Exception as event_error:
        logger.error(f"Error processing event: {str(event_error)}", exc_info=True)
        return True, None, full_response_text, False


class MessageCenter:
    INVALID_INPUT = "❌ Invalid input parameters, please check and try again."
    HISTORY_ERROR = lambda err: f"❌ History message processing error: {err}"
    HISTORY_TRIMMED = "⚠️ Some history messages have been omitted due to token limit, the response may be incomplete."
    CONTENT_ERROR = "❌ Error creating message content, please try again later."
    EVENT_ERROR = lambda err: f"❌ Error processing response: {err}"


async def stream_agent_responses(
    query: str,
    runner: Runner,
    user_id: str,
    session_id: str,
    only_final: bool = True,
    model: Optional[str] = None,
    max_tokens: Union[int, float] = float("inf"),
    interval_seconds: float = 0.0,
) -> AsyncGenerator[Result[str, str], None]:
    logger.info(f"\n>>> User Query for user {user_id}, session {session_id}: {query}")
    if not query:
        return
    if not user_id or not session_id or not model:
        logger.error(
            f"Invalid input parameters: {query}, {user_id}, {session_id}, {model}"
        )
        yield Err(MessageCenter.INVALID_INPUT)
        return
    # Lazy import to avoid circular dependency
    from discord_agents.scheduler.broker import BotRedisClient

    broker_client = BotRedisClient()
    prompt_result = _get_history_and_prompt(broker_client, model, query, max_tokens)
    if prompt_result.is_err():
        yield Err(MessageCenter.HISTORY_ERROR(prompt_result.err()))
        return
    result_tuple = prompt_result.ok()
    if result_tuple is None:
        yield Err("Failed to get prompt result")
        return
    prompt, trimmed_flag, query_tokens = result_tuple
    if trimmed_flag:
        yield Ok(MessageCenter.HISTORY_TRIMMED)
    try_content = None
    try:
        try_content = types.Content(role="user", parts=[types.Part(text=prompt)])
    except Exception as content_error:
        logger.error(f"Error creating content: {str(content_error)}", exc_info=True)
        yield Err(MessageCenter.CONTENT_ERROR)
        return
    user_content = try_content
    full_response_text = ""
    final_response_yielded = False

    # Initialize token tracker
    token_tracker = TokenTracker()
    token_tracker.add_input_tokens(query_tokens)

    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=user_content
    ):
        try:
            should_continue, yield_value, full_response_text, is_final = _handle_event(
                event, only_final, full_response_text, token_tracker
            )

            if yield_value is not None:
                yield Ok(yield_value)

            if is_final and not final_response_yielded:
                try:
                    # Get comprehensive token summary
                    token_summary = token_tracker.get_summary()

                    # Store both input and total token usage in history
                    broker_client.add_message_history(
                        model=model,
                        text=query,
                        tokens=token_summary["total_tokens"],  # Store total tokens instead of just input
                        interval_seconds=interval_seconds,
                        timestamp=time.time(),
                    )

                    # Log comprehensive token usage
                    logger.info(f"Comprehensive token usage:")
                    logger.info(f"  Input tokens: {token_summary['input_tokens']}")
                    logger.info(f"  Output tokens: {token_summary['output_tokens']}")
                    logger.info(f"  Function call tokens: {token_summary['function_call_tokens']}")
                    logger.info(f"  Function response tokens: {token_summary['function_response_tokens']}")
                    logger.info(f"  Reasoning tokens: {token_summary['reasoning_tokens']}")
                    logger.info(f"  Total tokens: {token_summary['total_tokens']}")

                except Exception as e:
                    logger.warning(f"Failed to add broker history: {e}")
                final_response_yielded = True
                full_response_text = ""
                return
            if not should_continue:
                break
        except Exception as event_error:
            logger.error(f"Error processing event: {str(event_error)}", exc_info=True)
            yield Err(MessageCenter.EVENT_ERROR(str(event_error)))
            continue

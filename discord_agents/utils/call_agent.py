from google.genai import types
from google.adk.runners import Runner
from google.adk.events import Event
from typing import AsyncGenerator, Optional, Union
from result import Result, Ok, Err
import tiktoken
import time

from discord_agents.utils.logger import get_logger
from discord_agents.scheduler.broker import BotRedisClient

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
    try:
        enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
        return len(enc.encode(text))
    except Exception:
        return len(text)


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
    broker_client: BotRedisClient, model: str, query: str, max_tokens: Union[int, float]
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
    event: Event, only_final: bool, full_response_text: str
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

        # Partial event
        if (
            getattr(event, "partial", False)
            and event.content
            and event.content.parts
            and event.content.parts[0].text
        ):
            full_response_text += event.content.parts[0].text
            if not only_final:
                return True, event.content.parts[0].text, full_response_text, False
            return True, None, full_response_text, False

        # Function call
        if hasattr(event, "get_function_calls") and event.get_function_calls():
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
                escalation_message = f"⚠️ 發生錯誤: {getattr(event, 'error_message', None) or '沒有特定訊息。'}"
                return False, escalation_message, "", True
            if event.content and event.content.parts:
                final_text = (full_response_text + event.content.parts[0].text).strip()
                return False, final_text, "", True
            else:
                return False, "⚠️ 未收到有效回應內容。", "", True

        # Non-final event full content
        if (
            event.content
            and event.content.parts
            and not getattr(event, "partial", False)
            and not event.is_final_response()
        ):
            for part in event.content.parts:
                if part.text and not only_final:
                    return True, part.text, full_response_text, False
        return True, None, full_response_text, False

    except Exception as event_error:
        logger.error(f"Error processing event: {str(event_error)}", exc_info=True)
        return True, None, full_response_text, False


class MessageCenter:
    INVALID_INPUT = "❌ 輸入參數有誤，請確認後再試。"
    HISTORY_ERROR = lambda err: f"❌ 歷史訊息處理錯誤: {err}"
    HISTORY_TRIMMED = "⚠️ 部分歷史訊息因 token 限制已被省略，回應可能不完整。"
    CONTENT_ERROR = "❌ 建立訊息內容時發生錯誤，請稍後再試。"
    EVENT_ERROR = lambda err: f"❌ 回應處理時發生錯誤: {err}"


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
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=user_content
    ):
        try:
            should_continue, yield_value, full_response_text, is_final = _handle_event(
                event, only_final, full_response_text
            )
            if yield_value is not None:
                yield Ok(yield_value)
            if is_final and not final_response_yielded:
                try:
                    broker_client.add_message_history(
                        model=model,
                        text=query,
                        tokens=query_tokens,
                        interval_seconds=interval_seconds,
                        timestamp=time.time(),
                    )
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

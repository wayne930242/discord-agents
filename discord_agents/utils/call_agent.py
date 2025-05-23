from google.genai import types
from google.adk.runners import Runner
from typing import AsyncGenerator, Union, Optional
import tiktoken

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


def count_tokens(text, model: Optional[str] = None):
    if model is None:
        return len(text)
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))


def trim_history(messages, max_tokens: int, model: Optional[str] = None):
    RESERVED_TOKENS = 100  # Reserved tokens to avoid token limit issues
    if max_tokens == float("inf") or model is None:
        logger.info(
            f"Token count (no limit): {sum(count_tokens(m, model) for m in messages)}"
        )
        logger.debug(f"Trimmed messages (no limit): {messages}")
        return messages, False  # New flag
    total_tokens = 0
    trimmed = []
    original_tokens = sum(count_tokens(m, model) for m in messages)
    logger.info(f"Token count (before trim): {original_tokens}")
    effective_max_tokens = max(0, max_tokens - RESERVED_TOKENS)
    for msg in reversed(messages):
        msg_tokens = count_tokens(msg, model)
        if total_tokens + msg_tokens > effective_max_tokens:
            break
        trimmed.append(msg)
        total_tokens += msg_tokens
    trimmed_msgs = list(reversed(trimmed))
    logger.debug(f"Trimmed messages: {trimmed_msgs}")
    trimmed_flag = len(trimmed_msgs) < len(messages)
    return trimmed_msgs, trimmed_flag


async def stream_agent_responses(
    query: str,
    runner: Runner,
    user_id: str,
    session_id: str,
    use_function_map: Union[dict[str, str], None] = None,
    only_final: bool = True,
    model: Optional[str] = None,
    max_tokens: int = float("inf"),
) -> AsyncGenerator[str, None]:
    try:
        logger.info(
            f"\n>>> User Query for user {user_id}, session {session_id}: {query}"
        )

        if not query or not user_id or not session_id:
            logger.error("Invalid input parameters")
            yield "⚠️ 輸入參數有誤，請確認後再試。"
            return

        session_service = getattr(runner, "session_service", None)
        app_name = getattr(runner, "app_name", None)
        history = []
        if session_service and app_name:
            try:
                session = session_service.get_session(
                    app_name=app_name,
                    user_id=user_id,
                    session_id=session_id,
                )
                if session and hasattr(session, "events"):
                    history = [
                        e.content["text"]
                        for e in session.events
                        if e.content and "text" in e.content
                    ]
            except Exception as e:
                logger.warning(f"Failed to get session history: {e}")
                history = []
        messages = history + [query]
        messages, trimmed_flag = trim_history(messages, max_tokens, model)
        prompt = "\n".join(messages)

        if trimmed_flag:
            yield "⚠️ 部分歷史訊息因 token 限制已被省略，回應可能不完整。"

        try:
            user_content = types.Content(role="user", parts=[types.Part(text=prompt)])
        except Exception as content_error:
            logger.error(f"Error creating content: {str(content_error)}", exc_info=True)
            yield "⚠️ 建立訊息內容時發生錯誤，請稍後再試。"
            return

        full_response_text = ""
        final_response_yielded = False

        try:
            async for event in runner.run_async(
                user_id=user_id, session_id=session_id, new_message=user_content
            ):
                try:
                    logger.debug(f"Event details: {event}")
                    logger.debug(f"Event type: {type(event).__name__}")
                    if event.content and event.content.parts:
                        for i, part in enumerate(event.content.parts):
                            logger.debug(f"Part {i} details:")
                            logger.debug(f"  Text: {part.text}")
                            logger.debug(f"  Function call: {part.function_call}")
                            logger.debug(
                                f"  Function response: {part.function_response}"
                            )
                            logger.debug(f"  Raw part: {part}")
                    if not event:
                        logger.warning("Received null event")
                        continue
                    # Handle partial event
                    if (
                        event.partial
                        and event.content
                        and event.content.parts
                        and event.content.parts[0].text
                    ):
                        full_response_text += event.content.parts[0].text
                        if not only_final:
                            yield event.content.parts[0].text
                        continue
                    # Handle function call
                    if event.get_function_calls():
                        for call in event.get_function_calls():
                            func_name = call.name
                            if use_function_map and func_name in use_function_map:
                                message_to_yield = (
                                    "（" + use_function_map[func_name] + "）"
                                )
                                logger.info(
                                    f"<<< Agent function_call received: {func_name} — yielding mapped string only (no execution)."
                                )
                                if not only_final:
                                    yield message_to_yield
                            else:
                                if not only_final:
                                    yield "（......）"
                    # Handle final event
                    if event.is_final_response() and not final_response_yielded:
                        logger.info(
                            f"<<< Final event received (ID: {getattr(event, 'id', 'N/A')})"
                        )
                        if (
                            hasattr(event, "actions")
                            and event.actions
                            and hasattr(event.actions, "escalate")
                            and event.actions.escalate
                        ):
                            escalation_message = f"⚠️ *Agent escalated*: {event.error_message or 'No specific message.'}"
                            if only_final:
                                yield escalation_message
                            else:
                                yield escalation_message
                            final_response_yielded = True
                            full_response_text = ""
                            return
                        # Normal final response
                        if event.content and event.content.parts:
                            final_text = (
                                full_response_text + event.content.parts[0].text
                            ).strip()
                            yield final_text
                            final_response_yielded = True
                            full_response_text = ""
                            return
                        else:
                            if only_final:
                                yield "⚠️ 未收到有效回應內容。"
                            else:
                                yield "⚠️ 未收到有效回應內容。"
                            final_response_yielded = True
                            full_response_text = ""
                            return
                    # Non-final event full content
                    if (
                        event.content
                        and event.content.parts
                        and not event.partial
                        and not event.is_final_response()
                    ):
                        for part in event.content.parts:
                            if part.text and not only_final:
                                yield part.text
                except Exception as event_error:
                    logger.error(
                        f"Error processing event: {str(event_error)}", exc_info=True
                    )
                    continue
        except Exception as stream_error:
            logger.error(
                f"Error in stream processing: {str(stream_error)}", exc_info=True
            )
            yield "⚠️ 回應處理時發生錯誤，請稍後再試。"
    except Exception as e:
        logger.error(
            f"Unexpected error in stream_agent_responses: {str(e)}", exc_info=True
        )
        yield "⚠️ 發生未知錯誤，請稍後再試。"

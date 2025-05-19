from google.genai import types
from google.adk.runners import Runner
from typing import AsyncGenerator, Union

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


async def stream_agent_responses(
    query: str,
    runner: Runner,
    user_id: str,
    session_id: str,
    use_function_map: Union[dict[str, str], None] = None,
    only_final: bool = True,
) -> AsyncGenerator[str, None]:
    try:
        logger.info(
            f"\n>>> User Query for user {user_id}, session {session_id}: {query}"
        )

        if not query or not user_id or not session_id:
            logger.error("Invalid input parameters")
            yield "⚠️ Invalid input parameters"
            return

        try:
            user_content = types.Content(role="user", parts=[types.Part(text=query)])
        except Exception as content_error:
            logger.error(f"Error creating content: {str(content_error)}", exc_info=True)
            yield "⚠️ Error creating content"
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
                            logger.debug(f"  Function response: {part.function_response}")
                            logger.debug(f"  Raw part: {part}")
                    if not event:
                        logger.warning("Received null event")
                        continue
                    # Handle partial event
                    if event.partial and event.content and event.content.parts and event.content.parts[0].text:
                        full_response_text += event.content.parts[0].text
                        if not only_final:
                            yield event.content.parts[0].text
                        continue
                    # Handle function call
                    if event.get_function_calls():
                        for call in event.get_function_calls():
                            func_name = call.name
                            if use_function_map and func_name in use_function_map:
                                message_to_yield = "（" + use_function_map[func_name] + "）"
                                logger.info(
                                    f"<<< Agent function_call received: {func_name} — yielding mapped string only (no execution)."
                                )
                                if not only_final:
                                    yield message_to_yield
                            else:
                                logger.warning(
                                    f"⚠️ [Unhandled FunctionCall] {func_name} not in use_function_map"
                                )
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
                            final_text = (full_response_text + event.content.parts[0].text).strip()
                            yield final_text
                            final_response_yielded = True
                            full_response_text = ""
                            return
                        else:
                            if only_final:
                                yield "⚠️ No valid response received"
                            else:
                                yield "⚠️ No valid response received"
                            final_response_yielded = True
                            full_response_text = ""
                            return
                    # Non-final event full content
                    if event.content and event.content.parts and not event.partial and not event.is_final_response():
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
            yield "⚠️ Error processing response, please try again later."
    except Exception as e:
        logger.error(
            f"Unexpected error in stream_agent_responses: {str(e)}", exc_info=True
        )
        yield "⚠️ Unexpected error, please try again later."

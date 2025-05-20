from typing import TypedDict, Optional


class MyBotInitConfig(TypedDict, total=False):
    bot_id: str
    token: str
    command_prefix_param: Optional[str]
    dm_whitelist: Optional[list[str]]
    srv_whitelist: Optional[list[str]]


class MyAgentSetupConfig(TypedDict):
    description: str
    role_instructions: str
    tool_instructions: str
    agent_model: str
    app_name: str
    use_function_map: dict[str, str]
    error_message: str
    tools: list[str]

from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime


class AgentBase(BaseModel):
    name: str
    description: str
    role_instructions: str
    tool_instructions: str
    agent_model: str
    tools: List[str] = []


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    role_instructions: Optional[str] = None
    tool_instructions: Optional[str] = None
    agent_model: Optional[str] = None
    tools: Optional[List[str]] = None


class Agent(AgentBase):
    id: int

    class Config:
        from_attributes = True


class BotBase(BaseModel):
    token: str
    error_message: str = ""
    command_prefix: str = "!"
    dm_whitelist: List[str] = []
    srv_whitelist: List[str] = []
    use_function_map: Dict[str, Any] = {}

    @field_validator('dm_whitelist', 'srv_whitelist', mode='before')
    @classmethod
    def convert_ids_to_strings(cls, v):
        """Convert integer IDs to strings for Discord IDs"""
        if isinstance(v, list):
            return [str(item) for item in v]
        return v


class BotCreate(BotBase):
    agent_id: Optional[int] = None


class BotUpdate(BaseModel):
    token: Optional[str] = None
    error_message: Optional[str] = None
    command_prefix: Optional[str] = None
    dm_whitelist: Optional[List[str]] = None
    srv_whitelist: Optional[List[str]] = None
    use_function_map: Optional[Dict[str, Any]] = None
    agent_id: Optional[int] = None

    @field_validator('dm_whitelist', 'srv_whitelist', mode='before')
    @classmethod
    def convert_ids_to_strings(cls, v):
        """Convert integer IDs to strings for Discord IDs"""
        if isinstance(v, list):
            return [str(item) for item in v]
        return v


class Bot(BotBase):
    id: int
    agent_id: Optional[int] = None
    agent: Optional[Agent] = None

    class Config:
        from_attributes = True


class NoteBase(BaseModel):
    session_id: str
    title: str
    content: str
    tags: List[str] = []


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None


class Note(NoteBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TokenUsageBase(BaseModel):
    agent_id: int
    agent_name: str
    model_name: str
    year: int
    month: int = Field(..., ge=1, le=12, description="Month (1-12)")
    input_tokens: int = Field(..., ge=0)
    output_tokens: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)
    input_cost: float = Field(..., ge=0.0)
    output_cost: float = Field(..., ge=0.0)
    total_cost: float = Field(..., ge=0.0)


class TokenUsageCreate(BaseModel):
    """Schema for creating token usage records"""

    agent_id: int
    agent_name: str
    model_name: str
    input_tokens: int = Field(..., ge=0)
    output_tokens: int = Field(..., ge=0)
    year: Optional[int] = None
    month: Optional[int] = Field(None, ge=1, le=12)


class TokenUsageUpdate(BaseModel):
    """Schema for updating token usage records"""

    input_tokens: Optional[int] = Field(None, ge=0)
    output_tokens: Optional[int] = Field(None, ge=0)


class TokenUsage(TokenUsageBase):
    """Schema for token usage response"""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenUsageSummaryByAgent(BaseModel):
    """Summary of token usage grouped by agent"""

    agent_id: int
    agent_name: str
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_input_cost: float
    total_output_cost: float
    total_cost: float


class TokenUsageSummaryByModel(BaseModel):
    """Summary of token usage grouped by model"""

    model_name: str
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_input_cost: float
    total_output_cost: float
    total_cost: float


class MonthlyUsageTrend(BaseModel):
    """Monthly usage trend data"""

    year: int
    month: int
    month_year: str
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_input_cost: float
    total_output_cost: float
    total_cost: float


class TotalCostSummary(BaseModel):
    """Total cost summary"""

    total_input_cost: float
    total_output_cost: float
    total_cost: float


class TokenUsageQuery(BaseModel):
    """Query parameters for token usage endpoints"""

    agent_id: Optional[int] = None
    model_name: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = Field(None, ge=1, le=12)
    limit: Optional[int] = Field(12, ge=1, le=100)


class ModelPricing(BaseModel):
    """Model pricing information"""

    model_name: str
    input_price_per_1M: float
    output_price_per_1M: float


class ModelPricingList(BaseModel):
    """List of all model pricing"""

    models: List[ModelPricing]

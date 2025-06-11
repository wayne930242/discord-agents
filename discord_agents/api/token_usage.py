from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from discord_agents.core.database import get_db
from discord_agents.core.security import get_current_user
from discord_agents.services.token_usage_service import TokenUsageService
from discord_agents.schemas.token_usage import (
    TokenUsage,
    TokenUsageCreate,
    TokenUsageSummaryByAgent,
    TokenUsageSummaryByModel,
    MonthlyUsageTrend,
    TotalCostSummary,
    ModelPricing,
    ModelPricingList,
)
from discord_agents.domain.agent import LLMs

router = APIRouter()


@router.post("/record", response_model=TokenUsage)
async def record_token_usage(
    usage: TokenUsageCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> TokenUsage:
    """Record token usage for an agent"""
    try:
        record = TokenUsageService.record_token_usage(
            db=db,
            agent_id=usage.agent_id,
            agent_name=usage.agent_name,
            model_name=usage.model_name,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            year=usage.year,
            month=usage.month,
        )
        return TokenUsage.model_validate(record)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record token usage: {str(e)}",
        )


@router.get("/agent/{agent_id}", response_model=List[TokenUsage])
async def get_agent_usage(
    agent_id: int,
    year: Optional[int] = Query(None, description="Filter by year"),
    month: Optional[int] = Query(
        None, ge=1, le=12, description="Filter by month (1-12)"
    ),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> List[TokenUsage]:
    """Get token usage records for a specific agent"""
    records = TokenUsageService.get_agent_usage(
        db=db, agent_id=agent_id, year=year, month=month
    )
    return [TokenUsage.model_validate(record) for record in records]


@router.get("/all", response_model=List[TokenUsage])
async def get_all_usage(
    year: Optional[int] = Query(None, description="Filter by year"),
    month: Optional[int] = Query(
        None, ge=1, le=12, description="Filter by month (1-12)"
    ),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> List[TokenUsage]:
    """Get all token usage records"""
    records = TokenUsageService.get_all_usage(db=db, year=year, month=month)
    return [TokenUsage.model_validate(record) for record in records]


@router.get("/summary/by-agent", response_model=List[TokenUsageSummaryByAgent])
async def get_usage_summary_by_agent(
    year: Optional[int] = Query(None, description="Filter by year"),
    month: Optional[int] = Query(
        None, ge=1, le=12, description="Filter by month (1-12)"
    ),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> List[TokenUsageSummaryByAgent]:
    """Get token usage summary grouped by agent"""
    summary = TokenUsageService.get_usage_summary_by_agent(
        db=db, year=year, month=month
    )
    return [TokenUsageSummaryByAgent.model_validate(item) for item in summary]


@router.get("/summary/by-model", response_model=List[TokenUsageSummaryByModel])
async def get_usage_summary_by_model(
    year: Optional[int] = Query(None, description="Filter by year"),
    month: Optional[int] = Query(
        None, ge=1, le=12, description="Filter by month (1-12)"
    ),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> List[TokenUsageSummaryByModel]:
    """Get token usage summary grouped by model"""
    summary = TokenUsageService.get_usage_summary_by_model(
        db=db, year=year, month=month
    )
    return [TokenUsageSummaryByModel.model_validate(item) for item in summary]


@router.get("/trend/monthly", response_model=List[MonthlyUsageTrend])
async def get_monthly_usage_trend(
    agent_id: Optional[int] = Query(None, description="Filter by agent ID"),
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    limit: int = Query(12, ge=1, le=100, description="Number of months to return"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> List[MonthlyUsageTrend]:
    """Get monthly usage trend data"""
    trend = TokenUsageService.get_monthly_usage_trend(
        db=db, agent_id=agent_id, model_name=model_name, limit=limit
    )
    return [MonthlyUsageTrend.model_validate(item) for item in trend]


@router.get("/cost/total", response_model=TotalCostSummary)
async def get_total_cost(
    agent_id: Optional[int] = Query(None, description="Filter by agent ID"),
    year: Optional[int] = Query(None, description="Filter by year"),
    month: Optional[int] = Query(
        None, ge=1, le=12, description="Filter by month (1-12)"
    ),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> TotalCostSummary:
    """Get total cost summary"""
    cost = TokenUsageService.get_total_cost(
        db=db, agent_id=agent_id, year=year, month=month
    )
    return TotalCostSummary.model_validate(cost)


@router.get("/models/pricing", response_model=ModelPricingList)
async def get_model_pricing(
    current_user: str = Depends(get_current_user),
) -> ModelPricingList:
    """Get pricing information for all available models"""
    models = []
    for llm in LLMs.llm_list:
        models.append(
            ModelPricing(
                model_name=llm["model"],
                input_price_per_1M=llm["input_price_per_1M"],
                output_price_per_1M=llm["output_price_per_1M"],
            )
        )
    return ModelPricingList(models=models)


@router.get("/models/{model_name}/pricing", response_model=ModelPricing)
async def get_model_pricing_detail(
    model_name: str,
    current_user: str = Depends(get_current_user),
) -> ModelPricing:
    """Get pricing information for a specific model"""
    input_price, output_price = LLMs.get_pricing(model_name)
    if input_price == 0.0 and output_price == 0.0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_name}' not found",
        )

    return ModelPricing(
        model_name=model_name,
        input_price_per_1M=input_price,
        output_price_per_1M=output_price,
    )

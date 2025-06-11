from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, date
from decimal import Decimal

from discord_agents.models.bot import TokenUsageModel
from discord_agents.domain.agent import LLMs


class TokenUsageService:
    """Token usage tracking and cost calculation service"""

    @staticmethod
    def record_token_usage(
        db: Session,
        agent_id: int,
        agent_name: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> TokenUsageModel:
        """Record or update token usage for an agent in a specific month.

        Args:
            db: Database session
            agent_id: Agent ID
            agent_name: Agent name
            model_name: Model name used
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            year: Year (defaults to current year)
            month: Month (defaults to current month)

        Returns:
            TokenUsageModel: The created or updated record
        """
        if year is None or month is None:
            now = datetime.now()
            year = year or now.year
            month = month or now.month

        # Get pricing for the model
        input_price_per_1M, output_price_per_1M = LLMs.get_pricing(model_name)

        # Calculate costs
        input_cost = Decimal(str(input_tokens * input_price_per_1M / 1_000_000))
        output_cost = Decimal(str(output_tokens * output_price_per_1M / 1_000_000))
        total_cost = input_cost + output_cost
        total_tokens = input_tokens + output_tokens

        # Try to find existing record for this agent/model/month
        existing_record = (
            db.query(TokenUsageModel)
            .filter(
                and_(
                    TokenUsageModel.agent_id == agent_id,
                    TokenUsageModel.model_name == model_name,
                    TokenUsageModel.year == year,
                    TokenUsageModel.month == month,
                )
            )
            .first()
        )

        if existing_record:
            # Update existing record
            existing_record.input_tokens += input_tokens
            existing_record.output_tokens += output_tokens
            existing_record.total_tokens += total_tokens
            existing_record.input_cost += input_cost
            existing_record.output_cost += output_cost
            existing_record.total_cost += total_cost
            existing_record.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(existing_record)
            return existing_record
        else:
            # Create new record
            new_record = TokenUsageModel(
                agent_id=agent_id,
                agent_name=agent_name,
                model_name=model_name,
                year=year,
                month=month,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                input_cost=input_cost,
                output_cost=output_cost,
                total_cost=total_cost,
            )
            db.add(new_record)
            db.commit()
            db.refresh(new_record)
            return new_record

    @staticmethod
    def get_agent_usage(
        db: Session,
        agent_id: int,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> List[TokenUsageModel]:
        """Get token usage records for a specific agent.

        Args:
            db: Database session
            agent_id: Agent ID
            year: Filter by year (optional)
            month: Filter by month (optional, requires year)

        Returns:
            List[TokenUsageModel]: List of usage records
        """
        query = db.query(TokenUsageModel).filter(TokenUsageModel.agent_id == agent_id)

        if year is not None:
            query = query.filter(TokenUsageModel.year == year)
            if month is not None:
                query = query.filter(TokenUsageModel.month == month)

        return query.order_by(
            TokenUsageModel.year.desc(), TokenUsageModel.month.desc()
        ).all()

    @staticmethod
    def get_all_usage(
        db: Session,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> List[TokenUsageModel]:
        """Get all token usage records.

        Args:
            db: Database session
            year: Filter by year (optional)
            month: Filter by month (optional, requires year)

        Returns:
            List[TokenUsageModel]: List of usage records
        """
        query = db.query(TokenUsageModel)

        if year is not None:
            query = query.filter(TokenUsageModel.year == year)
            if month is not None:
                query = query.filter(TokenUsageModel.month == month)

        return query.order_by(
            TokenUsageModel.year.desc(),
            TokenUsageModel.month.desc(),
            TokenUsageModel.agent_name,
        ).all()

    @staticmethod
    def get_usage_summary_by_agent(
        db: Session,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get token usage summary grouped by agent.

        Args:
            db: Database session
            year: Filter by year (optional)
            month: Filter by month (optional, requires year)

        Returns:
            List[Dict]: Summary data grouped by agent
        """
        query = db.query(
            TokenUsageModel.agent_id,
            TokenUsageModel.agent_name,
            func.sum(TokenUsageModel.input_tokens).label("total_input_tokens"),
            func.sum(TokenUsageModel.output_tokens).label("total_output_tokens"),
            func.sum(TokenUsageModel.total_tokens).label("total_tokens"),
            func.sum(TokenUsageModel.input_cost).label("total_input_cost"),
            func.sum(TokenUsageModel.output_cost).label("total_output_cost"),
            func.sum(TokenUsageModel.total_cost).label("total_cost"),
        ).group_by(TokenUsageModel.agent_id, TokenUsageModel.agent_name)

        if year is not None:
            query = query.filter(TokenUsageModel.year == year)
            if month is not None:
                query = query.filter(TokenUsageModel.month == month)

        results = query.all()

        return [
            {
                "agent_id": result.agent_id,
                "agent_name": result.agent_name,
                "total_input_tokens": int(result.total_input_tokens or 0),
                "total_output_tokens": int(result.total_output_tokens or 0),
                "total_tokens": int(result.total_tokens or 0),
                "total_input_cost": float(result.total_input_cost or 0),
                "total_output_cost": float(result.total_output_cost or 0),
                "total_cost": float(result.total_cost or 0),
            }
            for result in results
        ]

    @staticmethod
    def get_usage_summary_by_model(
        db: Session,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get token usage summary grouped by model.

        Args:
            db: Database session
            year: Filter by year (optional)
            month: Filter by month (optional, requires year)

        Returns:
            List[Dict]: Summary data grouped by model
        """
        query = db.query(
            TokenUsageModel.model_name,
            func.sum(TokenUsageModel.input_tokens).label("total_input_tokens"),
            func.sum(TokenUsageModel.output_tokens).label("total_output_tokens"),
            func.sum(TokenUsageModel.total_tokens).label("total_tokens"),
            func.sum(TokenUsageModel.input_cost).label("total_input_cost"),
            func.sum(TokenUsageModel.output_cost).label("total_output_cost"),
            func.sum(TokenUsageModel.total_cost).label("total_cost"),
        ).group_by(TokenUsageModel.model_name)

        if year is not None:
            query = query.filter(TokenUsageModel.year == year)
            if month is not None:
                query = query.filter(TokenUsageModel.month == month)

        results = query.all()

        return [
            {
                "model_name": result.model_name,
                "total_input_tokens": int(result.total_input_tokens or 0),
                "total_output_tokens": int(result.total_output_tokens or 0),
                "total_tokens": int(result.total_tokens or 0),
                "total_input_cost": float(result.total_input_cost or 0),
                "total_output_cost": float(result.total_output_cost or 0),
                "total_cost": float(result.total_cost or 0),
            }
            for result in results
        ]

    @staticmethod
    def get_monthly_usage_trend(
        db: Session,
        agent_id: Optional[int] = None,
        model_name: Optional[str] = None,
        limit: int = 12,
    ) -> List[Dict[str, Any]]:
        """Get monthly usage trend data.

        Args:
            db: Database session
            agent_id: Filter by agent ID (optional)
            model_name: Filter by model name (optional)
            limit: Number of months to return (default: 12)

        Returns:
            List[Dict]: Monthly trend data
        """
        query = db.query(
            TokenUsageModel.year,
            TokenUsageModel.month,
            func.sum(TokenUsageModel.input_tokens).label("total_input_tokens"),
            func.sum(TokenUsageModel.output_tokens).label("total_output_tokens"),
            func.sum(TokenUsageModel.total_tokens).label("total_tokens"),
            func.sum(TokenUsageModel.input_cost).label("total_input_cost"),
            func.sum(TokenUsageModel.output_cost).label("total_output_cost"),
            func.sum(TokenUsageModel.total_cost).label("total_cost"),
        ).group_by(TokenUsageModel.year, TokenUsageModel.month)

        if agent_id is not None:
            query = query.filter(TokenUsageModel.agent_id == agent_id)

        if model_name is not None:
            query = query.filter(TokenUsageModel.model_name == model_name)

        results = (
            query.order_by(TokenUsageModel.year.desc(), TokenUsageModel.month.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "year": result.year,
                "month": result.month,
                "month_year": f"{result.year}-{result.month:02d}",
                "total_input_tokens": int(result.total_input_tokens or 0),
                "total_output_tokens": int(result.total_output_tokens or 0),
                "total_tokens": int(result.total_tokens or 0),
                "total_input_cost": float(result.total_input_cost or 0),
                "total_output_cost": float(result.total_output_cost or 0),
                "total_cost": float(result.total_cost or 0),
            }
            for result in results
        ]

    @staticmethod
    def get_total_cost(
        db: Session,
        agent_id: Optional[int] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> Dict[str, float]:
        """Get total cost summary.

        Args:
            db: Database session
            agent_id: Filter by agent ID (optional)
            year: Filter by year (optional)
            month: Filter by month (optional, requires year)

        Returns:
            Dict: Total cost breakdown
        """
        query = db.query(
            func.sum(TokenUsageModel.input_cost).label("total_input_cost"),
            func.sum(TokenUsageModel.output_cost).label("total_output_cost"),
            func.sum(TokenUsageModel.total_cost).label("total_cost"),
        )

        if agent_id is not None:
            query = query.filter(TokenUsageModel.agent_id == agent_id)

        if year is not None:
            query = query.filter(TokenUsageModel.year == year)
            if month is not None:
                query = query.filter(TokenUsageModel.month == month)

        result = query.first()

        if result is None:
            return {
                "total_input_cost": 0.0,
                "total_output_cost": 0.0,
                "total_cost": 0.0,
            }

        return {
            "total_input_cost": float(result.total_input_cost or 0),
            "total_output_cost": float(result.total_output_cost or 0),
            "total_cost": float(result.total_cost or 0),
        }

"""
Admin Analytics Routes

Contains routes for statistical analysis and reporting.
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from sqlmodel import Session
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional

# Import models
from models import engine

# Import helper functions
from app_helpers.services.auth_helpers import current_user, is_admin
from app_helpers.services.statistics_service import StatisticsService

# Create router for this module
router = APIRouter()


def require_admin(user_session: tuple = Depends(current_user)):
    """Require admin access for statistics endpoints"""
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/api/statistics/prayers")
async def get_prayer_statistics(
    period: str = Query(..., regex="^(daily|weekly|monthly|yearly)$"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user=Depends(require_admin)
) -> Dict[str, Any]:
    """Get prayer statistics by time period"""
    
    # Set default date range if not provided
    if not start_date or not end_date:
        end_date_obj = date.today()
        if period == "daily":
            start_date_obj = end_date_obj - timedelta(days=30)
        elif period == "weekly":
            start_date_obj = end_date_obj - timedelta(weeks=12)
        elif period == "monthly":
            start_date_obj = end_date_obj - timedelta(days=365)
        else:  # yearly
            start_date_obj = end_date_obj - timedelta(days=365*3)
    else:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Validate date range
    if start_date_obj > end_date_obj:
        raise HTTPException(status_code=400, detail="Start date must be before end date")
    
    # Get statistics
    try:
        with Session(engine) as session:
            stats_service = StatisticsService(session)
            
            prayer_counts = stats_service.get_prayer_counts_by_period(
                period, start_date_obj, end_date_obj
            )
            
            user_counts = stats_service.get_user_registration_counts_by_period(
                period, start_date_obj, end_date_obj
            )
            
            summary = stats_service.get_summary_statistics()
            
            return {
                "period": period,
                "start_date": start_date_obj.isoformat(),
                "end_date": end_date_obj.isoformat(),
                "prayer_counts": prayer_counts,
                "user_counts": user_counts,
                "summary": summary
            }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/statistics/summary")
async def get_summary_statistics(
    current_user=Depends(require_admin)
) -> Dict[str, int]:
    """Get summary statistics for dashboard overview"""
    
    try:
        with Session(engine) as session:
            stats_service = StatisticsService(session)
            return stats_service.get_summary_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
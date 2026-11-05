from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query

from database.historical_store import historical_store
from telemetry.telemetry import telemetry_collector
from receipt.receipt_generator import generate_eco_receipt
from receipt.schemas import EcoReceipt
from api.schemas_dashboard import (
    DashboardSummaryResponse,
    DashboardEnvironmentResponse,
    DashboardRoutesResponse,
    TimeseriesPoint,
    PaginatedReceiptsResponse
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analytics"])

@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    start_date: Optional[str] = Query(None, description="Start date ISO-8601 filter"),
    end_date: Optional[str] = Query(None, description="End date ISO-8601 filter")
):
    """
    Retrieve aggregated operational and performance overview metrics from historical requests.
    Calculates execution counts, success rate, latency averages, authentic token totals,
    itemized external API charges, and counterfactual avoidance facts.
    """
    return historical_store.get_summary(start_date=start_date, end_date=end_date)

@router.get("/environment", response_model=DashboardEnvironmentResponse)
def get_dashboard_environment(
    start_date: Optional[str] = Query(None, description="Start date ISO-8601 filter"),
    end_date: Optional[str] = Query(None, description="End date ISO-8601 filter")
):
    """
    Retrieve aggregated environmental footprint metrics.
    Strictly segregates hardware-measured energy from model-based estimations,
    computes operational carbon only where valid grid intensity exists,
    preserves measurement boundaries, and provides clear water disclosures.
    """
    return historical_store.get_environmental_summary(start_date=start_date, end_date=end_date)

@router.get("/routes", response_model=DashboardRoutesResponse)
def get_dashboard_routes(
    start_date: Optional[str] = Query(None, description="Start date ISO-8601 filter"),
    end_date: Optional[str] = Query(None, description="End date ISO-8601 filter")
):
    """
    Retrieve multi-objective routing optimizer evaluation metrics.
    Analyzes candidate path distribution, Pareto frontier compliance rates,
    average route latency, quality compliance, and fallback justification audit.
    """
    return historical_store.get_routes_analytics(start_date=start_date, end_date=end_date)

@router.get("/timeseries", response_model=List[TimeseriesPoint])
def get_dashboard_timeseries(
    interval: str = Query("hour", pattern="^(hour|day)$", description="Bucket granularity: 'hour' or 'day'"),
    start_date: Optional[str] = Query(None, description="Start date ISO-8601 filter"),
    end_date: Optional[str] = Query(None, description="End date ISO-8601 filter")
):
    """
    Retrieve chronological timeseries data points bucketed by hour or day.
    Tracks query volume, mean latency, token volume, measured/estimated energy, and avoided calls.
    """
    return historical_store.get_timeseries(interval=interval, start_date=start_date, end_date=end_date)

@router.get("/receipts", response_model=PaginatedReceiptsResponse)
def list_dashboard_receipts(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(25, ge=1, le=100, description="Records per page"),
    start_date: Optional[str] = Query(None, description="Start date ISO-8601 filter"),
    end_date: Optional[str] = Query(None, description="End date ISO-8601 filter"),
    execution_path: Optional[str] = Query(None, description="Filter by path: deterministic_tool, semantic_cache, model_inference"),
    status: Optional[str] = Query(None, description="Filter by status: SUCCESS, FAILED, PARTIAL"),
    route: Optional[str] = Query(None, description="Filter by route name")
):
    """
    Retrieve a paginated, filterable table of Eco Receipt summaries from persistent SQLite storage.
    Enables deep inspection of historical requests with zero data fabrication.
    """
    return historical_store.list_receipts(
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
        execution_path=execution_path,
        status=status,
        route=route
    )

@router.get("/receipts/{request_id}", response_model=EcoReceipt)
def get_dashboard_receipt_by_id(request_id: str):
    """
    Retrieve full, machine-readable Eco Receipt for a specific request ID or receipt ID.
    Queries the persistent historical SQLite store first; falls back to in-memory telemetry if pending.
    """
    # 1. Check persistent SQLite store
    rcpt = historical_store.get_receipt(request_id)
    if rcpt:
        return rcpt

    # 2. Fallback to in-memory buffer
    rec = telemetry_collector.get_record(request_id)
    if rec:
        return generate_eco_receipt(rec)

    raise HTTPException(
        status_code=404,
        detail=f"Eco Receipt with request ID or receipt ID '{request_id}' not found in historical storage or memory buffer."
    )


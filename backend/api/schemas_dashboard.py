from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class DashboardSummaryResponse(BaseModel):
    """Aggregated operational and performance overview metrics."""
    total_requests: int = Field(..., description="Total requests recorded")
    successful_requests: int = Field(..., description="Successful request count")
    failed_requests: int = Field(..., description="Failed execution count")
    partial_requests: int = Field(..., description="Partial execution count")
    success_rate_percent: float = Field(..., description="Percentage of requests executed successfully")
    total_execution_time_ms: float = Field(..., description="Cumulative execution time in ms")
    avg_latency_ms: float = Field(..., description="Mean execution latency in ms")
    total_prompt_tokens: int = Field(..., description="Total input/prompt tokens")
    total_completion_tokens: int = Field(..., description="Total output/completion tokens")
    total_tokens: int = Field(..., description="Grand total tokens recorded")
    total_external_api_cost_usd: float = Field(..., description="Total external provider API charges incurred in USD")
    zero_external_api_cost_count: int = Field(..., description="Count of requests with $0 external provider charges (cache/tools/local)")
    billed_external_api_cost_count: int = Field(..., description="Count of requests with external provider charges")
    total_model_calls_avoided: int = Field(..., description="Model calls avoided via cache or deterministic tools")
    total_tokens_avoided: int = Field(..., description="Estimated tokens avoided")
    routes_breakdown: Dict[str, int] = Field(default_factory=dict, description="Request count per route")
    providers_breakdown: Dict[str, int] = Field(default_factory=dict, description="Request count per provider")
    execution_paths_breakdown: Dict[str, int] = Field(default_factory=dict, description="Request count per execution path")
    filter_start_date: Optional[str] = Field(default=None, description="Start date filter applied")
    filter_end_date: Optional[str] = Field(default=None, description="End date filter applied")

class DashboardEnvironmentResponse(BaseModel):
    """Aggregated environmental metrics strictly distinguishing measured from estimated."""
    total_requests: int = Field(..., description="Total requests in scope")
    records_with_measured_energy: int = Field(..., description="Count of requests with direct hardware-measured energy")
    records_with_estimated_energy: int = Field(..., description="Count of requests with validated model-estimated energy")
    records_with_unavailable_energy: int = Field(..., description="Count of requests where physical energy was unavailable")
    measured_energy_joules: float = Field(..., description="Total measured energy consumed in Joules")
    measured_energy_kwh: float = Field(..., description="Total measured energy consumed in kWh")
    estimated_energy_joules: float = Field(..., description="Total estimated energy consumed in Joules")
    estimated_energy_kwh: float = Field(..., description="Total estimated energy consumed in kWh")
    records_with_carbon: int = Field(..., description="Count of requests with operational carbon emissions calculated")
    records_with_unavailable_carbon: int = Field(..., description="Count of requests where carbon was unavailable")
    carbon_from_measured_energy_gco2e: float = Field(..., description="Carbon calculated from hardware-measured energy (gCO2e)")
    carbon_from_estimated_energy_gco2e: float = Field(..., description="Carbon calculated from estimated energy (gCO2e)")
    total_carbon_gco2e: float = Field(..., description="Total operational carbon emissions in gCO2e")
    records_with_water: int = Field(..., description="Count of requests with reported water")
    total_water_liters: Optional[float] = Field(default=None, description="Total reported water in liters (or null)")
    water_disclosure: str = Field(..., description="Statement explaining why water is unavailable in commercial environments")
    measurement_scopes_breakdown: Dict[str, int] = Field(default_factory=dict, description="Counts per measurement scope")
    grid_sources_breakdown: Dict[str, int] = Field(default_factory=dict, description="Counts per grid emissions data source")
    environmental_sources_breakdown: Dict[str, int] = Field(default_factory=dict, description="Counts per registered environmental source ID")
    scope_boundary_notice: str = Field(..., description="Explicit disclosure of active measurement boundaries")
    filter_start_date: Optional[str] = Field(default=None)
    filter_end_date: Optional[str] = Field(default=None)

class RouteStatItem(BaseModel):
    route: str
    request_count: int
    avg_latency_ms: float
    avg_inference_latency_ms: Optional[float] = None
    pareto_count: int
    fallback_count: int
    avoided_calls: int
    total_cost_usd: float
    total_energy_joules: Optional[float] = None

class DashboardRoutesResponse(BaseModel):
    """Multi-objective optimizer metrics and route efficiency."""
    total_evaluated_requests: int
    pareto_optimal_selection_rate_percent: float
    quality_threshold_compliance_percent: float
    fallback_engagement_rate_percent: float
    route_statistics: List[RouteStatItem]
    fallback_reasons_breakdown: Dict[str, int]
    filter_start_date: Optional[str] = None
    filter_end_date: Optional[str] = None

class TimeseriesPoint(BaseModel):
    time_bucket: str
    request_count: int
    avg_latency_ms: float
    total_tokens: int
    measured_energy_joules: float
    estimated_energy_joules: float
    total_carbon_gco2e: float
    total_cost_usd: float
    model_calls_avoided: int

class ReceiptSummaryItem(BaseModel):
    request_id: str
    receipt_id: str
    timestamp: str
    status: str
    execution_path: str
    route: str
    provider: str
    model: Optional[str] = None
    query_preview: Optional[str] = None
    execution_time_ms: float
    inference_latency_ms: Optional[float] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    is_zero_external_api_charge: bool
    energy_joules: Optional[float] = None
    is_energy_measured: bool
    is_energy_estimated: bool
    carbon_gco2e: Optional[float] = None

class PaginatedReceiptsResponse(BaseModel):
    items: List[ReceiptSummaryItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int


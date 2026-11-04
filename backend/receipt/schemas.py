from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from telemetry.schemas import (
    ProvenanceStatus,
    MeasurementScope,
    TokenTelemetry,
    CandidateScore,
    RoutingDecision
)

class ExecutionPath(str, Enum):
    """Execution pathway chosen for the request."""
    DETERMINISTIC_TOOL = "deterministic_tool"
    SEMANTIC_CACHE = "semantic_cache"
    MODEL_INFERENCE = "model_inference"

class CostMetric(BaseModel):
    """Defensible monetary cost calculation."""
    value_usd: Optional[float] = Field(default=None, description="Calculated monetary cost in USD (null if unavailable)")
    provenance: ProvenanceStatus = Field(default=ProvenanceStatus.UNAVAILABLE, description="Authentic cost provenance")
    pricing_source: Optional[str] = Field(default=None, description="Public pricing catalog or rate table used")
    details: Optional[str] = Field(default=None, description="Itemized calculation description")

class EnergyMetric(BaseModel):
    """Energy consumption metric with strict measurement boundary distinction."""
    value_joules: Optional[float] = Field(default=None, description="Energy consumed in Joules")
    value_kwh: Optional[float] = Field(default=None, description="Energy consumed in kilowatt-hours (J / 3,600,000)")
    unit: str = Field(default="J", description="Unit of measurement")
    scope: MeasurementScope = Field(default=MeasurementScope.UNKNOWN, description="Explicit physical measurement boundary")
    provenance: ProvenanceStatus = Field(default=ProvenanceStatus.UNAVAILABLE, description="Energy provenance: MEASURED, ESTIMATED, UNAVAILABLE")
    is_measured: bool = Field(default=False, description="True if directly measured via physical hardware sensor")
    is_estimated: bool = Field(default=False, description="True if derived from a validated estimation model")
    device_platform: Optional[str] = Field(default=None, description="Hardware device identifier if measured on-device")
    scope_disclaimer: str = Field(default="", description="Explicit boundary disclosure (e.g. GPU-only, not full system)")

class CarbonMetric(BaseModel):
    """Operational carbon emissions metric conditioned on valid grid intensity."""
    value_gco2e: Optional[float] = Field(default=None, description="Operational carbon emissions in gCO2e")
    unit: str = Field(default="gCO2e", description="Unit of emissions")
    scope: Optional[MeasurementScope] = Field(default=None, description="Carbon accounting boundary (e.g. GPU_BOARD_OPERATIONAL_CARBON)")
    provenance: ProvenanceStatus = Field(default=ProvenanceStatus.UNAVAILABLE, description="Carbon provenance: ESTIMATED, UNAVAILABLE")
    grid_intensity_gco2e_per_kwh: Optional[float] = Field(default=None, description="Grid carbon intensity factor applied (gCO2e/kWh)")
    grid_source: Optional[str] = Field(default=None, description="Source or regional reporting authority for grid intensity")
    formula: Optional[str] = Field(default=None, description="Mathematical equation used for calculation")

class WaterMetric(BaseModel):
    """Water consumption metric respecting anti-fabrication safeguards."""
    value_liters: Optional[float] = Field(default=None, description="Water consumed in liters (null if unavailable)")
    unit: str = Field(default="L", description="Unit of volume")
    accounting_scope: str = Field(default="unavailable", description="Water accounting scope category")
    provenance: ProvenanceStatus = Field(default=ProvenanceStatus.UNAVAILABLE, description="Water provenance (UNAVAILABLE in absence of verified data)")
    reason_unavailable: str = Field(
        default="Cloud provider or platform does not disclose data-center facility WUE or operational cooling consumption.",
        description="Integrity reason why water is unavailable"
    )

class EnvironmentalBreakdown(BaseModel):
    """Complete environmental footprint breakdown with provenance and source citations."""
    energy: EnergyMetric = Field(default_factory=EnergyMetric)
    carbon: CarbonMetric = Field(default_factory=CarbonMetric)
    water: WaterMetric = Field(default_factory=WaterMetric)
    source_id: Optional[str] = Field(default=None, description="Versioned registry source ID if estimated")
    source_name: Optional[str] = Field(default=None, description="Formal title or citation of estimation source")
    source_version: Optional[str] = Field(default=None, description="Version of source methodology")
    estimator_name: Optional[str] = Field(default=None, description="Name of the estimation adapter")
    estimator_version: Optional[str] = Field(default=None, description="Version of the estimation adapter")
    assumptions: List[str] = Field(default_factory=list, description="Methodological assumptions underpinning estimates")
    uncertainty_info: Optional[str] = Field(default=None, description="Documented confidence or uncertainty limitations")
    unavailable_reasons: Dict[str, str] = Field(default_factory=dict, description="Reasons specific metrics are unavailable")

class OptimizerSummary(BaseModel):
    """Summary of the Phase 6 multi-objective routing decision."""
    decision_id: Optional[str] = Field(default=None, description="Routing decision ID")
    selected_candidate: str = Field(..., description="Candidate route selected by optimizer")
    selected_tier: Optional[str] = Field(default=None, description="Logical model tier if applicable")
    routing_rationale: str = Field(..., description="Explainable justification for route selection")
    quality_threshold_required: float = Field(..., description="Minimum quality threshold Q_req enforced")
    quality_threshold_met: bool = Field(..., description="Whether the selected route satisfies quality threshold")
    pareto_frontier: List[str] = Field(default_factory=list, description="Routes on the Pareto-optimal frontier")
    active_weights: Dict[str, float] = Field(default_factory=dict, description="Active objective weights after dynamic renormalization")
    candidate_scores: List[CandidateScore] = Field(default_factory=list, description="Complete evaluation breakdown for candidates")
    fallback_applied: bool = Field(default=False, description="Whether fallback policy was engaged")
    fallback_reason: Optional[str] = Field(default=None, description="Explanation if fallback was applied")

class ReceiptExplainability(BaseModel):
    """Human-readable explainability for the execution and its resource implications."""
    selection_summary: str = Field(..., description="Why this route was selected based on query complexity and constraints")
    measurement_vs_estimation: str = Field(..., description="Summary of which metrics are directly measured vs estimated")
    unavailable_metrics_rationale: str = Field(..., description="Explanation of missing or unavailable metrics")
    caveats_and_uncertainty: str = Field(..., description="Scope boundaries, limitations, and non-optimality disclaimer")

class AvoidanceSummary(BaseModel):
    """Operational avoidance facts relative to counterfactual model baseline."""
    model_calls_avoided: int = Field(default=0, description="Inference calls avoided relative to baseline")
    tokens_avoided: Optional[int] = Field(default=None, description="Estimated tokens avoided if baseline is known")
    baseline_route: str = Field(default="large_model", description="Baseline comparison route")
    reasoning: str = Field(default="", description="Operational justification for avoidance")
    defensible_savings_reported: bool = Field(default=False, description="True only if physical baseline exists for comparison")
    savings_notice: str = Field(default="", description="Integrity notice on avoidance vs physical savings")

class EcoReceipt(BaseModel):
    """
    Structured, machine-readable Eco Receipt generated for each completed request.
    Translates authentic telemetry, multi-objective optimization decisions, and environmental
    accounting into a transparent, defensible resource invoice.
    """
    receipt_id: str = Field(..., description="Unique receipt identifier (e.g. rcpt_<uuid>)")
    request_id: str = Field(..., description="Associated request ID")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp of request completion")
    status: str = Field(default="SUCCESS", description="Request execution status: SUCCESS, FAILED, PARTIAL")
    execution_path: ExecutionPath = Field(..., description="Execution path: deterministic_tool, semantic_cache, or model_inference")
    route: str = Field(..., description="Selected route display label")
    provider: str = Field(..., description="Provider name")
    model: Optional[str] = Field(default=None, description="Model identifier if model was invoked")
    query_preview: Optional[str] = Field(default=None, description="Preview of user query or expression")
    
    # Latency & Operational Telemetry
    execution_time_ms: float = Field(..., description="Total control plane processing time in milliseconds")
    inference_latency_ms: Optional[float] = Field(default=None, description="Direct tool or model inference latency in ms")
    latency_provenance: ProvenanceStatus = Field(default=ProvenanceStatus.MEASURED, description="Latency provenance")
    tokens: TokenTelemetry = Field(default_factory=TokenTelemetry, description="Authentic token telemetry")
    cost: CostMetric = Field(default_factory=CostMetric, description="Defensible monetary cost calculation")
    
    # Environmental Breakdown
    environment: EnvironmentalBreakdown = Field(default_factory=EnvironmentalBreakdown, description="Itemized environmental breakdown")
    
    # Avoidance & Operational Baseline Facts
    avoidance: Optional[AvoidanceSummary] = Field(default=None, description="Avoided calls/tokens relative to baseline")
    
    # Multi-Objective Optimizer Record (Phase 6)
    optimizer: Optional[OptimizerSummary] = Field(default=None, description="Optimizer candidate evaluation and decision metadata")
    
    # Human-Readable Explainability
    explainability: ReceiptExplainability = Field(..., description="Transparent explainability and integrity disclosures")


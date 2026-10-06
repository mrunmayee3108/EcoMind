from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class ProvenanceStatus(str, Enum):
    """
    Data provenance and measurement authenticity classification.
    Phase 5A strictly distinguishes between directly measured hardware data,
    provider-reported API metadata, and unavailable physical metrics.
    ESTIMATED is intentionally not used in Phase 5A.
    """
    MEASURED = "MEASURED"
    PROVIDER_REPORTED = "PROVIDER_REPORTED"
    UNAVAILABLE = "UNAVAILABLE"

class MeasurementScope(str, Enum):
    """
    Explicit physical boundary/scope for what was actually measured.
    Do NOT call all device measurements simply 'energy'.
    The scope specifies the exact measurement boundary.
    """
    GPU_INFERENCE_WINDOW = "GPU_INFERENCE_WINDOW"
    DEVICE = "DEVICE"
    SYSTEM = "SYSTEM"
    CLOUD_INFERENCE = "CLOUD_INFERENCE"
    UNKNOWN = "UNKNOWN"

class MeasurementCapabilities(BaseModel):
    """
    Capability response structure defining which physical measurement sources
    are supported or unavailable on the host system / active execution path.
    """
    gpu_energy: str = Field(default="unavailable", description="'supported' or 'unavailable'")
    system_energy: str = Field(default="unavailable", description="'supported' or 'unavailable'")
    device_energy: str = Field(default="unavailable", description="'supported' or 'unavailable'")
    provider_energy: str = Field(default="unavailable", description="'supported' or 'unavailable'")

class PhysicalMeasurement(BaseModel):
    """
    Platform-agnostic physical measurement data container.
    Captures measured energy/power with strict provenance, explicit scope,
    and capability availability status.
    """
    value: Optional[float] = Field(default=None, description="Measured numeric energy value (e.g. in Joules)")
    unit: str = Field(default="J", description="Unit of measurement (e.g., J for Joules)")
    provenance: ProvenanceStatus = Field(
        default=ProvenanceStatus.UNAVAILABLE,
        description="Authentic provenance: MEASURED, PROVIDER_REPORTED, or UNAVAILABLE"
    )
    source: str = Field(default="UnavailableProvider", description="Measurement provider/sensor source name")
    scope: MeasurementScope = Field(default=MeasurementScope.UNKNOWN, description="Explicit measurement boundary/scope")
    device_platform: Optional[str] = Field(default=None, description="Physical device or platform identifier")
    status: str = Field(
        default="UNAVAILABLE",
        description="Capability availability status (e.g. AVAILABLE, UNAVAILABLE) - NOT statistical confidence"
    )
    timestamp: Optional[str] = Field(default=None, description="ISO-8601 UTC timestamp of measurement")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional vendor or sensor telemetry metadata")

class TokenTelemetry(BaseModel):
    """Accurately records token counts without fabricating values."""
    input_tokens: Optional[int] = Field(default=None, description="Prompt/input tokens consumed")
    output_tokens: Optional[int] = Field(default=None, description="Completion/candidate tokens produced")
    total_tokens: Optional[int] = Field(default=None, description="Total tokens processed")
    provenance: ProvenanceStatus = Field(
        default=ProvenanceStatus.UNAVAILABLE,
        description="Data provenance: PROVIDER_REPORTED for APIs, MEASURED for tools/cache, UNAVAILABLE if absent"
    )

class LatencyTelemetry(BaseModel):
    """Execution and inference latency metrics measured in milliseconds."""
    inference_latency_ms: Optional[float] = Field(
        default=None,
        description="Duration of the direct model API call or tool execution"
    )
    execution_time_ms: float = Field(
        ...,
        description="Total end-to-end request processing time in the control plane"
    )
    provenance: ProvenanceStatus = Field(
        default=ProvenanceStatus.MEASURED,
        description="Latency measured by high-resolution system timers (time.perf_counter)"
    )

class GpuTelemetry(BaseModel):
    """
    Direct physical measurement from on-device GPU telemetry (NVML / nvidia-smi).
    Clearly labeled as GPU-only energy; does NOT claim to represent total system energy.
    """
    device_name: Optional[str] = Field(default=None, description="Name of the physical GPU")
    average_power_watts: Optional[float] = Field(default=None, description="Average GPU power draw during inference window")
    peak_power_watts: Optional[float] = Field(default=None, description="Peak GPU power draw observed")
    energy_joules: Optional[float] = Field(default=None, description="Integrated GPU energy in Joules (W * s)")
    sample_count: int = Field(default=0, description="Number of discrete power samples taken")
    measurement_duration_ms: Optional[float] = Field(default=None, description="Duration of the GPU sampling window")
    provenance: ProvenanceStatus = Field(
        default=ProvenanceStatus.UNAVAILABLE,
        description="MEASURED if physical hardware was sampled; UNAVAILABLE otherwise"
    )
    label: str = Field(
        default="MEASURED GPU ENERGY (INFERENCE WINDOW ONLY - NOT TOTAL SYSTEM ENERGY)",
        description="Explicit limitation disclaimer"
    )
    scope: MeasurementScope = Field(
        default=MeasurementScope.GPU_INFERENCE_WINDOW,
        description="Explicit measurement boundary"
    )
    source: str = Field(
        default="NvidiaNvmlProvider",
        description="Sensor or measurement provider source"
    )

class EnvironmentalTelemetry(BaseModel):
    """
    Physical environmental metrics for inference execution.
    In Phase 5A, physical environmental data is UNAVAILABLE for cloud providers
    and zero values are fabricated.
    """
    energy_joules: Optional[float] = Field(
        default=None,
        description="Physical energy consumed. Null for cloud APIs; populated only when on-device measurement is sampled."
    )
    water_liters: Optional[float] = Field(
        default=None,
        description="Water consumption. UNAVAILABLE in Phase 5A (no fabrication)."
    )
    carbon_gco2e: Optional[float] = Field(
        default=None,
        description="Carbon emissions. UNAVAILABLE in Phase 5A (no fabrication)."
    )
    provenance: ProvenanceStatus = Field(
        default=ProvenanceStatus.UNAVAILABLE,
        description="Status of environmental metrics"
    )
    gpu_telemetry: Optional[GpuTelemetry] = Field(
        default=None,
        description="Physical GPU measurements if local GPU execution was sampled"
    )
    measurement: Optional[PhysicalMeasurement] = Field(
        default=None,
        description="Platform-agnostic physical measurement structure"
    )
    measurement_capabilities: MeasurementCapabilities = Field(
        default_factory=MeasurementCapabilities,
        description="Capability response indicating which measurement sources are supported"
    )
    note: str = Field(
        default="Physical environmental data is UNAVAILABLE for cloud APIs in Phase 5A. Local GPU energy is populated only when measured on-device.",
        description="Integrity disclosure"
    )

class TelemetryRecord(BaseModel):
    """Comprehensive telemetry record for a single control plane request."""
    request_id: str = Field(..., description="Unique identifier for the request")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp of execution")
    route: str = Field(..., description="Route selected (e.g. Small Model, Calculator, semantic_cache)")
    provider: str = Field(..., description="Provider name (e.g. groq, google, local, deterministic, cache)")
    model: Optional[str] = Field(default=None, description="Model identifier if an LLM was invoked")
    success: bool = Field(..., description="Whether the execution succeeded")
    error_message: Optional[str] = Field(default=None, description="Error detail if execution failed")
    tokens: TokenTelemetry = Field(default_factory=TokenTelemetry)
    latency: LatencyTelemetry
    environment: EnvironmentalTelemetry = Field(default_factory=EnvironmentalTelemetry)

class TelemetrySummary(BaseModel):
    """Aggregated summary of recorded telemetry events."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens_recorded: int = 0
    gpu_measured_requests: int = 0
    physical_measured_requests: int = 0
    routes_breakdown: Dict[str, int] = Field(default_factory=dict)
    providers_breakdown: Dict[str, int] = Field(default_factory=dict)
    measurement_capabilities: MeasurementCapabilities = Field(default_factory=MeasurementCapabilities)

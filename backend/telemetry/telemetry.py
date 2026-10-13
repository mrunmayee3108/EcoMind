import uuid
import threading
from datetime import datetime, timezone
from collections import deque
from typing import Optional, List, Dict, Any, Union

from .schemas import (
    ProvenanceStatus,
    MeasurementScope,
    MeasurementCapabilities,
    PhysicalMeasurement,
    TokenTelemetry,
    LatencyTelemetry,
    GpuTelemetry,
    EnvironmentalTelemetry,
    AvoidanceTelemetry,
    TelemetryRecord,
    TelemetrySummary
)
from .measurement import (
    MeasurementProvider,
    get_system_measurement_capabilities,
)
from config.settings import settings
from models.provider import TokenUsage

class TelemetryCollector:
    """
    Central telemetry management component for EcoMind Phase 5A.
    Accurately records real execution telemetry (timestamps, routes, providers,
    tokens, latencies, success/failure, and hardware-agnostic physical measurements)
    with strict data provenance and zero fabrication.

    Decoupled from specific hardware implementations via the MeasurementProvider interface.
    """

    def __init__(self, max_records: int = 1000):
        self._max_records = max_records
        self._records = deque(maxlen=max_records)
        self._lock = threading.Lock()

    def record_success(
        self,
        route: str,
        provider: str,
        execution_time_ms: float,
        model: Optional[str] = None,
        inference_latency_ms: Optional[float] = None,
        token_usage: Optional[Union[TokenUsage, Dict[str, Any]]] = None,
        physical_measurement: Optional[Union[PhysicalMeasurement, Dict[str, Any]]] = None,
        gpu_telemetry: Optional[Union[GpuTelemetry, Dict[str, Any]]] = None,
        request_id: Optional[str] = None,
        avoidance: Optional[AvoidanceTelemetry] = None
    ) -> TelemetryRecord:
        """Record telemetry for a successfully executed control plane query."""
        req_id = request_id or str(uuid.uuid4())
        ts = datetime.now(timezone.utc).isoformat()

        # 1. Token Telemetry & Provenance
        tokens = self._resolve_token_telemetry(provider, token_usage)

        # 2. Latency Telemetry & Provenance
        latency = LatencyTelemetry(
            inference_latency_ms=round(inference_latency_ms, 2) if inference_latency_ms is not None else None,
            execution_time_ms=round(execution_time_ms, 2),
            provenance=ProvenanceStatus.MEASURED
        )

        # 3. Environmental Telemetry & Provenance (Hardware-Agnostic)
        env = self._resolve_environmental_telemetry(
            provider=provider,
            physical_measurement=physical_measurement,
            gpu_telemetry=gpu_telemetry
        )

        # 4. Model Call & Token Avoidance Telemetry (Phase 5B)
        if avoidance is None and provider in ("deterministic", "cache"):
            avoidance = AvoidanceTelemetry(
                model_calls_avoided=1,
                tokens_avoided=None,
                baseline_route="large_model",
                reasoning=f"Satisfied via {provider} without neural network inference."
            )

        record = TelemetryRecord(
            request_id=req_id,
            timestamp=ts,
            route=route,
            provider=provider,
            model=model,
            success=True,
            error_message=None,
            tokens=tokens,
            latency=latency,
            environment=env,
            avoidance=avoidance
        )

        with self._lock:
            self._records.append(record)

        return record

    def record_failure(
        self,
        route: str,
        provider: str,
        execution_time_ms: float,
        error_message: str,
        model: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> TelemetryRecord:
        """Record telemetry for a failed execution."""
        req_id = request_id or str(uuid.uuid4())
        ts = datetime.now(timezone.utc).isoformat()

        record = TelemetryRecord(
            request_id=req_id,
            timestamp=ts,
            route=route,
            provider=provider,
            model=model,
            success=False,
            error_message=str(error_message),
            tokens=TokenTelemetry(
                input_tokens=None,
                output_tokens=None,
                total_tokens=None,
                provenance=ProvenanceStatus.UNAVAILABLE
            ),
            latency=LatencyTelemetry(
                inference_latency_ms=None,
                execution_time_ms=round(execution_time_ms, 2),
                provenance=ProvenanceStatus.MEASURED
            ),
            environment=EnvironmentalTelemetry(
                energy_joules=None,
                water_liters=None,
                carbon_gco2e=None,
                provenance=ProvenanceStatus.UNAVAILABLE,
                gpu_telemetry=None,
                measurement=PhysicalMeasurement(
                    value=None,
                    unit="J",
                    provenance=ProvenanceStatus.UNAVAILABLE,
                    source="UnavailableProvider",
                    scope=MeasurementScope.UNKNOWN,
                    status="UNAVAILABLE",
                    timestamp=ts,
                    details={"error": str(error_message)}
                ),
                measurement_capabilities=get_system_measurement_capabilities(),
                note="Execution failed; physical environmental telemetry is UNAVAILABLE."
            )
        )

        with self._lock:
            self._records.append(record)

        return record

    def _resolve_token_telemetry(
        self,
        provider: str,
        token_usage: Optional[Union[TokenUsage, Dict[str, Any]]]
    ) -> TokenTelemetry:
        """Resolve token counts and assign authentic data provenance."""
        # Deterministic tools and cache hits have direct certainty of 0 tokens consumed
        if provider in ("deterministic", "cache"):
            return TokenTelemetry(
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                provenance=ProvenanceStatus.MEASURED
            )

        if token_usage is None:
            return TokenTelemetry(
                input_tokens=None,
                output_tokens=None,
                total_tokens=None,
                provenance=ProvenanceStatus.UNAVAILABLE
            )

        # Handle dataclass or dict
        if isinstance(token_usage, dict):
            prompt = token_usage.get("prompt_tokens")
            comp = token_usage.get("completion_tokens")
            total = token_usage.get("total_tokens")
        else:
            prompt = getattr(token_usage, "prompt_tokens", None)
            comp = getattr(token_usage, "completion_tokens", None)
            total = getattr(token_usage, "total_tokens", None)

        if prompt is not None or comp is not None or total is not None:
            return TokenTelemetry(
                input_tokens=prompt,
                output_tokens=comp,
                total_tokens=total,
                provenance=ProvenanceStatus.PROVIDER_REPORTED
            )

        return TokenTelemetry(
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            provenance=ProvenanceStatus.UNAVAILABLE
        )

    def _resolve_environmental_telemetry(
        self,
        provider: str,
        physical_measurement: Optional[Union[PhysicalMeasurement, Dict[str, Any]]],
        gpu_telemetry: Optional[Union[GpuTelemetry, Dict[str, Any]]]
    ) -> EnvironmentalTelemetry:
        """
        Resolve environmental metrics with zero fabrication and strict provenance.
        Supports generic PhysicalMeasurement, with backward compatibility for GpuTelemetry.
        Cloud APIs (Groq, Google) have physical energy marked as UNAVAILABLE.
        """
        ts = datetime.now(timezone.utc).isoformat()
        sys_caps = get_system_measurement_capabilities()

        # Parse physical_measurement if provided
        meas_obj: Optional[PhysicalMeasurement] = None
        if physical_measurement is not None:
            if isinstance(physical_measurement, dict):
                meas_obj = PhysicalMeasurement(**physical_measurement)
            elif isinstance(physical_measurement, PhysicalMeasurement):
                meas_obj = physical_measurement

        # Parse gpu_telemetry if provided (backward compatibility)
        gpu_obj: Optional[GpuTelemetry] = None
        if gpu_telemetry is not None:
            if isinstance(gpu_telemetry, dict):
                gpu_obj = GpuTelemetry(**gpu_telemetry)
            elif isinstance(gpu_telemetry, GpuTelemetry):
                gpu_obj = gpu_telemetry

        # If gpu_telemetry was provided but meas_obj was not, bridge it into a PhysicalMeasurement
        if gpu_obj is not None and meas_obj is None:
            if gpu_obj.provenance == ProvenanceStatus.MEASURED and gpu_obj.energy_joules is not None:
                meas_obj = PhysicalMeasurement(
                    value=gpu_obj.energy_joules,
                    unit="J",
                    provenance=ProvenanceStatus.MEASURED,
                    source=gpu_obj.source or "NvidiaNvmlProvider",
                    scope=gpu_obj.scope or MeasurementScope.GPU_INFERENCE_WINDOW,
                    device_platform=gpu_obj.device_name or "NVIDIA GPU",
                    status="AVAILABLE",
                    timestamp=ts,
                    details={
                        "label": gpu_obj.label,
                        "average_power_watts": gpu_obj.average_power_watts,
                        "peak_power_watts": gpu_obj.peak_power_watts,
                        "sample_count": gpu_obj.sample_count,
                        "measurement_duration_ms": gpu_obj.measurement_duration_ms
                    }
                )
            else:
                meas_obj = PhysicalMeasurement(
                    value=None,
                    unit="J",
                    provenance=ProvenanceStatus.UNAVAILABLE,
                    source=gpu_obj.source or "NvidiaNvmlProvider",
                    scope=gpu_obj.scope or MeasurementScope.GPU_INFERENCE_WINDOW,
                    device_platform=gpu_obj.device_name,
                    status="UNAVAILABLE",
                    timestamp=ts,
                    details={"label": gpu_obj.label}
                )

        # If meas_obj was provided and is MEASURED
        if meas_obj and meas_obj.provenance == ProvenanceStatus.MEASURED and meas_obj.value is not None:
            # If scope is GPU_INFERENCE_WINDOW and gpu_obj is missing, bridge back to gpu_obj
            if meas_obj.scope == MeasurementScope.GPU_INFERENCE_WINDOW and gpu_obj is None:
                det = meas_obj.details or {}
                gpu_obj = GpuTelemetry(
                    device_name=meas_obj.device_platform,
                    average_power_watts=det.get("average_power_watts"),
                    peak_power_watts=det.get("peak_power_watts"),
                    energy_joules=meas_obj.value,
                    sample_count=det.get("sample_count", 1),
                    measurement_duration_ms=det.get("measurement_duration_ms"),
                    provenance=ProvenanceStatus.MEASURED,
                    label=det.get("label", "MEASURED GPU ENERGY (INFERENCE WINDOW ONLY - NOT TOTAL SYSTEM ENERGY)"),
                    scope=meas_obj.scope,
                    source=meas_obj.source
                )

            caps = MeasurementCapabilities(
                gpu_energy="supported" if meas_obj.scope == MeasurementScope.GPU_INFERENCE_WINDOW else "unavailable",
                system_energy="supported" if meas_obj.scope == MeasurementScope.SYSTEM else "unavailable",
                device_energy="supported" if meas_obj.scope == MeasurementScope.DEVICE else "unavailable",
                provider_energy="supported" if meas_obj.provenance == ProvenanceStatus.PROVIDER_REPORTED else "unavailable"
            )

            # Phase 5B: Conditional Local GPU Carbon Calculation
            carbon_val = None
            carbon_scope = None
            carbon_prov = ProvenanceStatus.UNAVAILABLE
            grid_intensity_used = None

            if meas_obj.scope == MeasurementScope.GPU_INFERENCE_WINDOW:
                grid_factor = getattr(settings, "LOCAL_GRID_INTENSITY_GCO2E_PER_KWH", None)
                if grid_factor is not None and isinstance(grid_factor, (int, float)) and grid_factor > 0:
                    # 1 kWh = 3,600,000 J
                    energy_kwh = meas_obj.value / 3600000.0
                    carbon_val = round(energy_kwh * float(grid_factor), 6)
                    carbon_scope = MeasurementScope.GPU_BOARD_OPERATIONAL_CARBON
                    carbon_prov = ProvenanceStatus.ESTIMATED
                    grid_intensity_used = float(grid_factor)

            if carbon_val is not None:
                note_str = (
                    f"Physical GPU energy directly measured ({meas_obj.scope.value} via {meas_obj.source}). "
                    f"GPU-board operational carbon estimated at {carbon_val} gCO2e using configured grid intensity ({grid_intensity_used} gCO2e/kWh). "
                    "Strictly scoped to GPU board; does NOT represent total system energy. Water is UNAVAILABLE."
                )
            else:
                note_str = (
                    f"Physical energy directly measured ({meas_obj.scope.value} via {meas_obj.source}). "
                    "Does NOT represent total system energy. Water is UNAVAILABLE. "
                    "Operational carbon is UNAVAILABLE (configure LOCAL_GRID_INTENSITY_GCO2E_PER_KWH to enable GPU-board carbon calculation)."
                )

            return EnvironmentalTelemetry(
                energy_joules=meas_obj.value,
                water_liters=None,
                carbon_gco2e=carbon_val,
                carbon_scope=carbon_scope,
                grid_intensity_gco2e_per_kwh=grid_intensity_used,
                provenance=ProvenanceStatus.MEASURED,
                energy_provenance=ProvenanceStatus.MEASURED,
                carbon_provenance=carbon_prov,
                water_provenance=ProvenanceStatus.UNAVAILABLE,
                gpu_telemetry=gpu_obj,
                measurement=meas_obj,
                measurement_capabilities=caps,
                note=note_str
            )

        # Execution without real physical measurement (Cloud APIs, tools, cache, or unavailable hardware)
        cloud_scope = MeasurementScope.CLOUD_INFERENCE if provider in ("groq", "google") else MeasurementScope.UNKNOWN
        fallback_meas = meas_obj or PhysicalMeasurement(
            value=None,
            unit="J",
            provenance=ProvenanceStatus.UNAVAILABLE,
            source="UnavailableProvider",
            scope=cloud_scope,
            device_platform=None,
            status="UNAVAILABLE",
            timestamp=ts,
            details={"note": f"Physical measurement unavailable for provider '{provider}'."}
        )

        return EnvironmentalTelemetry(
            energy_joules=None,
            water_liters=None,
            carbon_gco2e=None,
            carbon_scope=None,
            grid_intensity_gco2e_per_kwh=None,
            provenance=ProvenanceStatus.UNAVAILABLE,
            energy_provenance=ProvenanceStatus.UNAVAILABLE,
            carbon_provenance=ProvenanceStatus.UNAVAILABLE,
            water_provenance=ProvenanceStatus.UNAVAILABLE,
            gpu_telemetry=None,
            measurement=fallback_meas,
            measurement_capabilities=sys_caps,
            note="Physical environmental metrics are UNAVAILABLE for cloud APIs and non-measured executions in Phase 5B (zero fabrication)."
        )

    def get_capabilities(self) -> MeasurementCapabilities:
        """Return the physical measurement capabilities supported by the host environment."""
        return get_system_measurement_capabilities()

    def get_recent(self, limit: int = 50) -> List[TelemetryRecord]:
        """Return the most recent telemetry records in reverse chronological order."""
        with self._lock:
            items = list(self._records)
        return items[-limit:][::-1]

    def get_summary(self) -> TelemetrySummary:
        """Produce aggregated summary statistics from stored telemetry."""
        with self._lock:
            items = list(self._records)

        summary = TelemetrySummary()
        summary.total_requests = len(items)
        summary.measurement_capabilities = self.get_capabilities()

        for rec in items:
            if rec.success:
                summary.successful_requests += 1
            else:
                summary.failed_requests += 1

            if rec.tokens.total_tokens:
                summary.total_tokens_recorded += rec.tokens.total_tokens

            if rec.environment.provenance == ProvenanceStatus.MEASURED:
                summary.physical_measured_requests += 1

            if rec.environment.gpu_telemetry and rec.environment.gpu_telemetry.provenance == ProvenanceStatus.MEASURED:
                summary.gpu_measured_requests += 1

            summary.routes_breakdown[rec.route] = summary.routes_breakdown.get(rec.route, 0) + 1
            summary.providers_breakdown[rec.provider] = summary.providers_breakdown.get(rec.provider, 0) + 1

        return summary

    def get_record(self, request_id: str) -> Optional[TelemetryRecord]:
        """Find and return a recorded telemetry record by its unique request ID."""
        with self._lock:
            for rec in self._records:
                if rec.request_id == request_id:
                    return rec
        return None

    def clear(self):
        """Reset all in-memory telemetry records."""
        with self._lock:
            self._records.clear()

# Global telemetry collector singleton
telemetry_collector = TelemetryCollector()

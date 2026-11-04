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
from .grid import grid_manager
from .water import water_accounting_engine
from .cloud_estimator import cloud_energy_estimator
from .registry import source_registry, source_validation_service
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
            gpu_telemetry=gpu_telemetry,
            model=model,
            tokens=tokens,
            inference_latency_ms=inference_latency_ms
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
                unavailable_reasons={"execution": f"Execution failed: {str(error_message)}"},
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
        gpu_telemetry: Optional[Union[GpuTelemetry, Dict[str, Any]]],
        model: Optional[str] = None,
        tokens: Optional[TokenTelemetry] = None,
        inference_latency_ms: Optional[float] = None
    ) -> EnvironmentalTelemetry:
        """
        Resolve environmental metrics with zero fabrication and strict provenance.
        Supports:
        1. Local GPU hardware sensor measurements (NVML).
        2. Verified empirical / LCA estimators for cloud inference (ML.ENERGY / EcoLogits).
        3. Strict UNAVAILABLE status for unmeasured or unsupported executions.
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

        # 1. On-Device Physical Measurement (e.g. Local NVIDIA GPU via NVML)
        if meas_obj and meas_obj.provenance == ProvenanceStatus.MEASURED and meas_obj.value is not None:
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

            # Operational carbon calculation via grid_manager
            carbon_val = None
            carbon_scope = None
            carbon_prov = ProvenanceStatus.UNAVAILABLE
            grid_intensity_used = None

            if meas_obj.scope == MeasurementScope.GPU_INFERENCE_WINDOW:
                carbon_val, grid_rec = grid_manager.calculate_operational_carbon(meas_obj.value)
                if carbon_val is not None and grid_rec is not None:
                    carbon_scope = MeasurementScope.GPU_BOARD_OPERATIONAL_CARBON
                    carbon_prov = ProvenanceStatus.ESTIMATED
                    grid_intensity_used = grid_rec.intensity_gco2e_per_kwh

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

            _, water_prov, water_expl = water_accounting_engine.evaluate_water(provider, model, meas_obj.scope)

            return EnvironmentalTelemetry(
                energy_joules=meas_obj.value,
                water_liters=None,
                carbon_gco2e=carbon_val,
                carbon_scope=carbon_scope,
                grid_intensity_gco2e_per_kwh=grid_intensity_used,
                provenance=ProvenanceStatus.MEASURED,
                energy_provenance=ProvenanceStatus.MEASURED,
                carbon_provenance=carbon_prov,
                water_provenance=water_prov,
                gpu_telemetry=gpu_obj,
                measurement=meas_obj,
                measurement_capabilities=caps,
                source_id="src-nvml-nvidia-2024",
                source_version="12.0",
                estimator_name="NvidiaNvmlProvider",
                estimator_version="1.0.0",
                data_freshness_status="CURRENT",
                assumptions=[
                    "On-device GPU board power sampled via NVML C-bindings during inference window only",
                    "Host CPU, DRAM, storage, fans, and power supply losses excluded"
                ],
                uncertainty_info="Board-level power accuracy is +/- 5W per NVIDIA hardware sensor specifications.",
                unavailable_reasons={"water": water_expl.get("reason", "Water is UNAVAILABLE on air-cooled client.")},
                note=note_str
            )

        # 2. Cloud Inference Environmental Estimation (Phase 5B Upgrade)
        enable_cloud_est = getattr(settings, "ENABLE_CLOUD_ENERGY_ESTIMATION", False)
        if enable_cloud_est and provider in ("groq", "google", "openai", "anthropic", "cloud") and model:
            p_in = tokens.input_tokens if (tokens and tokens.input_tokens is not None) else 0
            p_out = tokens.output_tokens if (tokens and tokens.output_tokens is not None) else 0
            if (p_in > 0 or p_out > 0) and cloud_energy_estimator.supports(provider, model):
                est_res = cloud_energy_estimator.estimate(
                    provider=provider,
                    model=model,
                    prompt_tokens=p_in,
                    completion_tokens=p_out,
                    latency_ms=inference_latency_ms
                )
                if est_res:
                    est_meas = PhysicalMeasurement(
                        value=est_res.energy_joules,
                        unit="J",
                        provenance=ProvenanceStatus.ESTIMATED,
                        source=est_res.estimator_name,
                        scope=est_res.scope,
                        device_platform=None,
                        status="AVAILABLE",
                        timestamp=ts,
                        details={"assumptions": est_res.assumptions}
                    )
                    return EnvironmentalTelemetry(
                        energy_joules=est_res.energy_joules,
                        water_liters=None,
                        carbon_gco2e=None,
                        carbon_scope=None,
                        grid_intensity_gco2e_per_kwh=None,
                        provenance=ProvenanceStatus.ESTIMATED,
                        energy_provenance=ProvenanceStatus.ESTIMATED,
                        carbon_provenance=ProvenanceStatus.UNAVAILABLE,
                        water_provenance=ProvenanceStatus.UNAVAILABLE,
                        gpu_telemetry=None,
                        measurement=est_meas,
                        measurement_capabilities=sys_caps,
                        source_id=est_res.source_id,
                        source_version=est_res.source_version,
                        estimator_name=est_res.estimator_name,
                        estimator_version=est_res.estimator_version,
                        data_freshness_status="CURRENT",
                        assumptions=est_res.assumptions,
                        uncertainty_info=est_res.uncertainty_info,
                        unavailable_reasons=est_res.unavailable_reasons,
                        note=(
                            f"Cloud inference energy estimated via {est_res.estimator_name} ({est_res.source_id}). "
                            "Authentically labeled ESTIMATED. Direct water and carbon remain UNAVAILABLE without facility disclosures."
                        )
                    )

        # 3. Execution without real physical measurement and without matching estimator
        cloud_scope = MeasurementScope.CLOUD_INFERENCE if provider in ("groq", "google", "openai", "anthropic") else MeasurementScope.UNKNOWN
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

        if provider in ("deterministic", "cache"):
            unav_reasons = {
                "energy": f"Execution handled via {provider} with 0 model tokens. Physical energy is UNAVAILABLE unless hardware counters are sampled.",
                "water": "Water is UNAVAILABLE without host telemetry and regional utility WIE.",
                "carbon": "Carbon is UNAVAILABLE without measured energy."
            }
            note_str = f"Execution handled via {provider} with 0 model tokens. Physical environmental metrics are UNAVAILABLE without hardware sensors."
        else:
            unav_reasons = {
                "energy": f"No validated empirical benchmark or architectural profile available for model '{model}' on provider '{provider}'. Retained as UNAVAILABLE without fabrication.",
                "water": f"Cloud provider '{provider}' does not disclose data-center facility locations, cooling technology, or WUE.",
                "carbon": f"Cloud provider '{provider}' data-center location is opaque; grid emissions factor cannot be resolved."
            }
            note_str = "Physical environmental metrics are UNAVAILABLE for cloud APIs and non-measured executions in Phase 5B (zero fabrication)."

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
            source_id=None,
            source_version=None,
            estimator_name=None,
            estimator_version=None,
            data_freshness_status="NOT_APPLICABLE",
            assumptions=[],
            uncertainty_info="No empirical measurement or validated estimation model available.",
            unavailable_reasons=unav_reasons,
            note=note_str
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

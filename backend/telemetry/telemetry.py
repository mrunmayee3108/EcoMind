import uuid
import threading
from datetime import datetime, timezone
from collections import deque
from typing import Optional, List, Dict, Any, Union

from .schemas import (
    ProvenanceStatus,
    TokenTelemetry,
    LatencyTelemetry,
    GpuTelemetry,
    EnvironmentalTelemetry,
    TelemetryRecord,
    TelemetrySummary
)
from models.provider import TokenUsage

class TelemetryCollector:
    """
    Central telemetry management component for EcoMind Phase 5A.
    Accurately records real execution telemetry (timestamps, routes, providers,
    tokens, latencies, success/failure, and on-device GPU power/energy measurements)
    with strict data provenance and zero fabrication.
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
        gpu_telemetry: Optional[Union[GpuTelemetry, Dict[str, Any]]] = None,
        request_id: Optional[str] = None
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

        # 3. Environmental Telemetry & Provenance
        env = self._resolve_environmental_telemetry(gpu_telemetry)

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
            environment=env
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
                gpu_telemetry=None
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
        gpu_telemetry: Optional[Union[GpuTelemetry, Dict[str, Any]]]
    ) -> EnvironmentalTelemetry:
        """
        Resolve environmental metrics with zero fabrication.
        For cloud APIs (Groq, Google), physical energy, water, and carbon are UNAVAILABLE.
        For local GPU execution, physical GPU energy is attached when directly sampled.
        """
        gpu_obj: Optional[GpuTelemetry] = None
        if gpu_telemetry is not None:
            if isinstance(gpu_telemetry, dict):
                gpu_obj = GpuTelemetry(**gpu_telemetry)
            elif isinstance(gpu_telemetry, GpuTelemetry):
                gpu_obj = gpu_telemetry

        if gpu_obj and gpu_obj.provenance == ProvenanceStatus.MEASURED and gpu_obj.energy_joules is not None:
            return EnvironmentalTelemetry(
                energy_joules=gpu_obj.energy_joules,
                water_liters=None,
                carbon_gco2e=None,
                provenance=ProvenanceStatus.MEASURED,
                gpu_telemetry=gpu_obj,
                note="Physical GPU energy directly measured on-device. Does not represent total system energy. Water and carbon are UNAVAILABLE."
            )

        return EnvironmentalTelemetry(
            energy_joules=None,
            water_liters=None,
            carbon_gco2e=None,
            provenance=ProvenanceStatus.UNAVAILABLE,
            gpu_telemetry=None,
            note="Physical environmental metrics are UNAVAILABLE for cloud APIs and non-GPU executions in Phase 5A (zero fabrication)."
        )

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

        for rec in items:
            if rec.success:
                summary.successful_requests += 1
            else:
                summary.failed_requests += 1

            if rec.tokens.total_tokens:
                summary.total_tokens_recorded += rec.tokens.total_tokens

            if rec.environment.gpu_telemetry and rec.environment.gpu_telemetry.provenance == ProvenanceStatus.MEASURED:
                summary.gpu_measured_requests += 1

            summary.routes_breakdown[rec.route] = summary.routes_breakdown.get(rec.route, 0) + 1
            summary.providers_breakdown[rec.provider] = summary.providers_breakdown.get(rec.provider, 0) + 1

        return summary

    def clear(self):
        """Reset all in-memory telemetry records."""
        with self._lock:
            self._records.clear()

# Global telemetry collector singleton
telemetry_collector = TelemetryCollector()

import time
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from .schemas import (
    ProvenanceStatus,
    MeasurementScope,
    MeasurementCapabilities,
    PhysicalMeasurement,
    GpuTelemetry,
)

class MeasurementProvider(ABC):
    """
    Abstract base interface for physical energy measurement providers.
    
    EcoMind is measurement-capability aware. Physical energy is reported only
    when a trustworthy measurement source is available. The absence of a measurement
    is represented explicitly as UNAVAILABLE rather than replaced with a fabricated estimate.
    """
    name: str = "BaseMeasurementProvider"
    scope: MeasurementScope = MeasurementScope.UNKNOWN
    device_platform: str = "Unknown"

    @abstractmethod
    def is_available(self) -> bool:
        """Detect whether this measurement provider is available on current runtime/hardware."""
        pass

    @abstractmethod
    def get_capabilities(self) -> MeasurementCapabilities:
        """Return the physical measurement capabilities supported by this provider."""
        pass

    def start_measurement(self) -> None:
        """Begin sampling/measurement window (for active hardware monitors)."""
        pass

    def stop_measurement(self) -> None:
        """Stop sampling/measurement window and compute aggregated metrics."""
        pass

    @abstractmethod
    def get_measurement(self) -> PhysicalMeasurement:
        """
        Produce a standardized PhysicalMeasurement with explicit provenance,
        scope, source, and capability availability status.
        """
        pass

    def __enter__(self):
        self.start_measurement()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_measurement()


class NvidiaNvmlProvider(MeasurementProvider):
    """
    Direct physical measurement provider for NVIDIA GPUs via NVML (with nvidia-smi fallback).
    Measures GPU power draw during the inference window on local NVIDIA hardware.

    EXPLICIT LIMITATION & SCOPE:
    Scope: GPU_INFERENCE_WINDOW
    Label: MEASURED GPU ENERGY (INFERENCE WINDOW ONLY - NOT TOTAL SYSTEM ENERGY)
    Captures GPU power draw only. Does NOT claim to represent total system power
    (which includes CPU, DRAM, motherboard, storage, fans, and PSU conversion losses).
    """
    name = "NvidiaNvmlProvider"
    scope = MeasurementScope.GPU_INFERENCE_WINDOW
    device_platform = "NVIDIA"
    LIMITATION_LABEL = "MEASURED GPU ENERGY (INFERENCE WINDOW ONLY - NOT TOTAL SYSTEM ENERGY)"

    def __init__(self, sample_interval_ms: float = 20.0):
        from .gpu import NVMLDevice
        self._sample_interval = sample_interval_ms / 1000.0
        self._device = NVMLDevice()
        self._is_active: bool = False
        self._stop_event = threading.Event()
        self._sample_thread: Optional[threading.Thread] = None
        self._samples: List[float] = []
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
        self._duration_ms: Optional[float] = None
        self._device_name: Optional[str] = self._device.get_device_name()

    def is_available(self) -> bool:
        """Detect whether NVML or nvidia-smi is available on the host machine."""
        from .gpu import FallbackNvidiaSmi
        return bool(self._device.available or FallbackNvidiaSmi.is_available())

    def get_capabilities(self) -> MeasurementCapabilities:
        """Return capabilities based on NVIDIA hardware presence."""
        if self.is_available():
            return MeasurementCapabilities(
                gpu_energy="supported",
                system_energy="unavailable",
                device_energy="unavailable",
                provider_energy="unavailable"
            )
        return MeasurementCapabilities(
            gpu_energy="unavailable",
            system_energy="unavailable",
            device_energy="unavailable",
            provider_energy="unavailable"
        )

    def _sample_loop(self):
        while not self._stop_event.is_set():
            p = self._device.get_power_watts()
            if p is not None:
                self._samples.append(p)
            self._stop_event.wait(self._sample_interval)

    def start_measurement(self):
        """Begin sampling GPU power draw during the inference window."""
        self._samples.clear()
        self._stop_event.clear()
        self._start_time = time.perf_counter()
        self._is_active = True

        if self._device.available:
            self._sample_thread = threading.Thread(target=self._sample_loop, daemon=True)
            self._sample_thread.start()
        else:
            from .gpu import FallbackNvidiaSmi
            if FallbackNvidiaSmi.is_available():
                p, name = FallbackNvidiaSmi.get_power_and_name()
                if p is not None:
                    self._samples.append(p)
                if name and not self._device_name:
                    self._device_name = name

    def stop_measurement(self):
        """Stop power sampling and finalize metrics."""
        if not self._is_active:
            return
        self._end_time = time.perf_counter()
        self._is_active = False
        self._stop_event.set()

        if self._sample_thread is not None and self._sample_thread.is_alive():
            self._sample_thread.join(timeout=0.2)

        if self._start_time is not None and self._end_time is not None:
            self._duration_ms = (self._end_time - self._start_time) * 1000.0

        if self._device.available and not self._samples:
            p = self._device.get_power_watts()
            if p is not None:
                self._samples.append(p)

    def get_measurement(self) -> PhysicalMeasurement:
        """Produce standardized PhysicalMeasurement model."""
        ts = datetime.now(timezone.utc).isoformat()
        if not self.is_available() or not self._samples:
            return PhysicalMeasurement(
                value=None,
                unit="J",
                provenance=ProvenanceStatus.UNAVAILABLE,
                source=self.name,
                scope=self.scope,
                device_platform=self._device_name or "NVIDIA GPU",
                status="UNAVAILABLE",
                timestamp=ts,
                details={
                    "label": self.LIMITATION_LABEL,
                    "sample_count": 0,
                    "duration_ms": self._duration_ms
                }
            )

        avg_power = sum(self._samples) / len(self._samples)
        peak_power = max(self._samples)
        duration_sec = (self._duration_ms or 0.0) / 1000.0
        energy_joules = avg_power * duration_sec

        return PhysicalMeasurement(
            value=round(energy_joules, 6),
            unit="J",
            provenance=ProvenanceStatus.MEASURED,
            source=self.name,
            scope=self.scope,
            device_platform=self._device_name or "NVIDIA GPU",
            status="AVAILABLE",
            timestamp=ts,
            details={
                "label": self.LIMITATION_LABEL,
                "device_name": self._device_name or "NVIDIA GPU",
                "average_power_watts": round(avg_power, 4),
                "peak_power_watts": round(peak_power, 4),
                "energy_joules": round(energy_joules, 6),
                "sample_count": len(self._samples),
                "measurement_duration_ms": round(self._duration_ms or 0.0, 2)
            }
        )

    def to_gpu_telemetry(self) -> GpuTelemetry:
        """Produce backward-compatible GpuTelemetry model for legacy consumers."""
        if not self.is_available() or not self._samples:
            return GpuTelemetry(
                device_name=self._device_name,
                average_power_watts=None,
                peak_power_watts=None,
                energy_joules=None,
                sample_count=0,
                measurement_duration_ms=self._duration_ms,
                provenance=ProvenanceStatus.UNAVAILABLE,
                label=self.LIMITATION_LABEL,
                scope=self.scope,
                source=self.name
            )

        avg_power = sum(self._samples) / len(self._samples)
        peak_power = max(self._samples)
        duration_sec = (self._duration_ms or 0.0) / 1000.0
        energy_joules = avg_power * duration_sec

        return GpuTelemetry(
            device_name=self._device_name or "NVIDIA GPU",
            average_power_watts=round(avg_power, 4),
            peak_power_watts=round(peak_power, 4),
            energy_joules=round(energy_joules, 6),
            sample_count=len(self._samples),
            measurement_duration_ms=round(self._duration_ms or 0.0, 2),
            provenance=ProvenanceStatus.MEASURED,
            label=self.LIMITATION_LABEL,
            scope=self.scope,
            source=self.name
        )


class AndroidEnergyProvider(MeasurementProvider):
    """
    Architecture and interface abstraction for future native Android client device telemetry.

    ARCHITECTURAL NOTE:
    The Python backend runs on server/desktop environments and cannot directly access
    a remote user's mobile device hardware.
    This provider specifies the architectural interface for future native mobile client
    integration (e.g. Android BatteryManager, hardware power rails, or OS energy profiles)
    transmitting validated client telemetry payloads to the backend.

    In the absence of authentic client-transmitted data, it returns UNAVAILABLE.
    Values are never fabricated.
    """
    name = "AndroidEnergyProvider"
    scope = MeasurementScope.DEVICE
    device_platform = "Android"

    def __init__(self, client_payload: Optional[Dict[str, Any]] = None):
        self._client_payload = client_payload

    def is_available(self) -> bool:
        """Available only when a validated native mobile telemetry payload is supplied."""
        return bool(
            self._client_payload
            and isinstance(self._client_payload, dict)
            and self._client_payload.get("energy_joules") is not None
        )

    def get_capabilities(self) -> MeasurementCapabilities:
        if self.is_available():
            return MeasurementCapabilities(
                gpu_energy="unavailable",
                system_energy="unavailable",
                device_energy="supported",
                provider_energy="unavailable"
            )
        return MeasurementCapabilities(
            gpu_energy="unavailable",
            system_energy="unavailable",
            device_energy="unavailable",
            provider_energy="unavailable"
        )

    def ingest_client_telemetry(self, payload: Dict[str, Any]) -> PhysicalMeasurement:
        """Ingest validated native mobile telemetry transmitted by an Android client."""
        self._client_payload = payload
        return self.get_measurement()

    def get_measurement(self) -> PhysicalMeasurement:
        ts = datetime.now(timezone.utc).isoformat()
        if not self.is_available() or not self._client_payload:
            return PhysicalMeasurement(
                value=None,
                unit="J",
                provenance=ProvenanceStatus.UNAVAILABLE,
                source=self.name,
                scope=self.scope,
                device_platform=self.device_platform,
                status="UNAVAILABLE",
                timestamp=ts,
                details={
                    "note": "Native Android mobile client integration is planned future work. No client telemetry received."
                }
            )

        val = float(self._client_payload["energy_joules"])
        prov_str = str(self._client_payload.get("provenance", "MEASURED")).upper()
        prov = ProvenanceStatus.MEASURED if prov_str == "MEASURED" else ProvenanceStatus.PROVIDER_REPORTED
        return PhysicalMeasurement(
            value=round(val, 6),
            unit=self._client_payload.get("unit", "J"),
            provenance=prov,
            source=self.name,
            scope=self.scope,
            device_platform=self._client_payload.get("device_model", self.device_platform),
            status="AVAILABLE",
            timestamp=ts,
            details=self._client_payload
        )


class AppleEnergyProvider(MeasurementProvider):
    """
    Architecture and interface abstraction for future Apple client device telemetry (macOS / iOS).

    ARCHITECTURAL NOTE:
    Defines the contract for receiving native Apple Silicon telemetry (e.g. powermetrics,
    IOKit energy rails, or iOS client battery counters).
    In the absence of authentic client-transmitted data, it returns UNAVAILABLE.
    Values are never fabricated.
    """
    name = "AppleEnergyProvider"
    scope = MeasurementScope.DEVICE
    device_platform = "Apple"

    def __init__(self, client_payload: Optional[Dict[str, Any]] = None):
        self._client_payload = client_payload

    def is_available(self) -> bool:
        """Available only when a validated Apple client telemetry payload is supplied."""
        return bool(
            self._client_payload
            and isinstance(self._client_payload, dict)
            and self._client_payload.get("energy_joules") is not None
        )

    def get_capabilities(self) -> MeasurementCapabilities:
        if self.is_available():
            return MeasurementCapabilities(
                gpu_energy="unavailable",
                system_energy="unavailable",
                device_energy="supported",
                provider_energy="unavailable"
            )
        return MeasurementCapabilities(
            gpu_energy="unavailable",
            system_energy="unavailable",
            device_energy="unavailable",
            provider_energy="unavailable"
        )

    def ingest_client_telemetry(self, payload: Dict[str, Any]) -> PhysicalMeasurement:
        """Ingest validated native telemetry transmitted by an Apple client."""
        self._client_payload = payload
        return self.get_measurement()

    def get_measurement(self) -> PhysicalMeasurement:
        ts = datetime.now(timezone.utc).isoformat()
        if not self.is_available() or not self._client_payload:
            return PhysicalMeasurement(
                value=None,
                unit="J",
                provenance=ProvenanceStatus.UNAVAILABLE,
                source=self.name,
                scope=self.scope,
                device_platform=self.device_platform,
                status="UNAVAILABLE",
                timestamp=ts,
                details={
                    "note": "Native Apple client integration is planned future work. No client telemetry received."
                }
            )

        val = float(self._client_payload["energy_joules"])
        prov_str = str(self._client_payload.get("provenance", "MEASURED")).upper()
        prov = ProvenanceStatus.MEASURED if prov_str == "MEASURED" else ProvenanceStatus.PROVIDER_REPORTED
        return PhysicalMeasurement(
            value=round(val, 6),
            unit=self._client_payload.get("unit", "J"),
            provenance=prov,
            source=self.name,
            scope=self.scope,
            device_platform=self._client_payload.get("device_model", self.device_platform),
            status="AVAILABLE",
            timestamp=ts,
            details=self._client_payload
        )


class UnavailableProvider(MeasurementProvider):
    """
    Fallback/null provider for environments without physical measurement support
    (e.g., cloud API invocations, CPU without power counters, absent GPU).
    """
    name = "UnavailableProvider"
    scope = MeasurementScope.UNKNOWN
    device_platform = "None"

    def is_available(self) -> bool:
        return False

    def get_capabilities(self) -> MeasurementCapabilities:
        return MeasurementCapabilities(
            gpu_energy="unavailable",
            system_energy="unavailable",
            device_energy="unavailable",
            provider_energy="unavailable"
        )

    def get_measurement(self) -> PhysicalMeasurement:
        return PhysicalMeasurement(
            value=None,
            unit="J",
            provenance=ProvenanceStatus.UNAVAILABLE,
            source=self.name,
            scope=self.scope,
            device_platform=None,
            status="UNAVAILABLE",
            timestamp=datetime.now(timezone.utc).isoformat(),
            details={"note": "Physical energy measurement is UNAVAILABLE for this execution path."}
        )


def get_default_measurement_provider() -> MeasurementProvider:
    """
    Detect and return the best available physical measurement provider.
    1. If NVIDIA NVML / nvidia-smi is available on the machine -> NvidiaNvmlProvider.
    2. Otherwise -> UnavailableProvider.
    Never substitutes an estimate automatically.
    """
    nvidia = NvidiaNvmlProvider()
    if nvidia.is_available():
        return nvidia
    return UnavailableProvider()


def get_system_measurement_capabilities() -> MeasurementCapabilities:
    """
    Return physical measurement capabilities supported by the active host environment.
    """
    provider = get_default_measurement_provider()
    return provider.get_capabilities()

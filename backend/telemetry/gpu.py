import time
import threading
import ctypes
import os
import subprocess
from typing import Optional, List, Tuple
from .schemas import GpuTelemetry, ProvenanceStatus

class NVMLDevice:
    """Low-level interface to NVIDIA NVML via ctypes for high-speed, zero-dependency GPU sampling."""
    
    def __init__(self):
        self._nvml = None
        self._handle = None
        self._device_name: Optional[str] = None
        self.available: bool = False
        self._initialize()

    def _initialize(self):
        # Attempt to load NVML DLL / SO
        dll_names = ["nvml.dll"] if os.name == "nt" else ["libnvidia-ml.so.1", "libnvidia-ml.so"]
        for dll_name in dll_names:
            try:
                lib = ctypes.CDLL(dll_name)
                # Call nvmlInit_v2
                if lib.nvmlInit_v2() == 0:
                    self._nvml = lib
                    handle = ctypes.c_void_p()
                    # Query device 0
                    if self._nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(handle)) == 0:
                        self._handle = handle
                        name_buf = ctypes.create_string_buffer(64)
                        if self._nvml.nvmlDeviceGetName(self._handle, name_buf, 64) == 0:
                            self._device_name = name_buf.value.decode("utf-8", errors="replace")
                        self.available = True
                        break
            except Exception:
                continue

    def get_power_watts(self) -> Optional[float]:
        """Query current GPU power draw in Watts."""
        if not self.available or self._nvml is None or self._handle is None:
            return None
        try:
            power_mw = ctypes.c_uint()
            res = self._nvml.nvmlDeviceGetPowerUsage(self._handle, ctypes.byref(power_mw))
            if res == 0:
                return power_mw.value / 1000.0
        except Exception:
            return None
        return None

    def get_device_name(self) -> Optional[str]:
        return self._device_name

    def shutdown(self):
        """Release NVML resources."""
        if self._nvml is not None:
            try:
                self._nvml.nvmlShutdown()
            except Exception:
                pass
            self._nvml = None
            self.available = False


class FallbackNvidiaSmi:
    """Fallback power sampler using nvidia-smi CLI when direct NVML C-library binding is unavailable."""
    
    @staticmethod
    def is_available() -> bool:
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=1
            )
            return res.returncode == 0 and bool(res.stdout.strip())
        except Exception:
            return False

    @staticmethod
    def get_power_and_name() -> Tuple[Optional[float], Optional[str]]:
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=power.draw,name", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=1
            )
            if res.returncode == 0 and res.stdout.strip():
                parts = [p.strip() for p in res.stdout.strip().split(",")]
                power = float(parts[0]) if len(parts) > 0 else None
                name = parts[1] if len(parts) > 1 else None
                return power, name
        except Exception:
            return None, None
        return None, None


class GpuEnergyMonitor:
    """
    Context manager and active sampler for physical on-device GPU inference energy.
    Accurately measures GPU power draw during the inference window and computes:
      Energy (Joules) = Average Power (Watts) * Duration (seconds).

    IMPORTANT:
    This measurement captures GPU-only power. It is explicitly labeled as
    MEASURED GPU ENERGY and does NOT represent total system power (which includes
    CPU, DRAM, motherboard, storage, cooling fans, and PSU conversion losses).
    """

    def __init__(self, sample_interval_ms: float = 20.0):
        self.sample_interval = sample_interval_ms / 1000.0
        self._device = NVMLDevice()
        self._is_active: bool = False
        self._stop_event = threading.Event()
        self._sample_thread: Optional[threading.Thread] = None
        self._samples: List[float] = []
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
        self._duration_ms: Optional[float] = None
        self._device_name: Optional[str] = self._device.get_device_name()

    @property
    def is_hardware_available(self) -> bool:
        return self._device.available or FallbackNvidiaSmi.is_available()

    def _sample_loop(self):
        while not self._stop_event.is_set():
            p = self._device.get_power_watts()
            if p is not None:
                self._samples.append(p)
            self._stop_event.wait(self.sample_interval)

    def start(self):
        """Begin sampling GPU power during the inference window."""
        self._samples.clear()
        self._stop_event.clear()
        self._start_time = time.perf_counter()
        self._is_active = True

        if self._device.available:
            # High-frequency background sampling thread
            self._sample_thread = threading.Thread(target=self._sample_loop, daemon=True)
            self._sample_thread.start()
        elif FallbackNvidiaSmi.is_available():
            p, name = FallbackNvidiaSmi.get_power_and_name()
            if p is not None:
                self._samples.append(p)
            if name and not self._device_name:
                self._device_name = name

    def stop(self):
        """Stop sampling and finalize measurement metrics."""
        if not self._is_active:
            return
        self._end_time = time.perf_counter()
        self._is_active = False
        self._stop_event.set()

        if self._sample_thread is not None and self._sample_thread.is_alive():
            self._sample_thread.join(timeout=0.2)

        if self._start_time is not None and self._end_time is not None:
            self._duration_ms = (self._end_time - self._start_time) * 1000.0

        # One final sample if thread captured nothing or for single-point validation
        if self._device.available and not self._samples:
            p = self._device.get_power_watts()
            if p is not None:
                self._samples.append(p)

    def get_telemetry(self) -> GpuTelemetry:
        """Produce standardized GpuTelemetry model."""
        if not self.is_hardware_available or not self._samples:
            return GpuTelemetry(
                device_name=self._device_name,
                average_power_watts=None,
                peak_power_watts=None,
                energy_joules=None,
                sample_count=0,
                measurement_duration_ms=self._duration_ms,
                provenance=ProvenanceStatus.UNAVAILABLE,
                label="MEASURED GPU ENERGY (INFERENCE WINDOW ONLY - NOT TOTAL SYSTEM ENERGY)"
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
            label="MEASURED GPU ENERGY (INFERENCE WINDOW ONLY - NOT TOTAL SYSTEM ENERGY)"
        )

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

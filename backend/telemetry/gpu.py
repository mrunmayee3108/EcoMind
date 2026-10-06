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

    Refactored to delegate to generic NvidiaNvmlProvider for architecture consistency.
    """

    def __init__(self, sample_interval_ms: float = 20.0):
        from .measurement import NvidiaNvmlProvider
        self._provider = NvidiaNvmlProvider(sample_interval_ms=sample_interval_ms)

    @property
    def is_hardware_available(self) -> bool:
        return self._provider.is_available()

    def start(self):
        """Begin sampling GPU power during the inference window."""
        self._provider.start_measurement()

    def stop(self):
        """Stop sampling and finalize measurement metrics."""
        self._provider.stop_measurement()

    def get_telemetry(self) -> GpuTelemetry:
        """Produce standardized GpuTelemetry model."""
        return self._provider.to_gpu_telemetry()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


import unittest
import time
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from models.provider import ProviderResponse, TokenUsage
from telemetry.schemas import (
    ProvenanceStatus,
    MeasurementScope,
    MeasurementCapabilities,
    PhysicalMeasurement,
    TokenTelemetry,
    LatencyTelemetry,
    GpuTelemetry,
    EnvironmentalTelemetry,
    TelemetryRecord,
)
from telemetry.telemetry import TelemetryCollector, telemetry_collector
from telemetry.gpu import GpuEnergyMonitor, NVMLDevice, FallbackNvidiaSmi
from telemetry.measurement import (
    MeasurementProvider,
    NvidiaNvmlProvider,
    AndroidEnergyProvider,
    AppleEnergyProvider,
    UnavailableProvider,
    get_default_measurement_provider,
    get_system_measurement_capabilities,
)
from cache.semantic_cache import semantic_cache

class TestTelemetryUnit(unittest.TestCase):
    """Unit tests for the hardware-agnostic modular telemetry layer in Phase 5A."""

    def setUp(self):
        self.collector = TelemetryCollector()

    def test_token_telemetry_provider_reported(self):
        """1. Token telemetry: Real provider token counts marked as PROVIDER_REPORTED."""
        usage = TokenUsage(prompt_tokens=42, completion_tokens=18, total_tokens=60, is_estimated=False)
        record = self.collector.record_success(
            route="Small Model (Groq)",
            provider="groq",
            model="openai/gpt-oss-20b",
            execution_time_ms=125.4,
            inference_latency_ms=120.1,
            token_usage=usage
        )

        self.assertEqual(record.tokens.input_tokens, 42)
        self.assertEqual(record.tokens.output_tokens, 18)
        self.assertEqual(record.tokens.total_tokens, 60)
        self.assertEqual(record.tokens.provenance, ProvenanceStatus.PROVIDER_REPORTED)

    def test_token_telemetry_measured_for_tools_and_cache(self):
        """1. Token telemetry: Tools and cache hits have direct certainty of 0 tokens, marked as MEASURED."""
        # Tool execution
        tool_rec = self.collector.record_success(
            route="Calculator / Deterministic Tool",
            provider="deterministic",
            model="None",
            execution_time_ms=0.8,
            inference_latency_ms=0.5,
            token_usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        )
        self.assertEqual(tool_rec.tokens.input_tokens, 0)
        self.assertEqual(tool_rec.tokens.output_tokens, 0)
        self.assertEqual(tool_rec.tokens.total_tokens, 0)
        self.assertEqual(tool_rec.tokens.provenance, ProvenanceStatus.MEASURED)

        # Cache hit
        cache_rec = self.collector.record_success(
            route="semantic_cache",
            provider="cache",
            model=None,
            execution_time_ms=2.1,
            inference_latency_ms=0.0
        )
        self.assertEqual(cache_rec.tokens.total_tokens, 0)
        self.assertEqual(cache_rec.tokens.provenance, ProvenanceStatus.MEASURED)

    def test_latency_telemetry(self):
        """2. Latency telemetry: Capture inference and end-to-end latency marked as MEASURED."""
        record = self.collector.record_success(
            route="Medium Model (Groq)",
            provider="groq",
            model="qwen/qwen3.8-27b",
            execution_time_ms=245.678,
            inference_latency_ms=230.123
        )
        self.assertEqual(record.latency.execution_time_ms, 245.68)
        self.assertEqual(record.latency.inference_latency_ms, 230.12)
        self.assertEqual(record.latency.provenance, ProvenanceStatus.MEASURED)

    def test_provider_model_recording(self):
        """3. Provider and model recording: Faithfully record provider and model identifiers."""
        record = self.collector.record_success(
            route="Large Model (Google)",
            provider="google",
            model="gemini-2.5-pro",
            execution_time_ms=512.0,
            inference_latency_ms=500.0
        )
        self.assertEqual(record.provider, "google")
        self.assertEqual(record.model, "gemini-2.5-pro")
        self.assertEqual(record.route, "Large Model (Google)")

    def test_successful_request(self):
        """4. Successful request: Generates complete valid telemetry record."""
        record = self.collector.record_success(
            route="Small Model (Groq)",
            provider="groq",
            model="openai/gpt-oss-20b",
            execution_time_ms=88.4,
            inference_latency_ms=85.0,
            token_usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        )
        self.assertTrue(record.success)
        self.assertIsNone(record.error_message)
        self.assertTrue(record.request_id)
        self.assertTrue(record.timestamp)
        self.assertEqual(len(self.collector.get_recent(limit=10)), 1)

    def test_failed_request(self):
        """5. Failed request: Records failure state, error details, and UNAVAILABLE tokens/env."""
        record = self.collector.record_failure(
            route="Large Model",
            provider="groq",
            model="openai/gpt-oss-120b",
            execution_time_ms=45.2,
            error_message="Groq API key not found. Please set GROQ_API_KEY in backend/.env"
        )
        self.assertFalse(record.success)
        self.assertIn("GROQ_API_KEY", record.error_message)
        self.assertEqual(record.tokens.provenance, ProvenanceStatus.UNAVAILABLE)
        self.assertEqual(record.environment.provenance, ProvenanceStatus.UNAVAILABLE)
        self.assertEqual(record.latency.provenance, ProvenanceStatus.MEASURED)

    def test_unavailable_environmental_measurement(self):
        """6. Unavailable environmental measurement: Cloud requests have null energy/water/carbon with UNAVAILABLE status."""
        record = self.collector.record_success(
            route="Medium Model (Groq)",
            provider="groq",
            model="qwen/qwen3.8-27b",
            execution_time_ms=180.0,
            inference_latency_ms=175.0,
            token_usage=TokenUsage(prompt_tokens=30, completion_tokens=20, total_tokens=50)
        )
        # Strict zero-fabrication assertion
        self.assertIsNone(record.environment.energy_joules)
        self.assertIsNone(record.environment.water_liters)
        self.assertIsNone(record.environment.carbon_gco2e)
        self.assertEqual(record.environment.provenance, ProvenanceStatus.UNAVAILABLE)
        self.assertIsNone(record.environment.gpu_telemetry)
        self.assertIsNotNone(record.environment.measurement)
        self.assertEqual(record.environment.measurement.provenance, ProvenanceStatus.UNAVAILABLE)
        self.assertEqual(record.environment.measurement.scope, MeasurementScope.CLOUD_INFERENCE)

    def test_local_gpu_telemetry_legacy_monitor(self):
        """7. Local GPU telemetry: Backward-compatible GpuEnergyMonitor interface."""
        monitor = GpuEnergyMonitor(sample_interval_ms=10.0)
        if monitor.is_hardware_available:
            with monitor:
                time.sleep(0.05)  # Simulate 50ms inference window
            gpu_res = monitor.get_telemetry()

            self.assertIsNotNone(gpu_res.device_name)
            self.assertEqual(gpu_res.provenance, ProvenanceStatus.MEASURED)
            self.assertIsNotNone(gpu_res.average_power_watts)
            self.assertGreater(gpu_res.average_power_watts, 0.0)
            self.assertIsNotNone(gpu_res.energy_joules)
            self.assertGreater(gpu_res.energy_joules, 0.0)
            self.assertGreaterEqual(gpu_res.sample_count, 1)
            self.assertIn("MEASURED GPU ENERGY", gpu_res.label)
            self.assertIn("NOT TOTAL SYSTEM ENERGY", gpu_res.label)

            # Record attached to telemetry collector
            rec = self.collector.record_success(
                route="Small Model (Local)",
                provider="local",
                model="qwen2.5:0.5b",
                execution_time_ms=55.0,
                inference_latency_ms=50.0,
                gpu_telemetry=gpu_res
            )
            self.assertEqual(rec.environment.provenance, ProvenanceStatus.MEASURED)
            self.assertEqual(rec.environment.energy_joules, gpu_res.energy_joules)
            self.assertIsNone(rec.environment.water_liters)
            self.assertIsNone(rec.environment.carbon_gco2e)
        else:
            # When hardware is unavailable, monitor gracefully returns UNAVAILABLE
            gpu_res = monitor.get_telemetry()
            self.assertEqual(gpu_res.provenance, ProvenanceStatus.UNAVAILABLE)
            self.assertIsNone(gpu_res.energy_joules)

    def test_generic_measurement_interface_abstraction(self):
        """8. Generic measurement interface: Verify ABC enforcement and null UnavailableProvider behavior."""
        # MeasurementProvider cannot be instantiated directly without abstract methods
        with self.assertRaises(TypeError):
            MeasurementProvider()

        # UnavailableProvider adheres to interface and safely returns UNAVAILABLE
        unavail = UnavailableProvider()
        self.assertFalse(unavail.is_available())
        caps = unavail.get_capabilities()
        self.assertEqual(caps.gpu_energy, "unavailable")
        self.assertEqual(caps.system_energy, "unavailable")
        self.assertEqual(caps.device_energy, "unavailable")
        self.assertEqual(caps.provider_energy, "unavailable")

        meas = unavail.get_measurement()
        self.assertIsNone(meas.value)
        self.assertEqual(meas.unit, "J")
        self.assertEqual(meas.provenance, ProvenanceStatus.UNAVAILABLE)
        self.assertEqual(meas.scope, MeasurementScope.UNKNOWN)
        self.assertEqual(meas.status, "UNAVAILABLE")

    def test_nvidia_nvml_provider_when_available(self):
        """9. NVIDIA available: Directly verifies NvidiaNvmlProvider measures GPU energy with strict limitation labeling."""
        provider = NvidiaNvmlProvider(sample_interval_ms=10.0)
        if provider.is_available():
            with provider:
                time.sleep(0.05)  # 50ms window
            meas = provider.get_measurement()
            self.assertEqual(meas.provenance, ProvenanceStatus.MEASURED)
            self.assertEqual(meas.scope, MeasurementScope.GPU_INFERENCE_WINDOW)
            self.assertEqual(meas.source, "NvidiaNvmlProvider")
            self.assertEqual(meas.status, "AVAILABLE")
            self.assertIsNotNone(meas.value)
            self.assertGreater(meas.value, 0.0)
            self.assertIn("NOT TOTAL SYSTEM ENERGY", meas.details["label"])
            self.assertIn("MEASURED GPU ENERGY", meas.details["label"])

            # Capabilities confirm GPU energy is supported
            caps = provider.get_capabilities()
            self.assertEqual(caps.gpu_energy, "supported")
            self.assertEqual(caps.system_energy, "unavailable")
            self.assertEqual(caps.device_energy, "unavailable")
        else:
            # Dev environment without NVIDIA GPU
            meas = provider.get_measurement()
            self.assertEqual(meas.provenance, ProvenanceStatus.UNAVAILABLE)
            self.assertIsNone(meas.value)

    def test_nvidia_nvml_provider_when_unavailable_does_not_fail(self):
        """10. NVIDIA unavailable: Gracefully returns UNAVAILABLE without failing or raising exceptions."""
        with patch.object(NVMLDevice, "_initialize", lambda self: None), \
             patch.object(FallbackNvidiaSmi, "is_available", return_value=False):
            mock_provider = NvidiaNvmlProvider()
            mock_provider._device.available = False

            self.assertFalse(mock_provider.is_available())
            caps = mock_provider.get_capabilities()
            self.assertEqual(caps.gpu_energy, "unavailable")

            # Executing sampling window does not fail
            with mock_provider:
                time.sleep(0.01)

            meas = mock_provider.get_measurement()
            self.assertEqual(meas.provenance, ProvenanceStatus.UNAVAILABLE)
            self.assertIsNone(meas.value)
            self.assertEqual(meas.status, "UNAVAILABLE")
            self.assertEqual(meas.scope, MeasurementScope.GPU_INFERENCE_WINDOW)

    def test_android_energy_provider_architecture(self):
        """11. Android client provider: Interface architecture for native clients; never fabricates values."""
        # Case A: Default without client telemetry transmission -> strictly UNAVAILABLE
        android = AndroidEnergyProvider()
        self.assertFalse(android.is_available())
        caps = android.get_capabilities()
        self.assertEqual(caps.device_energy, "unavailable")

        meas = android.get_measurement()
        self.assertIsNone(meas.value)
        self.assertEqual(meas.provenance, ProvenanceStatus.UNAVAILABLE)
        self.assertEqual(meas.scope, MeasurementScope.DEVICE)
        self.assertEqual(meas.status, "UNAVAILABLE")
        self.assertIn("future work", meas.details["note"].lower())

        # Case B: Ingesting authentic native client telemetry payload
        client_payload = {
            "energy_joules": 0.354,
            "unit": "J",
            "provenance": "MEASURED",
            "device_model": "Google Pixel 8",
            "sample_rate_hz": 100
        }
        ingested = android.ingest_client_telemetry(client_payload)
        self.assertTrue(android.is_available())
        self.assertEqual(ingested.provenance, ProvenanceStatus.MEASURED)
        self.assertEqual(ingested.value, 0.354)
        self.assertEqual(ingested.scope, MeasurementScope.DEVICE)
        self.assertEqual(ingested.device_platform, "Google Pixel 8")
        self.assertEqual(ingested.status, "AVAILABLE")

    def test_apple_energy_provider_architecture(self):
        """12. Apple client provider: Interface architecture for macOS / iOS client telemetry; never fabricates values."""
        # Case A: Default without client transmission -> strictly UNAVAILABLE
        apple = AppleEnergyProvider()
        self.assertFalse(apple.is_available())
        caps = apple.get_capabilities()
        self.assertEqual(caps.device_energy, "unavailable")

        meas = apple.get_measurement()
        self.assertIsNone(meas.value)
        self.assertEqual(meas.provenance, ProvenanceStatus.UNAVAILABLE)
        self.assertEqual(meas.scope, MeasurementScope.DEVICE)
        self.assertEqual(meas.status, "UNAVAILABLE")

        # Case B: Ingesting authentic native Apple client telemetry
        client_payload = {
            "energy_joules": 0.812,
            "unit": "J",
            "provenance": "MEASURED",
            "device_model": "MacBook Pro M3 Max"
        }
        ingested = apple.ingest_client_telemetry(client_payload)
        self.assertTrue(apple.is_available())
        self.assertEqual(ingested.provenance, ProvenanceStatus.MEASURED)
        self.assertEqual(ingested.value, 0.812)
        self.assertEqual(ingested.scope, MeasurementScope.DEVICE)
        self.assertEqual(ingested.device_platform, "MacBook Pro M3 Max")

    def test_scope_correctness_and_non_conflation(self):
        """13. Scope correctness: Scopes explicitly distinguish what was measured; never conflated as generic 'energy'."""
        self.assertEqual(MeasurementScope.GPU_INFERENCE_WINDOW.value, "GPU_INFERENCE_WINDOW")
        self.assertEqual(MeasurementScope.DEVICE.value, "DEVICE")
        self.assertEqual(MeasurementScope.SYSTEM.value, "SYSTEM")
        self.assertEqual(MeasurementScope.CLOUD_INFERENCE.value, "CLOUD_INFERENCE")
        self.assertEqual(MeasurementScope.UNKNOWN.value, "UNKNOWN")

        # Record with device scope
        dev_meas = PhysicalMeasurement(
            value=0.5,
            unit="J",
            provenance=ProvenanceStatus.MEASURED,
            source="AndroidEnergyProvider",
            scope=MeasurementScope.DEVICE,
            status="AVAILABLE"
        )
        rec_dev = self.collector.record_success(
            route="Small Model (Mobile Client)",
            provider="local_client",
            execution_time_ms=80.0,
            physical_measurement=dev_meas
        )
        self.assertEqual(rec_dev.environment.measurement.scope, MeasurementScope.DEVICE)
        self.assertEqual(rec_dev.environment.measurement_capabilities.device_energy, "supported")
        self.assertEqual(rec_dev.environment.measurement_capabilities.gpu_energy, "unavailable")

    def test_provenance_correctness(self):
        """14. Provenance correctness: Strictly distinguishes MEASURED, PROVIDER_REPORTED, and UNAVAILABLE without ESTIMATED."""
        # Confirm valid statuses
        statuses = [p.value for p in ProvenanceStatus]
        self.assertIn("MEASURED", statuses)
        self.assertIn("PROVIDER_REPORTED", statuses)
        self.assertIn("UNAVAILABLE", statuses)
        self.assertNotIn("ESTIMATED", statuses, "ESTIMATED must NOT exist in Phase 5A")

    def test_cloud_provider_physical_energy_remains_unavailable(self):
        """15. Cloud provider integrity: Groq and Google calls leave physical energy strictly UNAVAILABLE."""
        for provider_name in ["groq", "google"]:
            rec = self.collector.record_success(
                route=f"Large Model ({provider_name})",
                provider=provider_name,
                model="test-model",
                execution_time_ms=300.0,
                token_usage=TokenUsage(prompt_tokens=50, completion_tokens=50, total_tokens=100)
            )
            self.assertIsNone(rec.environment.energy_joules)
            self.assertEqual(rec.environment.provenance, ProvenanceStatus.UNAVAILABLE)
            self.assertEqual(rec.environment.measurement.provenance, ProvenanceStatus.UNAVAILABLE)
            self.assertEqual(rec.environment.measurement.scope, MeasurementScope.CLOUD_INFERENCE)
            self.assertEqual(rec.tokens.provenance, ProvenanceStatus.PROVIDER_REPORTED)
            self.assertEqual(rec.tokens.total_tokens, 100)


class TestTelemetryAPIIntegration(unittest.TestCase):
    """Integration tests verifying telemetry collection via FastAPI /chat and /telemetry endpoints."""

    def setUp(self):
        self.client = TestClient(app)
        telemetry_collector.clear()
        semantic_cache.clear()

    def test_chat_tool_telemetry_integration(self):
        """Chat with deterministic tool collects telemetry with MEASURED 0 tokens."""
        res = self.client.post("/chat", json={"query": "what is 50 + 25?"})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("telemetry", data)
        telem = data["telemetry"]
        self.assertIsNotNone(telem)
        self.assertTrue(telem["success"])
        self.assertEqual(telem["route"], "Calculator / Deterministic Tool")
        self.assertEqual(telem["provider"], "deterministic")
        self.assertEqual(telem["tokens"]["input_tokens"], 0)
        self.assertEqual(telem["tokens"]["output_tokens"], 0)
        self.assertEqual(telem["tokens"]["total_tokens"], 0)
        self.assertEqual(telem["tokens"]["provenance"], "MEASURED")
        self.assertEqual(telem["latency"]["provenance"], "MEASURED")
        self.assertEqual(telem["environment"]["provenance"], "UNAVAILABLE")

    def test_chat_failure_telemetry_integration(self):
        """Failed route preference records failure telemetry."""
        res = self.client.post("/chat", json={"query": "test query", "preferred_route": "invalid_tier"})
        self.assertEqual(res.status_code, 400)

        # Check telemetry collector recorded the failure
        recent = telemetry_collector.get_recent(limit=5)
        self.assertGreaterEqual(len(recent), 1)
        failed_rec = recent[0]
        self.assertFalse(failed_rec.success)
        self.assertIn("invalid_tier", failed_rec.error_message)

    def test_telemetry_capabilities_endpoint(self):
        """Verify GET /telemetry/capabilities returns structured capability statuses."""
        res = self.client.get("/telemetry/capabilities")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("gpu_energy", data)
        self.assertIn("system_energy", data)
        self.assertIn("device_energy", data)
        self.assertIn("provider_energy", data)
        self.assertIn(data["gpu_energy"], ["supported", "unavailable"])
        self.assertIn(data["system_energy"], ["supported", "unavailable"])
        self.assertIn(data["device_energy"], ["supported", "unavailable"])
        self.assertIn(data["provider_energy"], ["supported", "unavailable"])

    def test_telemetry_endpoints(self):
        """Verify /telemetry/recent, /telemetry/summary, and /telemetry/clear endpoints."""
        # 1. Trigger an operation
        self.client.post("/chat", json={"query": "what is 10 * 10?"})

        # 2. GET /telemetry/recent
        recent_res = self.client.get("/telemetry/recent")
        self.assertEqual(recent_res.status_code, 200)
        recent_data = recent_res.json()
        self.assertIsInstance(recent_data, list)
        self.assertGreaterEqual(len(recent_data), 1)

        # 3. GET /telemetry/summary
        summary_res = self.client.get("/telemetry/summary")
        self.assertEqual(summary_res.status_code, 200)
        summary_data = summary_res.json()
        self.assertGreaterEqual(summary_data["total_requests"], 1)
        self.assertGreaterEqual(summary_data["successful_requests"], 1)
        self.assertIn("measurement_capabilities", summary_data)

        # 4. POST /telemetry/clear
        clear_res = self.client.post("/telemetry/clear")
        self.assertEqual(clear_res.status_code, 200)

        # Verify cleared
        recent_after = self.client.get("/telemetry/recent").json()
        self.assertEqual(len(recent_after), 0)

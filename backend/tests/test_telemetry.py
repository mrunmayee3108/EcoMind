import unittest
import time
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from models.provider import ProviderResponse, TokenUsage
from telemetry.schemas import (
    ProvenanceStatus,
    TokenTelemetry,
    LatencyTelemetry,
    GpuTelemetry,
    EnvironmentalTelemetry,
    TelemetryRecord,
)
from telemetry.telemetry import TelemetryCollector, telemetry_collector
from telemetry.gpu import GpuEnergyMonitor, NVMLDevice, FallbackNvidiaSmi
from cache.semantic_cache import semantic_cache

class TestTelemetryUnit(unittest.TestCase):
    """Unit tests for the modular telemetry layer in Phase 5A."""

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

    def test_local_gpu_telemetry(self):
        """7. Local GPU telemetry: Direct physical measurement on supported hardware."""
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

        # 4. POST /telemetry/clear
        clear_res = self.client.post("/telemetry/clear")
        self.assertEqual(clear_res.status_code, 200)

        # Verify cleared
        recent_after = self.client.get("/telemetry/recent").json()
        self.assertEqual(len(recent_after), 0)

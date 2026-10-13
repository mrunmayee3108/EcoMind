import unittest
from unittest.mock import patch

from config.settings import settings
from telemetry.schemas import (
    ProvenanceStatus,
    MeasurementScope,
    PhysicalMeasurement,
    TokenTelemetry,
    LatencyTelemetry,
    GpuTelemetry,
    EnvironmentalTelemetry,
    AvoidanceTelemetry,
    TelemetryRecord,
    MetricSavings,
    SavingsComparison,
)
from telemetry.telemetry import TelemetryCollector
from telemetry.savings import calculate_savings
from models.provider import TokenUsage

class TestEnvironmentalAccountingPhase5B(unittest.TestCase):
    """
    Verification tests for Phase 5B Environmental Accounting Methodology.
    Ensures absolute zero fabrication, authentic provenance tracking,
    strict GPU measurement scoping, conditional carbon calculation,
    and enforcement of the Pair-Wise Non-Zero Savings Rule.
    """

    def setUp(self):
        self.collector = TelemetryCollector()

    def test_cloud_environmental_metrics_strictly_unavailable(self):
        """1. Preserve UNAVAILABLE for unsupported cloud environmental metrics (Groq, Google)."""
        for provider_name in ["groq", "google"]:
            rec = self.collector.record_success(
                route=f"Large Model ({provider_name.capitalize()})",
                provider=provider_name,
                model="test-checkpoint-1",
                execution_time_ms=250.0,
                inference_latency_ms=240.0,
                token_usage=TokenUsage(prompt_tokens=40, completion_tokens=60, total_tokens=100)
            )

            # Environmental metrics must be None with UNAVAILABLE provenance
            self.assertIsNone(rec.environment.energy_joules)
            self.assertIsNone(rec.environment.water_liters)
            self.assertIsNone(rec.environment.carbon_gco2e)
            self.assertEqual(rec.environment.provenance, ProvenanceStatus.UNAVAILABLE)
            self.assertEqual(rec.environment.energy_provenance, ProvenanceStatus.UNAVAILABLE)
            self.assertEqual(rec.environment.water_provenance, ProvenanceStatus.UNAVAILABLE)
            self.assertEqual(rec.environment.carbon_provenance, ProvenanceStatus.UNAVAILABLE)
            self.assertEqual(rec.environment.measurement.scope, MeasurementScope.CLOUD_INFERENCE)

            # Token metadata is authentically PROVIDER_REPORTED
            self.assertEqual(rec.tokens.provenance, ProvenanceStatus.PROVIDER_REPORTED)
            self.assertEqual(rec.tokens.total_tokens, 100)

            # Latency is MEASURED via high-res timer
            self.assertEqual(rec.latency.provenance, ProvenanceStatus.MEASURED)

    def test_local_gpu_energy_strictly_scoped_to_inference_window(self):
        """2. Keep local NVIDIA GPU energy strictly scoped to GPU inference window, not total system energy."""
        gpu_meas = PhysicalMeasurement(
            value=45.2,
            unit="J",
            provenance=ProvenanceStatus.MEASURED,
            source="NvidiaNvmlProvider",
            scope=MeasurementScope.GPU_INFERENCE_WINDOW,
            device_platform="NVIDIA GeForce RTX 4070 Laptop GPU",
            status="AVAILABLE",
            details={
                "average_power_watts": 45.2,
                "peak_power_watts": 52.0,
                "sample_count": 5,
                "measurement_duration_ms": 1000.0,
                "label": "MEASURED GPU ENERGY (INFERENCE WINDOW ONLY - NOT TOTAL SYSTEM ENERGY)"
            }
        )

        rec = self.collector.record_success(
            route="Small Model (Ollama Local)",
            provider="local",
            model="llama3.1:8b",
            execution_time_ms=1050.0,
            inference_latency_ms=1000.0,
            physical_measurement=gpu_meas
        )

        self.assertEqual(rec.environment.energy_joules, 45.2)
        self.assertEqual(rec.environment.provenance, ProvenanceStatus.MEASURED)
        self.assertEqual(rec.environment.energy_provenance, ProvenanceStatus.MEASURED)
        self.assertEqual(rec.environment.measurement.scope, MeasurementScope.GPU_INFERENCE_WINDOW)
        self.assertIn("INFERENCE WINDOW ONLY", rec.environment.gpu_telemetry.label)
        self.assertIn("NOT TOTAL SYSTEM ENERGY", rec.environment.gpu_telemetry.label)

    def test_local_gpu_carbon_unavailable_when_grid_factor_unconfigured(self):
        """3A. Local GPU-board operational carbon is UNAVAILABLE when grid intensity factor is None or unconfigured."""
        with patch.object(settings, "LOCAL_GRID_INTENSITY_GCO2E_PER_KWH", None):
            gpu_meas = PhysicalMeasurement(
                value=360.0,
                unit="J",
                provenance=ProvenanceStatus.MEASURED,
                source="NvidiaNvmlProvider",
                scope=MeasurementScope.GPU_INFERENCE_WINDOW,
                status="AVAILABLE"
            )

            rec = self.collector.record_success(
                route="Small Model (Ollama Local)",
                provider="local",
                execution_time_ms=500.0,
                physical_measurement=gpu_meas
            )

            self.assertEqual(rec.environment.energy_joules, 360.0)
            self.assertEqual(rec.environment.energy_provenance, ProvenanceStatus.MEASURED)
            self.assertIsNone(rec.environment.carbon_gco2e)
            self.assertIsNone(rec.environment.carbon_scope)
            self.assertEqual(rec.environment.carbon_provenance, ProvenanceStatus.UNAVAILABLE)
            self.assertIn("Operational carbon is UNAVAILABLE", rec.environment.note)

    def test_local_gpu_carbon_calculated_when_grid_factor_configured(self):
        """3B. Calculate local GPU-board operational carbon when valid grid-emissions factor is configured."""
        # 360 Joules = 360 / 3,600,000 kWh = 0.0001 kWh
        # At 370.0 gCO2e/kWh: 0.0001 * 370.0 = 0.037 gCO2e
        with patch.object(settings, "LOCAL_GRID_INTENSITY_GCO2E_PER_KWH", 370.0):
            gpu_meas = PhysicalMeasurement(
                value=360.0,
                unit="J",
                provenance=ProvenanceStatus.MEASURED,
                source="NvidiaNvmlProvider",
                scope=MeasurementScope.GPU_INFERENCE_WINDOW,
                status="AVAILABLE"
            )

            rec = self.collector.record_success(
                route="Small Model (Ollama Local)",
                provider="local",
                execution_time_ms=500.0,
                physical_measurement=gpu_meas
            )

            self.assertEqual(rec.environment.energy_joules, 360.0)
            self.assertEqual(rec.environment.energy_provenance, ProvenanceStatus.MEASURED)
            self.assertEqual(rec.environment.carbon_gco2e, 0.037)
            self.assertEqual(rec.environment.carbon_scope, MeasurementScope.GPU_BOARD_OPERATIONAL_CARBON)
            self.assertEqual(rec.environment.carbon_provenance, ProvenanceStatus.ESTIMATED)
            self.assertEqual(rec.environment.grid_intensity_gco2e_per_kwh, 370.0)
            self.assertIn("Strictly scoped to GPU board", rec.environment.note)

    def test_local_gpu_carbon_invalid_grid_factor_remains_unavailable(self):
        """3C. Negative or zero grid-emissions factors do not fabricate carbon; remain UNAVAILABLE."""
        for invalid_factor in [0.0, -100.0]:
            with patch.object(settings, "LOCAL_GRID_INTENSITY_GCO2E_PER_KWH", invalid_factor):
                gpu_meas = PhysicalMeasurement(
                    value=100.0,
                    unit="J",
                    provenance=ProvenanceStatus.MEASURED,
                    source="NvidiaNvmlProvider",
                    scope=MeasurementScope.GPU_INFERENCE_WINDOW,
                    status="AVAILABLE"
                )

                rec = self.collector.record_success(
                    route="Small Model (Ollama Local)",
                    provider="local",
                    execution_time_ms=200.0,
                    physical_measurement=gpu_meas
                )

                self.assertIsNone(rec.environment.carbon_gco2e)
                self.assertEqual(rec.environment.carbon_provenance, ProvenanceStatus.UNAVAILABLE)

    def test_tool_and_cache_avoidance_facts_and_zero_tokens(self):
        """4. Record tool/cache model-call and token avoidance accurately, relative to explicit baseline."""
        # A: Deterministic Tool
        tool_rec = self.collector.record_success(
            route="Calculator / Deterministic Tool",
            provider="deterministic",
            model="None",
            execution_time_ms=1.2,
            inference_latency_ms=0.8,
            token_usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        )

        self.assertEqual(tool_rec.tokens.input_tokens, 0)
        self.assertEqual(tool_rec.tokens.output_tokens, 0)
        self.assertEqual(tool_rec.tokens.total_tokens, 0)
        self.assertEqual(tool_rec.tokens.provenance, ProvenanceStatus.MEASURED)
        self.assertEqual(tool_rec.latency.provenance, ProvenanceStatus.MEASURED)
        self.assertIsNotNone(tool_rec.avoidance)
        self.assertEqual(tool_rec.avoidance.model_calls_avoided, 1)
        self.assertEqual(tool_rec.avoidance.baseline_route, "large_model")
        # Physical energy remains UNAVAILABLE (not fabricated as 0.0)
        self.assertIsNone(tool_rec.environment.energy_joules)
        self.assertEqual(tool_rec.environment.provenance, ProvenanceStatus.UNAVAILABLE)

        # B: Semantic Cache Hit
        cache_rec = self.collector.record_success(
            route="semantic_cache",
            provider="cache",
            model=None,
            execution_time_ms=4.5,
            inference_latency_ms=0.0,
            token_usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        )

        self.assertEqual(cache_rec.tokens.total_tokens, 0)
        self.assertEqual(cache_rec.tokens.provenance, ProvenanceStatus.MEASURED)
        self.assertIsNotNone(cache_rec.avoidance)
        self.assertEqual(cache_rec.avoidance.model_calls_avoided, 1)
        self.assertIsNone(cache_rec.environment.energy_joules)
        self.assertEqual(cache_rec.environment.provenance, ProvenanceStatus.UNAVAILABLE)

    def test_pairwise_savings_integrity_rule_unmeasured_never_zero(self):
        """5A. Pair-Wise Non-Zero Rule: Unavailable metrics are NEVER treated as zero or subtracted to fabricate savings."""
        # Selected route: Deterministic tool (0 tokens, energy UNAVAILABLE)
        tool_rec = self.collector.record_success(
            route="Calculator / Deterministic Tool",
            provider="deterministic",
            execution_time_ms=2.0,
            token_usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        )

        # Baseline route: Large Model (Groq) (150 tokens, energy UNAVAILABLE)
        baseline_rec = self.collector.record_success(
            route="Large Model (Groq)",
            provider="groq",
            model="openai/gpt-oss-120b",
            execution_time_ms=500.0,
            token_usage=TokenUsage(prompt_tokens=50, completion_tokens=100, total_tokens=150)
        )

        savings = calculate_savings(selected=tool_rec, baseline=baseline_rec)

        # Energy savings must be UNAVAILABLE (never 0.0 J or baseline - 0)
        self.assertIsNone(savings.energy_savings.savings_value)
        self.assertEqual(savings.energy_savings.provenance, ProvenanceStatus.UNAVAILABLE)
        self.assertIn("at least one route lacks physical energy measurement", savings.energy_savings.note)

        # Water savings must be UNAVAILABLE
        self.assertIsNone(savings.water_savings.savings_value)
        self.assertEqual(savings.water_savings.provenance, ProvenanceStatus.UNAVAILABLE)

        # Carbon savings must be UNAVAILABLE
        self.assertIsNone(savings.carbon_savings.savings_value)
        self.assertEqual(savings.carbon_savings.provenance, ProvenanceStatus.UNAVAILABLE)

        # Authentic operational proxies are reported
        self.assertEqual(savings.model_calls_avoided, 1)
        self.assertEqual(savings.tokens_saved, 150)
        self.assertEqual(savings.tokens_provenance, ProvenanceStatus.MEASURED)
        self.assertEqual(savings.latency_delta_ms, 498.0)
        self.assertIn("Physical environmental savings are UNAVAILABLE", savings.notice)

    def test_pairwise_savings_asymmetric_measurement_remains_unavailable(self):
        """5B. If selected has measured energy but baseline is cloud/UNAVAILABLE, savings is strictly UNAVAILABLE."""
        # Selected route: Local GPU measured at 50.0 J
        gpu_meas = PhysicalMeasurement(
            value=50.0,
            unit="J",
            provenance=ProvenanceStatus.MEASURED,
            source="NvidiaNvmlProvider",
            scope=MeasurementScope.GPU_INFERENCE_WINDOW,
            status="AVAILABLE"
        )
        local_rec = self.collector.record_success(
            route="Small Model (Ollama Local)",
            provider="local",
            execution_time_ms=300.0,
            physical_measurement=gpu_meas
        )

        # Baseline route: Cloud API with UNAVAILABLE energy
        cloud_rec = self.collector.record_success(
            route="Large Model (Groq)",
            provider="groq",
            execution_time_ms=600.0,
            token_usage=TokenUsage(prompt_tokens=50, completion_tokens=100, total_tokens=150)
        )

        savings = calculate_savings(selected=local_rec, baseline=cloud_rec)

        # Must NOT subtract 50 - None or treat None as 0 (which would falsely report -50 J negative savings)
        self.assertIsNone(savings.energy_savings.savings_value)
        self.assertEqual(savings.energy_savings.provenance, ProvenanceStatus.UNAVAILABLE)

    def test_pairwise_savings_both_measured_reports_genuine_savings(self):
        """5C. When both routes are measured with matching scope, authentic savings are computed."""
        with patch.object(settings, "LOCAL_GRID_INTENSITY_GCO2E_PER_KWH", 370.0):
            # Baseline: Large model on local GPU (180 J)
            meas_large = PhysicalMeasurement(
                value=180.0,
                unit="J",
                provenance=ProvenanceStatus.MEASURED,
                source="NvidiaNvmlProvider",
                scope=MeasurementScope.GPU_INFERENCE_WINDOW,
                status="AVAILABLE"
            )
            base_rec = self.collector.record_success(
                route="Large Model (Local GPU)",
                provider="local",
                execution_time_ms=800.0,
                token_usage=TokenUsage(prompt_tokens=50, completion_tokens=150, total_tokens=200),
                physical_measurement=meas_large
            )

            # Selected: Small model on local GPU (45 J)
            meas_small = PhysicalMeasurement(
                value=45.0,
                unit="J",
                provenance=ProvenanceStatus.MEASURED,
                source="NvidiaNvmlProvider",
                scope=MeasurementScope.GPU_INFERENCE_WINDOW,
                status="AVAILABLE"
            )
            sel_rec = self.collector.record_success(
                route="Small Model (Local GPU)",
                provider="local",
                execution_time_ms=200.0,
                token_usage=TokenUsage(prompt_tokens=50, completion_tokens=50, total_tokens=100),
                physical_measurement=meas_small
            )

            savings = calculate_savings(selected=sel_rec, baseline=base_rec)

            # Energy savings
            self.assertEqual(savings.energy_savings.baseline_value, 180.0)
            self.assertEqual(savings.energy_savings.selected_value, 45.0)
            self.assertEqual(savings.energy_savings.savings_value, 135.0)
            self.assertEqual(savings.energy_savings.savings_pct, 75.0)
            self.assertEqual(savings.energy_savings.provenance, ProvenanceStatus.MEASURED)
            self.assertEqual(savings.energy_savings.scope, MeasurementScope.GPU_INFERENCE_WINDOW)

            # Carbon savings:
            # Baseline carbon = (180 / 3,600,000) * 370.0 = 0.0185 gCO2e
            # Selected carbon = (45 / 3,600,000) * 370.0 = 0.004625 gCO2e
            # Delta = 0.0185 - 0.004625 = 0.013875 gCO2e
            self.assertAlmostEqual(savings.carbon_savings.savings_value, 0.013875, places=5)
            self.assertEqual(savings.carbon_savings.provenance, ProvenanceStatus.ESTIMATED)
            self.assertEqual(savings.carbon_savings.scope, MeasurementScope.GPU_BOARD_OPERATIONAL_CARBON)

    def test_pairwise_savings_quality_gate(self):
        """5D. Quality gate flag is reflected in the integrity notice when threshold is not met."""
        tool_rec = self.collector.record_success(
            route="Calculator / Deterministic Tool",
            provider="deterministic",
            execution_time_ms=2.0
        )
        base_rec = self.collector.record_success(
            route="Large Model (Groq)",
            provider="groq",
            execution_time_ms=500.0
        )

        savings = calculate_savings(selected=tool_rec, baseline=base_rec, quality_threshold_met=False)
        self.assertFalse(savings.quality_threshold_met)
        self.assertIn("Quality threshold not met", savings.notice)
        self.assertIn("quality degradation penalty", savings.notice)


from fastapi.testclient import TestClient
from main import app
from telemetry.telemetry import telemetry_collector

class TestSavingsAPIIntegration(unittest.TestCase):
    """Integration test for POST /telemetry/savings/compare endpoint."""

    def setUp(self):
        self.client = TestClient(app)
        telemetry_collector.clear()

    def test_compare_endpoint_pairwise_integrity(self):
        # 1. Execute a tool request
        res1 = self.client.post("/chat", json={"query": "100 * 5"})
        self.assertEqual(res1.status_code, 200)
        sel_rec = res1.json()["telemetry"]

        # 2. Add a baseline record directly to collector
        base_rec = telemetry_collector.record_success(
            route="Large Model (Groq)",
            provider="groq",
            model="openai/gpt-oss-120b",
            execution_time_ms=450.0,
            token_usage=TokenUsage(prompt_tokens=20, completion_tokens=80, total_tokens=100)
        )

        # 3. Call /telemetry/savings/compare
        comp_res = self.client.post(
            "/telemetry/savings/compare",
            json={
                "selected_request_id": sel_rec["request_id"],
                "baseline_request_id": base_rec.request_id,
                "quality_threshold_met": True
            }
        )
        self.assertEqual(comp_res.status_code, 200)
        data = comp_res.json()

        self.assertEqual(data["model_calls_avoided"], 1)
        self.assertEqual(data["tokens_saved"], 100)
        self.assertEqual(data["energy_savings"]["provenance"], "UNAVAILABLE")
        self.assertIsNone(data["energy_savings"]["savings_value"])
        self.assertEqual(data["water_savings"]["provenance"], "UNAVAILABLE")
        self.assertEqual(data["carbon_savings"]["provenance"], "UNAVAILABLE")
        self.assertIn("Physical environmental savings are UNAVAILABLE", data["notice"])

    def test_compare_endpoint_404_for_missing_ids(self):
        res = self.client.post(
            "/telemetry/savings/compare",
            json={
                "selected_request_id": "nonexistent-id-1",
                "baseline_request_id": "nonexistent-id-2",
                "quality_threshold_met": True
            }
        )
        self.assertEqual(res.status_code, 404)

if __name__ == "__main__":
    unittest.main()


import unittest
import uuid
from typing import Dict, Any
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from main import app
from cache.semantic_cache import semantic_cache
from telemetry.telemetry import telemetry_collector
from telemetry.schemas import (
    ProvenanceStatus,
    MeasurementScope,
    TokenTelemetry,
    LatencyTelemetry,
    EnvironmentalTelemetry,
    GpuTelemetry,
    AvoidanceTelemetry,
    RoutingDecision,
    CandidateScore,
    TelemetryRecord
)
from receipt.schemas import (
    ExecutionPath,
    EcoReceipt,
    CostMetric,
    EnergyMetric,
    CarbonMetric,
    WaterMetric
)
from receipt.receipt_generator import generate_eco_receipt

class TestEcoReceipt(unittest.TestCase):
    def setUp(self):
        semantic_cache.clear()
        telemetry_collector.clear()
        self.client = TestClient(app)

    def tearDown(self):
        semantic_cache.clear()
        telemetry_collector.clear()

    def test_receipt_creation_for_deterministic_tool(self):
        """Receipt for deterministic tool execution verifies 0 tokens, $0.00 cost, and tool avoidance."""
        rec = telemetry_collector.record_success(
            route="Calculator / Deterministic Tool",
            provider="deterministic",
            model="None",
            execution_time_ms=0.45,
            inference_latency_ms=0.12,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "is_estimated": False}
        )
        receipt = generate_eco_receipt(rec, query="calculate 45 * 20")

        self.assertEqual(receipt.status, "SUCCESS")
        self.assertEqual(receipt.execution_path, ExecutionPath.DETERMINISTIC_TOOL)
        self.assertEqual(receipt.route, "Calculator / Deterministic Tool")
        self.assertEqual(receipt.provider, "deterministic")
        self.assertEqual(receipt.tokens.total_tokens, 0)
        self.assertEqual(receipt.tokens.provenance, ProvenanceStatus.MEASURED)
        self.assertEqual(receipt.cost.value_usd, 0.0)
        self.assertEqual(receipt.cost.provenance, ProvenanceStatus.MEASURED)
        self.assertEqual(receipt.latency_provenance, ProvenanceStatus.MEASURED)
        self.assertEqual(receipt.avoidance.model_calls_avoided, 1)
        self.assertFalse(receipt.avoidance.defensible_savings_reported)
        self.assertIn("0 model tokens", receipt.explainability.selection_summary)

    def test_receipt_creation_for_semantic_cache_hit(self):
        """Receipt for semantic cache hit verifies cache reuse, 0 model calls, and operational avoidance."""
        rec = telemetry_collector.record_success(
            route="semantic_cache",
            provider="cache",
            model=None,
            execution_time_ms=1.2,
            inference_latency_ms=0.0,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "is_estimated": False}
        )
        receipt = generate_eco_receipt(rec, query="What is photosythesis?")

        self.assertEqual(receipt.status, "SUCCESS")
        self.assertEqual(receipt.execution_path, ExecutionPath.SEMANTIC_CACHE)
        self.assertEqual(receipt.tokens.total_tokens, 0)
        self.assertEqual(receipt.tokens.provenance, ProvenanceStatus.MEASURED)
        self.assertEqual(receipt.cost.value_usd, 0.0)
        self.assertEqual(receipt.cost.provenance, ProvenanceStatus.MEASURED)
        self.assertEqual(receipt.avoidance.model_calls_avoided, 1)
        self.assertIn("precision-first semantic cache", receipt.explainability.selection_summary)

    def test_receipt_creation_for_model_inference_with_pricing(self):
        """Receipt for model inference computes catalog cost and provider-reported tokens."""
        rec = telemetry_collector.record_success(
            route="Small Model (Groq)",
            provider="groq",
            model="llama-3.1-8b-instant",
            execution_time_ms=145.0,
            inference_latency_ms=130.0,
            token_usage={"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75, "is_estimated": False}
        )
        receipt = generate_eco_receipt(rec, query="Explain gradient descent briefly")

        self.assertEqual(receipt.status, "SUCCESS")
        self.assertEqual(receipt.execution_path, ExecutionPath.MODEL_INFERENCE)
        self.assertEqual(receipt.model, "llama-3.1-8b-instant")
        self.assertEqual(receipt.tokens.total_tokens, 75)
        self.assertEqual(receipt.tokens.provenance, ProvenanceStatus.PROVIDER_REPORTED)
        
        # Llama 3.1 8B instant pricing: 0.05/1M in, 0.08/1M out
        # (50/1e6)*0.05 + (25/1e6)*0.08 = 0.0000025 + 0.000002 = 0.0000045
        self.assertIsNotNone(receipt.cost.value_usd)
        self.assertAlmostEqual(receipt.cost.value_usd, 0.0000045, places=7)
        self.assertEqual(receipt.cost.provenance, ProvenanceStatus.ESTIMATED)

    def test_receipt_optimizer_metadata_mapping(self):
        """Receipt accurately maps Phase 6 multi-objective routing optimizer decision metadata."""
        decision = RoutingDecision(
            selected_route="Medium Model (Groq)",
            selected_tier="medium",
            decision_rationale="Candidate met quality threshold Q_req=0.65 with lowest scalarized cost (0.24).",
            objective_weights={"quality": 0.40, "latency": 0.25, "cost": 0.20, "environment": 0.15},
            quality_threshold=0.65,
            hard_constraints_passed=["Small Model", "Medium Model (Groq)", "Large Model (Gemini)"],
            pareto_frontier=["Medium Model (Groq)", "Large Model (Gemini)"],
            candidates=[
                CandidateScore(
                    route_name="Small Model",
                    provider="groq",
                    model="llama-3.1-8b-instant",
                    quality_score=0.55,
                    expected_latency_ms=80.0,
                    estimated_cost_usd=0.00001,
                    is_hard_constraint_met=False,
                    is_pareto_optimal=False,
                    scalarized_score=0.45,
                    rejection_reason="Failed quality threshold Q_req=0.65"
                ),
                CandidateScore(
                    route_name="Medium Model (Groq)",
                    provider="groq",
                    model="gemini-2.5-flash",
                    quality_score=0.78,
                    expected_latency_ms=160.0,
                    estimated_cost_usd=0.00005,
                    is_hard_constraint_met=True,
                    is_pareto_optimal=True,
                    scalarized_score=0.24
                )
            ]
        )
        rec = telemetry_collector.record_success(
            route="Medium Model (Groq)",
            provider="groq",
            model="gemini-2.5-flash",
            execution_time_ms=180.0,
            token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150, "is_estimated": False},
            routing_decision=decision
        )
        receipt = generate_eco_receipt(rec)

        self.assertIsNotNone(receipt.optimizer)
        self.assertEqual(receipt.optimizer.selected_candidate, "Medium Model (Groq)")
        self.assertEqual(receipt.optimizer.selected_tier, "medium")
        self.assertEqual(receipt.optimizer.quality_threshold_required, 0.65)
        self.assertTrue(receipt.optimizer.quality_threshold_met)
        self.assertEqual(len(receipt.optimizer.pareto_frontier), 2)
        self.assertEqual(len(receipt.optimizer.candidate_scores), 2)
        self.assertIn("quality: 0.40", receipt.explainability.selection_summary)

    def test_missing_environmental_metrics_remain_null_and_unavailable(self):
        """Missing environmental metrics remain None rather than 0.0 and are marked UNAVAILABLE."""
        rec = telemetry_collector.record_success(
            route="Large Model (Gemini)",
            provider="google",
            model="gemini-2.5-pro",
            execution_time_ms=450.0,
            token_usage={"prompt_tokens": 80, "completion_tokens": 120, "total_tokens": 200, "is_estimated": False}
        )
        receipt = generate_eco_receipt(rec)

        # Cloud API without estimation must NEVER fabricate 0.0 J or 0.0 gCO2e
        self.assertIsNone(receipt.environment.energy.value_joules)
        self.assertIsNone(receipt.environment.energy.value_kwh)
        self.assertEqual(receipt.environment.energy.provenance, ProvenanceStatus.UNAVAILABLE)
        self.assertFalse(receipt.environment.energy.is_measured)
        self.assertFalse(receipt.environment.energy.is_estimated)

        self.assertIsNone(receipt.environment.carbon.value_gco2e)
        self.assertEqual(receipt.environment.carbon.provenance, ProvenanceStatus.UNAVAILABLE)

        self.assertIsNone(receipt.environment.water.value_liters)
        self.assertEqual(receipt.environment.water.provenance, ProvenanceStatus.UNAVAILABLE)

    def test_measured_gpu_energy_and_estimated_carbon(self):
        """Directly measured GPU energy is scoped to GPU_INFERENCE_WINDOW and derives operational carbon."""
        gpu_telemetry = GpuTelemetry(
            device_name="NVIDIA GeForce RTX 3050 A Laptop GPU",
            average_power_watts=42.5,
            peak_power_watts=55.0,
            energy_joules=12.75,
            sample_count=8,
            measurement_duration_ms=300.0,
            provenance=ProvenanceStatus.MEASURED,
            scope=MeasurementScope.GPU_INFERENCE_WINDOW
        )
        # Configure grid intensity
        with patch("telemetry.telemetry.settings.LOCAL_GRID_INTENSITY_GCO2E_PER_KWH", 380.0):
            rec = telemetry_collector.record_success(
                route="Small Model (Local)",
                provider="local",
                model="local-small",
                execution_time_ms=320.0,
                inference_latency_ms=300.0,
                token_usage={"prompt_tokens": 20, "completion_tokens": 40, "total_tokens": 60, "is_estimated": False},
                gpu_telemetry=gpu_telemetry
            )
            receipt = generate_eco_receipt(rec)

            self.assertEqual(receipt.environment.energy.value_joules, 12.75)
            self.assertEqual(receipt.environment.energy.provenance, ProvenanceStatus.MEASURED)
            self.assertTrue(receipt.environment.energy.is_measured)
            self.assertEqual(receipt.environment.energy.scope, MeasurementScope.GPU_INFERENCE_WINDOW)
            self.assertIn("INFERENCE WINDOW ONLY", receipt.environment.energy.scope_disclaimer)

            # Carbon = (12.75 / 3,600,000) * 380 = 0.0013458 gCO2e
            self.assertIsNotNone(receipt.environment.carbon.value_gco2e)
            self.assertEqual(receipt.environment.carbon.provenance, ProvenanceStatus.ESTIMATED)
            self.assertAlmostEqual(receipt.environment.carbon.value_gco2e, (12.75 / 3_600_000.0) * 380.0, places=6)
            self.assertEqual(receipt.environment.carbon.grid_intensity_gco2e_per_kwh, 380.0)

    def test_carbon_unavailable_when_grid_intensity_missing(self):
        """Operational carbon is strictly UNAVAILABLE if grid intensity is not configured (<= 0)."""
        gpu_telemetry = GpuTelemetry(
            device_name="NVIDIA GeForce RTX 3050 A Laptop GPU",
            average_power_watts=40.0,
            peak_power_watts=50.0,
            energy_joules=10.0,
            sample_count=5,
            provenance=ProvenanceStatus.MEASURED
        )
        with patch("telemetry.telemetry.settings.LOCAL_GRID_INTENSITY_GCO2E_PER_KWH", 0.0):
            rec = telemetry_collector.record_success(
                route="Small Model (Local)",
                provider="local",
                model="local-small",
                execution_time_ms=250.0,
                gpu_telemetry=gpu_telemetry
            )
            receipt = generate_eco_receipt(rec)

            self.assertEqual(receipt.environment.energy.provenance, ProvenanceStatus.MEASURED)
            self.assertIsNone(receipt.environment.carbon.value_gco2e)
            self.assertEqual(receipt.environment.carbon.provenance, ProvenanceStatus.UNAVAILABLE)

    def test_water_impact_strictly_unavailable(self):
        """Water footprint remains strictly None and UNAVAILABLE with anti-fabrication reason."""
        rec = telemetry_collector.record_success(
            route="Medium Model (Groq)",
            provider="groq",
            model="gemini-2.5-flash",
            execution_time_ms=120.0
        )
        receipt = generate_eco_receipt(rec)

        self.assertIsNone(receipt.environment.water.value_liters)
        self.assertEqual(receipt.environment.water.provenance, ProvenanceStatus.UNAVAILABLE)
        self.assertIn("anti-fabrication safeguard", receipt.environment.water.reason_unavailable)

    def test_receipt_for_failed_request(self):
        """Failed requests record failure honestly without inventing completed-inference metrics."""
        rec = telemetry_collector.record_failure(
            route="Large Model (Gemini)",
            provider="google",
            execution_time_ms=85.0,
            error_message="API rate limit exceeded (HTTP 429)",
            model="gemini-2.5-pro"
        )
        receipt = generate_eco_receipt(rec)

        self.assertEqual(receipt.status, "FAILED")
        self.assertIsNone(receipt.tokens.total_tokens)
        self.assertEqual(receipt.tokens.provenance, ProvenanceStatus.UNAVAILABLE)
        self.assertIsNone(receipt.cost.value_usd)
        self.assertEqual(receipt.cost.provenance, ProvenanceStatus.UNAVAILABLE)
        self.assertIn("API rate limit exceeded", receipt.explainability.selection_summary)

    def test_api_chat_includes_eco_receipt(self):
        """Chat API response includes full EcoReceipt and preserves backward compatibility."""
        response = self.client.post("/chat", json={"query": "25 * 4", "preferred_route": "auto"})
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Backward compatibility check
        self.assertIn("query", data)
        self.assertIn("answer", data)
        self.assertIn("route", data)
        self.assertIn("execution_time_ms", data)
        self.assertIn("telemetry", data)
        self.assertIn("metadata", data)

        # Phase 7 Eco Receipt checks
        self.assertIn("eco_receipt", data)
        receipt = data["eco_receipt"]
        self.assertIsNotNone(receipt)
        self.assertTrue(receipt["receipt_id"].startswith("rcpt_"))
        self.assertEqual(receipt["status"], "SUCCESS")
        self.assertEqual(receipt["execution_path"], "deterministic_tool")
        self.assertEqual(receipt["tokens"]["total_tokens"], 0)
        self.assertEqual(receipt["cost"]["value_usd"], 0.0)
        self.assertIn("eco_receipt", data["metadata"])

    def test_api_receipt_retrieval_endpoint(self):
        """Receipt can be retrieved by request_id from GET /receipts/{request_id}."""
        # 1. Execute a query to create a telemetry record
        chat_resp = self.client.post("/chat", json={"query": "convert 50 km to miles"})
        self.assertEqual(chat_resp.status_code, 200)
        req_id = chat_resp.json()["telemetry"]["request_id"]

        # 2. Retrieve receipt via GET /receipts/{req_id}
        resp = self.client.get(f"/receipts/{req_id}")
        self.assertEqual(resp.status_code, 200)
        receipt_data = resp.json()
        self.assertEqual(receipt_data["request_id"], req_id)
        self.assertEqual(receipt_data["execution_path"], "deterministic_tool")
        self.assertEqual(receipt_data["status"], "SUCCESS")

        # 3. Retrieve via alias GET /telemetry/receipt/{req_id}
        alias_resp = self.client.get(f"/telemetry/receipt/{req_id}")
        self.assertEqual(alias_resp.status_code, 200)
        self.assertEqual(alias_resp.json()["receipt_id"], receipt_data["receipt_id"])

    def test_api_receipt_retrieval_not_found(self):
        """GET /receipts/{request_id} returns 404 for unknown request ID."""
        resp = self.client.get("/receipts/non-existent-uuid-12345")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("No telemetry record found", resp.json()["detail"])

    def test_receipt_serialization_roundtrip(self):
        """Receipt serializes to dict/json and validates back into Pydantic schema without error."""
        rec = telemetry_collector.record_success(
            route="Calculator / Deterministic Tool",
            provider="deterministic",
            model="None",
            execution_time_ms=0.5,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "is_estimated": False}
        )
        receipt = generate_eco_receipt(rec)
        serialized = receipt.model_dump()
        reconstructed = EcoReceipt.model_validate(serialized)
        self.assertEqual(receipt.receipt_id, reconstructed.receipt_id)
        self.assertEqual(receipt.explainability.selection_summary, reconstructed.explainability.selection_summary)

if __name__ == "__main__":
    unittest.main()


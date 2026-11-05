import os
import unittest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from main import app
from database.historical_store import HistoricalStore, historical_store
from telemetry.telemetry import TelemetryCollector, telemetry_collector
from receipt.receipt_generator import generate_eco_receipt
from telemetry.schemas import (
    ProvenanceStatus,
    MeasurementScope,
    PhysicalMeasurement,
    TokenTelemetry,
    LatencyTelemetry,
    EnvironmentalTelemetry,
    AvoidanceTelemetry,
    TelemetryRecord,
    RoutingDecision
)
from models.provider import TokenUsage

class TestDashboardAndHistoricalStore(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Use a fresh in-memory or isolated test historical store
        self.test_store = HistoricalStore(db_path=":memory:")
        # Point the global singleton's connection or clear the real store
        historical_store.clear()
        telemetry_collector.clear()

    def tearDown(self):
        historical_store.clear()
        telemetry_collector.clear()

    def _create_mock_record(
        self,
        request_id="test_req_1",
        route="Calculator / Deterministic Tool",
        provider="deterministic",
        model=None,
        success=True,
        execution_time_ms=12.5,
        energy_joules=None,
        is_measured=False,
        is_estimated=False,
        carbon_gco2e=None,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        cost_usd=0.0,
        is_zero_cost=True,
        calls_avoided=1
    ):
        """Helper to create realistic TelemetryRecord and EcoReceipt pairs."""
        prov = ProvenanceStatus.MEASURED if is_measured else (ProvenanceStatus.ESTIMATED if is_estimated else ProvenanceStatus.UNAVAILABLE)
        env = EnvironmentalTelemetry(
            energy_joules=energy_joules,
            water_liters=None,
            carbon_gco2e=carbon_gco2e,
            provenance=prov,
            energy_provenance=prov,
            carbon_provenance=ProvenanceStatus.ESTIMATED if carbon_gco2e is not None else ProvenanceStatus.UNAVAILABLE,
            water_provenance=ProvenanceStatus.UNAVAILABLE,
            measurement=PhysicalMeasurement(
                value=energy_joules,
                unit="J",
                provenance=prov,
                scope=MeasurementScope.GPU_INFERENCE_WINDOW if is_measured else MeasurementScope.UNKNOWN
            ) if energy_joules is not None else None
        )
        avoidance = AvoidanceTelemetry(
            model_calls_avoided=calls_avoided,
            tokens_avoided=None,
            baseline_route="large_model",
            reasoning="Test avoidance"
        )
        rec = TelemetryRecord(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            route=route,
            provider=provider,
            model=model,
            success=success,
            error_message=None if success else "Simulated error",
            tokens=TokenTelemetry(
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                total_tokens=total_tokens,
                provenance=ProvenanceStatus.MEASURED if provider in ("deterministic", "cache") else ProvenanceStatus.ESTIMATED
            ),
            latency=LatencyTelemetry(
                execution_time_ms=execution_time_ms,
                inference_latency_ms=execution_time_ms * 0.8,
                provenance=ProvenanceStatus.MEASURED
            ),
            environment=env,
            avoidance=avoidance
        )
        receipt = generate_eco_receipt(rec, query="test query")
        if carbon_gco2e is not None:
            receipt.environment.carbon.value_gco2e = carbon_gco2e
            receipt.environment.carbon.provenance = ProvenanceStatus.ESTIMATED
        if cost_usd is not None and cost_usd > 0:
            receipt.cost.value_usd = cost_usd
            receipt.cost.is_zero_external_api_charge = is_zero_cost
        return rec, receipt

    def test_save_and_retrieve_receipt_from_store(self):
        """Verify saving and retrieving Eco Receipts from SQLite store."""
        rec, receipt = self._create_mock_record(
            request_id="req_det_1",
            route="Calculator / Deterministic Tool",
            provider="deterministic"
        )
        saved = self.test_store.save_record(rec, receipt, query_preview="calculate 2 + 2")
        self.assertTrue(saved)

        fetched = self.test_store.get_receipt("req_det_1")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.request_id, "req_det_1")
        self.assertEqual(fetched.execution_path.value, "deterministic_tool")
        self.assertEqual(fetched.cost.is_zero_external_api_charge, True)
        self.assertEqual(fetched.query_preview, "calculate 2 + 2")

    def test_deduplication_on_repeated_request_id(self):
        """Verify saving with an identical request_id updates existing record without duplicate rows."""
        rec, receipt = self._create_mock_record(request_id="dedup_req_1", execution_time_ms=10.0)
        self.test_store.save_record(rec, receipt)
        self.assertEqual(self.test_store.count(), 1)

        # Update and save again with same request_id
        rec.latency.execution_time_ms = 25.0
        receipt2 = generate_eco_receipt(rec, query="updated query")
        self.test_store.save_record(rec, receipt2)

        self.assertEqual(self.test_store.count(), 1)
        fetched = self.test_store.get_receipt("dedup_req_1")
        self.assertEqual(fetched.execution_time_ms, 25.0)

    def test_query_preview_length_cap(self):
        """Verify long query texts are safely truncated to protect privacy."""
        long_query = "A" * 300
        rec, receipt = self._create_mock_record(request_id="long_q_req")
        self.test_store.save_record(rec, receipt, query_preview=long_query)

        res = self.test_store.list_receipts(page=1, page_size=10)
        self.assertEqual(len(res["items"]), 1)
        preview = res["items"][0]["query_preview"]
        self.assertLessEqual(len(preview), 120)

    def test_pagination_and_path_filtering(self):
        """Verify pagination offsets, page sizes, and execution_path filtering."""
        # Insert 3 deterministic, 2 cache, 2 model inference records
        for i in range(3):
            r, rc = self._create_mock_record(request_id=f"det_{i}", route="Calculator / Deterministic Tool", provider="deterministic")
            self.test_store.save_record(r, rc)
        for i in range(2):
            r, rc = self._create_mock_record(request_id=f"cache_{i}", route="Semantic Cache", provider="cache")
            self.test_store.save_record(r, rc)
        for i in range(2):
            r, rc = self._create_mock_record(request_id=f"model_{i}", route="Small Model (Groq)", provider="groq", model="llama-3")
            self.test_store.save_record(r, rc)

        self.assertEqual(self.test_store.count(), 7)

        # Test pagination page 1 with page_size=3
        p1 = self.test_store.list_receipts(page=1, page_size=3)
        self.assertEqual(len(p1["items"]), 3)
        self.assertEqual(p1["total_count"], 7)
        self.assertEqual(p1["total_pages"], 3)

        # Test pagination page 3
        p3 = self.test_store.list_receipts(page=3, page_size=3)
        self.assertEqual(len(p3["items"]), 1)

        # Test filtering by deterministic_tool
        filtered_det = self.test_store.list_receipts(execution_path="deterministic_tool")
        self.assertEqual(filtered_det["total_count"], 3)
        for it in filtered_det["items"]:
            self.assertEqual(it["execution_path"], "deterministic_tool")

        # Test filtering by model_inference
        filtered_model = self.test_store.list_receipts(execution_path="model_inference")
        self.assertEqual(filtered_model["total_count"], 2)

    def test_environmental_summary_measured_vs_estimated(self):
        """Verify environmental aggregations strictly separate measured from estimated energy and handle nulls."""
        # Record 1: Measured energy (e.g. 500 Joules, 0.05 gCO2e)
        r1, rc1 = self._create_mock_record(
            request_id="env_m",
            route="Local GPU Small",
            provider="ollama",
            energy_joules=500.0,
            is_measured=True,
            carbon_gco2e=0.05
        )
        self.test_store.save_record(r1, rc1)

        # Record 2: Estimated energy (e.g. 200 Joules, no carbon)
        r2, rc2 = self._create_mock_record(
            request_id="env_e",
            route="Cloud Groq",
            provider="groq",
            energy_joules=200.0,
            is_estimated=True,
            carbon_gco2e=None
        )
        self.test_store.save_record(r2, rc2)

        # Record 3: Unavailable energy (deterministic tool with 0 tokens)
        r3, rc3 = self._create_mock_record(
            request_id="env_u",
            route="Calculator / Deterministic Tool",
            provider="deterministic",
            energy_joules=None
        )
        self.test_store.save_record(r3, rc3)

        env_summary = self.test_store.get_environmental_summary()
        self.assertEqual(env_summary["total_requests"], 3)
        self.assertEqual(env_summary["records_with_measured_energy"], 1)
        self.assertEqual(env_summary["records_with_estimated_energy"], 1)
        self.assertEqual(env_summary["records_with_unavailable_energy"], 1)

        self.assertAlmostEqual(env_summary["measured_energy_joules"], 500.0)
        self.assertAlmostEqual(env_summary["estimated_energy_joules"], 200.0)
        self.assertAlmostEqual(env_summary["carbon_from_measured_energy_gco2e"], 0.05)
        self.assertAlmostEqual(env_summary["total_carbon_gco2e"], 0.05)
        self.assertEqual(env_summary["records_with_water"], 0)
        self.assertIn("UNAVAILABLE", env_summary["water_disclosure"])
        self.assertIn("GPU inference windows only", env_summary["scope_boundary_notice"])

    def test_summary_kpis(self):
        """Verify summary aggregations for counts, costs, and avoided calls."""
        r1, rc1 = self._create_mock_record(
            request_id="kpi_1",
            execution_time_ms=10.0,
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            cost_usd=0.00004,
            is_zero_cost=False,
            calls_avoided=0
        )
        r2, rc2 = self._create_mock_record(
            request_id="kpi_2",
            execution_time_ms=5.0,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            cost_usd=0.0,
            is_zero_cost=True,
            calls_avoided=1
        )
        self.test_store.save_record(r1, rc1)
        self.test_store.save_record(r2, rc2)

        summary = self.test_store.get_summary()
        self.assertEqual(summary["total_requests"], 2)
        self.assertEqual(summary["successful_requests"], 2)
        self.assertEqual(summary["success_rate_percent"], 100.0)
        self.assertEqual(summary["total_tokens"], 30)
        self.assertAlmostEqual(summary["total_external_api_cost_usd"], 0.00004, places=7)
        self.assertEqual(summary["zero_external_api_cost_count"], 1)
        self.assertEqual(summary["billed_external_api_cost_count"], 1)
        self.assertEqual(summary["total_model_calls_avoided"], 1)

    def test_routes_analytics_and_pareto(self):
        """Verify route analytics and Pareto frequency tracking."""
        r1, rc1 = self._create_mock_record(request_id="route_1", route="Small Model")
        self.test_store.save_record(r1, rc1)

        routes_summary = self.test_store.get_routes_analytics()
        self.assertEqual(routes_summary["total_evaluated_requests"], 1)
        self.assertIn("route_statistics", routes_summary)
        self.assertEqual(len(routes_summary["route_statistics"]), 1)
        self.assertEqual(routes_summary["route_statistics"][0]["route"], "Small Model")

    def test_timeseries_aggregation(self):
        """Verify hourly/daily timeseries grouping."""
        r1, rc1 = self._create_mock_record(request_id="ts_1", execution_time_ms=15.0)
        self.test_store.save_record(r1, rc1)

        series = self.test_store.get_timeseries(interval="hour")
        self.assertEqual(len(series), 1)
        self.assertEqual(series[0]["request_count"], 1)
        self.assertEqual(series[0]["avg_latency_ms"], 15.0)

    def test_api_dashboard_endpoints(self):
        """Verify FastAPI REST endpoints for /dashboard/*."""
        # Insert a record directly into the live historical_store singleton
        r1, rc1 = self._create_mock_record(
            request_id="api_test_req",
            route="Calculator / Deterministic Tool",
            provider="deterministic"
        )
        historical_store.save_record(r1, rc1, query_preview="api test")

        # 1. GET /dashboard/summary
        resp = self.client.get("/dashboard/summary")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(data["total_requests"], 1)

        # 2. GET /dashboard/environment
        resp = self.client.get("/dashboard/environment")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("records_with_measured_energy", data)
        self.assertIn("records_with_estimated_energy", data)

        # 3. GET /dashboard/routes
        resp = self.client.get("/dashboard/routes")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("route_statistics", data)

        # 4. GET /dashboard/timeseries
        resp = self.client.get("/dashboard/timeseries?interval=hour")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

        # 5. GET /dashboard/receipts
        resp = self.client.get("/dashboard/receipts?page=1&page_size=10")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("items", data)
        self.assertGreaterEqual(data["total_count"], 1)

        # 6. GET /dashboard/receipts/{request_id}
        resp = self.client.get("/dashboard/receipts/api_test_req")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["request_id"], "api_test_req")

        # 7. GET /dashboard/receipts/nonexistent -> 404
        resp = self.client.get("/dashboard/receipts/non_existent_id_xyz")
        self.assertEqual(resp.status_code, 404)

    def test_live_chat_persists_to_sqlite_and_survives_memory_eviction(self):
        """
        Verify that a real request through /chat automatically persists to SQLite,
        and remains retrievable even if the in-memory telemetry buffer is wiped out!
        """
        # Call /chat with a deterministic calculation
        chat_resp = self.client.post("/chat", json={"query": "calculate 42 * 10", "preferred_route": "auto"})
        self.assertEqual(chat_resp.status_code, 200)
        chat_data = chat_resp.json()
        req_id = chat_data["telemetry"]["request_id"]
        self.assertTrue(req_id)

        # Verify receipt exists in SQLite store immediately
        stored_rcpt = historical_store.get_receipt(req_id)
        self.assertIsNotNone(stored_rcpt)
        self.assertEqual(stored_rcpt.request_id, req_id)
        self.assertEqual(stored_rcpt.route, "Calculator / Deterministic Tool")

        # Now simulate memory eviction by clearing the in-memory telemetry collector
        telemetry_collector.clear()
        self.assertIsNone(telemetry_collector.get_record(req_id))

        # Retrieve via /dashboard/receipts/{request_id}
        dash_rcpt_resp = self.client.get(f"/dashboard/receipts/{req_id}")
        self.assertEqual(dash_rcpt_resp.status_code, 200)
        self.assertEqual(dash_rcpt_resp.json()["request_id"], req_id)

        # Retrieve via /receipts/{request_id}
        std_rcpt_resp = self.client.get(f"/receipts/{req_id}")
        self.assertEqual(std_rcpt_resp.status_code, 200)
        self.assertEqual(std_rcpt_resp.json()["request_id"], req_id)

if __name__ == "__main__":
    unittest.main()

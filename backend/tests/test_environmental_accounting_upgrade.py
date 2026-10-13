"""
EcoMind Phase 5B Upgrade: Verification Test Suite for Fresh, Evidence-Based Environmental Accounting.

Covers:
1. Versioned Environmental Source Registry and metadata completeness.
2. Source freshness auditing, review intervals, stale flags, and failure fallback retention.
3. Pluggable Cloud Energy Estimation (ML.ENERGY empirical and EcoLogits LCA adapters).
4. Unsupported model handling, unknown uncertainty reporting, and unit conversions.
5. Static and dynamic regional grid carbon intensity management with non-substitution guarantees.
6. Water accounting safeguards and distinct categorization.
7. Upgraded pair-wise savings comparison (measured vs measured, estimated vs estimated, mixed provenance, quality gates).
8. Telemetry API endpoints (/telemetry/sources, /telemetry/grid, /telemetry/savings/compare).
"""

import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from config.settings import settings
from main import app
from models.provider import TokenUsage
from telemetry.schemas import (
    ProvenanceStatus,
    MeasurementScope,
    ComparisonType,
    SourceType,
    SourceValidationStatus,
    EnvironmentalSource,
    SourceCheckResult,
    GridIntensityRecord,
    PhysicalMeasurement,
    TokenTelemetry,
    LatencyTelemetry,
    EnvironmentalTelemetry,
    TelemetryRecord,
    MetricSavings,
    SavingsComparison,
)
from telemetry.registry import (
    SourceRegistry,
    SourceValidationService,
    source_registry,
    source_validation_service,
)
from telemetry.cloud_estimator import (
    MLEnergyEstimator,
    EcoLogitsEstimator,
    CompositeCloudEstimator,
    cloud_energy_estimator,
)
from telemetry.grid import GridIntensityManager, grid_manager
from telemetry.water import WaterAccountingEngine, water_accounting_engine
from telemetry.savings import calculate_savings
from telemetry.telemetry import TelemetryCollector, telemetry_collector


class TestEnvironmentalAccountingUpgrade(unittest.TestCase):
    """Test suite for Phase 5B fresh evidence-based environmental accounting."""

    def setUp(self):
        self.collector = TelemetryCollector()
        self.client = TestClient(app)

    # =========================================================================
    # 1. Source Registry & Metadata Tests
    # =========================================================================

    def test_default_source_registry_catalog(self):
        """Verify all default peer-reviewed and empirical sources are loaded."""
        sources = source_registry.list_all()
        self.assertGreaterEqual(len(sources), 6)

        source_ids = [s.source_id for s in sources]
        self.assertIn("src-nvml-nvidia-2024", source_ids)
        self.assertIn("src-mlenergy-leaderboard-v3", source_ids)
        self.assertIn("src-ecologits-lca-2024", source_ids)
        self.assertIn("src-google-elsworth-2025", source_ids)
        self.assertIn("src-ember-climate-2024", source_ids)
        self.assertIn("src-electricitymaps-v3", source_ids)
        self.assertIn("src-groq-isca-2020", source_ids)

    def test_source_metadata_completeness_and_hash(self):
        """Verify that every source contains citations, formula, assumptions, scope, and integrity hash."""
        ml_src = source_registry.get("src-mlenergy-leaderboard-v3")
        self.assertIsNotNone(ml_src)
        self.assertEqual(ml_src.source_type, SourceType.BENCHMARK_DATASET)
        self.assertEqual(ml_src.measurement_scope, MeasurementScope.SYSTEM)
        self.assertIn("E_inference", ml_src.formula)
        self.assertIn("energy", ml_src.supported_metrics)
        self.assertGreater(len(ml_src.assumptions), 0)
        self.assertTrue(len(ml_src.content_hash) > 0)
        self.assertIn("SymbioticLab", ml_src.publisher)

    def test_source_registry_duplicate_registration_protection(self):
        """Registering a duplicate source ID without overwrite=True must raise ValueError."""
        src = source_registry.get("src-nvml-nvidia-2024")
        with self.assertRaises(ValueError):
            source_registry.register(src, overwrite=False)

    # =========================================================================
    # 2. Source Freshness & Lifecycle Validation Tests
    # =========================================================================

    def test_source_freshness_current_status(self):
        """A source verified recently is marked CURRENT."""
        svc = SourceValidationService(source_registry)
        res = svc.check_source("src-mlenergy-leaderboard-v3")
        self.assertEqual(res.status, SourceValidationStatus.CURRENT)
        self.assertFalse(res.needs_review)

    def test_source_freshness_review_needed_and_stale_flagging(self):
        """Sources older than review threshold become REVIEW_NEEDED; older than stale threshold become STALE."""
        reg = SourceRegistry()
        svc = SourceValidationService(reg)

        # Create source verified 45 days ago (> 30 days review threshold)
        t_review = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
        src_rev = EnvironmentalSource(
            source_id="test-review-src",
            name="Test Review Source",
            url="https://example.com/test",
            publisher="Test Org",
            source_type=SourceType.RESEARCH_PAPER,
            publication_date="2024-01-01",
            retrieval_date="2024-01-01",
            last_verified_timestamp=t_review,
            measurement_scope=MeasurementScope.SYSTEM,
            version="1.0"
        )
        reg.register(src_rev)
        res_rev = svc.check_source("test-review-src")
        self.assertEqual(res_rev.status, SourceValidationStatus.REVIEW_NEEDED)
        self.assertTrue(res_rev.needs_review)

        # Create source verified 100 days ago (> 90 days stale threshold)
        t_stale = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        src_stale = EnvironmentalSource(
            source_id="test-stale-src",
            name="Test Stale Source",
            url="https://example.com/stale",
            publisher="Test Org",
            source_type=SourceType.RESEARCH_PAPER,
            publication_date="2024-01-01",
            retrieval_date="2024-01-01",
            last_verified_timestamp=t_stale,
            measurement_scope=MeasurementScope.SYSTEM,
            version="1.0"
        )
        reg.register(src_stale)
        res_stale = svc.check_source("test-stale-src")
        self.assertEqual(res_stale.status, SourceValidationStatus.STALE)
        self.assertTrue(res_stale.needs_review)

    def test_source_refresh_failure_retains_last_validated_version(self):
        """When upstream reachability fails, validation flags UNAVAILABLE/needs_review but retains existing version."""
        reg = SourceRegistry()
        svc = SourceValidationService(reg)
        src = reg.get("src-mlenergy-leaderboard-v3")

        def failing_network_checker(url: str) -> bool:
            return False  # Simulate offline / DNS failure

        res = svc.check_source(src.source_id, network_checker=failing_network_checker)
        self.assertEqual(res.status, SourceValidationStatus.UNAVAILABLE)
        self.assertTrue(res.needs_review)
        self.assertFalse(res.is_accessible)
        # Previous version remains intact in registry
        retained = reg.get("src-mlenergy-leaderboard-v3")
        self.assertEqual(retained.version, "3.0")

    # =========================================================================
    # 3. Cloud Energy Estimators (ML.ENERGY & EcoLogits)
    # =========================================================================

    def test_mlenergy_estimator_small_tier(self):
        """ML.ENERGY estimator calculates correct energy for small model tier."""
        est = MLEnergyEstimator()
        self.assertTrue(est.supports("groq", "openai/gpt-oss-20b"))

        # prompt=100, completion=50
        # prefill: 100 * 0.0008 = 0.08 J
        # decode: 50 * 0.0080 = 0.40 J
        # baseline: 0.50 J -> Total = 0.98 J
        res = est.estimate("groq", "openai/gpt-oss-20b", prompt_tokens=100, completion_tokens=50)
        self.assertIsNotNone(res)
        self.assertEqual(res.energy_joules, 0.98)
        self.assertEqual(res.energy_kwh, round(0.98 / 3_600_000.0, 8))
        self.assertEqual(res.energy_provenance, ProvenanceStatus.ESTIMATED)
        self.assertEqual(res.carbon_provenance, ProvenanceStatus.UNAVAILABLE)
        self.assertEqual(res.water_provenance, ProvenanceStatus.UNAVAILABLE)
        self.assertEqual(res.scope, MeasurementScope.SYSTEM)
        self.assertEqual(res.estimator_name, "MLEnergyEstimator")
        self.assertEqual(res.source_id, "src-mlenergy-leaderboard-v3")
        self.assertIn("NVIDIA H100 SXM5", res.assumptions[0])

    def test_mlenergy_estimator_large_tier(self):
        """ML.ENERGY estimator calculates correct energy for 70B/120B large tier."""
        est = MLEnergyEstimator()
        self.assertTrue(est.supports("groq", "openai/gpt-oss-120b"))
        self.assertTrue(est.supports("groq", "llama-3.3-70b"))

        # prompt=200, completion=100
        # prefill: 200 * 0.0040 = 0.80 J
        # decode: 100 * 0.0450 = 4.50 J
        # baseline: 1.50 J -> Total = 6.80 J
        res = est.estimate("groq", "openai/gpt-oss-120b", prompt_tokens=200, completion_tokens=100)
        self.assertIsNotNone(res)
        self.assertEqual(res.energy_joules, 6.80)
        self.assertEqual(res.energy_provenance, ProvenanceStatus.ESTIMATED)

    def test_ecologits_estimator_lca_model(self):
        """EcoLogits estimator computes energy using active generation time, PUE, and embodied overhead."""
        est = EcoLogitsEstimator()
        self.assertTrue(est.supports("openai", "gpt-4o"))

        res = est.estimate("openai", "gpt-4o", prompt_tokens=50, completion_tokens=100, latency_ms=2000.0)
        self.assertIsNotNone(res)
        self.assertGreater(res.energy_joules, 0.0)
        self.assertEqual(res.energy_provenance, ProvenanceStatus.ESTIMATED)
        self.assertEqual(res.scope, MeasurementScope.CLOUD_INFERENCE)
        self.assertEqual(res.estimator_name, "EcoLogitsEstimator")
        self.assertIn("Life Cycle Assessment", res.assumptions[0])
        self.assertIn("Confidence interval is unknown", res.uncertainty_info)

    def test_unsupported_cloud_model_returns_none(self):
        """A proprietary or uncharacterized model without empirical evidence returns None without fabrication."""
        comp = CompositeCloudEstimator()
        self.assertFalse(comp.supports("groq", "nonexistent-model-xyz"))
        res = comp.estimate("groq", "nonexistent-model-xyz", prompt_tokens=50, completion_tokens=50)
        self.assertIsNone(res)

    def test_point_estimate_uncertainty_explicitly_reported(self):
        """Estimators explicitly report that point estimates have unknown confidence intervals without fabricating."""
        est = MLEnergyEstimator()
        res = est.estimate("groq", "llama-3.1-8b", prompt_tokens=10, completion_tokens=10)
        self.assertIn("Point estimate", res.uncertainty_info)
        self.assertIn("ML.ENERGY", res.uncertainty_info)

    def test_telemetry_collector_with_cloud_estimator_enabled(self):
        """When ENABLE_CLOUD_ENERGY_ESTIMATION is True, TelemetryCollector attaches validated estimated energy."""
        with patch.object(settings, "ENABLE_CLOUD_ENERGY_ESTIMATION", True):
            rec = self.collector.record_success(
                route="Large Model (Groq)",
                provider="groq",
                model="openai/gpt-oss-120b",
                execution_time_ms=500.0,
                inference_latency_ms=480.0,
                token_usage=TokenUsage(prompt_tokens=100, completion_tokens=100, total_tokens=200)
            )

            # Energy is ESTIMATED via MLEnergyEstimator
            self.assertIsNotNone(rec.environment.energy_joules)
            self.assertEqual(rec.environment.provenance, ProvenanceStatus.ESTIMATED)
            self.assertEqual(rec.environment.energy_provenance, ProvenanceStatus.ESTIMATED)
            self.assertEqual(rec.environment.estimator_name, "MLEnergyEstimator")
            self.assertEqual(rec.environment.source_id, "src-mlenergy-leaderboard-v3")
            self.assertIn("vLLM", rec.environment.assumptions[3])

            # Water and carbon remain strictly UNAVAILABLE
            self.assertIsNone(rec.environment.water_liters)
            self.assertEqual(rec.environment.water_provenance, ProvenanceStatus.UNAVAILABLE)
            self.assertIsNone(rec.environment.carbon_gco2e)
            self.assertEqual(rec.environment.carbon_provenance, ProvenanceStatus.UNAVAILABLE)

    # =========================================================================
    # 4. Grid Carbon Intensity Management Tests
    # =========================================================================

    def test_static_configured_grid_intensity(self):
        """Verify static configured factor calculation and provenance."""
        with patch.object(settings, "LOCAL_GRID_INTENSITY_GCO2E_PER_KWH", 370.0):
            mgr = GridIntensityManager()
            rec = mgr.get_intensity()
            self.assertIsNotNone(rec)
            self.assertEqual(rec.intensity_gco2e_per_kwh, 370.0)
            self.assertFalse(rec.is_live)
            self.assertEqual(rec.source_name, "UserConfiguredStatic")

            # 3,600,000 J = 1 kWh -> at 370 gCO2e/kWh = 370.0 gCO2e
            c_val, _ = mgr.calculate_operational_carbon(3_600_000.0)
            self.assertEqual(c_val, 370.0)

    def test_regional_catalog_fallback_ember(self):
        """Verify verified regional database lookups (Ember 2024)."""
        with patch.object(settings, "LOCAL_GRID_INTENSITY_GCO2E_PER_KWH", None):
            mgr = GridIntensityManager()
            rec_fr = mgr.get_intensity("FR")
            self.assertIsNotNone(rec_fr)
            self.assertEqual(rec_fr.intensity_gco2e_per_kwh, 55.0)  # Low carbon France
            self.assertFalse(rec_fr.is_live)
            self.assertEqual(rec_fr.source_name, "EmberGlobalElectricityReview2024")

            rec_in = mgr.get_intensity("IN")
            self.assertEqual(rec_in.intensity_gco2e_per_kwh, 710.0)

    def test_dynamic_grid_intensity_provider_and_fallback(self):
        """Verify live dynamic grid provider and graceful fallback when dynamic provider fails."""
        mock_dynamic_live = MagicMock(return_value=195.5)
        mgr = GridIntensityManager(dynamic_provider_fn=mock_dynamic_live)

        with patch.object(settings, "LOCAL_GRID_INTENSITY_GCO2E_PER_KWH", None), \
             patch.object(settings, "ENABLE_DYNAMIC_GRID_INTENSITY", True):
            rec = mgr.get_intensity("US-CA")
            self.assertIsNotNone(rec)
            self.assertEqual(rec.intensity_gco2e_per_kwh, 195.5)
            self.assertTrue(rec.is_live)

        # When dynamic provider raises an exception, fallback to static Ember database
        mock_failing = MagicMock(side_effect=RuntimeError("API timeout"))
        mgr_failing = GridIntensityManager(dynamic_provider_fn=mock_failing)
        with patch.object(settings, "LOCAL_GRID_INTENSITY_GCO2E_PER_KWH", None), \
             patch.object(settings, "ENABLE_DYNAMIC_GRID_INTENSITY", True):
            rec_fallback = mgr_failing.get_intensity("US")
            self.assertIsNotNone(rec_fallback)
            self.assertEqual(rec_fallback.intensity_gco2e_per_kwh, 370.0)
            self.assertFalse(rec_fallback.is_live)
            self.assertTrue(rec_fallback.fallback_used)

    def test_no_silent_substitution_for_unknown_region(self):
        """When grid factor is unconfigured and region is DEFAULT/unrecognized, do NOT invent country values."""
        with patch.object(settings, "LOCAL_GRID_INTENSITY_GCO2E_PER_KWH", None), \
             patch.object(settings, "LOCAL_GRID_REGION", "DEFAULT"):
            mgr = GridIntensityManager()
            rec = mgr.get_intensity()
            self.assertIsNone(rec)
            carbon_val, _ = mgr.calculate_operational_carbon(1000.0)
            self.assertIsNone(carbon_val)

    # =========================================================================
    # 5. Water Accounting Safeguards Tests
    # =========================================================================

    def test_water_accounting_cloud_safeguard(self):
        """Cloud providers return UNAVAILABLE with detailed explanation of missing data."""
        engine = WaterAccountingEngine()
        val, prov, expl = engine.evaluate_water("groq", "llama-3.3-70b")
        self.assertIsNone(val)
        self.assertEqual(prov, ProvenanceStatus.UNAVAILABLE)
        self.assertIn("does not disclose physical data-center facility locations", expl["reason"])
        self.assertIn("WUE", expl["missing_data"])

    def test_water_accounting_local_safeguard(self):
        """Air-cooled local hardware distinguishes 0 direct water from unmeasured indirect utility water."""
        engine = WaterAccountingEngine()
        val, prov, expl = engine.evaluate_water("local", "llama3.1:8b")
        self.assertIsNone(val)
        self.assertEqual(prov, ProvenanceStatus.UNAVAILABLE)
        self.assertIn("ambient air-cooling with 0.0 direct", expl["reason"])
        self.assertIn("utility water consumption intensity", expl["missing_data"])

    # =========================================================================
    # 6. Upgraded Pair-Wise Savings Comparison Tests
    # =========================================================================

    def test_pairwise_savings_measured_vs_measured(self):
        """Both routes measured -> comparison_type = MEASURED_VS_MEASURED."""
        meas_base = PhysicalMeasurement(
            value=100.0, unit="J", provenance=ProvenanceStatus.MEASURED,
            source="NvidiaNvmlProvider", scope=MeasurementScope.GPU_INFERENCE_WINDOW, status="AVAILABLE"
        )
        meas_sel = PhysicalMeasurement(
            value=40.0, unit="J", provenance=ProvenanceStatus.MEASURED,
            source="NvidiaNvmlProvider", scope=MeasurementScope.GPU_INFERENCE_WINDOW, status="AVAILABLE"
        )

        base_rec = self.collector.record_success(
            route="Large Model (Local)", provider="local", execution_time_ms=1000.0,
            token_usage=TokenUsage(prompt_tokens=20, completion_tokens=80, total_tokens=100),
            physical_measurement=meas_base
        )
        sel_rec = self.collector.record_success(
            route="Small Model (Local)", provider="local", execution_time_ms=400.0,
            token_usage=TokenUsage(prompt_tokens=20, completion_tokens=30, total_tokens=50),
            physical_measurement=meas_sel
        )

        savings = calculate_savings(selected=sel_rec, baseline=base_rec)
        self.assertEqual(savings.comparison_type, ComparisonType.MEASURED_VS_MEASURED)
        self.assertEqual(savings.energy_savings.comparison_type, ComparisonType.MEASURED_VS_MEASURED)
        self.assertEqual(savings.energy_savings.provenance, ProvenanceStatus.MEASURED)
        self.assertEqual(savings.energy_savings.savings_value, 60.0)
        self.assertEqual(savings.energy_savings.savings_pct, 60.0)
        self.assertEqual(savings.tokens_saved, 50)
        self.assertEqual(savings.latency_delta_ms, 600.0)

    def test_pairwise_savings_estimated_vs_estimated(self):
        """Both routes estimated -> comparison_type = ESTIMATED_VS_ESTIMATED."""
        base_rec = TelemetryRecord(
            request_id="base-1", timestamp="2026-10-13T10:00:00Z", route="Large Model (Groq)",
            provider="groq", model="openai/gpt-oss-120b", success=True,
            tokens=TokenTelemetry(input_tokens=100, output_tokens=100, total_tokens=200, provenance=ProvenanceStatus.PROVIDER_REPORTED),
            latency=LatencyTelemetry(execution_time_ms=500.0, provenance=ProvenanceStatus.MEASURED),
            environment=EnvironmentalTelemetry(
                energy_joules=6.80, energy_provenance=ProvenanceStatus.ESTIMATED,
                provenance=ProvenanceStatus.ESTIMATED, estimator_name="MLEnergyEstimator"
            )
        )
        sel_rec = TelemetryRecord(
            request_id="sel-1", timestamp="2026-10-13T10:01:00Z", route="Small Model (Groq)",
            provider="groq", model="openai/gpt-oss-20b", success=True,
            tokens=TokenTelemetry(input_tokens=100, output_tokens=50, total_tokens=150, provenance=ProvenanceStatus.PROVIDER_REPORTED),
            latency=LatencyTelemetry(execution_time_ms=200.0, provenance=ProvenanceStatus.MEASURED),
            environment=EnvironmentalTelemetry(
                energy_joules=0.98, energy_provenance=ProvenanceStatus.ESTIMATED,
                provenance=ProvenanceStatus.ESTIMATED, estimator_name="MLEnergyEstimator"
            )
        )

        savings = calculate_savings(selected=sel_rec, baseline=base_rec)
        self.assertEqual(savings.comparison_type, ComparisonType.ESTIMATED_VS_ESTIMATED)
        self.assertEqual(savings.energy_savings.provenance, ProvenanceStatus.ESTIMATED)
        self.assertEqual(savings.energy_savings.savings_value, 5.82)
        self.assertEqual(savings.baseline_estimator, "MLEnergyEstimator")

    def test_pairwise_savings_mixed_provenance(self):
        """One route measured, other estimated -> comparison_type = MIXED_PROVENANCE with qualification."""
        base_rec = TelemetryRecord(
            request_id="base-est", timestamp="2026-10-13T10:00:00Z", route="Large Model (Cloud)",
            provider="groq", model="openai/gpt-oss-120b", success=True,
            tokens=TokenTelemetry(total_tokens=100, provenance=ProvenanceStatus.PROVIDER_REPORTED),
            latency=LatencyTelemetry(execution_time_ms=500.0, provenance=ProvenanceStatus.MEASURED),
            environment=EnvironmentalTelemetry(
                energy_joules=6.80, energy_provenance=ProvenanceStatus.ESTIMATED,
                provenance=ProvenanceStatus.ESTIMATED, estimator_name="MLEnergyEstimator"
            )
        )
        sel_rec = TelemetryRecord(
            request_id="sel-meas", timestamp="2026-10-13T10:01:00Z", route="Small Model (Local GPU)",
            provider="local", model="llama3.1:8b", success=True,
            tokens=TokenTelemetry(total_tokens=50, provenance=ProvenanceStatus.PROVIDER_REPORTED),
            latency=LatencyTelemetry(execution_time_ms=200.0, provenance=ProvenanceStatus.MEASURED),
            environment=EnvironmentalTelemetry(
                energy_joules=1.50, energy_provenance=ProvenanceStatus.MEASURED,
                provenance=ProvenanceStatus.MEASURED
            )
        )

        savings = calculate_savings(selected=sel_rec, baseline=base_rec)
        self.assertEqual(savings.comparison_type, ComparisonType.MIXED_PROVENANCE)
        self.assertEqual(savings.energy_savings.comparison_type, ComparisonType.MIXED_PROVENANCE)
        self.assertIn("Mixed-provenance", savings.notice)
        self.assertTrue(len(savings.limitations) > 0)

    def test_quality_threshold_gate_penalizes_savings(self):
        """When quality_threshold_met is False, savings credit is flagged and notice communicates penalty."""
        base_rec = TelemetryRecord(
            request_id="base-1", timestamp="2026-10-13T10:00:00Z", route="Large Model",
            provider="groq", success=True,
            tokens=TokenTelemetry(total_tokens=100, provenance=ProvenanceStatus.PROVIDER_REPORTED),
            latency=LatencyTelemetry(execution_time_ms=500.0, provenance=ProvenanceStatus.MEASURED),
            environment=EnvironmentalTelemetry(energy_joules=10.0, energy_provenance=ProvenanceStatus.MEASURED, provenance=ProvenanceStatus.MEASURED)
        )
        sel_rec = TelemetryRecord(
            request_id="sel-1", timestamp="2026-10-13T10:01:00Z", route="Small Model",
            provider="local", success=True,
            tokens=TokenTelemetry(total_tokens=50, provenance=ProvenanceStatus.PROVIDER_REPORTED),
            latency=LatencyTelemetry(execution_time_ms=200.0, provenance=ProvenanceStatus.MEASURED),
            environment=EnvironmentalTelemetry(energy_joules=2.0, energy_provenance=ProvenanceStatus.MEASURED, provenance=ProvenanceStatus.MEASURED)
        )

        savings = calculate_savings(selected=sel_rec, baseline=base_rec, quality_threshold_met=False)
        self.assertFalse(savings.quality_threshold_met)
        self.assertIn("Quality threshold not met", savings.notice)
        self.assertIn("Quality degradation penalty", savings.limitations[0])

    # =========================================================================
    # 7. Telemetry & Source API Endpoints Tests
    # =========================================================================

    def test_api_list_sources(self):
        """GET /telemetry/sources returns 200 with all registered sources."""
        resp = self.client.get("/telemetry/sources")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 6)
        ids = [s["source_id"] for s in data]
        self.assertIn("src-mlenergy-leaderboard-v3", ids)

    def test_api_get_source_detail_and_404(self):
        """GET /telemetry/sources/{id} returns details or 404 if not found."""
        resp = self.client.get("/telemetry/sources/src-ecologits-lca-2024")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["source_id"], "src-ecologits-lca-2024")
        self.assertEqual(data["publisher"], "MLCO2 & Data for Good")

        resp_404 = self.client.get("/telemetry/sources/unknown-source-123")
        self.assertEqual(resp_404.status_code, 404)

    def test_api_refresh_sources(self):
        """POST /telemetry/sources/refresh returns audit check results."""
        resp = self.client.post("/telemetry/sources/refresh")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 6)
        self.assertIn("status", data[0])

    def test_api_get_grid_intensity(self):
        """GET /telemetry/grid returns current regional emissions intensity information."""
        with patch.object(settings, "LOCAL_GRID_INTENSITY_GCO2E_PER_KWH", 370.0):
            resp = self.client.get("/telemetry/grid")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["intensity_gco2e_per_kwh"], 370.0)
            self.assertEqual(data["units"], "gCO2e/kWh")

    def test_api_savings_compare_endpoint(self):
        """POST /telemetry/savings/compare correctly invokes upgraded calculate_savings."""
        telemetry_collector.clear()
        base_rec = telemetry_collector.record_success(
            route="Large Model (Groq)", provider="groq", model="test-1", execution_time_ms=500.0,
            token_usage=TokenUsage(prompt_tokens=50, completion_tokens=50, total_tokens=100)
        )
        sel_rec = telemetry_collector.record_success(
            route="Calculator / Deterministic Tool", provider="deterministic", execution_time_ms=0.5,
            token_usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        )

        resp = self.client.post("/telemetry/savings/compare", json={
            "selected_request_id": sel_rec.request_id,
            "baseline_request_id": base_rec.request_id,
            "quality_threshold_met": True
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["model_calls_avoided"], 1)
        self.assertEqual(data["tokens_saved"], 100)
        self.assertEqual(data["energy_savings"]["provenance"], "UNAVAILABLE")
        self.assertIn("Physical environmental savings are UNAVAILABLE", data["notice"])


if __name__ == "__main__":
    unittest.main()

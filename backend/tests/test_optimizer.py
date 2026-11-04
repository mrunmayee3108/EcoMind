"""
EcoMind Phase 6 Test Suite: Multi-Objective Routing Optimizer.

Covers:
1. Task suitability and capability scoring across low, medium, and high complexity.
2. Hard quality constraints (Q >= Q_req; rejecting under-capable models on reasoning tasks).
3. Deterministic tool candidate priority and sub-millisecond execution dominance.
4. Semantic cache candidate evaluation and zero-token dominance.
5. Pareto dominance computation and elimination of dominated candidates.
6. Missing environmental data handling and dynamic weight re-normalization (Non-Zero Rule).
7. Configurable weight sensitivity (Quality vs. Latency vs. Cost vs. Eco).
8. Provider unavailability and graceful failure degradation.
9. Safety fallback when quality constraints are excessively strict.
10. API endpoints (/router/config, /router/optimize, and /chat telemetry integration).
"""

import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from config.settings import settings
from router.query_analyzer import QueryAnalyzer, QueryAnalysis
from router.optimizer import RoutingOptimizer, RouteCandidate, routing_optimizer
from router.routing_policy import RoutingPolicy
from models.provider import ProviderResponse, TokenUsage
from models.dispatcher import ProviderUnavailableError
from telemetry.schemas import ProvenanceStatus
from cache.semantic_cache import semantic_cache


class TestRoutingOptimizer(unittest.TestCase):
    """Unit tests for Phase 6 Multi-Objective Routing Optimizer."""

    def setUp(self):
        semantic_cache.clear()
        self.analyzer = QueryAnalyzer()
        self.optimizer = RoutingOptimizer()
        self.policy = RoutingPolicy(optimizer=self.optimizer)
        self.client = TestClient(app)

    def tearDown(self):
        semantic_cache.clear()

    # =========================================================================
    # 1. Hard Constraints & Quality Threshold Tests
    # =========================================================================

    def test_high_complexity_reasoning_rejects_small_tier(self):
        """Reasoning/derivation tasks enforce Q_req=0.80, eliminating the small model."""
        analysis = self.analyzer.analyze("Compare BFS and DFS and prove why BFS finds shortest path in unweighted graphs.")
        self.assertTrue(analysis.requires_reasoning)
        self.assertEqual(analysis.complexity, "high")

        decision = self.optimizer.optimize(
            query="Compare BFS and DFS and prove why BFS finds shortest path in unweighted graphs.",
            analysis=analysis
        )

        self.assertEqual(decision.quality_threshold, 0.80)
        self.assertIn("Large Model", decision.selected_route)
        self.assertEqual(decision.selected_tier, "large")

        # Verify Small Model was rejected by hard quality constraint
        small_cand = next((c for c in decision.candidates if c.tier == "small"), None)
        self.assertIsNotNone(small_cand)
        self.assertFalse(small_cand.is_hard_constraint_met)
        self.assertIn("below required threshold", small_cand.rejection_reason)

    def test_low_complexity_factual_selects_resource_efficient_route(self):
        """Simple factual tasks enforce Q_req=0.50, allowing small model to win on latency and cost."""
        analysis = self.analyzer.analyze("What is the capital of France?")
        self.assertFalse(analysis.requires_reasoning)
        self.assertEqual(analysis.complexity, "low")

        decision = self.optimizer.optimize(
            query="What is the capital of France?",
            analysis=analysis
        )

        self.assertEqual(decision.quality_threshold, 0.50)
        self.assertIn("Small Model", decision.selected_route)
        self.assertEqual(decision.selected_tier, "small")

        # Small model met hard constraint and was selected
        small_cand = next((c for c in decision.candidates if c.tier == "small"), None)
        self.assertIsNotNone(small_cand)
        self.assertTrue(small_cand.is_hard_constraint_met)
        self.assertTrue(small_cand.is_pareto_optimal)

    def test_medium_complexity_task_routes_to_medium_or_better(self):
        """Medium complexity task (Q_req=0.65) rejects small model (Q=0.60) and selects medium."""
        analysis = self.analyzer.analyze("Summarize the key architectural patterns of microservices.")
        self.assertEqual(analysis.complexity, "medium")

        decision = self.optimizer.optimize(
            query="Summarize the key architectural patterns of microservices.",
            analysis=analysis
        )

        self.assertEqual(decision.quality_threshold, 0.65)
        self.assertEqual(decision.selected_tier, "medium")

    # =========================================================================
    # 2. Deterministic Tools & Semantic Cache Priority
    # =========================================================================

    def test_deterministic_calculator_priority_and_dominance(self):
        """Calculable queries route directly to deterministic tool with perfect quality and zero cost."""
        query = "calculate 45 * 180"
        analysis = self.analyzer.analyze(query)
        self.assertTrue(analysis.requires_tool)
        self.assertEqual(analysis.candidate_tool, "calculator")

        decision = self.optimizer.optimize(
            query=query,
            analysis=analysis,
            candidate_tool_name="calculator"
        )

        self.assertIn("Calculator / Deterministic Tool", decision.selected_route)
        self.assertIsNone(decision.selected_tier)
        self.assertIn("mathematical precision (Quality=1.00)", decision.decision_rationale)
        self.assertEqual(len(decision.hard_constraints_passed), 1)

    def test_semantic_cache_hit_dominance(self):
        """A verified cache hit candidate delivers Q=0.98, zero tokens, and dominates cold inference."""
        query = "Explain TCP vs UDP"
        analysis = self.analyzer.analyze(query)

        decision = self.optimizer.optimize(
            query=query,
            analysis=analysis,
            cache_hit_entry=MagicMock(answer="Cached TCP/UDP answer")
        )

        self.assertEqual(decision.selected_route, "semantic_cache")
        self.assertIn("0 model tokens", decision.decision_rationale)
        self.assertEqual(decision.candidates[0].quality_score, 0.98)

    # =========================================================================
    # 3. Pareto Dominance Evaluation Tests
    # =========================================================================

    def test_pareto_dominance_filters_dominated_candidates(self):
        """Candidate strictly worse across all comparable dimensions is excluded from the Pareto frontier."""
        # Candidate A: high quality, low latency, low cost
        cand_a = RouteCandidate(
            route_name="Candidate A",
            quality_score=0.90,
            expected_latency_ms=200.0,
            estimated_cost_usd=0.0001
        )
        # Candidate B: strictly worse quality, higher latency, higher cost
        cand_b = RouteCandidate(
            route_name="Candidate B",
            quality_score=0.80,
            expected_latency_ms=400.0,
            estimated_cost_usd=0.0005
        )

        pareto = self.optimizer.evaluate_pareto_dominance([cand_a, cand_b])
        self.assertEqual(len(pareto), 1)
        self.assertEqual(pareto[0].route_name, "Candidate A")

    def test_pareto_frontier_preserves_trade_off_candidates(self):
        """Candidates offering different trade-offs (e.g. higher quality vs lower latency) both belong to Pareto frontier."""
        # Candidate Fast: lower quality, much faster
        cand_fast = RouteCandidate(
            route_name="Fast",
            quality_score=0.85,
            expected_latency_ms=150.0,
            estimated_cost_usd=0.00005
        )
        # Candidate Accurate: higher quality, slower, more expensive
        cand_accurate = RouteCandidate(
            route_name="Accurate",
            quality_score=0.95,
            expected_latency_ms=750.0,
            estimated_cost_usd=0.00080
        )

        pareto = self.optimizer.evaluate_pareto_dominance([cand_fast, cand_accurate])
        self.assertEqual(len(pareto), 2)
        names = [c.route_name for c in pareto]
        self.assertIn("Fast", names)
        self.assertIn("Accurate", names)

    # =========================================================================
    # 4. Missing Environmental Data & Dynamic Renormalization
    # =========================================================================

    def test_missing_energy_renormalizes_weights_without_fabrication(self):
        """When energy is UNAVAILABLE, w_E becomes 0 and weights re-normalize over Q, L, and Cost."""
        cands = [
            RouteCandidate(route_name="M1", quality_score=0.85, expected_latency_ms=200.0, estimated_cost_usd=0.0001, energy_joules=None),
            RouteCandidate(route_name="M2", quality_score=0.95, expected_latency_ms=800.0, estimated_cost_usd=0.0005, energy_joules=None)
        ]

        scored, weights, fallback_reason = self.optimizer.compute_scalarized_scores(cands)
        self.assertIsNotNone(fallback_reason)
        self.assertIn("Environmental data UNAVAILABLE", fallback_reason)
        self.assertEqual(weights["environment"], 0.0)

        # Active weights sum to 1.0
        active_sum = round(weights["quality"] + weights["latency"] + weights["cost"], 2)
        self.assertEqual(active_sum, 1.0)

    def test_available_energy_utilizes_full_weighting(self):
        """When empirical energy estimates exist for all candidates, environmental weight is applied."""
        cands = [
            RouteCandidate(route_name="M1", quality_score=0.85, expected_latency_ms=200.0, estimated_cost_usd=0.0001, energy_joules=0.98, energy_provenance=ProvenanceStatus.ESTIMATED),
            RouteCandidate(route_name="M2", quality_score=0.95, expected_latency_ms=800.0, estimated_cost_usd=0.0005, energy_joules=6.80, energy_provenance=ProvenanceStatus.ESTIMATED)
        ]

        scored, weights, fallback_reason = self.optimizer.compute_scalarized_scores(cands)
        self.assertIsNone(fallback_reason)
        self.assertGreater(weights["environment"], 0.0)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=2)

    # =========================================================================
    # 5. Configurable Weights Sensitivity Tests
    # =========================================================================

    def test_latency_prioritized_optimizer(self):
        """Optimizer with high latency weight prefers faster routes."""
        opt_fast = RoutingOptimizer(weight_quality=0.20, weight_latency=0.70, weight_cost=0.10, weight_environment=0.0)
        analysis = QueryAnalysis(task_type="general_qa", complexity="low", requires_tool=False, requires_reasoning=False)

        decision = opt_fast.optimize(query="What is an algorithm?", analysis=analysis)
        self.assertEqual(decision.selected_tier, "small")
        self.assertIn("Small Model", decision.selected_route)

    def test_quality_prioritized_optimizer(self):
        """Optimizer with very high quality weight prefers frontier large models."""
        opt_quality = RoutingOptimizer(weight_quality=0.96, weight_latency=0.02, weight_cost=0.02, weight_environment=0.0)
        analysis = QueryAnalysis(task_type="general_qa", complexity="medium", requires_tool=False, requires_reasoning=False)

        decision = opt_quality.optimize(query="Explain concurrency vs parallelism.", analysis=analysis)
        self.assertEqual(decision.selected_tier, "large")

    # =========================================================================
    # 6. Provider Failure & Safety Fallback Tests
    # =========================================================================

    def test_provider_unavailable_marks_candidate_rejection(self):
        """When a model tier resolves to an unreachable provider, it is excluded with an explicit rejection reason."""
        with patch("router.optimizer.model_dispatcher.get_provider") as mock_get_provider:
            mock_inst = MagicMock()
            mock_inst.get_capabilities.side_effect = ProviderUnavailableError("Connection refused to local daemon at :11434")
            mock_get_provider.return_value = mock_inst

            analysis = QueryAnalysis(task_type="general_qa", complexity="low", requires_tool=False, requires_reasoning=False)
            decision = self.optimizer.optimize(query="test query", analysis=analysis)

            # At least one candidate has provider unavailable error
            unavail_cand = next((c for c in decision.candidates if not c.is_hard_constraint_met and "unavailable" in (c.rejection_reason or "").lower()), None)
            self.assertIsNotNone(unavail_cand)

    def test_safety_fallback_relaxes_impossible_threshold(self):
        """If quality threshold is set higher than any available candidate capability, safety fallback selects highest available."""
        with patch.object(settings, "ROUTER_QUALITY_THRESHOLD_HIGH", 0.999):
            analysis = QueryAnalysis(task_type="reasoning", complexity="high", requires_tool=False, requires_reasoning=True)
            decision = self.optimizer.optimize(query="Hard proof query", analysis=analysis)

            self.assertIsNotNone(decision.selected_route)
            self.assertEqual(decision.selected_tier, "large")
            self.assertIn("safety fallback", (decision.fallback_reason or "").lower())

    # =========================================================================
    # 7. Routing Policy Integration & Backward Compatibility
    # =========================================================================

    def test_routing_policy_select_route_backward_compatibility(self):
        """Existing select_route() method preserves exact backward compatibility."""
        tool_analysis = QueryAnalysis(task_type="calculation", complexity="low", requires_tool=True, requires_reasoning=False, candidate_tool="calculator")
        self.assertEqual(self.policy.select_route(tool_analysis), "calculator")

        high_analysis = QueryAnalysis(task_type="reasoning", complexity="high", requires_tool=False, requires_reasoning=True)
        self.assertEqual(self.policy.select_route(high_analysis), "large")

        med_analysis = QueryAnalysis(task_type="general_qa", complexity="medium", requires_tool=False, requires_reasoning=False)
        self.assertEqual(self.policy.select_route(med_analysis), "medium")

        low_analysis = QueryAnalysis(task_type="general_qa", complexity="low", requires_tool=False, requires_reasoning=False)
        self.assertEqual(self.policy.select_route(low_analysis), "small")

    # =========================================================================
    # 8. API Endpoints Integration Tests
    # =========================================================================

    def test_api_get_router_config(self):
        """GET /router/config returns active weights and quality thresholds."""
        res = self.client.get("/router/config")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["weight_quality"], 0.40)
        self.assertEqual(data["weight_latency"], 0.25)
        self.assertEqual(data["weight_cost"], 0.20)
        self.assertEqual(data["weight_environment"], 0.15)
        self.assertEqual(data["quality_threshold_high"], 0.80)
        self.assertTrue(data["pareto_enabled"])

    def test_api_post_router_optimize_preview(self):
        """POST /router/optimize returns detailed routing decision without executing inference."""
        res = self.client.post("/router/optimize", json={"query": "Compare merge sort and quick sort."})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("selected_route", data)
        self.assertEqual(data["selected_tier"], "large")
        self.assertGreaterEqual(len(data["candidates"]), 3)
        self.assertIn("quality_threshold", data)
        self.assertEqual(data["quality_threshold"], 0.80)
        self.assertTrue(len(data["decision_rationale"]) > 0)

    @patch("api.routes_chat.model_dispatcher.dispatch")
    def test_api_chat_attaches_routing_decision_telemetry(self, mock_dispatch):
        """POST /chat attaches complete routing decision to metadata and telemetry."""
        mock_dispatch.return_value = ProviderResponse(
            content="Binary search operates in O(log n) time.",
            model_name="openai/gpt-oss-20b",
            provider_name="groq",
            latency_ms=20.0,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=15, total_tokens=25)
        )

        res = self.client.post("/chat", json={"query": "What is the time complexity of binary search?"})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("metadata", data)
        self.assertIn("routing_decision", data["metadata"])
        dec = data["metadata"]["routing_decision"]
        self.assertEqual(dec["selected_tier"], "small")
        self.assertIn("decision_rationale", data["metadata"])

        # Telemetry record contains routing_decision
        self.assertIn("telemetry", data)
        self.assertIsNotNone(data["telemetry"]["routing_decision"])
        self.assertEqual(data["telemetry"]["routing_decision"]["selected_tier"], "small")


if __name__ == "__main__":
    unittest.main()

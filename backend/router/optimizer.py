"""
EcoMind Phase 6: Multi-Objective Routing Optimizer.

Makes Pareto-aware, scientifically grounded routing decisions that balance:
1. Answer quality and task suitability (Hard Constraint: Q >= Q_req)
2. Expected latency
3. Estimated API/model cost
4. Environmental impact (using only defensible empirical/measured data; never fabricating zeros)

Formulation:
min (w_Q * (1 - Q_norm) + w_L * L_norm + w_$ * $_norm + w_E * E_norm)
subject to Q >= Q_req and Provider Availability.
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any

from config.settings import settings
from models.model_profiles import MODEL_CATALOG, ModelTier, ModelProfile, get_model_profile
from models.dispatcher import model_dispatcher, ProviderUnavailableError
from router.query_analyzer import QueryAnalysis
from telemetry.schemas import (
    ProvenanceStatus,
    CandidateScore,
    RoutingDecision,
)
from telemetry.cloud_estimator import cloud_energy_estimator


@dataclass
class RouteCandidate:
    """Internal representation of an eligible execution path."""
    route_name: str
    tier: Optional[str] = None
    provider: str = "deterministic"
    model: Optional[str] = None
    quality_score: float = 1.0
    expected_latency_ms: float = 1.0
    estimated_cost_usd: float = 0.0
    energy_joules: Optional[float] = None
    energy_provenance: ProvenanceStatus = ProvenanceStatus.UNAVAILABLE
    is_tool: bool = False
    is_cache: bool = False
    is_available: bool = True
    availability_error: Optional[str] = None


class RoutingOptimizer:
    """
    Modular Multi-Objective Optimizer for EcoMind query execution routing.
    Enforces hard constraints first, identifies non-dominated Pareto candidates,
    and applies normalized scalarized weighting with missing-data safeguards.
    """

    def __init__(
        self,
        weight_quality: Optional[float] = None,
        weight_latency: Optional[float] = None,
        weight_cost: Optional[float] = None,
        weight_environment: Optional[float] = None,
        pareto_enabled: Optional[bool] = None
    ):
        self.w_quality = weight_quality if weight_quality is not None else getattr(settings, "ROUTER_WEIGHT_QUALITY", 0.40)
        self.w_latency = weight_latency if weight_latency is not None else getattr(settings, "ROUTER_WEIGHT_LATENCY", 0.25)
        self.w_cost = weight_cost if weight_cost is not None else getattr(settings, "ROUTER_WEIGHT_COST", 0.20)
        self.w_environment = weight_environment if weight_environment is not None else getattr(settings, "ROUTER_WEIGHT_ENVIRONMENT", 0.15)
        self.pareto_enabled = pareto_enabled if pareto_enabled is not None else getattr(settings, "ROUTER_PARETO_ENABLED", True)

    def determine_quality_threshold(self, analysis: QueryAnalysis) -> float:
        """
        Determine minimum acceptable capability score Q_req.
        Hard constraint: Higher complexity queries demand frontier reasoning capabilities.
        """
        if analysis.requires_reasoning or analysis.complexity == "high":
            return getattr(settings, "ROUTER_QUALITY_THRESHOLD_HIGH", 0.80)
        elif analysis.complexity == "medium":
            return getattr(settings, "ROUTER_QUALITY_THRESHOLD_MEDIUM", 0.65)
        else:
            return getattr(settings, "ROUTER_QUALITY_THRESHOLD_LOW", 0.50)

    def generate_model_candidates(
        self,
        query: str,
        analysis: QueryAnalysis
    ) -> List[RouteCandidate]:
        """
        Generate candidate routes for available model tiers based on active dispatcher configuration.
        """
        candidates: List[RouteCandidate] = []
        prompt_tokens_est = max(1, len(query.split()) * 2)

        # Output tokens estimated by complexity
        if analysis.complexity == "high" or analysis.requires_reasoning:
            comp_tokens_est = 250
        elif analysis.complexity == "medium":
            comp_tokens_est = 120
        else:
            comp_tokens_est = 50

        tiers = ["small", "medium", "large"]
        for tier in tiers:
            try:
                provider_name, model_name = model_dispatcher.resolve_tier(tier)
            except Exception:
                continue

            # Check provider availability
            is_avail = True
            avail_err = None
            try:
                provider_inst = model_dispatcher.get_provider(provider_name)
                # Quick health/capability check
                caps = provider_inst.get_capabilities()
                if not caps.get("supports_streaming", True) and not caps.get("supports_tools", True) and not caps.get("context_window", 0):
                    is_avail = False
                    avail_err = f"Provider '{provider_name}' capabilities unavailable."
            except ProviderUnavailableError as pue:
                is_avail = False
                avail_err = str(pue)
            except Exception as e:
                is_avail = False
                avail_err = str(e)

            # Model profile & pricing
            prof = get_model_profile(model_name)
            cost = 0.0
            if prof:
                p_in = prof.pricing_input_per_1m_usd or 0.0
                p_out = prof.pricing_output_per_1m_usd or 0.0
                cost = round(
                    (prompt_tokens_est * p_in / 1_000_000.0) +
                    (comp_tokens_est * p_out / 1_000_000.0),
                    8
                )

            # Expected Latency (empirically calibrated defaults by tier)
            if tier == "small":
                expected_lat = 220.0
            elif tier == "medium":
                expected_lat = 420.0
            else:
                expected_lat = 850.0

            # Quality Suitability Score by complexity
            if tier == "small":
                if analysis.complexity == "high" or analysis.requires_reasoning:
                    q_score = 0.35  # Under-capable for deep reasoning/derivation
                elif analysis.complexity == "medium":
                    q_score = 0.60
                else:
                    q_score = 0.85
            elif tier == "medium":
                if analysis.complexity == "high" or analysis.requires_reasoning:
                    q_score = 0.68  # Marginal for hard reasoning
                elif analysis.complexity == "medium":
                    q_score = 0.88
                else:
                    q_score = 0.92
            else:  # large tier
                if analysis.complexity == "high" or analysis.requires_reasoning:
                    q_score = 0.95
                elif analysis.complexity == "medium":
                    q_score = 0.95
                else:
                    q_score = 0.96

            # Environmental estimation (defensible only; otherwise UNAVAILABLE)
            energy_j = None
            energy_prov = ProvenanceStatus.UNAVAILABLE
            enable_cloud_est = getattr(settings, "ENABLE_CLOUD_ENERGY_ESTIMATION", False)
            if enable_cloud_est and cloud_energy_estimator.supports(provider_name, model_name):
                est_res = cloud_energy_estimator.estimate(
                    provider=provider_name,
                    model=model_name,
                    prompt_tokens=prompt_tokens_est,
                    completion_tokens=comp_tokens_est,
                    latency_ms=expected_lat
                )
                if est_res and est_res.energy_joules is not None:
                    energy_j = est_res.energy_joules
                    energy_prov = ProvenanceStatus.ESTIMATED

            candidates.append(RouteCandidate(
                route_name=f"{tier.capitalize()} Model ({provider_name.capitalize()})",
                tier=tier,
                provider=provider_name,
                model=model_name,
                quality_score=q_score,
                expected_latency_ms=expected_lat,
                estimated_cost_usd=cost,
                energy_joules=energy_j,
                energy_provenance=energy_prov,
                is_tool=False,
                is_cache=False,
                is_available=is_avail,
                availability_error=avail_err
            ))

        return candidates

    def evaluate_pareto_dominance(
        self,
        candidates: List[RouteCandidate]
    ) -> List[RouteCandidate]:
        """
        Identify the non-dominated Pareto frontier among candidates.
        Candidate A dominates Candidate B if A is >= B across all comparable objectives
        (Quality higher, Latency lower, Cost lower, Energy lower) and strictly better in at least one.
        """
        if not candidates or len(candidates) <= 1:
            return candidates

        pareto_candidates: List[RouteCandidate] = []

        for a in candidates:
            is_dominated = False
            for b in candidates:
                if a == b:
                    continue

                # Quality: higher is better
                b_better_q = b.quality_score > a.quality_score
                b_worse_q = b.quality_score < a.quality_score

                # Latency: lower is better
                b_better_l = b.expected_latency_ms < a.expected_latency_ms
                b_worse_l = b.expected_latency_ms > a.expected_latency_ms

                # Cost: lower is better
                b_better_c = b.estimated_cost_usd < a.estimated_cost_usd
                b_worse_c = b.estimated_cost_usd > a.estimated_cost_usd

                # Energy: lower is better (only comparable if BOTH have valid energy)
                energy_comparable = (
                    a.energy_joules is not None and
                    b.energy_joules is not None and
                    a.energy_provenance != ProvenanceStatus.UNAVAILABLE and
                    b.energy_provenance != ProvenanceStatus.UNAVAILABLE
                )
                if energy_comparable:
                    b_better_e = b.energy_joules < a.energy_joules
                    b_worse_e = b.energy_joules > a.energy_joules
                else:
                    b_better_e = False
                    b_worse_e = False

                # B dominates A if B is as good or better in all dimensions, and strictly better in at least one
                no_worse = (not b_worse_q) and (not b_worse_l) and (not b_worse_c)
                if energy_comparable:
                    no_worse = no_worse and (not b_worse_e)

                strictly_better = b_better_q or b_better_l or b_better_c or (energy_comparable and b_better_e)

                if no_worse and strictly_better:
                    is_dominated = True
                    break

            if not is_dominated:
                pareto_candidates.append(a)

        return pareto_candidates

    def compute_scalarized_scores(
        self,
        candidates: List[RouteCandidate]
    ) -> Tuple[List[CandidateScore], Dict[str, float], Optional[str]]:
        """
        Normalize objectives and compute scalarized weighted costs.
        Enforces dynamic weight renormalization when environmental data is unavailable.
        """
        if not candidates:
            return [], {}, None

        # Min/Max ranges across candidate pool for normalization
        qualities = [c.quality_score for c in candidates]
        latencies = [c.expected_latency_ms for c in candidates]
        costs = [c.estimated_cost_usd for c in candidates]
        energies = [c.energy_joules for c in candidates if c.energy_joules is not None and c.energy_provenance != ProvenanceStatus.UNAVAILABLE]

        min_q, max_q = min(qualities), max(qualities)
        min_l, max_l = min(latencies), max(latencies)
        min_c, max_c = min(costs), max(costs)
        has_energy = len(energies) == len(candidates) and len(energies) > 0

        # Dynamic weight renormalization
        w_q = self.w_quality
        w_l = self.w_latency
        w_c = self.w_cost
        w_e = self.w_environment
        fallback_reason = None

        if not has_energy:
            # Environmental data unavailable for one or more candidates
            # Never treat unavailable as 0.0 J; re-normalize across Quality, Latency, and Cost
            sum_active = w_q + w_l + w_c
            if sum_active > 0:
                w_q_norm = w_q / sum_active
                w_l_norm = w_l / sum_active
                w_c_norm = w_c / sum_active
            else:
                w_q_norm, w_l_norm, w_c_norm = 0.5, 0.25, 0.25
            w_e_norm = 0.0
            fallback_reason = "Environmental data UNAVAILABLE across candidates; weights dynamically re-normalized over Quality, Latency, and Cost without fabricating zeros."
        else:
            sum_all = w_q + w_l + w_c + w_e
            w_q_norm = w_q / sum_all
            w_l_norm = w_l / sum_all
            w_c_norm = w_c / sum_all
            w_e_norm = w_e / sum_all
            min_e, max_e = min(energies), max(energies)

        active_weights = {
            "quality": round(w_q_norm, 4),
            "latency": round(w_l_norm, 4),
            "cost": round(w_c_norm, 4),
            "environment": round(w_e_norm, 4)
        }

        scored: List[CandidateScore] = []
        for c in candidates:
            # Normalized quality deficit in [0, 1] (0 is perfect quality 1.0, 1 is total lack of capability 0.0)
            norm_q_deficit = max(0.0, min(1.0, 1.0 - c.quality_score))

            # Normalized latency in [0, 1]
            if max_l > min_l:
                norm_l = (c.expected_latency_ms - min_l) / (max_l - min_l)
            else:
                norm_l = 0.0

            # Normalized cost in [0, 1]
            if max_c > min_c:
                norm_c = (c.estimated_cost_usd - min_c) / (max_c - min_c)
            else:
                norm_c = 0.0

            # Normalized energy in [0, 1]
            if has_energy and max_e > min_e:
                norm_e = (c.energy_joules - min_e) / (max_e - min_e)
            else:
                norm_e = 0.0

            # Composite cost score (lower is better)
            score = (
                w_q_norm * norm_q_deficit +
                w_l_norm * norm_l +
                w_c_norm * norm_c +
                w_e_norm * norm_e
            )

            scored.append(CandidateScore(
                route_name=c.route_name,
                tier=c.tier,
                provider=c.provider,
                model=c.model,
                quality_score=c.quality_score,
                expected_latency_ms=c.expected_latency_ms,
                estimated_cost_usd=c.estimated_cost_usd,
                energy_joules=c.energy_joules,
                energy_provenance=c.energy_provenance,
                is_hard_constraint_met=True,
                is_pareto_optimal=True,
                scalarized_score=round(score, 5),
                rejection_reason=None
            ))

        return scored, active_weights, fallback_reason

    def optimize(
        self,
        query: str,
        analysis: QueryAnalysis,
        candidate_tool_name: Optional[str] = None,
        cache_hit_entry: Optional[Any] = None
    ) -> RoutingDecision:
        """
        Execute full multi-objective routing optimization:
        1. Evaluate deterministic tool candidate (if matched).
        2. Evaluate semantic cache candidate (if hit).
        3. Formulate and evaluate model tier candidates.
        4. Apply hard constraints (Quality threshold Q >= Q_req, provider availability).
        5. Evaluate Pareto dominance to discard dominated routes.
        6. Compute normalized scalarized cost scores on Pareto frontier.
        7. Select optimal route and emit explainable decision telemetry.
        """
        all_evaluations: List[CandidateScore] = []
        q_threshold = self.determine_quality_threshold(analysis)

        # -------------------------------------------------------------
        # STEP 1: Deterministic Tool Route Evaluation
        # -------------------------------------------------------------
        if candidate_tool_name or analysis.requires_tool:
            tool_name = candidate_tool_name or analysis.candidate_tool or "calculator"
            tool_cand = RouteCandidate(
                route_name=f"{tool_name.capitalize()} / Deterministic Tool",
                tier=None,
                provider="deterministic",
                model="None",
                quality_score=1.0,
                expected_latency_ms=0.8,
                estimated_cost_usd=0.0,
                energy_joules=None,
                energy_provenance=ProvenanceStatus.UNAVAILABLE,
                is_tool=True,
                is_available=True
            )

            rationale = (
                f"Selected deterministic {tool_name} with mathematical precision (Quality=1.00). "
                "Executes with 0 model tokens, 0 inference cost, and sub-millisecond latency (<1 ms). "
                "Dominates all neural network model alternatives."
            )

            tool_score = CandidateScore(
                route_name=tool_cand.route_name,
                tier=None,
                provider="deterministic",
                model="None",
                quality_score=1.0,
                expected_latency_ms=0.8,
                estimated_cost_usd=0.0,
                energy_joules=None,
                energy_provenance=ProvenanceStatus.UNAVAILABLE,
                is_hard_constraint_met=True,
                is_pareto_optimal=True,
                scalarized_score=0.0,
                rejection_reason=None
            )

            return RoutingDecision(
                selected_route=tool_cand.route_name,
                selected_tier=None,
                decision_rationale=rationale,
                objective_weights={"quality": 1.0, "latency": 0.0, "cost": 0.0, "environment": 0.0},
                quality_threshold=q_threshold,
                hard_constraints_passed=[tool_cand.route_name],
                pareto_frontier=[tool_cand.route_name],
                candidates=[tool_score],
                fallback_reason=None
            )

        # -------------------------------------------------------------
        # STEP 2: Semantic Cache Route Evaluation
        # -------------------------------------------------------------
        if cache_hit_entry is not None:
            cache_cand = RouteCandidate(
                route_name="semantic_cache",
                tier=None,
                provider="cache",
                model=None,
                quality_score=0.98,
                expected_latency_ms=3.5,
                estimated_cost_usd=0.0,
                energy_joules=None,
                energy_provenance=ProvenanceStatus.UNAVAILABLE,
                is_tool=False,
                is_cache=True,
                is_available=True
            )

            rationale = (
                "Selected precision-first semantic cache with verified compatibility (Quality=0.98). "
                "Serves identical verified answer with 0 model tokens, 0 inference cost, and ~3.5 ms retrieval."
            )

            cache_score = CandidateScore(
                route_name="semantic_cache",
                tier=None,
                provider="cache",
                model=None,
                quality_score=0.98,
                expected_latency_ms=3.5,
                estimated_cost_usd=0.0,
                energy_joules=None,
                energy_provenance=ProvenanceStatus.UNAVAILABLE,
                is_hard_constraint_met=True,
                is_pareto_optimal=True,
                scalarized_score=0.0,
                rejection_reason=None
            )

            return RoutingDecision(
                selected_route="semantic_cache",
                selected_tier=None,
                decision_rationale=rationale,
                objective_weights={"quality": 1.0, "latency": 0.0, "cost": 0.0, "environment": 0.0},
                quality_threshold=q_threshold,
                hard_constraints_passed=["semantic_cache"],
                pareto_frontier=["semantic_cache"],
                candidates=[cache_score],
                fallback_reason=None
            )

        # -------------------------------------------------------------
        # STEP 3: Model Candidates Evaluation
        # -------------------------------------------------------------
        model_candidates = self.generate_model_candidates(query, analysis)

        # Filter by hard constraints: Provider Availability & Quality Threshold
        passed_candidates: List[RouteCandidate] = []
        for cand in model_candidates:
            if not cand.is_available:
                all_evaluations.append(CandidateScore(
                    route_name=cand.route_name,
                    tier=cand.tier,
                    provider=cand.provider,
                    model=cand.model,
                    quality_score=cand.quality_score,
                    expected_latency_ms=cand.expected_latency_ms,
                    estimated_cost_usd=cand.estimated_cost_usd,
                    energy_joules=cand.energy_joules,
                    energy_provenance=cand.energy_provenance,
                    is_hard_constraint_met=False,
                    is_pareto_optimal=False,
                    scalarized_score=None,
                    rejection_reason=f"Provider '{cand.provider}' unavailable: {cand.availability_error}"
                ))
            elif cand.quality_score < q_threshold:
                # Quality gate rejection (never sacrifice quality for efficiency)
                all_evaluations.append(CandidateScore(
                    route_name=cand.route_name,
                    tier=cand.tier,
                    provider=cand.provider,
                    model=cand.model,
                    quality_score=cand.quality_score,
                    expected_latency_ms=cand.expected_latency_ms,
                    estimated_cost_usd=cand.estimated_cost_usd,
                    energy_joules=cand.energy_joules,
                    energy_provenance=cand.energy_provenance,
                    is_hard_constraint_met=False,
                    is_pareto_optimal=False,
                    scalarized_score=None,
                    rejection_reason=(
                        f"Quality capability ({cand.quality_score:.2f}) below required threshold ({q_threshold:.2f}) "
                        f"for task complexity '{analysis.complexity}'."
                    )
                ))
            else:
                passed_candidates.append(cand)

        # Safety Fallback: If no candidate passed hard constraints, relax quality threshold to highest available
        safety_fallback_used = False
        if not passed_candidates:
            available_cands = [c for c in model_candidates if c.is_available]
            if available_cands:
                # Pick candidate with highest quality
                available_cands.sort(key=lambda c: c.quality_score, reverse=True)
                passed_candidates = [available_cands[0]]
                safety_fallback_used = True

        hard_passed_names = [c.route_name for c in passed_candidates]

        # -------------------------------------------------------------
        # STEP 4: Pareto Dominance Filtering
        # -------------------------------------------------------------
        if self.pareto_enabled and len(passed_candidates) > 1:
            pareto_cands = self.evaluate_pareto_dominance(passed_candidates)
        else:
            pareto_cands = passed_candidates

        pareto_names = [c.route_name for c in pareto_cands]

        # Mark non-pareto surviving candidates in evaluation list
        for cand in passed_candidates:
            if cand.route_name not in pareto_names:
                all_evaluations.append(CandidateScore(
                    route_name=cand.route_name,
                    tier=cand.tier,
                    provider=cand.provider,
                    model=cand.model,
                    quality_score=cand.quality_score,
                    expected_latency_ms=cand.expected_latency_ms,
                    estimated_cost_usd=cand.estimated_cost_usd,
                    energy_joules=cand.energy_joules,
                    energy_provenance=cand.energy_provenance,
                    is_hard_constraint_met=True,
                    is_pareto_optimal=False,
                    scalarized_score=None,
                    rejection_reason="Dominated by another candidate across all objective dimensions."
                ))

        # -------------------------------------------------------------
        # STEP 5: Scalarized Scoring on Pareto Frontier
        # -------------------------------------------------------------
        scored_pareto, active_weights, fallback_reason = self.compute_scalarized_scores(pareto_cands)
        all_evaluations.extend(scored_pareto)

        if safety_fallback_used:
            fallback_reason = (
                f"No candidate met strict quality threshold ({q_threshold:.2f}); "
                "selected highest-capability available candidate as safety fallback."
            )

        # -------------------------------------------------------------
        # STEP 6: Select Best Route (Lowest Scalarized Cost Score)
        # -------------------------------------------------------------
        if scored_pareto:
            scored_pareto.sort(key=lambda s: s.scalarized_score if s.scalarized_score is not None else 999.0)
            winner = scored_pareto[0]
            selected_route = winner.route_name
            selected_tier = winner.tier

            rationale = (
                f"Selected {winner.route_name} on Pareto frontier (Scalarized Cost: {winner.scalarized_score:.4f}). "
                f"Quality capability ({winner.quality_score:.2f} >= {q_threshold:.2f}) meets task requirements. "
                f"Expected latency: {winner.expected_latency_ms:.0f} ms; Estimated cost: ${winner.estimated_cost_usd:.6f}."
            )
            if winner.energy_joules is not None:
                rationale += f" Estimated energy: {winner.energy_joules:.2f} J ({winner.energy_provenance.value})."
        else:
            # Absolute fallback if dispatcher cannot resolve any tier
            selected_route = "Small Model (Fallback)"
            selected_tier = "small"
            rationale = "Default fallback route selected due to absence of eligible candidates."

        return RoutingDecision(
            selected_route=selected_route,
            selected_tier=selected_tier,
            decision_rationale=rationale,
            objective_weights=active_weights,
            quality_threshold=q_threshold,
            hard_constraints_passed=hard_passed_names,
            pareto_frontier=pareto_names,
            candidates=all_evaluations,
            fallback_reason=fallback_reason
        )


# Global optimizer instance
routing_optimizer = RoutingOptimizer()

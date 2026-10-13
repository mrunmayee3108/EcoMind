"""
EcoMind Phase 5B: Pair-Wise Environmental Savings Integrity Engine.

Upgraded to support:
- Strict Pair-Wise Non-Zero Rule for physical environmental metrics.
- Explicit comparison classification:
  * MEASURED_VS_MEASURED (direct sensor readings in matching scope)
  * ESTIMATED_VS_ESTIMATED (modeled estimates under comparable methodology)
  * MIXED_PROVENANCE (direct sensor vs modeled estimate with explicit caution)
  * UNAVAILABLE (missing data or unmeasured metrics)
- Preservation of authentic operational proxies (model calls avoided, tokens saved, latency).
- Quality threshold gating (penalizing routes failing minimum quality).
- Zero fabrication of physical savings merely because a model call was avoided.
"""

from typing import Optional, List
from .schemas import (
    ProvenanceStatus,
    MeasurementScope,
    ComparisonType,
    MetricSavings,
    SavingsComparison,
    TelemetryRecord,
)


def calculate_savings(
    selected: TelemetryRecord,
    baseline: TelemetryRecord,
    quality_threshold_met: bool = True
) -> SavingsComparison:
    """
    Compute pair-wise savings between an executed route and an explicit baseline route.
    Enforces the Non-Zero Rule, classifies comparison reliability, and verifies quality gates.
    """
    limitations: List[str] = []

    # 1. Operational Proxies: Model Calls Avoided
    if selected.provider in ("deterministic", "cache"):
        model_calls_avoided = 1
    else:
        model_calls_avoided = 0

    # 2. Operational Proxies: Tokens Saved
    tokens_saved: Optional[int] = None
    tokens_prov = ProvenanceStatus.UNAVAILABLE
    if baseline.tokens.total_tokens is not None and selected.tokens.total_tokens is not None:
        tokens_saved = baseline.tokens.total_tokens - selected.tokens.total_tokens
        if selected.tokens.provenance == ProvenanceStatus.MEASURED:
            tokens_prov = ProvenanceStatus.MEASURED
        else:
            tokens_prov = ProvenanceStatus.PROVIDER_REPORTED
    elif baseline.tokens.total_tokens is not None and selected.provider in ("deterministic", "cache"):
        tokens_saved = baseline.tokens.total_tokens
        tokens_prov = ProvenanceStatus.MEASURED

    # 3. Latency Delta
    latency_delta_ms = round(baseline.latency.execution_time_ms - selected.latency.execution_time_ms, 2)

    # 4. Energy Savings Evaluation
    sel_energy = selected.environment.energy_joules
    base_energy = baseline.environment.energy_joules
    sel_energy_prov = getattr(selected.environment, "energy_provenance", selected.environment.provenance)
    base_energy_prov = getattr(baseline.environment, "energy_provenance", baseline.environment.provenance)

    if (
        sel_energy is None or
        base_energy is None or
        sel_energy_prov == ProvenanceStatus.UNAVAILABLE or
        base_energy_prov == ProvenanceStatus.UNAVAILABLE
    ):
        energy_savings = MetricSavings(
            baseline_value=base_energy,
            selected_value=sel_energy,
            savings_value=None,
            savings_pct=None,
            unit="J",
            provenance=ProvenanceStatus.UNAVAILABLE,
            scope=None,
            comparison_type=ComparisonType.UNAVAILABLE,
            note="Energy savings UNAVAILABLE: at least one route lacks physical energy measurement. Unmeasured metrics are never treated as zero."
        )
    else:
        delta_j = round(base_energy - sel_energy, 4)
        pct = round((delta_j / base_energy) * 100, 2) if base_energy > 0 else 0.0

        # Determine comparison type and scope
        sel_scope = selected.environment.measurement.scope if selected.environment.measurement else None
        base_scope = baseline.environment.measurement.scope if baseline.environment.measurement else None
        shared_scope = sel_scope if sel_scope == base_scope else None

        if sel_energy_prov == ProvenanceStatus.MEASURED and base_energy_prov == ProvenanceStatus.MEASURED:
            comp_type = ComparisonType.MEASURED_VS_MEASURED
            res_prov = ProvenanceStatus.MEASURED
            unc_info = "Direct physical energy differential measured via hardware sensors."
            note_str = "Physical energy differential directly measured between routes."
        elif sel_energy_prov == ProvenanceStatus.ESTIMATED and base_energy_prov == ProvenanceStatus.ESTIMATED:
            comp_type = ComparisonType.ESTIMATED_VS_ESTIMATED
            res_prov = ProvenanceStatus.ESTIMATED
            unc_info = "Estimate-versus-estimate comparison; subject to underlying methodology assumptions."
            note_str = "Estimated energy savings derived from verified scientific estimation models."
        else:
            comp_type = ComparisonType.MIXED_PROVENANCE
            res_prov = ProvenanceStatus.ESTIMATED
            unc_info = f"Mixed provenance comparison: baseline is {base_energy_prov} and selected is {sel_energy_prov}."
            note_str = (
                f"Mixed-provenance comparison ({base_energy_prov} baseline vs {sel_energy_prov} selected). "
                "Direct hardware sensor telemetry is compared against a modeled estimate; interpret with caution."
            )
            limitations.append("Mixed provenance comparison: physical measurement compared against modeled estimate.")

        energy_savings = MetricSavings(
            baseline_value=base_energy,
            selected_value=sel_energy,
            savings_value=delta_j,
            savings_pct=pct,
            unit="J",
            provenance=res_prov,
            scope=shared_scope,
            comparison_type=comp_type,
            uncertainty_info=unc_info,
            note=note_str
        )

    # 5. Water Savings Evaluation (Strictly UNAVAILABLE - Zero Fabrication)
    water_savings = MetricSavings(
        baseline_value=None,
        selected_value=None,
        savings_value=None,
        savings_pct=None,
        unit="L",
        provenance=ProvenanceStatus.UNAVAILABLE,
        scope=None,
        comparison_type=ComparisonType.UNAVAILABLE,
        uncertainty_info="Water savings UNAVAILABLE across all routes in Phase 5B (zero fabrication).",
        note="Cloud providers and local client execution lack verified per-request water telemetry."
    )

    # 6. Carbon Savings Evaluation
    sel_carbon = selected.environment.carbon_gco2e
    base_carbon = baseline.environment.carbon_gco2e
    sel_carbon_prov = getattr(selected.environment, "carbon_provenance", ProvenanceStatus.UNAVAILABLE)
    base_carbon_prov = getattr(baseline.environment, "carbon_provenance", ProvenanceStatus.UNAVAILABLE)

    if (
        sel_carbon is None or
        base_carbon is None or
        sel_carbon_prov == ProvenanceStatus.UNAVAILABLE or
        base_carbon_prov == ProvenanceStatus.UNAVAILABLE
    ):
        carbon_savings = MetricSavings(
            baseline_value=base_carbon,
            selected_value=sel_carbon,
            savings_value=None,
            savings_pct=None,
            unit="gCO2e",
            provenance=ProvenanceStatus.UNAVAILABLE,
            scope=None,
            comparison_type=ComparisonType.UNAVAILABLE,
            uncertainty_info="Carbon savings UNAVAILABLE: at least one route lacks authentic carbon calculation.",
            note="Operational carbon calculation requires valid energy and verified regional grid intensity."
        )
    else:
        delta_c = round(base_carbon - sel_carbon, 6)
        pct_c = round((delta_c / base_carbon) * 100, 2) if base_carbon > 0 else 0.0

        if sel_carbon_prov == ProvenanceStatus.MEASURED and base_carbon_prov == ProvenanceStatus.MEASURED:
            comp_type_c = ComparisonType.MEASURED_VS_MEASURED
            prov_c = ProvenanceStatus.MEASURED
        elif sel_carbon_prov == ProvenanceStatus.ESTIMATED and base_carbon_prov == ProvenanceStatus.ESTIMATED:
            comp_type_c = ComparisonType.ESTIMATED_VS_ESTIMATED
            prov_c = ProvenanceStatus.ESTIMATED
        else:
            comp_type_c = ComparisonType.MIXED_PROVENANCE
            prov_c = ProvenanceStatus.ESTIMATED

        carbon_savings = MetricSavings(
            baseline_value=base_carbon,
            selected_value=sel_carbon,
            savings_value=delta_c,
            savings_pct=pct_c,
            unit="gCO2e",
            provenance=prov_c,
            scope=MeasurementScope.GPU_BOARD_OPERATIONAL_CARBON,
            comparison_type=comp_type_c,
            uncertainty_info="Derived from measured/estimated energy and regional electricity grid emissions factor.",
            note="Operational carbon savings strictly scoped to GPU board / compute window."
        )

    # 7. Overall Comparison Type Resolution
    if energy_savings.comparison_type:
        overall_comp_type = energy_savings.comparison_type
    else:
        overall_comp_type = ComparisonType.UNAVAILABLE

    # 8. Formulate Overall Integrity Notice & Quality Gate
    if not quality_threshold_met:
        limitations.append("Quality degradation penalty: selected route failed minimum acceptable accuracy threshold.")
        notice = "Quality threshold not met by selected route. Resource savings cannot be credited without accounting for the quality degradation penalty."
    elif energy_savings.provenance == ProvenanceStatus.UNAVAILABLE:
        notice = "Physical environmental savings are UNAVAILABLE for this comparison (zero fabrication). Authentic operational proxies (model calls avoided, tokens avoided, latency) are reported."
    elif overall_comp_type == ComparisonType.MIXED_PROVENANCE:
        notice = "Mixed-provenance environmental savings computed. A direct sensor measurement is compared with a modeled estimate; interpret with caution."
    elif overall_comp_type == ComparisonType.ESTIMATED_VS_ESTIMATED:
        notice = "Estimated environmental savings computed from verified scientific estimation models and authentic token metadata."
    else:
        notice = "Environmental savings computed from authentic physical measurements and configured operational parameters."

    baseline_estimator = getattr(baseline.environment, "estimator_name", None) or getattr(baseline.environment, "source_id", None)
    selected_estimator = getattr(selected.environment, "estimator_name", None) or getattr(selected.environment, "source_id", None)

    return SavingsComparison(
        selected_route=selected.route,
        baseline_route=baseline.route,
        quality_threshold_met=quality_threshold_met,
        comparison_type=overall_comp_type,
        baseline_estimator=baseline_estimator,
        selected_estimator=selected_estimator,
        limitations=limitations,
        model_calls_avoided=model_calls_avoided,
        tokens_saved=tokens_saved,
        tokens_provenance=tokens_prov,
        latency_delta_ms=latency_delta_ms,
        energy_savings=energy_savings,
        water_savings=water_savings,
        carbon_savings=carbon_savings,
        notice=notice
    )

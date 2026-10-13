"""
EcoMind Phase 5B: Pair-Wise Environmental Savings Integrity Engine.

Enforces the Pair-Wise Non-Zero Rule:
If either route in a comparison lacks authentic physical measurements
(ProvenanceStatus.UNAVAILABLE or None), environmental savings are strictly
marked UNAVAILABLE. Unmeasured metrics are NEVER treated as zero, and
environmental savings are NEVER fabricated.

Genuine operational proxies (model calls avoided, tokens avoided, latency)
are reported as factual proxies when applicable.
"""

from typing import Optional
from .schemas import (
    ProvenanceStatus,
    MeasurementScope,
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
    Strictly enforces the Non-Zero Rule for environmental metrics:
    - If either route's energy is UNAVAILABLE/None, energy_savings is UNAVAILABLE.
    - If either route's carbon is UNAVAILABLE/None, carbon_savings is UNAVAILABLE.
    - Water savings is UNAVAILABLE across all routes (zero fabrication).
    - Operational facts (model calls avoided, tokens saved, latency delta) are reported as authentic proxies.
    - If quality_threshold_met is False, savings credit is flagged with a quality degradation penalty.
    """
    # 1. Operational Proxies: Model Calls Avoided
    if selected.provider in ("deterministic", "cache"):
        model_calls_avoided = 1
    else:
        # If selected is also a model call, 0 calls avoided (even if smaller tier)
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

    # 4. Energy Savings (Pair-Wise Non-Zero Rule)
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
            note="Energy savings UNAVAILABLE: at least one route lacks physical energy measurement. Unmeasured metrics are never treated as zero."
        )
    else:
        delta_j = base_energy - sel_energy
        pct = round((delta_j / base_energy) * 100, 2) if base_energy > 0 else 0.0
        shared_scope = (
            selected.environment.measurement.scope
            if selected.environment.measurement and baseline.environment.measurement and
               selected.environment.measurement.scope == baseline.environment.measurement.scope
            else None
        )
        energy_savings = MetricSavings(
            baseline_value=base_energy,
            selected_value=sel_energy,
            savings_value=round(delta_j, 4),
            savings_pct=pct,
            unit="J",
            provenance=ProvenanceStatus.MEASURED,
            scope=shared_scope,
            note="Physical energy differential directly measured between routes."
        )

    # 5. Water Savings (Always UNAVAILABLE - Zero Fabrication)
    water_savings = MetricSavings(
        baseline_value=None,
        selected_value=None,
        savings_value=None,
        savings_pct=None,
        unit="L",
        provenance=ProvenanceStatus.UNAVAILABLE,
        scope=None,
        note="Water savings UNAVAILABLE across all routes in Phase 5B (zero fabrication)."
    )

    # 6. Carbon Savings (Pair-Wise Non-Zero Rule)
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
            note="Carbon savings UNAVAILABLE: at least one route lacks authentic carbon calculation."
        )
    else:
        delta_c = base_carbon - sel_carbon
        pct = round((delta_c / base_carbon) * 100, 2) if base_carbon > 0 else 0.0
        carbon_savings = MetricSavings(
            baseline_value=base_carbon,
            selected_value=sel_carbon,
            savings_value=round(delta_c, 6),
            savings_pct=pct,
            unit="gCO2e",
            provenance=ProvenanceStatus.ESTIMATED,
            scope=MeasurementScope.GPU_BOARD_OPERATIONAL_CARBON,
            note="Estimated operational carbon savings strictly scoped to GPU board."
        )

    # 7. Formulate Overall Integrity Notice
    if not quality_threshold_met:
        notice = "Quality threshold not met by selected route. Resource savings cannot be credited without accounting for the quality degradation penalty."
    elif energy_savings.provenance == ProvenanceStatus.UNAVAILABLE:
        notice = "Physical environmental savings are UNAVAILABLE for this comparison (zero fabrication). Authentic operational proxies (model calls avoided, tokens avoided, latency) are reported."
    else:
        notice = "Environmental savings computed from authentic physical measurements and configured operational parameters."

    return SavingsComparison(
        selected_route=selected.route,
        baseline_route=baseline.route,
        quality_threshold_met=quality_threshold_met,
        model_calls_avoided=model_calls_avoided,
        tokens_saved=tokens_saved,
        tokens_provenance=tokens_prov,
        latency_delta_ms=latency_delta_ms,
        energy_savings=energy_savings,
        water_savings=water_savings,
        carbon_savings=carbon_savings,
        notice=notice
    )

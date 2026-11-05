import uuid
from typing import Optional, Dict, Any, List

from telemetry.schemas import (
    ProvenanceStatus,
    MeasurementScope,
    TokenTelemetry,
    TelemetryRecord,
    RoutingDecision
)
from models.model_profiles import get_model_profile
from telemetry.registry import source_registry
from .schemas import (
    ExecutionPath,
    CostMetric,
    EnergyMetric,
    CarbonMetric,
    WaterMetric,
    EnvironmentalBreakdown,
    OptimizerSummary,
    ReceiptExplainability,
    AvoidanceSummary,
    EcoReceipt
)

def _classify_execution_path(telemetry_record: TelemetryRecord) -> ExecutionPath:
    """Classify execution into tool, cache, or model inference."""
    provider = (telemetry_record.provider or "").lower()
    route = (telemetry_record.route or "").lower()
    if provider == "deterministic" or "tool" in route or route.startswith("calculator"):
        return ExecutionPath.DETERMINISTIC_TOOL
    if provider == "cache" or "semantic_cache" in route or "cache" in route:
        return ExecutionPath.SEMANTIC_CACHE
    return ExecutionPath.MODEL_INFERENCE

def _calculate_monetary_cost(
    telemetry_record: TelemetryRecord,
    execution_path: ExecutionPath,
    status: str
) -> CostMetric:
    """
    Calculate defensible monetary cost in USD representing external provider API billing.
    Accurately distinguishes zero external API charges from zero total computing cost.
    Cost is never categorized as a direct measurement.
    """
    if status in ("FAILED", "PARTIAL"):
        return CostMetric(
            value_usd=None,
            provenance=ProvenanceStatus.UNAVAILABLE,
            pricing_source="None",
            details="Execution did not complete successfully; monetary cost is unavailable without full provider billing metadata.",
            is_zero_external_api_charge=False
        )

    if execution_path == ExecutionPath.DETERMINISTIC_TOOL:
        return CostMetric(
            value_usd=0.0,
            provenance=ProvenanceStatus.ESTIMATED,
            pricing_source="Local CPU Deterministic Tool",
            details="0.00 USD external provider API charges (zero external API calls). Does not imply zero total computing, hardware, or host electricity cost.",
            is_zero_external_api_charge=True
        )

    if execution_path == ExecutionPath.SEMANTIC_CACHE:
        return CostMetric(
            value_usd=0.0,
            provenance=ProvenanceStatus.ESTIMATED,
            pricing_source="Local Semantic Cache",
            details="0.00 USD external provider API charges (reused from local cache). Does not imply zero total computing, hardware, or host electricity cost.",
            is_zero_external_api_charge=True
        )

    # Model inference path
    model_id = telemetry_record.model
    if not model_id or model_id == "None":
        return CostMetric(
            value_usd=None,
            provenance=ProvenanceStatus.UNAVAILABLE,
            pricing_source="Unknown",
            details="Model identifier absent; cost cannot be computed.",
            is_zero_external_api_charge=False
        )

    profile = get_model_profile(model_id)
    if not profile:
        return CostMetric(
            value_usd=None,
            provenance=ProvenanceStatus.UNAVAILABLE,
            pricing_source=f"Unregistered Model: {model_id}",
            details=f"Pricing profile for model '{model_id}' is not configured in the catalog.",
            is_zero_external_api_charge=False
        )

    if profile.is_local:
        return CostMetric(
            value_usd=0.0,
            provenance=ProvenanceStatus.ESTIMATED,
            pricing_source=f"Local Model Catalog ({model_id})",
            details="0.00 USD external provider API charges (on-device local inference). Does not imply zero total computing, hardware, or host electricity cost.",
            is_zero_external_api_charge=True
        )

    # Cloud model with public pricing
    if profile.pricing_input_per_1m_usd is not None and profile.pricing_output_per_1m_usd is not None:
        in_tokens = telemetry_record.tokens.input_tokens
        out_tokens = telemetry_record.tokens.output_tokens
        if in_tokens is None or out_tokens is None:
            return CostMetric(
                value_usd=None,
                provenance=ProvenanceStatus.UNAVAILABLE,
                pricing_source=f"Catalog ({model_id})",
                details="Cannot calculate monetary cost because provider token counts are unavailable or unmeasured.",
                is_zero_external_api_charge=False
            )
        in_cost = (in_tokens / 1_000_000.0) * profile.pricing_input_per_1m_usd
        out_cost = (out_tokens / 1_000_000.0) * profile.pricing_output_per_1m_usd
        total_cost = round(in_cost + out_cost, 8)
        return CostMetric(
            value_usd=total_cost,
            provenance=ProvenanceStatus.ESTIMATED,
            pricing_source=f"Official catalog pricing ({profile.provider}: ${profile.pricing_input_per_1m_usd}/1M in, ${profile.pricing_output_per_1m_usd}/1M out)",
            details=f"Prompt: {in_tokens} tokens (${in_cost:.6f}) + Completion: {out_tokens} tokens (${out_cost:.6f}). External provider API charges only.",
            is_zero_external_api_charge=False
        )

    return CostMetric(
        value_usd=None,
        provenance=ProvenanceStatus.UNAVAILABLE,
        pricing_source=f"Catalog ({model_id})",
        details="Pricing rate is missing or undisclosed for this model.",
        is_zero_external_api_charge=False
    )

def _build_environmental_breakdown(telemetry_record: TelemetryRecord) -> EnvironmentalBreakdown:
    """Build itemized environmental breakdown respecting Non-Zero and Anti-Fabrication rules."""
    env = telemetry_record.environment

    # 1. Energy
    val_j = env.energy_joules
    val_kwh = round(val_j / 3_600_000.0, 9) if val_j is not None else None
    is_meas = (env.energy_provenance == ProvenanceStatus.MEASURED)
    is_est = (env.energy_provenance == ProvenanceStatus.ESTIMATED)
    
    scope = MeasurementScope.UNKNOWN
    dev_platform = None
    scope_note = ""

    if env.gpu_telemetry and env.gpu_telemetry.provenance == ProvenanceStatus.MEASURED:
        scope = MeasurementScope.GPU_INFERENCE_WINDOW
        dev_platform = env.gpu_telemetry.device_name
        scope_note = "MEASURED GPU ENERGY (INFERENCE WINDOW ONLY - NOT TOTAL SYSTEM ENERGY)"
    elif env.measurement and env.measurement.provenance == ProvenanceStatus.MEASURED:
        scope = env.measurement.scope
        dev_platform = env.measurement.device_platform
        scope_note = f"Measured via {env.measurement.source} under scope {env.measurement.scope}."
    elif is_est:
        scope = MeasurementScope.CLOUD_INFERENCE
        scope_note = "Estimated cloud server energy using empirical benchmark / LCA model. Physical datacenter power draw is inaccessible."
    else:
        scope = MeasurementScope.UNKNOWN
        scope_note = "Physical energy is unmetered or undisclosed on this execution path."

    energy_metric = EnergyMetric(
        value_joules=val_j,
        value_kwh=val_kwh,
        unit="J",
        scope=scope,
        provenance=env.energy_provenance,
        is_measured=is_meas,
        is_estimated=is_est,
        device_platform=dev_platform,
        scope_disclaimer=scope_note
    )

    # 2. Carbon
    val_c = env.carbon_gco2e
    c_prov = env.carbon_provenance
    c_scope = env.carbon_scope
    grid_int = env.grid_intensity_gco2e_per_kwh
    grid_source_label = None
    formula_str = None

    # Carbon calculation strictly requires valid energy AND valid positive grid intensity
    if val_c is not None and val_j is not None and grid_int is not None and grid_int > 0:
        grid_source_label = "Configured Regional Grid Intensity Factor"
        formula_str = "Operational_Carbon (gCO2e) = Energy (kWh) * Grid_Intensity (gCO2e/kWh)"
    else:
        val_c = None
        c_prov = ProvenanceStatus.UNAVAILABLE
        c_scope = None

    carbon_metric = CarbonMetric(
        value_gco2e=val_c,
        unit="gCO2e",
        scope=c_scope,
        provenance=c_prov,
        grid_intensity_gco2e_per_kwh=grid_int,
        grid_source=grid_source_label,
        formula=formula_str
    )

    # 3. Water
    val_w = env.water_liters
    w_prov = env.water_provenance
    water_metric = WaterMetric(
        value_liters=val_w,
        unit="L",
        accounting_scope="unavailable",
        provenance=w_prov,
        reason_unavailable="Data center facility locations, cooling technologies, and WUE factors are undisclosed by model providers (anti-fabrication safeguard)."
    )

    # 4. Source & Estimator Metadata
    source_title = None
    if env.source_id:
        src = source_registry.get(env.source_id)
        if src:
            source_title = src.name
        else:
            source_title = env.source_id

    return EnvironmentalBreakdown(
        energy=energy_metric,
        carbon=carbon_metric,
        water=water_metric,
        source_id=env.source_id,
        source_name=source_title,
        source_version=env.source_version,
        estimator_name=env.estimator_name,
        estimator_version=env.estimator_version,
        assumptions=list(env.assumptions),
        uncertainty_info=env.uncertainty_info,
        unavailable_reasons=dict(env.unavailable_reasons)
    )

def _build_optimizer_summary(telemetry_record: TelemetryRecord) -> Optional[OptimizerSummary]:
    """Extract and format Phase 6 multi-objective routing summary."""
    dec: Optional[RoutingDecision] = telemetry_record.routing_decision
    if not dec:
        return None

    # Check if selected route satisfied threshold
    quality_met = True
    if dec.candidates:
        for cand in dec.candidates:
            if cand.route_name == dec.selected_route:
                quality_met = cand.is_hard_constraint_met
                break

    return OptimizerSummary(
        decision_id=getattr(dec, "decision_id", None),
        selected_candidate=dec.selected_route,
        selected_tier=dec.selected_tier,
        routing_rationale=dec.decision_rationale,
        quality_threshold_required=dec.quality_threshold,
        quality_threshold_met=quality_met,
        pareto_frontier=list(dec.pareto_frontier),
        active_weights=dict(dec.objective_weights),
        candidate_scores=list(dec.candidates),
        fallback_applied=(dec.fallback_reason is not None),
        fallback_reason=dec.fallback_reason
    )

def _build_explainability(
    telemetry_record: TelemetryRecord,
    execution_path: ExecutionPath,
    status: str,
    optimizer_summary: Optional[OptimizerSummary],
    cost_metric: CostMetric,
    env_breakdown: EnvironmentalBreakdown
) -> ReceiptExplainability:
    """Generate concise, honest human-readable explainability without unsupported claims."""

    # 1. Selection summary
    if status == "FAILED":
        selection_summary = (
            f"The request failed prior to completion with error: '{telemetry_record.error_message or 'Unknown error'}'. "
            f"Execution halted before completion; no subsequent inference or cache writes were performed."
        )
    elif status == "PARTIAL":
        selection_summary = (
            f"The request partially executed but encountered an error before completion: '{telemetry_record.error_message or 'Incomplete'}'. "
            f"Only preliminary operational metrics captured prior to interruption are reported."
        )
    elif execution_path == ExecutionPath.DETERMINISTIC_TOOL:
        selection_summary = (
            f"The query matched candidate rules for deterministic execution ({telemetry_record.route}). "
            f"It was resolved with mathematical exactness on local CPU in {telemetry_record.latency.execution_time_ms:.1f} ms, "
            f"completely bypassing neural network inference and consuming 0 model tokens."
        )
    elif execution_path == ExecutionPath.SEMANTIC_CACHE:
        selection_summary = (
            f"The query matched a verified cached answer in the precision-first semantic cache (Stage 1 cosine search + "
            f"Stage 2 deterministic compatibility validation). The stored answer was reused as-is in "
            f"{telemetry_record.latency.execution_time_ms:.1f} ms with 0 model calls."
        )
    else:
        if optimizer_summary:
            w = optimizer_summary.active_weights
            w_str = ", ".join(f"{k}: {v:.2f}" for k, v in w.items()) if w else "configured weights"
            selection_summary = (
                f"Selected route '{telemetry_record.route}' via the Multi-Objective Routing Optimizer using active weights ({w_str}). "
                f"The candidate satisfied the required quality threshold Q_req={optimizer_summary.quality_threshold_required:.2f} "
                f"(quality met: {optimizer_summary.quality_threshold_met}) and scored lowest scalarized cost among non-dominated candidates. "
                f"Rationale: {optimizer_summary.routing_rationale}"
            )
        else:
            selection_summary = (
                f"Selected route '{telemetry_record.route}' on provider '{telemetry_record.provider}' "
                f"based on requested execution preference."
            )

    # 2. Measurement vs Estimation (Strict Non-Fabrication)
    measured_items: List[str] = [f"Total Latency ({telemetry_record.latency.execution_time_ms:.1f} ms)"]
    if telemetry_record.latency.inference_latency_ms is not None:
        measured_items.append(f"Inference Latency ({telemetry_record.latency.inference_latency_ms:.1f} ms)")
    
    if execution_path in (ExecutionPath.DETERMINISTIC_TOOL, ExecutionPath.SEMANTIC_CACHE):
        measured_items.append("Token Count (0 LLM tokens, known zero by construction without neural model inference)")
    elif telemetry_record.tokens.provenance == ProvenanceStatus.PROVIDER_REPORTED and telemetry_record.tokens.total_tokens is not None:
        measured_items.append(f"Tokens ({telemetry_record.tokens.total_tokens} provider-reported)")
    elif telemetry_record.tokens.provenance == ProvenanceStatus.MEASURED and telemetry_record.tokens.total_tokens is not None:
        measured_items.append(f"Tokens ({telemetry_record.tokens.total_tokens} directly measured)")

    if env_breakdown.energy.is_measured and env_breakdown.energy.value_joules is not None:
        measured_items.append(f"GPU Board Energy ({env_breakdown.energy.value_joules:.2f} J measured on-device)")

    estimated_items: List[str] = []
    if env_breakdown.energy.is_estimated and env_breakdown.energy.value_joules is not None:
        estimated_items.append(f"Cloud Energy ({env_breakdown.energy.value_joules:.2f} J estimated via {env_breakdown.estimator_name or 'model'})")
    if env_breakdown.carbon.provenance == ProvenanceStatus.ESTIMATED and env_breakdown.carbon.value_gco2e is not None:
        estimated_items.append(f"Operational Carbon ({env_breakdown.carbon.value_gco2e:.4f} gCO2e estimated from grid intensity)")
    
    if cost_metric.value_usd is not None:
        if cost_metric.is_zero_external_api_charge:
            estimated_items.append("External Provider API Charges ($0.00 established zero vendor fee)")
        else:
            estimated_items.append(f"External Provider API Cost (${cost_metric.value_usd:.6f} estimated from catalog token rates)")

    meas_str = ", ".join(measured_items) if measured_items else "None"
    est_str = ", ".join(estimated_items) if estimated_items else "None"
    measurement_vs_estimation = (
        f"Directly Measured / Known Zero: {meas_str}. "
        f"Scientifically Estimated / Catalog-Derived: {est_str}."
    )

    # 3. Unavailable metrics rationale
    unav_list: List[str] = []
    if telemetry_record.tokens.provenance == ProvenanceStatus.UNAVAILABLE:
        unav_list.append("Token counts are UNAVAILABLE because no token usage metadata was provided by the upstream engine.")
    if env_breakdown.energy.provenance == ProvenanceStatus.UNAVAILABLE:
        unav_list.append("Physical Energy is UNAVAILABLE because cloud providers do not disclose server power draw and no hardware sensor was active.")
    if env_breakdown.carbon.provenance == ProvenanceStatus.UNAVAILABLE:
        unav_list.append("Carbon Emissions are UNAVAILABLE because grid carbon intensity was unconfigured or physical energy was unmeasured.")
    if env_breakdown.water.provenance == ProvenanceStatus.UNAVAILABLE:
        unav_list.append("Water Footprint is UNAVAILABLE because datacenter cooling WUE and locations are undisclosed (anti-fabrication safeguard).")
    if cost_metric.provenance == ProvenanceStatus.UNAVAILABLE:
        unav_list.append(f"External API Cost is UNAVAILABLE ({cost_metric.details}).")

    if not unav_list:
        unavailable_rationale = "All expected operational and environmental metrics were successfully measured or estimated."
    else:
        unavailable_rationale = " ".join(unav_list)

    # 4. Caveats & Uncertainty
    caveats: List[str] = [
        "Routing decisions are determined by the configured optimizer policy, weights, and available proxy metrics; "
        "they are not claimed to be globally optimal across unmeasured variables or untracked models.",
        "Reported monetary cost reflects external provider API billing only, and does not reflect host electricity or server hardware amortisation."
    ]
    if env_breakdown.energy.is_measured:
        caveats.append(
            "Measured energy represents active GPU die and VRAM consumption during the inference window only; "
            "server CPU, RAM, storage, cooling fans, and power delivery conversion losses are excluded."
        )
    if env_breakdown.energy.is_estimated and env_breakdown.uncertainty_info:
        caveats.append(f"Estimation Model Uncertainty: {env_breakdown.uncertainty_info}")

    caveats_and_uncertainty = " ".join(caveats)

    return ReceiptExplainability(
        selection_summary=selection_summary,
        measurement_vs_estimation=measurement_vs_estimation,
        unavailable_metrics_rationale=unavailable_rationale,
        caveats_and_uncertainty=caveats_and_uncertainty
    )

def generate_eco_receipt(
    telemetry_record: TelemetryRecord,
    query: Optional[str] = None
) -> EcoReceipt:
    """
    Generate an EcoReceipt from a recorded TelemetryRecord and optional query context.
    Enforces strict non-fabrication, measurement scope isolation, and clear explainability.
    """
    if telemetry_record.success:
        status = "SUCCESS"
    elif (
        (telemetry_record.tokens.input_tokens is not None and telemetry_record.tokens.input_tokens > 0)
        or (telemetry_record.latency.inference_latency_ms is not None and telemetry_record.latency.inference_latency_ms > 0)
    ):
        status = "PARTIAL"
    else:
        status = "FAILED"

    execution_path = _classify_execution_path(telemetry_record)
    
    # Calculate monetary cost
    cost_metric = _calculate_monetary_cost(telemetry_record, execution_path, status)
    
    # Build environmental breakdown
    env_breakdown = _build_environmental_breakdown(telemetry_record)
    
    # Build optimizer summary
    optimizer_summary = _build_optimizer_summary(telemetry_record)
    
    # Build avoidance summary
    avoidance_summary = None
    if telemetry_record.avoidance:
        avoidance_summary = AvoidanceSummary(
            model_calls_avoided=telemetry_record.avoidance.model_calls_avoided,
            tokens_avoided=telemetry_record.avoidance.tokens_avoided,
            baseline_route=telemetry_record.avoidance.baseline_route,
            reasoning=telemetry_record.avoidance.reasoning,
            defensible_savings_reported=False,
            savings_notice=(
                f"Operational avoidance reflects bypassed model calls relative to counterfactual '{telemetry_record.avoidance.baseline_route}' baseline. "
                "Bypassing a model call does NOT imply physical energy or carbon savings unless both routes have directly measured or validated baseline telemetry (Non-Zero Rule). "
                "Physical environmental savings remain UNAVAILABLE."
            )
        )

    # Build explainability
    explainability = _build_explainability(
        telemetry_record=telemetry_record,
        execution_path=execution_path,
        status=status,
        optimizer_summary=optimizer_summary,
        cost_metric=cost_metric,
        env_breakdown=env_breakdown
    )

    # Preview query
    query_preview = None
    if query:
        query_preview = query[:120] + ("..." if len(query) > 120 else "")

    receipt_id = f"rcpt_{telemetry_record.request_id}"

    return EcoReceipt(
        receipt_id=receipt_id,
        request_id=telemetry_record.request_id,
        timestamp=telemetry_record.timestamp,
        status=status,
        execution_path=execution_path,
        route=telemetry_record.route,
        provider=telemetry_record.provider,
        model=telemetry_record.model,
        query_preview=query_preview,
        execution_time_ms=telemetry_record.latency.execution_time_ms,
        inference_latency_ms=telemetry_record.latency.inference_latency_ms,
        latency_provenance=telemetry_record.latency.provenance,
        tokens=telemetry_record.tokens,
        cost=cost_metric,
        environment=env_breakdown,
        avoidance=avoidance_summary,
        optimizer=optimizer_summary,
        explainability=explainability
    )

import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException

from .schemas import (
    ChatRequest,
    ChatResponse,
    TokenUsageSchema,
    ToolInfoSchema,
    ModelProfileSchema,
    CacheStatsSchema,
    SavingsCompareRequest,
    RouterConfigSchema,
    RoutePreviewRequest
)
from tools.tool_registry import tool_registry
from router.query_analyzer import QueryAnalyzer, QueryAnalysis
from router.routing_policy import RoutingPolicy
from models.dispatcher import model_dispatcher, ProviderUnavailableError
from models.model_profiles import list_all_profiles
from models.provider import TokenUsage
from cache.semantic_cache import semantic_cache
from telemetry.telemetry import telemetry_collector
from telemetry.schemas import (
    TelemetryRecord,
    TelemetrySummary,
    MeasurementCapabilities,
    SavingsComparison,
    EnvironmentalSource,
    SourceCheckResult,
    GridIntensityRecord,
    RoutingDecision,
    CandidateScore
)
from telemetry.savings import calculate_savings
from telemetry.registry import source_registry, source_validation_service
from telemetry.grid import grid_manager

router = APIRouter()

# Instantiate router components
query_analyzer = QueryAnalyzer()
routing_policy = RoutingPolicy()

@router.get("/tools", response_model=List[ToolInfoSchema])
def get_tools():
    """Return all available deterministic tools."""
    return tool_registry.list_tools()

@router.get("/models", response_model=List[ModelProfileSchema])
def get_models():
    """Return all configured model profiles across small, medium, and large tiers."""
    return list_all_profiles()

@router.get("/cache/stats", response_model=CacheStatsSchema)
def get_cache_stats():
    """Return telemetry and metrics for the precision-first semantic cache."""
    return semantic_cache.stats()

@router.post("/cache/clear")
def clear_cache():
    """Clear all entries in the semantic cache."""
    semantic_cache.clear()
    return {
        "message": "Semantic cache cleared successfully.",
        "total_entries": 0
    }

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Control plane execution endpoint:
    1. Evaluates deterministic candidate tools first (0 tokens, no model call).
    2. If no tool matches, checks Accuracy-First Semantic Cache (Stage 1 + Stage 2).
       - On Cache Hit: returns stored answer directly (0 tokens, 0 model calls).
    3. On Cache Miss: uses QueryAnalyzer + RoutingPolicy to determine logical tier.
    4. Resolves logical tier to configured provider + model via ModelDispatcher.
    5. Stores successful response into Semantic Cache for future conservative reuse.
    6. Accurately reports latency, authentic token usage, cache status, and large model avoidance.
    """
    start_time = time.perf_counter()
    query = request.query.strip()
    route_pref = (request.preferred_route or "auto").lower()

    # Step 1: Check Deterministic Tools FIRST (if auto or deterministic_tool requested)
    if route_pref in ("auto", "deterministic_tool"):
        candidate_tool = tool_registry.find_candidate_tool(query)
        if candidate_tool:
            tool_result = candidate_tool.execute(query)
            if tool_result.success:
                total_latency = (time.perf_counter() - start_time) * 1000
                route_label = (
                    "Calculator / Deterministic Tool"
                    if candidate_tool.name == "calculator"
                    else f"{candidate_tool.name.capitalize()} / Deterministic Tool"
                )
                tool_decision = routing_policy.optimize_route(
                    query=query,
                    analysis=QueryAnalysis(
                        task_type=candidate_tool.name,
                        complexity="low",
                        requires_tool=True,
                        requires_reasoning=False,
                        candidate_tool=candidate_tool.name
                    ),
                    candidate_tool_name=candidate_tool.name
                )
                telemetry_rec = telemetry_collector.record_success(
                    route=route_label,
                    provider="deterministic",
                    model="None",
                    execution_time_ms=total_latency,
                    inference_latency_ms=tool_result.execution_time_ms,
                    token_usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0, is_estimated=False),
                    routing_decision=tool_decision
                )
                return ChatResponse(
                    query=query,
                    answer=str(tool_result.result),
                    route=route_label,
                    model="None",
                    provider="deterministic",
                    execution_time_ms=total_latency,
                    token_usage=TokenUsageSchema(
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        is_estimated=False
                    ),
                    large_model_avoided=True,
                    cache_status="not_checked",
                    cache_similarity=None,
                    metadata={
                        "tool_used": candidate_tool.name,
                        "tool_metadata": tool_result.metadata,
                        "tool_execution_ms": tool_result.execution_time_ms,
                        "complexity": "deterministic",
                        "reasoning": f"Deterministic {candidate_tool.name} solved without neural network inference.",
                        "routing_decision": tool_decision.model_dump(),
                        "decision_rationale": tool_decision.decision_rationale
                    },
                    telemetry=telemetry_rec
                )
            elif route_pref == "deterministic_tool":
                telemetry_collector.record_failure(
                    route="deterministic_tool",
                    provider="deterministic",
                    execution_time_ms=(time.perf_counter() - start_time) * 1000,
                    error_message=str(tool_result.error)
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"Deterministic tool execution failed: {tool_result.error}"
                )
        elif route_pref == "deterministic_tool":
            telemetry_collector.record_failure(
                route="deterministic_tool",
                provider="deterministic",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
                error_message="No available deterministic tool can handle this query."
            )
            raise HTTPException(
                status_code=400,
                detail="No available deterministic tool can handle this query."
            )

    # Step 2: Semantic Cache Lookup (Stage 1 retrieval + Stage 2 compatibility validation)
    cache_status = "not_checked"
    cache_similarity: Optional[float] = None

    if route_pref in ("auto", "semantic_cache"):
        cache_result = semantic_cache.lookup(query=query)
        cache_similarity = cache_result.similarity

        if cache_result.status == "hit" and cache_result.entry:
            total_latency = (time.perf_counter() - start_time) * 1000
            cached = cache_result.entry
            cache_decision = routing_policy.optimize_route(
                query=query,
                analysis=QueryAnalysis(
                    task_type=cached.task_type or "general_qa",
                    complexity="low",
                    requires_tool=False,
                    requires_reasoning=False
                ),
                cache_hit_entry=cached
            )
            telemetry_rec = telemetry_collector.record_success(
                route="semantic_cache",
                provider="cache",
                model=None,
                execution_time_ms=total_latency,
                inference_latency_ms=0.0,
                token_usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0, is_estimated=False),
                routing_decision=cache_decision
            )
            return ChatResponse(
                query=query,
                answer=cached.answer,
                route="semantic_cache",
                model=None,
                provider="cache",
                execution_time_ms=total_latency,
                token_usage=TokenUsageSchema(
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    is_estimated=False
                ),
                large_model_avoided=True,
                cache_status="hit",
                cache_similarity=cache_similarity,
                metadata={
                    "cache_status": "hit",
                    "cache_similarity": cache_similarity,
                    "cached_query": cached.query,
                    "hit_count": cached.hit_count,
                    "task_type": cached.task_type,
                    "original_provider": cached.provider,
                    "original_model": cached.model,
                    "reasoning": "Answer reused from precision-first semantic cache with verified compatibility; 0 model inference calls.",
                    "routing_decision": cache_decision.model_dump(),
                    "decision_rationale": cache_decision.decision_rationale
                },
                telemetry=telemetry_rec
            )
        else:
            cache_status = "miss"
            if route_pref == "semantic_cache":
                telemetry_collector.record_failure(
                    route="semantic_cache",
                    provider="cache",
                    execution_time_ms=(time.perf_counter() - start_time) * 1000,
                    error_message="Cache miss: no compatible cached response found."
                )
                raise HTTPException(
                    status_code=404,
                    detail="Cache miss: no compatible cached response found."
                )

    # Step 3: Determine Logical Model Tier via QueryAnalyzer & RoutingPolicy (Multi-Objective Optimization)
    analysis = None
    routing_decision = None
    if route_pref in ("small_model", "medium_model", "large_model"):
        # Explicit user override
        tier = route_pref.replace("_model", "")
    elif route_pref == "auto":
        # Dynamic, provider-agnostic multi-objective Pareto routing
        analysis = query_analyzer.analyze(query)
        routing_decision = routing_policy.optimize_route(query=query, analysis=analysis)
        if routing_decision.selected_tier in ("small", "medium", "large"):
            tier = routing_decision.selected_tier
        else:
            raw_route = routing_policy.select_route(analysis)
            tier = raw_route if raw_route in ("small", "medium", "large") else "small"
    else:
        telemetry_collector.record_failure(
            route=request.preferred_route or "invalid",
            provider="unknown",
            execution_time_ms=(time.perf_counter() - start_time) * 1000,
            error_message=f"Unsupported route preference '{request.preferred_route}'."
        )
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported route preference '{request.preferred_route}'."
        )

    # Step 4: Model Dispatcher Execution
    try:
        resp = model_dispatcher.dispatch(tier=tier, prompt=query)
        total_latency = (time.perf_counter() - start_time) * 1000

        token_usage = None
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        if resp.usage:
            prompt_tokens = resp.usage.prompt_tokens or 0
            completion_tokens = resp.usage.completion_tokens or 0
            total_tokens = resp.usage.total_tokens or 0
            token_usage = TokenUsageSchema(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                is_estimated=resp.usage.is_estimated
            )

        large_model_avoided = (tier != "large")
        provider_display = resp.provider_name.capitalize()
        tier_display = f"{tier.capitalize()} Model ({provider_display})"

        # Step 5: Store successful model response in Semantic Cache (if auto routing)
        if route_pref == "auto":
            semantic_cache.store_result(
                query=query,
                answer=resp.content,
                task_type=analysis.task_type if analysis else "general_qa",
                route=tier_display,
                provider=resp.provider_name,
                model=resp.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                execution_time_ms=total_latency,
                analysis=analysis
            )

        metadata: Dict[str, Any] = {
            "tier": tier,
            "provider": resp.provider_name,
            "model": resp.model_name,
            "cache_status": cache_status,
            "cache_similarity": cache_similarity,
            "raw_metadata": resp.raw_metadata
        }
        if analysis:
            metadata.update({
                "task_type": analysis.task_type,
                "complexity": analysis.complexity,
                "requires_reasoning": analysis.requires_reasoning
            })
        if routing_decision:
            metadata.update({
                "routing_decision": routing_decision.model_dump(),
                "decision_rationale": routing_decision.decision_rationale
            })

        phys_meta = resp.raw_metadata.get("physical_measurement") if resp.raw_metadata else None
        gpu_meta = resp.raw_metadata.get("gpu_telemetry") if resp.raw_metadata else None
        telemetry_rec = telemetry_collector.record_success(
            route=tier_display,
            provider=resp.provider_name,
            model=resp.model_name,
            execution_time_ms=total_latency,
            inference_latency_ms=resp.latency_ms,
            token_usage=resp.usage,
            physical_measurement=phys_meta,
            gpu_telemetry=gpu_meta,
            routing_decision=routing_decision
        )

        return ChatResponse(
            query=query,
            answer=resp.content,
            route=tier_display,
            model=resp.model_name,
            provider=resp.provider_name,
            execution_time_ms=total_latency,
            token_usage=token_usage,
            large_model_avoided=large_model_avoided,
            cache_status=cache_status,
            cache_similarity=cache_similarity,
            metadata=metadata,
            telemetry=telemetry_rec
        )
    except ProviderUnavailableError as pue:
        telemetry_collector.record_failure(
            route=tier,
            provider="unknown",
            model=None,
            execution_time_ms=(time.perf_counter() - start_time) * 1000,
            error_message=str(pue)
        )
        raise HTTPException(status_code=503, detail=str(pue))
    except ValueError as ve:
        telemetry_collector.record_failure(
            route=tier,
            provider="unknown",
            model=None,
            execution_time_ms=(time.perf_counter() - start_time) * 1000,
            error_message=str(ve)
        )
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        telemetry_collector.record_failure(
            route=tier,
            provider="unknown",
            model=None,
            execution_time_ms=(time.perf_counter() - start_time) * 1000,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/telemetry/capabilities", response_model=MeasurementCapabilities)
def get_telemetry_capabilities():
    """Return physical energy measurement capabilities of the host system."""
    return telemetry_collector.get_capabilities()

@router.get("/telemetry/recent", response_model=List[TelemetryRecord])
def get_recent_telemetry(limit: int = 50):
    """Return recently captured real telemetry records."""
    return telemetry_collector.get_recent(limit=limit)

@router.get("/telemetry/summary", response_model=TelemetrySummary)
def get_telemetry_summary():
    """Return aggregated telemetry metrics across all captured requests."""
    return telemetry_collector.get_summary()

@router.post("/telemetry/clear")
def clear_telemetry():
    """Clear recorded in-memory telemetry."""
    telemetry_collector.clear()
    return {"message": "Telemetry records cleared successfully."}

@router.post("/telemetry/savings/compare", response_model=SavingsComparison)
def compare_telemetry_savings(request: SavingsCompareRequest):
    """
    Compute pair-wise savings between two recorded requests.
    Enforces the Non-Zero Rule: if either route lacks authentic environmental metrics,
    environmental savings are strictly UNAVAILABLE; operational proxies are reported instead.
    """
    sel = telemetry_collector.get_record(request.selected_request_id)
    if not sel:
        raise HTTPException(
            status_code=404,
            detail=f"Selected telemetry record '{request.selected_request_id}' not found."
        )

    base = telemetry_collector.get_record(request.baseline_request_id)
    if not base:
        raise HTTPException(
            status_code=404,
            detail=f"Baseline telemetry record '{request.baseline_request_id}' not found."
        )

    return calculate_savings(
        selected=sel,
        baseline=base,
        quality_threshold_met=request.quality_threshold_met
    )

@router.get("/telemetry/sources", response_model=List[EnvironmentalSource])
def list_environmental_sources():
    """List all registered, versioned environmental estimation sources and their freshness status."""
    return source_registry.list_all()

@router.get("/telemetry/sources/{source_id}", response_model=EnvironmentalSource)
def get_environmental_source(source_id: str):
    """Retrieve detailed metadata and methodology for a specific environmental source."""
    src = source_registry.get(source_id)
    if not src:
        raise HTTPException(
            status_code=404,
            detail=f"Environmental estimation source '{source_id}' not found in registry."
        )
    return src

@router.post("/telemetry/sources/refresh", response_model=List[SourceCheckResult])
def refresh_environmental_sources():
    """
    Audit freshness across all registered sources and flag review-needed or stale methodologies.
    Retains previous validated version if an external source is inaccessible.
    """
    return source_validation_service.refresh_all()

@router.get("/telemetry/grid", response_model=Optional[GridIntensityRecord])
def get_current_grid_intensity(region: Optional[str] = None):
    """
    Inspect the active electricity grid carbon emissions factor, applicable region,
    provenance, and live vs static status.
    """
    return grid_manager.get_intensity(region=region)

@router.get("/router/config", response_model=RouterConfigSchema)
def get_router_config():
    """Inspect current multi-objective optimizer weights, quality thresholds, and Pareto settings."""
    from config.settings import settings
    return RouterConfigSchema(
        weight_quality=routing_policy.optimizer.w_quality,
        weight_latency=routing_policy.optimizer.w_latency,
        weight_cost=routing_policy.optimizer.w_cost,
        weight_environment=routing_policy.optimizer.w_environment,
        quality_threshold_high=getattr(settings, "ROUTER_QUALITY_THRESHOLD_HIGH", 0.80),
        quality_threshold_medium=getattr(settings, "ROUTER_QUALITY_THRESHOLD_MEDIUM", 0.65),
        quality_threshold_low=getattr(settings, "ROUTER_QUALITY_THRESHOLD_LOW", 0.50),
        pareto_enabled=routing_policy.optimizer.pareto_enabled
    )

@router.post("/router/optimize", response_model=RoutingDecision)
def preview_routing_optimization(request: RoutePreviewRequest):
    """
    Preview multi-objective routing optimization for a query without executing LLM inference.
    Returns evaluated candidate routes, Pareto frontier, quality constraints, and rationale.
    """
    analysis = query_analyzer.analyze(request.query)
    candidate_tool = tool_registry.find_candidate_tool(request.query)
    tool_name = candidate_tool.name if candidate_tool else None
    return routing_policy.optimize_route(
        query=request.query,
        analysis=analysis,
        candidate_tool_name=tool_name
    )



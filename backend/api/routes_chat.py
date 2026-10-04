import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException

from .schemas import (
    ChatRequest,
    ChatResponse,
    TokenUsageSchema,
    ToolInfoSchema,
    ModelProfileSchema,
    CacheStatsSchema
)
from tools.tool_registry import tool_registry
from router.query_analyzer import QueryAnalyzer
from router.routing_policy import RoutingPolicy
from models.dispatcher import model_dispatcher, ProviderUnavailableError
from models.model_profiles import list_all_profiles
from cache.semantic_cache import semantic_cache

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
                        "reasoning": f"Deterministic {candidate_tool.name} solved without neural network inference."
                    }
                )
            elif route_pref == "deterministic_tool":
                raise HTTPException(
                    status_code=400,
                    detail=f"Deterministic tool execution failed: {tool_result.error}"
                )
        elif route_pref == "deterministic_tool":
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
                    "reasoning": "Answer reused from precision-first semantic cache with verified compatibility; 0 model inference calls."
                }
            )
        else:
            cache_status = "miss"
            if route_pref == "semantic_cache":
                raise HTTPException(
                    status_code=404,
                    detail="Cache miss: no compatible cached response found."
                )

    # Step 3: Determine Logical Model Tier via QueryAnalyzer & RoutingPolicy
    analysis = None
    if route_pref in ("small_model", "medium_model", "large_model"):
        # Explicit user override
        tier = route_pref.replace("_model", "")
    elif route_pref == "auto":
        # Dynamic, provider-agnostic routing
        analysis = query_analyzer.analyze(query)
        raw_route = routing_policy.select_route(analysis)
        if raw_route in ("small", "medium", "large"):
            tier = raw_route
        else:
            tier = "small"
    else:
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
            metadata=metadata
        )
    except ProviderUnavailableError as pue:
        raise HTTPException(status_code=503, detail=str(pue))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

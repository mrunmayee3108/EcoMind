from typing import Optional, Any
from .query_analyzer import QueryAnalysis
from .optimizer import RoutingOptimizer, routing_optimizer
from telemetry.schemas import RoutingDecision


class RoutingPolicy:
    """
    Control Plane Routing Policy.
    Supports both legacy deterministic heuristic route selection and
    Phase 6 Multi-Objective Pareto optimization.
    """

    def __init__(self, optimizer: Optional[RoutingOptimizer] = None):
        self.optimizer = optimizer or routing_optimizer

    def select_route(self, analysis: QueryAnalysis) -> str:
        """
        Baseline deterministic heuristic selection (backward compatibility).
        Prioritizes deterministic tools, then routes by complexity.
        """
        # 1. Deterministic tool routes (selected before model routes)
        if analysis.requires_tool:
            if analysis.candidate_tool:
                return analysis.candidate_tool
            # Fallback mapping from task_type
            tool_mapping = {
                "calculation": "calculator",
                "unit_conversion": "unit_converter",
                "date_time": "datetime_calculator",
                "statistics": "statistics_tool",
                "text_analysis": "text_analyzer",
            }
            return tool_mapping.get(analysis.task_type, "calculator")

        # 2. Model routes based on query complexity
        if analysis.complexity == "high":
            return "large"

        if analysis.complexity == "medium":
            return "medium"

        # low complexity model route
        return "small"

    def optimize_route(
        self,
        query: str,
        analysis: QueryAnalysis,
        candidate_tool_name: Optional[str] = None,
        cache_hit_entry: Optional[Any] = None
    ) -> RoutingDecision:
        """
        Phase 6 Multi-Objective Optimization.
        Evaluates hard constraints, computes Pareto frontier, normalizes objectives,
        and returns an explainable RoutingDecision.
        """
        return self.optimizer.optimize(
            query=query,
            analysis=analysis,
            candidate_tool_name=candidate_tool_name,
            cache_hit_entry=cache_hit_entry
        )

from .query_analyzer import QueryAnalysis

class RoutingPolicy:
    def select_route(self, analysis: QueryAnalysis) -> str:
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
        
        
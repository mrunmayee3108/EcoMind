from dataclasses import dataclass
from typing import Optional
from tools.tool_registry import tool_registry as default_tool_registry

# 'dataclasses' is built into Python standard library (no pip install needed).
# @dataclass auto-generates __init__, __repr__, and comparison methods for data models.

@dataclass 
class QueryAnalysis: 
    task_type: str 
    complexity: str 
    requires_tool: bool 
    requires_reasoning: bool
    candidate_tool: Optional[str] = None

class QueryAnalyzer:
    def __init__(self, registry=None):
        self.tool_registry = registry or default_tool_registry

    def analyze(self, query: str) -> QueryAnalysis:
        query_clean = query.strip()
        query_lower = query_clean.lower()

        # 1. Deterministic tool candidate detection
        candidate = self.tool_registry.find_candidate_tool(query_clean)
        if candidate:
            task_type_map = {
                "calculator": "calculation",
                "unit_converter": "unit_conversion",
                "datetime_calculator": "date_time",
                "statistics_tool": "statistics",
                "text_analyzer": "text_analysis",
            }
            task_type = task_type_map.get(candidate.name, "calculation")
            return QueryAnalysis(
                task_type=task_type,
                complexity="low",
                requires_tool=True,
                requires_reasoning=False,
                candidate_tool=candidate.name,
            )

        # 2. Reasoning detection
        reasoning_words = [
            "compare",
            "derive",
            "prove",
            "analyze",
            "evaluate",
            "why",
            "explain why",
        ]
        requires_reasoning = any(word in query_lower for word in reasoning_words)
        if requires_reasoning:
            return QueryAnalysis(
                task_type="reasoning",
                complexity="high",
                requires_tool=False,
                requires_reasoning=True,
                candidate_tool=None,
            )

        # 3. Medium complexity detection (summaries, translations, explanations)
        medium_words = ["summarize", "rephrase", "translate", "outline", "draft", "explain"]
        if any(word in query_lower for word in medium_words):
            return QueryAnalysis(
                task_type="general_qa",
                complexity="medium",
                requires_tool=False,
                requires_reasoning=False,
                candidate_tool=None,
            )

        # 4. Default simple factual QA
        return QueryAnalysis(
            task_type="general_qa",
            complexity="low",
            requires_tool=False,
            requires_reasoning=False,
            candidate_tool=None,
        )
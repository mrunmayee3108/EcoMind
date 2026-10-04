import math
import re
import statistics
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from .base import BaseTool, ToolResult


class StatisticsTool(BaseTool):
    """Deterministic tool for descriptive statistics (mean, median, mode, min, max, stdev)."""

    name = "statistics_tool"
    description = "Computes deterministic descriptive statistics (mean, median, min, max, standard deviation) on a numeric dataset without an LLM."

    _query_pattern = re.compile(
        r'^(?:(?:what\s+is\s+the|calculate\s+the|find\s+the|compute\s+the)\s+)?'
        r'(mean|average|median|mode|min|minimum|max|maximum|standard\s+deviation|stdev|std|variance|summary|stats)\s+'
        r'(?:of|for)\s+'
        r'(.+?)\??$',
        re.IGNORECASE
    )

    def _normalize_operation(self, op: str) -> str:
        op = op.strip().lower()
        if op in ("mean", "average"):
            return "mean"
        if op == "median":
            return "median"
        if op == "mode":
            return "mode"
        if op in ("min", "minimum"):
            return "min"
        if op in ("max", "maximum"):
            return "max"
        if op in ("standard deviation", "stdev", "std"):
            return "stdev"
        if op == "variance":
            return "variance"
        if op in ("summary", "stats"):
            return "summary"
        return op

    def parse_numbers(self, raw_str: str) -> Optional[List[float]]:
        """Extracts and validates a list of numbers from a string.
        
        Requires that all comma or whitespace-separated tokens are valid numeric values.
        """
        cleaned = raw_str.strip()
        # Remove surrounding brackets or parentheses
        cleaned = re.sub(r'^[\[\(\{]+|[\]\)\}]+$', '', cleaned).strip()

        # If comma-separated, split by comma
        if ',' in cleaned:
            tokens = [t.strip() for t in cleaned.split(',') if t.strip()]
        else:
            tokens = [t.strip() for t in cleaned.split() if t.strip()]

        if not tokens:
            return None

        numbers: List[float] = []
        for t in tokens:
            # Check if token is a valid float
            try:
                val = float(t)
                numbers.append(val)
            except ValueError:
                return None

        return numbers

    def can_handle(self, query: str) -> bool:
        """Conservatively check if the query is a valid statistics calculation."""
        m = self._query_pattern.match(query.strip())
        if not m:
            return False

        op_raw, nums_raw = m.groups()
        numbers = self.parse_numbers(nums_raw)
        if numbers is None or len(numbers) == 0:
            return False

        op = self._normalize_operation(op_raw)

        # Standard deviation and variance require at least 2 numbers
        if op in ("stdev", "variance") and len(numbers) < 2:
            return False

        return True

    def compute(self, op: str, numbers: List[float]) -> Union[float, int, Dict[str, Any]]:
        """Computes the requested statistic deterministically."""
        if not numbers:
            raise ValueError("Numeric dataset cannot be empty.")

        if op == "mean":
            res = statistics.mean(numbers)
            return int(res) if res.is_integer() else round(res, 6)

        elif op == "median":
            res = statistics.median(numbers)
            return int(res) if isinstance(res, float) and res.is_integer() else round(res, 6)

        elif op == "mode":
            res = statistics.mode(numbers)
            return int(res) if isinstance(res, float) and res.is_integer() else round(res, 6)

        elif op == "min":
            res = min(numbers)
            return int(res) if isinstance(res, float) and res.is_integer() else res

        elif op == "max":
            res = max(numbers)
            return int(res) if isinstance(res, float) and res.is_integer() else res

        elif op == "stdev":
            if len(numbers) < 2:
                raise ValueError("Standard deviation requires at least 2 data points.")
            res = statistics.stdev(numbers)
            return int(res) if res.is_integer() else round(res, 6)

        elif op == "variance":
            if len(numbers) < 2:
                raise ValueError("Variance requires at least 2 data points.")
            res = statistics.variance(numbers)
            return int(res) if res.is_integer() else round(res, 6)

        elif op == "summary":
            mean_val = statistics.mean(numbers)
            median_val = statistics.median(numbers)
            min_val = min(numbers)
            max_val = max(numbers)
            stdev_val = round(statistics.stdev(numbers), 6) if len(numbers) > 1 else 0.0
            return {
                "count": len(numbers),
                "min": int(min_val) if isinstance(min_val, float) and min_val.is_integer() else min_val,
                "max": int(max_val) if isinstance(max_val, float) and max_val.is_integer() else max_val,
                "mean": int(mean_val) if mean_val.is_integer() else round(mean_val, 6),
                "median": int(median_val) if isinstance(median_val, float) and median_val.is_integer() else round(median_val, 6),
                "stdev": int(stdev_val) if isinstance(stdev_val, float) and stdev_val.is_integer() else stdev_val,
            }

        raise ValueError(f"Unsupported statistics operation: '{op}'")

    def execute(self, query: str) -> ToolResult:
        """Executes the statistics calculation and returns ToolResult."""
        start_time = time.perf_counter()
        q = query.strip()
        m = self._query_pattern.match(q)

        if not m:
            exec_time = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                success=False,
                result=None,
                tool_name=self.name,
                execution_time_ms=exec_time,
                error="Could not parse a valid statistics query.",
                metadata={"calls_llm": False, "query": query},
            )

        op_raw, nums_raw = m.groups()
        numbers = self.parse_numbers(nums_raw)

        if numbers is None:
            exec_time = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                success=False,
                result=None,
                tool_name=self.name,
                execution_time_ms=exec_time,
                error="Invalid numeric input list. All values must be numbers.",
                metadata={"calls_llm": False, "query": query},
            )

        op = self._normalize_operation(op_raw)
        try:
            val = self.compute(op, numbers)
            exec_time = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                success=True,
                result=val,
                tool_name=self.name,
                execution_time_ms=exec_time,
                metadata={
                    "operation": op,
                    "count": len(numbers),
                    "calls_llm": False,
                },
            )
        except Exception as e:
            exec_time = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                success=False,
                result=None,
                tool_name=self.name,
                execution_time_ms=exec_time,
                error=str(e),
                metadata={"calls_llm": False, "query": query},
            )

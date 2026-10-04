from typing import Any, Dict, List, Optional
from .base import BaseTool
from .calculator import Calculator
from .unit_converter import UnitConverter
from .datetime_calculator import DateTimeCalculator
from .statistics_tool import StatisticsTool
from .text_analyzer import TextAnalyzer

class ToolRegistry:
    """Central registry for all deterministic tools in EcoMind."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        # Automatically register default deterministic tools
        self.register_tool(Calculator())
        self.register_tool(UnitConverter())
        self.register_tool(DateTimeCalculator())
        self.register_tool(StatisticsTool())
        self.register_tool(TextAnalyzer())

    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieve a registered tool by its name."""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """List metadata for all registered tools."""
        return [tool.get_info() for tool in self._tools.values()]

    def find_candidate_tool(self, query: str) -> Optional[BaseTool]:
        """Find the first deterministic tool capable of handling the query."""
        for tool in self._tools.values():
            if tool.can_handle(query):
                return tool
        return None

tool_registry = ToolRegistry()

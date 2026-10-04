from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass
class ToolResult:
    """Standard result object returned by deterministic tools."""
    success: bool
    result: Any
    tool_name: str
    execution_time_ms: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseTool(ABC):
    """Abstract base class for all deterministic tools in EcoMind."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the tool."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""
        pass

    @abstractmethod
    def can_handle(self, query: str) -> bool:
        """Deterministically determine if this tool can handle the query directly."""
        pass

    @abstractmethod
    def execute(self, query: str) -> ToolResult:
        """Execute the tool on the query without calling an LLM."""
        pass

    def get_info(self) -> Dict[str, Any]:
        """Return metadata about the tool."""
        return {
            "name": self.name,
            "description": self.description,
            "type": "deterministic_tool",
            "calls_llm": False,
        }

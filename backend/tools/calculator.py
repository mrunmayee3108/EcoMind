import ast
import operator
import re
import time
from typing import Any, Dict, Optional, Union
from .base import BaseTool, ToolResult

class Calculator(BaseTool):
    """Safe deterministic calculator that evaluates arithmetic expressions without calling an LLM."""
    
    name = "calculator"
    description = "Evaluates basic and intermediate arithmetic expressions deterministically using Python AST."
    
    _operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    _prefix_pattern = re.compile(
        r'^\s*(?:calculate|what\s+is\s+(?:the\s+)?|what\'s\s+(?:the\s+)?|compute\s+(?:the\s+)?|eval|evaluate\s+(?:the\s+)?|solve\s+(?:the\s+)?|find\s+(?:the\s+)?|math\s*:)\s*',
        re.IGNORECASE
    )

    def extract_expression(self, query: str) -> str:
        """Strip natural language prefix, translate arithmetic phrases, trailing punctuation, and equals signs."""
        cleaned = query.strip()
        cleaned = self._prefix_pattern.sub('', cleaned)
        cleaned = re.sub(r'[\?=\s]+$', '', cleaned).strip()

        # Prefix phrasing patterns:
        # e.g. "multiply 25 by 100", "product of 25 and 100"
        cleaned = re.sub(
            r'^\s*(?:multiply|product\s+of)\s+(\d+(?:\.\d+)?)\s+(?:by|and)\s+(\d+(?:\.\d+)?)\s*$',
            r'\1 * \2',
            cleaned,
            flags=re.IGNORECASE
        )
        # e.g. "divide 25 by 5", "quotient of 25 and 5"
        cleaned = re.sub(
            r'^\s*(?:divide|quotient\s+of)\s+(\d+(?:\.\d+)?)\s+(?:by|and)\s+(\d+(?:\.\d+)?)\s*$',
            r'\1 / \2',
            cleaned,
            flags=re.IGNORECASE
        )
        # e.g. "add 25 and 10", "add 25 to 10", "sum of 25 and 10"
        cleaned = re.sub(
            r'^\s*(?:add|sum\s+of)\s+(\d+(?:\.\d+)?)\s+(?:and|to)\s+(\d+(?:\.\d+)?)\s*$',
            r'\1 + \2',
            cleaned,
            flags=re.IGNORECASE
        )
        # e.g. "subtract 10 from 25"
        cleaned = re.sub(
            r'^\s*subtract\s+(\d+(?:\.\d+)?)\s+from\s+(\d+(?:\.\d+)?)\s*$',
            r'\2 - \1',
            cleaned,
            flags=re.IGNORECASE
        )
        # e.g. "difference between 100 and 25"
        cleaned = re.sub(
            r'^\s*difference\s+between\s+(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)\s*$',
            r'\1 - \2',
            cleaned,
            flags=re.IGNORECASE
        )

        # Percentage: "10% of 500", "10 percent of 500"
        cleaned = re.sub(
            r'(\d+(?:\.\d+)?)\s*(?:%|\s*percent)\s+of\s+(\d+(?:\.\d+)?)',
            r'(\1 / 100) * \2',
            cleaned,
            flags=re.IGNORECASE
        )

        # Infix phrases between numbers / parentheses:
        cleaned = re.sub(r'(?<=\d|\))\s+(?:times\s+of|times)\s+(?=\d|\()', ' * ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(?<=\d|\))\s+multiplied\s+by\s+(?=\d|\()', ' * ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(?<=\d|\))\s+divided\s+by\s+(?=\d|\()', ' / ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(?<=\d|\))\s+plus\s+(?=\d|\()', ' + ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(?<=\d|\))\s+minus\s+(?=\d|\()', ' - ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(?<=\d|\))\s+(?:to\s+the\s+power\s+of|power\s+of)\s+(?=\d|\()', ' ** ', cleaned, flags=re.IGNORECASE)

        # Replace carat ^ with ** for power if used
        cleaned = cleaned.replace('^', '**')
        # Replace x or X with * if used between numbers (e.g., 5 x 4)
        cleaned = re.sub(r'(?<=\d)\s*[xX]\s*(?=\d)', ' * ', cleaned)
        return cleaned

    def can_handle(self, query: str) -> bool:
        """Check if query is or contains a clean arithmetic expression."""
        expr = self.extract_expression(query)
        if not expr:
            return False
        
        # Must contain at least one digit and only allowed math characters
        if not re.search(r'\d', expr):
            return False
        if not re.match(r'^[\d\s\+\-\*\/\%\.\(\)]+$', expr):
            return False

        try:
            parsed = ast.parse(expr, mode='eval')
            return self._validate_ast(parsed.body)
        except Exception:
            return False

    def _validate_ast(self, node: ast.AST) -> bool:
        """Verify that the AST contains only numbers, unary, and binary operations."""
        if isinstance(node, (ast.Constant, ast.Num)):
            return True
        elif isinstance(node, ast.BinOp):
            if type(node.op) not in self._operators:
                return False
            # Check exponent magnitude to prevent ReDoS / CPU lockup
            if isinstance(node.op, ast.Pow) and isinstance(node.right, (ast.Constant, ast.Num)):
                val = getattr(node.right, 'n', getattr(node.right, 'value', 0))
                if isinstance(val, (int, float)) and val > 1000:
                    return False
            return self._validate_ast(node.left) and self._validate_ast(node.right)
        elif isinstance(node, ast.UnaryOp):
            if type(node.op) not in self._operators:
                return False
            return self._validate_ast(node.operand)
        return False

    def _eval_node(self, node: ast.AST) -> Union[int, float]:
        if isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float)):
                raise TypeError(f"Unsupported constant type: {type(node.value)}")
            return node.value
        elif isinstance(node, ast.Num):  # for older Python AST compatibility
            return node.n
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op = self._operators.get(type(node.op))
            if op is None:
                raise TypeError(f"Unsupported operator: {type(node.op)}")
            
            # Division by zero check
            if type(node.op) in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                raise ZeroDivisionError("Division or modulo by zero is not allowed.")
            
            # Guard against huge power calculations
            if type(node.op) == ast.Pow:
                if right > 1000 or (left > 10 and right > 300):
                    raise ValueError("Exponentiation values exceed safety limits.")

            return op(left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op = self._operators.get(type(node.op))
            if op is None:
                raise TypeError(f"Unsupported unary operator: {type(node.op)}")
            return op(operand)
        else:
            raise TypeError(f"Unsupported expression node: {type(node)}")

    def evaluate_expression(self, expression: str) -> Union[int, float]:
        """Safely parse and evaluate the arithmetic expression."""
        try:
            node = ast.parse(expression, mode='eval')
            if not self._validate_ast(node.body):
                raise ValueError("Expression contains unauthorized operations.")
            raw_result = self._eval_node(node.body)
            
            # If float is an exact integer, return int for clean formatting
            if isinstance(raw_result, float) and raw_result.is_integer():
                return int(raw_result)
            return raw_result
        except ZeroDivisionError:
            raise ValueError("Division by zero is not allowed.")
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Invalid arithmetic expression: {str(e)}")

    @classmethod
    def evaluate(cls, expression: str) -> Union[int, float]:
        """Classmethod kept for backward compatibility."""
        instance = cls()
        expr = instance.extract_expression(expression)
        return instance.evaluate_expression(expr)

    def execute(self, query: str) -> ToolResult:
        """Executes the calculator tool and records real latency."""
        start_time = time.perf_counter()
        expr = self.extract_expression(query)
        try:
            val = self.evaluate_expression(expr)
            exec_time = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                success=True,
                result=val,
                tool_name=self.name,
                execution_time_ms=exec_time,
                metadata={
                    "expression": expr,
                    "method": "python_ast_eval",
                    "calls_llm": False
                }
            )
        except Exception as e:
            exec_time = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                success=False,
                result=None,
                tool_name=self.name,
                execution_time_ms=exec_time,
                error=str(e),
                metadata={"expression": expr}
            )

    @staticmethod
    def get_info() -> Dict[str, Any]:
        return {
            "name": "calculator",
            "description": "Evaluates basic arithmetic expressions deterministically.",
            "type": "deterministic-tool",
            "calls_llm": False
        }

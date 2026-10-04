import unittest
from tools.tool_registry import tool_registry, ToolRegistry
from tools.calculator import Calculator

class TestToolRegistry(unittest.TestCase):
    def test_default_registration(self):
        tools = tool_registry.list_tools()
        names = [t["name"] for t in tools]
        self.assertIn("calculator", names)

    def test_get_tool(self):
        tool = tool_registry.get_tool("calculator")
        self.assertIsNotNone(tool)
        self.assertIsInstance(tool, Calculator)
        self.assertEqual(tool.name, "calculator")

    def test_find_candidate_tool(self):
        # Math queries should match calculator
        candidate = tool_registry.find_candidate_tool("15 * 6")
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.name, "calculator")

        candidate2 = tool_registry.find_candidate_tool("what is (20 + 30) / 5?")
        self.assertIsNotNone(candidate2)
        self.assertEqual(candidate2.name, "calculator")

        # Non-math query should not match
        non_candidate = tool_registry.find_candidate_tool("Explain what photosynthesis is.")
        self.assertIsNone(non_candidate)

if __name__ == "__main__":
    unittest.main()

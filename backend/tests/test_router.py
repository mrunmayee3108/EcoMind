import unittest

from router.query_analyzer import QueryAnalyzer
from router.routing_policy import RoutingPolicy


class TestRouter(unittest.TestCase):

    def setUp(self):
        self.analyzer = QueryAnalyzer()
        self.router = RoutingPolicy()

    def test_calculation(self):
        analysis = self.analyzer.analyze("Calculate 25 * 48")

        self.assertEqual(
            analysis.task_type,
            "calculation"
        )

        self.assertEqual(
            self.router.select_route(analysis),
            "calculator"
        )

    def test_simple_query(self):
        analysis = self.analyzer.analyze(
            "What is Python?"
        )

        self.assertEqual(
            self.router.select_route(analysis),
            "small"
        )

    def test_reasoning_query(self):
        analysis = self.analyzer.analyze(
            "Compare BFS and DFS and explain why they differ."
        )

        self.assertEqual(
            self.router.select_route(analysis),
            "large"
        )

    def test_unit_conversion_routing(self):
        analysis = self.analyzer.analyze("convert 100 km to miles")
        self.assertEqual(analysis.task_type, "unit_conversion")
        self.assertTrue(analysis.requires_tool)
        self.assertEqual(analysis.candidate_tool, "unit_converter")
        self.assertEqual(self.router.select_route(analysis), "unit_converter")

    def test_datetime_routing(self):
        analysis = self.analyzer.analyze("days between 2024-01-01 and 2024-01-15")
        self.assertEqual(analysis.task_type, "date_time")
        self.assertTrue(analysis.requires_tool)
        self.assertEqual(analysis.candidate_tool, "datetime_calculator")
        self.assertEqual(self.router.select_route(analysis), "datetime_calculator")

    def test_statistics_routing(self):
        analysis = self.analyzer.analyze("mean of 10, 20, 30, 40")
        self.assertEqual(analysis.task_type, "statistics")
        self.assertTrue(analysis.requires_tool)
        self.assertEqual(analysis.candidate_tool, "statistics_tool")
        self.assertEqual(self.router.select_route(analysis), "statistics_tool")

    def test_text_analysis_routing(self):
        analysis = self.analyzer.analyze('word count of "EcoMind Control Plane"')
        self.assertEqual(analysis.task_type, "text_analysis")
        self.assertTrue(analysis.requires_tool)
        self.assertEqual(analysis.candidate_tool, "text_analyzer")
        self.assertEqual(self.router.select_route(analysis), "text_analyzer")

    def test_medium_complexity_query(self):
        analysis = self.analyzer.analyze("Summarize the main differences between SQL and NoSQL databases.")
        self.assertEqual(analysis.complexity, "medium")
        self.assertFalse(analysis.requires_tool)
        self.assertEqual(self.router.select_route(analysis), "medium")


if __name__ == "__main__":
    unittest.main()
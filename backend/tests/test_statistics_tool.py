import unittest
from tools.statistics_tool import StatisticsTool
from tools.tool_registry import ToolRegistry


class TestStatisticsTool(unittest.TestCase):
    def setUp(self):
        self.stats = StatisticsTool()
        self.registry = ToolRegistry()

    # --- 1. Successful Operations ---
    def test_mean(self):
        # Even sum
        res1 = self.stats.execute("mean of 10, 20, 30")
        self.assertTrue(res1.success)
        self.assertEqual(res1.result, 20)
        self.assertEqual(res1.tool_name, "statistics_tool")
        self.assertFalse(res1.metadata["calls_llm"])

        # Decimal mean
        res2 = self.stats.execute("average of 1, 2, 4")
        self.assertTrue(res2.success)
        self.assertAlmostEqual(res2.result, 2.333333, places=5)

    def test_median(self):
        # Odd count
        res1 = self.stats.execute("median of [1, 5, 2, 8, 7]")
        self.assertTrue(res1.success)
        self.assertEqual(res1.result, 5)

        # Even count (average of two middle numbers)
        res2 = self.stats.execute("median of 10, 20, 30, 40")
        self.assertTrue(res2.success)
        self.assertEqual(res2.result, 25)

    def test_min_and_max(self):
        res_min = self.stats.execute("min of 15, 3, 42, -5, 10")
        self.assertTrue(res_min.success)
        self.assertEqual(res_min.result, -5)

        res_max = self.stats.execute("maximum of 15, 3, 42, -5, 10")
        self.assertTrue(res_max.success)
        self.assertEqual(res_max.result, 42)

    def test_stdev_and_variance(self):
        # Sample: [2, 4, 4, 4, 5, 5, 7, 9] -> mean=5, var=4.5714..., stdev=2.13809...
        res_std = self.stats.execute("standard deviation of 2, 4, 4, 4, 5, 5, 7, 9")
        self.assertTrue(res_std.success)
        self.assertAlmostEqual(res_std.result, 2.13809, places=4)

        res_var = self.stats.execute("variance of 10, 20, 30")
        self.assertTrue(res_var.success)
        self.assertEqual(res_var.result, 100)

    def test_summary(self):
        res = self.stats.execute("summary of [10, 20, 30, 40, 50]")
        self.assertTrue(res.success)
        data = res.result
        self.assertEqual(data["count"], 5)
        self.assertEqual(data["min"], 10)
        self.assertEqual(data["max"], 50)
        self.assertEqual(data["mean"], 30)
        self.assertEqual(data["median"], 30)
        self.assertAlmostEqual(data["stdev"], 15.811388, places=4)

    # --- 2. Invalid Input Tests ---
    def test_invalid_input(self):
        # Non-numeric item in list
        res1 = self.stats.execute("mean of 10, 20, apple, 40")
        self.assertFalse(res1.success)
        self.assertIn("Invalid numeric input", res1.error)

        # Standard deviation with only 1 element
        res2 = self.stats.execute("stdev of 10")
        self.assertFalse(res2.success)
        self.assertIn("requires at least 2", res2.error)

    # --- 3. Conservative can_handle & False Positives ---
    def test_can_handle_true(self):
        self.assertTrue(self.stats.can_handle("mean of 1, 2, 3, 4, 5"))
        self.assertTrue(self.stats.can_handle("what is the average of 10, 20, 30?"))
        self.assertTrue(self.stats.can_handle("calculate the median of [5, 10, 15]"))
        self.assertTrue(self.stats.can_handle("stdev of 4, 8, 6, 5, 3"))
        self.assertTrue(self.stats.can_handle("min of 10, 20, 5"))

    def test_can_handle_false_positives(self):
        # Conversational English with "average" or "mean"
        self.assertFalse(self.stats.can_handle("What is the average speed of an eagle?"))
        self.assertFalse(self.stats.can_handle("What does this word mean?"))
        self.assertFalse(self.stats.can_handle("Find the minimum age to vote in France"))
        self.assertFalse(self.stats.can_handle("Explain standard deviation to a beginner"))
        self.assertFalse(self.stats.can_handle("Summary of the French Revolution"))

        # Stdev with 1 element should be rejected by can_handle
        self.assertFalse(self.stats.can_handle("stdev of 5"))

        # Non-numeric list rejected by can_handle
        self.assertFalse(self.stats.can_handle("mean of red, green, blue"))

    # --- 4. ToolRegistry Candidate Matching ---
    def test_registry_candidate_matching(self):
        tool = self.registry.find_candidate_tool("calculate the mean of 10, 20, 30")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "statistics_tool")

        # Other tools still resolve correctly
        dt_tool = self.registry.find_candidate_tool("days between 2024-01-01 and 2024-01-10")
        self.assertIsNotNone(dt_tool)
        self.assertEqual(dt_tool.name, "datetime_calculator")

        calc_tool = self.registry.find_candidate_tool("25 * 4")
        self.assertIsNotNone(calc_tool)
        self.assertEqual(calc_tool.name, "calculator")


if __name__ == "__main__":
    unittest.main()

import unittest
from tools.datetime_calculator import DateTimeCalculator
from tools.tool_registry import ToolRegistry


class TestDateTimeCalculator(unittest.TestCase):
    def setUp(self):
        self.dt_calc = DateTimeCalculator()
        self.registry = ToolRegistry()

    # --- 1. Successful Cases ---
    def test_date_difference(self):
        # ISO format
        res1 = self.dt_calc.execute("days between 2024-01-01 and 2024-01-15")
        self.assertTrue(res1.success)
        self.assertEqual(res1.result, "14 days")
        self.assertEqual(res1.tool_name, "datetime_calculator")
        self.assertEqual(res1.metadata["details"]["days"], 14)

        # Natural language phrasing with month name
        res2 = self.dt_calc.execute("how many days between January 1, 2024 and January 10, 2024?")
        self.assertTrue(res2.success)
        self.assertEqual(res2.result, "9 days")

        # Reversed order should still give positive absolute difference
        res3 = self.dt_calc.execute("difference between 2024-02-10 and 2024-02-01")
        self.assertTrue(res3.success)
        self.assertEqual(res3.result, "9 days")

    def test_date_offsets(self):
        # Days after
        res1 = self.dt_calc.execute("what date is 10 days after 2024-01-01?")
        self.assertTrue(res1.success)
        self.assertEqual(res1.result, "2024-01-11")

        # Days before
        res2 = self.dt_calc.execute("5 days before 2024-03-01")
        self.assertTrue(res2.success)
        # 2024 is a leap year, so Feb has 29 days: March 1 - 5 days = Feb 25
        self.assertEqual(res2.result, "2024-02-25")

        # Weeks after
        res3 = self.dt_calc.execute("2 weeks after 2024-01-01")
        self.assertTrue(res3.success)
        self.assertEqual(res3.result, "2024-01-15")

        # Arithmetic notation: date + N days
        res4 = self.dt_calc.execute("2024-05-01 + 20 days")
        self.assertTrue(res4.success)
        self.assertEqual(res4.result, "2024-05-21")

        # Arithmetic notation: date - N days
        res5 = self.dt_calc.execute("2024-05-20 - 10 days")
        self.assertTrue(res5.success)
        self.assertEqual(res5.result, "2024-05-10")

    def test_day_of_week(self):
        # 2024-01-01 was a Monday
        res1 = self.dt_calc.execute("what day of the week was 2024-01-01?")
        self.assertTrue(res1.success)
        self.assertEqual(res1.result, "Monday")

        # 2024-12-25 will be a Wednesday
        res2 = self.dt_calc.execute("day of week for December 25, 2024")
        self.assertTrue(res2.success)
        self.assertEqual(res2.result, "Wednesday")

    def test_leap_year(self):
        res1 = self.dt_calc.execute("is 2024 a leap year?")
        self.assertTrue(res1.success)
        self.assertTrue(res1.metadata["details"]["is_leap_year"])
        self.assertIn("is a leap year", res1.result)

        res2 = self.dt_calc.execute("is 2023 a leap year?")
        self.assertTrue(res2.success)
        self.assertFalse(res2.metadata["details"]["is_leap_year"])
        self.assertIn("is not a leap year", res2.result)

    # --- 2. Invalid Input Tests ---
    def test_invalid_input(self):
        # Invalid day for month (Feb 30)
        res1 = self.dt_calc.execute("what date is 5 days after 2024-02-30")
        self.assertFalse(res1.success)
        self.assertIn("Could not parse", res1.error)

        # Unparseable query string
        res2 = self.dt_calc.execute("random query with no dates")
        self.assertFalse(res2.success)

    # --- 3. Conservative can_handle & False Positives ---
    def test_can_handle_true(self):
        self.assertTrue(self.dt_calc.can_handle("days between 2024-01-01 and 2024-02-01"))
        self.assertTrue(self.dt_calc.can_handle("what date is 30 days after 2024-06-01?"))
        self.assertTrue(self.dt_calc.can_handle("is 2028 a leap year?"))
        self.assertTrue(self.dt_calc.can_handle("what day of the week was 2023-07-04?"))
        self.assertTrue(self.dt_calc.can_handle("2024-01-01 + 10 days"))

    def test_can_handle_false_positives(self):
        # Conversational English mentioning dates or time
        self.assertFalse(self.dt_calc.can_handle("Who was born on July 4, 1776?"))
        self.assertFalse(self.dt_calc.can_handle("I like going on dates in Paris"))
        self.assertFalse(self.dt_calc.can_handle("How many days in a week?"))
        self.assertFalse(self.dt_calc.can_handle("Explain the Gregorian calendar"))
        self.assertFalse(self.dt_calc.can_handle("Calculate 25 * 48"))
        self.assertFalse(self.dt_calc.can_handle("convert 50 km to miles"))

        # Queries with invalid date values should be rejected by can_handle
        self.assertFalse(self.dt_calc.can_handle("days between 2024-02-31 and 2024-03-01"))

    # --- 4. ToolRegistry Candidate Matching ---
    def test_registry_candidate_matching(self):
        tool = self.registry.find_candidate_tool("days between 2024-01-01 and 2024-01-10")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "datetime_calculator")

        # Unit converter and calculator still match their respective queries
        unit_tool = self.registry.find_candidate_tool("convert 100 km to miles")
        self.assertIsNotNone(unit_tool)
        self.assertEqual(unit_tool.name, "unit_converter")

        calc_tool = self.registry.find_candidate_tool("what is 50 * 20?")
        self.assertIsNotNone(calc_tool)
        self.assertEqual(calc_tool.name, "calculator")


if __name__ == "__main__":
    unittest.main()

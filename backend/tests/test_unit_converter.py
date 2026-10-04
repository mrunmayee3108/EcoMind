import unittest
from tools.unit_converter import UnitConverter
from tools.tool_registry import ToolRegistry


class TestUnitConverter(unittest.TestCase):
    def setUp(self):
        self.converter = UnitConverter()
        self.registry = ToolRegistry()

    # --- 1. Successful Conversions ---
    def test_length_conversions(self):
        # Meters to Kilometers
        self.assertEqual(self.converter.convert(1000, "meters", "km"), 1.0)
        self.assertEqual(self.converter.convert(5, "km", "m"), 5000.0)
        # Inches to cm
        self.assertAlmostEqual(self.converter.convert(1, "inch", "cm"), 2.54, places=4)
        # Miles to meters
        self.assertAlmostEqual(self.converter.convert(1, "mile", "m"), 1609.344, places=3)
        # Feet to inches
        self.assertAlmostEqual(self.converter.convert(2, "feet", "inches"), 24.0, places=4)

    def test_mass_conversions(self):
        # Kilograms to grams
        self.assertEqual(self.converter.convert(2.5, "kg", "g"), 2500.0)
        # Grams to milligrams
        self.assertAlmostEqual(self.converter.convert(1, "g", "mg"), 1000.0, places=4)
        # Pounds to kg
        self.assertAlmostEqual(self.converter.convert(10, "lbs", "kg"), 4.53592, places=3)
        # Ounces to grams
        self.assertAlmostEqual(self.converter.convert(1, "oz", "g"), 28.3495, places=3)

    def test_temperature_conversions(self):
        # Celsius to Fahrenheit (freezing point)
        self.assertAlmostEqual(self.converter.convert(0, "c", "f"), 32.0, places=4)
        # Boiling point
        self.assertAlmostEqual(self.converter.convert(100, "c", "f"), 212.0, places=4)
        # Negative temperature equality point: -40 C == -40 F
        self.assertAlmostEqual(self.converter.convert(-40, "c", "f"), -40.0, places=4)
        # Fahrenheit to Celsius
        self.assertAlmostEqual(self.converter.convert(98.6, "f", "c"), 37.0, places=2)
        # Celsius to Kelvin
        self.assertAlmostEqual(self.converter.convert(25, "c", "k"), 298.15, places=4)
        # Kelvin to Celsius
        self.assertAlmostEqual(self.converter.convert(300, "k", "c"), 26.85, places=2)

    def test_natural_language_queries(self):
        # "convert 100 km to miles"
        res1 = self.converter.execute("convert 100 km to miles")
        self.assertTrue(res1.success)
        self.assertAlmostEqual(res1.result, 62.1371, places=3)
        self.assertEqual(res1.tool_name, "unit_converter")
        self.assertFalse(res1.metadata["calls_llm"])

        # "what is 50 kg in lbs?"
        res2 = self.converter.execute("what is 50 kg in lbs?")
        self.assertTrue(res2.success)
        self.assertAlmostEqual(res2.result, 110.231, places=2)

        # "how many feet in 12 inches"
        res3 = self.converter.execute("how many feet in 12 inches")
        self.assertTrue(res3.success)
        self.assertEqual(res3.result, 1)

        # "how much is 100 degrees celsius in fahrenheit?"
        res4 = self.converter.execute("how much is 100 degrees celsius in fahrenheit?")
        self.assertTrue(res4.success)
        self.assertEqual(res4.result, 212)

    # --- 2. Invalid Input Tests ---
    def test_invalid_input(self):
        # Non-parseable query
        res = self.converter.execute("this is not a conversion")
        self.assertFalse(res.success)
        self.assertIsNone(res.result)
        self.assertIn("Could not parse", res.error)

        # Negative Kelvin
        with self.assertRaises(ValueError):
            self.converter.convert(-5, "k", "c")

    # --- 3. Unsupported Units & Dimension Mismatch ---
    def test_unsupported_units(self):
        # Unsupported units like liters / gallons
        with self.assertRaises(ValueError):
            self.converter.convert(10, "liters", "gallons")

        # Incompatible dimensions (length to mass)
        with self.assertRaises(ValueError):
            self.converter.convert(10, "meters", "kilograms")

    # --- 4. Conservative can_handle & False Positives ---
    def test_can_handle_true(self):
        self.assertTrue(self.converter.can_handle("convert 100 km to miles"))
        self.assertTrue(self.converter.can_handle("what is 5.5 kg in pounds?"))
        self.assertTrue(self.converter.can_handle("how many cm in 2 meters?"))
        self.assertTrue(self.converter.can_handle("32 f to c"))
        self.assertTrue(self.converter.can_handle("how many feet in 3 yards?"))

    def test_can_handle_false_positives(self):
        # Conversational English with "to" or "in"
        self.assertFalse(self.converter.can_handle("Who went to the store in Paris?"))
        self.assertFalse(self.converter.can_handle("I want to convert my house into an office"))
        self.assertFalse(self.converter.can_handle("Explain the theory of relativity"))
        self.assertFalse(self.converter.can_handle("How many days in a leap year?"))
        self.assertFalse(self.converter.can_handle("What is the capital of France?"))

        # Incompatible dimensions should be rejected by can_handle
        self.assertFalse(self.converter.can_handle("convert 10 meters to kilograms"))
        self.assertFalse(self.converter.can_handle("what is 5 kg in celsius?"))

        # Unsupported units should be rejected by can_handle
        self.assertFalse(self.converter.can_handle("convert 10 liters to gallons"))
        self.assertFalse(self.converter.can_handle("what is 5 dollars in euros?"))

        # Negative Kelvin physically invalid
        self.assertFalse(self.converter.can_handle("convert -10 k to c"))

    # --- 5. ToolRegistry Candidate Matching ---
    def test_registry_candidate_matching(self):
        tool = self.registry.find_candidate_tool("convert 500 meters to feet")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "unit_converter")

        # Calculator must still match math queries
        calc_tool = self.registry.find_candidate_tool("what is 25 * 4?")
        self.assertIsNotNone(calc_tool)
        self.assertEqual(calc_tool.name, "calculator")


if __name__ == "__main__":
    unittest.main()

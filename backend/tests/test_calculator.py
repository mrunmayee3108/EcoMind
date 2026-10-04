import unittest
from tools.calculator import Calculator

class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = Calculator()

    def test_basic_arithmetic(self):
        self.assertEqual(self.calc.evaluate("2 + 2"), 4)
        self.assertEqual(self.calc.evaluate("10 - 4"), 6)
        self.assertEqual(self.calc.evaluate("7 * 8"), 56)
        self.assertEqual(self.calc.evaluate("20 / 4"), 5)
        self.assertEqual(self.calc.evaluate("17 // 3"), 5)
        self.assertEqual(self.calc.evaluate("17 % 3"), 2)
        self.assertEqual(self.calc.evaluate("2 ** 5"), 32)

    def test_order_of_operations_and_parens(self):
        self.assertEqual(self.calc.evaluate("2 + 3 * 4"), 14)
        self.assertEqual(self.calc.evaluate("(2 + 3) * 4"), 20)
        self.assertEqual(self.calc.evaluate("100 / (5 + 5) * 2"), 20)

    def test_natural_language_queries(self):
        self.assertEqual(self.calc.evaluate("what is 15 * 4?"), 60)
        self.assertEqual(self.calc.evaluate("Calculate 100 / 4"), 25)
        self.assertEqual(self.calc.evaluate("solve 2^8"), 256)
        self.assertEqual(self.calc.evaluate("math: 50 + 25 ="), 75)
        self.assertEqual(self.calc.evaluate("25 * 100"), 2500)
        self.assertEqual(self.calc.evaluate("25 times 100"), 2500)
        self.assertEqual(self.calc.evaluate("calculate 25 times 100"), 2500)
        self.assertEqual(self.calc.evaluate("calculate 25 times of 100"), 2500)
        self.assertEqual(self.calc.evaluate("what is 25 multiplied by 100"), 2500)
        self.assertEqual(self.calc.evaluate("multiply 25 by 100"), 2500)
        self.assertEqual(self.calc.evaluate("25 plus 10"), 35)
        self.assertEqual(self.calc.evaluate("25 minus 10"), 15)
        self.assertEqual(self.calc.evaluate("25 divided by 5"), 5)
        self.assertEqual(self.calc.evaluate("what is 10% of 500"), 50)

    def test_decimals_and_unary(self):
        self.assertEqual(self.calc.evaluate("-5 + 10"), 5)
        self.assertAlmostEqual(self.calc.evaluate("3.5 * 2"), 7)
        self.assertAlmostEqual(self.calc.evaluate("0.1 + 0.2"), 0.3, places=5)

    def test_can_handle(self):
        self.assertTrue(self.calc.can_handle("2 + 2"))
        self.assertTrue(self.calc.can_handle("what is 45 * 2?"))
        self.assertTrue(self.calc.can_handle("(10 + 20) / 2"))
        self.assertTrue(self.calc.can_handle("calculate 25 times of 100"))
        self.assertTrue(self.calc.can_handle("25 times 100"))
        self.assertTrue(self.calc.can_handle("what is 25 multiplied by 100"))
        self.assertTrue(self.calc.can_handle("multiply 25 by 100"))
        self.assertTrue(self.calc.can_handle("25 plus 10"))
        self.assertTrue(self.calc.can_handle("25 minus 10"))
        self.assertTrue(self.calc.can_handle("25 divided by 5"))
        self.assertTrue(self.calc.can_handle("what is 10% of 500"))

        # Negative test cases (should NOT be handled by calculator)
        self.assertFalse(self.calc.can_handle("What is Python?"))
        self.assertFalse(self.calc.can_handle("Explain multiplication."))
        self.assertFalse(self.calc.can_handle("Why is 25 important?"))
        self.assertFalse(self.calc.can_handle("Compare multiplication and addition."))
        self.assertFalse(self.calc.can_handle("Who was the 16th president of the US?"))
        self.assertFalse(self.calc.can_handle("Write a python script to sort a list"))
        self.assertFalse(self.calc.can_handle("hello world"))

    def test_safety_and_errors(self):
        with self.assertRaises(ValueError):
            self.calc.evaluate("10 / 0")

        # Code injection attempts should fail AST validation
        with self.assertRaises(ValueError):
            self.calc.evaluate("__import__('os').system('ls')")

        with self.assertRaises(ValueError):
            self.calc.evaluate("open('test.txt', 'w')")

    def test_tool_execute(self):
        res = self.calc.execute("calculate 25 times of 100")
        self.assertTrue(res.success)
        self.assertEqual(res.result, 2500)
        self.assertEqual(res.tool_name, "calculator")
        self.assertGreaterEqual(res.execution_time_ms, 0)
        self.assertFalse(res.metadata["calls_llm"])

if __name__ == "__main__":
    unittest.main()

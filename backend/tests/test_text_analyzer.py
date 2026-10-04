import unittest
from tools.text_analyzer import TextAnalyzer
from tools.tool_registry import ToolRegistry


class TestTextAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = TextAnalyzer()
        self.registry = ToolRegistry()

    # --- 1. Successful Operations ---
    def test_word_count(self):
        # Quoted string
        res1 = self.analyzer.execute('word count of "The quick brown fox jumps over the lazy dog."')
        self.assertTrue(res1.success)
        self.assertEqual(res1.result, 9)
        self.assertEqual(res1.tool_name, "text_analyzer")
        self.assertFalse(res1.metadata["calls_llm"])

        # Colon format
        res2 = self.analyzer.execute('word count: Sustainable artificial intelligence saves energy.')
        self.assertTrue(res2.success)
        self.assertEqual(res2.result, 5)

        # "how many words in ..."
        res3 = self.analyzer.execute('how many words in "EcoMind control plane"')
        self.assertTrue(res3.success)
        self.assertEqual(res3.result, 3)

        # Hyphenated word and apostrophe handling
        words = self.analyzer.extract_words("state-of-the-art AI shouldn't over-consume")
        self.assertEqual(len(words), 4)

    def test_character_count(self):
        # Total characters including spaces
        res1 = self.analyzer.execute('character count of "EcoMind 2.0"')
        self.assertTrue(res1.success)
        self.assertEqual(res1.result, 11)

        # "how many characters in ..."
        res2 = self.analyzer.execute('how many characters in "hello world"')
        self.assertTrue(res2.success)
        self.assertEqual(res2.result, 11)

    def test_sentence_count(self):
        sample = "EcoMind is fast. Is it sustainable? Absolutely!"
        res = self.analyzer.execute(f'sentence count of "{sample}"')
        self.assertTrue(res.success)
        self.assertEqual(res.result, 3)

    def test_word_frequency(self):
        text = "green energy is green and clean"
        res = self.analyzer.execute(f'word frequency in "{text}"')
        self.assertTrue(res.success)
        freq = res.result
        self.assertEqual(freq["green"], 2)
        self.assertEqual(freq["energy"], 1)
        self.assertEqual(freq["clean"], 1)

    def test_summary_analysis(self):
        text = "EcoMind optimizes inference. It saves power and carbon."
        res = self.analyzer.execute(f'analyze text: "{text}"')
        self.assertTrue(res.success)
        summary = res.result
        self.assertEqual(summary["word_count"], 8)
        self.assertEqual(summary["sentence_count"], 2)
        self.assertGreater(summary["character_count_total"], 0)
        self.assertIn("ecomind", summary["top_words"])

    # --- 2. Invalid Input Tests ---
    def test_invalid_input(self):
        # Unparseable query with no target text
        res = self.analyzer.execute("this is not a text analysis task")
        self.assertFalse(res.success)
        self.assertIn("Could not parse", res.error)

    # --- 3. Conservative can_handle & False Positives ---
    def test_can_handle_true(self):
        self.assertTrue(self.analyzer.can_handle('word count of "The quick brown fox"'))
        self.assertTrue(self.analyzer.can_handle('how many words in "Hello world!"?'))
        self.assertTrue(self.analyzer.can_handle('character count: Test string'))
        self.assertTrue(self.analyzer.can_handle('count sentences in "One. Two? Three!"'))
        self.assertTrue(self.analyzer.can_handle('analyze text: "Sample paragraph here."'))

    def test_can_handle_false_positives(self):
        # Conversational English / World Knowledge
        self.assertFalse(self.analyzer.can_handle("How many words in the English dictionary?"))
        self.assertFalse(self.analyzer.can_handle("How many words can a human speak per minute?"))
        self.assertFalse(self.analyzer.can_handle("How many characters are in Hamlet?"))
        self.assertFalse(self.analyzer.can_handle("What is a character count?"))
        self.assertFalse(self.analyzer.can_handle("Explain the importance of words"))

        # Other deterministic tools
        self.assertFalse(self.analyzer.can_handle("Calculate 25 * 48"))
        self.assertFalse(self.analyzer.can_handle("convert 100 km to miles"))
        self.assertFalse(self.analyzer.can_handle("days between 2024-01-01 and 2024-01-10"))
        self.assertFalse(self.analyzer.can_handle("mean of 1, 2, 3, 4"))

    # --- 4. ToolRegistry Candidate Matching ---
    def test_registry_candidate_matching(self):
        tool = self.registry.find_candidate_tool('word count of "EcoMind Control Plane"')
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "text_analyzer")

        # Prior tools still match accurately
        stats_tool = self.registry.find_candidate_tool("mean of 10, 20, 30")
        self.assertIsNotNone(stats_tool)
        self.assertEqual(stats_tool.name, "statistics_tool")

        calc_tool = self.registry.find_candidate_tool("100 / 4")
        self.assertIsNotNone(calc_tool)
        self.assertEqual(calc_tool.name, "calculator")


if __name__ == "__main__":
    unittest.main()

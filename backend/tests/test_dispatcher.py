import unittest
from unittest.mock import MagicMock, patch
from models.dispatcher import ModelDispatcher, ProviderUnavailableError
from models.provider import ProviderResponse, TokenUsage

class TestModelDispatcher(unittest.TestCase):
    def setUp(self):
        self.mock_groq = MagicMock()
        self.mock_gemini = MagicMock()
        self.mock_local = MagicMock()
        self.dispatcher = ModelDispatcher(
            groq_provider=self.mock_groq,
            gemini_provider=self.mock_gemini,
            local_provider=self.mock_local,
        )

    def test_resolve_tier(self):
        with patch("models.dispatcher.settings") as mock_settings:
            mock_settings.SMALL_PROVIDER = "groq"
            mock_settings.SMALL_MODEL = "openai/gpt-oss-20b"
            mock_settings.MEDIUM_PROVIDER = "gemini"
            mock_settings.MEDIUM_MODEL = "gemini-flash-latest"
            mock_settings.LARGE_PROVIDER = "groq"
            mock_settings.LARGE_MODEL = "openai/gpt-oss-120b"

            self.assertEqual(self.dispatcher.resolve_tier("small"), ("groq", "openai/gpt-oss-20b"))
            self.assertEqual(self.dispatcher.resolve_tier("medium"), ("gemini", "gemini-flash-latest"))
            self.assertEqual(self.dispatcher.resolve_tier("large"), ("groq", "openai/gpt-oss-120b"))

            with self.assertRaises(ValueError):
                self.dispatcher.resolve_tier("ultra_huge")

    def test_get_provider(self):
        self.assertEqual(self.dispatcher.get_provider("groq"), self.mock_groq)
        self.assertEqual(self.dispatcher.get_provider("gemini"), self.mock_gemini)
        self.assertEqual(self.dispatcher.get_provider("google"), self.mock_gemini)
        self.assertEqual(self.dispatcher.get_provider("ollama"), self.mock_local)
        self.assertEqual(self.dispatcher.get_provider("local"), self.mock_local)

        with self.assertRaises(ProviderUnavailableError):
            self.dispatcher.get_provider("unknown_provider")

    def test_dispatch_calls_correct_provider_and_model(self):
        with patch("models.dispatcher.settings") as mock_settings:
            mock_settings.SMALL_PROVIDER = "groq"
            mock_settings.SMALL_MODEL = "openai/gpt-oss-20b"

            mock_response = ProviderResponse(
                content="Result from Groq",
                model_name="openai/gpt-oss-20b",
                provider_name="groq",
                latency_ms=45.2,
                usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
            )
            self.mock_groq.generate.return_value = mock_response

            resp = self.dispatcher.dispatch("small", "What is Python?")
            self.assertEqual(resp.content, "Result from Groq")
            self.mock_groq.generate.assert_called_once_with(
                "What is Python?",
                model="openai/gpt-oss-20b"
            )

    def test_dispatch_ollama_unavailable_raises_clear_error(self):
        with patch("models.dispatcher.settings") as mock_settings:
            mock_settings.SMALL_PROVIDER = "ollama"
            mock_settings.SMALL_MODEL = "qwen2.5:0.5b"

            self.mock_local.generate.side_effect = ConnectionError("Ollama unreachable")

            with self.assertRaises(ProviderUnavailableError) as ctx:
                self.dispatcher.dispatch("small", "Hello")
            self.assertIn("Ollama unreachable", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()

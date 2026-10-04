import unittest
from unittest.mock import MagicMock, patch
from models.groq_provider import GroqProvider
from models.provider import ProviderResponse, TokenUsage

class TestGroqProvider(unittest.TestCase):
    def test_provider_name_and_capabilities(self):
        provider = GroqProvider(model_name="test-model")
        self.assertEqual(provider.provider_name, "groq")
        caps = provider.get_capabilities()
        self.assertEqual(caps["provider"], "groq")
        self.assertEqual(caps["model"], "test-model")
        self.assertFalse(caps["is_local"])

    @patch("models.groq_provider.settings")
    @patch.dict("os.environ", {}, clear=True)
    def test_missing_api_key_raises_error(self, mock_settings):
        mock_settings.GROQ_API_KEY = ""
        provider = GroqProvider()
        with self.assertRaises(ValueError) as ctx:
            _ = provider.client
        self.assertIn("Groq API key not found", str(ctx.exception))

    @patch("models.groq_provider.Groq")
    @patch("models.groq_provider.settings")
    def test_generate_success_with_tokens(self, mock_settings, mock_groq_cls):
        mock_settings.GROQ_API_KEY = "dummy_key"
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client

        # Mock chat completion response
        mock_choice = MagicMock()
        mock_choice.message.content = "Groq generated response"
        mock_choice.finish_reason = "stop"

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 15
        mock_usage.completion_tokens = 25
        mock_usage.total_tokens = 40

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = mock_usage
        mock_completion.model = "openai/gpt-oss-20b"

        mock_client.chat.completions.create.return_value = mock_completion

        provider = GroqProvider(model_name="openai/gpt-oss-20b")
        resp = provider.generate("Explain algorithms")

        self.assertIsInstance(resp, ProviderResponse)
        self.assertEqual(resp.content, "Groq generated response")
        self.assertEqual(resp.model_name, "openai/gpt-oss-20b")
        self.assertEqual(resp.provider_name, "groq")
        self.assertGreaterEqual(resp.latency_ms, 0)
        self.assertIsNotNone(resp.usage)
        self.assertEqual(resp.usage.prompt_tokens, 15)
        self.assertEqual(resp.usage.completion_tokens, 25)
        self.assertEqual(resp.usage.total_tokens, 40)
        self.assertFalse(resp.usage.is_estimated)
        self.assertEqual(resp.raw_metadata["finish_reason"], "stop")

if __name__ == "__main__":
    unittest.main()

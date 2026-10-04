import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from models.provider import ProviderResponse, TokenUsage
from models.dispatcher import ProviderUnavailableError
from cache.semantic_cache import semantic_cache

class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        semantic_cache.clear()

    def test_root_endpoint(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("EcoMind", res.json()["message"])

    def test_tools_endpoint(self):
        res = self.client.get("/tools")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)
        tool_names = [t["name"] for t in data]
        self.assertIn("calculator", tool_names)
        self.assertIn("unit_converter", tool_names)
        self.assertIn("datetime_calculator", tool_names)
        self.assertIn("statistics_tool", tool_names)
        self.assertIn("text_analyzer", tool_names)
        self.assertEqual(len(tool_names), 5)

    def test_models_endpoint(self):
        res = self.client.get("/models")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)
        self.assertTrue(any(m["model_id"] == "gemini-2.5-flash" for m in data))
        self.assertTrue(any(m["model_id"] == "openai/gpt-oss-20b" for m in data))

    # --- Deterministic Tool Routing (0 Model Calls, 0 Tokens) ---

    def test_chat_calculator_routing(self):
        with patch("api.routes_chat.model_dispatcher.dispatch") as mock_dispatch:
            res = self.client.post("/chat", json={"query": "what is 25 * 4?"})
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["answer"], "100")
            self.assertEqual(data["route"], "Calculator / Deterministic Tool")
            self.assertEqual(data["model"], "None")
            self.assertEqual(data["provider"], "deterministic")
            self.assertTrue(data["large_model_avoided"])
            self.assertEqual(data["token_usage"]["total_tokens"], 0)
            self.assertEqual(data["metadata"]["tool_used"], "calculator")
            mock_dispatch.assert_not_called()

    def test_chat_unit_converter_routing(self):
        with patch("api.routes_chat.model_dispatcher.dispatch") as mock_dispatch:
            res = self.client.post("/chat", json={"query": "convert 100 km to miles"})
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertAlmostEqual(float(data["answer"]), 62.1371, places=3)
            self.assertEqual(data["route"], "Unit_converter / Deterministic Tool")
            self.assertEqual(data["model"], "None")
            self.assertEqual(data["provider"], "deterministic")
            self.assertTrue(data["large_model_avoided"])
            self.assertEqual(data["token_usage"]["total_tokens"], 0)
            mock_dispatch.assert_not_called()

    # --- Natural Language Calculator Queries (Zero Model Calls) ---

    def test_natural_language_calculator_queries(self):
        test_cases = [
            ("25 * 100", "2500"),
            ("25 times 100", "2500"),
            ("calculate 25 times 100", "2500"),
            ("calculate 25 times of 100", "2500"),
            ("what is 25 multiplied by 100", "2500"),
            ("multiply 25 by 100", "2500"),
            ("25 divided by 5", "5"),
        ]

        for query, expected_answer in test_cases:
            with patch("api.routes_chat.model_dispatcher.dispatch") as mock_dispatch:
                res = self.client.post("/chat", json={"query": query, "preferred_route": "auto"})
                self.assertEqual(res.status_code, 200, f"Failed for query: {query}")
                data = res.json()
                self.assertEqual(data["answer"], expected_answer, f"Wrong answer for query: {query}")
                self.assertEqual(data["route"], "Calculator / Deterministic Tool")
                self.assertEqual(data["model"], "None")
                self.assertEqual(data["provider"], "deterministic")
                self.assertEqual(data["token_usage"]["total_tokens"], 0)
                self.assertTrue(data["large_model_avoided"])
                self.assertEqual(data["metadata"]["tool_used"], "calculator")
                mock_dispatch.assert_not_called()

    def test_chat_forced_deterministic_tool_invalid(self):
        res = self.client.post(
            "/chat",
            json={"query": "Explain quantum computing", "preferred_route": "deterministic_tool"}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("No available deterministic tool", res.json()["detail"])

    # --- Automatic Model Routing (Auto -> QueryAnalyzer -> RoutingPolicy -> Dispatcher) ---

    @patch("api.routes_chat.model_dispatcher.dispatch")
    def test_chat_auto_routing_small_tier(self, mock_dispatch):
        mock_dispatch.return_value = ProviderResponse(
            content="Python is a high-level programming language.",
            model_name="openai/gpt-oss-20b",
            provider_name="groq",
            latency_ms=25.0,
            usage=TokenUsage(prompt_tokens=8, completion_tokens=15, total_tokens=23)
        )

        res = self.client.post("/chat", json={"query": "What is Python?", "preferred_route": "auto"})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Verifies dispatcher was invoked with 'small'
        mock_dispatch.assert_called_once_with(tier="small", prompt="What is Python?")
        self.assertIn("Small Model", data["route"])
        self.assertEqual(data["model"], "openai/gpt-oss-20b")
        self.assertEqual(data["provider"], "groq")
        self.assertTrue(data["large_model_avoided"])
        self.assertEqual(data["token_usage"]["total_tokens"], 23)
        self.assertEqual(data["metadata"]["tier"], "small")
        self.assertEqual(data["metadata"]["complexity"], "low")

    @patch("api.routes_chat.model_dispatcher.dispatch")
    def test_chat_auto_routing_medium_tier_explain(self, mock_dispatch):
        mock_dispatch.return_value = ProviderResponse(
            content="Multiplication is the process of repeated addition.",
            model_name="qwen/qwen3.8-27b",
            provider_name="groq",
            latency_ms=35.0,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        )

        query = "Explain multiplication."
        res = self.client.post("/chat", json={"query": query, "preferred_route": "auto"})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # "Explain multiplication." matches medium complexity keyword 'explain' -> medium tier
        mock_dispatch.assert_called_once_with(tier="medium", prompt=query)
        self.assertIn("Medium Model", data["route"])
        self.assertEqual(data["model"], "qwen/qwen3.8-27b")
        self.assertTrue(data["large_model_avoided"])
        self.assertEqual(data["metadata"]["tier"], "medium")

    @patch("api.routes_chat.model_dispatcher.dispatch")
    def test_chat_auto_routing_large_tier(self, mock_dispatch):
        mock_dispatch.return_value = ProviderResponse(
            content="BFS explores level-by-level using a queue, while DFS explores branch depth using a stack.",
            model_name="openai/gpt-oss-120b",
            provider_name="groq",
            latency_ms=90.0,
            usage=TokenUsage(prompt_tokens=20, completion_tokens=50, total_tokens=70)
        )

        query = "Compare BFS and DFS and explain why they differ."
        res = self.client.post("/chat", json={"query": query, "preferred_route": "auto"})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        mock_dispatch.assert_called_once_with(tier="large", prompt=query)
        self.assertIn("Large Model", data["route"])
        self.assertEqual(data["model"], "openai/gpt-oss-120b")
        self.assertFalse(data["large_model_avoided"])  # Large model WAS used
        self.assertEqual(data["metadata"]["tier"], "large")
        self.assertEqual(data["metadata"]["complexity"], "high")
        self.assertTrue(data["metadata"]["requires_reasoning"])

    # --- Explicit Route Overrides ---

    @patch("api.routes_chat.model_dispatcher.dispatch")
    def test_chat_explicit_tier_overrides(self, mock_dispatch):
        mock_dispatch.return_value = ProviderResponse(
            content="Explicit response",
            model_name="test-model",
            provider_name="test-provider",
            latency_ms=10.0,
            usage=TokenUsage(prompt_tokens=5, completion_tokens=5, total_tokens=10)
        )

        for route_pref, expected_tier in [
            ("small_model", "small"),
            ("medium_model", "medium"),
            ("large_model", "large"),
        ]:
            res = self.client.post("/chat", json={"query": "Test query", "preferred_route": route_pref})
            self.assertEqual(res.status_code, 200)
            mock_dispatch.assert_called_with(tier=expected_tier, prompt="Test query")

    # --- Failure Handling ---

    @patch("api.routes_chat.model_dispatcher.dispatch")
    def test_chat_provider_unavailable_returns_503(self, mock_dispatch):
        mock_dispatch.side_effect = ProviderUnavailableError("Ollama daemon is offline at http://localhost:11434")

        res = self.client.post("/chat", json={"query": "What is Python?", "preferred_route": "auto"})
        self.assertEqual(res.status_code, 503)
        self.assertIn("Ollama daemon is offline", res.json()["detail"])

if __name__ == "__main__":
    unittest.main()

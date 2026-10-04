import unittest
from models.model_profiles import (
    ModelTier,
    MODEL_CATALOG,
    get_model_profile,
    get_models_by_tier,
    list_all_profiles
)
from models.local_provider import LocalProvider
from models.provider import ProviderResponse, TokenUsage

class TestModelsAndProfiles(unittest.TestCase):
    def test_model_catalog_structure(self):
        self.assertIn("gemini-2.5-flash", MODEL_CATALOG)
        self.assertIn("gemini-2.5-pro", MODEL_CATALOG)
        self.assertIn("local-small", MODEL_CATALOG)

        profile = get_model_profile("gemini-2.5-flash")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.tier, ModelTier.MEDIUM)
        self.assertEqual(profile.provider, "google")
        self.assertFalse(profile.is_local)

    def test_get_models_by_tier(self):
        small_models = get_models_by_tier(ModelTier.SMALL)
        self.assertTrue(any(m.model_id == "local-small" for m in small_models))

        large_models = get_models_by_tier(ModelTier.LARGE)
        self.assertTrue(any(m.model_id == "gemini-2.5-pro" for m in large_models))

    def test_list_all_profiles(self):
        profiles = list_all_profiles()
        self.assertIsInstance(profiles, list)
        self.assertGreaterEqual(len(profiles), 3)
        self.assertIn("tier", profiles[0])
        self.assertIn("model_id", profiles[0])

    def test_local_provider_fallback(self):
        provider = LocalProvider()
        resp = provider.generate("Test prompt query")
        self.assertIsInstance(resp, ProviderResponse)
        self.assertEqual(resp.provider_name, "local")
        self.assertGreaterEqual(resp.latency_ms, 0)
        self.assertIsNotNone(resp.usage)
        self.assertIsInstance(resp.usage.total_tokens, int)
        self.assertIn("local", resp.content.lower())

if __name__ == "__main__":
    unittest.main()

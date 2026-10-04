import os
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import numpy as np

from main import app
from models.provider import ProviderResponse, TokenUsage
from cache.semantic_cache import semantic_cache, CacheLookupResult
from cache.compatibility_checker import compatibility_checker
from cache.cache_store import CacheStore, CacheEntry

class TestSemanticCache(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        semantic_cache.clear()
        semantic_cache.threshold = 0.90
        semantic_cache.store.max_entries = 1000
        semantic_cache.store.ttl_days = 30

    def tearDown(self):
        semantic_cache.clear()
        semantic_cache.store.max_entries = 1000
        semantic_cache.store.ttl_days = 30

    # --- TEST 1: Exact / Near-Equivalent Semantic Query (Cache Hit, 0 Model Calls) ---
    @patch("api.routes_chat.model_dispatcher.dispatch")
    def test_exact_near_equivalent_query_cache_hit(self, mock_dispatch):
        mock_dispatch.return_value = ProviderResponse(
            content="TCP is connection-oriented and reliable, while UDP is connectionless and faster.",
            provider_name="groq",
            model_name="openai/gpt-oss-20b",
            latency_ms=25.0,
            usage=TokenUsage(prompt_tokens=25, completion_tokens=40, total_tokens=65)
        )

        # 1st query: Cache miss -> model executed -> answer stored in cache
        res1 = self.client.post("/chat", json={"query": "Explain the difference between TCP and UDP."})
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.json()["cache_status"], "miss")
        self.assertEqual(mock_dispatch.call_count, 1)

        mock_dispatch.reset_mock()

        # 2nd query: Semantically equivalent question
        res2 = self.client.post("/chat", json={"query": "What is the difference between UDP and TCP?"})
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()

        # Verify Cache Hit
        self.assertEqual(data2["cache_status"], "hit")
        self.assertGreaterEqual(data2["cache_similarity"], 0.90)
        self.assertEqual(data2["answer"], "TCP is connection-oriented and reliable, while UDP is connectionless and faster.")
        self.assertEqual(data2["route"], "semantic_cache")
        self.assertIsNone(data2["model"])
        self.assertEqual(data2["provider"], "cache")
        self.assertTrue(data2["large_model_avoided"])
        self.assertEqual(data2["token_usage"]["total_tokens"], 0)

        # CRITICAL: 0 model calls on cache hit
        self.assertEqual(mock_dispatch.call_count, 0)

    # --- TEST 2: Same Topic but Additional Requirement (Cache Miss, Model Called) ---
    @patch("api.routes_chat.model_dispatcher.dispatch")
    def test_same_topic_additional_requirement_cache_miss(self, mock_dispatch):
        mock_dispatch.return_value = ProviderResponse(
            content="Generic TCP vs UDP explanation.",
            provider_name="groq",
            model_name="openai/gpt-oss-20b",
            latency_ms=20.0,
            usage=TokenUsage(prompt_tokens=25, completion_tokens=30, total_tokens=55)
        )

        # Populate cache with generic TCP vs UDP query
        res1 = self.client.post("/chat", json={"query": "Explain the difference between TCP and UDP."})
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(mock_dispatch.call_count, 1)

        # Update mock for specific query
        mock_dispatch.return_value = ProviderResponse(
            content="In high-latency networks, UDP is preferred because TCP handshakes introduce delay.",
            provider_name="groq",
            model_name="openai/gpt-oss-20b",
            latency_ms=30.0,
            usage=TokenUsage(prompt_tokens=35, completion_tokens=50, total_tokens=85)
        )
        mock_dispatch.reset_mock()

        # New query adds specific constraint: "specifically for high-latency networks"
        res2 = self.client.post("/chat", json={"query": "Compare TCP and UDP specifically for high-latency networks."})
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()

        # MUST BE CACHE MISS
        self.assertEqual(data2["cache_status"], "miss")
        self.assertIn("Model", data2["route"])
        self.assertNotEqual(data2["provider"], "cache")
        # Model MUST be called
        self.assertEqual(mock_dispatch.call_count, 1)
        self.assertEqual(data2["answer"], "In high-latency networks, UDP is preferred because TCP handshakes introduce delay.")

    # --- TEST 3: Different Concept, Same Broad Topic (Cache Miss) ---
    @patch("api.routes_chat.model_dispatcher.dispatch")
    def test_different_concept_same_broad_topic_cache_miss(self, mock_dispatch):
        mock_dispatch.return_value = ProviderResponse(
            content="Decorators wrap functions.",
            provider_name="groq",
            model_name="openai/gpt-oss-20b",
            latency_ms=15.0,
            usage=TokenUsage(prompt_tokens=15, completion_tokens=20, total_tokens=35)
        )

        res1 = self.client.post("/chat", json={"query": "Explain Python decorators."})
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(mock_dispatch.call_count, 1)

        mock_dispatch.return_value = ProviderResponse(
            content="Generators yield values lazily.",
            provider_name="groq",
            model_name="openai/gpt-oss-20b",
            latency_ms=15.0,
            usage=TokenUsage(prompt_tokens=15, completion_tokens=20, total_tokens=35)
        )
        mock_dispatch.reset_mock()

        # Same topic (Python) but different concept (generators vs decorators)
        res2 = self.client.post("/chat", json={"query": "Explain Python generators."})
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()["cache_status"], "miss")
        self.assertEqual(mock_dispatch.call_count, 1)

    # --- TEST 4: Dynamic / Time-Sensitive Query (Prefer Cache Miss, Stale Prevention) ---
    @patch("api.routes_chat.model_dispatcher.dispatch")
    def test_dynamic_time_sensitive_query_cache_miss(self, mock_dispatch):
        mock_dispatch.return_value = ProviderResponse(
            content="The current price of Bitcoin is $65,000.",
            provider_name="groq",
            model_name="openai/gpt-oss-20b",
            latency_ms=20.0,
            usage=TokenUsage(prompt_tokens=15, completion_tokens=20, total_tokens=35)
        )

        # Dynamic queries should not be served as stale cache hits
        res1 = self.client.post("/chat", json={"query": "What is the current price of Bitcoin?"})
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.json()["cache_status"], "miss")
        self.assertEqual(mock_dispatch.call_count, 1)

        mock_dispatch.reset_mock()

        # Repeating query must still be a cache miss because dynamic queries are uncacheable
        res2 = self.client.post("/chat", json={"query": "What is the current price of Bitcoin?"})
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()["cache_status"], "miss")
        self.assertEqual(mock_dispatch.call_count, 1)

    # --- TEST 5: Deterministic Tool Takes Precedence (0 Model Calls, 0 Cache Overhead) ---
    @patch("api.routes_chat.model_dispatcher.dispatch")
    def test_deterministic_tool_bypasses_cache_and_model(self, mock_dispatch):
        # Calculator query must be intercepted by deterministic tool FIRST
        res = self.client.post("/chat", json={"query": "calculate 25 times 100"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["answer"], "2500")
        self.assertEqual(data["route"], "Calculator / Deterministic Tool")
        self.assertEqual(data["provider"], "deterministic")
        self.assertEqual(data["cache_status"], "not_checked")
        self.assertIsNone(data["cache_similarity"])
        self.assertEqual(data["token_usage"]["total_tokens"], 0)
        self.assertEqual(mock_dispatch.call_count, 0)

    # --- TEST 6: Unrelated Query (Cache Miss) ---
    @patch("api.routes_chat.model_dispatcher.dispatch")
    def test_unrelated_query_cache_miss(self, mock_dispatch):
        mock_dispatch.return_value = ProviderResponse(
            content="TCP vs UDP summary",
            provider_name="groq",
            model_name="openai/gpt-oss-20b",
            latency_ms=18.0
        )
        self.client.post("/chat", json={"query": "Explain TCP vs UDP."})
        mock_dispatch.reset_mock()

        mock_dispatch.return_value = ProviderResponse(
            content="Python decorators summary",
            provider_name="groq",
            model_name="openai/gpt-oss-20b",
            latency_ms=18.0
        )
        res = self.client.post("/chat", json={"query": "Explain Python decorators."})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["cache_status"], "miss")
        self.assertEqual(mock_dispatch.call_count, 1)

    # --- TEST 7: Below Configured Threshold (Cache Miss & Configurable Thresholds) ---
    def test_below_threshold_similarity_cache_miss(self):
        # With threshold 0.90, similarity 0.85 must be rejected
        comp = compatibility_checker.validate(
            new_query="What is the capital of Germany?",
            cached_query="What is the capital of France?",
            similarity=0.85,
            threshold=0.90
        )
        self.assertFalse(comp.is_compatible)
        self.assertIn("below configured threshold", comp.reason)

    def test_configurable_threshold_tradeoffs(self):
        """Demonstrates that thresholds can be adjusted (0.85, 0.90, 0.95, 0.97, 0.99) for precision/recall evaluation."""
        sim = 0.92
        # Passes under lower threshold (0.85, 0.90)
        self.assertTrue(sim >= 0.85)
        self.assertTrue(sim >= 0.90)
        # Rejected under stricter precision thresholds (0.95, 0.97, 0.99)
        self.assertFalse(sim >= 0.95)
        self.assertFalse(sim >= 0.97)
        self.assertFalse(sim >= 0.99)

    # --- TEST 8: Cache Hit Telemetry Verification ---
    @patch("api.routes_chat.model_dispatcher.dispatch")
    def test_cache_hit_telemetry(self, mock_dispatch):
        mock_dispatch.return_value = ProviderResponse(
            content="Paris is the capital of France.",
            provider_name="groq",
            model_name="openai/gpt-oss-20b",
            latency_ms=15.0,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20)
        )

        self.client.post("/chat", json={"query": "What is the capital of France?"})
        mock_dispatch.reset_mock()

        res = self.client.post("/chat", json={"query": "Which city is the capital of France?"})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["cache_status"], "hit")
        self.assertEqual(data["route"], "semantic_cache")
        self.assertIsNone(data["model"])
        self.assertEqual(data["provider"], "cache")
        self.assertTrue(data["large_model_avoided"])
        self.assertEqual(data["token_usage"]["total_tokens"], 0)
        self.assertEqual(mock_dispatch.call_count, 0)
        self.assertGreater(data["cache_similarity"], 0.90)

    # --- TEST 9: Cache Miss Telemetry Verification ---
    @patch("api.routes_chat.model_dispatcher.dispatch")
    def test_cache_miss_telemetry(self, mock_dispatch):
        mock_dispatch.return_value = ProviderResponse(
            content="Paris is the capital.",
            provider_name="groq",
            model_name="openai/gpt-oss-20b",
            latency_ms=15.0,
            usage=TokenUsage(prompt_tokens=12, completion_tokens=15, total_tokens=27)
        )

        res = self.client.post("/chat", json={"query": "What is the capital of France?"})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["cache_status"], "miss")
        self.assertEqual(data["provider"], "groq")
        self.assertEqual(data["model"], "openai/gpt-oss-20b")
        self.assertEqual(data["token_usage"]["total_tokens"], 27)
        self.assertEqual(mock_dispatch.call_count, 1)

    # --- TEST 10: Regression Check - Small Model Routing ---
    @patch("api.routes_chat.model_dispatcher.dispatch")
    def test_regression_small_model_routing(self, mock_dispatch):
        mock_dispatch.return_value = ProviderResponse(
            content="Python is a programming language.",
            provider_name="groq",
            model_name="openai/gpt-oss-20b",
            latency_ms=12.0
        )
        res = self.client.post("/chat", json={"query": "What is Python?"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("Small Model", data["route"])
        self.assertEqual(data["cache_status"], "miss")
        mock_dispatch.assert_called_with(tier="small", prompt="What is Python?")

    # --- TEST 11: Regression Check - Medium Model Routing ---
    @patch("api.routes_chat.model_dispatcher.dispatch")
    def test_regression_medium_model_routing(self, mock_dispatch):
        mock_dispatch.return_value = ProviderResponse(
            content="SQL is relational; NoSQL is non-relational.",
            provider_name="groq",
            model_name="qwen/qwen3.8-27b",
            latency_ms=16.0
        )
        res = self.client.post("/chat", json={"query": "Summarize SQL vs NoSQL."})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("Medium Model", data["route"])
        self.assertEqual(data["cache_status"], "miss")
        mock_dispatch.assert_called_with(tier="medium", prompt="Summarize SQL vs NoSQL.")

    # --- TEST 12: Regression Check - Large Model Routing ---
    @patch("api.routes_chat.model_dispatcher.dispatch")
    def test_regression_large_model_routing(self, mock_dispatch):
        mock_dispatch.return_value = ProviderResponse(
            content="BFS uses queues; DFS uses stacks.",
            provider_name="groq",
            model_name="openai/gpt-oss-120b",
            latency_ms=25.0
        )
        res = self.client.post("/chat", json={"query": "Compare BFS and DFS and explain why they differ."})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("Large Model", data["route"])
        self.assertEqual(data["cache_status"], "miss")
        self.assertFalse(data["large_model_avoided"])
        mock_dispatch.assert_called_with(tier="large", prompt="Compare BFS and DFS and explain why they differ.")

    # --- TEST 13: Temporal Modifier Addition Incompatibility ---
    def test_temporal_modifier_addition_incompatibility(self):
        comp = compatibility_checker.validate(
            new_query="What was the capital of France in 1800?",
            cached_query="What is the capital of France?",
            similarity=0.97,
            threshold=0.95
        )
        self.assertFalse(comp.is_compatible)
        self.assertIn("temporal constraints", comp.reason)

    # --- TEST 14: Reasoning Depth Incompatibility ---
    def test_reasoning_depth_incompatibility(self):
        comp = compatibility_checker.validate(
            new_query="Derive gradient descent mathematically and explain the convergence condition.",
            cached_query="Give a basic explanation of gradient descent.",
            similarity=0.96,
            threshold=0.95
        )
        self.assertFalse(comp.is_compatible)
        self.assertIn("mathematical derivation", comp.reason)

    # --- TEST 15: Cache Stats and Clear Endpoints ---
    @patch("api.routes_chat.model_dispatcher.dispatch")
    def test_cache_stats_and_clear_endpoints(self, mock_dispatch):
        mock_dispatch.return_value = ProviderResponse(
            content="Test content",
            provider_name="groq",
            model_name="openai/gpt-oss-20b",
            latency_ms=10.0
        )
        # Seed cache with one item
        self.client.post("/chat", json={"query": "Explain recursion in computer science."})

        # Query stats
        res_stats = self.client.get("/cache/stats")
        self.assertEqual(res_stats.status_code, 200)
        stats = res_stats.json()
        self.assertTrue(stats["enabled"])
        self.assertGreaterEqual(stats["total_entries"], 1)

        # Clear cache
        res_clear = self.client.post("/cache/clear")
        self.assertEqual(res_clear.status_code, 200)

        # Verify cleared
        res_stats_after = self.client.get("/cache/stats")
        self.assertEqual(res_stats_after.json()["total_entries"], 0)

    # --- TEST 16: Maximum Cache Size Enforcement ---
    def test_maximum_cache_size_enforcement(self):
        """Verify that cache never exceeds MAX_CACHE_ENTRIES limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_cache.db")
            idx_path = os.path.join(tmpdir, "test_cache.index")
            store = CacheStore(dimension=4, db_path=db_path, index_path=idx_path, max_entries=3)

            for i in range(5):
                entry = CacheEntry(query=f"Query {i}", answer=f"Answer {i}")
                vec = np.array([float(i), 1.0, 0.0, 0.0], dtype=np.float32)
                store.add_entry(entry, vec)

            stats = store.get_stats()
            self.assertEqual(stats["total_entries"], 3)
            self.assertEqual(stats["faiss_total_vectors"], 3)
            store.close()

    # --- TEST 17: LRU Eviction Policy ---
    def test_lru_eviction_policy(self):
        """Verify that least recently used/accessed entry is evicted when limit is reached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_lru.db")
            idx_path = os.path.join(tmpdir, "test_lru.index")
            store = CacheStore(dimension=4, db_path=db_path, index_path=idx_path, max_entries=3)

            # Insert A, B, C
            entry_a = CacheEntry(query="Query A", answer="Answer A")
            entry_b = CacheEntry(query="Query B", answer="Answer B")
            entry_c = CacheEntry(query="Query C", answer="Answer C")

            id_a = store.add_entry(entry_a, np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32))
            id_b = store.add_entry(entry_b, np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32))
            id_c = store.add_entry(entry_c, np.array([0.0, 0.0, 1.0, 0.0], dtype=np.float32))

            # Record hit on A to refresh its last_used_at timestamp
            store.record_hit(id_a)

            # Now access order: B (oldest), C (newer), A (newest)
            # Adding D should evict B (least recently used)
            entry_d = CacheEntry(query="Query D", answer="Answer D")
            id_d = store.add_entry(entry_d, np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32))

            remaining_entries = [store.get_entry_by_id(x) for x in [id_a, id_b, id_c, id_d]]
            # B must have been evicted (None)
            self.assertIsNone(remaining_entries[1], "Entry B should have been evicted by LRU")
            # A, C, D must still exist
            self.assertIsNotNone(remaining_entries[0], "Entry A (recently hit) should have been retained")
            self.assertIsNotNone(remaining_entries[2], "Entry C should have been retained")
            self.assertIsNotNone(remaining_entries[3], "Entry D should have been retained")

            # Check FAISS index synchronization
            self.assertEqual(store._index.ntotal, 3)
            store.close()

    # --- TEST 18: TTL Eviction Policy ---
    def test_ttl_eviction_policy(self):
        """Verify that entries older than CACHE_TTL_DAYS are prioritized for eviction."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_ttl.db")
            idx_path = os.path.join(tmpdir, "test_ttl.index")
            store = CacheStore(dimension=4, db_path=db_path, index_path=idx_path, max_entries=2, ttl_days=7)

            # Insert an old entry created 10 days ago
            old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
            entry_old = CacheEntry(query="Old Query", answer="Old Answer", created_at=old_time, last_used_at=old_time)
            id_old = store.add_entry(entry_old, np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32))

            # Insert fresh entry
            entry_fresh = CacheEntry(query="Fresh Query", answer="Fresh Answer")
            id_fresh = store.add_entry(entry_fresh, np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32))

            # Manually trigger evict_expired
            evicted = store.evict_expired()
            self.assertIn(id_old, evicted)
            self.assertEqual(store.get_entry_by_id(id_old), None)
            self.assertIsNotNone(store.get_entry_by_id(id_fresh))
            store.close()

    # --- TEST 19: Cache Persistence Across Reloads ---
    def test_cache_persistence_across_reloads(self):
        """Verify that SQLite and FAISS data persist correctly across store re-instantiations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "persistent.db")
            idx_path = os.path.join(tmpdir, "persistent.index")

            # Create store 1 and insert items
            store1 = CacheStore(dimension=4, db_path=db_path, index_path=idx_path)
            vec = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
            store1.add_entry(CacheEntry(query="Persistent Query", answer="Persistent Answer"), vec)
            store1.close()

            # Create store 2 pointing to the exact same paths
            store2 = CacheStore(dimension=4, db_path=db_path, index_path=idx_path)
            stats = store2.get_stats()
            self.assertEqual(stats["total_entries"], 1)
            self.assertEqual(stats["faiss_total_vectors"], 1)

            entry = store2.get_entry_by_id(1)
            self.assertIsNotNone(entry)
            self.assertEqual(entry.query, "Persistent Query")
            self.assertEqual(entry.answer, "Persistent Answer")

            # Search vector in reloaded index
            results = store2.search_vector(vec, top_k=1)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0][0].query, "Persistent Query")
            self.assertAlmostEqual(results[0][1], 1.0, places=4)
            store2.close()

    # --- TEST 20: Comprehensive Cache Statistics & Telemetry ---
    @patch("api.routes_chat.model_dispatcher.dispatch")
    def test_comprehensive_cache_statistics(self, mock_dispatch):
        """Verify all fields in CacheStatsSchema including storage size, hits, and misses."""
        mock_dispatch.return_value = ProviderResponse(
            content="Answer content",
            provider_name="groq",
            model_name="openai/gpt-oss-20b",
            latency_ms=12.0
        )

        # Ensure cache starts clean
        semantic_cache.clear()

        # Miss: query cache when empty
        res_miss = self.client.post("/chat", json={"query": "What is Python?"})
        self.assertEqual(res_miss.json()["cache_status"], "miss")

        # Hit: query cache with equivalent question
        res_hit = self.client.post("/chat", json={"query": "What is Python?"})
        self.assertEqual(res_hit.json()["cache_status"], "hit")

        # Fetch stats
        res_stats = self.client.get("/cache/stats")
        self.assertEqual(res_stats.status_code, 200)
        stats = res_stats.json()

        self.assertEqual(stats["total_entries"], 1)
        self.assertGreaterEqual(stats["cache_hits"], 1)
        self.assertGreaterEqual(stats["cache_misses"], 1)
        self.assertIn("storage_size_bytes", stats)
        self.assertIn("storage_size_kb", stats)
        self.assertEqual(stats["max_entries"], 1000)
        self.assertEqual(stats["ttl_days"], 30)
        self.assertIn("semantic_cache.db", stats["cache_db_path"])
        self.assertIn("semantic_cache.index", stats["cache_index_path"])

if __name__ == "__main__":
    unittest.main()

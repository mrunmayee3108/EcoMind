import time
import json
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from config.settings import settings
from router.query_analyzer import QueryAnalysis
from .embedding_service import embedding_service, EmbeddingService
from .cache_store import cache_store, CacheStore, CacheEntry
from .compatibility_checker import compatibility_checker, CompatibilityChecker

logger = logging.getLogger(__name__)

@dataclass
class CacheLookupResult:
    status: str                         # "hit" or "miss"
    entry: Optional[CacheEntry] = None
    similarity: Optional[float] = None
    reason: str = ""
    latency_ms: float = 0.0

class SemanticCache:
    """
    Accuracy-First Semantic Cache Controller.
    Executes a conservative two-stage validation pipeline:
      Stage 1: L2-normalized vector retrieval (FAISS IndexFlatIP)
      Stage 2: Deterministic semantic compatibility validation (entities, constraints, temporal, task)
    """

    def __init__(
        self,
        store: Optional[CacheStore] = None,
        embedder: Optional[EmbeddingService] = None,
        checker: Optional[CompatibilityChecker] = None,
        threshold: Optional[float] = None,
        enabled: Optional[bool] = None,
        max_entries: Optional[int] = None,
        ttl_days: Optional[int] = None
    ):
        self.store = store or cache_store
        self.embedder = embedder or embedding_service
        self.checker = checker or compatibility_checker
        self.threshold = threshold if threshold is not None else settings.CACHE_SIMILARITY_THRESHOLD
        self.enabled = enabled if enabled is not None else settings.CACHE_ENABLED
        if max_entries is not None:
            self.store.max_entries = max_entries
        if ttl_days is not None:
            self.store.ttl_days = ttl_days
        self._session_hits: int = 0
        self._session_misses: int = 0

    def lookup(
        self,
        query: str,
        threshold: Optional[float] = None,
        analysis: Optional[QueryAnalysis] = None
    ) -> CacheLookupResult:
        """
        Looks up a query in the cache.
        Returns a CacheLookupResult with status="hit" only if Stage 1 and Stage 2 both pass.
        """
        start_time = time.perf_counter()

        if not self.enabled:
            return CacheLookupResult(
                status="miss",
                reason="Semantic cache is disabled.",
                latency_ms=(time.perf_counter() - start_time) * 1000
            )

        # Stage 1: Vector Search
        try:
            query_vector = self.embedder.embed_query(query)
            top_candidates = self.store.search_vector(query_vector, top_k=1)
        except Exception as e:
            logger.error(f"Semantic cache retrieval error: {e}")
            self._session_misses += 1
            return CacheLookupResult(
                status="miss",
                reason=f"Vector retrieval error: {e}",
                latency_ms=(time.perf_counter() - start_time) * 1000
            )

        if not top_candidates:
            self._session_misses += 1
            return CacheLookupResult(
                status="miss",
                reason="Cache is empty or no candidates found.",
                latency_ms=(time.perf_counter() - start_time) * 1000
            )

        candidate_entry, similarity = top_candidates[0]
        effective_threshold = threshold if threshold is not None else self.threshold

        # Stage 2: Compatibility Validation
        comp_result = self.checker.validate(
            new_query=query,
            cached_query=candidate_entry.query,
            similarity=similarity,
            threshold=effective_threshold,
            new_analysis=analysis,
            cached_task_type=candidate_entry.task_type
        )

        lookup_latency = (time.perf_counter() - start_time) * 1000

        if comp_result.is_compatible:
            # CACHE HIT: record hit in database and return cached entry
            self._session_hits += 1
            self.store.record_hit(candidate_entry.id)
            candidate_entry.hit_count += 1
            return CacheLookupResult(
                status="hit",
                entry=candidate_entry,
                similarity=similarity,
                reason=comp_result.reason,
                latency_ms=lookup_latency
            )
        else:
            # CACHE MISS
            self._session_misses += 1
            return CacheLookupResult(
                status="miss",
                entry=None,
                similarity=similarity,
                reason=comp_result.reason,
                latency_ms=lookup_latency
            )

    def store_result(
        self,
        query: str,
        answer: str,
        task_type: str = "general_qa",
        route: str = "",
        provider: str = "",
        model: str = "",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        execution_time_ms: float = 0.0,
        analysis: Optional[QueryAnalysis] = None
    ) -> Optional[CacheEntry]:
        """
        Stores an LLM-generated result in the semantic cache.
        Does not store dynamic or time-sensitive queries to prevent stale data.
        """
        if not self.enabled:
            return None

        # Do not cache dynamic or time-sensitive queries
        if self.checker.is_dynamic_or_time_sensitive(query):
            logger.info(f"Skipping cache store for dynamic/time-sensitive query: '{query}'")
            return None

        try:
            vector = self.embedder.embed_query(query)
            entities = list(self.checker.extract_core_terms(query))
            constraints = self.checker.extract_constraints(query)

            analysis_json = None
            if analysis:
                analysis_json = json.dumps({
                    "task_type": analysis.task_type,
                    "complexity": analysis.complexity,
                    "requires_reasoning": analysis.requires_reasoning
                })

            entry = CacheEntry(
                query=query,
                normalized_query=query.lower().strip(),
                answer=answer,
                task_type=task_type,
                entities=entities,
                constraints=constraints,
                route=route,
                provider=provider,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                execution_time_ms=execution_time_ms,
                is_dynamic=False,
                analysis_json=analysis_json
            )

            entry_id = self.store.add_entry(entry, vector)
            entry.id = entry_id
            return entry
        except Exception as e:
            logger.error(f"Failed to store entry in semantic cache: {e}")
            return None

    def clear(self):
        """Clears all entries in the cache and resets session counters."""
        self.store.clear()
        self._session_hits = 0
        self._session_misses = 0

    def stats(self) -> Dict[str, Any]:
        """Returns statistics and lifecycle telemetry of the semantic cache."""
        store_stats = self.store.get_stats()
        return {
            "enabled": self.enabled,
            "threshold": self.threshold,
            "embedding_model": self.embedder.model_name,
            **store_stats,
            "cache_misses": self._session_misses
        }

# Global default instance
semantic_cache = SemanticCache()

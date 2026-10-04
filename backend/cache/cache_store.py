import os
import json
import sqlite3
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple, Dict, Any
import numpy as np
import faiss

from config.settings import settings

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    id: Optional[int] = None
    query: str = ""
    normalized_query: str = ""
    answer: str = ""
    task_type: str = "general_qa"
    entities: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    route: str = ""
    provider: str = ""
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    execution_time_ms: float = 0.0
    created_at: str = ""
    last_used_at: str = ""
    hit_count: int = 0
    is_dynamic: bool = False
    analysis_json: Optional[str] = None

class CacheStore:
    """
    Precision-First Persistent Cache Store.
    Combines SQLite for structured metadata with FAISS IndexFlatIP for exact cosine vector retrieval.
    """

    def __init__(
        self,
        dimension: int = 384,
        db_path: Optional[str] = None,
        index_path: Optional[str] = None,
        max_entries: Optional[int] = None,
        ttl_days: Optional[int] = None
    ):
        self.dimension = dimension
        self.db_path = db_path or settings.CACHE_DB_PATH
        self.index_path = index_path or settings.CACHE_INDEX_PATH
        self.max_entries = max_entries if max_entries is not None else settings.MAX_CACHE_ENTRIES
        self.ttl_days = ttl_days if ttl_days is not None else settings.CACHE_TTL_DAYS

        self._conn: Optional[sqlite3.Connection] = None
        self._index: Optional[faiss.Index] = None
        self._init_storage()

    def _init_storage(self):
        # Resolve absolute paths or handle in-memory
        if self.db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

        # Initialize FAISS IndexIDMap with FlatIP
        sub_index = faiss.IndexFlatIP(self.dimension)
        self._index = faiss.IndexIDMap(sub_index)

        # Load existing index if present and not in-memory
        if self.index_path and os.path.exists(self.index_path) and self.db_path != ":memory:":
            try:
                loaded_index = faiss.read_index(self.index_path)
                self._index = loaded_index
                logger.info(f"Loaded existing FAISS index from {self.index_path} with {self._index.ntotal} vectors.")
            except Exception as e:
                logger.warning(f"Could not load FAISS index from {self.index_path}, re-initializing: {e}")

    def _create_tables(self):
        cursor = self._conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                normalized_query TEXT NOT NULL,
                answer TEXT NOT NULL,
                task_type TEXT,
                entities TEXT,
                constraints TEXT,
                route TEXT,
                provider TEXT,
                model TEXT,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                execution_time_ms REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                last_used_at TEXT NOT NULL,
                hit_count INTEGER DEFAULT 0,
                is_dynamic INTEGER DEFAULT 0,
                analysis_json TEXT
            );
        """)
        self._conn.commit()

    def add_entry(self, entry: CacheEntry, vector: np.ndarray) -> int:
        """
        Stores metadata in SQLite and indexes the normalized vector in FAISS.
        Evicts expired or least-recently-used entries if MAX_CACHE_ENTRIES limit is reached.
        Returns the generated database entry ID.
        """
        if self.max_entries and self.max_entries > 0:
            self.evict_if_needed(entries_to_add=1)

        now = datetime.now(timezone.utc).isoformat()
        entry.created_at = entry.created_at or now
        entry.last_used_at = entry.last_used_at or now

        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO cache_entries (
                query, normalized_query, answer, task_type, entities, constraints,
                route, provider, model, prompt_tokens, completion_tokens, total_tokens,
                execution_time_ms, created_at, last_used_at, hit_count, is_dynamic, analysis_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.query,
            entry.normalized_query or entry.query.lower().strip(),
            entry.answer,
            entry.task_type,
            json.dumps(entry.entities),
            json.dumps(entry.constraints),
            entry.route,
            entry.provider,
            entry.model,
            entry.prompt_tokens,
            entry.completion_tokens,
            entry.total_tokens,
            entry.execution_time_ms,
            entry.created_at,
            entry.last_used_at,
            entry.hit_count,
            1 if entry.is_dynamic else 0,
            entry.analysis_json
        ))
        entry_id = cursor.lastrowid
        self._conn.commit()
        entry.id = entry_id

        # Add to FAISS index
        vec_2d = np.ascontiguousarray(vector.reshape(1, -1), dtype=np.float32)
        id_arr = np.array([entry_id], dtype=np.int64)
        self._index.add_with_ids(vec_2d, id_arr)

        # Persist index if configured
        self._save_index_if_configured()
        return entry_id

    def search_vector(self, vector: np.ndarray, top_k: int = 5) -> List[Tuple[CacheEntry, float]]:
        """
        Searches FAISS for the nearest vectors and returns matching CacheEntries with cosine similarities.
        """
        if self._index.ntotal == 0:
            return []

        vec_2d = np.ascontiguousarray(vector.reshape(1, -1), dtype=np.float32)
        distances, ids = self._index.search(vec_2d, min(top_k, self._index.ntotal))

        results: List[Tuple[CacheEntry, float]] = []
        for dist, entry_id in zip(distances[0], ids[0]):
            if entry_id == -1:
                continue
            entry = self.get_entry_by_id(int(entry_id))
            if entry:
                # In FlatIP with unit vectors, dist is cosine similarity in [-1, 1]
                score = float(dist)
                results.append((entry, score))

        return results

    def get_entry_by_id(self, entry_id: int) -> Optional[CacheEntry]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM cache_entries WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_entry(row)

    def record_hit(self, entry_id: int) -> None:
        """Increments hit count and updates last_used_at for an entry."""
        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.cursor()
        cursor.execute("""
            UPDATE cache_entries
            SET hit_count = hit_count + 1, last_used_at = ?
            WHERE id = ?
        """, (now, entry_id))
        self._conn.commit()

    def remove_entries(self, entry_ids: List[int]) -> int:
        """Removes entries by ID from both SQLite and the FAISS vector index."""
        if not entry_ids:
            return 0
        cursor = self._conn.cursor()
        placeholders = ",".join("?" for _ in entry_ids)
        cursor.execute(f"DELETE FROM cache_entries WHERE id IN ({placeholders})", entry_ids)
        self._conn.commit()

        if self._index and self._index.ntotal > 0:
            try:
                id_arr = np.array(entry_ids, dtype=np.int64)
                self._index.remove_ids(id_arr)
                self._save_index_if_configured()
            except Exception as e:
                logger.warning(f"Error removing IDs {entry_ids} from FAISS index: {e}")

        return len(entry_ids)

    def evict_if_needed(self, entries_to_add: int = 1) -> List[int]:
        """
        Enforces MAX_CACHE_ENTRIES capacity with precision-first safe eviction:
        1. Checks and evicts entries exceeding CACHE_TTL_DAYS (if configured).
        2. If still at/over capacity, evicts the least-recently-used (LRU) entries
           (oldest last_used_at, breaking ties by lowest hit_count and oldest ID).
        Does NOT silently purge useful, frequently accessed entries.
        Returns the list of evicted entry IDs.
        """
        if self.max_entries is None or self.max_entries <= 0:
            return []

        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cache_entries")
        current_count = cursor.fetchone()[0] or 0

        target_max = max(0, self.max_entries - entries_to_add)
        if current_count <= target_max:
            return []

        evicted_ids: List[int] = []

        # 1. TTL-based eviction: prioritize expired entries
        if self.ttl_days and self.ttl_days > 0:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=self.ttl_days)).isoformat()
            cursor.execute(
                "SELECT id FROM cache_entries WHERE created_at < ? ORDER BY last_used_at ASC",
                (cutoff,)
            )
            for r in cursor.fetchall():
                evicted_ids.append(r[0])
                if current_count - len(evicted_ids) <= target_max:
                    break

        # 2. LRU-based eviction: evict least recently accessed entries
        remaining_needed = (current_count - len(evicted_ids)) - target_max
        if remaining_needed > 0:
            if evicted_ids:
                placeholders = ",".join("?" for _ in evicted_ids)
                query = f"""
                    SELECT id FROM cache_entries
                    WHERE id NOT IN ({placeholders})
                    ORDER BY last_used_at ASC, hit_count ASC, id ASC
                    LIMIT ?
                """
                params = list(evicted_ids) + [remaining_needed]
            else:
                query = """
                    SELECT id FROM cache_entries
                    ORDER BY last_used_at ASC, hit_count ASC, id ASC
                    LIMIT ?
                """
                params = [remaining_needed]

            cursor.execute(query, params)
            for r in cursor.fetchall():
                evicted_ids.append(r[0])

        if evicted_ids:
            self.remove_entries(evicted_ids)
            logger.info(
                f"Evicted {len(evicted_ids)} cache entries (IDs: {evicted_ids}) "
                f"to maintain MAX_CACHE_ENTRIES={self.max_entries}."
            )

        return evicted_ids

    def evict_expired(self) -> List[int]:
        """Evicts all entries older than CACHE_TTL_DAYS."""
        if not self.ttl_days or self.ttl_days <= 0:
            return []
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.ttl_days)).isoformat()
        cursor = self._conn.cursor()
        cursor.execute("SELECT id FROM cache_entries WHERE created_at < ?", (cutoff,))
        expired_ids = [r[0] for r in cursor.fetchall()]
        if expired_ids:
            self.remove_entries(expired_ids)
            logger.info(f"Evicted {len(expired_ids)} expired entries older than {self.ttl_days} days.")
        return expired_ids

    def clear(self) -> None:
        """Clears all entries from both SQLite and FAISS index."""
        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM cache_entries")
        try:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'cache_entries'")
        except Exception:
            pass
        self._conn.commit()

        sub_index = faiss.IndexFlatIP(self.dimension)
        self._index = faiss.IndexIDMap(sub_index)
        self._save_index_if_configured()

    def get_storage_size(self) -> Dict[str, Any]:
        """Calculates storage footprint on disk for SQLite DB and FAISS index."""
        total_bytes = 0
        db_bytes = 0
        index_bytes = 0

        if self.db_path and self.db_path != ":memory:" and os.path.exists(self.db_path):
            try:
                db_bytes = os.path.getsize(self.db_path)
                total_bytes += db_bytes
            except OSError:
                pass

        if self.index_path and self.db_path != ":memory:" and os.path.exists(self.index_path):
            try:
                index_bytes = os.path.getsize(self.index_path)
                total_bytes += index_bytes
            except OSError:
                pass

        return {
            "storage_size_bytes": total_bytes,
            "storage_size_kb": round(total_bytes / 1024.0, 2),
            "db_file_bytes": db_bytes,
            "index_file_bytes": index_bytes
        }

    def get_stats(self) -> Dict[str, Any]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*), SUM(hit_count), SUM(total_tokens * hit_count) FROM cache_entries")
        row = cursor.fetchone()
        count = row[0] or 0
        total_hits = row[1] or 0
        avoided_tokens = row[2] or 0

        storage_info = self.get_storage_size()

        return {
            "total_entries": count,
            "total_hits": total_hits,
            "cache_hits": total_hits,
            "faiss_total_vectors": self._index.ntotal if self._index else 0,
            "avoided_model_calls": total_hits,
            "avoided_tokens": avoided_tokens,
            "max_entries": self.max_entries,
            "ttl_days": self.ttl_days,
            "cache_db_path": self.db_path,
            "cache_index_path": self.index_path,
            **storage_info
        }

    def _save_index_if_configured(self):
        if self.index_path and self.db_path != ":memory:":
            try:
                os.makedirs(os.path.dirname(os.path.abspath(self.index_path)), exist_ok=True)
                faiss.write_index(self._index, self.index_path)
            except Exception as e:
                logger.error(f"Failed to persist FAISS index: {e}")

    def _row_to_entry(self, row: sqlite3.Row) -> CacheEntry:
        entities = []
        if row["entities"]:
            try:
                entities = json.loads(row["entities"])
            except Exception:
                pass

        constraints = []
        if row["constraints"]:
            try:
                constraints = json.loads(row["constraints"])
            except Exception:
                pass

        return CacheEntry(
            id=row["id"],
            query=row["query"],
            normalized_query=row["normalized_query"],
            answer=row["answer"],
            task_type=row["task_type"] or "general_qa",
            entities=entities,
            constraints=constraints,
            route=row["route"] or "",
            provider=row["provider"] or "",
            model=row["model"] or "",
            prompt_tokens=row["prompt_tokens"] or 0,
            completion_tokens=row["completion_tokens"] or 0,
            total_tokens=row["total_tokens"] or 0,
            execution_time_ms=row["execution_time_ms"] or 0.0,
            created_at=row["created_at"],
            last_used_at=row["last_used_at"],
            hit_count=row["hit_count"] or 0,
            is_dynamic=bool(row["is_dynamic"]),
            analysis_json=row["analysis_json"]
        )

    def close(self):
        if self._conn:
            self._conn.close()

# Global default instance
cache_store = CacheStore()

import logging
from typing import List, Optional, Callable
import numpy as np
from config.settings import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Precision-First Embedding Service using SentenceTransformers.
    Computes L2-normalized embeddings for accurate cosine similarity calculation.
    Supports lazy model loading and custom/mock encoder injection for offline tests.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.CACHE_EMBEDDING_MODEL
        self._model = None
        self._custom_encoder: Optional[Callable[[List[str]], np.ndarray]] = None
        self._dimension: Optional[int] = None

    def set_custom_encoder(self, encoder: Optional[Callable[[List[str]], np.ndarray]], dimension: int = 384):
        """Allows injecting a custom or mock embedding function for fast, offline unit testing."""
        self._custom_encoder = encoder
        self._dimension = dimension

    def _load_model(self):
        if self._custom_encoder is not None:
            return
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading sentence-transformer embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                if hasattr(self._model, "get_embedding_dimension"):
                    self._dimension = self._model.get_embedding_dimension()
                else:
                    self._dimension = self._model.get_sentence_embedding_dimension()
            except Exception as e:
                logger.error(f"Failed to load sentence-transformer model {self.model_name}: {e}")
                raise

    @property
    def dimension(self) -> int:
        if self._dimension is not None:
            return self._dimension
        self._load_model()
        return self._dimension or 384

    def embed_query(self, query: str) -> np.ndarray:
        """Embeds a single query string into a 1D L2-normalized float32 numpy vector."""
        batch = self.embed_batch([query])
        return batch[0]

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Embeds a list of texts into a 2D (N, D) L2-normalized float32 numpy array."""
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        if self._custom_encoder is not None:
            vectors = self._custom_encoder(texts)
            vectors = np.array(vectors, dtype=np.float32)
        else:
            self._load_model()
            vectors = self._model.encode(
                texts,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True
            )

        # Ensure L2 normalization and float32 dtype for FAISS cosine similarity
        vectors = vectors.astype(np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = vectors / norms
        return normalized

# Global default instance
embedding_service = EmbeddingService()

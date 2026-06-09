"""
Vector Embedding Pipeline for Study Materials
NVIDIA nv-embedqa-e5-v5 API for embeddings + FAISS for local vector storage.
"""
import asyncio
import json
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple, Union
from pathlib import Path
import logging
import pickle
import httpx

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingMetadata:
    """Metadata for a stored embedding"""
    chunk_id: str
    document_id: Optional[str] = None
    user_id: Optional[str] = None
    syllabus_tags: List[str] = field(default_factory=list)  # topic IDs
    chunk_type: str = "paragraph"
    source: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """Result from vector search"""
    chunk_id: str
    content: str
    score: float  # Similarity score (higher is better)
    metadata: EmbeddingMetadata

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "score": float(self.score),
            "metadata": {
                "document_id": self.metadata.document_id,
                "user_id": self.metadata.user_id,
                "syllabus_tags": self.metadata.syllabus_tags,
                "chunk_type": self.metadata.chunk_type,
                "source": self.metadata.source,
            }
        }


class NvidiaEmbeddingModel:
    """
    NVIDIA NIM embedding model via API.
    Uses nvidia/nv-embedqa-e5-v5 (1024-dim) — no local model download required.
    """

    EMBED_URL = "https://integrate.api.nvidia.com/v1/embeddings"
    BATCH_SIZE = 50  # API limit

    def __init__(
        self,
        model_name: str = "nvidia/nv-embedqa-e5-v5",
        api_key: Optional[str] = None,
        dimension: int = 1024,
    ):
        self.model_name = model_name
        self._dimension = dimension

        # Resolve API key
        if api_key:
            self._api_key = api_key
        else:
            try:
                from app.core.config import settings
                self._api_key = settings.NVIDIA_API_KEY
            except Exception:
                self._api_key = None

        if not self._api_key:
            logger.warning("NVIDIA_API_KEY not configured — embeddings will fail.")

    @property
    def dimension(self) -> int:
        return self._dimension

    def _build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def embed_async(
        self,
        texts: List[str],
        input_type: str = "passage",  # "passage" for indexing, "query" for search
        max_retries: int = 3,
    ) -> np.ndarray:
        """
        Generate embeddings via NVIDIA API.

        Args:
            texts: List of texts to embed
            input_type: "passage" for document chunks, "query" for search queries
            max_retries: Number of retry attempts on failure

        Returns:
            numpy array of shape (len(texts), dimension)
        """
        if not texts:
            return np.zeros((0, self._dimension), dtype=np.float32)

        all_embeddings = []

        # Process in batches
        for batch_start in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[batch_start: batch_start + self.BATCH_SIZE]
            batch_embeddings = await self._embed_batch(batch, input_type, max_retries)
            all_embeddings.extend(batch_embeddings)

        return np.array(all_embeddings, dtype=np.float32)

    async def _embed_batch(
        self,
        texts: List[str],
        input_type: str,
        max_retries: int,
    ) -> List[List[float]]:
        """Embed a single batch of texts with retry logic."""
        payload = {
            "input": texts,
            "model": self.model_name,
            "input_type": input_type,
            "encoding_format": "float",
            "truncate": "END",
        }

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        self.EMBED_URL,
                        headers=self._build_headers(),
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()

                # Sort by index to maintain order
                sorted_data = sorted(data["data"], key=lambda x: x["index"])
                return [item["embedding"] for item in sorted_data]

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning(f"Rate limited, retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"NVIDIA embedding API error: {e.response.status_code} - {e.response.text}")
                    raise
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    logger.warning(f"Embedding attempt {attempt + 1} failed: {e}")
                else:
                    raise

        return []

    def embed(self, texts: List[str], input_type: str = "passage") -> np.ndarray:
        """Synchronous wrapper (runs async in new event loop if needed)."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.embed_async(texts, input_type))
                    return future.result()
            else:
                return loop.run_until_complete(self.embed_async(texts, input_type))
        except RuntimeError:
            return asyncio.run(self.embed_async(texts, input_type))


# Keep the old name as an alias so existing imports don't break
EmbeddingModel = NvidiaEmbeddingModel


class FAISSVectorStore:
    """
    FAISS-based vector store with metadata filtering.

    Features:
    - Fast similarity search
    - Metadata filtering (user_id, document_id, syllabus_tag)
    - Persistence to disk
    - Async-friendly design
    """

    def __init__(
        self,
        dimension: int = 1024,
        index_type: str = "flat",  # flat, ivf, hnsw
        storage_path: Optional[str] = None,
    ):
        self.dimension = dimension
        self.index_type = index_type
        self.storage_path = Path(storage_path) if storage_path else None

        self._index = None
        self._id_map: Dict[int, str] = {}  # FAISS ID -> chunk_id
        self._chunk_map: Dict[str, int] = {}  # chunk_id -> FAISS ID
        self._metadata: Dict[str, EmbeddingMetadata] = {}  # chunk_id -> metadata
        self._contents: Dict[str, str] = {}  # chunk_id -> content
        self._next_id = 0

        self._init_index()

    def _init_index(self):
        """Initialize FAISS index"""
        try:
            import faiss

            if self.index_type == "flat":
                self._index = faiss.IndexFlatIP(self.dimension)
            elif self.index_type == "ivf":
                quantizer = faiss.IndexFlatIP(self.dimension)
                self._index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)
            elif self.index_type == "hnsw":
                self._index = faiss.IndexHNSWFlat(self.dimension, 32)
            else:
                self._index = faiss.IndexFlatIP(self.dimension)

            logger.info(f"Initialized FAISS index: {self.index_type} (dim={self.dimension})")

        except ImportError:
            logger.error("FAISS not installed. Install with: pip install faiss-cpu")
            raise

    def add(
        self,
        embeddings: np.ndarray,
        contents: List[str],
        metadata_list: List[EmbeddingMetadata],
    ) -> List[str]:
        """Add embeddings to the index."""
        assert len(embeddings) == len(contents) == len(metadata_list)

        chunk_ids = []

        for i, (content, metadata) in enumerate(zip(contents, metadata_list)):
            chunk_id = metadata.chunk_id
            faiss_id = self._next_id

            self._id_map[faiss_id] = chunk_id
            self._chunk_map[chunk_id] = faiss_id
            self._metadata[chunk_id] = metadata
            self._contents[chunk_id] = content

            chunk_ids.append(chunk_id)
            self._next_id += 1

        embeddings = embeddings.astype(np.float32)
        self._index.add(embeddings)

        logger.debug(f"Added {len(embeddings)} embeddings to index. Total: {self._index.ntotal}")

        return chunk_ids

    async def add_async(
        self,
        embeddings: np.ndarray,
        contents: List[str],
        metadata_list: List[EmbeddingMetadata],
    ) -> List[str]:
        """Async wrapper for add"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.add, embeddings, contents, metadata_list
        )

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        user_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        syllabus_tags: Optional[List[str]] = None,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """Search for similar chunks with optional filtering."""
        if self._index.ntotal == 0:
            return []

        # FAISS requires 2D input (n_queries, dim). Reshape if 1D.
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        # Guard: dimension mismatch → return empty rather than crashing
        if query_embedding.shape[1] != self._index.d:
            logger.error(
                f"FAISS dimension mismatch: query={query_embedding.shape[1]}, "
                f"index={self._index.d}. Reset the index by deleting data/vectors/."
            )
            return []

        # Search more than top_k to account for filtering
        search_k = min(top_k * 5, self._index.ntotal)

        query_embedding = query_embedding.astype(np.float32).reshape(1, -1)
        scores, indices = self._index.search(query_embedding, search_k)

        results = []

        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue

            chunk_id = self._id_map.get(idx)
            if not chunk_id:
                continue

            metadata = self._metadata.get(chunk_id)
            if not metadata:
                continue

            # Apply filters
            if user_id and metadata.user_id and metadata.user_id != user_id:
                continue

            if document_ids:
                if metadata.document_id not in document_ids:
                    continue

            if syllabus_tags:
                if not any(tag in metadata.syllabus_tags for tag in syllabus_tags):
                    continue

            if score < min_score:
                continue

            content = self._contents.get(chunk_id, "")

            results.append(SearchResult(
                chunk_id=chunk_id,
                content=content,
                score=float(score),
                metadata=metadata,
            ))

            if len(results) >= top_k:
                break

        return results

    async def search_async(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        user_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        syllabus_tags: Optional[List[str]] = None,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """Async wrapper for search"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.search(query_embedding, top_k, user_id, document_ids, syllabus_tags, min_score)
        )

    def delete(self, chunk_ids: List[str]) -> int:
        """Remove chunks from metadata (FAISS doesn't support deletion)."""
        deleted = 0
        for chunk_id in chunk_ids:
            if chunk_id in self._metadata:
                del self._metadata[chunk_id]
                del self._contents[chunk_id]
                deleted += 1
        return deleted

    def save(self, path: Optional[str] = None):
        """Save index and metadata to disk."""
        import faiss

        save_path = Path(path) if path else self.storage_path
        if not save_path:
            raise ValueError("No storage path specified")

        save_path.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self._index, str(save_path / "index.faiss"))

        data = {
            "id_map": self._id_map,
            "chunk_map": self._chunk_map,
            "metadata": {k: v.__dict__ for k, v in self._metadata.items()},
            "contents": self._contents,
            "next_id": self._next_id,
            "dimension": self.dimension,
        }

        with open(save_path / "metadata.pkl", "wb") as f:
            pickle.dump(data, f)

        logger.info(f"Saved vector store: {self._index.ntotal} vectors → {save_path}")

    def load(self, path: Optional[str] = None):
        """Load index and metadata from disk."""
        import faiss

        load_path = Path(path) if path else self.storage_path
        if not load_path or not load_path.exists():
            raise ValueError(f"Path does not exist: {load_path}")

        index_file = load_path / "index.faiss"
        meta_file = load_path / "metadata.pkl"

        if not index_file.exists() or not meta_file.exists():
            raise ValueError(f"Index files not found in {load_path}")

        loaded_index = faiss.read_index(str(index_file))

        # Validate dimension — if saved index has different dim, discard it
        if loaded_index.d != self._dimension:
            logger.warning(
                f"Stale FAISS index has dim={loaded_index.d}, expected dim={self._dimension}. "
                f"Discarding stale index and starting fresh. Re-upload your documents."
            )
            # Leave _index as the fresh empty one initialized in __init__
            return

        self._index = loaded_index

        with open(meta_file, "rb") as f:
            data = pickle.load(f)

        self._id_map = data["id_map"]
        self._chunk_map = data["chunk_map"]
        self._metadata = {
            k: EmbeddingMetadata(**v) for k, v in data["metadata"].items()
        }
        self._contents = data["contents"]
        self._next_id = data["next_id"]

        logger.info(f"Loaded vector store: {self._index.ntotal} vectors from {load_path}")

    @property
    def size(self) -> int:
        """Number of vectors in the index"""
        return self._index.ntotal if self._index else 0


class EmbeddingPipeline:
    """
    Complete embedding pipeline for study materials.
    Uses NVIDIA API for embeddings + FAISS for local storage.
    """

    def __init__(
        self,
        model_name: str = "nvidia/nv-embedqa-e5-v5",
        storage_path: Optional[str] = None,
        index_type: str = "flat",
        dimension: int = 1024,
    ):
        self.embedding_model = NvidiaEmbeddingModel(
            model_name=model_name,
            dimension=dimension,
        )
        self.vector_store = FAISSVectorStore(
            dimension=dimension,
            index_type=index_type,
            storage_path=storage_path,
        )
        self._storage_path = storage_path

        # Try to load existing index on init
        if storage_path:
            try:
                self.vector_store.load()
                logger.info(f"Loaded existing vector store ({self.vector_store.size} vectors)")
            except Exception:
                logger.info(f"No existing vector store at {storage_path}, starting fresh.")

    async def index_chunks(
        self,
        chunks: List[Dict[str, Any]],
        user_id: Optional[str] = None,
    ) -> int:
        """
        Index a list of document chunks.

        Args:
            chunks: List of dicts with keys: id, content, document_id, chunk_type, source, syllabus_tags
            user_id: Owner user ID

        Returns:
            Number of chunks indexed
        """
        if not chunks:
            return 0

        contents = [c["content"] for c in chunks]

        metadata_list = []
        for chunk in chunks:
            metadata = EmbeddingMetadata(
                chunk_id=chunk.get("id", str(hash(chunk["content"]))),
                document_id=chunk.get("document_id"),
                user_id=user_id,
                syllabus_tags=chunk.get("syllabus_tags", []),
                chunk_type=chunk.get("chunk_type", "paragraph"),
                source=chunk.get("source", ""),
            )
            metadata_list.append(metadata)

        logger.info(f"Generating embeddings for {len(contents)} chunks via NVIDIA API...")
        embeddings = await self.embedding_model.embed_async(contents, input_type="passage")

        await self.vector_store.add_async(embeddings, contents, metadata_list)

        # Auto-save after indexing
        self.save()

        logger.info(f"Indexed {len(chunks)} chunks. Total vectors: {self.vector_store.size}")
        return len(chunks)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        user_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        syllabus_tags: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """
        Search for relevant chunks using semantic similarity.

        Args:
            query: Search query text
            top_k: Number of results to return
            user_id: Filter by user
            document_ids: Filter by specific documents
            syllabus_tags: Filter by syllabus topics

        Returns:
            List of SearchResult objects
        """
        query_embedding = await self.embedding_model.embed_async([query], input_type="query")

        results = await self.vector_store.search_async(
            query_embedding[0],
            top_k=top_k,
            user_id=user_id,
            document_ids=document_ids,
            syllabus_tags=syllabus_tags,
        )

        return results

    def save(self):
        """Save the vector store to disk."""
        if self._storage_path:
            self.vector_store.save()

    def load(self):
        """Load the vector store from disk."""
        self.vector_store.load()


# Convenience function (backward compatible)
async def create_embedding_pipeline(
    storage_path: str = "data/vectors",
    model_name: str = "nvidia/nv-embedqa-e5-v5",
) -> EmbeddingPipeline:
    """Create and initialize an embedding pipeline"""
    return EmbeddingPipeline(
        model_name=model_name,
        storage_path=storage_path,
    )

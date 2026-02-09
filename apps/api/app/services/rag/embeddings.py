"""
Vector Embedding Pipeline for Study Materials
Sentence-level embeddings with FAISS vector store and metadata filtering.
"""
import asyncio
import json
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple, Union
from pathlib import Path
import logging
import pickle

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


class EmbeddingModel:
    """
    Wrapper for embedding models.
    Supports sentence-transformers for local embedding.
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
    ):
        self.model_name = model_name
        self.device = device
        self._model = None
        self._dimension = None
    
    def _load_model(self):
        """Lazy load the embedding model"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name, device=self.device)
                self._dimension = self._model.get_sentence_embedding_dimension()
                logger.info(f"Loaded embedding model: {self.model_name} (dim={self._dimension})")
            except ImportError:
                logger.error("sentence-transformers not installed. Install with: pip install sentence-transformers")
                raise
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension"""
        self._load_model()
        return self._dimension
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings
            
        Returns:
            numpy array of shape (len(texts), dimension)
        """
        self._load_model()
        embeddings = self._model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,  # For cosine similarity
            show_progress_bar=False,
        )
        return embeddings
    
    async def embed_async(self, texts: List[str]) -> np.ndarray:
        """Async wrapper for embedding"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed, texts)


class FAISSVectorStore:
    """
    FAISS-based vector store with metadata filtering.
    
    Features:
    - Fast similarity search
    - Metadata filtering (user_id, syllabus_tag)
    - Persistence to disk
    - Async-friendly design
    """
    
    def __init__(
        self,
        dimension: int = 384,
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
                # Exact search - best for small datasets
                self._index = faiss.IndexFlatIP(self.dimension)
            elif self.index_type == "ivf":
                # IVF for larger datasets
                quantizer = faiss.IndexFlatIP(self.dimension)
                self._index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)
            elif self.index_type == "hnsw":
                # HNSW for large datasets with fast search
                self._index = faiss.IndexHNSWFlat(self.dimension, 32)
            else:
                self._index = faiss.IndexFlatIP(self.dimension)
            
            logger.info(f"Initialized FAISS index: {self.index_type}")
            
        except ImportError:
            logger.error("FAISS not installed. Install with: pip install faiss-cpu")
            raise
    
    def add(
        self,
        embeddings: np.ndarray,
        contents: List[str],
        metadata_list: List[EmbeddingMetadata],
    ) -> List[str]:
        """
        Add embeddings to the index.
        
        Args:
            embeddings: Numpy array of embeddings
            contents: List of text contents
            metadata_list: List of metadata objects
            
        Returns:
            List of chunk IDs
        """
        assert len(embeddings) == len(contents) == len(metadata_list)
        
        chunk_ids = []
        
        for i, (content, metadata) in enumerate(zip(contents, metadata_list)):
            chunk_id = metadata.chunk_id
            faiss_id = self._next_id
            
            # Store mappings
            self._id_map[faiss_id] = chunk_id
            self._chunk_map[chunk_id] = faiss_id
            self._metadata[chunk_id] = metadata
            self._contents[chunk_id] = content
            
            chunk_ids.append(chunk_id)
            self._next_id += 1
        
        # Add to FAISS index
        embeddings = embeddings.astype(np.float32)
        self._index.add(embeddings)
        
        logger.debug(f"Added {len(embeddings)} embeddings to index")
        
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
        """
        Search for similar chunks with optional filtering.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results
            user_id: Filter by user ID
            syllabus_tags: Filter by syllabus topic IDs
            min_score: Minimum similarity score
            
        Returns:
            List of SearchResult objects
        """
        if self._index.ntotal == 0:
            return []
        
        # Search more than top_k to account for filtering
        search_k = min(top_k * 5, self._index.ntotal)
        
        query_embedding = query_embedding.astype(np.float32).reshape(1, -1)
        scores, indices = self._index.search(query_embedding, search_k)
        
        results = []
        
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
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
        """
        Delete chunks by ID.
        Note: FAISS doesn't support deletion, so we just remove from metadata.
        For production, use a database-backed solution or rebuild index.
        """
        deleted = 0
        for chunk_id in chunk_ids:
            if chunk_id in self._metadata:
                del self._metadata[chunk_id]
                del self._contents[chunk_id]
                deleted += 1
        return deleted
    
    def save(self, path: Optional[str] = None):
        """Save index and metadata to disk"""
        import faiss
        
        save_path = Path(path) if path else self.storage_path
        if not save_path:
            raise ValueError("No storage path specified")
        
        save_path.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self._index, str(save_path / "index.faiss"))
        
        # Save metadata
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
        
        logger.info(f"Saved vector store to {save_path}")
    
    def load(self, path: Optional[str] = None):
        """Load index and metadata from disk"""
        import faiss
        
        load_path = Path(path) if path else self.storage_path
        if not load_path or not load_path.exists():
            raise ValueError(f"Path does not exist: {load_path}")
        
        # Load FAISS index
        self._index = faiss.read_index(str(load_path / "index.faiss"))
        
        # Load metadata
        with open(load_path / "metadata.pkl", "rb") as f:
            data = pickle.load(f)
        
        self._id_map = data["id_map"]
        self._chunk_map = data["chunk_map"]
        self._metadata = {
            k: EmbeddingMetadata(**v) for k, v in data["metadata"].items()
        }
        self._contents = data["contents"]
        self._next_id = data["next_id"]
        
        logger.info(f"Loaded vector store from {load_path} ({self._index.ntotal} vectors)")
    
    @property
    def size(self) -> int:
        """Number of vectors in the index"""
        return self._index.ntotal if self._index else 0


class EmbeddingPipeline:
    """
    Complete embedding pipeline for study materials.
    
    Combines:
    - Text chunking
    - Embedding generation
    - Vector storage
    - Similarity search
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        storage_path: Optional[str] = None,
        index_type: str = "flat",
    ):
        self.embedding_model = EmbeddingModel(model_name)
        self.vector_store = FAISSVectorStore(
            dimension=self.embedding_model.dimension,
            index_type=index_type,
            storage_path=storage_path,
        )
        
        # Try to load existing index
        if storage_path:
            try:
                self.vector_store.load()
            except Exception:
                logger.info(f"No existing vector store found at {storage_path}, starting fresh.")
    
    async def index_chunks(
        self,
        chunks: List[Dict[str, Any]],  # List of chunk dicts with content, id, metadata
        user_id: Optional[str] = None,
    ) -> int:
        """
        Index a list of chunks.
        
        Args:
            chunks: List of chunk dictionaries
            user_id: Owner user ID
            
        Returns:
            Number of chunks indexed
        """
        if not chunks:
            return 0
        
        # Extract content and metadata
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
        
        # Generate embeddings
        embeddings = await self.embedding_model.embed_async(contents)
        
        # Store in vector store
        await self.vector_store.add_async(embeddings, contents, metadata_list)
        
        # Save to disk
        self.save()
        
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
        Search for relevant chunks.
        
        Args:
            query: Search query
            top_k: Number of results
            user_id: Filter by user
            syllabus_tags: Filter by topics
            
        Returns:
            List of search results
        """
        # Embed query
        query_embedding = await self.embedding_model.embed_async([query])
        
        # Search
        results = await self.vector_store.search_async(
            query_embedding[0],
            top_k=top_k,
            user_id=user_id,
            document_ids=document_ids,
            syllabus_tags=syllabus_tags,
        )
        
        return results
    
    def save(self):
        """Save the vector store"""
        self.vector_store.save()
    
    def load(self):
        """Load the vector store"""
        self.vector_store.load()


# Convenience function
async def create_embedding_pipeline(
    storage_path: str = "data/vectors",
    model_name: str = "all-MiniLM-L6-v2",
) -> EmbeddingPipeline:
    """Create and initialize an embedding pipeline"""
    return EmbeddingPipeline(
        model_name=model_name,
        storage_path=storage_path,
    )

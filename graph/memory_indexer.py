"""Memory indexer for RAG retrieval."""

import hashlib
from pathlib import Path
from typing import Any

from llama_index.core import (
    Document,
    Settings,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding

from microclaw.config import get_embeddings_config


def _get_embed_model() -> OpenAIEmbedding:
    """Get embedding model from config.json embeddings section."""
    emb = get_embeddings_config()
    info = emb.get("info") or {}
    model = info.get("model")
    base_url = info.get("base_url") or ""
    api_key = info.get("api_key") or ""
    return OpenAIEmbedding(
        model_name=model,
        api_base=base_url or None,
        api_key=api_key,
    )


class MemoryIndexer:
    """Indexes from memory/MEMORY.md for RAG."""

    def __init__(self, base_dir: Path | str) -> None:
        self._base_dir = Path(base_dir)
        self._memory_path = self._base_dir / "memory" / "MEMORY.md"
        self._storage_dir = self._base_dir / "storage" / "memory_index"
        self._hash_path = self._storage_dir / ".memory_hash"
        self._index: Any = None

    def _get_file_hash(self) -> str:
        """Get hash of memory file."""
        if not self._memory_path.exists():
            return ""
        content = self._memory_path.read_bytes()
        return hashlib.md5(content).hexdigest()

    def _get_store_hash(self) -> str:
        """Get the stored hash from the last build."""
        if not self._hash_path.exists():
            return ""
        return self._hash_path.read_text(encoding="utf-8").strip()

    def _save_hash(self, hash_value: str) -> None:
        """Save current hash."""
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._hash_path.write_text(hash_value, encoding="utf-8")

    def _maybe_rebuild(self) -> None:
        """Rebuild index if file hash changed."""
        current_hash = self._get_file_hash()
        stored_hash = self._get_store_hash()
        if current_hash and current_hash != stored_hash:
            self._rebuild_index()

    def _rebuild_index(self) -> None:
        """Rebuild index from MEMORY.md."""
        if not self._memory_path.exists():
            self._index = None
            return
        try:
            Settings.embed_model = _get_embed_model()
            content = self._memory_path.read_text(encoding="utf-8")
            if not content.strip():
                self._index = None
                return

            doc = Document(text=content, metadata={"source": "MEMORY.md"})
            splitter = SentenceSplitter(chunk_size=256, chunk_overlap=32)
            nodes = splitter.get_nodes_from_documents([doc])

            if not nodes:
                self._index = None
                return

            self._storage_dir.mkdir(parents=True, exist_ok=True)
            index = VectorStoreIndex(nodes)
            index.storage_context.persist(persist_dir=str(self._storage_dir))
            self._index = index
            self._save_hash(self._get_file_hash())

        except Exception as e:
            print(f"Memory indexer build error: {e}")
            self._index = None

    def _load_index(self) -> Any:
        """Load index from storage."""
        if not (self._storage_dir / "docstore.json").exists():
            return None
        try:
            storage_context = StorageContext.from_defaults(
                persist_dir=str(self._storage_dir)
            )
            self._index = load_index_from_storage(storage_context)
            return self._index
        except Exception as e:
            print(f"Failed to load memory index: {e}")
            return None

    def _ensure_index(self) -> Any:
        """Ensure index is loaded: rebuild if needed, else load from storage."""
        Settings.embed_model = _get_embed_model()
        self._maybe_rebuild()
        if self._index is None:
            self._load_index()
        return self._index

    def retrieve(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Retrieve relevant chunks for a query. Returns list of {text, score}."""
        index = self._ensure_index()
        if index is None:
            return []
        try:
            retriever = index.as_retriever(similarity_top_k=top_k)
            nodes_with_scores = retriever.retrieve(query)
            return [
                {"text": n.node.get_content(), "score": float(n.score)}
                for n in nodes_with_scores
            ]
        except Exception as e:
            print(f"Memory retrieve error: {e}")
            return []


def get_memory_indexer(base_dir: Path | str) -> MemoryIndexer:
    """Return MemoryIndexer instance."""
    return MemoryIndexer(base_dir)

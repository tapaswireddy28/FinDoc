"""A tiny on-disk vector store: NumPy vectors + JSON metadata, cosine search.

For a single document this is all you need. The interface (add/search/save/load)
mirrors what FAISS or ChromaDB would give, so it's an easy swap later.
"""
import json
from pathlib import Path

import numpy as np

from config import VECTOR_DB_DIR


class VectorStore:
    def __init__(self):
        self.vectors: np.ndarray | None = None   # shape (n_chunks, dim)
        self.metadata: list[dict] = []           # one dict per chunk

    # --- build -------------------------------------------------------------
    def add(self, vectors: np.ndarray, metadata: list[dict]) -> None:
        if len(vectors) != len(metadata):
            raise ValueError("vectors and metadata length mismatch")
        self.vectors = np.asarray(vectors, dtype=np.float32)
        self.metadata = metadata

    # --- search ------------------------------------------------------------
    def search(self, query_vector: np.ndarray, k: int) -> list[dict]:
        """Return the top-k metadata dicts, each with an added 'score'."""
        if self.vectors is None or len(self.vectors) == 0:
            return []
        # vectors are normalized, so dot product is cosine similarity
        scores = self.vectors @ np.asarray(query_vector, dtype=np.float32)
        k = min(k, len(scores))
        top = np.argsort(-scores)[:k]
        results = []
        for idx in top:
            item = dict(self.metadata[int(idx)])
            item["score"] = float(scores[int(idx)])
            results.append(item)
        return results

    # --- persistence -------------------------------------------------------
    def save(self, directory: str | Path = VECTOR_DB_DIR) -> None:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        np.save(directory / "vectors.npy", self.vectors)
        (directory / "metadata.json").write_text(
            json.dumps(self.metadata, ensure_ascii=False), encoding="utf-8"
        )

    @classmethod
    def load(cls, directory: str | Path = VECTOR_DB_DIR) -> "VectorStore":
        directory = Path(directory)
        vec_path = directory / "vectors.npy"
        meta_path = directory / "metadata.json"
        if not vec_path.exists() or not meta_path.exists():
            raise FileNotFoundError(
                f"No index found in {directory}. Run `ingest` first."
            )
        store = cls()
        store.vectors = np.load(vec_path)
        store.metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        return store

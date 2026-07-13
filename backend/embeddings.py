"""Embedding wrapper: LLM Foundry's OpenAI-compatible embeddings endpoint.

Vectors are L2-normalized here so the vector store's dot-product search equals
cosine similarity. Needs LLMFOUNDRY_TOKEN (sent as "<token>:<project>").
"""
import numpy as np

from config import EMBEDDING_MODEL, EMBED_API_URL, LLM_PROJECT, LLMFOUNDRY_TOKEN


def _l2_normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0          # avoid divide-by-zero on empty rows
    return (vectors / norms).astype(np.float32)


class Embedder:
    """Lazy-loads the OpenAI-compatible embeddings client and encodes text."""

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.model_name = model_name
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not LLMFOUNDRY_TOKEN:
                raise RuntimeError(
                    "LLMFOUNDRY_TOKEN is not set - required for API embeddings. "
                    "Add it to backend/.env."
                )
            from langchain_openai import OpenAIEmbeddings
            print(f"[embeddings] using {self.model_name} via LLM Foundry")
            self._client = OpenAIEmbeddings(
                openai_api_base=EMBED_API_URL,
                openai_api_key=f"{LLMFOUNDRY_TOKEN}:{LLM_PROJECT}",
                model=self.model_name,
                check_embedding_ctx_length=False,  # gateway handles batching/limits
            )
        return self._client

    def encode(self, texts: list[str]) -> np.ndarray:
        """Embed a list of texts -> (n, dim) L2-normalized float32 array."""
        vectors = np.asarray(self.client.embed_documents(texts), dtype=np.float32)
        return _l2_normalize(vectors)

    def encode_one(self, text: str) -> np.ndarray:
        vector = np.asarray(self.client.embed_query(text), dtype=np.float32)
        return _l2_normalize(vector[None, :])[0]

"""RAG orchestration: ingest a document, then answer / summarize from it."""
from pathlib import Path

from config import TOP_K, SUMMARY_MAX_CHUNKS, VECTOR_DB_DIR, MIN_RELEVANCE_SCORE
from parser import extract_pages
from chunker import chunk_pages
from embeddings import Embedder
from vectorstore import VectorStore
from generator import Generator


class RAGPipeline:
    def __init__(self):
        self.embedder = Embedder()
        self.generator = Generator()

    # --- INGEST: parse -> chunk -> embed -> store --------------------------
    def ingest(self, path: str | Path) -> int:
        # pass the vision OCR callback so image files can be ingested too
        pages = extract_pages(path, ocr=self.generator.ocr_image)
        if not pages:
            raise ValueError("No extractable text found in the document.")

        chunks = chunk_pages(pages)
        print(f"[rag] {len(pages)} page(s) -> {len(chunks)} chunk(s); embedding...")

        vectors = self.embedder.encode([c["text"] for c in chunks])

        # store the source filename on each chunk for nicer citations
        source = Path(path).name
        for c in chunks:
            c["source"] = source

        store = VectorStore()
        store.add(vectors, chunks)
        store.save()
        print(f"[rag] index saved to {VECTOR_DB_DIR}")
        return len(chunks)

    # --- ASK: retrieve -> generate -> cite ---------------------------------
    def ask(self, question: str, k: int = TOP_K) -> dict:
        store = VectorStore.load()
        q_vec = self.embedder.encode_one(question)
        hits = store.search(q_vec, k)

        # Drop weak matches so the model isn't grounded on off-topic passages,
        # but always keep the single best hit so a valid question still answers.
        if hits:
            strong = [h for h in hits if h["score"] >= MIN_RELEVANCE_SCORE]
            hits = strong or hits[:1]

        context = "\n\n".join(f"[page {h['page']}] {h['text']}" for h in hits)
        answer = self.generator.answer(question, context)

        citations = sorted({h["page"] for h in hits})
        return {"answer": answer, "pages": citations, "hits": hits}

    # --- whole-document excerpt sample (shared by summarize + analyze) -----
    def _document_excerpts(self, max_chunks: int = SUMMARY_MAX_CHUNKS) -> list[str]:
        """Sample chunks evenly across the document and page-tag each excerpt."""
        chunks = VectorStore.load().metadata
        if len(chunks) > max_chunks:
            step = len(chunks) / max_chunks
            chunks = [chunks[int(i * step)] for i in range(max_chunks)]
        # tag each excerpt with its page so the model can cite where facts came from
        return [f"[page {c['page']}] {c['text']}" for c in chunks]

    # --- SUMMARIZE the whole document --------------------------------------
    def summarize(self) -> str:
        return self.generator.summarize(self._document_excerpts())

    # --- ANALYZE the whole document ----------------------------------------
    def analyze(self) -> str:
        return self.generator.analyze(self._document_excerpts())

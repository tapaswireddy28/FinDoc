"""Split page text into overlapping word-based chunks with page metadata."""
from config import CHUNK_SIZE_WORDS, CHUNK_OVERLAP_WORDS


def chunk_pages(
    pages: list[dict],
    size: int = CHUNK_SIZE_WORDS,
    overlap: int = CHUNK_OVERLAP_WORDS,
) -> list[dict]:
    """Turn [{"page", "text"}] into [{"chunk_id", "page", "text"}].

    Chunks are ~`size` words with `overlap` words shared between neighbours so
    no sentence is lost at a boundary. Each chunk keeps the page it came from,
    which becomes the citation shown with answers.
    """
    if overlap >= size:
        raise ValueError("overlap must be smaller than chunk size")

    step = size - overlap
    chunks: list[dict] = []

    for page in pages:
        words = page["text"].split()
        for start in range(0, len(words), step):
            window = words[start:start + size]
            if not window:
                continue
            chunks.append({
                "chunk_id": len(chunks),
                "page": page["page"],
                "text": " ".join(window),
            })
            if start + size >= len(words):
                break  # last window for this page

    return chunks

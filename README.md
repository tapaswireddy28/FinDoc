# FinDoc AI — Financial Document RAG

FinDoc AI is a Retrieval-Augmented Generation (RAG) web app for financial
documents (10-K, 10-Q, earnings decks, any **PDF / PPTX / image / TXT**). Give it
a document and it **answers questions**, **summarizes**, and **analyzes** it —
using only the document's own content, with **page / slide citations**.

It's a real web app: a **FastAPI** backend + a **React (Vite)** frontend, plus a
CLI for scripted use.

> Not offline: embeddings and generation run through the **LLM Foundry** gateway,
> so it needs an `LLMFOUNDRY_TOKEN` (in `backend/.env`) and network access.

## Features
- **Upload & Ask** — drag-drop a file, ask questions; answers are grounded in the
  document with page citations and show the source passages.
- **Voice input** — a "TAP TO SPEAK" orb dictates your question (Web Speech API).
- **Summarize** — one-click structured, page-cited summary of the whole document.
- **Analyze** — structured analysis with a **Sentiment** verdict, key themes,
  entities, notable figures, and suggested questions.
- **History** — past Q&A kept in the browser (localStorage); revisit or clear.
- **Streak** — a calendar tracking days you used the app.
- **Light / dark theme** toggle (persisted; follows your OS by default).

## Pipeline
`parse (PyMuPDF / python-pptx / vision OCR) → chunk (160w, 30 overlap) → embed
(text-embedding-3-small, 1536-dim) → store (NumPy + JSON) → retrieve (cosine,
top-6) → generate (hosted LLM via LLM Foundry) → cite (page / slide)`

If the model/token/network is unavailable, generation falls back to an
**extractive** answer (returns the most relevant passage) so the app still works.

## Setup
```bash
# 1. Backend dependencies
cd backend
python -m pip install -r requirements.txt

# 2. Add your token: copy the template and fill it in
#    (config.py auto-loads backend/.env, so run commands stay secret-free)
cp .env.example .env          # then edit .env:  LLMFOUNDRY_TOKEN=your_token_here
```

## Run (web app)
```bash
# Terminal 1 — backend API on http://127.0.0.1:8000
cd backend
python -m uvicorn app:app          # use `python -m uvicorn` if `uvicorn` isn't on PATH

# Terminal 2 — frontend dev server (proxies /api → :8000)
cd frontend
npm install                        # first time only
npm run dev                        # open the printed http://localhost:5173 (or 5174)
```

## Run (CLI, no browser)
```bash
cd backend
python cli.py ingest "../data/AnnualReport.pdf"
python cli.py ask "What were total net sales in 2024?"
python cli.py summarize
```

## API
| Method & path        | Body / result |
|----------------------|---------------|
| `POST /api/upload`   | multipart file → ingest → `{chunks, source}` |
| `POST /api/ingest`   | `{path}` → ingest a file already on disk |
| `POST /api/ask`      | `{question}` → `{answer, pages, hits}` |
| `POST /api/summarize`| → `{summary}` (structured, page-cited) |
| `POST /api/analyze`  | → `{analysis}` (sentiment, themes, entities, figures) |
| `GET  /`             | serves the built frontend from `static/` |

## Configuration (`backend/config.py`)
- `LLM_MODEL` / `VISION_MODEL` — the hosted chat + vision models (swappable).
- `EMBEDDING_MODEL` — `text-embedding-3-small` (1536-dim).
- `CHUNK_SIZE_WORDS` (160) / `CHUNK_OVERLAP_WORDS` (30).
- `TOP_K` (6) / `SUMMARY_MAX_CHUNKS` (24) / `MIN_RELEVANCE_SCORE` (0.15).
- `GEN_MAX_NEW_TOKENS` (1536).

## Project layout
```
backend/
  app.py          FastAPI REST API + serves the built frontend
  config.py       settings + loads LLMFOUNDRY_TOKEN from .env
  parser.py       PDF / PPTX / image / TXT extraction + cleaning
  chunker.py      overlapping chunks with page/slide metadata
  embeddings.py   LLM Foundry embeddings (L2-normalized)
  vectorstore.py  NumPy vectors + JSON metadata, cosine search
  generator.py    answer / summarize / analyze + image OCR (extractive fallback)
  rag.py          ingest / ask / summarize / analyze orchestration
  cli.py          command-line interface
  static/         built frontend (served at "/")
frontend/         React + Vite UI (sidebar pages, voice, streak, theming)
data/             documents you ingest (images are NOT stored here)
vector_db/        generated index — auto-created on first ingest
```

See `IMPLEMENTATION.txt` for the full build process and design rationale.

## Notes
- `vector_db/` is **auto-created on first ingest** and safe to delete (it
  regenerates on the next upload) — hence it's git-ignored.
- Uploaded **images are transcribed then discarded** — they are not saved to `data/`.
- `backend/.env` (your token) is git-ignored; commit `.env.example` instead.

## Upgrade ideas
FAISS / ChromaDB store · multi-document libraries · financial-ratio extraction ·
company comparison · hybrid search · reranking · conversation memory.

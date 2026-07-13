"""FastAPI server for the Financial RAG app.

Wraps the existing RAGPipeline with HTTP endpoints and serves a small web UI:

    uvicorn app:app --reload        # from the backend/ folder
    open http://127.0.0.1:8000/

Endpoints:
    POST /api/ingest     {"path": "NYSE_MTX_2024.pdf"}  -> {"chunks": N, "source": ...}
    POST /api/ask        {"question": "..."}            -> {"answer", "pages", "hits"}
    POST /api/summarize                                  -> {"summary": "..."}
    POST /api/analyze                                    -> {"analysis": "..."}
"""
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import DATA_DIR, SUPPORTED_EXTS, IMAGE_EXTS
from rag import RAGPipeline

app = FastAPI(title="Financial RAG")
rag = RAGPipeline()                       # embedder + Claude generator (both lazy)
STATIC_DIR = Path(__file__).resolve().parent / "static"


# --- request models ----------------------------------------------------------
class IngestRequest(BaseModel):
    path: str


class AskRequest(BaseModel):
    question: str


# --- API ----------------------------------------------------------------------
@app.post("/api/ingest")
def ingest(req: IngestRequest):
    p = Path(req.path)
    if not p.is_absolute():                # relative names resolve against data/
        p = DATA_DIR / req.path
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {p}")
    n = rag.ingest(p)
    return {"chunks": n, "source": p.name}


@app.post("/api/upload")
def upload(file: UploadFile = File(...)):
    """Accept any supported file (PDF/PPTX/image/TXT) and ingest it.

    Images are only transcribed at ingest time, so they are processed from a
    temporary directory and never persisted in data/. Other document types are
    saved to data/ so they can be re-ingested later without re-uploading.
    """
    name = Path(file.filename or "upload").name
    ext = Path(name).suffix.lower()
    if ext not in SUPPORTED_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported type '{ext}'. Allowed: "
                   + ", ".join(sorted(SUPPORTED_EXTS)),
        )

    if ext in IMAGE_EXTS:
        # Transcribe-and-discard: keep the image out of data/ entirely.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp) / name
            with tmp_path.open("wb") as out:
                shutil.copyfileobj(file.file, out)
            try:
                n = rag.ingest(tmp_path)
            except Exception as e:  # noqa: BLE001 - surface parse/ingest errors to the UI
                raise HTTPException(status_code=400, detail=str(e))
        return {"chunks": n, "source": name}

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest = DATA_DIR / name
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    try:
        n = rag.ingest(dest)
    except Exception as e:  # noqa: BLE001 - surface parse/ingest errors to the UI
        raise HTTPException(status_code=400, detail=str(e))
    return {"chunks": n, "source": name}


@app.post("/api/ask")
def ask(req: AskRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question is empty.")
    try:
        return rag.ask(req.question)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="No document ingested yet. Ingest one first.")


@app.post("/api/summarize")
def summarize():
    try:
        return {"summary": rag.summarize()}
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="No document ingested yet. Ingest one first.")


@app.post("/api/analyze")
def analyze():
    try:
        return {"analysis": rag.analyze()}
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="No document ingested yet. Ingest one first.")


# --- web UI -------------------------------------------------------------------
# Serve the built frontend (Vite output copied into backend/static/). The
# /assets mount is guarded so the server still starts if the frontend hasn't
# been built yet — the API keeps working; only the web UI is unavailable.
if (STATIC_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/favicon.svg")
def favicon():
    icon = STATIC_DIR / "favicon.svg"
    if not icon.exists():
        raise HTTPException(status_code=404, detail="favicon not found")
    return FileResponse(icon)


@app.get("/")
def index():
    idx = STATIC_DIR / "index.html"
    if not idx.exists():
        raise HTTPException(
            status_code=404,
            detail="Frontend not built. Build the frontend and copy its dist/ "
                   "into backend/static/, or use the Vite dev server for development.",
        )
    return FileResponse(idx)

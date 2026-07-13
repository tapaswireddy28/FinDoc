"""Central configuration for the Financial RAG project.

Everything tunable lives here so nothing is hard-coded across the codebase.

Secrets (the LLM Foundry token) are loaded from a local .env file so the run
command stays clean — just `uvicorn app:app`, no env vars on the command line.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# --- Paths -------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent        # the backend/ folder
BASE_DIR = BACKEND_DIR.parent                        # the project root folder
DATA_DIR = BASE_DIR / "data"                         # put your PDFs/TXTs here
VECTOR_DB_DIR = BASE_DIR / "vector_db"               # generated index lives here

# --- Secrets -----------------------------------------------------------------
# Load backend/.env into the environment, then read the token from it. Existing
# OS-level env vars take precedence (override=False), so deployments can still
# set LLMFOUNDRY_TOKEN the usual way.
load_dotenv(BACKEND_DIR / ".env", override=False)
LLMFOUNDRY_TOKEN = os.getenv("LLMFOUNDRY_TOKEN", "").strip()

# --- Embeddings: LLM Foundry OpenAI-compatible gateway -----------------------
# text-embedding-3-small is 1536-dim. Needs LLMFOUNDRY_TOKEN + network at
# ingest/query time (sent as "<token>:<project>", same as the generator).
EMBEDDING_MODEL = "text-embedding-3-small"
EMBED_API_URL = "https://llmfoundry.straive.com/openai/v1/"

# --- Generator: Claude via LLM Foundry (Straive's Anthropic gateway) ---------
# Auth uses your LLMFOUNDRY_TOKEN env var, sent as "<token>:<project>".
# claude-sonnet-4-6 gives strong summaries/answers; switch to "claude-haiku-4-5"
# for cheaper/faster runs. Whatever you pick must be exposed by your gateway.
LLM_MODEL = "claude-sonnet-4-6"
# Vision model used to OCR/transcribe image files at ingest time.
VISION_MODEL = "claude-sonnet-4-6"
LLM_API_URL = "https://llmfoundry.straive.com/anthropic/"
LLM_PROJECT = "my-test-project"         # appended to the token as <token>:<project>

# --- Supported input formats -------------------------------------------------
TEXT_EXTS = {".txt", ".md"}
PDF_EXTS = {".pdf"}
PPTX_EXTS = {".pptx"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
SUPPORTED_EXTS = TEXT_EXTS | PDF_EXTS | PPTX_EXTS | IMAGE_EXTS

# --- Chunking ----------------------------------------------------------------
# ~160 words keeps each chunk under the embedder's 256-token limit while still
# carrying enough context. Overlap stops sentences being split between chunks.
CHUNK_SIZE_WORDS = 160
CHUNK_OVERLAP_WORDS = 30

# --- Retrieval ---------------------------------------------------------------
TOP_K = 6                 # how many chunks to retrieve for a question
SUMMARY_MAX_CHUNKS = 24   # how many chunks (sampled across the doc) to summarize
# Cosine-similarity floor (0-1) for retrieved chunks. Hits scoring below this
# are treated as irrelevant and dropped before they reach the model, which keeps
# off-topic passages out of the context. Safety net: if nothing clears the bar,
# the single best hit is still kept so a valid question can be answered.
MIN_RELEVANCE_SCORE = 0.15

# --- Generation --------------------------------------------------------------
GEN_MAX_NEW_TOKENS = 1536     # max length of the generated answer/summary

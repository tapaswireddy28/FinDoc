import base64
from pathlib import Path

from config import (
    LLM_MODEL, VISION_MODEL, LLM_API_URL, LLM_PROJECT, GEN_MAX_NEW_TOKENS,
    LLMFOUNDRY_TOKEN,
)

_MIME_BY_EXT = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
}

# --- Prompts -----------------------------------------------------------------
# Kept as named constants so they're easy to find, tweak, and version. Answer
# and summary calls are split into a system message (role + rules) and a user
# message (the actual context/question): Claude follows instructions far more
# reliably when the persona/rules are separated from the task data, and the
# document is wrapped in delimiters so the model knows exactly what to ground on.

ANSWER_SYSTEM = (
    "You are a careful research assistant. You answer questions about ONE "
    "document using only the excerpts you are given.\n"
    "Rules:\n"
    "1. Use ONLY the information in the context. Never rely on outside knowledge "
    "or guess.\n"
    "2. Copy figures, dates, names, and quotes exactly as written — never round, "
    "convert, or paraphrase numbers.\n"
    "3. Cite the source of each fact inline as (p. N), using the page shown in "
    'the "[page N]" tag that precedes each excerpt. Combine adjacent pages like '
    "(pp. 2-3).\n"
    '4. If the context does not contain the answer, reply with exactly: "Not '
    'found in the document." Do not pad it with anything else.\n'
    "5. Be concise and factual. Use short paragraphs or bullet points; lead with "
    "the direct answer."
)

ANSWER_USER = (
    "Answer the question using only the context below.\n\n"
    "<context>\n{context}\n</context>\n\n"
    "Question: {question}"
)

SUMMARY_SYSTEM = (
    "You write clear, faithful summaries of a document using only the excerpts "
    "provided. The excerpts are sampled from across the document, so they may be "
    "partial — summarize only what they actually show and never invent facts to "
    "fill gaps. Preserve key figures, dates, and named entities exactly as "
    'written, and cite the page each fact came from inline as (p. N) using the '
    '"[page N]" tag that precedes each excerpt.'
)

SUMMARY_USER = (
    "Summarize the document from the excerpts below so that someone who has not "
    "read it understands what it covers and why it matters. Write in Markdown "
    "with these sections:\n\n"
    "**Overview** — 2-3 sentences on what the document is, who produced it, and "
    "the purpose or period it covers.\n\n"
    "**Key points** — 6-10 bullets grouped by theme (e.g. business/operations, "
    "financials, strategy, outlook). Include concrete figures, dates, and names, "
    "each with its page citation (p. N), and a few words of context so the "
    "number is meaningful rather than bare.\n\n"
    '**Key risks / caveats** — bullets for any risks, uncertainties, or '
    "limitations mentioned (omit this whole section if none appear).\n\n"
    "Aim for 250-400 words. Don't repeat the same fact in more than one "
    "section.\n\n"
    "<excerpts>\n{excerpts}\n</excerpts>"
)

ANALYSIS_SYSTEM = (
    "You are an analyst who produces a structured analysis of a document using "
    "only the excerpts provided. The excerpts are sampled from across the "
    "document, so they may be partial — analyze only what they actually show and "
    "never invent facts. Preserve figures, dates, and named entities exactly as "
    'written, and cite the page each fact came from inline as (p. N) using the '
    '"[page N]" tag that precedes each excerpt.'
)

ANALYSIS_USER = (
    "Analyze the document from the excerpts below. Write in Markdown with these "
    "sections:\n\n"
    "**Document type & purpose** — what kind of document this is and what it is "
    "for.\n\n"
    "**Sentiment & tone** — start this section with a single bold verdict line in "
    "the form `**Sentiment:** <Positive | Neutral | Cautious | Negative>` , then "
    "one or two sentences explaining the overall tone with page citations "
    "(p. N). If the document mixes positive and negative signals, name both.\n\n"
    "**Key themes** — 3-6 bullets naming the main topics the document is about.\n\n"
    "**Key entities** — the notable organizations, people, places, and dates "
    "mentioned (group them by type).\n\n"
    "**Notable figures & metrics** — the most important numbers, each with a few "
    "words of context and its page citation (p. N). If the excerpts contain "
    "several comparable figures, present them as a Markdown table.\n\n"
    "**Overall assessment** — 2-3 sentences on the document's tone and main "
    "takeaway.\n\n"
    "**Questions worth asking** — 3-5 questions a reader could explore next, "
    "based on what the document covers.\n\n"
    "Aim for 300-450 words. Omit any section the excerpts give you nothing "
    "for.\n\n"
    "<excerpts>\n{excerpts}\n</excerpts>"
)

OCR_PROMPT = (
    "Transcribe ALL text in this image verbatim, preserving numbers and labels "
    "exactly. Render any tables as Markdown tables. Then add a short "
    "'Description:' of any charts, figures, or diagrams. Output plain text only "
    "— no preamble or commentary."
)


class Generator:
    def __init__(self, model_name: str = LLM_MODEL):
        self.model_name = model_name
        self._clients: dict[str, object] = {}   # model_name -> ChatAnthropic
        self._load_failed = False

    def _client_for(self, model_name: str):
        """Lazily build (and cache) a ChatAnthropic client for a given model."""
        if self._load_failed:
            return None
        if model_name not in self._clients:
            try:
                if not LLMFOUNDRY_TOKEN:
                    raise RuntimeError("LLMFOUNDRY_TOKEN is not set (add it to backend/.env)")
                from langchain_anthropic import ChatAnthropic
                print(f"[generator] using {model_name} via LLM Foundry")
                self._clients[model_name] = ChatAnthropic(
                    anthropic_api_key=f"{LLMFOUNDRY_TOKEN}:{LLM_PROJECT}",
                    anthropic_api_url=LLM_API_URL,
                    model_name=model_name,
                    max_tokens=GEN_MAX_NEW_TOKENS,
                )
            except Exception as e:  # noqa: BLE001 - fall back to extractive mode
                print(f"[generator] could not init Claude client ({e}); using extractive fallback")
                self._load_failed = True
                return None
        return self._clients[model_name]

    @property
    def client(self):
        return self._client_for(self.model_name)

    # --- vision OCR --------------------------------------------------------
    def ocr_image(self, path: str | Path) -> str:
        """Transcribe/describe an image with Claude vision. Returns "" on failure."""
        client = self._client_for(VISION_MODEL)
        if client is None:
            return ""
        path = Path(path)
        mime = _MIME_BY_EXT.get(path.suffix.lower(), "image/png")
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        try:
            from langchain_core.messages import HumanMessage
            msg = HumanMessage(content=[
                {"type": "text", "text": OCR_PROMPT},
                {"type": "image_url",
                 "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ])
            return client.invoke([msg]).content.strip()
        except Exception as e:  # noqa: BLE001 - network/auth/unsupported
            print(f"[generator] image OCR failed ({e})")
            return ""

    def _generate(self, system: str, user: str) -> str | None:
        """Return the model's text, or None if the call fails (caller falls back).

        Sends a system message (role + rules) and a user message (the task data)
        so Claude separates instructions from content.
        """
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [SystemMessage(content=system), HumanMessage(content=user)]
            return self.client.invoke(messages).content.strip()
        except Exception as e:  # noqa: BLE001 - network/auth/rate-limit at call time
            print(f"[generator] generation failed ({e}); using extractive fallback")
            return None

    # --- answering ---------------------------------------------------------
    def answer(self, question: str, context: str) -> str:
        if self.client is not None:
            text = self._generate(
                ANSWER_SYSTEM,
                ANSWER_USER.format(context=context, question=question),
            )
            if text is not None:
                return text
        # extractive fallback
        return ("(model unavailable - showing most relevant passage)\n\n"
                + context[:800])

    # --- summarizing -------------------------------------------------------
    def summarize(self, texts: list[str]) -> str:
        if not texts:
            return "No content to summarize."
        if self.client is not None:
            # Claude's context window is large enough to summarize the sampled
            # chunks in a single pass - no map-reduce needed.
            combined = "\n\n".join(texts)
            text = self._generate(SUMMARY_SYSTEM, SUMMARY_USER.format(excerpts=combined))
            if text is not None:
                return text
        # extractive fallback: first lines of each chunk
        joined = " ".join(texts)
        return "(model unavailable - extractive summary)\n\n" + joined[:1000]

    # --- analyzing ---------------------------------------------------------
    def analyze(self, texts: list[str]) -> str:
        if not texts:
            return "No content to analyze."
        if self.client is not None:
            combined = "\n\n".join(texts)
            text = self._generate(ANALYSIS_SYSTEM, ANALYSIS_USER.format(excerpts=combined))
            if text is not None:
                return text
        # extractive fallback
        joined = " ".join(texts)
        return "(model unavailable - extractive analysis)\n\n" + joined[:1000]

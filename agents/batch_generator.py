"""
Batch book generation — runs multiple book jobs in parallel,
each using a different LLM provider/model.

Usage:
    from agents.batch_generator import BatchJobSpec, run_batch_parallel, PROVIDER_MODELS

Every job runs in its own OS thread → its own asyncio event loop,
so jobs genuinely execute concurrently even under Python's GIL
(all heavy work is I/O-bound API calls).
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

# ---------------------------------------------------------------------------
# Provider → model catalogue (shown in Batch UI)
# ---------------------------------------------------------------------------
PROVIDER_MODELS: dict[str, list[str]] = {
    "github":  ["gpt-4o-mini", "gpt-4o", "Meta-Llama-3.1-70B-Instruct", "Mistral-large"],
    "qwen":    ["qwen-flash", "qwen-plus", "qwen-max", "qwen3-max"],
    "claude":  ["claude-haiku-4-5", "claude-sonnet-4-6", "claude-opus-4-6"],
    "azure":   ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-35-turbo"],
}

PROVIDER_LABELS: dict[str, str] = {
    "github": "🐙 GitHub Models",
    "qwen":   "☁️ Qwen / Alibaba",
    "claude": "🟠 Anthropic Claude",
    "azure":  "🔷 Azure OpenAI",
}

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BatchJobSpec:
    """Configuration for a single batch job."""
    job_id: str                      # e.g. "job_1"
    label: str                       # Human-readable label shown in UI
    provider: str                    # "github" | "qwen" | "claude" | "azure"
    model: str                       # model name as accepted by the agents
    # ── book params (all optional — defaults applied by caller) ──────────
    topic: str = ""
    target_audience_age: int = 12
    language: str = "English"
    country: str = "USA"
    learning_method: str = "Project-Based Learning"
    num_chapters: int = 5
    pages_per_chapter: int = 4
    template_id: str = "auto"
    palette_id: str = ""
    max_tokens_curriculum: int = 2000
    max_tokens_chapter: int = 4000
    generate_images: bool = False


@dataclass
class BatchJobResult:
    """Result of a single batch job."""
    job_id: str
    label: str
    provider: str
    model: str
    success: bool
    # Output paths (None on failure)
    html_path: str | None = None
    json_path: str | None = None
    md_path: str | None = None
    # Metrics
    elapsed_sec: float = 0.0
    tokens_est: int = 0
    num_chapters: int = 0
    word_count: int = 0
    # Error info
    error: str = ""
    # Log lines captured during generation
    log: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core: single-job async generation (no Streamlit dependency)
# ---------------------------------------------------------------------------

async def _generate_job_async(
    spec: BatchJobSpec,
    output_base: Path,
    log_fn: Callable[[str], None],
) -> tuple:
    """
    Async book generation for batch context.
    Uses the same underlying agents as the main app but logs via callback
    instead of st.empty()  so it's safe to run off the main thread.

    Returns (curriculum, full_chapters) or (None, None) on failure.
    """
    # Lazy imports — agents may not be available at module load time
    from models.book_spec import BookRequest
    from agents.curriculum_agent import create_curriculum_agent, generate_curriculum
    from agents.chapter_agent import create_chapter_agent, generate_chapter
    from agents.html_css_agent import generate_html_css_book_from_json
    from agents.markdown_agent import save_markdown_book
    from agents.html_to_pdf_converter import generate_pdf_from_data
    from models.book_spec import BookOutput
    from models.template_registry import auto_pick_template

    use_qwen = spec.provider == "qwen"

    request = BookRequest(
        topic=spec.topic,
        target_audience_age=spec.target_audience_age,
        language=spec.language,
        country=spec.country,
        learning_method=spec.learning_method,
        num_chapters=spec.num_chapters,
        pages_per_chapter=spec.pages_per_chapter,
    )

    log_fn(f"📋 Building curriculum…")
    curriculum_agent = await create_curriculum_agent(use_qwen=use_qwen, model_id=spec.model)
    curriculum = await generate_curriculum(
        curriculum_agent, request, max_tokens=spec.max_tokens_curriculum
    )
    if not curriculum:
        raise ValueError("Curriculum generation returned None")

    log_fn(f"✅ Curriculum ready — {len(curriculum.chapters)} chapters")

    chapter_agent = await create_chapter_agent(use_qwen=use_qwen, model_id=spec.model)
    context = {
        "age": request.target_audience_age,
        "country": request.country,
        "learning_method": request.learning_method,
        "language": request.language,
        "pages_per_chapter": request.pages_per_chapter,
    }

    full_chapters = []
    for i, outline in enumerate(curriculum.chapters):
        log_fn(f"📝 Chapter {i+1}/{len(curriculum.chapters)}: {outline.title}")
        chapter = await generate_chapter(
            chapter_agent, outline, context,
            max_tokens=spec.max_tokens_chapter,
            images_per_chapter=0,  # no images in batch mode (fast)
        )
        if chapter:
            full_chapters.append(chapter)

    log_fn(f"✅ All {len(full_chapters)} chapters generated")
    return curriculum, full_chapters


def _run_job_in_thread(
    spec: BatchJobSpec,
    output_base: Path,
    status: dict,        # shared mutable status dict
    status_lock,         # threading.Lock
) -> BatchJobResult:
    """
    Entry point for each thread.  Creates its own asyncio event loop.
    Writes incremental log/status to `status[spec.job_id]`.
    """
    import threading

    log: list[str] = []

    def log_fn(msg: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {msg}"
        log.append(entry)
        print(f"[{spec.job_id}] {entry}")
        with status_lock:
            status[spec.job_id]["log"] = log.copy()

    t0 = time.perf_counter()
    log_fn(f"🚀 Starting job — provider={spec.provider}, model={spec.model}")

    with status_lock:
        status[spec.job_id]["state"] = "running"

    try:
        # Each thread gets its own event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Set provider env var for this thread
        _set_provider_env(spec.provider, spec.model)

        try:
            curriculum, full_chapters = loop.run_until_complete(
                _generate_job_async(spec, output_base, log_fn)
            )
        finally:
            loop.close()

        if not curriculum or not full_chapters:
            raise ValueError("Generation returned empty data")

        # ── Save outputs ─────────────────────────────────────────────
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_dir = output_base / spec.job_id / timestamp
        json_dir  = batch_dir / "json"
        html_dir  = batch_dir / "html"
        md_dir    = batch_dir / "md"
        for d in (json_dir, html_dir, md_dir):
            d.mkdir(parents=True, exist_ok=True)

        output_data = {
            "book_request": {"topic": spec.topic, "provider": spec.provider, "model": spec.model},
            "curriculum": curriculum.model_dump(),
            "chapters": [c.model_dump() for c in full_chapters],
        }
        json_path = json_dir / "book_output.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        log_fn(f"💾 JSON saved → {json_path}")

        # Resolve template
        effective_template_id = spec.template_id
        if effective_template_id == "auto":
            effective_template_id = auto_pick_template(spec.topic)

        # Lazy import for HTML gen
        from models.book_spec import BookRequest
        from agents.html_css_agent import generate_html_css_book_from_json
        from models.book_spec import BookOutput, BookRequest
        from agents.markdown_agent import save_markdown_book

        request_obj = BookRequest(
            topic=spec.topic,
            target_audience_age=spec.target_audience_age,
            language=spec.language,
            country=spec.country,
            learning_method=spec.learning_method,
            num_chapters=spec.num_chapters,
            pages_per_chapter=spec.pages_per_chapter,
        )

        html_path = html_dir / "book.html"
        generate_html_css_book_from_json(
            request_obj, curriculum, full_chapters, str(html_path),
            template_id=effective_template_id,
            palette_id=spec.palette_id,
        )
        log_fn(f"🌐 HTML saved → {html_path}")

        md_path = md_dir / "book.md"
        book_output = BookOutput(
            book_request=request_obj,
            curriculum=curriculum,
            chapters=full_chapters,
        )
        save_markdown_book(book_output, str(md_path))
        log_fn(f"📄 Markdown saved → {md_path}")

        # Metrics
        elapsed = time.perf_counter() - t0
        text = " ".join(c.markdown_content or "" for c in full_chapters)
        words = len(text.split())
        tokens = max(1, int(words * 1.33))

        log_fn(f"🏁 Done in {elapsed:.1f}s — {words:,} words, ~{tokens:,} tokens")

        with status_lock:
            status[spec.job_id]["state"] = "done"

        return BatchJobResult(
            job_id       = spec.job_id,
            label        = spec.label,
            provider     = spec.provider,
            model        = spec.model,
            success      = True,
            html_path    = str(html_path),
            json_path    = str(json_path),
            md_path      = str(md_path),
            elapsed_sec  = elapsed,
            tokens_est   = tokens,
            num_chapters = len(full_chapters),
            word_count   = words,
            log          = log,
        )

    except Exception as exc:
        elapsed = time.perf_counter() - t0
        err_msg = f"{type(exc).__name__}: {exc}"
        log_fn(f"❌ FAILED — {err_msg}")
        log_fn(traceback.format_exc())
        with status_lock:
            status[spec.job_id]["state"] = "error"
        return BatchJobResult(
            job_id   = spec.job_id,
            label    = spec.label,
            provider = spec.provider,
            model    = spec.model,
            success  = False,
            error    = err_msg,
            elapsed_sec = elapsed,
            log      = log,
        )


def _set_provider_env(provider: str, model: str) -> None:
    """
    Configure the MODEL_PROVIDER env var so curriculum/chapter agents
    pick the right client.  Called once per thread before generation starts.
    """
    os.environ["MODEL_PROVIDER"] = provider
    if provider == "azure":
        os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = model


# ---------------------------------------------------------------------------
# Public: run multiple jobs in parallel
# ---------------------------------------------------------------------------

def run_batch_parallel(
    specs: list[BatchJobSpec],
    output_base: Path | None = None,
    max_workers: int | None = None,
) -> tuple[list[BatchJobResult], dict]:
    """
    Run all specs in parallel using a ThreadPoolExecutor.

    Returns
    -------
    results : list[BatchJobResult]  (one per spec, in completion order)
    status  : dict[job_id → {"state": str, "log": list[str]}]
              Shared mutable dict — can be polled by the UI during execution.
    """
    import threading

    if output_base is None:
        output_base = Path("books") / "batch"

    status: dict = {
        s.job_id: {"state": "pending", "log": []}
        for s in specs
    }
    lock = threading.Lock()

    workers = max_workers or len(specs)
    results: list[BatchJobResult] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_run_job_in_thread, spec, output_base, status, lock): spec
            for spec in specs
        }
        for fut in as_completed(futures):
            results.append(fut.result())

    return results, status

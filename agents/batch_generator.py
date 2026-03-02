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
    "qwen": [
        "qwen3.5-flash",
        "qwen3.5-flash-2026-02-23",
        "qwen3.5-35b-a3b",
        "qwen3.5-27b",
        "qwen3.5-122b-a10b",
    ],
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
    genre: str = "educational"
    template_id: str = "auto"
    palette_id: str = ""
    max_tokens_curriculum: int = 2000
    max_tokens_chapter: int = 4000
    generate_images: bool = False
    # ── Image settings ───────────────────────────────────────────────────
    use_ddg_images: bool = False
    image_model: str = "qwen-image-plus"
    art_style: str = "auto"
    images_per_chapter: int = 1    # ── YouTube video search settings ────────────────────────────────
    enable_youtube_search: bool = False    # ── TTS / Audio settings ─────────────────────────────────────────────
    enable_tts: bool = False
    tts_voice: str = "longxiaochun"
    tts_model: str = "qwen3-tts-vc-realtime"
    tts_audio_format: str = "wav_24k"
    tts_speech_rate: float = 0.95


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
    audio_dir: str | None = None
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
    from models.book_spec import BookRequest, BookOutput
    from agents.curriculum_agent import create_curriculum_agent, generate_curriculum
    from agents.chapter_agent import create_chapter_agent, generate_chapter

    # Pass provider explicitly so each thread uses its own config independently
    # of the MODEL_PROVIDER env-var (which is a shared global and causes race
    # conditions when multiple batch threads run concurrently).
    use_qwen = spec.provider == "qwen"  # kept for legacy callers; provider= overrides it

    request = BookRequest(
        topic=spec.topic,
        target_audience_age=spec.target_audience_age,
        language=spec.language,
        country=spec.country,
        learning_method=spec.learning_method,
        num_chapters=spec.num_chapters,
        pages_per_chapter=spec.pages_per_chapter,
        genre=spec.genre,
    )

    log_fn(f"📋 Building curriculum…")
    curriculum_agent = await create_curriculum_agent(
        use_qwen=use_qwen, model_id=spec.model, provider=spec.provider
    )
    curriculum = await generate_curriculum(
        curriculum_agent, request, max_tokens=spec.max_tokens_curriculum
    )
    if not curriculum:
        raise ValueError("Curriculum generation returned None")

    log_fn(f"✅ Curriculum ready — {len(curriculum.chapters)} chapters")

    chapter_agent = await create_chapter_agent(
        use_qwen=use_qwen, model_id=spec.model, provider=spec.provider
    )
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
            images_per_chapter=spec.images_per_chapter if (spec.generate_images or spec.use_ddg_images) else 0,
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
            js = status[spec.job_id]
            js["log"] = log.copy()
            # Update current_step from meaningful log lines
            _clean = msg.strip()
            if _clean and not _clean.startswith("Traceback") and not _clean.startswith("  File"):
                js["current_step"] = _clean[:90]

    t0 = time.perf_counter()
    log_fn(f"🚀 Starting job — provider={spec.provider}, model={spec.model}")

    with status_lock:
        status[spec.job_id]["state"] = "running"
        status[spec.job_id]["current_step"] = "🚀 Starting…"

    try:
        # Each thread gets its own event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Import here so it is available in this thread's scope (not inside _generate_job_async)
        from models.template_registry import auto_pick_template  # noqa: F811

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
        _mslug = re.sub(r'[^a-z0-9]', '-', spec.model.lower())[:20].strip('-')
        # Use resolve() so all child paths (images, html, audio) are absolute —
        # this lets _embed_images_as_base64 locate image files regardless of cwd.
        batch_dir = (output_base / spec.job_id / f"{spec.provider}_{_mslug}_{timestamp}").resolve()
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
        json_path = (json_dir / "book_output.json").resolve()
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        log_fn(f"💾 JSON saved → {json_path}")

        # Resolve template
        effective_template_id = spec.template_id
        if effective_template_id == "auto":
            effective_template_id = auto_pick_template(spec.topic)

        # Lazy import for HTML gen
        from agents.html_css_agent import generate_html_css_book_from_json
        from models.book_spec import BookOutput, BookRequest
        from agents.markdown_agent import save_markdown_book

        # ── Image injection (DDG or AI) ───────────────────────────────────
        if spec.use_ddg_images or spec.generate_images:
            n_img = max(1, spec.images_per_chapter)
            images_dir = batch_dir / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            if spec.use_ddg_images:
                from agents.ddg_image_search_agent import search_and_download_image as _ddg_search
                _img_loop = asyncio.new_event_loop()
                try:
                    for chapter in full_chapters:
                        ch_slug = re.sub(r'[^\w]', '_', chapter.chapter_title)[:30]
                        ch_img_dir = str(images_dir / ch_slug)
                        found: list[str] = []
                        for _ in range(n_img):
                            try:
                                img_path = _img_loop.run_until_complete(
                                    _ddg_search(
                                        query=f"{chapter.chapter_title} educational illustration",
                                        output_dir=ch_img_dir,
                                    )
                                )
                                if img_path:
                                    found.append(str(img_path))
                            except Exception as _ie:
                                log_fn(f"⚠️ DDG image failed: {_ie}")
                        if found:
                            chapter.generated_images = found
                            inject_md = "\n".join(f"![illustration]({p})" for p in found)
                            chapter.markdown_content = (
                                re.sub(r'\[IMAGE:[^\]]*\]', '', chapter.markdown_content or '', count=len(found))
                                + f"\n\n{inject_md}"
                            )
                            log_fn(f"🖼️ {len(found)} DDG image(s) → {chapter.chapter_title[:40]}")
                finally:
                    _img_loop.close()
            elif spec.generate_images:
                from agents.qwen_image_agent import generate_chapter_image as _gen_img
                from utils.retry import calculate_delay as _calc_delay

                log_fn(f"🖼️ Generating images in parallel ({len(full_chapters)} chapters)…")

                # Capture spec values for closure safety
                _spec_lang    = spec.language
                _spec_country = spec.country
                _spec_age     = spec.target_audience_age
                _spec_imodel  = spec.image_model
                _spec_art     = spec.art_style

                async def _gen_chapter_images_async(
                    _ch, _n: int, _sem: asyncio.Semaphore
                ) -> tuple:
                    """Parallelised per-chapter image gen with jitter+retry."""
                    _ch_title = _ch.chapter_title
                    _ch_slug  = re.sub(r'[^\w]', '_', _ch_title)[:30]
                    _ch_dir   = str(images_dir / _ch_slug)
                    _found: list[str] = []
                    _running_loop = asyncio.get_running_loop()

                    async with _sem:
                        for _img_i in range(_n):
                            for _retry in range(1, 6):  # up to 5 attempts
                                try:
                                    def _sync_call(
                                        _t=_ch_title, _sl=_ch_slug,
                                        _la=_spec_lang, _co=_spec_country, _ag=_spec_age,
                                        _im=_spec_imodel, _ar=_spec_art,
                                        _idir=str(images_dir),
                                    ):
                                        return _gen_img(
                                            title=_t, summary="",
                                            output_dir=_idir,
                                            chapter_name=_sl,
                                            language=_la, country=_co,
                                            audience_age=_ag, use_qwen_text=True,
                                            text_model="qwen3.5-flash",
                                            image_model=_im, art_style=_ar,
                                        )
                                    _res = await _running_loop.run_in_executor(None, _sync_call)
                                    if _res and _res.url:
                                        _found.append(str(_res.url))
                                    break  # success
                                except Exception as _ie:
                                    _es = str(_ie).lower()
                                    _is_rate = (
                                        "rate" in _es or "429" in _es
                                        or "throttl" in _es or "quota" in _es
                                        or "too many" in _es
                                    )
                                    if _is_rate and _retry < 5:
                                        _d = _calc_delay(_retry, base_delay=3.0, max_delay=45.0, jitter=True)
                                        log_fn(
                                            f"⚠️ Rate limit '{_ch_title[:25]}' "
                                            f"retry {_retry}/4 in {_d:.1f}s…"
                                        )
                                        await asyncio.sleep(_d)
                                    else:
                                        log_fn(
                                            f"⚠️ AI image failed '{_ch_title[:25]}': {_ie}"
                                        )
                                        break
                    return _ch, _found

                _img_loop2 = asyncio.new_event_loop()
                asyncio.set_event_loop(_img_loop2)
                try:
                    # Semaphore MUST be created inside the running loop
                    async def _run_all_images():
                        _img_sem = asyncio.Semaphore(3)  # max 3 concurrent Qwen requests
                        _tasks = [
                            _gen_chapter_images_async(ch, n_img, _img_sem)
                            for ch in full_chapters
                        ]
                        return await asyncio.gather(*_tasks, return_exceptions=True)

                    _img_results2 = _img_loop2.run_until_complete(_run_all_images())
                finally:
                    _img_loop2.close()

                for _item in _img_results2:
                    if isinstance(_item, Exception):
                        log_fn(f"⚠️ Image batch task exception: {_item}")
                        continue
                    _chapter, _found2 = _item
                    if _found2:
                        _chapter.generated_images = _found2
                        _inject = "\n".join(f"![illustration]({p})" for p in _found2)
                        _chapter.markdown_content = (
                            re.sub(
                                r'\[IMAGE:[^\]]*\]',
                                '',
                                _chapter.markdown_content or '',
                                count=len(_found2),
                            )
                            + f"\n\n{_inject}"
                        )
                        log_fn(f"🖼️ {len(_found2)} AI image(s) → {_chapter.chapter_title[:40]}")

        # ── YouTube video search ──────────────────────────────────────────
        if spec.enable_youtube_search:
            from agents.youtube_search_agent import search_videos_for_chapter as _yt_search
            log_fn(f"🎬 Searching YouTube videos for {len(full_chapters)} chapters…")
            _yt_loop = asyncio.new_event_loop()
            try:
                async def _yt_search_all():
                    for _ch in full_chapters:
                        try:
                            _video_queries = re.findall(
                                r'\[VIDEO:\s*([^\]]+)\]', _ch.markdown_content or ''
                            )
                            if not _video_queries:
                                _video_queries = [
                                    f"{_ch.chapter_title} {spec.language} educational"
                                ]
                            _videos = await _yt_search(
                                chapter_title=_ch.chapter_title,
                                video_queries=_video_queries,
                                topic=spec.topic,
                                language=spec.language,
                                country=spec.country,
                            )
                            if _videos:
                                _ch.youtube_videos = _videos
                                log_fn(
                                    f"🎬 {len(_videos)} video(s) → {_ch.chapter_title[:40]}"
                                )
                        except Exception as _ve:
                            log_fn(f"⚠️ YouTube search failed for '{_ch.chapter_title[:30]}': {_ve}")
                _yt_loop.run_until_complete(_yt_search_all())
            finally:
                _yt_loop.close()

        request_obj = BookRequest(
            topic=spec.topic,
            target_audience_age=spec.target_audience_age,
            language=spec.language,
            country=spec.country,
            learning_method=spec.learning_method,
            num_chapters=spec.num_chapters,
            pages_per_chapter=spec.pages_per_chapter,
            genre=spec.genre,
        )

        html_path = (html_dir / "book.html").resolve()
        generate_html_css_book_from_json(
            request_obj, curriculum, full_chapters, str(html_path),
            template_id=effective_template_id,
            palette_id=spec.palette_id,
        )
        log_fn(f"🌐 HTML saved → {html_path}")

        md_path = (md_dir / "book.md").resolve()
        book_output = BookOutput(
            book_request=request_obj,
            curriculum=curriculum,
            chapters=full_chapters,
        )
        save_markdown_book(book_output, str(md_path))
        log_fn(f"📄 Markdown saved → {md_path}")

        # ── Audio narration ───────────────────────────────────────────────
        audio_dir_str: str | None = None
        if spec.enable_tts:
            from agents.voice_agent import narrate_chapter as _narrate
            audio_dir_path = batch_dir / "audio"
            audio_dir_path.mkdir(parents=True, exist_ok=True)
            audio_dir_str = str(audio_dir_path)
            for chapter in full_chapters:
                log_fn(f"🔊 Narrating: {chapter.chapter_title[:50]}…")
                try:
                    nar = _narrate(
                        chapter_title=chapter.chapter_title,
                        markdown_content=chapter.markdown_content or "",
                        output_dir=audio_dir_str,
                        voice=spec.tts_voice,
                        model=spec.tts_model,
                        audio_format=spec.tts_audio_format,
                        speech_rate=spec.tts_speech_rate,
                    )
                    if nar:
                        chapter.audio_narration = nar
                        log_fn(f"   🔔 Audio → {Path(nar.file_path).name}")
                except Exception as _ae:
                    log_fn(f"⚠️ Audio failed — {_ae}")

        # Metrics
        elapsed = time.perf_counter() - t0
        text = " ".join(c.markdown_content or "" for c in full_chapters)
        words = len(text.split())
        tokens = max(1, int(words * 1.33))

        log_fn(f"🏁 Done in {elapsed:.1f}s — {words:,} words, ~{tokens:,} tokens")

        with status_lock:
            status[spec.job_id]["state"] = "done"
            status[spec.job_id]["current_step"] = "🏁 Complete"

        return BatchJobResult(
            job_id       = spec.job_id,
            label        = spec.label,
            provider     = spec.provider,
            model        = spec.model,
            success      = True,
            html_path    = str(html_path),
            json_path    = str(json_path),
            md_path      = str(md_path),
            audio_dir    = audio_dir_str,
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
            status[spec.job_id]["current_step"] = f"❌ {type(exc).__name__}: {str(exc)[:60]}"
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
    Legacy helper — kept for backward compatibility but no longer relied on
    for agent creation (provider is now passed explicitly to avoid cross-thread
    env-var contamination when multiple batch jobs run in parallel).
    """
    # Only set AZURE_OPENAI_DEPLOYMENT_NAME which is still read from env by
    # the Azure config path; skip MODEL_PROVIDER to avoid thread races.
    if provider == "azure":
        os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = model


# ---------------------------------------------------------------------------
# Public: run multiple jobs in parallel
# ---------------------------------------------------------------------------

def run_batch_parallel(
    specs: list[BatchJobSpec],
    output_base: Path | None = None,
    max_workers: int | None = None,
    status_dict: dict | None = None,
) -> tuple[list[BatchJobResult], dict]:
    """
    Run all specs in parallel using a ThreadPoolExecutor.

    Parameters
    ----------
    status_dict : optional pre-created dict keyed by job_id.
                  If provided the caller can poll it for live progress while
                  the jobs run in the background thread.

    Returns
    -------
    results : list[BatchJobResult]  (one per spec, in completion order)
    status  : the populated status dict (same object as status_dict if given)
    """
    import threading

    if output_base is None:
        output_base = Path("books") / "batch"

    if status_dict is not None:
        # Caller supplied the dict; ensure required keys exist
        for s in specs:
            status_dict.setdefault(
                s.job_id,
                {"state": "pending", "log": [], "current_step": "⏳ Waiting…"},
            )
        status = status_dict
    else:
        status: dict = {
            s.job_id: {"state": "pending", "log": [], "current_step": "⏳ Waiting…"}
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

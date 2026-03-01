#!/usr/bin/env python3
"""
Integration test — Math Exercises Book (Low Budget)
====================================================
Generates a complete math exercises book for children using:
  • GitHub Models (gpt-4o-mini)  → free tier, no spend
  • "math" HTML template         → KaTeX rendering, exercise grids, formula boxes
  • DuckDuckGo image search       → low-budget, royalty-free images (no AI generation)
  • "low_budget" palette          → B&W printable, printer-friendly

Run from the repo root:
    python tests/test_math_book.py

Output lands in:  books/test_math_book/<timestamp>/
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("math_book_test")

# ── Config ─────────────────────────────────────────────────────────────────
BOOK_CONFIG = dict(
    topic            = "Matemáticas: Operaciones Básicas, Fracciones y Geometría",
    target_audience_age = 10,
    language         = "Spanish",
    country          = "Mexico",
    learning_method  = "Project-Based Learning",
    num_chapters     = 6,
    pages_per_chapter= 8,
    genre            = "educational",
)

# Provider: force Qwen/DashScope (the DASHSCOPE_API_KEY is present in .env).
# Override USE_QWEN env var so .env defaults don't interfere with this test.
os.environ["USE_QWEN"] = "true"
USE_QWEN  = True
MODEL_ID  = os.getenv("MODEL_ID") or "qwen-plus"

TEMPLATE_ID = "math"       # math template → KaTeX, exercise grid, formula boxes
PALETTE_ID  = ""           # math template uses its own B&W palette

# Images: DuckDuckGo search (low budget) — no Qwen image API calls
IMAGES_PER_CHAPTER = 1     # 1 image per chapter via DDG
DDG_FALLBACK        = True  # always prefer DDG over AI generation

TIMESTAMP  = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_DIR    = ROOT / f"books/test_math_book/{TIMESTAMP}"
OUT_HTML   = OUT_DIR / "math_book.html"
OUT_JSON   = OUT_DIR / "book_output.json"
IMAGES_DIR = OUT_DIR / "images"


# ═══════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _chapter_context(req) -> dict:
    return {
        "age":             req.target_audience_age,
        "country":         req.country,
        "learning_method": req.learning_method,
        "language":        req.language,
        "pages_per_chapter": req.pages_per_chapter,
    }


async def _search_image_for_chapter(chapter_title: str, topic: str, language: str, country: str) -> str | None:
    """Download one DDG image for a chapter. Returns local file path or None."""
    try:
        from agents.ddg_image_search_agent import search_and_download_image
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = "".join(c for c in chapter_title[:40] if c.isalnum() or c in " -_").strip()
        result = await search_and_download_image(
            query=chapter_title,
            output_dir=str(IMAGES_DIR),
            chapter_name=safe_name,
            language=language,
            country=country,
            topic=topic,
        )
        if result and result.url:
            log.info(f"  🖼  Image saved → {result.url}")
            return result.url
    except Exception as exc:
        log.warning(f"  ⚠️  DDG image failed for '{chapter_title}': {exc}")
    return None


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN GENERATION PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

async def generate_math_book():
    log.info("=" * 60)
    log.info("📐 MATH EXERCISES BOOK — TEST RUN")
    log.info(f"   Topic   : {BOOK_CONFIG['topic']}")
    log.info(f"   Age     : {BOOK_CONFIG['target_audience_age']} years")
    log.info(f"   Country : {BOOK_CONFIG['country']}")
    log.info(f"   Provider: {'Qwen' if USE_QWEN else 'GitHub Models'} / {MODEL_ID}")
    log.info(f"   Template: {TEMPLATE_ID}  (KaTeX + exercise grids)")
    log.info(f"   Images  : DuckDuckGo (low budget, no AI generation)")
    log.info(f"   Output  : {OUT_DIR}")
    log.info("=" * 60)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Imports ──────────────────────────────────────────────────────────
    from models.book_spec import BookRequest, BookOutput
    from agents.curriculum_agent import create_curriculum_agent, generate_curriculum
    from agents.chapter_agent import create_chapter_agent, generate_chapter
    from agents.html_css_agent import generate_html_css_book_from_json
    from agents.markdown_agent import save_markdown_book

    # ── Book request ─────────────────────────────────────────────────────
    req = BookRequest(**BOOK_CONFIG)

    # ── 1. Curriculum ────────────────────────────────────────────────────
    log.info("\n📋 Step 1 — Generating curriculum …")
    curriculum_agent = await create_curriculum_agent(use_qwen=USE_QWEN, model_id=MODEL_ID)
    curriculum = await generate_curriculum(curriculum_agent, req, max_tokens=2000)
    if not curriculum:
        raise RuntimeError("❌ Curriculum generation failed — is your API key set?")
    log.info(f"✅ Curriculum: '{curriculum.title}' — {len(curriculum.chapters)} chapters")
    for i, ch in enumerate(curriculum.chapters, 1):
        log.info(f"   {i:2d}. {ch.title}")

    # ── 2. Chapters ──────────────────────────────────────────────────────
    log.info("\n📝 Step 2 — Writing chapters …")
    chapter_agent = await create_chapter_agent(use_qwen=USE_QWEN, model_id=MODEL_ID)
    ctx = _chapter_context(req)

    chapters = []
    for i, outline in enumerate(curriculum.chapters, 1):
        log.info(f"   ✍️  Chapter {i}/{len(curriculum.chapters)}: {outline.title}")
        ch = await generate_chapter(
            chapter_agent, outline, ctx,
            max_tokens=4000,
            images_per_chapter=0,   # images added by DDG below
        )
        if ch:
            chapters.append(ch)
        else:
            log.warning(f"   ⚠️  Chapter {i} returned empty — skipping")

    if not chapters:
        raise RuntimeError("❌ No chapters were generated")
    log.info(f"✅ {len(chapters)} chapters written")

    # ── 3. DDG Images (low budget) ───────────────────────────────────────
    log.info("\n🔍 Step 3 — Fetching DDG images (low budget) …")
    for ch in chapters:
        img_path = await _search_image_for_chapter(
            chapter_title=ch.chapter_title,
            topic=req.topic,
            language=req.language,
            country=req.country,
        )
        if img_path:
            # Inject image into chapter markdown so html_css_agent picks it up
            ch.markdown_content = f"![{ch.chapter_title}]({img_path})\n\n" + ch.markdown_content

    # ── 4. HTML export ───────────────────────────────────────────────────
    log.info("\n🎨 Step 4 — Building HTML book …")
    generate_html_css_book_from_json(
        book_request=req,
        curriculum=curriculum,
        chapters=chapters,
        output_html=str(OUT_HTML),
        template_id=TEMPLATE_ID,
        palette_id=PALETTE_ID,
    )
    log.info(f"✅ HTML saved → {OUT_HTML}")

    # ── 5. Markdown export ───────────────────────────────────────────────
    log.info("\n📄 Step 5 — Saving Markdown …")
    output = BookOutput(book_request=req, curriculum=curriculum, chapters=chapters)
    md_path = save_markdown_book(output, str(OUT_DIR / "math_book.md"))
    log.info(f"✅ Markdown saved → {md_path}")

    # ── 6. JSON snapshot ─────────────────────────────────────────────────
    log.info("\n💾 Step 6 — Saving JSON snapshot …")
    snapshot = {
        "book_request": req.model_dump(),
        "curriculum":   curriculum.model_dump(),
        "chapters":     [c.model_dump() for c in chapters],
        "meta": {
            "template":  TEMPLATE_ID,
            "provider":  "qwen" if USE_QWEN else "github",
            "model":     MODEL_ID,
            "images":    "ddg_low_budget",
            "generated": TIMESTAMP,
        },
    }
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, ensure_ascii=False, indent=2)
    log.info(f"✅ JSON saved → {OUT_JSON}")

    # ── Summary ──────────────────────────────────────────────────────────
    html_size_kb = OUT_HTML.stat().st_size // 1024
    total_words  = sum(len(c.markdown_content.split()) for c in chapters)
    imgs_found   = len(list(IMAGES_DIR.glob("*"))) if IMAGES_DIR.exists() else 0

    log.info("\n" + "=" * 60)
    log.info("🎉 MATH BOOK COMPLETE")
    log.info(f"   HTML  : {OUT_HTML.name}  ({html_size_kb} KB)")
    log.info(f"   Chaps : {len(chapters)} chapters  (~{total_words:,} words)")
    log.info(f"   Images: {imgs_found} DDG images (low budget)")
    log.info(f"   Folder: {OUT_DIR}")
    log.info("=" * 60)

    return OUT_HTML


# ═══════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Check for required API key
    if USE_QWEN and not os.getenv("DASHSCOPE_API_KEY"):
        log.error("❌ DASHSCOPE_API_KEY not set. Add it to your .env file.")
        sys.exit(1)
    if not USE_QWEN and not os.getenv("GITHUB_TOKEN"):
        log.error("❌ GITHUB_TOKEN not set. Add it to your .env file or set USE_QWEN=true.")
        sys.exit(1)

    try:
        html_path = asyncio.run(generate_math_book())
        print(f"\n✅ Done! Open the book: {html_path}")
    except KeyboardInterrupt:
        log.warning("Interrupted by user.")
        sys.exit(0)
    except Exception as exc:
        log.error(f"❌ Test failed: {exc}", exc_info=True)
        sys.exit(1)

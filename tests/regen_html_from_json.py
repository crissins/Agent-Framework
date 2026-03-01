#!/usr/bin/env python3
"""
Regenerate the HTML book from an existing book_output.json snapshot.
Useful for testing template/CSS/JS changes without re-calling the LLM.

Usage:
    python tests/regen_html_from_json.py [path/to/book_output.json] [--template TEMPLATE_ID]

    TEMPLATE_ID defaults to "educational" (master_book.html).
    Use "math" for the math exercises template.

If no JSON path is given, uses the most recent books/json run.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models.book_spec import BookRequest, Curriculum, ChapterContent
from agents.html_css_agent import generate_html_css_book_from_json

# ── Parse args ─────────────────────────────────────────────────────────────
_args = sys.argv[1:]
_template_override = None
if "--template" in _args:
    _idx = _args.index("--template")
    _template_override = _args[_idx + 1]
    _args = [a for i, a in enumerate(_args) if i not in (_idx, _idx + 1)]

# ── Find JSON ──────────────────────────────────────────────────────────────
if _args:
    json_path = Path(_args[0]).resolve()
else:
    # Default: most recent books/json run
    runs = sorted((ROOT / "books" / "json").glob("*/book_output.json"), reverse=True)
    if not runs:
        # Fallback to test_math_book
        runs = sorted((ROOT / "books" / "test_math_book").glob("*/book_output.json"), reverse=True)
    if not runs:
        print("❌ No book_output.json found. Run a book generation first.")
        sys.exit(1)
    json_path = runs[0]

print(f"📂 Loading: {json_path}")
data = json.loads(json_path.read_text(encoding="utf-8"))

# ── Reconstruct objects ────────────────────────────────────────────────────
req        = BookRequest(**data["book_request"])
curriculum = Curriculum(**data["curriculum"])
chapters   = [ChapterContent(**c) for c in data["chapters"]]
meta       = data.get("meta", {})

template_id = _template_override or meta.get("template") or "educational"
palette_id  = meta.get("palette_id", "")

out_html = ROOT / "books" / "html" / json_path.parent.name / "libro_interactivo_regen.html"

print(f"📐 Template : {template_id}")
print(f"🎨 Palette  : {palette_id or '(default)'}")
print(f"📑 Chapters : {len(chapters)}")
print(f"💾 Output   : {out_html}")

# ── Re-generate HTML ───────────────────────────────────────────────────────
generate_html_css_book_from_json(
    book_request=req,
    curriculum=curriculum,
    chapters=chapters,
    output_html=str(out_html),
    template_id=template_id,
    palette_id=palette_id,
)

size_kb = out_html.stat().st_size // 1024
print(f"\n✅ HTML regenerated → {out_html}  ({size_kb} KB)")
print(f"   Serve: python -m http.server 8091 --directory \"{out_html.parent}\"")
print(f"   Then open: http://localhost:8091/libro_interactivo_regen.html")

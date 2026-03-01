# agents/html_css_agent.py
"""
HTML book generator that fills the educational_book_template with live data.

Parses LLM-generated markdown chapters into typed blocks (concept, example,
activity, challenge, fact, question, image, divider) and serialises them
into a JS ``BOOK`` object that the self-contained HTML template renders.
"""
import base64
import json
import os
import re
from pathlib import Path
from typing import Dict, Any, List

from models.book_spec import BookRequest, Curriculum, ChapterContent, VideoPlaceholder
from models.i18n import get_i18n_strings, detect_lang_code, is_rtl
from models.template_registry import get_template

# ── Locate template ───────────────────────────────────────────────────────
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_TEMPLATE_NAME = "master_book.html"


# ═══════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════

def generate_html_css_book_from_json(
    book_request: BookRequest,
    curriculum: Curriculum,
    chapters: list[ChapterContent],
    output_html: str,
    template_id: str = "educational",
    palette_id: str = "",
):
    """Build a self-contained HTML book file from structured data."""

    template_path = _TEMPLATE_DIR / _TEMPLATE_NAME
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    template = template_path.read_text(encoding="utf-8")

    # Build the JS data object that the template's <script> section expects
    book_obj = _build_book_object(book_request, curriculum, chapters, template_id, palette_id)
    book_json = json.dumps(book_obj, ensure_ascii=False, indent=2)
    # Keep JSON safe inside <script> contexts
    book_json = (
        book_json
        .replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )

    # Replace the BOOK object in the template.
    # Match from 'var BOOK = {' to the closing '};' at column 0.
    html = re.sub(
        r'var BOOK\s*=\s*\{[\s\S]*?\n\};',
        lambda m: 'var BOOK = ' + book_json + ';',
        template,
        count=1,
    )

    # Inject theme CSS from the template registry
    tmpl = get_template(template_id)
    if tmpl.theme_css:
        html = html.replace('/* THEME_CSS_PLACEHOLDER */', tmpl.theme_css)

    # Set the <html lang="..."> and dir attribute
    lang_code = detect_lang_code(book_request.language)
    rtl = is_rtl(lang_code)
    if rtl:
        html = re.sub(r'<html lang="[^"]*"[^>]*>', f'<html lang="{lang_code}" dir="rtl">', html)
    else:
        html = re.sub(r'<html lang="[^"]*"[^>]*>', f'<html lang="{lang_code}" dir="ltr">', html)

    # Set <title>
    html = re.sub(
        r'<title>[^<]*</title>',
        f'<title>{_esc(curriculum.title)}</title>',
        html,
        count=1,
    )

    # Set palette + theme class on <body>
    palette = book_obj.get("palette", "pal-naranja")
    theme_class = book_obj.get("theme", {}).get("class", "")
    body_class = f"{palette} {theme_class}".strip()
    html = re.sub(
        r'<body class="[^"]*">',
        f'<body class="{body_class}">',
        html,
        count=1,
    )

    # Write the final file
    Path(output_html).parent.mkdir(parents=True, exist_ok=True)
    Path(output_html).write_text(html, encoding="utf-8")

    # Post-process: embed local images as base64
    _embed_images_as_base64(output_html)

    print(f"✅ HTML book saved as: {output_html} (template: {template_id}, images embedded)")


# ═══════════════════════════════════════════════════════════════════════════
#  DATA BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def _build_book_object(
    req: BookRequest,
    cur: Curriculum,
    chapters: List[ChapterContent],
    template_id: str = "educational",
    palette_id: str = "",
) -> dict:
    """Create the dict that becomes ``var BOOK = ...`` in the template."""

    toc = []
    ch_list = []

    for i, ch in enumerate(chapters):
        outline = cur.chapters[i] if i < len(cur.chapters) else None
        summary = outline.summary if outline else ""
        toc.append({"title": ch.chapter_title, "summary": summary})

        blocks = _parse_markdown_to_blocks(ch.markdown_content, ch)
        ch_list.append({"title": ch.chapter_title, "blocks": blocks})

    # Theme from template registry
    tmpl = get_template(template_id)

    # i18n strings for the book language
    lang_code = detect_lang_code(req.language)
    i18n_strings = get_i18n_strings(lang_code)

    # Non-educational templates MUST use their own palette (e.g. dark themes
    # need dark-palette text colours; pal-naranja text is invisible on #0A0608).
    # palette_id allows an explicit override for the educational template.
    if template_id != "educational":
        palette = tmpl.default_palette
    elif palette_id and palette_id != "auto" and palette_id.startswith("pal-"):
        palette = palette_id
    else:
        palette = _pick_palette(req.topic)

    return {
        "palette": palette,
        "theme": {
            "id": tmpl.id,
            "class": f"theme-{tmpl.id}" if tmpl.id != "educational" else "",
            "ornament": tmpl.corner_ornament,
            "darkMode": tmpl.dark_mode,
            "fontDisplay": tmpl.font_display,
            "fontBody": tmpl.font_body,
        },
        "i18n": i18n_strings,
        "request": {
            "topic": req.topic,
            "age": req.target_audience_age,
            "language": req.language,
            "country": req.country,
            "method": req.learning_method,
            "chapters": req.num_chapters,
        },
        "title": cur.title,
        "description": cur.description,
        "toc": toc,
        "chapters": ch_list,
    }


def _pick_palette(topic: str) -> str:
    """Choose a palette class based on topic keywords."""
    t = (topic or "").lower()
    if any(kw in t for kw in ("ciencia", "biolog", "quim", "fisic", "science")):
        return "pal-olivo"
    if any(kw in t for kw in ("matem", "algebra", "geometr", "math")):
        return "pal-azul"
    if any(kw in t for kw in ("histor", "social", "history")):
        return "pal-rojo"
    if any(kw in t for kw in ("arte", "music", "dibujo", "art")):
        return "pal-rosa"
    if any(kw in t for kw in ("liter", "lectura", "escrit", "reading")):
        return "pal-azul"
    if any(kw in t for kw in ("geograf", "natur", "ambient", "geo")):
        return "pal-olivo"
    if any(kw in t for kw in ("tecnolog", "comput", "program", "ia ", "ai ", "tech")):
        return "pal-negro"
    return "pal-naranja"


# ═══════════════════════════════════════════════════════════════════════════
#  MARKDOWN → BLOCK PARSER
# ═══════════════════════════════════════════════════════════════════════════

# Map section heading keywords → block type
_HEADING_MAP = {
    "concepto clave":       "concept",
    "key concept":          "concept",
    "ejemplo":              "example",
    "example":              "example",
    "actividad":            "activity",
    "activity":             "activity",
    "desafío creativo":     "challenge",
    "desafio creativo":     "challenge",
    "creative challenge":   "challenge",
    "sabías que":           "fact",
    "sabias que":           "fact",
    "did you know":         "fact",
    "pregunta":             "question",
    "question":             "question",
    "mini experimento":     "activity",
    "mini experiment":      "activity",
    "debate":               "activity",
    "rincón del inventor":  "challenge",
    "rincon del inventor":  "challenge",
    "historia corta":       "example",
    "short story":          "example",
    "conexión":             "fact",
    "conexion":             "fact",
    "connection":           "fact",
}


def _classify_heading(heading: str) -> str:
    """Return the block type for a markdown ``##`` heading."""
    h = heading.strip().lower()
    # Remove leading emoji / markdown bold markers
    h = re.sub(r'^[*_#\s]+', '', h)
    h = re.sub(r'[*_]+$', '', h)
    # Remove emoji
    h = re.sub(r'[\U00010000-\U0010ffff]', '', h).strip()
    for keyword, btype in _HEADING_MAP.items():
        if keyword in h:
            return btype
    return "concept"  # safe default


# Regex that matches either a markdown heading (#..######) or a standalone
# **bold** heading line.
# Group 1 = markdown heading text, Group 2 = **bold** heading text.
_SECTION_BOUNDARY = re.compile(
    r'^[ \t]*(?:#{1,6}\s+(.+)|\*\*([^*\n]{2,80})\*\*)[ \t]*$',
    re.MULTILINE,
)


def _extract_video(body: str, gen_vids: list, vid_idx: int) -> tuple:
    """Return (video_text, video_placeholder, new_vid_idx) for a block body."""
    _CLAPBOARD = '\U0001F3AC'
    _vid_patterns = [
        r'\[VIDEO:\s*([^\]]+)\]',
        _CLAPBOARD + r'\s*\**\s*[Vv]ideo[:\s]+\**([^*\n\]]+)',
    ]
    vid_match = None
    for _p in _vid_patterns:
        vid_match = re.search(_p, body)
        if vid_match:
            break

    vid_link_m = re.search(
        _CLAPBOARD + r'[^\[]*\[([^\]]+)\]\((https?://[^)]+)\)', body
    )

    video_text = ""
    video_placeholder = None

    if vid_match:
        vid_label = vid_match.group(1).strip()
        if vid_idx < len(gen_vids):
            video_placeholder = gen_vids[vid_idx]
            video_text = video_placeholder.title or vid_label
            vid_idx += 1
        elif vid_link_m:
            from agents.qr_agent import generate_qr_code as _gen_qr
            _url = vid_link_m.group(2).strip()
            video_text = vid_link_m.group(1).strip()
            video_placeholder = VideoPlaceholder(
                query=vid_label, title=video_text, url=_url,
                qr_code=_gen_qr(_url),
            )
        else:
            video_text = vid_label
    elif vid_link_m:
        _url = vid_link_m.group(2).strip()
        _title = vid_link_m.group(1).strip()
        if vid_idx < len(gen_vids):
            video_placeholder = gen_vids[vid_idx]
            video_text = video_placeholder.title or _title
            vid_idx += 1
        else:
            from agents.qr_agent import generate_qr_code as _gen_qr
            video_placeholder = VideoPlaceholder(
                query=_title, title=_title, url=_url,
                qr_code=_gen_qr(_url),
            )
            video_text = _title

    return video_text, video_placeholder, vid_idx


def _parse_markdown_to_blocks(md: str, chapter: ChapterContent) -> List[dict]:
    """
    Split LLM-generated markdown into the typed block objects that the
    HTML template's ``renderBlock()`` function understands.

    Recognises:
    * ``## Section name`` headings → ``heading`` block if no keyword match,
      otherwise the matching typed block
    * ``**Bold heading**`` standalone lines → typed blocks (concept/example/…)
    * ``[IMAGE: description]`` → image blocks
    * ``[VIDEO: description]`` / 🎬 markers → video pill inside parent block
    * Inline images ``![alt](path)`` → image blocks
    """
    blocks: List[dict] = []
    # NOTE: Do NOT use gen_imgs here. Images have already been embedded
    # into the markdown as ![alt](path) by _embed_images_in_markdown() in
    # app.py. Re-using gen_imgs would create DUPLICATE image blocks.
    gen_imgs: list = []  # intentionally empty — images are already in markdown
    img_idx = 0
    gen_vids = list(chapter.videos) if chapter.videos else []
    vid_idx = 0

    # Collect all section boundaries (markdown and **bold** headings) with positions
    boundaries = []
    for m in _SECTION_BOUNDARY.finditer(md):
        h2_text   = (m.group(1) or "").strip()   # #..###### heading text
        bold_text = (m.group(2) or "").strip()   # **bold** heading text
        heading   = h2_text or bold_text
        if heading:
            boundaries.append((m.start(), m.end(), heading, bool(h2_text)))

    # Text before the first boundary
    first_start = boundaries[0][0] if boundaries else len(md)
    intro = md[:first_start].strip()
    if intro:
        blocks, img_idx = _extract_inline_images(intro, blocks, gen_imgs, img_idx)
        text = _strip_images_and_videos(intro)
        text_plain = _md_to_plain(text).strip()
        # Drop intro lines that are just a restatement of the chapter title
        # (LLMs often open with the title as plain text or a lone # heading)
        _ch_title_norm = re.sub(r'[^\w\s]', '', chapter.chapter_title.lower()).strip()
        _intro_norm    = re.sub(r'[^\w\s]', '', text_plain.lower()).strip()
        _is_intro_title = (
            _intro_norm == _ch_title_norm
            or _ch_title_norm in _intro_norm
            or re.sub(r'^cap[íi]tulo\s+\d+\s*[:\-]\s*', '', _intro_norm) == _ch_title_norm
        )
        if text_plain and not _is_intro_title:
            blocks.append({"type": "concept", "label": "", "text": text_plain})

    for b_idx, (start, end, heading, is_h2) in enumerate(boundaries):
        next_start = boundaries[b_idx + 1][0] if b_idx + 1 < len(boundaries) else len(md)
        body = md[end:next_start]

        btype = _classify_heading(heading)
        label = _clean_heading(heading)

        # Markdown heading with no matching keyword → might be the chapter title or a sub-section
        has_keyword = any(kw in heading.lower() for kw in _HEADING_MAP)

        # Detect whether this heading is simply repeating the chapter title.
        # LLMs often emit "Capítulo N: <title>" or "**<title>**" at the top
        # of the chapter body — both must be suppressed so the template's
        # ch-h2 doesn't render the title a second time.
        def _is_title_repeat(h: str, ct: str) -> bool:
            h_n = re.sub(r'^cap[íi]tulo\s+\d+\s*[:\-]\s*', '',
                         re.sub(r'^chapter\s+\d+\s*[:\-]\s*', '',
                                h.strip().lower()))
            ct_n = ct.strip().lower()
            return h_n == ct_n or ct_n in h_n

        is_title_repeat = (
            not has_keyword
            and _is_title_repeat(heading, chapter.chapter_title)
        )

        if is_h2 and not has_keyword:
            if not is_title_repeat:
                blocks.append({"type": "heading", "text": label})

            # IMPORTANT: still process the body text under this heading
            # (intro paragraphs, images, videos) — don't skip it
            # Only create image blocks for [IMAGE:] placeholders that have a real URL;
            # leftover placeholders without images are silently dropped.
            blocks, img_idx = _extract_inline_images(body, blocks, gen_imgs, img_idx)
            video_text, video_placeholder, vid_idx = _extract_video(body, gen_vids, vid_idx)
            text = _md_to_plain(_strip_images_and_videos(body)).strip()
            if text:
                block: dict = {"type": "concept", "label": "", "text": text}
                if video_text:
                    block["video"] = video_text
                if video_placeholder and video_placeholder.qr_code:
                    block["video_qr"] = video_placeholder.qr_code
                    block["video_url"] = video_placeholder.url
                blocks.append(block)
            continue

        # Bold **heading** lines that repeat the chapter title → skip heading,
        # but still process the body content beneath them.
        if is_title_repeat and not is_h2:
            blocks, img_idx = _extract_inline_images(body, blocks, gen_imgs, img_idx)
            video_text, video_placeholder, vid_idx = _extract_video(body, gen_vids, vid_idx)
            text = _md_to_plain(_strip_images_and_videos(body)).strip()
            if text:
                block: dict = {"type": "concept", "label": "", "text": text}
                if video_text:
                    block["video"] = video_text
                if video_placeholder and video_placeholder.qr_code:
                    block["video_qr"] = video_placeholder.qr_code
                    block["video_url"] = video_placeholder.url
                blocks.append(block)
            continue

        # Extract inline markdown images (![alt](url)) — [IMAGE:] placeholders
        # without real URLs are intentionally skipped to avoid empty placeholders.
        blocks, img_idx = _extract_inline_images(body, blocks, gen_imgs, img_idx)

        # Extract video reference
        video_text, video_placeholder, vid_idx = _extract_video(body, gen_vids, vid_idx)

        # Plain text for the block body
        text = _md_to_plain(_strip_images_and_videos(body)).strip()

        if not text and not video_text:
            continue

        block: dict = {"type": btype, "label": label, "text": text}
        if video_text:
            block["video"] = video_text
        if video_placeholder and video_placeholder.qr_code:
            block["video_qr"]  = video_placeholder.qr_code
            block["video_url"] = video_placeholder.url
        blocks.append(block)

    # Fallback: whole content as one concept block
    if not blocks:
        blocks.append({"type": "concept", "label": "", "text": _md_to_plain(md)})

    return blocks


# ═══════════════════════════════════════════════════════════════════════════
#  TEXT HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _extract_inline_images(text: str, blocks: list, gen_imgs: list, img_idx: int):
    """Pull ``![alt](src)`` out of *text* and append image blocks.

    Only creates image blocks for images that have a real URL.
    Skips data: URIs (e.g. QR code PNGs embedded by app.py).
    Callout-style image descriptions (> 🖼️ *Illustration: desc*) are
    intentionally IGNORED — they are leftover placeholders with no actual
    image and should not appear in the HTML.
    """
    for m in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', text):
        alt, src = m.group(1), m.group(2)
        if src.startswith('data:'):
            continue  # skip embedded data-URI images (QR codes etc.)
        blocks.append({"type": "image", "alt": alt or "Illustration", "url": src})

    # NOTE: Callout-style image descriptions (> 🖼️ *Illustration: desc*)
    # are NOT extracted. These are leftover [IMAGE:] placeholders that had
    # no actual generated image. Showing them as empty placeholders in the
    # HTML is undesirable — they are silently skipped.

    return blocks, img_idx


def _strip_images_and_videos(text: str) -> str:
    """Remove image/video markdown markers from text."""
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    text = re.sub(r'\[IMAGE:\s*[^\]]+\]', '', text)
    text = re.sub(r'\[VIDEO:\s*[^\]]+\]', '', text)
    # Strip converted callouts produced by _embed_images_in_markdown:
    #   > 🖼️ *Illustration: desc*
    #   > 🎬 *Video: desc*
    text = re.sub(r'>\s*\U0001F5BC\uFE0F?\s*\*?Illustration:[^\n]*\n?', '', text)
    # Strip converted video markers (> 🎬 *Video: desc* from _embed_images_in_markdown)
    # and appended video links (🎬 **Video recomendado:** from app.py)
    text = re.sub('>?\\s*\U0001F3AC[^\n]+\n?', '', text)
    # Strip standalone --- dividers added by app.py before video recommendations
    text = re.sub(r'^\s*---\s*$', '', text, flags=re.MULTILINE)
    return text


def _md_to_plain(md: str) -> str:
    """Lightweight markdown-to-plaintext for block content.

    LaTeX expressions ($$...$$, $...$) are preserved intact so they can be
    rendered by KaTeX in the HTML template.
    """
    t = md.strip()

    # ── Protect LaTeX before stripping markdown ───────────────────────────
    # Stash $$ display and $ inline math so italic/bold regexes can't mangle
    # subscripts, superscripts, or multiply signs inside them.
    _math_store: list = []

    def _save(m: re.Match) -> str:  # type: ignore[type-arg]
        idx = len(_math_store)
        _math_store.append(m.group(0))
        return f'\x00M{idx}\x00'

    t = re.sub(r'\$\$[\s\S]+?\$\$', _save, t)   # display math first
    t = re.sub(r'\$[^$\n]+?\$', _save, t)         # then inline math

    # Remove markdown headings (keep heading text)
    t = re.sub(r'^\s*#{1,6}\s+', '', t, flags=re.MULTILINE)
    # Remove bold/italic markers
    t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)
    t = re.sub(r'\*(.+?)\*', r'\1', t)
    t = re.sub(r'__(.+?)__', r'\1', t)
    t = re.sub(r'_(.+?)_', r'\1', t)
    # Collapse newlines
    t = re.sub(r'\n{3,}', '\n\n', t)
    # Remove list markers at beginning of lines (keep text)
    t = re.sub(r'^[\-\*]\s+', '• ', t, flags=re.MULTILINE)
    t = re.sub(r'^\d+\.\s+', '• ', t, flags=re.MULTILINE)

    # ── Restore LaTeX ─────────────────────────────────────────────────────
    for i, expr in enumerate(_math_store):
        t = t.replace(f'\x00M{i}\x00', expr)

    return t.strip()


def _clean_heading(h: str) -> str:
    """Clean a markdown heading for use as a block label."""
    h = re.sub(r'^[*_]+|[*_]+$', '', h.strip())
    h = re.sub(r'[\U00010000-\U0010ffff]', '', h).strip()
    return h


def _esc(s: str) -> str:
    """HTML-escape a string."""
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ═══════════════════════════════════════════════════════════════════════════
#  IMAGE EMBEDDING  (same post-process as before)
# ═══════════════════════════════════════════════════════════════════════════

def _embed_images_as_base64(html_path: str):
    """Post-process: embed every local ``<img src="...">`` as base64."""
    path = Path(html_path)
    if not path.exists():
        return
    content = path.read_text(encoding="utf-8")
    base_dir = path.parent

    def _replace_src(match):
        prefix, src, suffix = match.group(1), match.group(2), match.group(3)
        if src.startswith(("http://", "https://", "data:")):
            return match.group(0)
        img_path = (base_dir / src).resolve()
        if not img_path.exists():
            return match.group(0)
        ext = img_path.suffix.lower().lstrip(".")
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "gif": "image/gif", "webp": "image/webp"}.get(ext, "image/png")
        try:
            data = base64.b64encode(img_path.read_bytes()).decode("ascii")
            return f'{prefix}data:{mime};base64,{data}{suffix}'
        except Exception:
            return match.group(0)

    content = re.sub(r'(<img[^>]*\bsrc=")([^"]+)(")', _replace_src, content)
    # Also handle URLs inside the JS BOOK JSON (image blocks with local paths)
    # The template embeds images via JS so we also rewrite paths inside the JSON
    def _replace_json_url(m):
        url = m.group(1)
        if url.startswith(("http://", "https://", "data:")):
            return m.group(0)
        img_path = (base_dir / url).resolve()
        if not img_path.exists():
            return m.group(0)
        ext = img_path.suffix.lower().lstrip(".")
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "gif": "image/gif", "webp": "image/webp"}.get(ext, "image/png")
        try:
            data = base64.b64encode(img_path.read_bytes()).decode("ascii")
            return f'"url": "data:{mime};base64,{data}"'
        except Exception:
            return m.group(0)

    content = re.sub(r'"url":\s*"([^"]+)"', _replace_json_url, content)

    path.write_text(content, encoding="utf-8")
    print(f"  📎 Images embedded as base64 in HTML")
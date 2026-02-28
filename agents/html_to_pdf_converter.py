"""
Convert book data to PDF using fpdf2 (pure Python, no native dependencies).

Renders chapters with:
- Unicode support (system fonts on Windows, DejaVu on Linux)
- Embedded chapter images
- Clean white-background styling matching the HTML output
- Proper text wrapping and pagination
"""
import os
import re
import sys
import markdown as md_lib
from pathlib import Path
from typing import List, Optional

from fpdf import FPDF

from models.book_spec import BookRequest, Curriculum, ChapterContent


# ── Colours (clean white theme matching the HTML output) ────────────
_BG    = (255, 255, 255)   # white background
_CARD  = (248, 249, 250)   # --surface (light grey)
_TEXT  = (26, 32, 44)      # --text (near-black)
_TEXT2 = (74, 85, 104)     # --text-secondary
_GREEN = (0, 99, 65)       # --accent (mx-green)
_RED   = (206, 17, 38)     # --accent-red (mx-red)
_MUTED = (113, 128, 150)   # --text-muted
_BORDER = (226, 232, 240)  # --border


# ── Unicode helpers ───────────────────────────────────────────────────────────

def _sanitize_for_latin1(text: str) -> str:
    """Replace common Unicode characters with Latin-1 safe equivalents."""
    _MAP = {
        '\u2014': '--',   # \u2014 em dash
        '\u2013': '-',    # \u2013 en dash
        '\u2018': "'",    # left single quote
        '\u2019': "'",    # right single quote
        '\u201c': '"',    # left double quote
        '\u201d': '"',    # right double quote
        '\u2026': '...',  # ellipsis
        '\u2022': '*',    # bullet
        '\u2192': '->',   # arrow right
        '\u2190': '<-',   # arrow left
    }
    for old, new in _MAP.items():
        text = text.replace(old, new)
    return text.encode('latin-1', errors='replace').decode('latin-1')


def _load_unicode_font(pdf: FPDF) -> str:
    """Load a Unicode-capable TTF font. Returns the font family name."""
    # 1. Windows system fonts
    if sys.platform == "win32":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        fdir = Path(windir) / "Fonts"
        for family, reg, bold, italic in [
            ("Segoe", "segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf"),
            ("Calibri", "calibri.ttf", "calibrib.ttf", "calibrii.ttf"),
            ("ArialUni", "arial.ttf", "arialbd.ttf", "ariali.ttf"),
        ]:
            if (fdir / reg).exists():
                try:
                    pdf.add_font(family, "", str(fdir / reg))
                    b, i = fdir / bold, fdir / italic
                    pdf.add_font(family, "B", str(b) if b.exists() else str(fdir / reg))
                    pdf.add_font(family, "I", str(i) if i.exists() else str(fdir / reg))
                    print(f"  \U0001f4dd PDF font: {family}")
                    return family
                except Exception:
                    continue

    # 2. Common Linux / macOS font paths
    for dpath in ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/TTF"]:
        d = Path(dpath)
        if (d / "DejaVuSans.ttf").exists():
            try:
                pdf.add_font("DejaVu", "", str(d / "DejaVuSans.ttf"))
                pdf.add_font("DejaVu", "B", str(d / "DejaVuSans-Bold.ttf"))
                pdf.add_font("DejaVu", "I", str(d / "DejaVuSans-Oblique.ttf"))
                print("  \U0001f4dd PDF font: DejaVu")
                return "DejaVu"
            except Exception:
                continue

    # 3. Legacy fpdf2 bundled DejaVu
    try:
        pdf.add_font("DejaVu", "", "DejaVuSans.ttf")
        pdf.add_font("DejaVu", "B", "DejaVuSans-Bold.ttf")
        pdf.add_font("DejaVu", "I", "DejaVuSans-Oblique.ttf")
        return "DejaVu"
    except Exception:
        pass

    print("  \u26a0\ufe0f No Unicode font found \u2013 using Helvetica (limited charset)")
    return "Helvetica"


class _BookPDF(FPDF):
    """Subclass with dark background, header/footer, and Unicode-safe text."""

    def __init__(self, title: str = "", **kwargs):
        super().__init__(**kwargs)
        self._book_title = title
        self._ff = "Helvetica"
        self._unicode = False

    def configure_font(self, family: str):
        """Set the primary font family after loading."""
        self._ff = family
        self._unicode = family != "Helvetica"

    # White background on every page
    def header(self):
        self.set_fill_color(*_BG)
        self.rect(0, 0, self.w, self.h, style="F")

    def footer(self):
        self.set_y(-15)
        self.set_font(self._ff, "I", 8)
        self.set_text_color(*_MUTED)
        self.cell(0, 10, f"{self._book_title}  -  Page {self.page_no()}/{{nb}}", align="C")

    def multi_cell(self, w=0, h=None, text="", **kwargs):
        """Default new_x to LMARGIN so consecutive multi_cell(0,...) calls
        don't leave the cursor at the right margin (fpdf2 default is RIGHT)."""
        kwargs.setdefault("new_x", "LMARGIN")
        kwargs.setdefault("new_y", "NEXT")
        return super().multi_cell(w, h, text, **kwargs)

    def normalize_text(self, text):
        """Sanitize non-Latin-1 chars when using core fonts."""
        if not self._unicode:
            text = _sanitize_for_latin1(text)
        return super().normalize_text(text)


def convert_html_to_pdf(html_path: str, output_pdf_path: str) -> bool:
    """Legacy entry-point kept for backward compatibility.

    Reads the sibling JSON to get structured data, or falls back to
    a simple HTML-strip approach.
    """
    html_file = Path(html_path)
    if not html_file.exists():
        print(f"❌ HTML file not found: {html_path}")
        return False

    try:
        # Try to find corresponding JSON to get structured data
        timestamp_dir = html_file.parent.name          # e.g. 20260220_235808
        json_path = html_file.parent.parent.parent / "json" / timestamp_dir / "book_output.json"

        if json_path.exists():
            import json
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            request = BookRequest(**data["book_request"])
            curriculum = Curriculum(**data["curriculum"])
            chapters = [ChapterContent(**c) for c in data["chapters"]]

            return generate_pdf_from_data(
                request, curriculum, chapters,
                output_pdf_path,
                images_base=html_file.parent  # resolve relative imgs from HTML dir
            )

        # Fallback: simple HTML text extraction
        print("⚠️  JSON not found – generating minimal PDF from HTML text")
        return _simple_html_to_pdf(html_file, output_pdf_path)

    except Exception as e:
        print(f"❌ Error converting to PDF: {e}")
        import traceback
        traceback.print_exc()
        return False


# ── Main public API ─────────────────────────────────────────────────

def generate_pdf_from_data(
    request: BookRequest,
    curriculum: Curriculum,
    chapters: List[ChapterContent],
    output_pdf_path: str,
    images_base: Optional[Path] = None,
) -> bool:
    """Build a styled PDF directly from structured book data.

    Args:
        request: Book metadata (language, country, age …)
        curriculum: Title + description + chapter outlines
        chapters: Full chapter content with markdown and images
        output_pdf_path: Destination path for the PDF
        images_base: Directory used to resolve relative image paths.
                     Falls back to the parent of ``output_pdf_path``.

    Returns:
        True on success, False otherwise.
    """
    if images_base is None:
        images_base = Path(output_pdf_path).parent

    try:
        print(f"\n{'='*80}")
        print(f"📄 Generating PDF: {Path(output_pdf_path).name}")
        print(f"{'='*80}")

        pdf = _BookPDF(title=curriculum.title, orientation="P", unit="mm", format="A4")
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=20)

        # ── Load Unicode font ──────────────────────────────────────────────────
        _FONT = _load_unicode_font(pdf)
        pdf.configure_font(_FONT)

        # ── Title Page ──────────────────────────────────────────────
        pdf.add_page()
        pdf.ln(50)
        pdf.set_font(_FONT, "B", 28)
        pdf.set_text_color(*_TEXT)
        pdf.multi_cell(0, 14, curriculum.title, align="C")
        pdf.ln(8)
        pdf.set_font(_FONT, "", 13)
        pdf.set_text_color(*_TEXT2)
        pdf.multi_cell(0, 7, curriculum.description, align="C")
        pdf.ln(10)
        pdf.set_font(_FONT, "", 10)
        pdf.set_text_color(*_MUTED)
        meta = (
            f"{request.num_chapters} chapters  |  "
            f"Audience: {request.target_audience_age} years  |  "
            f"{request.country}  |  {request.language}"
        )
        pdf.multi_cell(0, 6, meta, align="C")

        # ── Chapters ────────────────────────────────────────────────
        for i, ch in enumerate(chapters, 1):
            pdf.add_page()

            # Chapter heading with green accent bar
            _draw_accent_bar(pdf, _GREEN)
            pdf.set_font(_FONT, "B", 20)
            pdf.set_text_color(*_TEXT)
            pdf.cell(0, 12, f"Chapter {i}: {ch.chapter_title}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)

            # Render chapter body
            _render_markdown_content(pdf, ch.markdown_content, _FONT, images_base)

        # ── Write PDF ───────────────────────────────────────────────
        pdf.output(output_pdf_path)
        print(f"✅ PDF generated successfully: {output_pdf_path}\n")
        return True

    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return False


# ── Helpers ─────────────────────────────────────────────────────────

def _draw_accent_bar(pdf: FPDF, color: tuple, width: int = 4):
    """Draw a small vertical accent bar to the left of the current position."""
    x, y = pdf.get_x(), pdf.get_y()
    pdf.set_fill_color(*color)
    pdf.rect(x - 2, y, width, 12, style="F")


def _place_image(pdf: FPDF, img_path: Path, max_height_ratio: float = 0.40):
    """Place an image in the PDF with layout adapted to its aspect ratio.

    Layout strategy based on the image dimensions:
    - **Landscape (aspect > 1.2)**: Full-width, centred horizontally.
    - **Square-ish (0.8 ≤ aspect ≤ 1.2)**: Centred at 60 % of page width.
    - **Portrait (aspect < 0.8)**: Right-aligned at 45 % of page width
      so body text can flow beside it on subsequent calls.

    In every case the image height is capped at *max_height_ratio* of the
    usable page height.  If it won't fit on the current page a new page
    is added first.
    """
    usable_w = pdf.w - pdf.l_margin - pdf.r_margin
    usable_h = pdf.h - pdf.t_margin - pdf.b_margin
    max_img_h = usable_h * max_height_ratio

    # Get real pixel dimensions to compute aspect ratio
    try:
        from PIL import Image as PILImage
        with PILImage.open(str(img_path)) as im:
            px_w, px_h = im.size
    except Exception:
        px_w, px_h = 16, 9  # fallback: assume 16:9

    aspect = px_w / max(px_h, 1)

    # ── Decide layout ────────────────────────────────────────────────
    if aspect > 1.2:
        # Landscape → full usable width
        img_w = usable_w
        img_h = img_w / aspect
        if img_h > max_img_h:
            img_h = max_img_h
            img_w = img_h * aspect
        x_offset = pdf.l_margin + (usable_w - img_w) / 2
    elif aspect < 0.8:
        # Portrait → right-aligned, max 45 % of page width
        img_w = usable_w * 0.45
        img_h = img_w / aspect
        if img_h > max_img_h:
            img_h = max_img_h
            img_w = img_h * aspect
        x_offset = pdf.w - pdf.r_margin - img_w  # right-align
    else:
        # Square-ish → centred at 60 % of page width
        img_w = usable_w * 0.60
        img_h = img_w / aspect
        if img_h > max_img_h:
            img_h = max_img_h
            img_w = img_h * aspect
        x_offset = pdf.l_margin + (usable_w - img_w) / 2

    # Check remaining space on current page
    remaining = usable_h - (pdf.get_y() - pdf.t_margin)
    if img_h + 8 > remaining:
        pdf.add_page()

    y_before = pdf.get_y()
    pdf.image(str(img_path), x=x_offset, y=y_before, w=img_w, h=img_h)
    pdf.set_y(y_before + img_h + 4)
    pdf.set_x(pdf.l_margin)


def _resolve_image_path(url_or_path: str, base: Path) -> Optional[Path]:
    """Try to turn an image reference into a real file path."""
    if not url_or_path or url_or_path.startswith("data:"):
        return None

    p = Path(url_or_path)

    # Absolute path
    if p.is_absolute() and p.exists():
        return p

    # Exists relative to CWD
    if p.exists():
        return p.resolve()

    # Relative to supplied base directory (handles ../.. via OS resolution)
    candidate = base / url_or_path
    if candidate.exists():
        return candidate.resolve()

    # Strip ../ prefixes and retry
    stripped = url_or_path.replace("\\", "/")
    while stripped.startswith("../"):
        stripped = stripped[3:]

    candidate = base / stripped
    if candidate.exists():
        return candidate.resolve()

    # Try from CWD with common prefixes
    for prefix in ["books/", ""]:
        candidate = Path(prefix + stripped)
        if candidate.exists():
            return candidate.resolve()

    return None


def _render_markdown_content(pdf: FPDF, markdown_text: str, font: str, images_base: Path):
    """Render markdown chapter content into the PDF.

    Walks through lines and renders headings, bold, images, and body text.
    """
    if not markdown_text:
        return

    # Clean up leftover media placeholders
    text = re.sub(r'\[IMAGE:\s*([^\]]+)\]', r'Illustration: \1', markdown_text)
    text = re.sub(r'\[VIDEO:\s*([^\]]+)\]', r'Video: \1', text)
    # Strip illustration callouts (> 🖼️ *Illustration: ...* ) — already shown as image blocks
    text = re.sub(r'>\s*\U0001F5BC\uFE0F?\s*\*?Illustration:[^\n]*', '', text)

    lines = text.split("\n")
    for line in lines:
        stripped = line.strip()
        if not stripped:
            pdf.ln(3)
            continue

        # ── data: URI images (QR codes encoded as base64 PNGs) ─────────
        data_img_match = re.match(r'^!\[([^\]]*)\]\((data:image/[^)]+)\)\s*$', stripped)
        if data_img_match:
            alt, data_uri = data_img_match.group(1), data_img_match.group(2)
            try:
                import base64 as _b64
                header, b64data = data_uri.split(',', 1)
                img_bytes = _b64.b64decode(b64data)
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    tmp.write(img_bytes)
                    tmp_path = tmp.name
                _place_image(pdf, Path(tmp_path), max_height_ratio=0.18)
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            except Exception:
                pass
            continue

        # Inline markdown image syntax: render in-place to preserve HTML-like flow
        img_match = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)\s*$', stripped)
        if img_match:
            _, src = img_match.group(1), img_match.group(2)
            img_path = _resolve_image_path(src, images_base)
            if img_path and img_path.exists():
                try:
                    _place_image(pdf, img_path)
                except Exception:
                    pass
            continue

        # Reset X to left margin on every line to avoid leftover X drift
        pdf.set_x(pdf.l_margin)

        # Heading detection
        if stripped.startswith("### "):
            pdf.ln(3)
            pdf.set_font(font, "B", 12)
            pdf.set_text_color(*_TEXT)
            heading = re.sub(r'\*\*(.+?)\*\*', r'\1', stripped[4:].strip())
            pdf.multi_cell(0, 7, heading)
            pdf.ln(1)
        elif stripped.startswith("## "):
            pdf.ln(4)
            _draw_accent_bar(pdf, _GREEN)
            pdf.set_font(font, "B", 14)
            pdf.set_text_color(*_TEXT)
            pdf.multi_cell(0, 8, stripped[3:].strip())
            pdf.ln(2)
        elif stripped.startswith("# "):
            pdf.ln(4)
            pdf.set_font(font, "B", 16)
            pdf.set_text_color(*_TEXT)
            pdf.multi_cell(0, 9, stripped[2:].strip())
            pdf.ln(2)
        elif stripped.startswith("**") and stripped.endswith("**"):
            # Bold section header
            pdf.set_font(font, "B", 11)
            pdf.set_text_color(*_TEXT)
            pdf.multi_cell(0, 6, stripped.strip("*").strip())
            pdf.ln(1)
        elif stripped.startswith("- ") or stripped.startswith("* "):
            pdf.set_font(font, "", 10)
            pdf.set_text_color(*_TEXT)
            bullet_text = stripped[2:].strip()
            clean = re.sub(r'\*\*(.+?)\*\*', r'\1', bullet_text)
            clean = re.sub(r'\*(.+?)\*', r'\1', clean)
            pdf.multi_cell(0, 6, f"    \u2022 {clean}")
        elif re.match(r'^\d+\.\s', stripped):
            # Numbered list
            pdf.set_font(font, "", 10)
            pdf.set_text_color(*_TEXT)
            clean = re.sub(r'\*\*(.+?)\*\*', r'\1', stripped)
            clean = re.sub(r'\*(.+?)\*', r'\1', clean)
            pdf.multi_cell(0, 6, f"  {clean}")
        elif stripped.startswith("---"):
            pdf.ln(4)
            y = pdf.get_y()
            pdf.set_draw_color(*_BORDER)
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.ln(4)
        elif stripped.startswith(">"):
            # Blockquote / callout
            pdf.set_font(font, "I", 10)
            pdf.set_text_color(*_MUTED)
            content = stripped.lstrip("> ").strip()
            pdf.multi_cell(0, 6, f"  {content}")
            pdf.ln(1)
        elif stripped.startswith("$$") or stripped.endswith("$$"):
            # LaTeX block — render as-is in italic
            pdf.set_font(font, "I", 10)
            pdf.set_text_color(*_MUTED)
            pdf.multi_cell(0, 6, stripped.strip("$").strip())
            pdf.ln(1)
        else:
            # Normal paragraph — handle inline bold **text** and markdown links
            pdf.set_font(font, "", 10)
            pdf.set_text_color(*_TEXT)
            clean = re.sub(r'\*\*(.+?)\*\*', r'\1', stripped)
            clean = re.sub(r'\*(.+?)\*', r'\1', clean)
            # Convert markdown links [text](url) → "text (url)"
            clean = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', clean)
            pdf.multi_cell(0, 6, clean)


def _simple_html_to_pdf(html_file: Path, output_pdf_path: str) -> bool:
    """Fallback: strip HTML tags and dump plain text into a PDF."""
    import re as _re
    html_text = html_file.read_text(encoding="utf-8")
    plain = _re.sub(r'<style[^>]*>.*?</style>', '', html_text, flags=_re.DOTALL)
    plain = _re.sub(r'<script[^>]*>.*?</script>', '', plain, flags=_re.DOTALL)
    plain = _re.sub(r'<[^>]+>', '\n', plain)
    plain = _re.sub(r'\n{3,}', '\n\n', plain).strip()

    pdf = _BookPDF(title="Book", orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    try:
        pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        _f = "DejaVu"
    except Exception:
        _f = _load_unicode_font(pdf)
    pdf.configure_font(_f)

    pdf.set_font(_f, "", 10)
    pdf.set_text_color(*_TEXT)
    pdf.multi_cell(0, 6, plain)
    pdf.output(output_pdf_path)
    print(f"✅ PDF generated (text-only fallback): {output_pdf_path}")
    return True


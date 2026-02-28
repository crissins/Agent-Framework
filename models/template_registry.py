# models/template_registry.py
"""
Template registry — defines themed visual presets for the book renderer.

Each template bundles:
* **CSS overrides** (fonts, colours, backgrounds, borders, ornaments)
* **Metadata** (id, name, description, preview emoji)
* **Theme config** consumed by the master template's JavaScript

The master HTML template injects `BOOK.theme` and a `<style>` block built
from `theme_css` so a single template file powers every visual style.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional


# ═══════════════════════════════════════════════════════════════════════════
#  TEMPLATE DATACLASS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class BookTemplate:
    """One themed visual preset."""

    id: str                         # e.g. "storybook"
    name: str                       # e.g. "Storybook"
    description: str                # Short UI description
    emoji: str                      # Quick preview icon
    category: str                   # "general" | "seasonal" | "genre"

    # CSS injected into the template <style> block
    theme_css: str = ""

    # JS theme config placed on BOOK.theme
    corner_ornament: str = "✦"     # Unicode char for page corner ornaments
    cover_badge_bg: str = ""        # Override cover badge background
    dark_mode: bool = False         # True → body/page backgrounds inverted

    # Font overrides (CSS values)
    font_display: str = ""          # Override --f-display
    font_body: str = ""             # Override --f-body

    # Default palette ID (must exist in template CSS)
    default_palette: str = "pal-naranja"

    # Extra decorative SVG for the cover (raw SVG string)
    cover_deco_svg: str = ""


# ═══════════════════════════════════════════════════════════════════════════
#  TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════

_TEMPLATES: Dict[str, BookTemplate] = {}


def _register(t: BookTemplate) -> BookTemplate:
    _TEMPLATES[t.id] = t
    return t


# ── 1. Educational (default — existing look) ─────────────────────────────
_register(BookTemplate(
    id="educational",
    name="Educational",
    description="Clean educational layout with double-border pages and ruled-paper texture",
    emoji="📚",
    category="general",
    corner_ornament="✦",
    default_palette="pal-naranja",
    theme_css="""\
/* Educational — base theme, no overrides needed */
""",
))


# ── 2. Storybook ─────────────────────────────────────────────────────────
_register(BookTemplate(
    id="storybook",
    name="Storybook",
    description="Whimsical fairy-tale style with rounded frames and playful ornaments",
    emoji="🧸",
    category="general",
    corner_ornament="★",
    font_display="'Georgia', 'Palatino Linotype', serif",
    default_palette="pal-rosa",
    theme_css="""\
/* Storybook theme */
.theme-storybook .page-frame {
  border-radius: 18px;
  border-width: 5px;
  border-style: dashed;
  background-image: radial-gradient(circle at 50% 50%, rgba(255,220,240,.15) 0%, transparent 70%);
}
.theme-storybook .inner-border {
  border-radius: 14px;
  border-style: dotted;
  border-width: 2px;
}
.theme-storybook .book-cover {
  border-radius: 8px 24px 24px 8px;
  background-image: linear-gradient(135deg, var(--p-primary), var(--p-secondary));
}
.theme-storybook .cover-title {
  font-style: italic;
}
.theme-storybook .blk-concept {
  border-radius: 16px;
  border-left-width: 6px;
}
.theme-storybook .blk-example {
  border-radius: 16px;
  border-left-width: 6px;
}
.theme-storybook .blk-activity {
  border-radius: 20px;
  border-width: 3px;
  border-style: dashed;
}
.theme-storybook .blk-challenge {
  border-radius: 20px;
}
.theme-storybook .blk-question {
  border-radius: 50px;
}
.theme-storybook .blk-fact {
  border-radius: 12px;
  border-top-style: dashed;
  border-bottom-style: dashed;
}
.theme-storybook .ch-h2 {
  border-left: 6px dotted var(--p-primary);
}
.theme-storybook .page-num {
  border-radius: 12px;
  transform: rotate(-3deg);
}
.theme-storybook .toc-num {
  color: var(--p-primary);
  font-style: italic;
}
""",
))


# ── 3. Botanical ──────────────────────────────────────────────────────────
_register(BookTemplate(
    id="botanical",
    name="Botanical",
    description="Elegant nature-inspired design with leaf motifs and muted earthy tones",
    emoji="🌿",
    category="general",
    corner_ornament="❧",
    font_display="Georgia, 'Palatino Linotype', 'Book Antiqua', serif",
    default_palette="pal-olivo",
    theme_css="""\
/* Botanical theme */
.theme-botanical .page-frame {
  border-style: double;
  border-width: 4px;
  background-image:
    radial-gradient(ellipse at 0% 100%, rgba(74,94,32,.06) 0%, transparent 50%),
    radial-gradient(ellipse at 100% 0%, rgba(74,94,32,.04) 0%, transparent 50%);
}
.theme-botanical .page-frame::before {
  background: repeating-linear-gradient(
    0deg,
    transparent, transparent 30px,
    rgba(74,94,32,.03) 30px, rgba(74,94,32,.03) 31px
  );
}
.theme-botanical .inner-border {
  border-style: double;
  border-width: 3px;
}
.theme-botanical .book-cover {
  background-image: linear-gradient(160deg, var(--p-primary) 0%, #2A3A10 100%);
}
.theme-botanical .cover-title {
  font-style: italic;
  letter-spacing: -.01em;
}
.theme-botanical .blk-concept {
  border-left: 5px double var(--p-primary);
  background: linear-gradient(90deg, var(--p-light) 0%, rgba(255,255,255,.4) 100%);
}
.theme-botanical .blk-challenge {
  background: linear-gradient(135deg, #2A3A10, var(--p-primary));
}
.theme-botanical .ch-eyebrow::after {
  background: var(--p-primary);
  width: 60px;
}
.theme-botanical .ch-h2 {
  border-left: 5px double var(--p-primary);
}
.theme-botanical .blk-fact {
  border-top: 3px double var(--p-accent2);
  border-bottom: 3px double var(--p-accent2);
}
.theme-botanical .page-num {
  border-radius: 4px;
}
""",
))


# ── 4. Horror ─────────────────────────────────────────────────────────────
_register(BookTemplate(
    id="horror",
    name="Horror",
    description="Dark and atmospheric with gothic elements and eerie decorations",
    emoji="🦇",
    category="genre",
    corner_ornament="☠",
    font_display="Georgia, 'Times New Roman', serif",
    dark_mode=True,
    default_palette="pal-halloween",
    theme_css="""\
/* Horror theme */
.theme-horror { background: #0A0608 !important; }
.theme-horror .page-frame {
  border-color: #4A0A1A;
  background: #120A0E;
  background-image:
    radial-gradient(ellipse at 30% 80%, rgba(100,0,30,.12) 0%, transparent 60%);
}
.theme-horror .page-frame::before {
  background: repeating-linear-gradient(
    0deg,
    transparent, transparent 28px,
    rgba(100,0,20,.05) 28px, rgba(100,0,20,.05) 29px
  );
}
.theme-horror .inner-border {
  border-color: rgba(160,20,40,.35);
}
.theme-horror .book-cover {
  background: linear-gradient(160deg, #1A0810 0%, #0A0408 50%, #2A0A14 100%);
  box-shadow: -8px 0 0 rgba(80,0,20,.5), 0 10px 50px rgba(0,0,0,.7);
}
.theme-horror .cover-badge {
  background: #8A0A1A;
  color: #FFD0D0;
}
.theme-horror .cover-topic { color: rgba(255,180,180,.5); }
.theme-horror .cover-desc { border-left-color: rgba(255,100,100,.3); color: rgba(255,200,200,.7); }
.theme-horror .cover-sep { background: rgba(255,100,100,.2); }
.theme-horror .cover-meta-item { color: rgba(255,180,180,.5); }
.theme-horror .cover-meta-item strong { color: #FFB0B0; }
.theme-horror .book-page {
  background: #0E0A0C;
  box-shadow: 0 4px 40px rgba(80,0,0,.25);
}
.theme-horror .content p { color: #C0A0A8; }
.theme-horror .content strong { color: #FFD0D0; }
.theme-horror .content em { color: #E06080; }
.theme-horror .page-hdr { border-bottom-color: #4A0A1A; }
.theme-horror .hdr-left { color: #8A2030; }
.theme-horror .hdr-dot { background: #C0303A; }
.theme-horror .hdr-right { color: #6A4048; }
.theme-horror .page-ftr { border-top-color: #3A0A14; }
.theme-horror .ftr-title, .theme-horror .ftr-chapter { color: #5A3040; }
.theme-horror .page-num { background: #5A0A1A; }
.theme-horror .toc-eyebrow { color: #A02030; }
.theme-horror .toc-heading { color: #FFD0D0; }
.theme-horror .toc-ch-name { color: #E0B0B8; }
.theme-horror .toc-ch-sum { color: #7A5060; }
.theme-horror .toc-num { color: #5A1020; }
.theme-horror .toc-pnum { color: #A02030; }
.theme-horror .toc-dots { border-bottom-color: rgba(160,30,50,.25); }
.theme-horror .toc-row { border-bottom-color: rgba(160,30,50,.15); }
.theme-horror .ch-eyebrow { color: #C03040; }
.theme-horror .ch-eyebrow::after { background: #C03040; }
.theme-horror .ch-bg-num { color: #1A0810; -webkit-text-stroke-color: #3A0A1A; }
.theme-horror .ch-h2 { color: #FFD0D0; border-left-color: #8A1020; }
.theme-horror .blk-concept { background: rgba(80,10,20,.35); border-left-color: #8A1020; }
.theme-horror .blk-concept .blk-label { color: #C04050; }
.theme-horror .blk-example { background: rgba(40,10,30,.35); border-left-color: #6A1040; }
.theme-horror .blk-example .blk-label { color: #A03060; }
.theme-horror .blk-activity { background: #1A0E10; border-color: #4A1020; }
.theme-horror .blk-activity .blk-label { color: #C03040; }
.theme-horror .blk-challenge { background: linear-gradient(135deg, #3A0A14, #5A0A1A); }
.theme-horror .blk-fact { background: #1A0E10; border-top-color: #6A3010; border-bottom-color: #6A3010; }
.theme-horror .blk-fact .blk-label { color: #C08020; }
.theme-horror .blk-question { background: #3A0A1A; }
.theme-horror .c-tl, .theme-horror .c-tr, .theme-horror .c-bl, .theme-horror .c-br { color: #5A0A1A; }
.theme-horror .divider { border-top-color: rgba(160,20,40,.2); }
.theme-horror .img-ph { background: linear-gradient(135deg, #1A0A10, #0A0408); border-color: #3A0A14; color: #5A2030; }
.theme-horror .img-block { border-color: #3A0A14; }
.theme-horror .img-caption { background: #1A0A10; color: #6A4050; }
""",
))


# ── 5. Fantasy ────────────────────────────────────────────────────────────
_register(BookTemplate(
    id="fantasy",
    name="Fantasy",
    description="Ornate medieval style with parchment backgrounds and scroll borders",
    emoji="🐉",
    category="genre",
    corner_ornament="⚜",
    font_display="Georgia, 'Palatino Linotype', 'Book Antiqua', serif",
    default_palette="pal-azul",
    theme_css="""\
/* Fantasy theme */
.theme-fantasy .page-frame {
  border-style: ridge;
  border-width: 6px;
  background-image:
    radial-gradient(ellipse at 50% 50%, rgba(245,200,66,.06) 0%, transparent 70%),
    linear-gradient(180deg, rgba(200,160,80,.04) 0%, transparent 40%, rgba(200,160,80,.04) 100%);
}
.theme-fantasy .page-frame::before {
  background: none;
}
.theme-fantasy .inner-border {
  border-style: groove;
  border-width: 2px;
}
.theme-fantasy .book-cover {
  background: linear-gradient(150deg, #0A1840 0%, var(--p-primary) 40%, #0A1040 100%);
  border-radius: 4px 18px 18px 4px;
}
.theme-fantasy .cover-title {
  font-variant: small-caps;
  letter-spacing: .04em;
}
.theme-fantasy .cover-badge {
  background: #D4A520;
  color: #1A0A00;
}
.theme-fantasy .blk-concept {
  border-left: 5px groove var(--p-primary);
}
.theme-fantasy .blk-challenge {
  background: linear-gradient(135deg, #0A1840, #1A3880);
  border: 1px solid rgba(212,165,32,.3);
}
.theme-fantasy .blk-activity {
  border-style: groove;
  border-width: 3px;
}
.theme-fantasy .blk-fact {
  border-top: 3px groove var(--p-accent2);
  border-bottom: 3px groove var(--p-accent2);
}
.theme-fantasy .ch-h2 {
  border-left: 6px groove var(--p-primary);
  font-variant: small-caps;
}
.theme-fantasy .ch-eyebrow {
  font-variant: small-caps;
  letter-spacing: .3em;
}
.theme-fantasy .toc-heading {
  font-variant: small-caps;
}
.theme-fantasy .page-num {
  border-radius: 4px;
  border: 2px groove var(--p-primary);
  background: var(--p-primary);
}
""",
))


# ── 6. Teen Romance ──────────────────────────────────────────────────────
_register(BookTemplate(
    id="teen_romance",
    name="Teen Romance",
    description="Soft pastels, modern typography, and heart accents for teen readers",
    emoji="💕",
    category="genre",
    corner_ornament="♥",
    font_display="Georgia, 'Segoe UI', sans-serif",
    font_body="'Segoe UI', -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif",
    default_palette="pal-rosa",
    theme_css="""\
/* Teen Romance theme */
.theme-teen_romance .page-frame {
  border-width: 4px;
  border-radius: 14px;
  background-image:
    radial-gradient(ellipse at 80% 20%, rgba(184,40,106,.05) 0%, transparent 50%),
    radial-gradient(ellipse at 20% 80%, rgba(240,96,144,.04) 0%, transparent 50%);
}
.theme-teen_romance .page-frame::before {
  background: none;
}
.theme-teen_romance .inner-border {
  border-radius: 10px;
  border-color: rgba(224,116,168,.35);
}
.theme-teen_romance .book-cover {
  background: linear-gradient(135deg, var(--p-primary) 0%, #E060A0 50%, var(--p-secondary) 100%);
  border-radius: 6px 20px 20px 6px;
}
.theme-teen_romance .blk-concept {
  border-radius: 14px;
  border-left: 5px solid var(--p-primary);
  background: linear-gradient(90deg, var(--p-light), rgba(255,255,255,.5));
}
.theme-teen_romance .blk-example {
  border-radius: 14px;
}
.theme-teen_romance .blk-activity {
  border-radius: 18px;
  border-color: var(--p-secondary);
}
.theme-teen_romance .blk-challenge {
  border-radius: 18px;
  background: linear-gradient(135deg, var(--p-primary), var(--p-secondary), #E060A0);
}
.theme-teen_romance .blk-question {
  border-radius: 50px;
  background: linear-gradient(90deg, var(--p-primary), var(--p-secondary));
}
.theme-teen_romance .blk-fact {
  border-radius: 8px;
}
.theme-teen_romance .ch-h2 {
  border-left-color: var(--p-secondary);
}
.theme-teen_romance .page-num {
  background: linear-gradient(135deg, var(--p-primary), var(--p-secondary));
  border-radius: 50%;
}
.theme-teen_romance .toc-num {
  color: var(--p-primary);
}
""",
))


# ── 7. Non-fiction ────────────────────────────────────────────────────────
_register(BookTemplate(
    id="nonfiction",
    name="Non-Fiction",
    description="Clean, professional layout with strong typography and minimal decoration",
    emoji="📰",
    category="general",
    corner_ornament="◆",
    font_display="Georgia, 'Times New Roman', serif",
    font_body="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif",
    default_palette="pal-negro",
    theme_css="""\
/* Non-fiction theme */
.theme-nonfiction .page-frame {
  border-width: 3px;
  border-style: solid;
  border-radius: 0;
}
.theme-nonfiction .page-frame::before {
  background: none;
}
.theme-nonfiction .inner-border {
  border-width: 1px;
  border-style: solid;
  border-radius: 0;
}
.theme-nonfiction .book-cover {
  border-radius: 0 8px 8px 0;
  background: var(--p-primary);
}
.theme-nonfiction .blk-concept {
  border-radius: 0;
  border-left-width: 5px;
}
.theme-nonfiction .blk-example {
  border-radius: 0;
}
.theme-nonfiction .blk-activity {
  border-radius: 4px;
}
.theme-nonfiction .blk-challenge {
  border-radius: 4px;
}
.theme-nonfiction .blk-question {
  border-radius: 4px;
}
.theme-nonfiction .ch-h2 {
  border-left-width: 4px;
  font-variant: small-caps;
  letter-spacing: .02em;
}
.theme-nonfiction .ch-eyebrow {
  letter-spacing: .3em;
}
.theme-nonfiction .toc-heading {
  font-variant: small-caps;
}
.theme-nonfiction .page-num {
  border-radius: 2px;
}
.theme-nonfiction .cover-title {
  letter-spacing: -.02em;
}
""",
))


# ── 8. Art & Activity ────────────────────────────────────────────────────
_register(BookTemplate(
    id="art_activity",
    name="Art & Activity",
    description="Colorful creative style with paint splatter accents and craft-inspired borders",
    emoji="🎨",
    category="general",
    corner_ornament="✿",
    font_display="Georgia, 'Comic Sans MS', cursive, serif",
    default_palette="pal-arcoiris",
    theme_css="""\
/* Art & Activity theme */
.theme-art_activity .page-frame {
  border-width: 5px;
  border-style: dashed;
  border-radius: 16px;
  background-image:
    radial-gradient(circle at 10% 90%, rgba(232,64,96,.05) 0%, transparent 30%),
    radial-gradient(circle at 90% 10%, rgba(32,168,112,.05) 0%, transparent 30%),
    radial-gradient(circle at 50% 50%, rgba(248,200,32,.04) 0%, transparent 40%);
}
.theme-art_activity .page-frame::before {
  background: none;
}
.theme-art_activity .inner-border {
  border-style: dotted;
  border-width: 2.5px;
  border-radius: 12px;
}
.theme-art_activity .book-cover {
  border-radius: 8px 22px 22px 8px;
  background: linear-gradient(135deg, #6030C8 0%, #E84060 25%, #F88020 50%, #20A870 75%, #2070E8 100%);
}
.theme-art_activity .blk-concept {
  border-radius: 16px;
  border-left-width: 6px;
  border-left-style: dotted;
}
.theme-art_activity .blk-example {
  border-radius: 16px;
  border-left-style: dotted;
  border-left-width: 6px;
}
.theme-art_activity .blk-activity {
  border-radius: 20px;
  border-style: dashed;
  border-width: 3px;
  border-color: var(--p-primary);
}
.theme-art_activity .blk-challenge {
  border-radius: 22px;
}
.theme-art_activity .blk-question {
  border-radius: 50px;
  background: linear-gradient(90deg, var(--p-primary), var(--p-secondary));
}
.theme-art_activity .ch-h2 {
  border-left: 6px dotted var(--p-primary);
}
.theme-art_activity .page-num {
  border-radius: 8px;
  transform: rotate(3deg);
}
.theme-art_activity .toc-num {
  color: var(--p-secondary);
  font-style: italic;
}
.theme-art_activity .cover-badge {
  transform: rotate(-3deg);
}
""",
))


# ── 9. Halloween ──────────────────────────────────────────────────────────
_register(BookTemplate(
    id="halloween",
    name="Halloween",
    description="Spooky dark theme with orange/purple accents and creepy decorations",
    emoji="🎃",
    category="seasonal",
    corner_ornament="🕷",
    dark_mode=True,
    default_palette="pal-halloween",
    theme_css="""\
/* Halloween theme */
.theme-halloween { background: #0E0804 !important; }
.theme-halloween .page-frame {
  border-color: #D05800;
  background: #120A08;
  background-image:
    radial-gradient(ellipse at 70% 30%, rgba(106,32,168,.08) 0%, transparent 50%),
    radial-gradient(ellipse at 30% 70%, rgba(208,88,0,.06) 0%, transparent 50%);
}
.theme-halloween .page-frame::before {
  background: repeating-linear-gradient(
    0deg,
    transparent, transparent 28px,
    rgba(208,88,0,.03) 28px, rgba(208,88,0,.03) 29px
  );
}
.theme-halloween .inner-border {
  border-color: rgba(255,140,0,.25);
}
.theme-halloween .book-cover {
  background: linear-gradient(160deg, #1A0A04 0%, #3A1800 40%, #0A0408 100%);
  box-shadow: -8px 0 0 rgba(100,30,0,.5), 0 10px 50px rgba(0,0,0,.7);
}
.theme-halloween .cover-badge { background: #D05800; color: #FFE0C0; }
.theme-halloween .cover-topic { color: rgba(255,200,150,.5); }
.theme-halloween .cover-desc { border-left-color: rgba(255,140,0,.3); color: rgba(255,220,180,.7); }
.theme-halloween .cover-sep { background: rgba(255,140,0,.2); }
.theme-halloween .cover-meta-item { color: rgba(255,200,150,.5); }
.theme-halloween .cover-meta-item strong { color: #FFC080; }
.theme-halloween .book-page { background: #0E0804; box-shadow: 0 4px 40px rgba(100,30,0,.2); }
.theme-halloween .content p { color: #C0A080; }
.theme-halloween .content strong { color: #FFD0A0; }
.theme-halloween .content em { color: #FF8C00; }
.theme-halloween .page-hdr { border-bottom-color: #3A1800; }
.theme-halloween .hdr-left { color: #D05800; }
.theme-halloween .hdr-dot { background: #FF8C00; }
.theme-halloween .hdr-right { color: #6A4020; }
.theme-halloween .page-ftr { border-top-color: #2A1200; }
.theme-halloween .ftr-title, .theme-halloween .ftr-chapter { color: #5A3020; }
.theme-halloween .page-num { background: #D05800; }
.theme-halloween .toc-eyebrow { color: #FF8C00; }
.theme-halloween .toc-heading { color: #FFD0A0; }
.theme-halloween .toc-ch-name { color: #E0C0A0; }
.theme-halloween .toc-ch-sum { color: #7A5030; }
.theme-halloween .toc-num { color: #5A2800; }
.theme-halloween .toc-pnum { color: #D05800; }
.theme-halloween .toc-dots { border-bottom-color: rgba(208,88,0,.2); }
.theme-halloween .toc-row { border-bottom-color: rgba(208,88,0,.12); }
.theme-halloween .ch-eyebrow { color: #FF8C00; }
.theme-halloween .ch-eyebrow::after { background: #FF8C00; }
.theme-halloween .ch-bg-num { color: #1A0A04; -webkit-text-stroke-color: #2A1200; }
.theme-halloween .ch-h2 { color: #FFD0A0; border-left-color: #D05800; }
.theme-halloween .blk-concept { background: rgba(100,30,0,.25); border-left-color: #D05800; }
.theme-halloween .blk-concept .blk-label { color: #FF8C00; }
.theme-halloween .blk-example { background: rgba(106,32,168,.15); border-left-color: #6A20A8; }
.theme-halloween .blk-example .blk-label { color: #A050D0; }
.theme-halloween .blk-activity { background: #1A0E08; border-color: #3A1800; }
.theme-halloween .blk-activity .blk-label { color: #FF8C00; }
.theme-halloween .blk-challenge { background: linear-gradient(135deg, #3A1800, #D05800); }
.theme-halloween .blk-fact { background: #1A0E08; border-top-color: #8A6000; border-bottom-color: #8A6000; }
.theme-halloween .blk-fact .blk-label { color: #F8C820; }
.theme-halloween .blk-question { background: #3A1800; }
.theme-halloween .c-tl, .theme-halloween .c-tr, .theme-halloween .c-bl, .theme-halloween .c-br { color: #D05800; }
.theme-halloween .divider { border-top-color: rgba(208,88,0,.15); }
.theme-halloween .img-ph { background: linear-gradient(135deg, #1A0A04, #0A0408); border-color: #3A1800; color: #5A3020; }
.theme-halloween .img-block { border-color: #3A1800; }
.theme-halloween .img-caption { background: #1A0A04; color: #6A4020; }
""",
))


# ── 10. Holiday / Christmas ──────────────────────────────────────────────
_register(BookTemplate(
    id="holiday",
    name="Holiday",
    description="Festive red and green with snowflake ornaments and gift-wrap borders",
    emoji="🎄",
    category="seasonal",
    corner_ornament="❄",
    default_palette="pal-navidad",
    theme_css="""\
/* Holiday theme */
.theme-holiday .page-frame {
  border-style: double;
  border-width: 5px;
  border-color: var(--p-primary);
  background-image:
    radial-gradient(ellipse at 20% 20%, rgba(30,110,46,.06) 0%, transparent 40%),
    radial-gradient(ellipse at 80% 80%, rgba(200,48,32,.05) 0%, transparent 40%);
}
.theme-holiday .page-frame::before {
  background: repeating-linear-gradient(
    0deg,
    transparent, transparent 32px,
    rgba(30,110,46,.03) 32px, rgba(30,110,46,.03) 33px
  );
}
.theme-holiday .inner-border {
  border-style: double;
  border-width: 3px;
  border-color: rgba(200,48,32,.35);
}
.theme-holiday .book-cover {
  background: linear-gradient(150deg, #0A2010 0%, var(--p-primary) 40%, #1A4020 100%);
}
.theme-holiday .cover-badge {
  background: #C83020;
  color: #FFEFEF;
}
.theme-holiday .blk-concept {
  border-left: 5px double var(--p-primary);
}
.theme-holiday .blk-example {
  border-left: 5px solid #C83020;
  background: rgba(200,48,32,.06);
}
.theme-holiday .blk-example .blk-label { color: #C83020; }
.theme-holiday .blk-challenge {
  background: linear-gradient(135deg, var(--p-primary), #C83020);
}
.theme-holiday .blk-fact {
  border-top-color: #F8CC20;
  border-bottom-color: #F8CC20;
}
.theme-holiday .blk-activity {
  border: 2.5px double var(--p-secondary);
}
.theme-holiday .ch-h2 {
  border-left: 6px double var(--p-primary);
}
.theme-holiday .page-num {
  border-radius: 4px;
}
.theme-holiday .toc-num {
  color: #C83020;
}
""",
))


# ═══════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════

def get_template(template_id: str) -> BookTemplate:
    """
    Return a :class:`BookTemplate` by ID.

    Falls back to ``"educational"`` when the ID is unknown.
    """
    return _TEMPLATES.get(template_id, _TEMPLATES["educational"])


def list_templates() -> list[BookTemplate]:
    """Return all registered templates (ordered by registration)."""
    return list(_TEMPLATES.values())


def list_template_ids() -> list[str]:
    """Return all registered template IDs."""
    return list(_TEMPLATES.keys())


def template_choices() -> list[tuple[str, str]]:
    """Return ``(display_label, template_id)`` pairs for a UI picker.

    Includes an "Auto" option that lets the system pick the best template.
    """
    choices = [("🤖  Auto — AI picks the best template for your topic", "auto")]
    choices.extend(
        (f"{t.emoji}  {t.name}", t.id) for t in _TEMPLATES.values()
    )
    return choices


# ═══════════════════════════════════════════════════════════════════════════
#  AUTO-PICK LOGIC
# ═══════════════════════════════════════════════════════════════════════════

_AUTO_PICK_RULES: list[tuple[list[str], str]] = [
    # (keyword list, template_id)
    (["terror", "horror", "miedo", "zombie", "vampir", "scary", "creepy", "dark"], "horror"),
    (["halloween", "brujas", "witch", "pumpkin", "calabaza"], "halloween"),
    (["navidad", "christmas", "santa", "holiday", "festiv"], "holiday"),
    (["fantasía", "fantasia", "fantasy", "dragón", "dragon", "medieval", "magic", "mago", "wizard"], "fantasy"),
    (["romance", "amor", "love", "teen", "adolescent"], "teen_romance"),
    (["arte", "art", "dibujo", "pintura", "manualidad", "craft", "drawing", "painting"], "art_activity"),
    (["cuento", "fairy", "fábula", "fabula", "story", "storybook", "hada"], "storybook"),
    (["biología", "biologia", "biology", "planta", "plant", "animal", "ecología", "ecology", "naturaleza", "nature", "botánica", "botanica"], "botanical"),
    (["periodismo", "journalism", "noticia", "news", "report", "non-fiction", "ensayo", "essay"], "nonfiction"),
]


def auto_pick_template(topic: str) -> str:
    """Choose a template ID based on the book topic.

    Returns ``"educational"`` when no keyword matches.
    """
    t = (topic or "").lower()
    for keywords, tid in _AUTO_PICK_RULES:
        if any(kw in t for kw in keywords):
            return tid
    return "educational"

# agents/html_css_agent.py
import json
import markdown
from pathlib import Path
from typing import Dict, Any
from models.book_spec import BookRequest, Curriculum, ChapterContent  # ✅ FIXED

def generate_html_css_book_from_json(
    book_request: BookRequest,
    curriculum: Curriculum,
    chapters: list[ChapterContent],
    output_html: str
):
    """Generate HTML book using real book metadata."""
    html = f"""<!DOCTYPE html>
<html lang="{book_request.language.lower()[:2]}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{curriculum.title}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>tailwind.config = {{ theme: {{ extend: {{ colors: {{ 
        'mx-green': '#006341', /* Mexican flag green (dark) */
        'mx-red': '#CE1126',   /* Mexican flag red */
        'mx-white': '#ffffff'
    }} }} }} }};</script>
    <style>
        :root {{
            --bg: #0b0f13; /* dark background */
            --card: #0f1720; /* slightly lighter card */
            --muted: #9ca3af;
        }}
        body {{ background: var(--bg); color: var(--mx-white); font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; }}
        .section-frame {{ border-left-width: 6px; padding: 1.25rem; margin: 1.5rem 0; }}
        .chapter-card {{ background: var(--card); border-radius: 0.75rem; padding: 1.25rem; box-shadow: 0 6px 18px rgba(2,6,23,0.6); }}
        .mx-accent-green {{ color: var(--mx-white); border-left: 6px solid #006341; background: linear-gradient(90deg, rgba(0,99,65,0.04), transparent); padding-left: 1rem; }}
        .mx-accent-red {{ color: var(--mx-white); border-left: 6px solid #CE1126; background: linear-gradient(90deg, rgba(206,17,38,0.04), transparent); padding-left: 1rem; }}
+        .qr-placeholder {{
            position: fixed;
            bottom: 1.5rem;
            right: 1.5rem;
            width: 120px;
            height: 120px;
            background: var(--mx-white);
            border-radius: 0.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 50;
        }}
        .qr-placeholder img {{ width: 100px; height: 100px; }}
+    </style>
</head>
<body>
<div class="max-w-4xl mx-auto px-4 py-8">
    <header class="text-center mb-12">
        <h1 class="text-3xl md:text-4xl font-bold text-gray-900 mb-4">{curriculum.title}</h1>
        <p class="text-lg text-gray-600">{curriculum.description}</p>
        <div class="mt-2 text-sm text-gray-500">
            {book_request.num_chapters} capítulos • Público: {book_request.target_audience_age} años • {book_request.country}
        </div>
    </header>
    <main>
"""

    for i, chapter in enumerate(chapters):
        md_html = markdown.markdown(chapter.markdown_content, extensions=["extra"])
        md_html = _apply_section_styling(md_html)
        placeholder_html = _generate_placeholders(chapter)

        html += f"""
        <article class="chapter-card mb-8">
            <h2 class="text-2xl font-bold mb-6" style="color:var(--mx-white);">{chapter.chapter_title}</h2>
+
            {md_html}
+
            {placeholder_html}
+
        </article>
        """

        if chapter.videos:
            video = chapter.videos[0]
            html += f"""
            <div class="qr-placeholder" title="Mira el video complementario">
                <img src="{video.qr_code}" alt="QR Video">
            </div>
            """

    html += """
    </main>
</div>
</body>
</html>"""

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ HTML book saved as: {output_html}")


def _apply_section_styling(html: str) -> str:
    # Simplified placeholder — implement as needed
    return html

def _generate_placeholders(chapter) -> str:
    # Simplified placeholder
    return ""
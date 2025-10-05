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
        'frame-blue': '#dbeafe',
        'frame-green': '#dcfce7',
        'frame-yellow': '#fef9c3',
        'frame-purple': '#ede9fe',
        'frame-pink': '#fce7f3'
    }} }} }} }};</script>
    <style>
        .section-frame {{ border-left-width: 6px; padding: 1.25rem; margin: 1.5rem 0; }}
        .qr-placeholder {{
            position: fixed;
            bottom: 1.5rem;
            right: 1.5rem;
            width: 120px;
            height: 120px;
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 0.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            z-index: 50;
        }}
        .qr-placeholder img {{ width: 100px; height: 100px; }}
    </style>
</head>
<body class="bg-gray-50">
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
        <article class="chapter bg-white rounded-xl shadow-sm p-6 mb-8">
            <h2 class="text-2xl font-bold text-gray-900 mb-6">{chapter.chapter_title}</h2>
            {md_html}
            {placeholder_html}
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
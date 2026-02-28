import re
import markdown
from models.book_spec import BookOutput


def generate_html_book(output: BookOutput, output_path: str):
    """Generate a simple dark-themed HTML book using Mexican flag colors.

    The function builds the HTML from the provided BookOutput and writes it to disk.
    """
    template = """<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{ --bg: #0b0f13; --card: #0f1720; --mx-white: #ffffff; --mx-green: #006341; --mx-red: #CE1126; --muted: #9ca3af; }}
    body {{ background: var(--bg); color: var(--mx-white); font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; margin: 0; padding: 28px; }}
    .container {{ max-width: 900px; margin: 0 auto; padding: 0 16px; }}
    .chapter-card {{ background: var(--card); border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 6px 18px rgba(2,6,23,0.6); }}
    h1, h2, h3 {{ color: var(--mx-white); margin: 0 0 12px 0; }}
    .meta {{ color: var(--muted); margin-bottom: 18px; }}
    .mx-accent-green {{ border-left: 6px solid var(--mx-green); padding-left: 12px; }}
    .mx-accent-red {{ border-left: 6px solid var(--mx-red); padding-left: 12px; }}
    a {{ color: #93c5fd; }}
    img {{ max-width: 100%; height: auto; }}
  </style>
</head>
<body>
  <div class="container">
    <header style="text-align:center; margin: 28px 0 36px 0;">
      <h1>{title}</h1>
      <p class="meta">{description}</p>
    </header>
    {chapters}
  </div>
</body>
</html>"""

    chapter_blocks = []
    for ch in output.chapters:
        md_html = markdown.markdown(ch.markdown_content or "", extensions=["extra"]) if ch.markdown_content is not None else ""
        # Replace leftover [IMAGE:]/[VIDEO:] text with styled HTML
        md_html = re.sub(
            r'\[IMAGE:\s*([^\]]+)\]',
            '<div style="border-left:6px solid #006341;padding:12px;margin:12px 0;background:rgba(0,99,65,0.06);border-radius:6px;"><span>🖼️</span> <em>\\1</em></div>',
            md_html,
        )
        md_html = re.sub(
            r'\[VIDEO:\s*([^\]]+)\]',
            '<div style="border-left:6px solid #CE1126;padding:12px;margin:12px 0;background:rgba(206,17,38,0.06);border-radius:6px;"><span>🎬</span> <em>\\1</em></div>',
            md_html,
        )
        block = f"<article class=\"chapter-card\"><h2>{ch.chapter_title}</h2>{md_html}</article>"
        chapter_blocks.append(block)

    rendered = template.format(
        lang=output.book_request.language[:2],
        title=output.curriculum.title,
        description=output.curriculum.description,
        chapters="\n".join(chapter_blocks),
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered)
# agents/html_agent.py
import markdown
from bs4 import BeautifulSoup
from models.book_spec import ChapterContent

def add_styles(html: str) -> str:
    styles = '''
    <style>
    body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }
    .frame-blue { border-left: 6px solid #4A90E2; background-color: #F0F8FF; padding: 16px; margin: 16px 0; }
    .frame-green { border-left: 6px solid #50C878; background-color: #F0FFF0; padding: 16px; margin: 16px 0; }
    .frame-yellow { border-left: 6px solid #FFD700; background-color: #FFFACD; padding: 16px; margin: 16px 0; }
    .frame-purple { border-left: 6px solid #9370DB; background-color: #F5F5DC; padding: 16px; margin: 16px 0; }
    img { max-width: 100%; height: auto; margin: 10px 0; }
    input[type="text"], textarea {
        width: 100%; padding: 8px; margin: 8px 0; border: 1px solid #ccc; border-radius: 4px;
    }
    .qr-video-surprise {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 120px;
        height: 120px;
        border: 2px solid #ccc;
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        z-index: 1000;
        background: white;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .qr-video-surprise img {
        width: 100px;
        height: 100px;
    }
    </style>
    '''
    return html.replace("</head>", styles + "</head>")

def add_mathjax(html: str) -> str:
    mathjax = '''
    <script>
    MathJax = { tex: { inlineMath: [['\\(', '\\)'], ['$$', '$$']] } };
    </script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    '''
    return html.replace("</head>", mathjax + "</head>")

def apply_section_colors(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    color_classes = ["frame-blue", "frame-green", "frame-yellow", "frame-purple"]
    for i, tag in enumerate(soup.find_all(["h2", "h3", "section", "div"])):
        if tag.name in ["h2", "h3"] or ("class" in tag.attrs and "section" in tag["class"]):
            tag["class"] = tag.get("class", []) + [color_classes[i % len(color_classes)]]
    return str(soup)

async def generate_html_book(chapters: list[ChapterContent]) -> str:
    html = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Libro Interactivo de IA en México 2025</title>
</head>
<body>'''

    for chapter in chapters:
        # Convert Markdown to HTML
        md_html = markdown.markdown(chapter.markdown_content, extensions=['extra'])
        md_html = apply_section_colors(md_html)
        html += f'<div class="chapter"><h1>{chapter.chapter_title}</h1>{md_html}</div>'

        # Add QR video (only first video per chapter)
        if chapter.videos:
            video = chapter.videos[0]
            html += f'''
            <div class="qr-video-surprise" title="Mira el video complementario">
                <img src="{video.qr_code}" alt="QR: {video.title}">
            </div>
            '''

    html += "</body></html>"
    html = add_styles(html)
    html = add_mathjax(html)
    return html
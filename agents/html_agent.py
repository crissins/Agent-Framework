import markdown
from models.book_spec import BookOutput

def generate_html_book(output: BookOutput, output_path: str):
    html = f"""<!DOCTYPE html>
<html lang="{output.book_request.language[:2]}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{output.curriculum.title}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .section-frame {{ border-left-width: 6px; padding: 1.25rem; margin: 1.5rem 0; }}
        .frame-blue {{ border-left-color: #4A90E2; background-color: #F0F8FF; }}
        .frame-green {{ border-left-color: #50C878; background-color: #F0FFF0; }}
        .frame-yellow {{ border-left-color: #FFD700; background-color: #FFFACD; }}
        .frame-purple {{ border-left-color: #9370DB; background-color: #F5F5DC; }}
    </style>
</head>
<body class="bg-gray-50 p-6">
    <header class="text-center mb-12">
        <h1 class="text-3xl font-bold">{output.curriculum.title}</h1>
        <p class="text-lg text-gray-600">{output.curriculum.description}</p>
    </header>
    <main>"""

    for ch in output.chapters:
        md_html = markdown.markdown(ch.markdown_content, extensions=["extra"])
        html += f'<article class="mb-8"><h2 class="text-2xl font-bold mb-4">{ch.chapter_title}</h2>{md_html}</article>'

    html += "</main></body></html>"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
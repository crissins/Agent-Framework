import base64
import re
from pathlib import Path

from models.book_spec import BookOutput


def _replace_media_placeholders(markdown: str) -> str:
    """Replace any remaining [IMAGE: ...] and [VIDEO: ...] placeholders with styled markdown."""
    result = re.sub(r'\[IMAGE:\s*([^\]]+)\]', '> 🖼️ *Illustration: \\1*', markdown)
    result = re.sub(r'\[VIDEO:\s*([^\]]+)\]', '> 🎬 *Video: \\1*', result)
    return result


def _strip_leading_heading(markdown: str, title: str) -> str:
    """Remove a leading H1 or H2 that duplicates the chapter title.

    Matches lines like '# Title' or '## Title' (case-insensitive, allows extra whitespace).
    Returns the markdown with the leading heading removed if it matched, otherwise returns original.
    """
    if not markdown:
        return markdown

    # Normalize title for comparison
    norm_title = re.sub(r"\s+", " ", title.strip()).lower()

    # Check first non-empty line
    lines = markdown.splitlines()
    i = 0
    # skip leading blank lines
    while i < len(lines) and lines[i].strip() == "":
        i += 1

    if i < len(lines):
        first = lines[i].strip()
        # Match H1 or H2 headings: '# Title' or '## Title'
        m = re.match(r"^#{1,2}\s+(.*)$", first)
        if m:
            first_title = re.sub(r"\s+", " ", m.group(1).strip()).lower()
            if first_title == norm_title:
                # remove that line
                del lines[i]
                # also strip following blank line (if any)
                if i < len(lines) and lines[i].strip() == "":
                    del lines[i]
                return "\n".join(lines)

    return markdown


def save_markdown_book(output: BookOutput, output_path: str):
    md = f"# {output.curriculum.title}\n\n{output.curriculum.description}\n\n---\n\n"
    for ch in output.chapters:
        # Remove duplicated leading headings in chapter markdown to avoid '## Title' followed by '# Title'
        clean_md = _strip_leading_heading(ch.markdown_content, ch.chapter_title)
        # Replace any remaining [IMAGE:]/[VIDEO:] placeholders with styled callouts
        clean_md = _replace_media_placeholders(clean_md)
        md += f"## {ch.chapter_title}\n\n{clean_md}\n\n---\n\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)

    _embed_images_as_base64_md(output_path)


def _embed_images_as_base64_md(md_path: str):
    """Post-process MD file to embed local images as base64 data URIs.

    Makes the Markdown completely self-contained.
    """
    path = Path(md_path)
    if not path.exists():
        return
    content = path.read_text(encoding="utf-8")
    base_dir = path.parent

    def _replace_md_img(match):
        alt, src = match.group(1), match.group(2)
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
            return f"![{alt}](data:{mime};base64,{data})"
        except Exception:
            return match.group(0)

    content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', _replace_md_img, content)
    path.write_text(content, encoding="utf-8")
    print(f"  📎 Images embedded as base64 in Markdown")
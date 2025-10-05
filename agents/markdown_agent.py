from models.book_spec import BookOutput
import re


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
        md += f"## {ch.chapter_title}\n\n{clean_md}\n\n---\n\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)
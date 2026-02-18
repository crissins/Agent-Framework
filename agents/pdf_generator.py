"""
PDF generation for book output using fpdf2 (lightweight, open-source).

Generates professional PDF books from markdown content with:
- Title page with book metadata
- Table of contents
- Chapter content with proper formatting
- Clean typography and page numbers
"""

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

from models.book_spec import BookRequest, Curriculum, ChapterContent
from typing import List
from datetime import datetime
import re


def generate_pdf_book(
    request: BookRequest,
    curriculum: Curriculum,
    chapters: List[ChapterContent],
    output_path: str
) -> bool:
    """
    Generate a professional PDF book from structured data using fpdf2.

    Args:
        request: BookRequest with book specifications
        curriculum: Curriculum object with chapter outlines
        chapters: List of ChapterContent objects with markdown
        output_path: Path where PDF will be saved

    Returns:
        True if successful, False otherwise
    """
    if FPDF is None:
        print("❌ fpdf2 not installed. Install with: pip install fpdf2")
        return False

    try:
        print(f"\n{'='*80}")
        print(f"Generating PDF: {output_path}")
        print(f"{'='*80}\n")

        pdf = CustomPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # === TITLE PAGE ===
        pdf.set_font("Helvetica", "B", 28)
        pdf.set_text_color(31, 71, 136)  # Dark blue
        pdf.multi_cell(0, 12, _strip_emoji(request.topic), align="C")

        pdf.ln(10)
        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(51, 51, 51)

        metadata = (
            f"Age: {request.target_audience_age} years\n"
            f"Country: {request.country}\n"
            f"Learning Method: {request.learning_method}\n"
            f"Language: {request.language}\n"
            f"Chapters: {len(chapters)}"
        )
        pdf.multi_cell(0, 6, metadata, align="C")

        pdf.ln(10)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 5, _strip_emoji(curriculum.description), align="L")

        pdf.ln(15)
        pdf.set_font("Helvetica", "I", 9)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pdf.cell(0, 5, f"Generated: {timestamp}", align="C")

        # === TABLE OF CONTENTS ===
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(31, 71, 136)
        pdf.cell(0, 10, "Table of Contents", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(5)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(0, 0, 0)

        for i, outline in enumerate(curriculum.chapters, 1):
            title = _strip_emoji(outline.title)
            summary = _strip_emoji(outline.summary)
            summary = summary[:80] + "..." if len(summary) > 80 else summary
            pdf.multi_cell(0, 6, f"Chapter {i}: {title}\n{summary}\n", align="L")
            pdf.ln(2)

        # === CHAPTERS ===
        for i, chapter in enumerate(chapters, 1):
            pdf.add_page()

            # Chapter header
            pdf.set_font("Helvetica", "B", 16)
            pdf.set_text_color(31, 71, 136)
            pdf.multi_cell(0, 8, f"Chapter {i}: {_strip_emoji(chapter.chapter_title)}", align="L")
            pdf.ln(5)

            # Chapter content
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(0, 0, 0)
            _add_markdown_to_pdf(pdf, chapter.markdown_content)

        # === SAVE PDF ===
        pdf.output(output_path)
        print(f"PDF generated successfully: {output_path}\n")
        return True

    except Exception as e:
        print(f"Error generating PDF: {e}\n")
        import traceback
        print(traceback.format_exc())
        return False


class CustomPDF(FPDF if FPDF else object):
    """Custom PDF class with page number footer."""

    def header(self):
        pass

    def footer(self):
        """Add page number at bottom."""
        self.set_y(-10)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def _strip_emoji(text: str) -> str:
    """Remove emoji characters that PDF fonts can't render."""
    # Remove characters outside the Latin-1 supplement range
    return re.sub(r'[^\x00-\xFF]', '', text).strip()


def _add_markdown_to_pdf(pdf: "FPDF", markdown_text: str) -> None:
    """
    Convert markdown to formatted PDF content.

    Supports:
    - ## / ### headers -> larger bold text
    - **bold** -> bold text
    - - bullets -> bullet points
    - [IMAGE: ...] / [VIDEO: ...] -> placeholder text
    - Regular paragraphs
    """
    lines = _strip_emoji(markdown_text).split('\n')

    for line in lines:
        line = line.strip()

        # Empty line
        if not line:
            pdf.ln(3)
            continue

        # H1 header (# title)
        if line.startswith('# ') and not line.startswith('## '):
            title = line[2:]
            pdf.set_font("Helvetica", "B", 15)
            pdf.set_text_color(31, 71, 136)
            pdf.multi_cell(0, 7, title, align="L")
            pdf.ln(2)
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(0, 0, 0)

        # H2 header (## title)
        elif line.startswith('## '):
            title = line[3:]
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(31, 71, 136)
            pdf.multi_cell(0, 7, title, align="L")
            pdf.ln(2)
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(0, 0, 0)

        # H3 header (### title)
        elif line.startswith('### '):
            title = line[4:]
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(60, 90, 150)
            pdf.multi_cell(0, 6, title, align="L")
            pdf.ln(1)
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(0, 0, 0)

        # Bold text lines containing **...**
        elif '**' in line:
            parts = line.split('**')
            for j, part in enumerate(parts):
                if not part:
                    continue
                if j % 2 == 0:
                    pdf.set_font("Helvetica", "", 11)
                else:
                    pdf.set_font("Helvetica", "B", 11)
                pdf.write(5, part)
            pdf.ln(5)
            pdf.set_font("Helvetica", "", 11)

        # Bullet points
        elif line.startswith('- ') or line.startswith('* '):
            bullet_text = line[2:]
            pdf.set_x(pdf.l_margin + 5)
            pdf.multi_cell(0, 5, f"  {bullet_text}", align="L")

        # Image/Video placeholders
        elif '[IMAGE:' in line or '[VIDEO:' in line:
            placeholder = re.sub(r'[\[\]]', '', line)
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(0, 5, f"[{placeholder}]", align="L")
            pdf.ln(3)
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(0, 0, 0)

        # Regular paragraph
        else:
            pdf.multi_cell(0, 5, line, align="L")
            pdf.ln(1)

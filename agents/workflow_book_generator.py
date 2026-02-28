"""
Workflow-style orchestration for end-to-end book generation.

This module provides a stable, testable pipeline that:
1) Collects a book request
2) Generates curriculum
3) Generates chapter content
4) Exports HTML and Markdown outputs
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict

from agents.chapter_agent import create_chapter_agent, generate_chapter
from agents.curriculum_agent import create_curriculum_agent, generate_curriculum
from agents.greet_agent import create_greet_agent, get_book_request
from agents.html_css_agent import generate_html_css_book_from_json
from agents.markdown_agent import save_markdown_book
from models.book_spec import BookOutput

logger = logging.getLogger(__name__)


def _chapter_context(book_request) -> Dict[str, object]:
    return {
        "age": book_request.target_audience_age,
        "country": book_request.country,
        "learning_method": book_request.learning_method,
        "language": book_request.language,
        "pages_per_chapter": book_request.pages_per_chapter,
    }


async def generate_book_output(use_qwen: bool = False) -> BookOutput:
    """Run the core generation pipeline and return a fully-populated BookOutput."""
    greet_agent = await create_greet_agent(use_qwen=use_qwen)
    book_request = await get_book_request(greet_agent)
    if not book_request:
        raise RuntimeError("Failed to collect a valid book request")

    curriculum_agent = await create_curriculum_agent(use_qwen=use_qwen)
    curriculum = await generate_curriculum(curriculum_agent, book_request)
    if not curriculum:
        raise RuntimeError("Failed to generate curriculum")

    chapter_agent = await create_chapter_agent(use_qwen=use_qwen)
    context = _chapter_context(book_request)

    chapters = []
    for outline in curriculum.chapters:
        chapter = await generate_chapter(chapter_agent, outline, context)
        if chapter:
            chapters.append(chapter)

    if not chapters:
        raise RuntimeError("No chapters were generated")

    return BookOutput(
        book_request=book_request,
        curriculum=curriculum,
        chapters=chapters,
    )


async def export_book_outputs(output: BookOutput, output_dir: str = "books/workflow") -> tuple[str, str]:
    """Export HTML + Markdown outputs and return generated file paths."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = Path(output_dir) / timestamp
    base_dir.mkdir(parents=True, exist_ok=True)

    html_path = str(base_dir / "book.html")
    md_path = str(base_dir / "book.md")

    generate_html_css_book_from_json(
        book_request=output.book_request,
        curriculum=output.curriculum,
        chapters=output.chapters,
        output_html=html_path,
    )
    save_markdown_book(output, md_path)

    return html_path, md_path


async def main() -> None:
    logger.info("Starting workflow-style LATAM book generation")

    output = await generate_book_output(use_qwen=False)
    html_path, md_path = await export_book_outputs(output)

    logger.info("Workflow completed successfully")
    logger.info("HTML: %s", html_path)
    logger.info("Markdown: %s", md_path)


if __name__ == "__main__":
    asyncio.run(main())

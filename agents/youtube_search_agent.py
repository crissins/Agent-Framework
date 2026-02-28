# agents/youtube_search_agent.py
"""
YouTube video search agent using DuckDuckGo.

Searches for real YouTube educational videos related to chapter content,
generates QR codes for easy access, and returns structured VideoPlaceholder
objects ready to embed in HTML/PDF exports.

This is a refined wrapper around video_search_agent.py with:
- Better query construction for educational content
- Multi-language search bias
- Configurable safety levels
- Batch search for entire books
"""
import asyncio
import re
import logging
from typing import Optional, List

from ddgs import DDGS
from models.book_spec import VideoPlaceholder
from agents.qr_agent import generate_qr_code

logger = logging.getLogger(__name__)

# ── Region mapping ────────────────────────────────────────────────────────
_REGION_MAP = {
    "Mexico": "mx-es",
    "Colombia": "co-es",
    "Argentina": "ar-es",
    "Chile": "cl-es",
    "Peru": "pe-es",
    "Brazil": "br-pt",
    "United States": "us-en",
}

# ── Language-specific educational keywords ────────────────────────────────
_EDU_KEYWORDS = {
    "Spanish": "educativo OR educación OR para niños OR aprender",
    "Portuguese": "educativo OR educação OR para crianças OR aprender",
    "English": "educational OR learning OR for kids OR tutorial",
}


async def search_youtube_video(
    query: str,
    language: str = "Spanish",
    country: str = "Mexico",
    max_results: int = 8,
    safesearch: str = "moderate",
    duration: str = "short",
) -> Optional[VideoPlaceholder]:
    """
    Search DuckDuckGo Videos for a YouTube result matching *query*.

    Args:
        query: Search query
        language: Content language for keyword biasing
        country: Target country for region selection
        max_results: Maximum results to scan
        safesearch: Safety level ('strict', 'moderate', 'off')
        duration: Video duration filter ('short', 'medium', 'long')

    Returns:
        VideoPlaceholder with URL, title, and QR code, or None
    """
    def _sync() -> Optional[VideoPlaceholder]:
        try:
            region = _REGION_MAP.get(country, "wt-wt")
            edu_kw = _EDU_KEYWORDS.get(language, "educational")

            # Include educational keywords but NOT site:youtube.com — DDG video
            # search already surfaces YouTube results and the site: operator
            # can interfere with ranking / result count.
            enhanced = f"{query} {edu_kw}"

            with DDGS() as ddgs:
                results = list(ddgs.videos(
                    enhanced,
                    region=region,
                    safesearch=safesearch,
                    max_results=max_results,
                    duration=duration,
                ))

            # Prefer youtube.com URLs
            for r in results:
                url = r.get("content") or r.get("embed_url") or ""
                if "youtube.com" in url or "youtu.be" in url:
                    title = r.get("title", query)
                    qr = generate_qr_code(url)
                    logger.info(f"🎬 Found YouTube: {title[:80]}  →  {url}")
                    return VideoPlaceholder(query=query, title=title, url=url, qr_code=qr)

            # Fallback: first result regardless of host
            if results:
                r = results[0]
                url = r.get("content") or ""
                title = r.get("title", query)
                qr = generate_qr_code(url) if url else ""
                logger.info(f"🎬 Fallback video: {title[:80]}  →  {url}")
                return VideoPlaceholder(query=query, title=title, url=url, qr_code=qr)

        except Exception as e:
            logger.warning(f"Video search failed for '{query}': {e}")
        return None

    return await asyncio.to_thread(_sync)


def extract_video_placeholders(markdown: str) -> List[str]:
    """Return all [VIDEO: description] placeholder texts from markdown."""
    return re.findall(r'\[VIDEO:\s*([^\]]+)\]', markdown)


async def search_videos_for_chapter(
    chapter_title: str,
    video_queries: List[str],
    topic: str = "",
    language: str = "Spanish",
    country: str = "Mexico",
) -> List[VideoPlaceholder]:
    """
    Search YouTube for every [VIDEO: ...] placeholder in a chapter.

    Returns a list of VideoPlaceholder (one per query, in order).
    Failed searches are silently skipped.
    """
    results: List[VideoPlaceholder] = []
    for q in video_queries:
        full_query = f"{topic} {q}" if topic else q
        vid = await search_youtube_video(
            query=full_query,
            language=language,
            country=country,
        )
        if vid:
            results.append(vid)
        else:
            logger.warning(f"  ⚠️ No video found for: {q}")
    return results


async def search_videos_for_book(
    chapters: list,
    topic: str = "",
    language: str = "Spanish",
    country: str = "Mexico",
) -> dict[int, List[VideoPlaceholder]]:
    """
    Search YouTube videos for all chapters in a book.

    Args:
        chapters: List of ChapterContent objects with markdown_content
        topic: Book topic for query enrichment
        language: Content language
        country: Target country

    Returns:
        Dict mapping chapter index → list of VideoPlaceholders
    """
    book_videos: dict[int, List[VideoPlaceholder]] = {}

    for i, chapter in enumerate(chapters):
        queries = extract_video_placeholders(chapter.markdown_content)
        if queries:
            logger.info(f"🔍 Searching {len(queries)} videos for chapter {i+1}: {chapter.chapter_title}")
            videos = await search_videos_for_chapter(
                chapter_title=chapter.chapter_title,
                video_queries=queries,
                topic=topic,
                language=language,
                country=country,
            )
            book_videos[i] = videos
        else:
            book_videos[i] = []

    return book_videos

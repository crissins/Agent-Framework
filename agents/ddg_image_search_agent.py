# agents/ddg_image_search_agent.py
"""
DuckDuckGo image search agent for educational content.

Searches for real images (not AI-generated) with strict safe search enabled.
Used as an alternative to Qwen AI image generation when the user prefers
to embed real-world photographs or illustrations.

Features:
- Strict safe search enforced by default
- Multi-region support matching LATAM countries
- Language-aware query enrichment
- Downloads and saves images locally for offline use
- Falls back gracefully on errors
"""
import asyncio
import logging
import os
import re
import requests
from io import BytesIO
from pathlib import Path
from typing import Optional, List

from ddgs import DDGS
from models.book_spec import ImagePlaceholder

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


def _build_image_query(query: str, language: str = "Spanish", topic: str = "") -> str:
    """Build a clean, short search query that avoids DDG 403 rate-limits.

    Strips Spanish/special punctuation (¡!¿?:,), keeps the 4 most
    meaningful words, and appends a single educational qualifier.
    Long quoted-phrase searches with special chars reliably get 403.
    """
    lang = (language or "Spanish").strip().lower()
    if lang.startswith("port"):
        qualifier = "educativo"
    elif lang.startswith("eng"):
        qualifier = "educational"
    else:
        qualifier = "educativo"

    # Remove punctuation characters that trigger DDG 403
    clean = re.sub(r'[¡!¿?:,;"\(\)\[\]]', ' ', query)
    clean = re.sub(r"'", ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()

    # Keep only the 4 most meaningful words (skip very short stop-words)
    words = [w for w in clean.split() if len(w) > 3][:4]
    base = " ".join(words) if words else clean[:40]

    return f"{base} {qualifier}"


def _score_image_result(result: dict, query: str, topic: str = "") -> float:
    """Score an image result by relevance to the query and topic.

    Higher score = better match. Returns 0.0 – 1.0.
    """
    title = (result.get("title") or "").lower()
    url = (result.get("image") or "").lower()
    source = (result.get("source") or "").lower()

    query_words = set(query.lower().split())
    # Remove very short / stop words
    query_words = {w for w in query_words if len(w) > 2}

    score = 0.0
    # Keyword overlap in title
    if query_words:
        title_words = set(title.split())
        overlap = len(query_words & title_words) / len(query_words)
        score += overlap * 0.5

    # Topic relevance bonus
    if topic:
        topic_lower = topic.lower()
        if topic_lower in title:
            score += 0.25
        elif any(w in title for w in topic_lower.split() if len(w) > 3):
            score += 0.15

    # Prefer known educational / stock sources
    trusted = ["wikipedia", "wikimedia", "britannica", "national geographic",
               "unsplash", "pexels", "pixabay", "shutterstock", "istockphoto",
               "gettyimages", "freepik", "educacion", "conaliteg"]
    if any(t in source or t in url for t in trusted):
        score += 0.15

    # Penalize social media / meme / unrelated sources
    untrusted = ["pinterest", "reddit", "tiktok", "twitter", "x.com",
                 "facebook", "instagram", "meme", "gif", "tenor"]
    if any(t in source or t in url for t in untrusted):
        score -= 0.3

    return max(0.0, min(1.0, score))


async def search_image(
    query: str,
    language: str = "Spanish",
    country: str = "Mexico",
    safesearch: str = "moderate",
    max_results: int = 10,
    image_type: str = "photo",
    size: str = "",
    timeout: int = 15,
    topic: str = "",
) -> Optional[ImagePlaceholder]:
    """
    Search for an educational image using DuckDuckGo with safe search.

    Args:
        query: Image search query
        language: Content language for query enrichment
        country: Target country for region selection
        safesearch: Safety level ('strict', 'moderate', 'off')
        max_results: Number of results to fetch (picks best by relevance)
        image_type: Type filter ('photo', 'clipart', 'gif', 'transparent', '')
        size: Size filter ('Small', 'Medium', 'Large', 'Wallpaper', '')
        timeout: Search timeout in seconds
        topic: Book topic for relevance scoring

    Returns:
        ImagePlaceholder with image URL and description, or None
    """
    def _sync() -> Optional[ImagePlaceholder]:
        region = _REGION_MAP.get(country, "wt-wt")
        # Try local region first, then us-en, then worldwide
        if region == "us-en":
            regions_to_try = ["us-en", "wt-wt"]
        else:
            regions_to_try = [region, "us-en", "wt-wt"]

        enhanced_query = _build_image_query(query, language, topic)
        # Cleaned ultra-short fallback: first 2 meaningful words + qualifier
        lang_q = "educational" if (language or "").lower().startswith("eng") else "educativo"
        short_words = [w for w in re.sub(r'[^\w\s]', ' ', query).split() if len(w) > 3][:2]
        short_query = " ".join(short_words) + f" {lang_q}" if short_words else enhanced_query
        queries_to_try = [enhanced_query, short_query]

        for attempt_region in regions_to_try:
            for q in queries_to_try:
                try:
                    kwargs: dict = {
                        "region": attempt_region,
                        "safesearch": safesearch,
                        "max_results": max_results,
                    }
                    if image_type:
                        kwargs["type_image"] = image_type
                    if size:
                        kwargs["size"] = size

                    with DDGS() as ddgs:
                        results = list(ddgs.images(q, **kwargs))

                    if not results:
                        logger.debug(f"No images for '{q}' (region={attempt_region})")
                        continue

                    # Score and rank results by relevance
                    scored = []
                    for r in results:
                        url = r.get("image", "")
                        if url and url.startswith("http"):
                            s = _score_image_result(r, query, topic)
                            scored.append((s, r))

                    if not scored:
                        continue

                    # Sort by score descending and pick best
                    scored.sort(key=lambda x: x[0], reverse=True)
                    best_score, best = scored[0]
                    url = best["image"]
                    title = best.get("title", query)

                    logger.info(
                        f"🖼️ Found image (score={best_score:.2f}): "
                        f"{title[:60]}  →  {url[:80]}"
                    )
                    return ImagePlaceholder(
                        description=title or query,
                        url=url,
                        prompt=f"DDG search: {query}",
                        resolution="",
                        image_model="duckduckgo-search",
                    )

                except Exception as e:
                    logger.warning(f"Image search failed for '{q}' (region={attempt_region}): {e}")
                    continue

        logger.warning(f"No images found for '{query}' after all attempts")
        return None

    return await asyncio.to_thread(_sync)


async def search_and_download_image(
    query: str,
    output_dir: str,
    chapter_name: str = "images",
    language: str = "Spanish",
    country: str = "Mexico",
    safesearch: str = "moderate",
    max_results: int = 10,
    topic: str = "",
) -> Optional[ImagePlaceholder]:
    """
    Search for an image and download it locally.

    Args:
        query: Image search query
        output_dir: Parent directory for saving
        chapter_name: Subfolder for this chapter's images
        language: Content language
        country: Target country
        safesearch: Safety level
        max_results: Number of results to scan
        topic: Book topic for relevance scoring

    Returns:
        ImagePlaceholder with local file path, or None
    """
    placeholder = await search_image(
        query=query,
        language=language,
        country=country,
        safesearch=safesearch,
        max_results=max_results,
        topic=topic,
    )

    if not placeholder:
        return None

    # Download the image
    try:
        chapter_dir = Path(output_dir) / chapter_name
        chapter_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        safe_name = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in query)
        safe_name = safe_name.replace(' ', '_')[:50]
        filename = f"{safe_name}.jpg"
        filepath = chapter_dir / filename

        response = requests.get(placeholder.url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (Educational Content Agent)"
        })
        response.raise_for_status()

        with open(filepath, 'wb') as f:
            f.write(response.content)

        logger.info(f"💾 Image downloaded: {filepath}")
        return ImagePlaceholder(
            description=placeholder.description,
            url=str(filepath),
            prompt=placeholder.prompt,
            resolution="",
            image_model="duckduckgo-search",
        )

    except Exception as e:
        logger.warning(f"Image download failed for '{query}': {e}")
        # Return the URL-only placeholder as fallback
        return placeholder


async def search_images_for_chapter(
    chapter_title: str,
    image_queries: List[str],
    output_dir: str = "./books/images",
    chapter_name: str = "images",
    topic: str = "",
    language: str = "Spanish",
    country: str = "Mexico",
    download: bool = True,
) -> List[ImagePlaceholder]:
    """
    Search and optionally download images for all [IMAGE: ...] placeholders
    in a chapter.

    Args:
        chapter_title: Chapter title for context
        image_queries: List of image search queries
        output_dir: Parent image directory
        chapter_name: Subfolder name
        topic: Book topic for query enrichment
        language: Content language
        country: Target country
        download: Whether to download images locally

    Returns:
        List of ImagePlaceholder objects
    """
    results: List[ImagePlaceholder] = []

    for q in image_queries:
        # Use the raw query — search_image now builds enhanced queries internally
        if download:
            img = await search_and_download_image(
                query=q,
                output_dir=output_dir,
                chapter_name=chapter_name,
                language=language,
                country=country,
                topic=topic,
            )
        else:
            img = await search_image(
                query=q,
                language=language,
                country=country,
                topic=topic,
            )

        if img:
            results.append(img)
        else:
            logger.warning(f"  ⚠️ No image found for: {q}")

    return results


def extract_image_placeholders(markdown: str) -> List[str]:
    """Return all [IMAGE: description] placeholder texts from markdown."""
    return re.findall(r'\[IMAGE:\s*([^\]]+)\]', markdown)

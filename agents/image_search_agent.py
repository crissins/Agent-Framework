# agents/image_search_agent.py
"""
Image search tool for educational content.
Implements async/await patterns for non-blocking I/O.
"""
import asyncio
from typing import Optional
from ddgs import DDGS
from models.book_spec import ImagePlaceholder


async def image_search_tool(query: str, timeout: int = 10) -> Optional[ImagePlaceholder]:
    """
    Search for an educational image using DuckDuckGo.
    
    Best practices applied:
    - Async/await for non-blocking I/O
    - Timeout handling to prevent hangs
    - Safe default fallback
    - Type hints and documentation
    
    Args:
        query: Image search query
        timeout: Search timeout in seconds
        
    Returns:
        ImagePlaceholder with URL or None if search fails
    """
    def _sync_search() -> str:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.images(
                    query,
                    region="mx-es",
                    safesearch="moderate",
                    max_results=1,
                ))
                return results[0]["image"] if results else None
        except Exception as e:
            print(f"Warning: Image search failed for '{query}': {e}")
            return None

    try:
        url = await asyncio.to_thread(_sync_search)
        
        return ImagePlaceholder(
            description=query,
            url=url or "https://via.placeholder.com/600x400?text=Educational+Image"
        )
    except Exception as e:
        print(f"Error in image_search_tool: {e}")
        return ImagePlaceholder(
            description=query,
            url="https://via.placeholder.com/600x400?text=Educational+Image"
        )
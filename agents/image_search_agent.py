# agents/image_search_agent.py
import asyncio
from ddgs import DDGS
from models.book_spec import ImagePlaceholder

async def image_search_tool(query: str) -> ImagePlaceholder:
    def _sync_search():
        with DDGS() as ddgs:
            results = ddgs.images(
                keywords=query,
                region="mx-es",
                safesearch="moderate",
                max_results=1
            )
            return results[0]["image"] if results else "https://via.placeholder.com/600x400?text=No+Image"

    url = await asyncio.to_thread(_sync_search)
    return ImagePlaceholder(description=query, url=url)
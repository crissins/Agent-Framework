import asyncio
import os
from dotenv import load_dotenv

from agents.greet_agent import create_greet_agent, get_book_request
from agents.curriculum_agent import create_curriculum_agent, generate_curriculum
from agents.chapter_agent import create_chapter_agent, generate_chapter
from agents.image_search_agent import create_image_search_agent

from agent_framework.observability import setup_observability
setup_observability(enable_sensitive_data=True)

load_dotenv()

async def main():
    # Step 1: Get book request
    greet_agent = await create_greet_agent()
    request = await get_book_request(greet_agent)
    print("✅ Book Request:", request)

    # Step 2: Generate curriculum
    curriculum_agent = await create_curriculum_agent()
    curriculum = await generate_curriculum(curriculum_agent, request)
    print("✅ Curriculum Generated:", curriculum.title)

    # Step 3: Generate first chapter (demo)
    chapter_agent = await create_chapter_agent()
    context = {
        "age": request.target_audience_age,
        "country": request.country,
        "learning_method": request.learning_method,
        "language": request.language
    }
    chapter_content = await generate_chapter(chapter_agent, curriculum.chapters[0], context)
    print("✅ Chapter Generated:", chapter_content.chapter_title[:50] + "...")

    # Step 4: Simulate image search for first placeholder
    if chapter_content.image_placeholders:
        image_agent = await create_image_search_agent()
        img_result = await search_image(image_agent, chapter_content.image_placeholders[0])
        print("✅ Image Found:", img_result.image_url)

if __name__ == "__main__":
    asyncio.run(main())
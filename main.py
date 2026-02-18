"""
Main orchestration for book generation workflow.
Demonstrates Microsoft Agent Framework best practices:
- Proper async/await with context managers
- Sequential agent orchestration with error handling
- Structured logging and observability
- Uses GitHub Models by default (Qwen available via Streamlit UI only)
"""
import asyncio
import os
from dotenv import load_dotenv

from agents.greet_agent import create_greet_agent, get_book_request
from agents.curriculum_agent import create_curriculum_agent, generate_curriculum
from agents.chapter_agent import create_chapter_agent, generate_chapter
from agents.qwen_image_agent import generate_image_with_qwen
from config import validate_api_keys

from agent_framework.observability import setup_observability

# Enable observability for production monitoring
setup_observability(enable_sensitive_data=False)

load_dotenv()


async def main():
    """
    Main workflow orchestration using GitHub Models.
    
    Best practices demonstrated:
    - Sequential agent creation and usage
    - Proper error handling with fallbacks
    - Observability enabled for debugging
    - Type-safe operations with validation
    
    Note: For Qwen models, use the Streamlit UI (streamlit run app.py)
    and toggle the "Use Qwen Models" checkbox.
    """
    # Validate API keys before starting (GitHub Models)
    is_valid, message = validate_api_keys(use_qwen=False)
    print(message)
    if not is_valid:
        print(f"❌ API configuration required. Please set up your environment.")
        return
    
    print(f"🔄 Using model provider: GitHub Models\n")
    
    try:
        # Step 1: Get book request from user
        print("📚 Step 1: Gathering book requirements...")
        greet_agent = await create_greet_agent(use_qwen=False)
        request = await get_book_request(greet_agent)
        
        if not request:
            print("❌ Failed to parse book request")
            return
            
        print(f"✅ Book Request: {request.topic} ({request.target_audience_age} years old, {request.country})")

        # Step 2: Generate curriculum structure
        print("\n📖 Step 2: Designing curriculum...")
        curriculum_agent = await create_curriculum_agent(use_qwen=False)
        curriculum = await generate_curriculum(curriculum_agent, request)
        
        if not curriculum:
            print("❌ Failed to generate curriculum")
            return
            
        print(f"✅ Curriculum: '{curriculum.title}' with {len(curriculum.chapters)} chapters")

        # Step 3: Generate first chapter as demo
        print("\n✍️ Step 3: Writing first chapter...")
        chapter_agent = await create_chapter_agent(use_qwen=False)
        
        context = {
            "age": request.target_audience_age,
            "country": request.country,
            "learning_method": request.learning_method,
            "language": request.language,
            "pages_per_chapter": request.pages_per_chapter
        }
        
        first_chapter = curriculum.chapters[0]
        chapter_content = await generate_chapter(chapter_agent, first_chapter, context)
        
        if not chapter_content:
            print("❌ Failed to generate chapter")
            return
            
        print(f"✅ Chapter Generated: {chapter_content.chapter_title}")

        # Step 4: Generate images using Qwen-Image-Max (demo)
        if chapter_content.image_placeholders:
            print("\n🎨 Step 4: Generating illustrations with Qwen-Image-Max...")
            for i, placeholder_text in enumerate(chapter_content.image_placeholders[:2], 1):  # Demo: first 2 images
                print(f"\n   Image {i}/2: {placeholder_text[:60]}...")
                img_result = await generate_image_with_qwen(
                    prompt=placeholder_text,
                    style="educational",
                    size="1664*928"
                )
                if img_result:
                    print(f"   ✅ Generated: {img_result.url[:80]}...")
                else:
                    print(f"   ⚠️ Image generation failed for: {placeholder_text}")

        print("\n✨ Book generation workflow completed successfully!")
        print(f"Generated content for: {len(curriculum.chapters)} chapters")
        print("\n💡 TIP: To generate images for all chapters, increase the polling in Step 4")

    except Exception as e:
        print(f"❌ Workflow error: {e}")
        raise


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 LATAM Book Generator with AI - Agent Framework")
    print("=" * 60)
    print("📝 Using GitHub Models (free tier)")
    print("💡 For Qwen models, run: streamlit run app.py")
    print("=" * 60 + "\n")
    
    asyncio.run(main())


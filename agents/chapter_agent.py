# agents/chapter_agent.py
import re
import os
from typing import Optional, Dict, Any
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from models.book_spec import ChapterOutline, ChapterContent
from config import get_model_config


async def create_chapter_agent(use_qwen: bool = False) -> ChatAgent:
    """
    Create a chapter writing agent using either GitHub Models or Qwen.
    
    Args:
        use_qwen: If True, use Qwen models via DashScope; if False, use GitHub Models
    
    Implements Microsoft Agent Framework best practices:
    - Uses OpenAIChatClient with specified endpoint
    - Clear, minimal instructions to avoid hallucinations
    - Respects token limits and learning method
    - Supports both development and production workflows
    """
    config = get_model_config(use_qwen)
    client = OpenAIChatClient(
        api_key=os.getenv(config["api_key_env"], ""),
        base_url=config["base_url"],
        model_id=config["model_id"]
    )
    
    agent = ChatAgent(
        chat_client=client,
        name="ChapterAgent",
        instructions=(
            "You are an expert in creating interactive, engaging educational content for children in LATAM. "
            "IMPORTANT: You MUST respond ONLY in the language specified by the user.\n\n"
            "Write chapters that are age-appropriate, culturally relevant, and follow the specified learning method.\n\n"
            "REQUIRED CHAPTER STRUCTURE (in this exact order):\n"
            "1. **Concepto Clave**: Simple explanation of the topic\n"
            "2. **Ejemplo en tu Vida**: How this applies to the student's daily life (home, school, community)\n"
            "3. **Pregunta para Pensar**: An open-ended reflection question\n"
            "4. **Actividad en Familia**: An offline family activity (no technology required)\n"
            "5. **Actividad en la Escuela**: A classroom group activity\n"
            "6. **Pregunta para una IA**: 1-2 suggested questions for AI assistants for deeper learning\n\n"
            "FORMATTING GUIDELINES:\n"
            "- Use Markdown with ## headers, **bold**, and lists\n"
            "- Include [IMAGE: description] placeholders where visuals help\n"
            "- Add [VIDEO: topic] tags for supplementary videos\n"
            "- Use LaTeX for formulas: $$formula$$\n"
            "- Keep language simple and engaging for the target age\n"
            "- Respect local culture and values\n"
            "- ALL output MUST be in the specified language"
        ),
    )
    return agent


async def generate_chapter(
    agent: ChatAgent,
    outline: ChapterOutline,
    context: Dict[str, Any]
) -> Optional[ChapterContent]:
    """
    Generate a complete chapter using streaming for real-time feedback.
    
    Demonstrates best practices:
    - Structured context passing
    - Error handling for generation failures
    - Streaming support for large content
    
    Args:
        agent: The chapter writing agent
        outline: Chapter outline with title and summary
        context: Dictionary with age, country, learning_method, language, pages_per_chapter
        
    Returns:
        ChapterContent with markdown or None if generation fails
    """
    prompt = (
        f"Write a full chapter titled '{outline.title}' for a {context['age']}-year-old "
        f"in {context['country']}, using the {context['learning_method']} learning method.\n\n"
        f"LANGUAGE REQUIREMENT: Respond ENTIRELY in {context['language']}. "
        f"Every section header, paragraph, and sentence MUST be in {context['language']}.\n\n"
        f"Chapter Summary: {outline.summary}\n\n"
        f"Target length: approximately {context.get('pages_per_chapter', 5)} pages.\n\n"
        f"Make the content interactive, engaging, and locally relevant to {context['country']}. "
        f"Follow the required structure exactly. "
        f"Remember: ALL output must be in {context['language']}."
    )
    
    try:
        # Log input
        print(f"\n{'='*80}")
        print(f"🎯 LLM INPUT - CHAPTER AGENT")
        print(f"{'='*80}")
        print(f"Chapter: {outline.title}")
        print(f"Summary: {outline.summary}")
        print(f"Context: Age={context['age']}, Country={context['country']}, Method={context['learning_method']}, Language={context['language']}")
        print(f"Prompt:\n{prompt}\n")
        print(f"Max Tokens: 4000")
        print(f"{'='*80}\n")
        
        response = await agent.run(
            prompt,
            max_tokens=4000
        )
        
        # Extract placeholders
        image_placeholders = _extract_image_placeholders(response.text)
        
        # Log output
        print(f"\n{'='*80}")
        print(f"✅ LLM OUTPUT - CHAPTER AGENT")
        print(f"{'='*80}")
        print(f"Chapter: {outline.title}")
        print(f"Content Length: {len(response.text)} characters")
        print(f"Image Placeholders Found: {len(image_placeholders)}")
        for i, placeholder in enumerate(image_placeholders, 1):
            print(f"  {i}. {placeholder[:60]}...")
        print(f"Response Preview (first 200 chars):\n{response.text[:200]}...\n")
        print(f"{'='*80}\n")
        
        return ChapterContent(
            chapter_title=outline.title,
            markdown_content=response.text,
            image_placeholders=image_placeholders
        )
    except Exception as e:
        print(f"\n❌ Error generating chapter '{outline.title}': {e}\n")
        import traceback
        print(traceback.format_exc())
        return None


def _extract_image_placeholders(markdown: str) -> list[str]:
    """
    Extract image placeholder descriptions from generated markdown.
    
    Helps coordinate with image search agent.
    
    Args:
        markdown: Generated chapter content
        
    Returns:
        List of image description strings
    """
    pattern = r"\[IMAGE:\s*([^\]]+)\]"
    return re.findall(pattern, markdown)
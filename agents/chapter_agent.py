# agents/chapter_agent.py
import re
import os
import logging
from typing import Optional, Dict, Any
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from models.book_spec import ChapterOutline, ChapterContent
from config import get_model_config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_chapter_agent(use_qwen: bool = False, model_id: str | None = None) -> ChatAgent:
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
    resolved_model_id = model_id if model_id else config.get("model_id")
    client = OpenAIChatClient(
        api_key=os.getenv(config["api_key_env"], ""),
        base_url=config["base_url"],
        model_id=resolved_model_id
    )
    
    agent = ChatAgent(
        chat_client=client,
        name="ChapterAgent",
        instructions=(
            "You are an expert in creating interactive, engaging educational content for children in LATAM. "
            "IMPORTANT: You MUST respond ONLY in the language specified by the user.\n\n"
            "Write chapters that are age-appropriate, culturally relevant, and follow the specified learning method.\n\n"
            "CHAPTER STRUCTURE — IMPORTANT: vary the structure between chapters!\n"
            "Every chapter MUST include the REQUIRED sections, but OPTIONAL sections should rotate\n"
            "so that each chapter feels fresh and different.\n\n"
            "REQUIRED SECTIONS (always include all of these):\n"
            "  • **Concepto Clave** — Clear, simple explanation of the main topic\n"
            "  • **Ejemplo en tu Vida** — How the topic applies to the student's daily life\n"
            "  • **Pregunta para Pensar** — An open-ended reflection question\n\n"
            "OPTIONAL SECTIONS (pick 2-3 per chapter, vary your choices):\n"
            "  • **Actividad en Familia** — An offline family activity (no technology needed)\n"
            "  • **Actividad en la Escuela** — A classroom group activity\n"
            "  • **Pregunta para una IA** — 1-2 suggested questions for AI assistants\n"
            "  • **Sabías que…** — A fun, surprising fact related to the topic\n"
            "  • **Desafío Creativo** — A creative challenge (drawing, writing, building)\n"
            "  • **Conexión con el Mundo** — How the topic connects to global issues\n"
            "  • **Mini Experimento** — A simple hands-on experiment or observation\n"
            "  • **Debate en Clase** — A discussion topic with two sides to argue\n"
            "  • **Rincón del Inventor** — Invent or design something related to the topic\n"
            "  • **Historia Corta** — A very short story illustrating the concept\n\n"
            "FORMATTING GUIDELINES:\n"
            "- Use Markdown with ## headers, **bold**, and lists\n"
            "- Include [IMAGE: description] placeholders where visuals help\n"
            "- Add [VIDEO: topic] tags for supplementary videos\n"
            "- Use LaTeX for formulas: $$formula$$\n"
            "- Keep language simple and engaging for the target age\n"
            "- Respect local culture and values\n"
            "- ALL output MUST be in the specified language\n"
            "- Do NOT repeat the same optional section combination in every chapter"
        ),
    )
    return agent


from utils.retry import async_retry

@async_retry(max_retries=3, base_delay=2.0, max_delay=60.0)
async def _run_agent_with_retry(agent: ChatAgent, prompt: str, options: dict):
    """Helper to run agent with retry logic"""
    return await agent.run(prompt, **options)


async def generate_chapter(
    agent: ChatAgent,
    outline: ChapterOutline,
    context: Dict[str, Any],
    max_tokens: int = 4000,
    images_per_chapter: int = 0,
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
    # Build image placeholder instruction based on images_per_chapter
    if images_per_chapter > 0:
        image_instruction = (
            f"5. Add EXACTLY {images_per_chapter} [IMAGE: detailed description] placeholder(s) "
            f"spread throughout the chapter where visuals would genuinely help understanding. "
            f"Each [IMAGE: ...] MUST have a UNIQUE, specific description \u2014 "
            f"never repeat the same description. Make each one describe a DIFFERENT aspect "
            f"of the topic (e.g. a diagram, a scene, a comparison, a close-up of an object).\n"
        )
    else:
        image_instruction = "5. Do NOT add any [IMAGE: ...] placeholders.\n"

    prompt = (
        f"=== CHAPTER WRITING REQUEST ===\n\n"
        f"### CHAPTER INFO ###\n"
        f"- Title: {outline.title}\n"
        f"- Summary: {outline.summary}\n\n"
        f"### AUDIENCE ###\n"
        f"- Age: {context['age']} years old\n"
        f"- Country: {context['country']}\n"
        f"- Language: {context['language']}\n"
        f"- Learning Method: {context['learning_method']}\n\n"
        f"### TASK STEPS ###\n"
        f"1. Start with the **Concepto Clave**: explain the core topic clearly using an analogy "
        f"or comparison a {context['age']}-year-old in {context['country']} would immediately understand\n"
        f"2. Write **Ejemplo en tu Vida**: describe a concrete, vivid scenario from the student's "
        f"daily life in {context['country']} that connects to this concept\n"
        f"3. Craft **Pregunta para Pensar**: pose an open-ended question with no single right answer "
        f"that encourages critical thinking\n"
        f"4. Choose 2-3 OPTIONAL sections that best fit THIS chapter's specific topic \u2014 "
        f"do NOT reuse the same combination from other chapters. Be creative!\n"
        + image_instruction +
        f"6. Add [VIDEO: specific topic] tags where a video would complement the written content\n\n"
        f"### LENGTH & DEPTH ###\n"
        f"Target approximately {context.get('pages_per_chapter', 5)} pages. Each section should be "
        f"substantial and detailed \u2014 not just 1-2 sentences. Use examples, mini-stories, and "
        f"real-world connections to bring the content alive.\n\n"
        f"### LANGUAGE REQUIREMENT ###\n"
        f"Write ENTIRELY in {context['language']}. Every heading, paragraph, question, and instruction "
        f"MUST be in {context['language']}. Use culturally appropriate references for {context['country']}."
    )
    
    try:
        # Log input
        logger.info(f"🎯 LLM INPUT - CHAPTER AGENT")
        logger.info(f"Chapter: {outline.title}")
        logger.info(f"Summary: {outline.summary}")
        logger.info(f"Context: Age={context['age']}, Country={context['country']}, Method={context['learning_method']}, Language={context['language']}")
        logger.info(f"Prompt:\n{prompt}\n")
        logger.info(f"Max Tokens: {max_tokens}")
        
        # Use the retrying helper
        response = await _run_agent_with_retry(
            agent, 
            prompt, 
            options={"max_tokens": max_tokens}
        )
        
        # Extract placeholders
        image_placeholders = _extract_image_placeholders(response.text)
        
        # Log output
        logger.info(f"✅ LLM OUTPUT - CHAPTER AGENT")
        logger.info(f"Chapter: {outline.title}")
        logger.info(f"Content Length: {len(response.text)} characters")
        logger.info(f"Image Placeholders Found: {len(image_placeholders)}")
        for i, placeholder in enumerate(image_placeholders, 1):
            logger.info(f"  {i}. {placeholder[:60]}...")
        logger.info(f"Response Preview (first 200 chars):\n{response.text[:200]}...\n")
        
        return ChapterContent(
            chapter_title=outline.title,
            markdown_content=response.text,
            image_placeholders=image_placeholders
        )
    except Exception as e:
        logger.error(f"❌ Error generating chapter '{outline.title}': {e}")
        import traceback
        logger.error(traceback.format_exc())
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
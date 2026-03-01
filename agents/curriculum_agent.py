import os
import logging
from typing import Optional
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from models.book_spec import BookRequest, Curriculum
from config import get_model_config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_curriculum_agent(
    use_qwen: bool = False,
    model_id: str | None = None,
    provider: str | None = None,
) -> ChatAgent:
    """
    Create a curriculum design agent using either GitHub Models or Qwen.

    Args:
        use_qwen:  Legacy bool — True → Qwen, False → GitHub (ignored when provider is set)
        model_id:  Override the default model ID.
        provider:  Explicit provider string: 'github' | 'qwen' | 'claude' | 'azure'.
                   When supplied this takes priority over use_qwen AND the MODEL_PROVIDER
                   env-var, which prevents cross-thread contamination in batch runs.

    Implements Microsoft Agent Framework best practices:
    - Uses OpenAIChatClient with specified endpoint
    - Provides clear, focused instructions without vague directives
    - Returns typed Agent instance
    - Supports both development and production workflows
    """
    config = get_model_config(use_qwen, provider=provider)
    # Allow explicit model override
    resolved_model_id = model_id if model_id else config.get("model_id")
    client = OpenAIChatClient(
        api_key=os.getenv(config["api_key_env"], ""),
        base_url=config["base_url"],
        model_id=resolved_model_id
    )
    
    agent = ChatAgent(
        chat_client=client,
        name="CurriculumAgent",
        instructions=(
            "### CONTEXT ###\n"
            "You are a world-class curriculum designer with 20+ years of experience creating "
            "award-winning educational content for children across Latin America, Europe, and Asia. "
            "You specialize in age-appropriate, culturally sensitive educational material that "
            "follows modern pedagogical methods (Montessori, Scandinavian, Project-Based, etc.).\n\n"
            "### OBJECTIVE ###\n"
            "Design a structured, well-sequenced educational curriculum with exactly these components:\n"
            "  1. 'title' — A compelling, memorable, age-appropriate book title that sparks curiosity\n"
            "  2. 'description' — A concise overview (2-3 sentences) explaining the curriculum's goals and approach\n"
            "  3. 'chapters' — An ordered array of chapter outlines, each containing ONLY:\n"
            "       - 'title': A clear, engaging chapter title\n"
            "       - 'summary': A 2-3 sentence description of learning objectives and key topics\n\n"
            "### STYLE ###\n"
            "Write like an experienced educational publisher — professional yet warm, with titles "
            "that ignite curiosity and summaries that clearly convey learning value.\n\n"
            "### CONSTRAINTS ###\n"
            "- Each chapter MUST have ONLY 'title' and 'summary' — NO page counts, durations, or extra metadata\n"
            "- Chapters must follow a logical learning progression: foundational → intermediate → advanced\n"
            "- Each chapter should build upon knowledge from previous chapters\n"
            "- Follow the specified pedagogical/learning method principles throughout\n"
            "- Ensure cultural relevance and sensitivity for the target country and age group\n\n"
            "### RESPONSE FORMAT ###\n"
            "- Respond EXCLUSIVELY in the language specified by the user\n"
            "- ALL fields (title, description, every chapter title, every summary) MUST be in the specified language\n"
            "- Return valid structured data matching the Curriculum JSON schema"
        ),
    )
    return agent


from utils.retry import async_retry

@async_retry(max_retries=3, base_delay=2.0, max_delay=60.0)
async def _run_agent_with_retry(agent: ChatAgent, prompt: str, options: dict):
    """Helper to run agent with retry logic"""
    return await agent.run(prompt, **options)


async def generate_curriculum(agent: ChatAgent, request: BookRequest, max_tokens: int = 2000) -> Optional[Curriculum]:
    """
    Generate a structured curriculum for the book.
    
    Demonstrates best practice error handling and structured output parsing.
    
    Args:
        agent: The curriculum agent instance
        request: BookRequest containing specifications
        
    Returns:
        Curriculum object or None if generation fails
    """
    prompt = (
        f"=== CURRICULUM DESIGN REQUEST ===\n\n"
        f"### TOPIC ###\n{request.topic}\n\n"
        f"### TARGET AUDIENCE ###\n"
        f"- Age: {request.target_audience_age} years old\n"
        f"- Country: {request.country}\n"
        f"- Language: {request.language}\n\n"
        f"### PEDAGOGICAL METHOD ###\n{request.learning_method}\n\n"
        f"### TASK STEPS ###\n"
        f"1. Analyze the topic and identify key concepts suitable for {request.target_audience_age}-year-olds\n"
        f"2. Consider what {request.target_audience_age}-year-olds in {request.country} already know about this topic\n"
        f"3. Structure exactly {request.num_chapters} chapters in a logical learning progression (simple → complex)\n"
        f"4. For each chapter, write a clear title and a 2-3 sentence summary of learning objectives\n"
        f"5. Ensure cultural references and examples are relevant to {request.country}\n\n"
        f"### LANGUAGE REQUIREMENT ###\n"
        f"Respond ENTIRELY in {request.language}. Every field — title, description, "
        f"all chapter titles, all summaries — MUST be written in {request.language}.\n\n"
        f"### QUALITY CRITERIA ###\n"
        f"- Titles should be engaging and spark curiosity in {request.target_audience_age}-year-olds\n"
        f"- Each chapter must build upon knowledge from the previous one\n"
        f"- Content must be age-appropriate and culturally relevant for {request.country}\n"
        f"- Follow the {request.learning_method} learning method principles throughout"
    )
    
    try:
        # Log input
        logger.info(f"🎯 LLM INPUT - CURRICULUM AGENT")
        logger.info(f"Prompt:\n{prompt}\n")
        logger.info(f"Response Format: Curriculum (JSON)")
        logger.info(f"Max Tokens: {max_tokens}")
        
        # Use the retrying helper
        response = await _run_agent_with_retry(
            agent, 
            prompt, 
            options={"response_format": Curriculum, "max_tokens": max_tokens}
        )
        
        # Log output
        logger.info(f"✅ LLM OUTPUT - CURRICULUM AGENT")
        logger.info(f"Curriculum Generated:")
        logger.info(f"  Title: {response.value.title}")
        logger.info(f"  Description: {response.value.description}")
        logger.info(f"  Chapters: {len(response.value.chapters)}")
        for i, ch in enumerate(response.value.chapters, 1):
            logger.info(f"    {i}. {ch.title}")
        
        return response.value
    except Exception as e:
        logger.error(f"❌ Error generating curriculum: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
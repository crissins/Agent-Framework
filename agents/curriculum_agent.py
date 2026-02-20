import os
from typing import Optional
from agent_framework import RawAgent
from agent_framework.openai import OpenAIChatClient
from models.book_spec import BookRequest, Curriculum
from config import get_model_config


async def create_curriculum_agent(use_qwen: bool = False, model_id: str | None = None) -> RawAgent:
    """
    Create a curriculum design agent using either GitHub Models or Qwen.
    
    Args:
        use_qwen: If True, use Qwen models via DashScope; if False, use GitHub Models
    
    Implements Microsoft Agent Framework best practices:
    - Uses OpenAIChatClient with specified endpoint
    - Provides clear, focused instructions without vague directives
    - Returns typed Agent instance
    - Supports both development and production workflows
    """
    config = get_model_config(use_qwen)
    # Allow explicit model override when using Qwen
    resolved_model_id = model_id if model_id else config.get("model_id")
    client = OpenAIChatClient(
        api_key=os.getenv(config["api_key_env"], ""),
        base_url=config["base_url"],
        model_id=resolved_model_id
    )
    
    agent = RawAgent(
        client=client,
        name="CurriculumAgent",
        instructions=(
            "You are an expert curriculum designer for LATAM K-12 education. "
            "IMPORTANT: You MUST respond ONLY in the language specified by the user. "
            "Your task: Create a structured curriculum with exactly these components:\n"
            "1. title: A compelling, age-appropriate title (IN THE SPECIFIED LANGUAGE)\n"
            "2. description: A brief overview of the curriculum (IN THE SPECIFIED LANGUAGE)\n"
            "3. chapters: An array of chapter outlines, each with only 'title' and 'summary' (IN THE SPECIFIED LANGUAGE)\n\n"
            "IMPORTANT CONSTRAINTS:\n"
            "- Each chapter must have ONLY title and summary fields\n"
            "- Do NOT include page counts, durations, or other metadata\n"
            "- Ensure cultural relevance for the target country and age group\n"
            "- Follow the specified learning method principles\n"
            "- ALL output (title, description, chapter titles, summaries) MUST be in the specified language"
        ),
    )
    return agent


from utils.retry import async_retry

@async_retry(max_retries=3, base_delay=2.0, max_delay=60.0)
async def _run_agent_with_retry(agent: RawAgent, prompt: str, options: dict):
    """Helper to run agent with retry logic"""
    return await agent.run(prompt, options=options)


async def generate_curriculum(agent: RawAgent, request: BookRequest) -> Optional[Curriculum]:
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
        f"Design a book curriculum for '{request.topic}' "
        f"for {request.target_audience_age}-year-olds in {request.country}, "
        f"using the {request.learning_method} learning method.\n\n"
        f"LANGUAGE REQUIREMENT: Respond ENTIRELY in {request.language}. "
        f"Every field (title, description, chapter titles, summaries) MUST be in {request.language}.\n\n"
        f"Create exactly {request.num_chapters} chapters with clear learning objectives. "
        f"Ensure each chapter builds upon the previous one. "
        f"All content must be culturally appropriate for {request.country}."
    )
    
    try:
        # Log input
        print(f"\n{'='*80}")
        print(f"🎯 LLM INPUT - CURRICULUM AGENT")
        print(f"{'='*80}")
        print(f"Prompt:\n{prompt}\n")
        print(f"Response Format: Curriculum (JSON)")
        print(f"Max Tokens: 2000")
        print(f"{'='*80}\n")
        
        # Use the retrying helper
        response = await _run_agent_with_retry(
            agent, 
            prompt, 
            options={"response_format": Curriculum, "max_tokens": 2000}
        )
        
        # Log output
        print(f"\n{'='*80}")
        print(f"✅ LLM OUTPUT - CURRICULUM AGENT")
        print(f"{'='*80}")
        print(f"Curriculum Generated:")
        print(f"  Title: {response.value.title}")
        print(f"  Description: {response.value.description}")
        print(f"  Chapters: {len(response.value.chapters)}")
        for i, ch in enumerate(response.value.chapters, 1):
            print(f"    {i}. {ch.title}")
        print(f"{'='*80}\n")
        
        return response.value
    except Exception as e:
        print(f"\n❌ Error generating curriculum: {e}\n")
        import traceback
        print(traceback.format_exc())
        return None
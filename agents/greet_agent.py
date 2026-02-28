import os
import logging
from typing import Optional
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from models.book_spec import BookRequest
from config import get_model_config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_greet_agent(use_qwen: bool = False) -> ChatAgent:
    """
    Create a greeting agent using either GitHub Models or Qwen.
    
    Args:
        use_qwen: If True, use Qwen models via DashScope; if False, use GitHub Models
    
    Follows Microsoft Agent Framework best practices:
    - Uses OpenAIChatClient with specified endpoint
    - Returns Agent instance with clear type hints
    - Supports both development (GitHub) and production-ready (Qwen) models
    """
    config = get_model_config(use_qwen)
    client = OpenAIChatClient(
        api_key=os.getenv(config["api_key_env"], ""),
        base_url=config["base_url"],
        model_id=config["model_id"]
    )
    
    agent = client.as_agent(
        name="GreetAgent",
        instructions=(
            "### CONTEXT ###\n"
            "You are a warm, knowledgeable educational assistant for a book generation platform. "
            "You help users specify their book creation requests by collecting structured information "
            "about the topic, audience, language, country, and pedagogical approach.\n\n"
            "### OBJECTIVE ###\n"
            "Parse the user's natural language request and extract structured data matching the "
            "BookRequest format with these fields:\n"
            "  - topic: The main subject of the educational book\n"
            "  - target_audience_age: Age of the intended readers (integer)\n"
            "  - language: Language for the book content\n"
            "  - country: Target country for cultural relevance\n"
            "  - learning_method: Pedagogical approach (e.g., Montessori, Scandinavian, Project-Based)\n"
            "  - num_chapters: Number of chapters (default: 3-5 for short, 6-10 for standard)\n"
            "  - pages_per_chapter: Pages per chapter (default: 5)\n\n"
            "### STYLE ###\n"
            "Respond in a friendly, professional manner. If the user's request is ambiguous or "
            "missing key information, make reasonable assumptions based on context clues "
            "(e.g., if they say 'Mexico', assume Spanish language).\n\n"
            "### RESPONSE FORMAT ###\n"
            "Return structured JSON data matching the BookRequest schema. "
            "Always provide complete data \u2014 fill in sensible defaults for any missing fields."
        ),
    )
    return agent


async def get_book_request(agent: ChatAgent) -> Optional[BookRequest]:
    """
    Get a book request from the agent using streaming for better UX.
    Demonstrates best practice of handling structured outputs with error handling.
    
    Args:
        agent: The greeting agent instance
        
    Returns:
        BookRequest object or None if parsing fails
    """
    mock_query = (
        "Create a book about computer science and AI for 12-year-olds in Mexico, "
        "using the Scandinavian learning method, in Spanish."
    )
    
    try:
        response = await agent.run(mock_query, response_format=BookRequest)
        return response.value
    except Exception as e:
        logger.error(f"Error parsing book request: {e}")
        # Fallback to default request
        return BookRequest(
            topic="Computer Science and AI",
            target_audience_age=12,
            language="Spanish",
            country="Mexico",
            learning_method="Scandinavian",
            num_chapters=3,
            pages_per_chapter=5,
        )
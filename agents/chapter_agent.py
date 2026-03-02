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


# ── Language-specific section names ─────────────────────────────────────────
# Used in prompts so the LLM generates headings in the target language.
_SECTION_NAMES: Dict[str, Dict[str, str]] = {
    "Spanish": {
        "key_concept":  "Concepto Clave",
        "life_example": "Ejemplo en tu Vida",
        "think":        "Pregunta para Pensar",
        "family":       "Actividad en Familia",
        "school":       "Actividad en la Escuela",
        "ai_question":  "Pregunta para una IA",
        "did_you_know": "Sabías que…",
        "challenge":    "Desafío Creativo",
        "world":        "Conexión con el Mundo",
        "experiment":   "Mini Experimento",
        "debate":       "Debate en Clase",
        "inventor":     "Rincón del Inventor",
        "short_story":  "Historia Corta",
    },
    "English": {
        "key_concept":  "Key Concept",
        "life_example": "Example in Your Life",
        "think":        "Think About It",
        "family":       "Family Activity",
        "school":       "School Activity",
        "ai_question":  "Ask an AI",
        "did_you_know": "Did You Know…",
        "challenge":    "Creative Challenge",
        "world":        "Connection to the World",
        "experiment":   "Mini Experiment",
        "debate":       "Class Debate",
        "inventor":     "Inventor's Corner",
        "short_story":  "Short Story",
    },
    "Portuguese": {
        "key_concept":  "Conceito-Chave",
        "life_example": "Exemplo na Sua Vida",
        "think":        "Pergunta para Pensar",
        "family":       "Atividade em Família",
        "school":       "Atividade na Escola",
        "ai_question":  "Pergunta para uma IA",
        "did_you_know": "Você Sabia…",
        "challenge":    "Desafio Criativo",
        "world":        "Conexão com o Mundo",
        "experiment":   "Mini Experimento",
        "debate":       "Debate em Classe",
        "inventor":     "Canto do Inventor",
        "short_story":  "História Curta",
    },
    "French": {
        "key_concept":  "Concept Clé",
        "life_example": "Exemple dans Ta Vie",
        "think":        "Question de Réflexion",
        "family":       "Activité en Famille",
        "school":       "Activité en Classe",
        "ai_question":  "Demande à une IA",
        "did_you_know": "Le Savais-tu…",
        "challenge":    "Défi Créatif",
        "world":        "Connexion au Monde",
        "experiment":   "Mini Expérience",
        "debate":       "Débat en Classe",
        "inventor":     "Coin de l'Inventeur",
        "short_story":  "Courte Histoire",
    },
}
_DEFAULT_SECTION_NAMES = _SECTION_NAMES["English"]


def _get_section_names(language: str) -> Dict[str, str]:
    """Return section-name strings for the given language (falls back to English)."""
    return _SECTION_NAMES.get(language, _DEFAULT_SECTION_NAMES)


_MATH_KEYWORDS = [
    "matemáticas", "matematicas", "math", "álgebra", "algebra",
    "geometría", "geometria", "geometry", "fraccion", "fracciones",
    "fractions", "aritmética", "aritmetica", "arithmetic",
    "cálculo", "calculo", "calculus", "trigonometría", "trigonometria",
    "estadística", "estadistica", "statistics", "ecuacion", "ecuaciones",
    "equations", "operaciones", "operations", "numeros", "números",
    "numbers", "decimales", "decimals", "porcentajes", "percentages",
    "área", "area", "perimetro", "perímetro", "perimeter", "volumen",
    "volume", "probabilidad", "probability",
]


def _is_math_topic(*texts: str) -> bool:
    """Return True if any of *texts* contains a maths-related keyword."""
    combined = " ".join(texts).lower()
    return any(kw in combined for kw in _MATH_KEYWORDS)


async def create_chapter_agent(
    use_qwen: bool = False,
    model_id: str | None = None,
    provider: str | None = None,
) -> ChatAgent:
    """
    Create a chapter writing agent using either GitHub Models or Qwen.

    Args:
        use_qwen:  Legacy bool — True → Qwen, False → GitHub (ignored when provider is set)
        model_id:  Override the default model ID.
        provider:  Explicit provider string: 'github' | 'qwen' | 'claude' | 'azure'.
                   When supplied this takes priority over use_qwen AND the MODEL_PROVIDER
                   env-var, which prevents cross-thread contamination in batch runs.

    Implements Microsoft Agent Framework best practices:
    - Uses OpenAIChatClient with specified endpoint
    - Clear, minimal instructions to avoid hallucinations
    - Respects token limits and learning method
    - Supports both development and production workflows
    """
    config = get_model_config(use_qwen, provider=provider)
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
            "CRITICAL RULE #1: You MUST write ENTIRELY in the language specified by the user. "
            "ALL headings, section names, paragraphs, questions, and instructions MUST be in that language. "
            "Do NOT mix languages — every single word must be in the specified language.\n\n"
            "Write chapters that are age-appropriate, culturally relevant, and follow the specified learning method.\n\n"
            "CHAPTER STRUCTURE — IMPORTANT: vary the structure between chapters!\n"
            "Every chapter MUST include the REQUIRED sections, but OPTIONAL sections should rotate\n"
            "so that each chapter feels fresh and different.\n\n"
            "REQUIRED SECTIONS (always include all three — use the EXACT translated name for the target language):\n"
            "  • Key Concept (e.g. 'Concepto Clave' in Spanish, 'Key Concept' in English, 'Conceito-Chave' in Portuguese)\n"
            "  • Daily Life Example (e.g. 'Ejemplo en tu Vida' in Spanish, 'Example in Your Life' in English)\n"
            "  • Reflection Question (e.g. 'Pregunta para Pensar' in Spanish, 'Think About It' in English)\n\n"
            "OPTIONAL SECTIONS (pick 2-3 per chapter, vary your choices — translate names to target language):\n"
            "  • Family Activity\n"
            "  • School Activity\n"
            "  • Ask an AI\n"
            "  • Did You Know…\n"
            "  • Creative Challenge\n"
            "  • Connection to the World\n"
            "  • Mini Experiment\n"
            "  • Class Debate\n"
            "  • Inventor's Corner\n"
            "  • Short Story\n\n"
            "FORMATTING GUIDELINES:\n"
            "- Use Markdown with ## headers, **bold**, and lists\n"
            "- Include [IMAGE: description] placeholders where visuals help\n"
            "- Add [VIDEO: topic] tags for supplementary videos\n"
            "- Use LaTeX for formulas: $$formula$$\n"
            "- Keep language simple and engaging for the target age\n"
            "- Respect local culture and values\n"
            "- ALL output MUST be 100% in the specified language — no English words in Spanish chapters, etc.\n"
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

    # ── Language-specific section names ────────────────────────────────────
    lang = context.get('language', 'Spanish')
    sn = _get_section_names(lang)

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
        f"1. Start with the **{sn['key_concept']}** section: explain the core topic clearly using an analogy "
        f"or comparison a {context['age']}-year-old in {context['country']} would immediately understand\n"
        f"2. Write the **{sn['life_example']}** section: describe a concrete, vivid scenario from the student's "
        f"daily life in {context['country']} that connects to this concept\n"
        f"3. Craft the **{sn['think']}** section: pose an open-ended question with no single right answer "
        f"that encourages critical thinking\n"
        f"4. Choose 2-3 OPTIONAL sections that best fit THIS chapter's specific topic \u2014 "
        f"do NOT reuse the same combination from other chapters. Be creative!\n"
        + image_instruction +
        f"6. Add [VIDEO: specific topic] tags where a video would complement the written content\n\n"
        f"### LENGTH & DEPTH ###\n"
        f"Target approximately {context.get('pages_per_chapter', 5)} pages. Each section should be "
        f"substantial and detailed \u2014 not just 1-2 sentences. Use examples, mini-stories, and "
        f"real-world connections to bring the content alive.\n\n"
    )

    # ── Math-specific LaTeX rules (injected when topic is maths) ────────
    topic_str   = context.get('topic', '')
    subject_str = outline.title + " " + outline.summary
    if _is_math_topic(topic_str, subject_str):
        prompt += (
            f"### MATHEMATICS FORMATTING RULES ###\n"
            f"This is a MATHEMATICS chapter. You MUST follow ALL of these rules:\n"
            f"1. Use LaTeX for EVERY number operation, formula, fraction, equation, or "
            f"mathematical expression — NO plain text like '1/2' or '3x4'.\n"
            f"2. Use INLINE math `$...$` for expressions that appear inside sentences.\n"
            f"3. Use DISPLAY math `$$...$$` ONLY for standalone highlighted key formulas. "
            f"   NEVER place more than 2 display equations consecutively without text between them.\n"
            f"4. Each worked example MUST show EVERY step with LaTeX:\n"
            f"   $\\frac{{1}}{{2}} + \\frac{{1}}{{4}} = \\frac{{2}}{{4}} + \\frac{{1}}{{4}} = \\frac{{3}}{{4}}$\n"
            f"5. Include at least 5 fully solved practice problems with LaTeX in each chapter, "
            f"   using everyday contexts from {context['country']} (market prices, recipes, sharing food).\n"
            f"6. Use LaTeX for list items that contain numbers.\n"
            f"\n"
        )

    prompt += (
        f"### LANGUAGE REQUIREMENT — CRITICAL ###\n"
        f"Write ENTIRELY in {context['language']}. Every heading, paragraph, question, and instruction "
        f"MUST be in {context['language']}. Use culturally appropriate references for {context['country']}.\n"
        f"DO NOT mix languages. If the target language is English, ALL section headings must be in English. "
        f"If the target language is Spanish, ALL headings must be in Spanish. Zero exceptions."
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
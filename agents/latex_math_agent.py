# agents/latex_math_agent.py
"""
LaTeX Math Agent — generates chapters with rich LaTeX notation for math books.

Produces markdown content where all formulas, equations, and mathematical
relationships are expressed using LaTeX notation ($$...$$ block or $...$ inline).
The output feeds into the math book HTML template which renders LaTeX via KaTeX.

Usage:
    agent = await create_latex_math_agent(use_qwen=True, model_id="qwen-flash")
    chapter = await generate_math_chapter(agent, outline, context)
"""
from __future__ import annotations

import logging
import os
import re
from typing import Dict, Any, Optional

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from config import get_model_config
from models.book_spec import ChapterOutline, ChapterContent
from utils.retry import async_retry

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────
#  SYSTEM INSTRUCTIONS
# ─────────────────────────────────────────────────────────────────────────

_MATH_AGENT_SYSTEM = """\
You are a world-class mathematics educator specialising in creating
interactive, engaging maths content for children and young adults in
Latin America.

### LANGUAGE RULE ###
You MUST write EVERYTHING in the language specified by the user.
Only LaTeX formula content stays in universal mathematical notation.

### CHAPTER STRUCTURE ###
Every chapter MUST include, in order:

1. **Concepto Clave** — Explain the core mathematical concept clearly.
   Use analogies a child of the target age would understand.
   Include the formal definition using LaTeX:
     - Inline:  $expression$
     - Display: $$expression$$

2. **Fórmulas y Propiedades** — List the key formulas and properties
   related to this concept.  Each formula MUST be in display-mode LaTeX:
     $$a^2 + b^2 = c^2$$
   Include brief plain-language explanations beside each formula.

3. **Ejemplo Resuelto** — Walk through a complete worked example
   step by step.  Show each algebraic step using LaTeX.

4. **Ejemplo en tu Vida** — Describe a concrete, vivid scenario from the
   student's daily life that connects to this concept.

5. **Ejercicios** — Provide 3-5 practice exercises of increasing difficulty.
   State each exercise clearly and include the answer key at the end
   (hidden inside a "Respuestas" section using <details> tags).

6. **Pregunta para Pensar** — Pose an open-ended reflection question.

OPTIONAL SECTIONS (pick 1-2 per chapter, vary your choices):
  • **Sabías que…** — A surprising mathematical fact or history tidbit.
  • **Desafío Creativo** — A creative challenge or puzzle.
  • **Conexión con el Mundo** — How this math topic is used in real life.
  • **Mini Experimento** — A hands-on measurement or estimation activity.
  • **Historia de las Matemáticas** — A short story about a mathematician
    or the discovery of this concept.

### LaTeX GUIDELINES ###
- Use $...$ for inline math (e.g., $x = 5$).
- Use $$...$$ for display-mode equations on their own line.
- Always use \\frac{a}{b} for fractions, never a/b in formulas.
- Use \\sqrt{x}, \\sum_{i=1}^{n}, \\int_{a}^{b}, etc.
- For aligned multi-step derivations use:
    $$\\begin{aligned}
      2x + 3 &= 11 \\\\
      2x &= 8 \\\\
      x &= 4
    \\end{aligned}$$
- Escape backslashes properly for LaTeX commands.
- For matrices:  $$\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}$$
- For systems:   $$\\begin{cases} x + y = 5 \\\\ x - y = 1 \\end{cases}$$

### FORMATTING ###
- Use Markdown with ## headers, **bold**, and lists.
- Include [IMAGE: description] placeholders where geometric diagrams
  or visual representations would aid understanding.
- Keep language simple and engaging for the target age.
- ALL output MUST be in the specified language.
- Do NOT repeat the same optional section combination in every chapter.
"""


# ─────────────────────────────────────────────────────────────────────────
#  AGENT FACTORY
# ─────────────────────────────────────────────────────────────────────────

async def create_latex_math_agent(
    use_qwen: bool = True,
    model_id: str | None = None,
) -> ChatAgent:
    """Create a ChatAgent specialised in mathematical content with LaTeX."""
    config = get_model_config(use_qwen)
    resolved_model = model_id or config.get("model_id", "qwen-flash")
    client = OpenAIChatClient(
        api_key=os.getenv(config["api_key_env"], ""),
        base_url=config["base_url"],
        model_id=resolved_model,
    )
    return ChatAgent(
        chat_client=client,
        name="LaTeXMathAgent",
        instructions=_MATH_AGENT_SYSTEM,
    )


# ─────────────────────────────────────────────────────────────────────────
#  CHAPTER GENERATION
# ─────────────────────────────────────────────────────────────────────────

@async_retry(max_retries=3, base_delay=2.0, max_delay=60.0)
async def _run_math_agent(agent: ChatAgent, prompt: str, options: dict):
    """Run the math agent with retry on transient failures."""
    return await agent.run(prompt, **options)


async def generate_math_chapter(
    agent: ChatAgent,
    outline: ChapterOutline,
    context: Dict[str, Any],
) -> Optional[ChapterContent]:
    """
    Generate a mathematics chapter with rich LaTeX notation.

    Args:
        agent:   LaTeXMathAgent created by create_latex_math_agent().
        outline: Chapter outline with title and summary.
        context: Dict with keys: age, country, learning_method, language,
                 pages_per_chapter, math_level (optional).

    Returns:
        ChapterContent with LaTeX-rich markdown, or None on failure.
    """
    math_level = context.get("math_level", "grade-school")
    prompt = (
        f"=== MATH CHAPTER WRITING REQUEST ===\n\n"
        f"### CHAPTER INFO ###\n"
        f"- Title: {outline.title}\n"
        f"- Summary: {outline.summary}\n\n"
        f"### AUDIENCE ###\n"
        f"- Age: {context['age']} years old\n"
        f"- Country: {context['country']}\n"
        f"- Language: {context['language']}\n"
        f"- Learning Method: {context['learning_method']}\n"
        f"- Math Level: {math_level}\n\n"
        f"### TASK ###\n"
        f"Write a complete mathematics chapter following the exact structure\n"
        f"from your system instructions.  Every formula or equation MUST use\n"
        f"LaTeX notation ($...$ for inline, $$...$$ for display).\n\n"
        f"The chapter should be approximately {context.get('pages_per_chapter', 3)} "
        f"pages long and written entirely in {context['language']}.\n\n"
        f"Begin writing now."
    )

    try:
        response = await _run_math_agent(agent, prompt, {"max_tokens": 4096})
        content = _extract_text(response)
        if not content or len(content) < 100:
            logger.warning(f"Math chapter too short or empty: {outline.title}")
            return None

        # Validate that LaTeX was actually used
        if "$" not in content:
            logger.warning(
                f"Chapter '{outline.title}' has NO LaTeX. "
                f"Asking model to add formulas..."
            )
            # One-shot fix: ask the model to add LaTeX
            fix_prompt = (
                f"The following chapter is missing LaTeX math notation. "
                f"Rewrite it adding proper LaTeX ($...$ inline, $$...$$ display) "
                f"for ALL formulas and equations:\n\n{content}"
            )
            fix_response = await _run_math_agent(agent, fix_prompt, {"max_tokens": 4096})
            fixed = _extract_text(fix_response)
            if fixed and "$" in fixed:
                content = fixed

        return ChapterContent(
            chapter_title=outline.title,
            markdown_content=content,
        )

    except Exception as exc:
        logger.error(f"Failed to generate math chapter '{outline.title}': {exc}")
        return None


# ─────────────────────────────────────────────────────────────────────────
#  LaTeX UTILITIES
# ─────────────────────────────────────────────────────────────────────────

def _extract_text(response) -> str:
    """Extract text content from agent response."""
    if hasattr(response, "text"):
        return response.text.strip()
    if hasattr(response, "content"):
        return response.content.strip()
    return str(response).strip()


def extract_latex_blocks(markdown: str) -> list[str]:
    """
    Extract all LaTeX blocks (display $$...$$ and inline $...$) from markdown.
    Useful for validation or rendering preview.
    """
    display = re.findall(r'\$\$(.+?)\$\$', markdown, re.DOTALL)
    inline = re.findall(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', markdown)
    return display + inline


def validate_latex_content(markdown: str) -> dict:
    """
    Quick validation of LaTeX content in a chapter.

    Returns dict with:
      - has_latex: bool
      - display_count: int  (number of $$...$$ blocks)
      - inline_count: int   (number of $...$ spans)
      - formulas: list[str] (first 10 formulas found)
    """
    display_blocks = re.findall(r'\$\$(.+?)\$\$', markdown, re.DOTALL)
    inline_blocks = re.findall(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', markdown)
    all_formulas = display_blocks + inline_blocks
    return {
        "has_latex": len(all_formulas) > 0,
        "display_count": len(display_blocks),
        "inline_count": len(inline_blocks),
        "formulas": all_formulas[:10],
    }

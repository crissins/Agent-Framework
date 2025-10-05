# agents/chapter_agent.py
import os
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from models.book_spec import ChapterOutline, ChapterContent

async def create_chapter_agent():
    client = OpenAIChatClient(
        api_key=os.getenv("GITHUB_TOKEN"),
        base_url="https://models.inference.ai.azure.com",
        model_id="gpt-4o-mini"
    )
    return client.create_agent(
        name="ChapterAgent",
        instructions=(
            "Eres un experto en educación digital para niños de LATAM. "
            "Escribe capítulos interactivos, divertidos y seguros para niños de {age} años en {country}. "
            "Usa un tono amigable, ejemplos locales (México, LATAM), y evita tecnicismos complejos. "
            "Cada capítulo DEBE incluir estas secciones en orden:\n"
            "1. **Concepto Clave**: Explicación simple del tema.\n"
            "2. **Ejemplo en tu Vida**: Cómo se ve esto en tu casa, escuela o comunidad.\n"
            "3. **Pregunta para Pensar**: Una pregunta abierta para reflexionar.\n"
            "4. **Actividad en Familia**: Una actividad offline que puedan hacer juntos (sin tecnología).\n"
            "5. **Actividad en la Escuela**: Una actividad grupal para el salón de clases (puede usar papel, pizarrón, o tecnología si está disponible).\n"
            "6. **Pregunta para una IA**: Sugiere 1–2 preguntas que el estudiante puede hacerle a cualquier asistente de IA (ChatGPT, Gemini, Claude, etc.) para aprender más. Ejemplo: '¿Cómo puede la IA ayudar a mi comunidad a reciclar mejor?'\n\n"
            "Formato: Usa Markdown con encabezados (`##`), listas, y negritas. "
            "Incluye fórmulas en LaTeX si es necesario: $$2 + 2 = 4$$. "
            "Agrega [IMAGE: descripción] y [VIDEO: tema] donde sea útil."
        ),
    )

async def generate_chapter(agent: ChatAgent, outline: ChapterOutline, context: dict) -> ChapterContent:
    # Build rich prompt with context
    prompt = (
        f"Escribe un capítulo completo titulado '{outline.title}' para niños de {context['age']} años en {context['country']}, "
        f"usando el método {context['learning_method']} y en {context['language']}. "
        f"Resumen del capítulo: {outline.summary}. "
        f"El capítulo debe tener aproximadamente {context['pages_per_chapter']} páginas de contenido rico y estructurado. "
        f"Incluye todas las secciones requeridas en las instrucciones del agente."
    )

    # Run with higher token limit for chapters
    response = await agent.run(
        prompt,
        max_tokens=2000  # Allow longer, richer output
    )
    
    return ChapterContent(
        chapter_title=outline.title,
        markdown_content=response.text
    )
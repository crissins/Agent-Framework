# agents/curriculum_agent.py
import os
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from models.book_spec import BookRequest, Curriculum, ChapterOutline

async def create_curriculum_agent():
    client = OpenAIChatClient(
        api_key=os.getenv("GITHUB_TOKEN"),
        base_url="https://models.inference.ai.azure.com",
        model_id="gpt-4o-mini"
    )
    return client.create_agent(
        name="CurriculumAgent",
        instructions=(
            "You are an expert curriculum designer for K-12 education in LATAM. "
            "You create chapter outlines with ONLY title and summary. "
            "DO NOT include page counts or estimated_pages in your output."
        ),
    )

async def generate_curriculum(agent: ChatAgent, request: BookRequest) -> Curriculum:
    prompt = (
        f"Design a book curriculum for topic '{request.topic}' "
        f"for {request.target_audience_age}-year-olds in {request.country}, "
        f"using the {request.learning_method} method, in {request.language}. "
        f"Create exactly {request.num_chapters} chapters. "
        "Each chapter must have only 'title' and 'summary'."
    )
    response = await agent.run(prompt, response_format=Curriculum, max_tokens=800)
    return response.value
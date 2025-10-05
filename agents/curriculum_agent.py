import os
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from models.book_spec import BookRequest, Curriculum

async def create_curriculum_agent():
    client = OpenAIChatClient(
        api_key=os.getenv("GITHUB_TOKEN"),
        base_url="https://models.inference.ai.azure.com",
        model_id="gpt-4o-mini"
    )
    return client.create_agent(
        name="CurriculumAgent",
        instructions=(
            "You are an expert curriculum designer for LATAM K-12 education. "
            "Create a curriculum with ONLY title, description, and chapter outlines (title + summary). "
            "Do NOT include page counts in chapters."
        ),
    )

async def generate_curriculum(agent: ChatAgent, request: BookRequest) -> Curriculum:
    prompt = (
        f"Design a book curriculum for '{request.topic}' "
        f"for {request.target_audience_age}-year-olds in {request.country}, "
        f"using the {request.learning_method} method, in {request.language}. "
        f"Create exactly {request.num_chapters} chapters."
    )
    response = await agent.run(prompt, response_format=Curriculum, max_tokens=1500)
    return response.value
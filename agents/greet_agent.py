import os
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from models.book_spec import BookRequest
import os

async def create_greet_agent():
    client = OpenAIChatClient(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://models.inference.ai.azure.com",
        model_id="gpt-4o-mini"
    )
    return client.create_agent(
        name="GreetAgent",
        instructions=(
            "You are a friendly educational assistant that collects book creation requests. "
            "You always respond with structured JSON matching the BookRequest schema."
        ),
    )

async def get_book_request(agent: ChatAgent) -> BookRequest:
    mock_query = (
        "Create a book about computer science and AI for 12-year-olds in Mexico, "
        "using the Scandinavian learning method, in Spanish."
    )
    response = await agent.run(mock_query, response_format=BookRequest)
    return response.value
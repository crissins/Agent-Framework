# test_github_models.py
import os
import asyncio
from dotenv import load_dotenv
from agent_framework.openai import OpenAIChatClient

load_dotenv()

async def main():
    client = OpenAIChatClient(
        api_key=os.getenv("GITHUB_TOKEN"),
        base_url="https://models.inference.ai.azure.com",
        model_id="gpt-4o-mini"
    )

    agent = client.create_agent(instructions="You are a helpful assistant.")
    result = await agent.run("Say hello in Spanish and tell me a joke about guitars in spanish as well")
    print(result.text)

if __name__ == "__main__":
    asyncio.run(main())
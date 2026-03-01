# Microsoft Agent Framework - Best Practices Implementation

This document outlines the best practices from Microsoft Learn that have been integrated into this Agent Framework project.

## 📌 Current Setup

### Supported Providers

The app supports **4 model providers** selectable via the sidebar (no restart needed):

| Provider | Key Variable(s) | Free Tier | Best For |
|----------|----------------|-----------|----------|
| **GitHub Models** | `GITHUB_TOKEN` | ✅ Yes | Development, testing |
| **Qwen/DashScope** | `DASHSCOPE_API_KEY` | ✅ Yes (limited) | TTS, voice cloning, images |
| **Claude (Anthropic)** | `ANTHROPIC_API_KEY` | ❗ Paid | Stronger reasoning, academic content |
| **Azure AI Foundry** | `AZURE_OPENAI_API_KEY` + endpoint + deployment | ❗ Paid | Enterprise, compliance |

The active provider is controlled by `MODEL_PROVIDER` env var or selected in the sidebar. `use_qwen_models` is kept for backward compatibility.

---

## 🚀 Quick Start

### Installation

```bash
# Core dependencies
pip install -r requirements.txt
```

### Configuration

Copy the template and fill in your keys for the provider(s) you want to use:

```bash
cp .env.example .env
```

Minimum for free immediate start:

```bash
GITHUB_TOKEN=ghp_xxxxxxxxxxxx     # Free via GitHub Settings > Tokens
MODEL_PROVIDER=github             # github | qwen | claude | azure
```

For Qwen (TTS + images):

```bash
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxx
DASHSCOPE_REGION=singapore        # singapore | beijing | us-virginia
MODEL_PROVIDER=qwen
```

For Claude:

```bash
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxx
MODEL_PROVIDER=claude
```

For Azure AI Foundry:

```bash
AZURE_OPENAI_API_KEY=xxxxxxxxx
AZURE_OPENAI_ENDPOINT=https://your-project.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
MODEL_PROVIDER=azure
```

### Run

```bash
# Windows
run_app.bat

# Any OS
python -m streamlit run app.py
```

Opens at `http://localhost:8501`

---

---

## 1. **Client Selection: Multi-Provider Support**

All four providers share the same `OpenAIChatClient` interface from Microsoft Agent Framework. Switching providers requires only setting `MODEL_PROVIDER` — no code changes.

### Provider Implementations

**GitHub Models (free dev tier)**:
```python
from agent_framework.openai import OpenAIChatClient

client = OpenAIChatClient(
    api_key=os.getenv("GITHUB_TOKEN"),
    base_url="https://models.inference.ai.azure.com",
    model_id="gpt-4o-mini"
)
```

**Qwen/DashScope (free tier, best for TTS/images)**:
```python
client = OpenAIChatClient(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    model_id="qwen-plus"
)
```

**Claude / Anthropic (paid, stronger reasoning)**:
```python
client = OpenAIChatClient(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    base_url="https://api.anthropic.com/v1",
    model_id="claude-haiku-4-5"
)
```

**Azure AI Foundry (enterprise/production)**:
```python
client = OpenAIChatClient(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    base_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
    model_id=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
)
```

In production with Azure, prefer `DefaultAzureCredential` for passwordless auth:
```python
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
client = AzureOpenAIChatClient(
    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    credential=credential,
)
```

**Selection in code:** All providers are routed via `config.get_model_config(provider=...)` which reads `MODEL_PROVIDER` env var. The returned config dict is passed to `OpenAIChatClient`.

---

## 1B. **Image Generation: Qwen-Image-Max (NEW)**

### ✅ Why Qwen-Image-Max for Educational Content

Qwen-Image-Max excels at:
1. **Complex Text Rendering**: Multi-line paragraphs, titles, subtitles in images (critical for books)
2. **Artistic Flexibility**: Multiple styles suitable for children's education
3. **Fine Detail**: Excellent for character textures and intricate designs
4. **Prompt Understanding**: Exceptional at following detailed specifications

### Performance Showcase
- ✅ Renders intricate text layouts with multiple fonts/sizes
- ✅ Handles complex compositions with many elements
- ✅ Produces high-quality, artifact-free images
- ✅ Supports 5 aspect ratios for various book layouts

### Setup & API

**Environment Variables Required**:
```bash
DASHSCOPE_API_KEY=sk-xxxx  # From Alibaba Cloud Model Studio
```

**Installation**:
```bash
pip install dashscope
```

**Quick Start**:
```python
from agents.qwen_image_agent import generate_image_with_qwen

# Generate single image
image = await generate_image_with_qwen(
    prompt="Educational poster for children...",
    style="educational",  # or "story", "technical", "artistic"
    size="1664*928"  # 16:9 ratio for book pages
)

# Generate multiple images (sequential to save quota)
images = await generate_multiple_images(
    prompts=[...],
    style="educational",
    parallel=False  # Set True for parallel generation
)
```

**Supported Sizes**:
- `1664*928` (16:9) - Default, best for book pages
- `1328*1328` (1:1) - Square format
- `1472*1104` (4:3) - Traditional aspect
- `1104*1472` (3:4) - Portrait
- `928*1664` (9:16) - Vertical story format

### Key Features
- ✅ **Enhanced Prompts**: Model can improve your prompt with `prompt_extend=True`
- ✅ **URL Persistence**: Generated URLs valid for 24 hours (download promptly)
- ✅ **Fast Generation**: ~15-30 seconds per image
- ✅ **Negative Prompts**: Specify what to avoid in the image
- ✅ **Seed Control**: Use same seed for reproducible results

### Example: Educational Poster with Text

```python
prompt = """
Healing-style hand-drawn poster for children learning about environmental conservation.
Features three animated puppies playing with a recycling symbol on lush green grass.
Adorned with decorative elements: birds and stars.

Main title "Save Our Planet!" in bold, blue cartoon font at the top.
Subtitle "Every Action Counts!" in green font below.

Speech bubble with text: "Help us make the world greener!"
Bottom text: "Start recycling today!"

Color palette: Fresh greens and sky blues, accented with bright pink and sunny yellow.
Style: Warm, hand-drawn illustration, storybook-like, cheerful atmosphere.
"""

image = await generate_image_with_qwen(
    prompt=prompt,
    style="educational",
    size="1664*928"
)
```

**Files Added**: `agents/qwen_image_agent.py`

---

## 2. **Agent Class vs. ChatAgent**

### ✅ What Was Changed
- **Before**: Used `ChatAgent` from `agent_framework`
- **After**: Uses `Agent` base class

### Why This Matters
- `Agent` is the modern, standardized interface
- Provides consistent patterns across all agent types
- Better type safety and IDE support

### Implementation
```python
agent = client.as_agent(
    name="MyAgent",
    instructions="Clear, focused instructions...",
)
```

**Files Updated**: All agent creation functions

---

## 3. **Async/Await and Context Managers**

### ✅ What Was Changed
- Added proper async context managers with `async with`
- Improved error handling throughout
- Added type hints for all functions

### Why This Matters
> "Proper resource management prevents connection leaks and ensures clean shutdown."

### Best Practice Pattern
```python
async def create_agent() -> Agent:
    """Create agent with proper type hints."""
    credential = DefaultAzureCredential()
    client = AzureOpenAIChatClient(...)
    agent = client.as_agent(...)
    return agent
```

**Files Updated**: `greet_agent.py`, `curriculum_agent.py`, `chapter_agent.py`, `main.py`

---

## 4. **Error Handling and Graceful Fallbacks**

### ✅ What Was Changed
- Added try-except blocks with informative error messages
- Implemented fallback values for failures
- Added validation of results before use

### Why This Matters
> "Plan for tool or LLM failures. Timeouts, malformed responses, or empty results can break a workflow."

### Example
```python
async def get_book_request(agent: Agent) -> Optional[BookRequest]:
    """Get book request with error handling."""
    try:
        response = await agent.run(query, response_format=BookRequest)
        return response.value
    except Exception as e:
        print(f"Error: {e}")
        # Fallback to defaults
        return BookRequest(...)
```

**Files Updated**: `greet_agent.py`, `curriculum_agent.py`, `chapter_agent.py`

---

## 5. **Structured Instructions**

### ✅ What Was Changed
- Simplified and clarified agent instructions
- Removed vague directives
- Added structured output requirements

### Why This Matters
> "Overly vague instructions lead to inconsistent behavior. Too many instructions can confuse the agent. Keep prompts clear and minimal to avoid hallucinations."

### Best Practice
```python
instructions=(
    "You are an expert curriculum designer.\n"
    "Your task: Create a structured curriculum with:\n"
    "1. title\n"
    "2. description\n"
    "3. chapters (array with title and summary only)\n\n"
    "CONSTRAINTS:\n"
    "- Do NOT include page counts\n"
    "- Ensure cultural relevance"
)
```

**Files Updated**: All agent creation functions

---

## 6. **Type Safety with Pydantic Models**

### ✅ What Was Changed
- Added proper type hints throughout
- Ensured Pydantic model validation
- Added `Optional` types for nullable returns

### Why This Matters
- Automatic validation of data types
- IDE auto-completion and type checking
- Self-documenting code

### Example
```python
async def generate_curriculum(
    agent: Agent,
    request: BookRequest
) -> Optional[Curriculum]:
    """Type-safe function with clear contract."""
    response = await agent.run(...)
    return response.value
```

**Files Updated**: All agent files

---

## 7. **Observability and Logging**

### ✅ What Was Changed
- Enabled observability with `setup_observability()`
- Added structured logging in main workflow
- Removed sensitive data from logs

### Why This Matters
> "Implement detailed logging for each user request, agent plan, and tool call."

### Implementation
```python
from agent_framework.observability import setup_observability

# Production: disable sensitive data logging
setup_observability(enable_sensitive_data=False)
```

**Files Updated**: `main.py`, `app.py`

---

## 8. **Streaming Support (Production Ready)**

### ✅ What Was Changed
- Prepared code for `run_stream()` support
- Structured response handling
- Added progress feedback for long operations

### Why This Matters
> "Use `run_stream()` for production apps to get real-time feedback and better UX."

### Future Implementation
```python
async for chunk in agent.run_stream(prompt):
    if chunk.text:
        print(chunk.text, end="", flush=True)
```

**Note**: Can be enabled in `chapter_agent.py` and `app.py` for production

---

## 9. **Tool Integration with Error Handling**

### ✅ What Was Changed
Updated tool functions (`image_search_tool`, `video_search_tool`):
- Added timeout parameters
- Implemented try-except blocks
- Added fallback mechanisms
- Improved async patterns

### Best Practice
```python
async def image_search_tool(
    query: str,
    timeout: int = 10
) -> Optional[ImagePlaceholder]:
    """Search with proper error handling."""
    def _sync_search() -> str:
        try:
            # Protected operation
            ...
        except Exception as e:
            print(f"Warning: {e}")
            return None
    
    try:
        url = await asyncio.to_thread(_sync_search)
        return ImagePlaceholder(...)
    except Exception as e:
        return ImagePlaceholder(url="fallback_url")
```

**Files Updated**: `image_search_agent.py`, `video_search_agent.py`

---

## 10. **Workflow Orchestration**

### ✅ What Was Changed
- Improved `main.py` with clear sequential steps
- Better error handling at orchestration level
- Structured logging of workflow progress

### Best Practice Pattern
```python
async def main():
    try:
        # Step 1: Get request
        print("Step 1...")
        request = await get_book_request(...)
        
        # Step 2: Generate curriculum
        print("Step 2...")
        curriculum = await generate_curriculum(...)
        
        # Step 3: Continue chain...
        
    except Exception as e:
        print(f"Workflow error: {e}")
        raise
```

**Files Updated**: `main.py`, `app.py`

---

## Key Microsoft Learn References

1. **Agent System Design Patterns**
   - Start simple, gradually add complexity
   - Keep prompts clear and minimal
   - Plan for failures and implement fallbacks

2. **Best Practices for Designing an Agent**
   - Avoid overly vague or contradictory instructions
   - Test with various input types and edge cases
   - Document your agent's purpose and constraints

3. **Agent Framework Overview**
   - Use enterprise-grade clients (`AzureOpenAIChatClient`, `AzureAIClient`)
   - Implement proper observability
   - Support multi-turn conversations with threads

---

## Environment Configuration

### Development Setup (Current)

Create a `.env` file in your project root:

```bash
# GitHub Models (for LLM agents)
GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# Qwen Image Generation
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxx
```

**Getting Credentials**:
1. **GITHUB_TOKEN**: 
   - Go to GitHub → Settings → Developer settings → Personal access tokens
   - Create token with `read:packages` scope
   - [GitHub Models Info](https://github.com/marketplace/models)

2. **DASHSCOPE_API_KEY**:
   - Go to [Alibaba Cloud Model Studio](https://www.alibabacloud.com/help/en/model-studio/get-api-key)
   - Create new API key (separate for Beijing and Singapore regions!)
   - [Qwen Image Documentation](https://www.alibabacloud.com/help/en/model-studio/qwen-image)

### Production Setup (Future)

```bash
# Azure OpenAI (for LLM agents)
AZURE_OPENAI_ENDPOINT=https://your-instance.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini

# Azure AI (for Foundry agents - alternative)
AZURE_AI_PROJECT_ENDPOINT=https://your-project.cognitiveservices.azure.com/
AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME=your-deployment

# For production image generation
AZURE_OPENAI_IMG_DEPLOYMENT=dall-e-3
```

---

## Testing Recommendations

According to Microsoft Learn best practices:

1. **Test with various inputs**: Edge cases, typos, different age groups
2. **Validate responses**: Check accuracy and completeness
3. **Check error recovery**: Ensure agents handle failures gracefully
4. **Performance testing**: Monitor token usage and response times

---

## Next Steps for Further Improvement

1. **Add streaming support** in Streamlit app:
   ```python
   async for chunk in agent.run_stream(prompt):
       st.write(chunk.text)
   ```

2. **Implement thread management** for user session persistence

3. **Add metrics collection** for evaluation:
   - Task completion rate
   - Response accuracy
   - User satisfaction

4. **Version-pin models** to prevent behavior drift:
   ```python
   deployment_name="gpt-4o-mini-2024-07-18"
   ```

5. **Add human-in-the-loop** for content review before publishing

---

## Summary of Updates

| Component | Before | After | Benefit |
|-----------|--------|-------|---------|
| Client | OpenAIChatClient | AzureOpenAIChatClient | Production-ready, secure |
| Agent Type | ChatAgent | Agent | Modern interface, type-safe |
| Error Handling | Minimal | Comprehensive | Resilient workflows |
| Type Hints | Limited | Complete | Better IDE support, clarity |
| Observability | Basic | Advanced | Better debugging, monitoring |
| Instructions | Vague | Structured | Consistent behavior |
| Async Patterns | Mixed | Proper | Clean resource management |

---

For more information, visit:
- [Microsoft Agent Framework Documentation](https://learn.microsoft.com/en-us/agent-framework/)
- [Agent Design Best Practices](https://learn.microsoft.com/en-us/agent-framework/guidance/best-practices/)
- [Azure OpenAI Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/)

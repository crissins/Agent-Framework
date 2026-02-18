"""
Model configuration and selection for Agent Framework.
Supports both GitHub Models (dev) and Qwen models (via DashScope).
"""
import os
from enum import Enum


class ModelProvider(Enum):
    """Available model providers."""
    GITHUB = "github"  # GitHub Models (gpt-4o-mini)
    QWEN = "qwen"      # Qwen via DashScope


class ModelConfig:
    """Configuration for different model providers."""
    
    # GitHub Models (OpenAI SDK)
    GITHUB_CONFIG = {
        "provider": "github",
        "api_key_env": "GITHUB_TOKEN",
        "base_url": "https://models.inference.ai.azure.com",
        "model_id": "gpt-4o-mini",
        "description": "GitHub Models (gpt-4o-mini) - Free tier for development"
    }
    
    # Qwen Models (DashScope via OpenAI-compatible API)
    QWEN_CONFIG_SINGAPORE = {
        "provider": "qwen",
        "api_key_env": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "model_id": "qwen-plus",
        "region": "singapore",
        "description": "Qwen Plus (Singapore region)"
    }
    
    QWEN_CONFIG_BEIJING = {
        "provider": "qwen",
        "api_key_env": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model_id": "qwen-plus",
        "region": "beijing",
        "description": "Qwen Plus (Beijing region)"
    }
    
    QWEN_CONFIG_US = {
        "provider": "qwen",
        "api_key_env": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope-us.aliyuncs.com/compatible-mode/v1",
        "model_id": "qwen-plus",
        "region": "us-virginia",
        "description": "Qwen Plus (US Virginia region)"
    }


def get_model_config(use_qwen: bool = False, qwen_region: str = "singapore") -> dict:
    """
    Get model configuration based on provider selection.
    
    Args:
        use_qwen: If True, returns Qwen config; if False, returns GitHub Models config
        qwen_region: Region for Qwen models ('singapore', 'beijing', 'us-virginia')
        
    Returns:
        Configuration dictionary with api_key_env, base_url, model_id, and description
    """
    if use_qwen:
        if qwen_region == "beijing":
            return ModelConfig.QWEN_CONFIG_BEIJING
        elif qwen_region == "us-virginia":
            return ModelConfig.QWEN_CONFIG_US
        else:  # default to singapore
            return ModelConfig.QWEN_CONFIG_SINGAPORE
    else:
        return ModelConfig.GITHUB_CONFIG


def validate_api_keys(use_qwen: bool = False) -> tuple[bool, str]:
    """
    Validate that required API keys are configured.
    
    Args:
        use_qwen: If True, checks DASHSCOPE_API_KEY; if False, checks GITHUB_TOKEN
        
    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    config = get_model_config(use_qwen)
    api_key_env = config["api_key_env"]
    api_key = os.getenv(api_key_env)
    
    if not api_key:
        return False, f"❌ Missing {api_key_env} environment variable"
    
    return True, f"✅ {config['description']} configured"


def get_fact_check_config() -> dict:
    """
    Get configuration for fact-checking agent with web search.
    
    Returns:
        Configuration optimized for fact-checking using Qwen models with web search
        
    Features:
    - Uses qwen3-max for best web search performance
    - OpenAI-compatible API through DashScope
    - Supports enable_search parameter for real-time verification
    """
    return {
        "provider": "qwen",
        "api_key_env": "DASHSCOPE_API_KEY",
        "base_url": "https://api.openai.com/v1",  # OpenAI compatible
        "model_id": "qwen3-max",  # For web search support
        "web_search_enabled": True,
        "description": "Qwen3-Max with Web Search for Fact-Checking"
    }


def verify_fact_check_setup() -> tuple[bool, str]:
    """
    Verify that fact-checking setup is ready with web search.
    
    Returns:
        Tuple of (is_ready: bool, message: str)
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")
    
    if not api_key:
        return False, (
            "❌ Web search fact-checking requires DASHSCOPE_API_KEY\n"
            "Get free API key at: https://dashscope.aliyun.com/\n"
            "Set: export DASHSCOPE_API_KEY=your_key (Linux/Mac) or\n"
            "Set: set DASHSCOPE_API_KEY=your_key (Windows Command Prompt)"
        )
    
    return True, "✅ Fact-check with web search is configured and ready!"


def print_fact_check_setup_guide():
    """Print setup guide for fact-checking with web search."""
    
    guide = """
╔════════════════════════════════════════════════════════════════════════════╗
║       FACT-CHECKING WITH WEB SEARCH - QUICK SETUP GUIDE                    ║
╚════════════════════════════════════════════════════════════════════════════╝

1️⃣  GET API KEY
   • Visit: https://dashscope.aliyun.com/
   • Sign up for free account
   • Create API key (format: sk-xxxxx...)

2️⃣  SET ENVIRONMENT VARIABLE

   Windows Command Prompt:
   ─────────────────────
   set DASHSCOPE_API_KEY=sk-your_key_here

   Windows PowerShell:
   ──────────────────
   $env:DASHSCOPE_API_KEY="sk-your_key_here"

   Python (in code):
   ────────────────
   import os
   os.environ['DASHSCOPE_API_KEY'] = 'sk-your_key_here'

3️⃣  VERIFY SETUP
   From config.py:
   ──────────────
   is_ready, msg = verify_fact_check_setup()
   print(msg)

4️⃣  USE FACT-CHECKING AGENT
   from agents.fact_check_agent import create_fact_check_agent
   import asyncio
   
   async def check():
       agent = await create_fact_check_agent(use_qwen=True)
       # Now ready for web search fact-checking!
   
   asyncio.run(check())

5️⃣  WITH BOOK GENERATION
   from agents.enhanced_book_workflow import generate_and_fact_check_book
   
   results = await generate_and_fact_check_book(
       book_title="My Book",
       age_group="8-10 years",
       chapters=[...],
       topics=[...],
       enable_fact_checking=True  # Uses web search!
   )

🎯 FEATURES UNLOCKED:
   ✅ Real-time web search verification
   ✅ Automatic fact-checking during book generation
   ✅ Source citations and confidence levels
   ✅ Age-appropriate content validation
   ✅ Comprehensive quality reports

╚════════════════════════════════════════════════════════════════════════════╝
"""
    print(guide)

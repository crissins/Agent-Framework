"""
Model configuration and selection for Agent Framework.
Supports both GitHub Models (dev) and Qwen models (via DashScope).
"""
import os
from enum import Enum


class ModelProvider(Enum):
    """Available model providers."""
    GITHUB  = "github"   # GitHub Models
    QWEN    = "qwen"     # Qwen via DashScope
    CLAUDE  = "claude"   # Anthropic Claude
    AZURE   = "azure"    # Azure AI Foundry / Azure OpenAI


# ── TTS / Voice Configuration ────────────────────────────────────────────
# Standard (non-clone) TTS models shown in the sidebar selectbox.
TTS_MODELS = {
    "qwen3-tts-flash":          "🔊 TTS Flash — Fast & cost-effective",
    "qwen3-tts-instruct-flash": "🎭 TTS Instruct Flash — Emotion & character control",
    "qwen3-tts-vd-2026-01-26":  "🎨 TTS Voice Design — Custom voice from text description",
}

# Scenario / recommended-use description shown as sidebar help text.
TTS_MODEL_SCENARIOS = {
    "qwen3-tts-flash": (
        "📌 Best for: e-learning narration, batch audiobooks, navigation, notifications.\n"
        "Per-character billing. Rich voice options. Multi-language support."
    ),
    "qwen3-tts-instruct-flash": (
        "📌 Best for: audiobooks, radio drama, game / animation dubbing.\n"
        "LLM auto-generates voice direction (pitch, rate, emotion, character personality)."
    ),
    "qwen3-tts-vd-2026-01-26": (
        "📌 Best for: brand-specific voices, exclusive voiceprints.\n"
        "Designs a custom voice from a text description — no audio sample needed."
    ),
    "qwen3-tts-vc-2026-01-22": (
        "📌 Best for: voice cloning from audio samples.\n"
        "Replicates a voice with high fidelity. Requires 'Use Cloned Voice' enabled."
    ),
}

# ── Voice Clone (Qwen3 TTS-VC) Configuration ─────────────────────────────
# Used automatically when "Use Cloned Voice" is enabled. Not shown in standard selectbox.
VC_MODELS = {
    "qwen3-tts-vc-2026-01-22": "🎤 TTS Voice Clone — Replicate voice from audio sample",
}

TTS_VOICES = {
    "longxiaochun": "Female · Warm · Narrator",
    "longxiaoxia": "Female · Lively · Storyteller",
    "longyue": "Female · Gentle · Soothing",
    "longxiaofei": "Female · Clear · Professional",
    "longlaotie": "Male · Deep · Authoritative",
    "longshuo": "Male · Energetic · Narrator",
    "longjielidou": "Male · Humorous · Storyteller",
    "longxiang": "Male · Calm · Educational",
    "longtong": "Child · Bright · Educational",
    "longxiaobai": "Youth · Neutral · General",
}

TTS_AUDIO_FORMATS = {
    "wav_24k": "WAV 24 kHz (native, recommended)",
    "wav_16k": "WAV 16 kHz",
    "wav_22k": "WAV 22 kHz",
}


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
        "model_id": "qwen3.5-flash",
        "region": "singapore",
        "description": "Qwen3.5 Flash (Singapore region) — free quota"
    }

    QWEN_CONFIG_BEIJING = {
        "provider": "qwen",
        "api_key_env": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model_id": "qwen3.5-flash",
        "region": "beijing",
        "description": "Qwen3.5 Flash (Beijing region) — free quota"
    }

    QWEN_CONFIG_US = {
        "provider": "qwen",
        "api_key_env": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope-us.aliyuncs.com/compatible-mode/v1",
        "model_id": "qwen3.5-flash",
        "region": "us-virginia",
        "description": "Qwen3.5 Flash (US Virginia region) — free quota"
    }

    # Anthropic Claude — OpenAI-compatible endpoint
    CLAUDE_CONFIG = {
        "provider": "claude",
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url": "https://api.anthropic.com/v1",
        "model_id": "claude-haiku-4-5",
        "description": "Anthropic Claude (claude-haiku-4-5)"
    }

    # Azure AI Foundry / Azure OpenAI — endpoint from env var
    AZURE_FOUNDRY_CONFIG = {
        "provider": "azure",
        "api_key_env": "AZURE_OPENAI_API_KEY",
        "base_url_env": "AZURE_OPENAI_ENDPOINT",   # resolved at runtime
        "model_id_env": "AZURE_OPENAI_DEPLOYMENT_NAME",
        "model_id": "gpt-4o",                       # fallback if env not set
        "description": "Azure AI Foundry / Azure OpenAI"
    }


def load_env_vars():
    """
    Load environment variables from .env file if it exists.
    """
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # Strip surrounding quotes (single or double)
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                        value = value[1:-1]
                    os.environ[key] = value


def get_model_config(
    use_qwen: bool = False,
    qwen_region: str | None = None,
    provider: str | None = None,
) -> dict:
    """
    Get model configuration based on provider selection.

    Args:
        use_qwen:    Legacy bool — True → Qwen, False → GitHub (ignored when provider is set)
        qwen_region: Region for Qwen models ('singapore', 'beijing', 'us-virginia')
        provider:    Explicit provider string: 'github' | 'qwen' | 'claude'.
                     Falls back to MODEL_PROVIDER env var, then use_qwen flag.

    Returns:
        Configuration dictionary with api_key_env, base_url, model_id, and description
    """
    load_env_vars()

    # Resolve provider: explicit arg > env var > legacy bool
    resolved_provider = (
        provider
        or os.getenv("MODEL_PROVIDER", "")
        or ("qwen" if use_qwen else "github")
    ).strip().lower()

    if resolved_provider == "claude":
        return ModelConfig.CLAUDE_CONFIG

    if resolved_provider == "azure":
        cfg = dict(ModelConfig.AZURE_FOUNDRY_CONFIG)
        # Resolve dynamic values from env at call time
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", cfg["model_id"])
        cfg["base_url"] = endpoint
        cfg["model_id"] = deployment
        cfg["description"] = f"Azure AI Foundry ({deployment})"
        return cfg

    if resolved_provider == "qwen":
        resolved_region = (qwen_region or os.getenv("DASHSCOPE_REGION", "singapore")).strip().lower()
        if resolved_region == "beijing":
            return ModelConfig.QWEN_CONFIG_BEIJING
        elif resolved_region == "us-virginia":
            return ModelConfig.QWEN_CONFIG_US
        else:
            return ModelConfig.QWEN_CONFIG_SINGAPORE

    # default: github
    return ModelConfig.GITHUB_CONFIG


def _check_github_models_scope(token: str) -> tuple[bool, str]:
    """
    Verify the GitHub token can actually reach the GitHub Models API.

    Strategy:
    1. Call https://api.github.com/user to get OAuth scopes (classic PATs).
       If 'models' is listed → OK.
    2. If no scopes returned (fine-grained PAT or GitHub App token), fall back
       to a lightweight GET against the models catalog endpoint to confirm access.

    Returns (ok, message).
    """
    import urllib.request
    import urllib.error

    headers = {"Authorization": f"Bearer {token}", "User-Agent": "libro-agent/1.0"}

    # ── Step 1: check classic OAuth scopes ──────────────────────────────
    try:
        req = urllib.request.Request("https://api.github.com/user", headers=headers)
        with urllib.request.urlopen(req, timeout=6) as resp:
            scopes_header = resp.headers.get("X-OAuth-Scopes", "")
            scopes = [s.strip() for s in scopes_header.split(",") if s.strip()]
            if "models" in scopes:
                return True, "✅ GitHub Models configured (models scope ✓)"
            # Fine-grained tokens return no OAuth scopes — fall through to live test
            if scopes:
                # Classic token but missing 'models' scope
                return (
                    False,
                    f"❌ Your GITHUB_TOKEN is missing the 'models' scope.\n"
                    f"Current scopes: {', '.join(scopes)}\n"
                    "Fix: Go to https://github.com/settings/tokens → regenerate your token "
                    "→ tick the 'models' permission → update your .env file.",
                )
    except Exception:
        pass  # network hiccup — continue to live test

    # ── Step 2: live test against the chat completions endpoint ───────────
    # The catalog endpoint (/models) can return 200 even without inference rights.
    # Test the actual inference endpoint with a minimal 1-token request.
    try:
        import json as _json
        payload = _json.dumps({
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1,
        }).encode()
        req2 = urllib.request.Request(
            "https://models.inference.ai.azure.com/chat/completions",
            data=payload,
            headers={**headers, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req2, timeout=10) as resp2:
            if resp2.status < 300:
                return True, "✅ GitHub Models configured (inference verified ✓)"
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            return (
                False,
                "❌ Your GITHUB_TOKEN is not authorised for GitHub Models inference.\n"
                "Fix: Go to https://github.com/settings/tokens →\n"
                "  • Classic token: regenerate and tick the 'models' permission.\n"
                "  • Fine-grained token: add 'Models > Read' under account permissions.\n"
                "Then update your .env file with the new token.",
            )
    except Exception:
        pass  # network error — don't block generation

    return True, "✅ GitHub Models configured"


def validate_api_keys(use_qwen: bool = False, provider: str | None = None) -> tuple[bool, str]:
    """
    Validate that required API keys are configured.

    Args:
        use_qwen: Legacy bool (used when provider is not supplied)
        provider: Explicit provider string: 'github' | 'qwen' | 'claude'

    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    config = get_model_config(use_qwen=use_qwen, provider=provider)
    api_key_env = config["api_key_env"]
    api_key = os.getenv(api_key_env)

    if not api_key:
        return False, f"❌ Missing {api_key_env} environment variable"

    # For GitHub Models, also verify the token has the 'models' scope
    if config.get("provider") == "github":
        return _check_github_models_scope(api_key)

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
        "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",  # DashScope OpenAI-compatible
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

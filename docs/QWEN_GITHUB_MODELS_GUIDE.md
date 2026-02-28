# 🔄 GitHub Models vs Qwen Models - Complete Guide

This guide explains how to use both GitHub Models and Qwen models in your Agent Framework setup, and when to choose each.

## Quick Comparison

| Feature | GitHub Models | Qwen Models |
|---------|---------------|------------|
| **Cost** | Free (Microsoft GitHub) | Free tier available (Alibaba Cloud) |
| **Setup** | Simple (GitHub token) | Requires DashScope account |
| **Model Name** | gpt-4o-mini | qwen-plus |
| **Quality** | Excellent for general tasks | Excellent + production-ready |
| **Use Case** | Quick development | Development & Production |
| **Infrastructure** | Managed by Microsoft | Managed by Alibaba (choose region!) |
| **Latency** | Variable | Consistent |
| **API Type** | OpenAI-compatible | OpenAI-compatible |

## 🎯 When to Use Each

### Use GitHub Models When:
- ✅ You want to get started immediately without sign-ups
- ✅ You're prototyping features quickly
- ✅ You're testing the Agent Framework
- ✅ You don't need guaranteed production SLAs
- ✅ You're outside of China mainland

### Use Qwen Models When:
- ✅ You're deploying to production
- ✅ You need consistent performance and SLAs
- ✅ You want to scale beyond Gₙimple prototypes
- ✅ You're targeting Asia-Pacific users
- ✅ You want a unified stack (Qwen for both chat AND images)

## 🚀 Setup Instructions

### GitHub Models (Default)

**Step 1: Get GitHub Token**
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scope: `read:packages`
4. Copy the token

**Step 2: Configure Environment**
```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env and add your GitHub token
GITHUB_TOKEN=ghp_your_token_here
```

**Step 3: That's it!**
- Streamlit app: `streamlit run app.py` (GitHub Models selected by default)
- CLI: `python main.py`

---

### Qwen Models via DashScope

**Step 1: Create Alibaba Cloud Account**
1. Go to: https://bailian.console.aliyun.com/
2. Sign up or login
3. Create a new API key

**Step 2: Select Your Region (⚠️ Important!)**

Regions are **NOT interchangeable**. Choose ONE:

**Option A: Singapore (Recommended for International)**
- Base URL: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`
- For: Global, non-China users
- No VPN needed
- Slightly higher latency from Asia

**Option B: Beijing (Mainland China)**
- Base URL: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- For: China-based users/deployments
- Requires China-based account
- Fastest for China users

**Option C: US Virginia (US-based)**
- Base URL: `https://dashscope-us.aliyuncs.com/compatible-mode/v1`
- For: US users
- New region, stable
- Lowest latency for US

**Step 3: Configure Environment**
```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env and add your DashScope API key
DASHSCOPE_API_KEY=sk_your_key_here
```

**Step 4: Toggle in Your Application**

**In Streamlit:**
1. Run: `streamlit run app.py`
2. Look for: **"Use Qwen Models (via DashScope)"** checkbox
3. Toggle it ON
4. Select your region from dropdown
5. Generate your book!

**In CLI:**
```bash
# Use GitHub Models (default)
python main.py

# Use Qwen Models
python main.py --qwen
```

---

## 🎨 Combined Workflow

The beauty of this setup is that you can use **different providers for text and images**:

```
Text Generation          Image Generation
┌─────────────────┐     ┌──────────────────┐
│ GitHub Models   │     │ Qwen-Image-Max   │
│ (gpt-4o-mini)   │ OR  │ (via DashScope)  │
│                 │     │                  │
│ Qwen-Plus       │     │                  │
│ (via DashScope) │     │ (Always Qwen)    │
└─────────────────┘     └──────────────────┘
        ↓                        ↓
   Book Structure          Beautiful
   & Content          Illustrations
```

### Recommended Combinations

**Development (Fastest start)**
- Text: GitHub Models
- Images: Qwen-Image-Max
- Setup time: ~5 minutes

**Production (Professional)**
- Text: Qwen
- Images: Qwen-Image-Max
- Cost: ~$0.01-0.05 per book
- Setup time: ~15 minutes

---

## 📊 Cost Comparison

### GitHub Models
- Free tier: ✅ Available
- Cost: $0.00 for development
- Limitations: Rate limits apply
- Best for: Rapid prototyping

### Qwen Models
- Free tier: ✅ Available (limited credits)
- Cost: ~$0.002 per 1K input tokens, $0.002 per 1K output tokens
- Typical book: $0.01-0.05
- Best for: Production deployments

### Qwen Images
- Cost: ~$0.02-0.05 per image
- Typical book (10 chapters × 2 images): $0.20-0.50
- Quality: Excellent for educational content

---

## 🔧 Technical Details

### API Compatibility
Both GitHub Models and Qwen use OpenAI-compatible APIs, so switching is seamless:

```python
# The config.py handles everything
from config import get_model_config

# GitHub Models
config = get_model_config(use_qwen=False)
# Returns: gpt-4o-mini endpoint

# Qwen Models  
config = get_model_config(use_qwen=True, qwen_region="singapore")
# Returns: qwen-plus via DashScope Singapore
```

### Supported Qwen Regions
```python
qwen_region Options:
- "singapore"      → Default, for international users
- "beijing"        → For China mainland
- "us-virginia"    → For US users
```

---

## ⚠️ Important Notes

### Region Selection
- **Do NOT mix API keys from different regions**
- You cannot use a Singapore key in Beijing region or vice versa
- Each region has its own separate API key
- If you change regions, get a new key from DashScope

### API Key Security
- Never commit `.env` to git (already in `.gitignore`)
- Rotate keys regularly in production
- Use different keys for dev/staging/production

### Qwen Model Availability
- `qwen-plus`: Recommended for balanced cost/quality
- `qwen-max`: Higher quality, higher cost
- Image generation always uses Qwen-Image-Max (can't be changed)

---

## 🐛 Troubleshooting

### "Missing GITHUB_TOKEN or DASHSCOPE_API_KEY"
**Solution:** Make sure your `.env` file exists and has the right values:
```bash
cp .env.example .env
# Then edit .env with your actual credentials
```

### "API key invalid in Singapore region"
**Solution:** You're using a Beijing key in Singapore region (or vice versa).
- Make sure you're using the correct DashScope key
- Choose the matching region in Streamlit or CLI

### "Qwen region not responding"
**Solution:** The region may be experiencing issues:
1. Try a different region (singapore) first
2. Check DashScope status: https://bailian.console.aliyun.com/
3. Fallback to GitHub Models while troubleshooting

### "Models too slow"
**Solution (Qwen):** You might be using Beijing region from international location:
- Switch to Singapore region for better latency
- Qwen images typically take 20-35 seconds

---

## 📚 Example Workflows

### Development (5 minutes setup)
```bash
# 1. Get GitHub token (quick signup if needed)
export GITHUB_TOKEN=ghp_xxxx

# 2. Run with GitHub Models
streamlit run app.py
# Toggle GitHub Models (default)
# Enjoy free development!
```

### Production (15 minutes setup)
```bash
# 1. Get DashScope key
export DASHSCOPE_API_KEY=sk_xxxx

# 2. Run with Qwen
python main.py --qwen
# OR open Streamlit and toggle Qwen
```

### Mixed Stack (Recommended)
```bash
# Have both configured
export GITHUB_TOKEN=ghp_xxxx
export DASHSCOPE_API_KEY=sk_xxxx

# Use GitHub Models for fast iterations
streamlit run app.py  # Toggle GitHub Models

# Switch to Qwen for final production build
streamlit run app.py  # Toggle Qwen Models
```

---

## 🎓 Learning Resources

- **GitHub Models Docs:** https://github.com/marketplace/models
- **Qwen Models:** https://qwenlm.github.io/
- **DashScope Console:** https://bailian.console.aliyun.com/
- **OpenAI API Reference:** https://platform.openai.com/docs/api-reference

---

## 🤝 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify your `.env.example` → `.env` setup
3. Ensure API keys are valid (test in DashScope console)
4. Check region selection (especially for Qwen)
5. Review logs in terminal for error messages

---

**Last Updated:** February 2026  
**Agent Framework Version:** Compatible with Microsoft Agent Framework latest  
**Supported Models:**
- GitHub: gpt-4o-mini
- Qwen: qwen-plus
- Image Gen: Qwen-Image-Max (DashScope)

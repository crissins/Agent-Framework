# ⚡ 5-MINUTE QUICK START

Get your fact-checking agent with web search running in 5 minutes.

## Step 1: Get FREE API Key (2 minutes)

Visit: **https://dashscope.aliyun.com/**

```
1. Click "Sign Up"
2. Create account (free)
3. Go to "API Keys" section
4. Click "Create New API Key"
5. Copy the key (looks like: sk-abc123xyz...)
```

## Step 2: Set Environment Variable (1 minute)

### Windows Command Prompt
```batch
set DASHSCOPE_API_KEY=sk-your_key_here
```

### Windows PowerShell
```powershell
$env:DASHSCOPE_API_KEY="sk-your_key_here"
```

## Step 3: Verify Setup (2 minutes)

```bash
python verify_setup.py
```

You should see: **✨ SETUP COMPLETE! YOU'RE READY TO USE FACT-CHECKING WITH WEB SEARCH!**

## Step 4: Run Your First Example (0 minutes, already done!)

```bash
python agents/example_fact_checking.py --example 1
```

---

## 🎉 Done!

Your fact-checking agent with **web search** is now active!

### Try These Next:

**Simple Fact-Check:**
```bash
python agents/example_fact_checking.py --example 1
```

**Multiple Claims:**
```bash
python agents/example_fact_checking.py --example 2
```

**Chapter Verification:**
```bash
python agents/example_fact_checking.py --example 3
```

**Book with Fact-Checking:**
```bash
python agents/example_fact_checking.py --example 4
```

---

## 📚 Get Full Details

- **Quick Reference:** Open `QUICK_REFERENCE.py`
- **Complete Guide:** Open `FACT_CHECK_README.md`
- **All Files:** Open `INDEX.md`

---

**That's it! You now have web search fact-checking! 🚀**

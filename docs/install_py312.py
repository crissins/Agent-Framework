#!/usr/bin/env python312
"""
Setup script to verify Python 3.12 and dependencies for Agent Framework.
Run with: python install_py312.py
"""
import sys
import subprocess

print(f"Python version: {sys.version}")
print(f"Executable: {sys.executable}\n")

packages = [
    "agent-framework==1.0.0b260212",
    "python-dotenv",
    "openai",
    "azure-identity",
    "opentelemetry-exporter-otlp-proto-grpc",
    "dashscope",
    "streamlit",
    "markdown",
    "requests",
    "pydantic",
    "aiohttp",
    "fpdf2",
    "qrcode",
    "pillow",
    "duckduckgo-search",
    "pytest",
    "black",
    "pylint",
]

print("Installing packages...")
for package in packages:
    print(f"  Installing {package}...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "--no-warn-script-location", package],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"    ⚠️  Error: {result.stderr[:100]}")
    else:
        print(f"    ✅ Success")

print("\n" + "="*60)
print("Testing imports...")
print("="*60)

try:
    from agent_framework import RawAgent
    print("✅ from agent_framework import RawAgent")
except ImportError as e:
    print(f"❌ Failed to import RawAgent: {e}")

try:
    from agent_framework.openai import OpenAIChatClient
    print("✅ from agent_framework.openai import OpenAIChatClient")
except ImportError as e:
    print(f"❌ Failed to import OpenAIChatClient: {e}")

try:
    from dotenv import load_dotenv
    print("✅ from dotenv import load_dotenv")
except ImportError as e:
    print(f"❌ Failed to import load_dotenv: {e}")

print("\n✅ Python 3.12 setup complete!")

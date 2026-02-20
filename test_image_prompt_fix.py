import sys
import os
from unittest.mock import MagicMock

# Create a mock for dashscope that can handle imports
mock_dashscope = MagicMock()
sys.modules["dashscope"] = mock_dashscope

# Also mock utils.retry since it might not be in path or we don't want to wait
sys.modules["utils.retry"] = MagicMock()
sys.modules["utils.retry"].sync_retry = lambda *args, **kwargs: lambda f: f

# Now we can safely import
from agents.qwen_image_agent import _enhance_prompt_with_style

def test_prompt_construction():
    print("🧪 Testing Image Prompt Construction...")
    
    # Test case 1: Spanish input with specific camera settings
    title = "La IA en México"
    summary = "Un capítulo sobre el futuro de la IA."
    raw_prompt = f"{title}: {summary}"
    
    enhanced = _enhance_prompt_with_style(
        prompt=raw_prompt,
        style="3D",
        shot_size="Long Shot",
        perspective="High Angle",
        lens_type="Telephoto",
        lighting="Studio",
        language="Spanish"
    )
    
    print("\n📋 Generated Prompt:")
    print("-" * 40)
    print(enhanced)
    print("-" * 40)
    
    # Verifications
    failures = []
    
    if "Camera View: Long Shot" not in enhanced:
        failures.append("❌ Missing 'Long Shot'")
    if "High Angle" not in enhanced:
        failures.append("❌ Missing 'High Angle'")
    if "Telephoto" not in enhanced:
        failures.append("❌ Missing 'Telephoto'")
    if "Studio" not in enhanced:
        failures.append("❌ Missing 'Studio'")
    if "NO TEXT" not in enhanced:
        failures.append("❌ Missing 'NO TEXT' instruction")
    if "Spanish-speaking" not in enhanced:
        failures.append("❌ Missing language context")
        
    if failures:
        print("\n❌ FAILED Check:")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)
    else:
        print("\n✅ All Checks Passed! Prompt is correctly formatted.")

if __name__ == "__main__":
    test_prompt_construction()

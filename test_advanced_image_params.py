import sys
import os
from agents.qwen_image_agent import _enhance_prompt_with_style

def test_enhance_prompt():
    print("🧪 Testing _enhance_prompt_with_style...")

    # Test Case 1: All parameters provided
    prompt = "A futuristic city"
    style = "3D"
    shot_size = "Wide Angle"
    perspective = "Bird's Eye View"
    lens_type = "Macro"
    lighting = "Cinematic"

    enhanced = _enhance_prompt_with_style(
        prompt, 
        style, 
        shot_size=shot_size, 
        perspective=perspective, 
        lens_type=lens_type, 
        lighting=lighting
    )

    print(f"\n[Case 1] Input: {prompt}, {style}, {shot_size}, {perspective}, {lens_type}, {lighting}")
    print(f"[Case 1] Output:\n{enhanced}\n")

    assert "3D rendering style" in enhanced, "Style description missing"
    assert "Wide Angle" in enhanced, "Shot size missing"
    assert "Bird's Eye View" in enhanced, "Perspective missing"
    assert "Macro" in enhanced, "Lens type missing"
    assert "Cinematic" in enhanced, "Lighting missing"
    print("✅ Case 1 Passed")

    # Test Case 2: No optional parameters
    prompt2 = "A cat"
    style2 = "watercolor"
    enhanced2 = _enhance_prompt_with_style(prompt2, style2)
    
    print(f"\n[Case 2] Input: {prompt2}, {style2} (No optional params)")
    print(f"[Case 2] Output:\n{enhanced2}\n")
    
    assert "Watercolor painting style" in enhanced2, "Style description missing"
    assert "medium shot" in enhanced2 or "Camera:" in enhanced2, "Default camera settings missing"
    assert "natural lighting" in enhanced2 or "Lighting:" in enhanced2, "Default lighting missing"
    print("✅ Case 2 Passed")

if __name__ == "__main__":
    try:
        test_enhance_prompt()
        print("\n🎉 All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test Failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        sys.exit(1)

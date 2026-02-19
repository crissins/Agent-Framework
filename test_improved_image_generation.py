#!/usr/bin/env python3
"""
Test script to demonstrate the improved image generation using Qwen best practices.
Tests the new functionality with prompt dictionary elements.
"""

import asyncio
from agents.qwen_image_agent import generate_image_with_qwen, generate_chapter_image

def test_basic_generation():
    """Test basic image generation with enhanced prompt engineering."""
    print("Testing basic image generation with Qwen best practices...")
    
    # Test with basic prompt and style
    # Since API key might not be set, we're just checking that the function can be called
    try:
        result = asyncio.run(generate_image_with_qwen(
            prompt="A cute panda eating bamboo in a forest",
            style="educational",
            size="1472*1104"
        ))
        
        if result:
            print(f"✓ Basic generation successful: {result.url}")
        else:
            print("✗ Basic generation failed (likely due to missing API key)")
    except Exception as e:
        print(f"✗ Basic generation failed with error: {e}")
        result = None
    
    return result


async def test_advanced_generation():
    """Test advanced image generation with all prompt dictionary elements."""
    print("\nTesting advanced image generation with prompt dictionary elements...")
    
    # Test with all prompt dictionary elements
    try:
        result = await generate_image_with_qwen(
            prompt="A futuristic cityscape with flying cars and neon lights",
            style="3D",
            shot_size="wide shot",
            perspective="bird's eye view",
            lens_type="telephoto",
            lighting="neon lighting",
            size="1664*928"
        )
        
        if result:
            print(f"✓ Advanced generation successful: {result.url}")
        else:
            print("✗ Advanced generation failed (likely due to missing API key)")
    except Exception as e:
        print(f"✗ Advanced generation failed with error: {e}")
        result = None
    
    return result


async def test_chapter_image_generation():
    """Test chapter image generation with enhanced features."""
    print("\nTesting chapter image generation with enhanced features...")
    
    try:
        result = await generate_chapter_image(
            title="The Solar System",
            summary="An exploration of planets, moons, and celestial bodies in our solar system",
            style="educational",
            shot_size="long shot",
            perspective="low angle",
            lens_type="wide angle",
            lighting="dramatic lighting",
            size="1328*1328"
        )
        
        if result:
            print(f"✓ Chapter image generation successful: {result.url}")
        else:
            print("✗ Chapter image generation failed (likely due to missing API key)")
    except Exception as e:
        print(f"✗ Chapter image generation failed with error: {e}")
        result = None
    
    return result


async def test_artistic_styles():
    """Test different artistic styles supported by the enhanced system."""
    print("\nTesting various artistic styles...")
    
    styles_to_test = [
        ("watercolor", "A field of wildflowers in spring"),
        ("surrealism", "A melting clock on a tree branch"),
        ("clay", "A friendly cat sitting on a windowsill"),
        ("origami", "A paper crane flying over mountains"),
        ("gongbi", "A traditional Chinese landscape with pagoda")
    ]
    
    results = []
    for style, prompt in styles_to_test:
        print(f"  Testing {style} style...")
        try:
            result = await generate_image_with_qwen(
                prompt=prompt,
                style=style,
                size="1104*1472"
            )
            
            if result:
                print(f"    ✓ {style} generation successful: {result.url}")
                results.append(result)
            else:
                print(f"    ✗ {style} generation failed (likely due to missing API key)")
        except Exception as e:
            print(f"    ✗ {style} generation failed with error: {e}")
    
    return results


def main():
    """Run all tests to demonstrate the improved image generation capabilities."""
    print("="*80)
    print("TESTING IMPROVED IMAGE GENERATION WITH QWEN BEST PRACTICES")
    print("="*80)
    
    # Run tests
    basic_result = test_basic_generation()
    advanced_result = asyncio.run(test_advanced_generation())
    chapter_result = asyncio.run(test_chapter_image_generation())
    style_results = asyncio.run(test_artistic_styles())
    total_styles = len([
        ("watercolor", "A field of wildflowers in spring"),
        ("surrealism", "A melting clock on a tree branch"),
        ("clay", "A friendly cat sitting on a windowsill"),
        ("origami", "A paper crane flying over mountains"),
        ("gongbi", "A traditional Chinese landscape with pagoda")
    ])
    
    print("\n" + "="*80)
    print("SUMMARY OF TEST RESULTS")
    print("="*80)
    
    print(f"Basic generation: {'✓ SUCCESS' if basic_result else '✗ FAILED'}")
    print(f"Advanced generation: {'✓ SUCCESS' if advanced_result else '✗ FAILED'}")
    print(f"Chapter image generation: {'✓ SUCCESS' if chapter_result else '✗ FAILED'}")
    print(f"Artistic style tests: {len(style_results)} out of {total_styles} succeeded")
    
    print("\nThe improved image generation system now supports:")
    print("- Advanced prompt formula: Entity + Environment + Style + Camera language + Atmosphere + Detail modifiers")
    print("- All 5 prompt dictionary elements: shot size, perspective, lens type, style, and lighting")
    print("- 15+ different artistic styles including 3D, watercolor, surrealism, origami, gongbi, etc.")
    print("- Negative prompting to prevent unwanted text/typography in images")
    print("- Better structured prompts following Qwen best practices")


if __name__ == "__main__":
    main()
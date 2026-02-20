import os
from dotenv import load_dotenv
import dashscope
from http import HTTPStatus

# Load environment variables
load_dotenv()

def check_api_key():
    api_key = os.getenv("DASHSCOPE_API_KEY")
    print(f"DEBUG: DASHSCOPE_API_KEY found: {bool(api_key)}")
    if api_key:
        print(f"DEBUG: Key length: {len(api_key)}")
        print(f"DEBUG: First 5 chars: '{api_key[:5]}'")
        print(f"DEBUG: Last 5 chars: '{api_key[-5:]}'")
        print(f"DEBUG: Contains whitespace? {' ' in api_key}")
        print(f"DEBUG: Contains quotes? {'\"' in api_key or '\'' in api_key}")
        
        endpoints = [
            ("Default", None),
            ("International (Singapore)", "https://dashscope-intl.aliyuncs.com/api/v1"),
            ("US (Virginia)", "https://dashscope-us.aliyuncs.com/api/v1"),
            ("China (Beijing)", "https://dashscope.aliyuncs.com/api/v1")
        ]

        for name, url in endpoints:
            print(f"\n--- Testing Endpoint: {name} ---")
            if url:
                dashscope.base_http_api_url = url
                print(f"Set base_http_api_url to: {url}")
            else:
                # Reset to default (whatever library uses) - unfortunately library doesn't have a simple reset, 
                # but we can try setting it to the default string if we knew it, or just testing strictly known URLs.
                # For this loop, if it's None, we skip explicit setting if we haven't set it yet, 
                # or we might need to rely on the fact that we test this first.
                pass

            # Test text generation
            try:
                print("  Trying text generation...")
                resp = dashscope.Generation.call(
                    api_key=api_key,
                    model='qwen-turbo',
                    prompt='Hello!'
                )
                if resp.status_code == HTTPStatus.OK:
                    print(f"  [SUCCESS] Key is valid for region: {name}")
                    return # Exit if found
                else:
                    print(f"  [FAILED] Failed: {resp.code} - {resp.message}")
            except Exception as e:
                print(f"  [FAILED] Exception: {e}")


if __name__ == "__main__":
    check_api_key()

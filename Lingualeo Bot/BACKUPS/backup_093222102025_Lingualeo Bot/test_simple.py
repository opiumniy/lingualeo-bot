#!/usr/bin/env python3
import asyncio
import sys
import os
from pathlib import Path

# Add current directory to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api_client import LingualeoAPIClient

async def test():
    print("Testing bot functionality...")

    client = LingualeoAPIClient(user_id=531253663)

    # Test cookie loading
    print("Testing cookie loading...")
    success = await client.load_user_cookies_async(531253663)

    if success:
        print("SUCCESS: Cookies loaded!")
        print(f"Cookie length: {len(client.cookies)}")

        # Test API call
        print("Testing API call...")
        try:
            response = client.process_training_answer_batch({"123": 1})
            print("SUCCESS: API call works!")
            print(f"Response type: {type(response)}")
        except Exception as e:
            print(f"API Error: {e}")
    else:
        print("FAILED: Could not load cookies")

if __name__ == "__main__":
    asyncio.run(test())
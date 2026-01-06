#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple script to extract repeat words count from Lingualeo API
Uses getLearningMain API endpoint to get training statistics
Requires user_id as CLI argument for multi-user support
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_client import LingualeoAPIClient


def get_repeat_count_api(user_id: int = None):
    """Extract the number of words left for repetition using API"""
    try:
        client = LingualeoAPIClient(user_id=user_id)
        
        if user_id:
            if not client.load_cookies(user_id):
                print(f"ERROR: No cookies found for user {user_id}")
                return None
        else:
            print("ERROR: user_id is required")
            return None

        response = client.get_learning_main()
        print("API Response received")

        script_dir = os.path.dirname(os.path.abspath(__file__))
        debug_file = os.path.join(script_dir, f"api_response_debug_{user_id}.json")
        with open(debug_file, "w", encoding="utf-8") as f:
            json.dump(response, f, indent=2, ensure_ascii=False)
        print(f"API response saved to {debug_file}")

        if response.get('status') == 'ok':
            data = response.get('data', [])

            for section in data:
                if 'word' in section:
                    word_trainings = section['word']
                    for training in word_trainings:
                        if training.get('tag') == 'repetition':
                            counter = training.get('counter', {})
                            words_count = counter.get('words', 0)
                            print(f"Found repetition training with {words_count} words")
                            return words_count

            print("Repetition training not found in response")
            return None
        else:
            print(f"API returned error status: {response.get('status')}")
            return None

    except Exception as e:
        print(f"Error calling API: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main function"""
    print("=== Lingualeo Repeat Words Counter (API) ===")
    
    if len(sys.argv) < 2:
        print("ERROR: user_id argument required")
        print("Usage: python get_repeat_count.py <user_id>")
        sys.exit(1)
    
    try:
        user_id = int(sys.argv[1])
    except ValueError:
        print(f"ERROR: Invalid user_id: {sys.argv[1]}")
        sys.exit(1)
    
    print(f"Getting repeat count for user_id: {user_id}")

    repeat_count = get_repeat_count_api(user_id)

    if repeat_count is not None:
        print(f"SUCCESS! Repeat words count: {repeat_count}")

        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, f"repeat_count_{user_id}.txt")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(str(repeat_count))
        print(f"Count saved to {output_file}")
    else:
        print("Could not extract repeat words count")
        sys.exit(1)


if __name__ == "__main__":
    main()

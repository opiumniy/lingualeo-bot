#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple script to extract repeat words count from Lingualeo API
Uses getLearningMain API endpoint to get training statistics
"""

import json
import os
from api_client import LingualeoAPIClient


def get_repeat_count_api():
    """Extract the number of words left for repetition using API"""
    try:
        client = LingualeoAPIClient()

        # Get learning main data
        response = client.get_learning_main()
        print("API Response received")

        # Debug: save response to file
        with open("api_response_debug.json", "w", encoding="utf-8") as f:
            json.dump(response, f, indent=2, ensure_ascii=False)
        print("API response saved to api_response_debug.json")

        if response.get('status') == 'ok':
            data = response.get('data', [])

            # Find word training data
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
        return None


def main():
    """Main function"""
    print("=== Lingualeo Repeat Words Counter (API) ===")

    repeat_count = get_repeat_count_api()

    if repeat_count is not None:
        print(f"SUCCESS! Repeat words count: {repeat_count}")

        # Write to file
        output_file = "repeat_count.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(str(repeat_count))
        print(f"Count saved to {output_file}")
    else:
        print("Could not extract repeat words count")


if __name__ == "__main__":
    main()
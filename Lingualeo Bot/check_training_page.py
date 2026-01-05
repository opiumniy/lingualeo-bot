#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script for loading Lingualeo training page and extracting repeat words count
Target element: div with classes 'll-leokit__training-card__subtitle ll-leokit__training-card__subtitle-counter'
Returns the number of words left for repetition
"""

import time
import json
import re
import os
import threading
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


def timeout_wrapper(func, timeout_seconds=10):
    """Wrapper to run function with timeout"""
    result = [None]
    exception = [None]

    def target():
        try:
            result[0] = func()
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout_seconds)

    if thread.is_alive():
        # Thread is still running, timeout occurred
        raise TimeoutError(f"Function execution timed out after {timeout_seconds} seconds")

    if exception[0]:
        raise exception[0]

    return result[0]


def load_cookies_from_file(cookie_file_path):
    """Load cookies from file"""
    try:
        with open(cookie_file_path, 'r', encoding='utf-8') as file:
            cookie_string = file.read().strip()

        # Parse cookies from simple format: name1=value1; name2=value2
        cookies = []
        for cookie_pair in cookie_string.split(';'):
            cookie_pair = cookie_pair.strip()
            if not cookie_pair:
                continue

            if '=' in cookie_pair:
                name, value = cookie_pair.split('=', 1)
                cookie = {
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.lingualeo.com',  # Default domain for Lingualeo
                    'path': '/',
                    'secure': False,
                }
                cookies.append(cookie)

        print(f"Loaded {len(cookies)} cookies: {[c['name'] for c in cookies]}")
        return cookies
    except Exception as e:
        print(f"Error loading cookies: {e}")
        return []


def save_page_as_mhtml(driver, filename):
    """Save current page as MHTML file using Chrome DevTools Protocol"""
    try:
        # Enable Page domain in DevTools
        driver.execute_cdp_cmd('Page.enable', {})

        # Get the current page as MHTML
        result = driver.execute_cdp_cmd('Page.captureSnapshot', {'format': 'mhtml'})

        # Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(result['data'])

        print(f"Page saved as MHTML: {filename}")
        return True
    except Exception as e:
        print(f"Error saving MHTML: {e}")
        return False


def get_repeat_words_count(driver):
    """Extract the number of words left for repetition from the specific element"""
    try:
        # First, look for elements containing "358 слов" pattern (from the logs)
        print("Looking for elements with '358 слов' pattern...")
        pattern_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '358 слов')]")

        for element in pattern_elements:
            text = element.text.strip()
            print(f"Found element with 358 pattern: '{text}'")

            # Extract 358 from the text
            numbers = re.findall(r'\d+', text)
            if numbers:
                count = int(numbers[0])
                print(f"Extracted count from pattern: {count}")
                return count

        # Look for any element containing "Повторение" and extract number from it
        print("Looking for 'Повторение' elements with numbers...")
        repeat_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Повторение')]")

        for element in repeat_elements:
            text = element.text.strip()
            print(f"Found repeat element: '{text}'")

            # Extract numbers from the text
            numbers = re.findall(r'\d+', text)
            if numbers:
                count = int(numbers[0])
                print(f"Extracted count from repeat element: {count}")
                return count

        # Try multiple selectors for the target element
        selectors = [
            ".ll-leokit__training-card__subtitle.ll-leokit__training-card__subtitle-counter",
            "[class*='ll-leokit__training-card__subtitle-counter']",
            "[class*='training-card__subtitle-counter']",
            ".ll-leokit__training-card__subtitle",
            "#ll-leokit__training-card__subtitle-counter",
            "[id*='ll-leokit__training-card__subtitle-counter']"
        ]

        for selector in selectors:
            try:
                print(f"Trying selector: {selector}")
                elements = driver.find_elements(By.CSS_SELECTOR, selector)

                for element in elements:
                    text = element.text.strip()
                    print(f"Found element with text: '{text}'")

                    # Extract numbers from the text
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        count = int(numbers[0])  # Take the first number found
                        print(f"Extracted count: {count}")
                        return count

            except Exception as e:
                print(f"Error with selector {selector}: {e}")
                continue

        # If CSS selectors don't work, try XPath
        xpath_selectors = [
            "//div[contains(@class, 'll-leokit__training-card__subtitle') and contains(@class, 'll-leokit__training-card__subtitle-counter')]",
            "//div[contains(@class, 'training-card__subtitle-counter')]",
            "//*[@class='ll-leokit__training-card__subtitle ll-leokit__training-card__subtitle-counter']"
        ]

        for xpath in xpath_selectors:
            try:
                print(f"Trying XPath: {xpath}")
                elements = driver.find_elements(By.XPATH, xpath)

                for element in elements:
                    text = element.text.strip()
                    print(f"Found element with text: '{text}'")

                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        count = int(numbers[0])
                        print(f"Extracted count: {count}")
                        return count

            except Exception as e:
                print(f"Error with XPath {xpath}: {e}")
                continue

        # If specific selectors don't work, try broader search
        print("Trying broader search for counter elements...")
        try:
            # Look for any elements that contain numbers and might be related to training
            all_elements = driver.find_elements(By.TAG_NAME, "*")
            potential_counters = []
            all_numbers_found = []

            for element in all_elements[:100]:  # Check first 100 elements for faster execution
                try:
                    text = element.text.strip()
                    if text and text.isdigit():
                        value = int(text)
                        all_numbers_found.append(value)

                        # Skip very small or very large numbers that are unlikely to be counters
                        if 1 <= value <= 10000:
                            element_class = element.get_attribute("class") or ""
                            element_id = element.get_attribute("id") or ""

                            # Check if element or its parent has training-related classes
                            try:
                                parent = element.find_element(By.XPATH, "..")
                                parent_class = parent.get_attribute("class") or ""
                            except:
                                parent_class = ""

                            # Check for training-related keywords
                            combined_info = f"{element_class} {element_id} {parent_class}".lower()

                            # Look for elements that might be counters based on class names or context
                            if (any(keyword in combined_info for keyword in ["training", "card", "repeat", "counter", "subtitle", "leokit"]) or
                                value > 10):  # Numbers > 10 are more likely to be meaningful counters

                                potential_counters.append({
                                    'value': value,
                                    'element_class': element_class,
                                    'element_id': element_id,
                                    'parent_class': parent_class,
                                    'element_tag': element.tag_name,
                                    'text': text
                                })

                except:
                    continue

            # Print diagnostic information
            print(f"All numbers found on page: {all_numbers_found}")

            if potential_counters:
                print(f"Found {len(potential_counters)} potential counter elements:")
                for counter in potential_counters:
                    print(f"  Value: {counter['value']}, Tag: {counter['element_tag']}, Class: {counter['element_class']}, ID: {counter['element_id']}, Parent: {counter['parent_class']}")

                # Return the first reasonable counter (you can adjust logic here)
                for counter in potential_counters:
                    # Prioritize elements with training-related classes
                    if any(keyword in counter['element_class'].lower() for keyword in ["training", "card", "repeat", "counter"]):
                        print(f"Selected counter based on training-related class: {counter['value']}")
                        return counter['value']

                # If no training-related classes found, return the largest reasonable number
                if len(potential_counters) > 1:
                    largest_counter = max(potential_counters, key=lambda x: x['value'])
                    print(f"Selected largest counter: {largest_counter['value']}")
                    return largest_counter['value']

                # Otherwise return the first one
                selected = potential_counters[0]
                print(f"Selected first counter: {selected['value']}")
                return selected['value']
            else:
                print("No potential counter elements found")
                print("Available numbers:", all_numbers_found)

                # Try to find elements with data attributes that might contain counts
                print("Looking for data attributes with numbers...")
                try:
                    elements_with_data = driver.execute_script(
                        "const elements = document.querySelectorAll('*');"
                        "const result = [];"
                        "for (let el of elements) {"
                        "    for (let attr of el.attributes) {"
                        "        if (attr.name.startsWith('data-') && /^\\d+$/.test(attr.value)) {"
                        "            result.push({"
                        "                tagName: el.tagName,"
                        "                dataAttr: attr.name,"
                        "                dataValue: attr.value,"
                        "                className: el.className || 'no-class'"
                        "            });"
                        "        }"
                        "    }"
                        "}"
                        "return result;"
                    )

                    for element_data in elements_with_data:
                        if 1 <= int(element_data['dataValue']) <= 10000:
                            print(f"Found data attribute '{element_data['dataAttr']}' with value: {element_data['dataValue']}")
                            return int(element_data['dataValue'])

                except Exception as e:
                    print(f"Error searching data attributes: {e}")

                for element in elements_with_data[:20]:  # Check first 20 elements with data attributes
                    for attr_name in element.get_property("attributes"):
                        if attr_name.startswith('data-'):
                            attr_value = element.get_attribute(attr_name)
                            if attr_value and attr_value.isdigit():
                                value = int(attr_value)
                                if 1 <= value <= 10000:
                                    print(f"Found data attribute '{attr_name}' with value: {value}")
                                    return value

                # Try to find numbers in JavaScript variables or JSON-like content
                print("Looking for numbers in script content...")
                scripts = driver.find_elements(By.TAG_NAME, "script")
                for script in scripts[:3]:  # Check first 3 scripts for faster execution
                    try:
                        content = script.get_attribute("textContent") or ""
                        if content:
                            # Look for patterns like "count": 123 or similar
                            json_patterns = re.findall(r'["\'](?:count|total|number|amount)["\']\s*:\s*(\d+)', content)
                            if json_patterns:
                                for number in json_patterns:
                                    value = int(number)
                                    if 1 <= value <= 10000:
                                        print(f"Found number in script JSON: {value}")
                                        return value
                    except:
                        continue

                print("No numbers found in data attributes or scripts")

            # Print all potential counters found
            if potential_counters:
                print(f"Found {len(potential_counters)} potential counter elements:")
                for counter in potential_counters:
                    print(f"  Value: {counter['value']}, Tag: {counter['element_tag']}, Class: {counter['element_class']}, ID: {counter['element_id']}, Parent: {counter['parent_class']}")

                # Return the first reasonable counter (you can adjust logic here)
                for counter in potential_counters:
                    # Prioritize elements with training-related classes
                    if any(keyword in counter['element_class'].lower() for keyword in ["training", "card", "repeat", "counter"]):
                        print(f"Selected counter based on training-related class: {counter['value']}")
                        return counter['value']

                # If no training-related classes found, return the largest reasonable number
                if len(potential_counters) > 1:
                    largest_counter = max(potential_counters, key=lambda x: x['value'])
                    print(f"Selected largest counter: {largest_counter['value']}")
                    return largest_counter['value']

                # Otherwise return the first one
                selected = potential_counters[0]
                print(f"Selected first counter: {selected['value']}")
                return selected['value']
            else:
                print("No potential counter elements found")

        except Exception as e:
            print(f"Error in broader search: {str(e)[:100]}")

        return None

    except Exception as e:
        print(f"Error in get_repeat_words_count: {e}")
        return None


def check_training_page():
    """Main function for checking training page and getting repeat count"""
    driver = None
    try:
        # Chrome settings
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # No interface
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # Create driver
        print("Starting Chrome driver...")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

        # Set implicit wait for all operations
        driver.implicitly_wait(10)

        # Load cookies
        print("Loading cookies...")
        cookies = load_cookies_from_file('cookies_current.txt')

        if not cookies:
            print("Failed to load cookies!")
            return None

        # Navigate to Lingualeo page
        print("Navigating to https://lingualeo.com/ru/training...")
        driver.get("https://lingualeo.com/ru/training")

        # Wait for page to load with timeout
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("Page loaded successfully")
        except TimeoutException:
            print("Timeout waiting for page load")

        # Add cookies to browser
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"Error adding cookie {cookie.get('name', 'unknown')}: {e}")

        # Refresh page with cookies
        print("Refreshing page with cookies...")
        driver.refresh()

        # Wait for page load
        print("Waiting for page to load...")
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("Page refreshed successfully")
        except TimeoutException:
            print("Timeout waiting for page refresh")

        # Wait for training cards to be present
        try:
            WebDriverWait(driver, 10).until(
                lambda driver: len(driver.find_elements(By.XPATH, "//*[contains(text(), 'Повторение')]")) > 0
            )
            print("Found 'Повторение' elements")
        except TimeoutException:
            print("No 'Повторение' elements found")

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mhtml_filename = f"lingualeo_training_{timestamp}.mhtml"

        # Save page as MHTML for debugging
        print(f"Saving page as MHTML: {mhtml_filename}")
        if save_page_as_mhtml(driver, mhtml_filename):
            print(f"Successfully saved: {mhtml_filename}")
        else:
            print("Failed to save MHTML file")

        # Find and click on "Тренировать" button in "Повторение" section
        print("Looking for 'Повторение' section and 'Тренировать' button...")
        try:
            # Find the "Повторение" section first
            repeat_sections = driver.find_elements(By.XPATH, "//*[contains(text(), 'Повторение')]")

            for section in repeat_sections:
                print(f"Found repeat section: '{section.text}'")

                # Look for "Тренировать" button near this section
                try:
                    # Try to find button in the same parent container
                    parent = section.find_element(By.XPATH, "..")
                    train_buttons = parent.find_elements(By.XPATH, ".//*[contains(text(), 'Тренировать')]")

                    if train_buttons:
                        button = train_buttons[0]
                        print(f"Found 'Тренировать' button: '{button.text}'")

                        # Click the button
                        button.click()
                        print("Clicked 'Тренировать' button")

                        # Wait for page transition
                        try:
                            WebDriverWait(driver, 10).until(
                                lambda driver: 'repetition' in driver.current_url or 'utm_action=10' in driver.current_url
                            )
                            print("Page transition completed")
                        except TimeoutException:
                            print("Timeout waiting for page transition")

                        # Check if URL changed (indicates successful transition)
                        current_url = driver.current_url
                        if 'repetition' in current_url or 'utm_action=10' in current_url:
                            print(f"Successfully navigated to: {current_url}")

                            # Now look for the counter on the new page
                            repeat_count = get_repeat_words_count(driver)
                            if repeat_count:
                                return repeat_count
                        else:
                            print(f"URL didn't change, still at: {current_url}")
                    else:
                        print("No 'Тренировать' button found near repeat section")

                except Exception as e:
                    print(f"Error clicking button: {e}")
                    continue

        except Exception as e:
            print(f"Error finding repeat section: {e}")

        # Fallback: try to find counter on current page
        print("Trying to find counter on current page...")
        repeat_count = get_repeat_words_count(driver)

        if repeat_count is not None:
            print(f"SUCCESS! Found repeat words count: {repeat_count}")
            return repeat_count
        else:
            print("Could not find repeat words count")
            return None

    except Exception as e:
        print(f"Error running script: {e}")
        return False

    finally:
        if driver:
            print("Closing browser...")
            driver.quit()


def main():
    """Main function"""
    print("=== Lingualeo Repeat Words Counter ===")
    print("Loading training page and extracting repeat words count...")

    try:
        repeat_count = timeout_wrapper(check_training_page, 10)

        if repeat_count is not None:
            print(f"\nRESULT: SUCCESS! Repeat words count: {repeat_count}")
            return repeat_count
        else:
            print("\nRESULT: Could not extract repeat words count")
            return None
    except TimeoutError:
        print("\nRESULT: Script timed out after 10 seconds")
        return None


if __name__ == "__main__":
    main()
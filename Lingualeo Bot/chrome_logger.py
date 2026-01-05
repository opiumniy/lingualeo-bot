#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chrome Logger - Interactive browser session with action logging
Allows manual exploration of Lingualeo training page while recording all user actions
"""

import time
import json
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


class ChromeLogger:
    def __init__(self):
        self.driver = None
        self.actions_log = []
        self.start_time = None
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def load_cookies_from_file(self, cookie_file_path):
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
                        'domain': '.lingualeo.com',
                        'path': '/',
                        'secure': False,
                    }
                    cookies.append(cookie)

            print(f"Loaded {len(cookies)} cookies: {[c['name'] for c in cookies]}")
            return cookies
        except Exception as e:
            print(f"Error loading cookies: {e}")
            return []

    def log_action(self, action_type, details, timestamp=None):
        """Log user action with timestamp"""
        if timestamp is None:
            timestamp = time.time() - self.start_time

        action = {
            'timestamp': timestamp,
            'type': action_type,
            'details': details,
            'session_id': self.session_id
        }

        self.actions_log.append(action)
        print(f"[{timestamp:.2f}] {action_type.upper()}: {details}")

    def inject_logging_script(self):
        """Inject JavaScript for comprehensive action logging"""
        logging_script = """
        (function() {
            const logger = {
                actions: [],

                log: function(type, details) {
                    const action = {
                        type: type,
                        details: details,
                        timestamp: Date.now(),
                        url: window.location.href,
                        title: document.title
                    };
                    this.actions.push(action);

                    // Also display on page for immediate feedback
                    const logDiv = document.getElementById('action-log') || this.createLogDiv();
                    const logEntry = document.createElement('div');
                    logEntry.style.cssText = 'background: #f0f0f0; margin: 2px; padding: 5px; border-radius: 3px; font-family: monospace; font-size: 12px;';
                    logEntry.innerHTML = `<strong>${type}:</strong> ${JSON.stringify(details)}`;
                    logDiv.appendChild(logEntry);

                    // Keep only last 20 entries
                    while (logDiv.children.length > 20) {
                        logDiv.removeChild(logDiv.firstChild);
                    }

                    console.log(`[ACTION LOG] ${type}:`, details);
                },

                createLogDiv: function() {
                    const div = document.createElement('div');
                    div.id = 'action-log';
                    div.style.cssText = 'position: fixed; top: 10px; right: 10px; width: 400px; height: 300px; overflow-y: auto; background: white; border: 2px solid #333; padding: 10px; z-index: 10000; font-size: 11px;';
                    document.body.appendChild(div);
                    return div;
                }
            };

            // Mouse events
            document.addEventListener('click', function(e) {
                logger.log('click', {
                    tag: e.target.tagName,
                    id: e.target.id || 'no-id',
                    class: e.target.className || 'no-class',
                    text: e.target.textContent?.substring(0, 50) || 'no-text',
                    x: e.clientX,
                    y: e.clientY
                });
            });

            document.addEventListener('dblclick', function(e) {
                logger.log('dblclick', {
                    tag: e.target.tagName,
                    id: e.target.id || 'no-id',
                    class: e.target.className || 'no-class'
                });
            });

            document.addEventListener('contextmenu', function(e) {
                logger.log('right_click', {
                    tag: e.target.tagName,
                    id: e.target.id || 'no-id',
                    class: e.target.className || 'no-class'
                });
            });

            // Keyboard events
            document.addEventListener('keydown', function(e) {
                if (e.key.length === 1 || e.key === 'Enter' || e.key === 'Backspace' || e.key === 'Delete') {
                    logger.log('keydown', {
                        key: e.key,
                        target_tag: e.target.tagName,
                        target_type: e.target.type || 'no-type'
                    });
                }
            });

            // Scroll events (throttled)
            let scrollTimeout;
            document.addEventListener('scroll', function(e) {
                if (!scrollTimeout) {
                    scrollTimeout = setTimeout(() => {
                        logger.log('scroll', {
                            scrollX: window.scrollX,
                            scrollY: window.scrollY,
                            maxScroll: Math.max(
                                document.body.scrollHeight - window.innerHeight,
                                document.documentElement.scrollHeight - window.innerHeight
                            )
                        });
                        scrollTimeout = null;
                    }, 500);
                }
            });

            // Form events
            document.addEventListener('input', function(e) {
                if (e.target.value) {
                    logger.log('input', {
                        tag: e.target.tagName,
                        type: e.target.type,
                        value_length: e.target.value.length,
                        name: e.target.name || 'no-name'
                    });
                }
            });

            document.addEventListener('focus', function(e) {
                logger.log('focus', {
                    tag: e.target.tagName,
                    type: e.target.type || 'no-type',
                    id: e.target.id || 'no-id'
                });
            });

            document.addEventListener('blur', function(e) {
                logger.log('blur', {
                    tag: e.target.tagName,
                    type: e.target.type || 'no-type',
                    id: e.target.id || 'no-id'
                });
            });

            // Page events
            window.addEventListener('load', function() {
                logger.log('page_load', {
                    url: window.location.href,
                    title: document.title,
                    timestamp: Date.now()
                });
            });

            window.addEventListener('beforeunload', function() {
                logger.log('page_unload', {
                    url: window.location.href,
                    time_spent: Date.now() - performance.now()
                });
            });

            // Network events (AJAX requests)
            const originalFetch = window.fetch;
            window.fetch = function(...args) {
                logger.log('fetch', {
                    url: args[0],
                    method: args[1]?.method || 'GET'
                });
                return originalFetch.apply(this, args);
            };

            // Store logger globally for access from console
            window.actionLogger = logger;

            console.log('Action logging initialized. Use window.actionLogger.actions to see logged actions.');
        })();
        """

        try:
            self.driver.execute_script(logging_script)
            print("Action logging script injected successfully")
        except Exception as e:
            print(f"Error injecting logging script: {e}")

    def start_session(self):
        """Start interactive Chrome session with logging"""
        try:
            # Chrome settings for interactive session
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")  # Reduce resource usage

            print("Starting Chrome with logging...")
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )

            # Set implicit wait for all operations
            self.driver.implicitly_wait(15)

            self.start_time = time.time()

            # Load cookies
            print("Loading cookies...")
            cookies = self.load_cookies_from_file('cookies_current.txt')

            if cookies:
                # Navigate to Lingualeo first
                print("Navigating to Lingualeo...")
                self.driver.get("https://lingualeo.com/")

                # Wait for page to load with timeout
                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    print("Page loaded successfully")
                except TimeoutException:
                    print("Timeout waiting for page load")

                # Add cookies
                for cookie in cookies:
                    try:
                        self.driver.add_cookie(cookie)
                    except Exception as e:
                        print(f"Error adding cookie {cookie.get('name', 'unknown')}: {e}")

                # Navigate to training page with cookies
                print("Navigating to training page...")
                self.driver.get("https://lingualeo.com/ru/training")

                # Wait for page to load with timeout
                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    print("Training page loaded successfully")
                except TimeoutException:
                    print("Timeout waiting for training page load")

                self.log_action("navigation", "Navigated to https://lingualeo.com/ru/training with cookies")
            else:
                print("No cookies loaded, navigating directly...")
                self.driver.get("https://lingualeo.com/ru/training")

                # Wait for page to load with timeout
                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    print("Training page loaded successfully")
                except TimeoutException:
                    print("Timeout waiting for training page load")

                self.log_action("navigation", "Navigated to https://lingualeo.com/ru/training without cookies")

            # Inject logging script
            self.inject_logging_script()

            print("\n" + "="*60)
            print("CHROME LOGGER SESSION STARTED")
            print("="*60)
            print("Browser window is now open for manual interaction.")
            print("All your actions will be logged.")
            print("Close the browser window when finished.")
            print("="*60)

            # Wait for user to close browser with timeout
            print("Waiting for user interaction... (Press Ctrl+C to stop)")
            session_timeout = 3600  # 1 hour timeout for the session
            start_wait = time.time()
            try:
                while True:
                    time.sleep(2)
                    # Check if browser window is still open
                    try:
                        # Try to get window handles - if empty, browser is closed
                        handles = self.driver.window_handles
                        if not handles:
                            print("Browser window closed by user")
                            break
                    except Exception as e:
                        print(f"Browser check failed: {e}")
                        break

                    # Check for session timeout
                    if time.time() - start_wait > session_timeout:
                        print("Session timeout reached")
                        break
            except KeyboardInterrupt:
                print("\nSession interrupted by user")

        except Exception as e:
            print(f"Error starting session: {e}")

        finally:
            self.end_session()

    def end_session(self):
        """End session and save logs"""
        if self.driver:
            print("\nClosing browser and saving logs...")

            try:
                # Get final page state
                final_url = self.driver.current_url
                final_title = self.driver.title

                self.log_action("session_end", {
                    "final_url": final_url,
                    "final_title": final_title,
                    "total_actions": len(self.actions_log)
                })

                # Save actions log
                log_filename = f"chrome_session_{self.session_id}.json"
                try:
                    with open(log_filename, 'w', encoding='utf-8') as f:
                        json.dump({
                            'session_info': {
                                'session_id': self.session_id,
                                'start_time': datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None,
                                'duration': time.time() - self.start_time if self.start_time else 0,
                                'final_url': final_url,
                                'final_title': final_title
                            },
                            'actions': self.actions_log
                        }, f, ensure_ascii=False, indent=2)
                    print(f"Session logs saved to: {log_filename}")
                except UnicodeEncodeError as e:
                    print(f"Unicode error in logs: {e}. Saving without special characters.")
                    with open(log_filename, 'w', encoding='utf-8') as f:
                        json.dump({
                            'session_info': {
                                'session_id': self.session_id,
                                'start_time': datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None,
                                'duration': time.time() - self.start_time if self.start_time else 0,
                                'final_url': final_url.encode('ascii', 'ignore').decode('ascii'),
                                'final_title': final_title.encode('ascii', 'ignore').decode('ascii')
                            },
                            'actions': self.actions_log
                        }, f, ensure_ascii=True, indent=2)
                    print(f"Session logs saved to: {log_filename} (with ASCII encoding)")

                print(f"Session logs saved to: {log_filename}")
                print(f"Total actions logged: {len(self.actions_log)}")

            except Exception as e:
                print(f"Error saving logs: {e}")
            finally:
                try:
                    # Quit driver with timeout
                    self.driver.quit()
                    print("Browser closed successfully")
                except Exception as e:
                    print(f"Error closing browser: {e}")

        print("Session ended.")


def main():
    """Main function"""
    print("=== Chrome Logger for Lingualeo Investigation ===")
    print("This will open Chrome browser for manual interaction.")
    print("All actions will be logged for later automation.")

    logger = ChromeLogger()
    logger.start_session()


if __name__ == "__main__":
    main()
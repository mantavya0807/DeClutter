#!/usr/bin/env python3
"""
Marketplace Listing API - Facebook Marketplace & eBay Auto-Listing
Integrates with image recognition and price scraping for intelligent listings
"""

import os
from dotenv import load_dotenv
import time
import re
import json
import random
import statistics
import tempfile
import base64
import threading
import atexit
import subprocess
from datetime import datetime
from typing import Dict, List, Optional
from difflib import SequenceMatcher

from flask import Flask, request, jsonify
from flask_cors import CORS

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from webdriver_manager.chrome import ChromeDriverManager

# eBay SDK
try:
    import requests
    EBAY_AVAILABLE = True
    print("[OK] eBay API client available")
except ImportError:
    EBAY_AVAILABLE = False
    print("[WARNING] eBay API client not available")

# Gemini for description generation
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    print("[OK] Gemini AI available for description generation")
except ImportError:
    GEMINI_AVAILABLE = False
    print("[WARNING] Gemini AI not available")

app = Flask(__name__)
CORS(app)

class MarketplaceLister:
    def __init__(self):
        self.driver = None
        self.profile_path = os.path.abspath('chrome_profile_lister')
        self.facebook_logged_in = False
        self.ebay_token = None
        self.gemini_model = None
        self.gemini_client = None  # Ensure attribute always exists
        self.monitor = None  # Facebook message monitor instance
        self.setup_gemini()
        self.setup_ebay()
        atexit.register(self.close)
        print("[ROCKET] Marketplace Lister initialized")
    
    def __del__(self):
        self.close()

    def log_error(self, message):
        """Log error to file"""
        try:
            log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'error_log.txt')
            with open(log_path, 'a') as f:
                f.write(f"[{datetime.now()}] {message}\n")
        except:
            pass

    def kill_stray_processes(self):
        """Kill stray chromedriver processes to release locks"""
        print("🧹 Cleaning up stray webdrivers (not Chrome tabs)...")
        try:
            if os.name == 'nt':
                subprocess.run(["taskkill", "/f", "/im", "chromedriver.exe"], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")

    def setup_gemini(self):
        """Initialize Gemini AI for description generation"""
        if not GEMINI_AVAILABLE:
            self.gemini_model = None
            return

        load_dotenv()
        key = os.getenv('GEMINI_API_KEY')
        if key and key.strip() and key != 'your_api_key_here':
            try:
                genai.configure(api_key=key.strip())
                self.gemini_model = genai.GenerativeModel("gemini-2.0-flash")
                # Test model
                try:
                    _ = self.gemini_model.generate_content("Test")
                    print(f"[OK] Gemini AI configured successfully: {key[:8]}...")
                    return
                except Exception as e:
                    print(f"[WARNING] Gemini model error: {e}")
                    print("Listing available models:")
                    try:
                        models = genai.list_models()
                        print(models)
                    except Exception as e2:
                        print(f"[WARNING] Could not list models: {e2}")
                    return
            except Exception as e:
                print(f"[WARNING] Gemini key failed {key[:8]}...: {e}")
                self.gemini_model = None
                return

        print("[WARNING] No working Gemini API key found")
        self.gemini_model = None
    
    def setup_ebay(self):
        """Initialize eBay API credentials"""
        load_dotenv()
        self.ebay_config = {
            'app_id': os.getenv('EBAY_APP_ID'),
            'cert_id': os.getenv('EBAY_CERT_ID'),
            'dev_id': os.getenv('EBAY_DEV_ID'),
            'user_token': os.getenv('EBAY_USER_TOKEN'),
            'sandbox': os.getenv('EBAY_SANDBOX', 'true').lower() == 'true'
        }
        
        if self.ebay_config['app_id']:
            print(f"[OK] eBay API configured: {self.ebay_config['app_id'][:8]}...")
        else:
            print("[WARNING] eBay API not configured - add credentials to .env")
    
    def start_browser(self, headless=False):
        """Start Chrome browser with anti-detection settings"""
        try:
            print(f"[GLOBE] Starting Chrome browser for Facebook... (Headless: {headless})")
            if not os.path.exists(self.profile_path):
                os.makedirs(self.profile_path)
                print(f"[FOLDER] Created profile directory: {self.profile_path}")

            options = Options()
            # Anti-detection settings (same as scraper.py)
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

            # Performance settings
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-logging')
            options.add_argument('--log-level=3')
            options.add_argument('--disable-extensions')

            # Persistent profile for login cookies
            options.add_argument(f'--user-data-dir={self.profile_path}')

            if headless:
                options.add_argument('--headless=new')
            else:
                options.add_argument('--start-maximized')

            # Install and start Chrome
            print("[DEBUG] Installing Chrome Driver...")
            driver_path = ChromeDriverManager().install()
            print(f"[DEBUG] Chrome Driver installed at: {driver_path}")
            
            service = ChromeService(driver_path)
            self.driver = webdriver.Chrome(service=service, options=options)

            # Hide automation indicators
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            print("[OK] Chrome browser started successfully")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to start browser: {e}")
            import traceback
            traceback.print_exc()
            self.log_error(f"Browser start failed: {e}")
            
            print("🔄 Attempting to clean up and retry...")
            self.kill_stray_processes()
            time.sleep(2)
            
            try:
                # Retry
                print("[DEBUG] Retrying Chrome Driver installation...")
                service = ChromeService(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
                print("[OK] Chrome browser started successfully (after retry)")
                return True
            except Exception as e2:
                print(f"[ERROR] Retry failed: {e2}")
                self.log_error(f"Browser retry failed: {e2}")
                return False
    
    def check_facebook_login(self) -> bool:
        """Check if logged into Facebook"""
        try:
            print("🔍 Checking Facebook login status...")
            
            self.driver.get("https://www.facebook.com/marketplace/create/item")
            
            # Wait for URL change or page load instead of sleep
            try:
                WebDriverWait(self.driver, 5).until(
                    lambda d: "marketplace" in d.current_url.lower() or "login" in d.current_url.lower()
                )
            except:
                pass
            
            current_url = self.driver.current_url.lower()
            page_title = self.driver.title.lower()
            
            if ("marketplace" in current_url and 
                "login" not in current_url and 
                ("marketplace" in page_title or "create" in current_url)):
                
                print("[OK] Facebook login confirmed")
                self.facebook_logged_in = True
                return True
            
            print("[LOCK] Facebook login required")
            return False
            
        except Exception as e:
            print(f"[ERROR] Error checking Facebook login: {e}")
            return False
    
    def facebook_login_flow(self) -> bool:
        """Interactive Facebook login process"""
        try:
            print("\n[LOCK] FACEBOOK LOGIN REQUIRED")
            print("=" * 60)
            print("Facebook Marketplace requires authentication to create listings.")
            print("This is a ONE-TIME setup - your login will be saved.")
            print("=" * 60)
            
            # Navigate to Facebook login
            self.driver.get("https://www.facebook.com/login")
            time.sleep(3)
            
            print("\n👆 Please complete the following steps:")
            print("1. Log into your Facebook account in the browser window")
            print("2. Complete any security checks (2FA, etc.)")
            print("3. Wait for the page to fully load")
            print("4. Return here and press Enter")
            
            input("\n>>> Press Enter after you've successfully logged in...")
            
            # Verify login by accessing marketplace create page
            for attempt in range(3):
                print(f"🔄 Verifying login... (attempt {attempt + 1}/3)")
                
                self.driver.get("https://www.facebook.com/marketplace/create/item")
                time.sleep(4)
                
                if self.check_facebook_login():
                    print("🎉 Facebook login successful and verified!")
                    return True
                
                if attempt < 2:
                    print("[WARNING] Login not detected, please check the browser window")
                    time.sleep(3)
            
            print("[ERROR] Facebook login verification failed")
            return False
            
        except Exception as e:
            print(f"[ERROR] Facebook login process failed: {e}")
            return False
    
    def handle_facebook_confirmation_dialogs(self, exclude: List[str] = None) -> bool:
        """Handle various Facebook confirmation dialogs that might appear"""
        try:
            if exclude is None:
                exclude = []
            
            print("🔍 Checking for Facebook confirmation dialogs...")
            
            # Common Facebook confirmation dialogs and their buttons
            dialog_patterns = [
                {
                    'name': 'Leave Page',
                    'selectors': [
                        "//div[@aria-label='Leave Page']",
                        "//span[text()='Leave Page']/ancestor::div[@role='button']",
                        "//div[@role='button' and .//span[text()='Leave Page']]",
                        "//button[text()='Leave Page']",
                        "//button[.//span[text()='Leave Page']]"
                    ],
                    'warning': True
                },
                {
                    'name': 'Continue',
                    'selectors': [
                        "//div[@aria-label='Continue']",
                        "//span[text()='Continue']/ancestor::div[@role='button']",
                        "//button[text()='Continue']"
                    ]
                },
                {
                    'name': 'Confirm',
                    'selectors': [
                        "//div[@aria-label='Confirm']",
                        "//span[text()='Confirm']/ancestor::div[@role='button']",
                        "//button[text()='Confirm']"
                    ]
                },
                {
                    'name': 'OK',
                    'selectors': [
                        "//div[@aria-label='OK']",
                        "//span[text()='OK']/ancestor::div[@role='button']",
                        "//button[text()='OK']"
                    ]
                }
            ]
            
            for dialog in dialog_patterns:
                if dialog['name'] in exclude:
                    continue

                for selector in dialog['selectors']:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                print(f"[OK] Found '{dialog['name']}' dialog button")
                                
                                if dialog.get('warning'):
                                    print(f"⚠️ WARNING: Clicking '{dialog['name']}' might discard unsaved changes if the listing isn't finished.")
                                    # Wait a bit to ensure it's not a transient state
                                    time.sleep(2)
                                
                                try:
                                    element.click()
                                    print(f"[OK] Successfully clicked '{dialog['name']}' button")
                                    time.sleep(2)
                                    return True
                                except Exception:
                                    try:
                                        self.driver.execute_script("arguments[0].click();", element)
                                        print(f"[OK] Successfully clicked '{dialog['name']}' button with JavaScript")
                                        time.sleep(2)
                                        return True
                                    except Exception as e:
                                        print(f"[WARNING] Failed to click '{dialog['name']}' button: {e}")
                                        continue
                    except Exception:
                        continue
            
            print("📝 No confirmation dialogs found")
            return False
            
        except Exception as e:
            print(f"[ERROR] Error handling confirmation dialogs: {e}")
            return False

    def ensure_facebook_access(self) -> bool:
        """Ensure Facebook access (login if needed)"""
        if not self.driver:
            if not self.start_browser(headless=False):
                return False
        
        if self.check_facebook_login():
            return True
        
        return self.facebook_login_flow()
    


    def generate_description(self, product_name: str, pricing_data: Dict, condition: str = "used") -> str:
        """Generate concise, human-like product description using Gemini AI"""
        try:
            if not self.gemini_model:
                # Fallback description
                return f"{product_name} in {condition} condition. Great value item!"

            # Extract pricing insights
            comps = pricing_data.get('comps', [])
            if not comps:
                market_info = "Limited market data available."
            else:
                avg_price = statistics.mean([comp['price'] for comp in comps])
                conditions = [comp['condition'] for comp in comps]
                platforms = [comp['platform'] for comp in comps]
                market_info = f"Average price: ${avg_price:.2f}. Common conditions: {', '.join(set(conditions))}. Available on: {', '.join(set(platforms))}."

            prompt = f"""
You are helping someone sell an item online. Write a short, friendly, and natural-sounding marketplace description for:
Product: {product_name}
Condition: {condition}
{market_info}

Guidelines:
- Maximum 2 short paragraphs, no more than 5 sentences total.
- Avoid generic AI phrases and keep it conversational, as if you are the seller.
- Mention the condition honestly and highlight practical features or benefits.
- End with a simple call to action (e.g., 'Message me if interested!').
- Do not use excessive capitalization, markdown, or spammy language.
"""

            response = self.gemini_model.generate_content(prompt)

            if hasattr(response, 'text') and response.text:
                description = response.text.strip()
                # Remove markdown, excessive whitespace, and AI-sounding phrases
                description = re.sub(r'\*\*', '', description)
                description = re.sub(r'\n\n+', '\n', description)
                # Truncate to 5 sentences max
                sentences = re.split(r'(?<=[.!?]) +', description)
                description = ' '.join(sentences[:5]).strip()
                # Remove common AI phrases
                description = re.sub(r'(As an AI language model,|I am an AI|I can|I will|This item is perfect for you if|Don\'t miss out on)', '', description, flags=re.I)
                
                # Remove any bracketed placeholders [Insert ...] or <Insert ...>
                description = re.sub(r'\[.*?\]', '', description)
                description = re.sub(r'\{.*?\}', '', description)
                description = re.sub(r'<.*?>', '', description)
                
                return description.strip()

        except Exception as e:
            print(f"[WARNING] Description generation failed: {e}")
            # Fallback description
            return f"{product_name} in {condition} condition. Well-maintained and ready for a new owner. Message me if interested!"
    
    def calculate_optimal_price(self, pricing_data: Dict, condition: str = "used") -> float:
        """Calculate optimal listing price based on market data"""
        try:
            comps = pricing_data.get('comps', [])
            if not comps:
                return 50.0  # Default fallback
            
            # Filter by similar condition
            condition_comps = [comp for comp in comps if comp['condition'] == condition]
            if not condition_comps:
                condition_comps = comps  # Use all if no exact condition matches
            
            prices = [comp['price'] for comp in condition_comps]
            
            # Calculate percentiles for intelligent pricing
            if len(prices) >= 4:
                prices_sorted = sorted(prices)
                p25 = prices_sorted[len(prices_sorted) // 4]
                p75 = prices_sorted[3 * len(prices_sorted) // 4]
                median = statistics.median(prices)
                
                # Price slightly below median for quick sale, but above P25
                optimal = median * 0.95
                optimal = max(optimal, p25 * 1.1)  # Don't go too low
                optimal = min(optimal, p75 * 0.9)  # Don't go too high
                
            else:
                # Use average with slight discount
                optimal = statistics.mean(prices) * 0.9
            
            return round(optimal, 2)
            
        except Exception as e:
            print(f"[WARNING] Price calculation failed: {e}")
            return 50.0
    
    def _handle_nested_category_selection(self, listing_data: Dict, depth: int = 0, max_depth: int = 5):
        """Recursively handle nested category selection using Gemini"""
        try:
            if depth >= max_depth:
                print(f"[WARNING] Maximum category depth ({max_depth}) reached")
                return
            
            print(f"🔄 Category Selection Level {depth + 1}...")
            time.sleep(2)  # Wait for animations
            
            # 1. Find all potential options in the currently visible dropdown/listbox
            # We look for elements that look like menu items
            potential_options = []
            
            # Strategy A: Look for elements with role="option" or in a listbox
            try:
                options = self.driver.find_elements(By.XPATH, "//div[@role='option']//span | //li[@role='option']//span | //div[@role='listbox']//span")
                for opt in options:
                    if opt.is_displayed() and len(opt.text.strip()) > 2:
                        potential_options.append((opt, opt.text.strip()))
            except:
                pass
            
            # Strategy B: If A failed, look for any span in a dialog or popover that isn't a button label
            if not potential_options:
                try:
                    # Broader search for containers including common FB classes or just generic divs that might be the menu
                    container_xpath = "//div[@role='dialog'] | //div[contains(@class, 'popover')] | //div[contains(@class, 'menu')] | //div[contains(@class, 'scrollable')] | //div[contains(@style, 'position: absolute')]"
                    spans = self.driver.find_elements(By.XPATH, f"{container_xpath}//span")
                    
                    excluded_texts = ['Back', 'Next', 'Cancel', 'Done', 'Search', 'Category', 'Condition', 'Title', 'Price', 'Location', 'Description', 'Photos', 'Videos']
                    
                    for span in spans:
                        text = span.text.strip()
                        if (span.is_displayed() and 
                            len(text) > 2 and 
                            len(text) < 50 and 
                            text not in excluded_texts and
                            not any(ex in text for ex in excluded_texts)):
                            
                            # Check if clickable
                            try:
                                parent = span.find_element(By.XPATH, "./..")
                                if parent.tag_name == "div" or parent.tag_name == "li":
                                    potential_options.append((span, text))
                            except:
                                pass
                except:
                    pass

            # Strategy C: Look for known top-level categories to find the container (Fallback)
            if not potential_options:
                known_categories = [
                    "Antiques and collectibles", "Arts and crafts", "Auto parts", "Baby supplies",
                    "Books, movies and music", "Cell phones", "Clothing", "Electronics",
                    "Furniture", "Garage sale", "Health and beauty", "Home and kitchen",
                    "Jewelry", "Musical instruments", "Pet supplies", "Sports", "Tools", "Toys", "Video games"
                ]
                
                print("Strategy C: Searching for known category markers...")
                for cat in known_categories:
                    try:
                        # Find elements containing this text
                        markers = self.driver.find_elements(By.XPATH, f"//span[contains(text(), '{cat}')]")
                        for marker in markers:
                            if marker.is_displayed():
                                print(f"Found marker: {cat}")
                                # Traverse up to find the list container
                                current = marker
                                found_list = False
                                # Go up max 12 levels to find a container with multiple children
                                for _ in range(12):
                                    try:
                                        current = current.find_element(By.XPATH, "./..")
                                        # Check for siblings (divs or lis)
                                        children = current.find_elements(By.XPATH, "./div | ./li | ./span")
                                        # If we find a container with > 3 children, it's likely the list (or a parent of the list items)
                                        if len(children) > 3:
                                            # Verify if children contain text
                                            text_children = [c for c in children if c.text.strip()]
                                            if len(text_children) > 3:
                                                found_list = True
                                                break
                                    except:
                                        break
                                
                                if found_list:
                                    print("Found potential list container via marker")
                                    # Search for all spans and divs in this container
                                    container_elements = current.find_elements(By.XPATH, ".//span | .//div")
                                    for el in container_elements:
                                        text = el.text.strip()
                                        # Clean up text (remove newlines)
                                        text = text.replace('\n', ' ').strip()
                                        
                                        # Filter out likely non-option text
                                        if (len(text) > 2 and 
                                            text not in [p[1] for p in potential_options] and
                                            text not in ['Delivery available', 'Shipping available'] and
                                            "See all" not in text and
                                            len(text) < 60): 
                                            potential_options.append((el, text))
                                
                        if potential_options:
                            break # Found the menu
                    except Exception as e:
                        print(f"Strategy C error for {cat}: {e}")
                        pass

            # Remove duplicates preserving order
            unique_options = []
            seen_texts = set()
            for span, text in potential_options:
                if text not in seen_texts:
                    unique_options.append((span, text))
                    seen_texts.add(text)
            
            potential_options = unique_options
            
            if not potential_options:
                print(f"[OK] No category options found at level {depth + 1}. Assuming selection complete.")
                return

            print(f"Found {len(potential_options)} options: {[t for _, t in potential_options[:10]]}...")

            # 2. Ask Gemini which one to pick
            if self.gemini_model:
                option_texts = [t for _, t in potential_options]
                context = f"Product: '{listing_data.get('title', '')}'"
                if listing_data.get('description'):
                    context += f" Description: '{listing_data.get('description', '')[:100]}...'"
                
                prompt = f"""
                {context}
                We are selecting a category on Facebook Marketplace.
                Current available options:
                {json.dumps(option_texts)}
                
                Select the ONE best option that fits the product.
                Return ONLY the exact text of the option.
                If none fit well, return "SKIP".
                """
                
                try:
                    response = self.gemini_model.generate_content(prompt)
                    if response and response.text:
                        choice = response.text.strip().replace('"', '')
                        print(f"Gemini chose: {choice}")
                        
                        if choice == "SKIP":
                            print("Gemini decided to skip.")
                            return

                        # Find and click the chosen option
                        clicked = False
                        for span, text in potential_options:
                            if text.lower() == choice.lower() or choice.lower() in text.lower():
                                print(f"Clicking option: {text}")
                                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", span)
                                time.sleep(0.5)
                                try:
                                    span.click()
                                except:
                                    self.driver.execute_script("arguments[0].click();", span)
                                clicked = True
                                break
                        
                        if clicked:
                            time.sleep(2)
                            # Recursively check for next level
                            self._handle_nested_category_selection(listing_data, depth + 1, max_depth)
                            return
                        else:
                            print(f"Could not find element for choice: {choice}")

                except Exception as e:
                    print(f"Gemini error: {e}")
            
            # Fallback if Gemini fails or not available: Pick first relevant looking option
            print("Fallback: Picking first option")
            if potential_options:
                span, text = potential_options[0]
                try:
                    span.click()
                    time.sleep(2)
                    self._handle_nested_category_selection(listing_data, depth + 1, max_depth)
                except:
                    pass

        except Exception as e:
            print(f"[WARNING] Error in nested category selection: {e}")

    def log_page_source(self, step_name: str):
        """Log current page HTML for debugging selectors"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debug_fb_{step_name}_{timestamp}.html"
            filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print(f"[DEBUG] Saved HTML snapshot to: {filepath}")
        except Exception as e:
            print(f"[WARNING] Failed to save HTML snapshot: {e}")

    def create_facebook_listing(self, listing_data: Dict) -> Dict:
        """Create Facebook Marketplace listing using Selenium with exact selectors"""
        try:
            # Ensure browser is running
            if not self.driver:
                print("🔄 Browser not running, starting now...")
                self.start_browser(headless=False)  # Force visible browser for debugging
            
            if not self.check_facebook_login():
                print("⚠️ Not logged in to Facebook. Attempting login flow...")
                if not self.facebook_login_flow():
                    return {"success": False, "error": "Facebook login failed"}
            
            print("✅ Logged in to Facebook. Navigating to create listing page...")
            self.driver.get("https://www.facebook.com/marketplace/create/item")
            
            # Log HTML before starting interaction
            self.log_page_source("1_create_page_loaded")

            print("📝 Creating Facebook Marketplace listing...")
            wait = WebDriverWait(self.driver, 15)
            
            # --- TITLE ---
            try:
                selector = "//label[.//span[text()='Title']]//input"
                value = listing_data['title']
                print(f"   [SELECTOR] Waiting for Title input: {selector}")
                print(f"   [DATA] Filling Title: '{value}'")
                
                title_input = wait.until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                title_input.clear()
                title_input.send_keys(value)
                print("[OK] Title filled")
            except TimeoutException:
                self.log_page_source("error_title_not_found")
                return {'error': 'Could not find title field', 'platform': 'facebook'}

            # --- PRICE ---
            try:
                selector = "//label[.//span[text()='Price']]//input"
                
                # Format price: Round to nearest integer for Facebook to avoid decimal issues
                price_val = listing_data['price']
                print(f"   [DEBUG] Calculated Price Value: {price_val}")
                
                try:
                    # Round to nearest integer
                    value = str(int(round(float(price_val))))
                except:
                    value = str(price_val)
                    
                print(f"   [SELECTOR] Waiting for Price input: {selector}")
                print(f"   [DATA] Filling Price: '{value}' (Raw: {price_val})")
                
                price_input = wait.until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                
                # Robust clearing
                price_input.click()
                time.sleep(0.5)
                price_input.send_keys(Keys.CONTROL + "a")
                time.sleep(0.2)
                price_input.send_keys(Keys.DELETE)
                time.sleep(0.2)
                
                # Type value
                price_input.send_keys(value)
                print("[OK] Price filled")
            except Exception as e:
                self.log_page_source("error_price_failed")
                print(f"[WARNING] Could not find or fill price field: {e}")
            
            # --- CATEGORY ---
            try:
                selector = "//label[.//span[text()='Category']]"
                print(f"   [SELECTOR] Waiting for Category dropdown: {selector}")
                
                # 1. Click the Category dropdown
                category_label = wait.until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", category_label)
                time.sleep(0.5) # Reduced sleep
                category_label.click()
                time.sleep(1) # Reduced sleep

                # 2. Use Recursive Gemini Selection
                self._handle_nested_category_selection(listing_data)
                print(f"[OK] Category selection completed")

            except Exception as e:
                self.log_page_source("error_category_failed")
                print(f"[WARNING] Could not select category: {e}")

            # --- CONDITION ---
            try:
                selector = "//label[.//span[text()='Condition']]"
                print(f"   [SELECTOR] Waiting for Condition dropdown: {selector}")
                
                # 1. Click the Condition dropdown
                condition_label = wait.until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", condition_label)
                time.sleep(0.5) # Reduced sleep
                
                try:
                    condition_label.click()
                except Exception as e:
                    if "click intercepted" in str(e):
                        print("[WARNING] Click intercepted. Attempting to close blocking elements (ESC)...")
                        webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                        time.sleep(1)
                        condition_label.click()
                    else:
                        raise e

                time.sleep(1) # Reduced sleep

                # 2. Select Condition Option
                condition_map = {
                    'new': 'New',
                    'like_new': 'Used – like new',
                    'good': 'Used – good', 
                    'fair': 'Used – fair',
                    'poor': 'Used – fair',
                    'used': 'Used – good'
                }
                fb_condition = condition_map.get(listing_data.get('condition', 'used'), 'Used – good')
                option_selector = f"//span[text()='{fb_condition}']"
                print(f"   [SELECTOR] Waiting for Condition option: {option_selector}")
                print(f"   [DATA] Selecting Condition: '{fb_condition}'")

                condition_option = wait.until(
                    EC.element_to_be_clickable((By.XPATH, option_selector))
                )
                condition_option.click()
                print(f"[OK] Condition '{fb_condition}' selected")
                time.sleep(0.5) # Reduced sleep

            except Exception as e:
                self.log_page_source("error_condition_failed")
                print(f"[WARNING] Could not set condition: {e}")
            
            # --- DESCRIPTION ---
            try:
                selector = "//label[.//span[text()='Description']]//textarea"
                value = listing_data['description'][:50] + "..." # Truncate for log
                print(f"   [SELECTOR] Waiting for Description input: {selector}")
                print(f"   [DATA] Filling Description: '{value}'")
                
                description_area = wait.until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                description_area.clear()
                description_area.send_keys(listing_data['description'])
                print("[OK] Description filled")
            except TimeoutException:
                self.log_page_source("error_description_failed")
                return {'error': 'Could not find description field', 'platform': 'facebook'}
            
            # --- PHOTOS ---
            try:
                print("📸 Uploading Photos...")
                # Check if we have a specific image path passed
                image_path = listing_data.get('image_path')
                
                if not image_path:
                    print("[WARNING] No image path provided for upload.")
                
                if image_path:
                    # Ensure absolute path
                    image_path = os.path.abspath(image_path)
                    
                    if os.path.exists(image_path):
                        selector = "//input[@type='file']"
                        print(f"   [SELECTOR] Finding file inputs: {selector}")
                        print(f"   [DATA] Uploading image: {image_path}")
                        
                        # Try multiple file input selectors
                        file_inputs = self.driver.find_elements(By.XPATH, selector)
                        uploaded = False
                        
                        if not file_inputs:
                             print("[WARNING] No file inputs found!")
                        
                        for i, file_input in enumerate(file_inputs):
                            try:
                                print(f"   [DEBUG] Trying file input #{i+1}")
                                # Unhide input if hidden (common in React apps)
                                self.driver.execute_script("arguments[0].style.display = 'block';", file_input)
                                file_input.send_keys(image_path)
                                uploaded = True
                                print(f"[OK] Uploaded image to input #{i+1}: {image_path}")
                                break # Stop after first success
                            except Exception as e:
                                print(f"[DEBUG] Failed to upload to input #{i+1}: {e}")
                        
                        if not uploaded:
                             print("[WARNING] Could not upload photo to any file input")
                        else:
                             time.sleep(5) # Wait for upload to process
                    else:
                        print(f"[WARNING] Image file does not exist at path: {image_path}")
                else:
                    print("[WARNING] No image found to upload.")
            except Exception as e:
                self.log_page_source("error_photos_failed")
                print(f"[WARNING] Could not upload photo: {e}")

            # --- PUBLISH ---
            try:
                print("🚀 Publishing...")
                publish_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Publish']"))
                )
                
                # Check if button is disabled first
                is_disabled = publish_button.get_attribute('aria-disabled') == 'true'
                if is_disabled:
                    self.log_page_source("publish_disabled")
                    return {
                        'success': True,
                        'platform': 'facebook',
                        'status': 'form_completed_needs_images',
                        'message': 'Facebook listing form completed but publish button is disabled. Check if all required fields are filled.'
                    }
                
                # Scroll to publish button and click it
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", publish_button)
                time.sleep(1)
                
                publish_button.click()
                print("[OK] Clicked Publish button!")
                
                # Wait for publish to process
                print("⏳ Waiting for publish to complete...")
                time.sleep(5)
                
                # Check for dialogs, but ignore 'Leave Page' initially to avoid cancelling the publish
                # if it's just a transient redirect confirmation
                if self.handle_facebook_confirmation_dialogs(exclude=['Leave Page']):
                    print("[OK] Handled confirmation dialog (excluding Leave Page)")
                
                # Wait and check for dialogs multiple times
                print("⏳ Waiting for confirmation dialogs...")
                for i in range(5):
                    time.sleep(2)
                    # Now we can handle all dialogs if they persist
                    if self.handle_facebook_confirmation_dialogs():
                        print("[OK] Handled confirmation dialog")
                        break
                    print(f"   ... checking for dialogs (attempt {i+1}/5)")
                    
                # Final check: If we are still on the create page, something might be wrong
                try:
                    if "create" in self.driver.current_url.lower():
                        print("[WARNING] Still on create page after publishing. Listing might not be live.")
                except:
                    pass
                    
                return {
                    'success': True,
                    'platform': 'facebook',
                    'status': 'published',
                    'message': 'Facebook listing published successfully!'
                }

            except TimeoutException:
                print("[WARNING] Could not find publish button")
                return {
                    'success': True,
                    'platform': 'facebook',
                    'status': 'form_filled',
                    'message': 'Facebook listing form completed successfully. Publish button may need manual click.'
                }
            
        except Exception as e:
            print(f"[ERROR] Facebook listing creation failed: {e}")
            self.log_page_source("fatal_error")
            return {'error': f'Facebook listing failed: {str(e)}', 'platform': 'facebook'}
    
    def create_ebay_listing(self, listing_data: Dict) -> Dict:
        """Create eBay listing using eBay API"""
        try:
            if not self.ebay_config['app_id']:
                return {'error': 'eBay API not configured', 'platform': 'ebay'}
            
            print("📝 Creating eBay listing via API...")
            
            # eBay API endpoint
            if self.ebay_config['sandbox']:
                base_url = "https://api.sandbox.ebay.com"
            else:
                base_url = "https://api.ebay.com"
            
            # Prepare listing data for eBay
            ebay_listing = {
                "Item": {
                    "Title": listing_data['title'][:80],  # eBay title limit
                    "Description": listing_data['description'],
                    "PrimaryCategory": {"CategoryID": "175672"},  # Electronics > Audio > Headphones (example)
                    "StartPrice": {
                        "currencyID": "USD",
                        "value": str(listing_data['price'])
                    },
                    "CategoryMappingAllowed": True,
                    "Country": "US",
                    "Currency": "USD",
                    "DispatchTimeMax": 3,
                    "ListingDuration": "Days_7",
                    "ListingType": "FixedPriceItem",
                    "PaymentMethods": ["PayPal"],
                    "PictureDetails": {
                        "GalleryType": "Gallery"
                    },
                    "Quantity": 1,
                    "ReturnPolicy": {
                        "ReturnsAcceptedOption": "ReturnsAccepted",
                        "RefundOption": "MoneyBack",
                        "ReturnsWithinOption": "Days_30"
                    },
                    "ShippingDetails": {
                        "ShippingType": "Flat",
                        "ShippingServiceOptions": [{
                            "ShippingServicePriority": 1,
                            "ShippingService": "USPSMedia",
                            "ShippingServiceCost": {
                                "currencyID": "USD", 
                                "value": "5.99"
                            }
                        }]
                    },
                    "Site": "US"
                }
            }
            
            # Map condition to eBay condition ID
            condition_map = {
                'new': '1000',
                'like_new': '1500', 
                'good': '3000',
                'fair': '4000',
                'poor': '5000',
                'used': '3000'
            }
            
            condition_id = condition_map.get(listing_data.get('condition', 'used'), '3000')
            ebay_listing["Item"]["ConditionID"] = condition_id
            
            # Headers for eBay API
            headers = {
                'X-EBAY-API-SITEID': '0',
                'X-EBAY-API-COMPATIBILITY-LEVEL': '967',
                'X-EBAY-API-CALL-NAME': 'AddFixedPriceItem',
                'X-EBAY-API-APP-NAME': self.ebay_config['app_id'],
                'X-EBAY-API-DEV-NAME': self.ebay_config['dev_id'],
                'X-EBAY-API-CERT-NAME': self.ebay_config['cert_id'],
                'Content-Type': 'text/xml'
            }
            
            # XML request body
            xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
<AddFixedPriceItemRequest xmlns="urn:ebay:apis:eBLBaseComponents">
    <RequesterCredentials>
        <eBayAuthToken>{self.ebay_config['user_token']}</eBayAuthToken>
    </RequesterCredentials>
    <Item>
        <Title>{listing_data['title'][:80]}</Title>
        <Description><![CDATA[{listing_data['description']}]]></Description>
        <PrimaryCategory>
            <CategoryID>175672</CategoryID>
        </PrimaryCategory>
        <StartPrice currencyID="USD">{listing_data['price']}</StartPrice>
        <CategoryMappingAllowed>true</CategoryMappingAllowed>
        <ConditionID>{condition_id}</ConditionID>
        <Country>US</Country>
        <Currency>USD</Currency>
        <DispatchTimeMax>3</DispatchTimeMax>
        <ListingDuration>Days_7</ListingDuration>
        <ListingType>FixedPriceItem</ListingType>
        <Quantity>1</Quantity>
        <ReturnPolicy>
            <ReturnsAcceptedOption>ReturnsAccepted</ReturnsAcceptedOption>
            <RefundOption>MoneyBack</RefundOption>
            <ReturnsWithinOption>Days_30</ReturnsWithinOption>
        </ReturnPolicy>
        <ShippingDetails>
            <ShippingType>Flat</ShippingType>
            <ShippingServiceOptions>
                <ShippingServicePriority>1</ShippingServicePriority>
                <ShippingService>USPSMedia</ShippingService>
                <ShippingServiceCost currencyID="USD">5.99</ShippingServiceCost>
            </ShippingServiceOptions>
        </ShippingDetails>
        <Site>US</Site>
    </Item>
</AddFixedPriceItemRequest>"""
            
            # Make API request
            response = requests.post(
                f"{base_url}/ws/api.dll",
                headers=headers,
                data=xml_request,
                timeout=30
            )
            
            if response.status_code == 200:
                # Parse XML response (simplified)
                if 'Success' in response.text:
                    # Extract item ID from response if needed
                    import re
                    item_match = re.search(r'<ItemID>(\d+)</ItemID>', response.text)
                    item_id = item_match.group(1) if item_match else None
                    
                    return {
                        'success': True,
                        'platform': 'ebay',
                        'item_id': item_id,
                        'status': 'listed',
                        'message': f'eBay listing created successfully. Item ID: {item_id}'
                    }
                else:
                    return {
                        'error': 'eBay API returned error',
                        'platform': 'ebay',
                        'details': response.text
                    }
            else:
                return {
                    'error': f'eBay API request failed: {response.status_code}',
                    'platform': 'ebay'
                }
            
        except Exception as e:
            print(f"[ERROR] eBay listing creation failed: {e}")
            return {'error': f'eBay listing failed: {str(e)}', 'platform': 'ebay'}
    
    def create_listings(self, product_data: Dict, pricing_data: Dict, platforms: List[str], images: List[str] = None) -> Dict:
        """Create listings on specified platforms"""
        results = {}
        
        # Generate optimal listing data
        condition = product_data.get('condition', 'used')
        optimal_price = self.calculate_optimal_price(pricing_data, condition)
        description = self.generate_description(
            product_data.get('name', 'Unknown Product'),
            pricing_data,
            condition
        )
        
        # Handle base64 images
        image_path = None
        if images and len(images) > 0:
            try:
                import base64
                import tempfile
                
                # Create temp file
                fd, path = tempfile.mkstemp(suffix='.jpg')
                with os.fdopen(fd, 'wb') as f:
                    # Remove header if present (data:image/jpeg;base64,...)
                    img_data = images[0]
                    if ',' in img_data:
                        img_data = img_data.split(',')[1]
                    f.write(base64.b64decode(img_data))
                image_path = path
                print(f"[OK] Saved base64 image to {image_path}")
            except Exception as e:
                print(f"[ERROR] Failed to save base64 image: {e}")

        listing_data = {
            'title': product_data.get('name', 'Unknown Product')[:75],  # Limit for platforms
            'price': product_data.get('price', optimal_price), # Use provided price if available
            'condition': condition,
            'description': description,
            'category': product_data.get('category', 'Electronics'),
            'image_path': image_path
        }
        
        print(f"📋 Creating listings for: {listing_data['title']} at ${listing_data['price']}")
        
        # Create Facebook listing
        if 'facebook' in platforms:
            fb_result = self.create_facebook_listing(listing_data)
            results['facebook'] = fb_result
        
        # Create eBay listing
        if 'ebay' in platforms:
            ebay_result = self.create_ebay_listing(listing_data)
            results['ebay'] = ebay_result
        
        return {
            'listings': results,
            'listing_data': listing_data,
            'platforms_attempted': platforms
        }
    
    def start_facebook_message_monitoring(self):
        """Start Facebook message monitoring in background thread"""
        try:
            from facebook_monitor import FacebookMessageMonitor
            
            print("[ROCKET] Starting Facebook message monitoring...")
            
            self.monitor = FacebookMessageMonitor()
            self.monitor.lister = self  # Use this lister's browser session
            
            # Start monitoring in background thread
            monitor_thread = threading.Thread(target=self.monitor.start_monitoring)
            monitor_thread.daemon = True  # Dies when main program exits
            monitor_thread.start()
            
            print("[OK] Facebook message monitor started in background")
            return self.monitor
            
        except Exception as e:
            print(f"[ERROR] Failed to start message monitor: {e}")
            return None

    def send_facebook_message(self, buyer_name: str, message_text: str) -> bool:
        """Send a Facebook message using the monitor instance"""
        if not self.monitor:
            # Try to start monitor if not running, or at least initialize it
            from facebook_monitor import FacebookMessageMonitor
            self.monitor = FacebookMessageMonitor()
            self.monitor.lister = self
            self.monitor.scraper.driver = self.driver # Share driver
            
        if not self.driver:
            self.start_browser(headless=False)
            
        return self.monitor.send_message(buyer_name, message_text)
    
    def close(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
                print("[FIRE] Browser closed")
            except:
                pass

# Initialize global lister
lister = MarketplaceLister()

# === API ROUTES ===

@app.route('/health', methods=['GET'])
def health_check():
    """API health check"""
    return jsonify({
        'status': 'OK',
        'service': 'marketplace_listing_api',
        'timestamp': datetime.now().isoformat(),
        'browser_ready': lister.driver is not None,
        'facebook_logged_in': lister.facebook_logged_in,
        'gemini_available': lister.gemini_model is not None,
        'ebay_configured': bool(lister.ebay_config['app_id']),
        'version': '1.0.0'
    })

@app.route('/api/facebook/login', methods=['POST'])
def facebook_login():
    """Trigger Facebook login process"""
    try:
        success = lister.ensure_facebook_access()
        
        if success:
            return jsonify({
                'ok': True,
                'message': 'Facebook login successful',
                'logged_in': True
            })
        else:
            return jsonify({
                'ok': False,
                'error_code': 'LOGIN_FAILED',
                'message': 'Facebook login process failed'
            }), 400
    
    except Exception as e:
        return jsonify({
            'ok': False,
            'error_code': 'LOGIN_ERROR',
            'message': f'Login error: {str(e)}'
        }), 500

@app.route('/api/listings/create', methods=['POST'])
def create_listings():
    """
    Create marketplace listings
    
    Body:
    {
        "product": {
            "name": "Anker Soundcore Liberty 4 NC",
            "condition": "used",
            "category": "Electronics",
            "price": 35.00 // Optional override
        },
        "pricing_data": {pricing data from price scraper},
        "platforms": ["facebook", "ebay"],
        "images": ["base64_image_data"] // optional
    }
    """
    try:
        if not request.is_json:
            return jsonify({
                'ok': False,
                'error_code': 'INVALID_REQUEST',
                'message': 'JSON request body required'
            }), 400
        
        data = request.get_json()
        
        # Validate required fields
        if 'product' not in data:
            return jsonify({
                'ok': False,
                'error_code': 'MISSING_PRODUCT_DATA',
                'message': 'Product data is required'
            }), 400
        
        if 'pricing_data' not in data:
            return jsonify({
                'ok': False,
                'error_code': 'MISSING_PRICING_DATA',
                'message': 'Pricing data is required'
            }), 400
        
        # Extract parameters
        product_data = data['product']
        pricing_data = data['pricing_data']
        platforms = data.get('platforms', ['facebook', 'ebay'])
        images = data.get('images', [])
        
        # Validate platforms
        valid_platforms = ['facebook', 'ebay']
        platforms = [p for p in platforms if p in valid_platforms]
        
        if not platforms:
            return jsonify({
                'ok': False,
                'error_code': 'NO_VALID_PLATFORMS',
                'message': f'Valid platforms are: {valid_platforms}'
            }), 400
        
        # Create listings
        result = lister.create_listings(product_data, pricing_data, platforms, images)
        
        # Check if any listings succeeded
        successes = [r for r in result['listings'].values() if r.get('success')]
        errors = [r for r in result['listings'].values() if 'error' in r]
        
        return jsonify({
            'ok': True,
            'data': {
                'listings': result['listings'],
                'listing_data': result['listing_data'],
                'summary': {
                    'platforms_attempted': len(platforms),
                    'successful_listings': len(successes),
                    'failed_listings': len(errors)
                }
            },
            'diagnostics': {
                'platforms_attempted': result['platforms_attempted'],
                'gemini_used': lister.gemini_model is not None,
                'provider': 'marketplace_listing_api_v1'
            }
        })
    
    except Exception as e:
        print(f"[ERROR] API error: {e}")
        return jsonify({
            'ok': False,
            'error_code': 'INTERNAL_ERROR',
            'message': 'Listing creation failed'
        }), 500

@app.route('/api/listings/facebook', methods=['POST'])
def create_facebook_listing_only():
    """Create Facebook listing only"""
    try:
        data = request.get_json()
        
        if not data or 'product' not in data or 'pricing_data' not in data:
            return jsonify({
                'ok': False,
                'error_code': 'INVALID_DATA',
                'message': 'Product and pricing data required'
            }), 400
        
        result = lister.create_listings(
            data['product'], 
            data['pricing_data'], 
            ['facebook'],
            data.get('images', [])
        )
        
        fb_result = result['listings'].get('facebook', {})
        
        return jsonify({
            'ok': fb_result.get('success', False),
            'data': fb_result,
            'listing_data': result['listing_data']
        })
    
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500

@app.route('/api/listings/ebay', methods=['POST'])
def create_ebay_listing_only():
    """Create eBay listing only"""
    try:
        data = request.get_json()
        
        if not data or 'product' not in data or 'pricing_data' not in data:
            return jsonify({
                'ok': False,
                'error_code': 'INVALID_DATA',
                'message': 'Product and pricing data required'
            }), 400
        
        result = lister.create_listings(
            data['product'], 
            data['pricing_data'], 
            ['ebay'],
            data.get('images', [])
        )
        
        ebay_result = result['listings'].get('ebay', {})
        
        return jsonify({
            'ok': ebay_result.get('success', False),
            'data': ebay_result,
            'listing_data': result['listing_data']
        })
    
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500

@app.route('/api/facebook/start-monitoring', methods=['POST'])
def start_facebook_monitoring():
    """Start Facebook message monitoring"""
    try:
        # Use your existing lister instance
        monitor = lister.start_facebook_message_monitoring()
        
        if monitor:
            return jsonify({
                'ok': True,
                'message': 'Facebook message monitoring started',
                'status': 'monitoring'
            })
        else:
            return jsonify({
                'ok': False,
                'error': 'Failed to start monitoring'
            }), 500
            
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500

@app.route('/api/facebook/monitor-status', methods=['GET'])
def get_monitor_status():
    """Get current monitoring status"""
    # Simple status check
    return jsonify({
        'ok': True,
        'status': 'running',  # You can make this more sophisticated
        'last_check': datetime.now().isoformat()
    })

# === MAIN ===

if __name__ == '__main__':
    print("[CART] Marketplace Listing API v1.0")
    print("=" * 50)
    print("[GLOBE] Server: http://localhost:3003")
    print("📝 Create Listings: POST /api/listings/create")
    print("📘 Facebook Only: POST /api/listings/facebook")  
    print("📙 eBay Only: POST /api/listings/ebay")
    print("[LOCK] FB Login: POST /api/facebook/login")
    print("[PHONE] Start Monitor: POST /api/facebook/start-monitoring")
    print("[CHART] Monitor Status: GET /api/facebook/monitor-status")
    print("❤️  Health: GET /health")
    print()
    print("[SPARKLES] Features:")
    print("  - Facebook Marketplace automation (Selenium)")
    print("  - eBay API integration for listings")
    print("  - AI-generated descriptions (Gemini)")
    print("  - Intelligent pricing based on market data")
    print("  - Anti-detection browser settings")
    print("  - Cookie-based login persistence")
    print("  🆕 - Facebook message monitoring")
    print()
    print("⚙️  Setup:")
    print("  1. Add eBay API credentials to .env")
    print("  2. Run Facebook login on first use")
    print("  3. Integrate with image recognition & price scraper")
    print("  4. Start Facebook message monitoring")
    print("[ROCKET] Ready for hackathon!")
    
    try:
        # Disable reloader to prevent crashes during Selenium execution if files change
        app.run(debug=True, use_reloader=False, host='0.0.0.0', port=3003)
    except Exception as e:
        print(f"[ERROR] Server error: {e}")
    finally:
        lister.close()

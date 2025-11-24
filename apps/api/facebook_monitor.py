#!/usr/bin/env python3
"""
Facebook Message Monitor for Decluttered.ai
Polls FB messages every 30 seconds and forwards to AgentMail
"""

import os
import time
import json
import threading
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re
import google.generativeai as genai

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import your existing scraper
from scraper import MarketplaceScraper

try:
    from agentmail import AgentMail
    AGENTMAIL_AVAILABLE = True
    print("[OK] AgentMail library available")
except ImportError:
    AGENTMAIL_AVAILABLE = False
    print("[WARNING] AgentMail not installed - using console output")

# Import Supabase client
try:
    from supabase_client import get_supabase
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("[WARNING] Supabase client not available")

class FacebookMessageMonitor:
    def __init__(self):
        self.scraper = MarketplaceScraper()
        self.last_checked = {}  # Track last message timestamps per conversation
        self.agentmail = None
        self.monitor_inbox = None
        self.supabase = get_supabase() if SUPABASE_AVAILABLE else None
        
        # Configure Gemini
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                
                # Try to find a working model
                available_models = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-pro']
                self.model = None
                
                for model_name in available_models:
                    try:
                        print(f"   Testing model: {model_name}...")
                        # Test the model with a simple prompt
                        test_model = genai.GenerativeModel(model_name)
                        # Actually call it to verify access
                        test_model.generate_content("test")
                        self.model = test_model
                        print(f"[OK] Gemini AI configured using model: {model_name}")
                        break
                    except Exception as e:
                        # print(f"   [DEBUG] Model {model_name} failed: {e}")
                        continue
                
                if not self.model:
                    print("[WARNING] Could not configure any Gemini model")
            else:
                self.model = None
                print("[WARNING] GEMINI_API_KEY not found")
        except Exception as e:
            print(f"[WARNING] Gemini setup failed: {e}")
            self.model = None

        if AGENTMAIL_AVAILABLE:
            self.setup_agentmail()
        
        self.running = False
        self.processed_messages = set() # Track replied message IDs
        self.last_auto_reply = {} # Track last reply time per buyer {name: timestamp}
        
    def setup_agentmail(self):
        """Setup AgentMail inbox for FB messages"""
        try:
            # Check if API key is available
            api_key = os.getenv('AGENTMAIL_API_KEY')
            if not api_key:
                print("[WARNING] AGENTMAIL_API_KEY not found in environment variables")
                return
                
            if api_key.startswith('am_42a33a4de15884a10d84785f54ffa4fe75eb04f6ec86555ae9cdb88e04d84f82'):
                print("[WARNING] Please replace the placeholder AGENTMAIL_API_KEY in .env with your actual API key")
                print("[BULB] Get your API key from: https://agentmail.com/dashboard")
                return
            
            print(f"🔑 Using AgentMail API key: {api_key[:8]}...")
            self.agentmail = AgentMail(api_key=api_key)
            self.monitor_inbox = self.agentmail.inboxes.create(
                username="fb-messages",
                domain="decluttered.ai"
            )
            print(f"[OK] AgentMail inbox created: {self.monitor_inbox.username}@decluttered.ai")
        except Exception as e:
            print(f"[WARNING] AgentMail setup failed: {e}")
            print("[BULB] Make sure your AGENTMAIL_API_KEY is correct in .env file")
            self.agentmail = None

    def start_monitoring(self):
        """Start the Facebook message monitoring loop"""
        print("[ROCKET] Starting Facebook Message Monitor...")
        
        # Ensure Facebook access using existing scraper logic
        if not self.scraper.ensure_facebook_access():
            print("[ERROR] Facebook access failed")
            return False
            
        self.running = True
        
        # Run monitoring loop
        while self.running:
            try:
                new_messages = self.check_facebook_inbox()
                
                if new_messages:
                    print(f"📨 Found {len(new_messages)} new messages")
                    for msg in new_messages:
                        self.process_message(msg)
                else:
                    print("🔍 No new messages found")
                    
                # Wait 30 seconds before next check
                for i in range(30):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                print(f"[ERROR] Monitor error: {e}")
                
                # Check for critical browser errors
                error_str = str(e).lower()
                if "invalid session id" in error_str or "no such window" in error_str or "disconnected" in error_str:
                    print("🚨 Browser session lost! Restarting browser...")
                    try:
                        if hasattr(self.scraper, 'driver'):
                            self.scraper.driver.quit()
                    except:
                        pass
                    
                    # Re-initialize scraper
                    try:
                        self.scraper = MarketplaceScraper()
                        if self.scraper.ensure_facebook_access():
                            print("[OK] Browser restarted successfully")
                            continue
                    except Exception as restart_error:
                        print(f"[ERROR] Restart failed: {restart_error}")
                
                print("⏳ Waiting 60 seconds before retry...")
                time.sleep(60)
                
        print("🛑 Facebook Message Monitor stopped")
        return True

    def get_actual_message_for_buyer(self, buyer_name, item_preview):
        """Click into conversation to get the actual latest message"""
        try:
            print(f"💬 Getting actual message from {buyer_name}...")
            
            # Look for clickable conversation row with this buyer
            conversation_xpath = f"//span[contains(text(), '{buyer_name}') and contains(text(), 'Anker')]"
            
            try:
                conv_element = self.scraper.driver.find_element(By.XPATH, conversation_xpath)
                # Find the clickable parent row
                clickable_row = conv_element.find_element(By.XPATH, "./ancestor::div[@role='row']")
                clickable_row.click()
                time.sleep(3)
                
                # Now extract the actual latest message
                message_selectors = [
                    'div[dir="auto"]:last-child',  # Last message
                    '[data-testid="message"] div[dir="auto"]',
                    'div[dir="auto"]'
                ]
                
                for selector in message_selectors:
                    try:
                        message_elements = self.scraper.driver.find_elements(By.CSS_SELECTOR, selector)
                        # Get messages that aren't UI text
                        for elem in reversed(message_elements):  # Start from most recent
                            text = elem.text.strip()
                            if (text and len(text) > 3 and 
                                text not in ['Marketplace', buyer_name, 'Message sent', 'You sent'] and
                                not text.startswith('Seen by') and
                                not text.endswith('...') and
                                text != item_preview[:50]):
                                
                                print(f"   [OK] Found real message: {text}")
                                return text
                    except:
                        continue
                
                return "Could not extract message content"
                
            except Exception as e:
                print(f"   [WARNING] Could not click into conversation: {e}")
                return f"New message from {buyer_name}"
                
        except Exception as e:
            print(f"   [ERROR] Message extraction failed: {e}")
            return f"Activity from {buyer_name}"

    def check_facebook_inbox(self):
        """Check inbox by clicking through conversations (Split-pane view)"""
        new_messages = []
        
        try:
            print("📬 Checking Facebook Marketplace inbox...")
            # Force the Selling tab via URL
            if "targetTab=SELLER" not in self.scraper.driver.current_url:
                self.scraper.driver.get("https://www.facebook.com/marketplace/inbox/?targetTab=SELLER")
                time.sleep(5)
            
            WebDriverWait(self.scraper.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[role="main"]'))
            )

            print("🔍 Scanning conversation list...")
            
            # Find all conversation buttons in the main area
            # Based on user HTML: div[role="button"] inside main
            try:
                main_content = self.scraper.driver.find_element(By.CSS_SELECTOR, '[role="main"]')
                # Get all buttons that look like conversation rows
                buttons = main_content.find_elements(By.CSS_SELECTOR, 'div[role="button"]')
            except Exception as e:
                print(f"   [WARNING] Could not find conversation list: {e}")
                return []

            # Filter valid conversation buttons (avoid header buttons etc)
            conversation_indices = []
            ignored_button_texts = ['Jobs', 'Browse all', 'Notifications', 'Inbox', 'Selling', 'Buying', 'Create new listing']
            
            for i, btn in enumerate(buttons):
                try:
                    text = btn.text.strip()
                    # Valid conversations usually have a newline or "·" or timestamp
                    # User HTML shows: "Name · Item" inside the button
                    if text and ("\n" in text or "·" in text):
                        # Extra check for ignored texts
                        is_ignored = False
                        for ignored in ignored_button_texts:
                            if text.startswith(ignored) or text == ignored:
                                is_ignored = True
                                break
                        if not is_ignored:
                            conversation_indices.append(i)
                except:
                    continue
            
            print(f"   Found {len(conversation_indices)} potential conversations")
            
            # Check the first 5 conversations (most recent)
            for i in conversation_indices[:5]:
                try:
                    # Re-find elements to avoid StaleElementReference
                    main_content = self.scraper.driver.find_element(By.CSS_SELECTOR, '[role="main"]')
                    buttons = main_content.find_elements(By.CSS_SELECTOR, 'div[role="button"]')
                    
                    if i >= len(buttons):
                        break
                        
                    btn = buttons[i]
                    
                    # Scroll into view
                    self.scraper.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(1)
                    
                    # Click to open chat on the right pane - FORCE CLICK with JS
                    try:
                        # Try regular click first
                        # btn.click() 
                        # actually, regular click failed. Let's use JS click directly or ActionChains
                        self.scraper.driver.execute_script("arguments[0].click();", btn)
                    except Exception as e:
                        print(f"   [WARNING] JS Click failed, trying ActionChains: {e}")
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(self.scraper.driver)
                        actions.move_to_element(btn).click().perform()
                    
                    time.sleep(5) # Wait for chat to load
                    
                    # Extract data from the open chat view
                    message_data = self.extract_conversation_data()
                    
                    if message_data:
                        # Check if it's new
                        if self.is_new_message(message_data):
                            new_messages.append(message_data)
                            print(f"📨 NEW: {message_data['buyer_name']} -> '{message_data['latest_message'][:30]}...'")
                            
                            # AUTO-RESPONSE LOGIC
                            # Only for Aakansha Mahajan and if we haven't replied yet
                            buyer_lower = message_data['buyer_name'].lower()
                            if "aakansha" in buyer_lower:
                                print(f"🤖 Auto-response candidate: {message_data['buyer_name']}")
                                
                                # Check if last message was from us (avoid loops)
                                if message_data['last_sender'] == 'seller':
                                    print("   [SKIP] Last message was from us")
                                    continue
                                
                                # Check cooldown (prevent double replies)
                                last_reply_time = self.last_auto_reply.get(message_data['buyer_name'])
                                if last_reply_time and (time.time() - last_reply_time < 120): # 2 minutes cooldown
                                    print(f"   [SKIP] Cooldown active for {message_data['buyer_name']}")
                                    continue

                                # Check if we already replied to this specific message content
                                msg_hash = hash(message_data['latest_message'])
                                if msg_hash not in self.processed_messages:
                                    # Generate response
                                    response_text = self.generate_response(
                                        message_data['buyer_name'], 
                                        message_data['item_title'], 
                                        message_data['latest_message']
                                    )
                                    
                                    # Send response using current context
                                    if self.send_message(message_data['buyer_name'], response_text, use_current_context=True):
                                        print(f"✅ Auto-responded to {message_data['buyer_name']}")
                                        self.processed_messages.add(msg_hash)
                                        # Add our response to processed so we don't reply to ourselves
                                        self.processed_messages.add(hash(response_text))
                                        self.last_auto_reply[message_data['buyer_name']] = time.time()
                                else:
                                    print("   [SKIP] Already replied to this message")
                        else:
                            # print(f"   [OK] Already seen: {message_data['buyer_name']}")
                            pass
                            
                except Exception as e:
                    print(f"   [ERROR] Failed to process conversation {i}: {e}")
                    continue
            
            return new_messages

        except Exception as e:
            print(f"[ERROR] Inbox check failed: {e}")
            # Re-raise critical errors to trigger browser restart
            error_str = str(e).lower()
            if "invalid session id" in error_str or "no such window" in error_str or "disconnected" in error_str:
                raise e
            return []

    def is_new_conversation(self, conv_id, preview_text):
        """Check if this conversation preview is new using Supabase"""
        # 1. Check local cache first (fastest)
        if conv_id in self.last_checked:
            if self.last_checked[conv_id] == preview_text:
                return False
        
        # 2. Check Supabase if available
        if self.supabase:
            try:
                # Check if we have this conversation
                response = self.supabase.table('conversations').select('id, last_message_at').eq('platform_thread_id', conv_id).execute()
                
                if response.data:
                    # We have the conversation, check if message is new
                    # For now, we rely on the preview text changing as a proxy for new message
                    # In a perfect world we'd compare timestamps, but FB timestamps are fuzzy ("5m")
                    pass
            except Exception as e:
                print(f"[WARNING] Supabase check failed: {e}")

        # Update our record
        self.last_checked[conv_id] = preview_text
        return True

    def extract_conversation_data(self):
        """Extract message data from current Facebook conversation - with debugging"""
        try:
            wait = WebDriverWait(self.scraper.driver, 5)
            
            print(f"🔍 Current URL: {self.scraper.driver.current_url}")
            
            # Save page source for debugging
            if hasattr(self, '_debug_mode'):
                with open(f'fb_debug_{int(time.time())}.html', 'w', encoding='utf-8') as f:
                    f.write(self.scraper.driver.page_source)
            
            # Get buyer name - try multiple strategies
            buyer_name = "Unknown"
            
            print("[USER] Looking for buyer name...")

            # Strategy 0: Look for "Name · Item" pattern in headers (Most reliable based on user HTML)
            try:
                # Look for h2 spans that might contain the " · " separator
                header_spans = self.scraper.driver.find_elements(By.CSS_SELECTOR, 'h2 span')
                for span in header_spans:
                    text = span.text.strip()
                    if " · " in text and len(text.split(" · ")) == 2:
                        parts = text.split(" · ", 1)
                        if len(parts) == 2:
                            possible_name = parts[0].strip()
                            possible_item = parts[1].strip()
                            # Validate it's not just UI text
                            if len(possible_name) > 2 and len(possible_item) > 5:
                                buyer_name = possible_name
                                item_title = possible_item
                                print(f"   [OK] Found combined header: '{buyer_name}' buying '{item_title}'")
                                break
            except Exception as e:
                print(f"   [WARNING] Combined header strategy failed: {e}")
            
            # Strategy 1: Look for profile names in various locations (if not found above)
            if buyer_name == "Unknown":
                buyer_selectors = [
                    # The main header in the chat view usually has the buyer's name
                    'div[role="main"] h2 span', 
                    'div[role="main"] h1 span',
                    # Fallback to other potential locations
                    'a[role="link"] span[dir="auto"]',
                    # 'div[role="complementary"] span' # Removed as it picks up sidebar items like "Jobs"
                ]
                
                for selector in buyer_selectors:
                    try:
                        elements = self.scraper.driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            text = elem.text.strip()
                            # Skip common UI text
                            if (text and len(text) > 2 and 
                                text not in ['Marketplace', 'Create new listing', 'Messages', 'Home', 'Profile', 'Browse all', 'Inbox', 'Selling', 'Buying', 'Notifications', 'Jobs', 'Your listings'] and
                                not text.startswith('$') and 
                                'listing' not in text.lower()):
                                
                                # Check if this name appears in the "started this chat" message
                                # This is a strong signal it's the buyer
                                page_source = self.scraper.driver.page_source
                                if f"{text} started this chat" in page_source or f"View {text}'s profile" in page_source:
                                    buyer_name = text
                                    print(f"   [OK] Confirmed buyer name from chat context: {buyer_name}")
                                    break
                                
                                # If we can't confirm, store as candidate but keep looking
                                if buyer_name == "Unknown":
                                    buyer_name = text
                                    print(f"   [CANDIDATE] Possible buyer name: {buyer_name}")
                                    
                        if buyer_name != "Unknown" and "Confirmed" in str(buyer_name): # If confirmed, stop
                            break
                    except Exception as e:
                        continue
            
            # Get item title/reference - try finding the actual listing (if not found above)
            if item_title == "Unknown Item":
                print("[PACKAGE] Looking for item title...")
                
                # In the new layout, the item title is often at the top of the chat or in the sidebar
                item_selectors = [
                    # Look for the item card in the chat header
                    'div[role="main"] a[href*="/marketplace/item/"]',
                    'div[role="complementary"] a[href*="/marketplace/item/"]',
                    # Fallback
                    'a[href*="/marketplace/item/"]'
                ]
                
                for selector in item_selectors:
                    try:
                        elements = self.scraper.driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            # Get text and clean it
                            raw_text = elem.text.strip()
                            if not raw_text:
                                 raw_text = elem.get_attribute('aria-label') or ""
                            
                            # Clean up the text (remove newlines, prices, UI text)
                            lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                            clean_text = ""
                            
                            for line in lines:
                                if (len(line) > 5 and 
                                    line not in ['Marketplace', 'See details', 'View listing', 'View buyer', 'More Options'] and
                                    not line.startswith('$')):
                                    clean_text = line
                                    break
                            
                            if clean_text:
                                item_title = clean_text
                                print(f"   [OK] Using item title: {item_title}")
                                break
                        if item_title != "Unknown Item":
                            break
                    except:
                        continue

            # Get latest message - focus on actual message bubbles
            latest_message = "No message found"
            last_sender = "unknown"
            valid_messages = []
            
            print("💬 Looking for messages...")
            
            # We need to find the message bubbles in the chat area
            # They usually have a specific structure
            try:
                # Find all message groups
                # This selector targets the message text bubbles specifically
                # We also want to check the parent row for sender info
                message_rows = self.scraper.driver.find_elements(By.CSS_SELECTOR, 'div[role="row"]')
                
                for row in message_rows:
                    try:
                        # Check if it's a message row
                        bubbles = row.find_elements(By.CSS_SELECTOR, 'div[dir="auto"]')
                        for bubble in bubbles:
                            text = bubble.text.strip()
                            if (text and 
                                text not in [buyer_name, 'You sent', 'Enter', 'Marketplace', item_title] and
                                not text.endswith('started this chat.') and
                                not text.startswith('Seen by') and
                                len(text) > 0):
                                valid_messages.append(text)
                                # Try to determine sender from row attributes
                                # Heuristic: Outgoing messages often don't have the buyer's profile pic or name next to them
                                # Or they might have specific aria-labels
                                # For now, we'll assume if it's the last one, we check it
                                pass
                    except:
                        continue
                
                if valid_messages:
                    latest_message = valid_messages[-1]
                    print(f"   [OK] Using latest message: {latest_message[:50]}...")
                    
                    # Determine sender of the LAST message
                    try:
                        # Heuristic 1: Check if message matches our known bot responses
                        if "Hi, thanks for your interest" in latest_message or "Yes, it is available" in latest_message:
                            last_sender = "seller"
                        
                        # Heuristic 2: Check for "You sent" in the row
                        # We look for a row that contains the text of the latest message
                        # This might be slow but it's safer
                        # Escape quotes in message for XPath
                        safe_msg = latest_message[:20].replace('"', "'")
                        xpath = f"//div[@role='row'][.//div[contains(text(), \"{safe_msg}\")]]"
                        rows = self.scraper.driver.find_elements(By.XPATH, xpath)
                        if rows:
                            last_row = rows[-1] # Get the last one (most recent)
                            aria_label = last_row.get_attribute("aria-label") or ""
                            row_text = last_row.text
                            if "You sent" in aria_label or "You sent" in row_text:
                                last_sender = "seller"
                                print(f"   [INFO] Detected last message as outgoing (seller)")
                    except Exception as e:
                        # print(f"   [DEBUG] Sender detection failed: {e}")
                        pass
                        
                else:
                    # Fallback: check for "sent you a message" system text
                    page_text = self.scraper.driver.find_element(By.TAG_NAME, "body").text
                    if "sent you a message about your listing" in page_text:
                         latest_message = "New inquiry (content hidden)"
                         last_sender = "buyer"

            except Exception as e:
                print(f"   [WARNING] Message extraction error: {e}")

            # Create conversation ID
            conversation_id = f"{buyer_name}_{hash(item_title) % 10000}"
            
            # Post-extraction validation
            if buyer_name in ['Jobs', 'Browse all', 'Marketplace', 'Notifications', 'Inbox', 'Selling', 'Buying', 'Create new listing', 'Unknown']:
                print(f"   [SKIP] Invalid buyer name: {buyer_name}")
                return None
                
            if "You're now friends with" in latest_message:
                print(f"   [SKIP] System notification detected")
                return None
                
            if item_title in ['Unknown Item', 'Jobs', 'Browse all']:
                # If we have a real message but unknown item, we might still want it, 
                # but if it's just "Unknown Item" and "No message found", skip it.
                if latest_message == "No message found":
                    return None

            message_data = {
                'conversation_id': conversation_id,
                'buyer_name': buyer_name,
                'item_title': item_title,
                'latest_message': latest_message,
                'last_sender': last_sender, # We need to populate this better
                'platform': 'facebook_marketplace',
                'timestamp': datetime.now().isoformat(),
                'url': self.scraper.driver.current_url,
                'all_messages_found': len(valid_messages),
                'debug_info': f"Found {len(valid_messages)} messages total"
            }
            
            print(f"📝 Final extraction: {buyer_name} -> {item_title[:30]}... -> {latest_message[:50]}...")
            return message_data
            
        except Exception as e:
            print(f"[ERROR] Data extraction failed: {e}")
            return None

    def is_new_message(self, message_data):
        """Check if this is a new message we haven't processed"""
        if not message_data:
            return False
            
        conv_id = message_data['conversation_id']
        current_message = message_data['latest_message']
        
        # Check if we've seen this exact message before
        if conv_id in self.last_checked:
            if self.last_checked[conv_id] == current_message:
                return False  # Same message as last time
        
        # Update our record
        self.last_checked[conv_id] = current_message
        return True

    def process_message(self, message_data):
        """Enhanced message processing with Supabase persistence"""
        priority = "🔴 HIGH PRIORITY" if message_data.get('is_unread', False) else "📨 Normal"
        
        print(f"\n{priority} - PROCESSING MESSAGE:")
        print(f"   [USER] Buyer: {message_data['buyer_name']}")
        print(f"   [PACKAGE] Item: {message_data['item_title']}")
        print(f"   💬 Message: '{message_data['latest_message']}'")
        
        # 1. Persist to Supabase
        if self.supabase:
            try:
                # Upsert Conversation
                conv_data = {
                    'platform_thread_id': message_data['conversation_id'],
                    'buyer_name': message_data['buyer_name'],
                    'item_title': message_data['item_title'],
                    'last_message': message_data['latest_message'],  # Added last_message
                    'last_message_at': datetime.now().isoformat(),
                    'is_unread': message_data.get('is_unread', False),
                    'status': 'active'
                }
                
                # Add user_id if available in .env
                user_id = os.getenv('USER_ID')
                if user_id:
                    conv_data['user_id'] = user_id
                
                # First try to get existing conversation to get UUID
                existing = self.supabase.table('conversations').select('id').eq('platform_thread_id', message_data['conversation_id']).execute()
                
                if existing.data:
                    conv_id = existing.data[0]['id']
                    try:
                        self.supabase.table('conversations').update(conv_data).eq('id', conv_id).execute()
                    except Exception as e:
                        # Handle missing column gracefully
                        if "Could not find the 'last_message' column" in str(e):
                            print("   [WARNING] 'last_message' column missing in DB, skipping it...")
                            if 'last_message' in conv_data:
                                del conv_data['last_message']
                            self.supabase.table('conversations').update(conv_data).eq('id', conv_id).execute()
                        else:
                            raise e
                else:
                    # Insert new
                    try:
                        res = self.supabase.table('conversations').insert(conv_data).execute()
                    except Exception as e:
                        # Handle missing column gracefully
                        if "Could not find the 'last_message' column" in str(e):
                            print("   [WARNING] 'last_message' column missing in DB, skipping it...")
                            if 'last_message' in conv_data:
                                del conv_data['last_message']
                            res = self.supabase.table('conversations').insert(conv_data).execute()
                        else:
                            raise e
                    
                    if res.data:
                        conv_id = res.data[0]['id']
                    else:
                        # Fallback if no data returned (shouldn't happen on success)
                        print("   [ERROR] No ID returned from insert")
                        return
                
                # Insert Message
                msg_data = {
                    'conversation_id': conv_id,
                    'sender': 'buyer', # We assume incoming messages are from buyer for now
                    'content': message_data['latest_message'],
                    'platform_timestamp': datetime.now().isoformat() # Approximate
                }
                if user_id:
                    msg_data['user_id'] = user_id
                    
                self.supabase.table('messages').insert(msg_data).execute()
                print(f"   [DB] Saved to Supabase (Conv ID: {conv_id})")
                
            except Exception as e:
                print(f"   [ERROR] Failed to save to Supabase: {e}")

        # 2. Forward to AgentMail (if configured)
        if self.agentmail and self.monitor_inbox:
            self.forward_to_agentmail_enhanced(message_data)
        else:
            self.log_to_console_enhanced(message_data)
            
        # 3. Save to file backup
        self.save_to_file(message_data)

    def forward_to_agentmail_enhanced(self, message_data):
        """Enhanced AgentMail forwarding with priority and context"""
        try:
            priority_prefix = "🔴 URGENT" if message_data.get('is_unread', False) else "📨"
            subject = f"{priority_prefix} FB: {message_data['buyer_name']} - {message_data['item_title'][:40]}"
            
            email_body = f"""🚨 FACEBOOK MARKETPLACE MESSAGE {'(UNREAD!)' if message_data.get('is_unread', False) else ''}

[USER] BUYER: {message_data['buyer_name']}
[PACKAGE] ITEM: {message_data['item_title']}
💬 MESSAGE: "{message_data['latest_message']}"
[CLOCK] TIME: {message_data.get('fb_timestamp', 'unknown')} ago
📍 STATUS: {'🔴 UNREAD' if message_data.get('is_unread', False) else '[OK] Read'}

[TARGET] QUICK ACTIONS:
- Respond immediately if unread
- Check for price negotiation keywords
- Assess buyer interest level

[CHART] CONTEXT:
Platform: Facebook Marketplace
Detected: {message_data['timestamp']}
Conversation ID: {message_data['conversation_id']}

--- Raw Data ---
{json.dumps(message_data, indent=2)}
"""
            
            # Send with priority routing
            recipient = "urgent@decluttered.ai" if message_data.get('is_unread', False) else "negotiations@decluttered.ai"
            
            self.agentmail.inboxes.messages.send(
                inbox_id=self.monitor_inbox.inbox_id,
                to=[recipient],
                subject=subject,
                text=email_body
            )
            
            status = "[OK] URGENT forwarded" if message_data.get('is_unread', False) else "[OK] Forwarded"
            print(f"   {status} to AgentMail")
            
        except Exception as e:
            print(f"[ERROR] AgentMail forward failed: {e}")

    def log_to_console_enhanced(self, message_data):
        """Enhanced console logging with priority and context"""
        is_unread = message_data.get('is_unread', False)
        priority = "🔴 URGENT" if is_unread else "📨 NORMAL"
        
        print("\n" + "="*60)
        print(f"{priority} FACEBOOK MARKETPLACE MESSAGE")
        print("="*60)
        print(f"[USER] Buyer: {message_data['buyer_name']}")
        print(f"[PACKAGE] Item: {message_data['item_title']}")
        print(f"💬 Message: \"{message_data['latest_message']}\"")
        print(f"[CLOCK] FB Time: {message_data.get('fb_timestamp', 'unknown')}")
        print(f"🕐 Detected: {message_data['timestamp']}")
        print(f"📍 Status: {'🔴 UNREAD' if is_unread else '[OK] Read'}")
        print(f"🔗 URL: {message_data['url']}")
        if is_unread:
            print("[WARNING]  ACTION REQUIRED: Respond to unread message!")
        print("="*60)



    def save_to_file(self, message_data):
        """Save message to file for debugging"""
        try:
            filename = f"fb_messages_{datetime.now().strftime('%Y%m%d')}.jsonl"
            with open(filename, 'a', encoding='utf-8') as f:
                f.write(json.dumps(message_data) + '\n')
        except Exception as e:
            print(f"[WARNING] File save failed: {e}")

    def generate_response(self, buyer_name, item_title, last_message):
        """Generate a response using Gemini"""
        if not self.model:
            return "Hi, thanks for your interest! Is this still available?"

        try:
            prompt = f"""
            You are a helpful seller on Facebook Marketplace.
            Item: {item_title}
            Buyer: {buyer_name}
            Buyer's last message: "{last_message}"
            
            Write a short, polite, and helpful response. 
            If they ask if it's available, say yes.
            If they ask for price, confirm the price (if known) or ask for their offer.
            Keep it under 20 words. Do not include quotes.
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"[ERROR] Gemini generation failed: {e}")
            return "Yes, it is available!"

    def send_message(self, buyer_name: str, message_text: str, use_current_context=False) -> bool:
        """Send a message to a specific buyer"""
        try:
            print(f"📤 Sending message to {buyer_name}: '{message_text}'")
            
            # If not using current context, navigate (legacy behavior)
            if not use_current_context:
                # 1. Navigate to inbox if not there
                if "marketplace/inbox" not in self.scraper.driver.current_url:
                    self.scraper.driver.get("https://www.facebook.com/marketplace/inbox/")
                    time.sleep(3)
                
                # 2. Find conversation logic (omitted for brevity as we usually use current context now)
                pass

            # 3. Find input box and send message
            try:
                # Common Messenger input selectors
                selectors = [
                    "div[role='textbox'][aria-label='Message']",
                    "div[role='textbox'][aria-label='Type a message']",
                    "div[role='textbox']"
                ]
                
                input_box = None
                for selector in selectors:
                    try:
                        box = self.scraper.driver.find_element(By.CSS_SELECTOR, selector)
                        if box.is_displayed():
                            input_box = box
                            break
                    except:
                        continue
                
                if not input_box:
                    print("[ERROR] Could not find message input box")
                    return False
                
                # Type message
                input_box.click()
                input_box.send_keys(message_text)
                time.sleep(0.5)
                
                # Press Enter to send (usually works for FB Messenger)
                input_box.send_keys(u'\ue007') # Keys.ENTER
                
                # Alternatively look for send button
                try:
                    send_btn = self.scraper.driver.find_element(By.CSS_SELECTOR, "div[aria-label='Press Enter to send']")
                    send_btn.click()
                except:
                    pass
                    
                print(f"[OK] Message sent to {buyer_name}")
                return True
                
            except Exception as e:
                print(f"[ERROR] Error typing/sending message: {e}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Send message failed: {e}")
            return False

    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.running = False

def main():
    """Main function for testing"""
    monitor = FacebookMessageMonitor()
    
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\n🛑 Stopping monitor...")
        monitor.stop_monitoring()
        print("[OK] Monitor stopped")

if __name__ == "__main__":
    main()
import sys
import os
from unittest.mock import MagicMock
from datetime import datetime
import time

# 1. Mock the scraper so we don't open a Chrome window just to test the DB
# We need to do this BEFORE importing FacebookMessageMonitor
sys.modules['scraper'] = MagicMock()

# Now we can import the monitor
from facebook_monitor import FacebookMessageMonitor

def run_simulation():
    print("🤖 Initializing Monitor (Simulation Mode)...")
    
    # The monitor will try to instantiate MarketplaceScraper, which is now a mock
    monitor = FacebookMessageMonitor()
    
    # Ensure supabase is connected
    if not monitor.supabase:
        print("❌ Supabase not connected! Check .env")
        return

    print("✅ Supabase connected.")

    # 2. Create a fake message payload
    # This mimics exactly what the scraper would produce
    timestamp = int(time.time())
    fake_msg = {
        'conversation_id': f'SIM_TEST_{timestamp}',
        'buyer_name': f'Simulation User {timestamp}',
        'item_title': 'Vintage Typewriter (Test Item)',
        'latest_message': f'Is this still available? I can pick it up today. (Test ID: {timestamp})',
        'platform': 'facebook_marketplace',
        'timestamp': datetime.now().isoformat(),
        'is_unread': True,
        'url': 'http://facebook.com/marketplace/test_url',
        'fb_timestamp': 'Just now'
    }

    print(f"\n📨 Injecting fake message from: {fake_msg['buyer_name']}")
    print(f"   Content: {fake_msg['latest_message']}")
    
    # 3. Process the message (this triggers the Supabase save)
    monitor.process_message(fake_msg)
    
    print("\n✨ Simulation complete!")
    print("👉 Go to your Supabase Dashboard -> Table Editor")
    print("   1. Check 'conversations' table for 'Simulation User'")
    print("   2. Check 'messages' table for the message content")

if __name__ == "__main__":
    run_simulation()

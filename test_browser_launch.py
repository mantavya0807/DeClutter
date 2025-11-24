
import sys
import os
import time

# Add apps/api to path
sys.path.append(os.path.join(os.getcwd(), 'apps', 'api'))

try:
    from listing import MarketplaceLister
    print("✅ Imported MarketplaceLister")
except ImportError as e:
    print(f"❌ Failed to import MarketplaceLister: {e}")
    sys.exit(1)

def test_launch():
    print("🚀 Testing browser launch...")
    lister = MarketplaceLister()
    
    print("Attempting to start browser (headless=False)...")
    success = lister.start_browser(headless=False)
    
    if success:
        print("✅ Browser launched successfully!")
        print("Waiting 5 seconds...")
        time.sleep(5)
        lister.close()
        print("✅ Browser closed.")
    else:
        print("❌ Browser failed to launch.")

if __name__ == "__main__":
    test_launch()

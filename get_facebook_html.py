import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

def capture_facebook_html():
    profile_path = os.path.abspath('chrome_profile_lister')
    
    print(f"[INFO] Using profile: {profile_path}")
    
    options = Options()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument(f'--user-data-dir={profile_path}')
    options.add_argument('--start-maximized')
    
    # Initialize driver
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print("[INFO] Navigating to Facebook Marketplace Create Page...")
        driver.get("https://www.facebook.com/marketplace/create/item")
        
        print("\n" + "="*60)
        print("ACTION REQUIRED:")
        print("1. If you see a login screen, please log in.")
        print("2. If you see a 'See more on Facebook' popup, close it or log in.")
        print("3. Ensure you are on the 'Item for sale' creation page.")
        print("4. Wait for the form (Title, Price, etc.) to be visible.")
        print("="*60 + "\n")
        
        input(">>> Press ENTER once the Create Listing form is visible on your screen...")

        # Save the HTML
        output_file = "facebook_marketplace.html"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
            
        print(f"[SUCCESS] HTML saved to {output_file}")
        print("You can now close the browser.")
        
    except Exception as e:
        print(f"[ERROR] Failed to capture HTML: {e}")
    finally:
        # Keep browser open for a moment so user can see
        time.sleep(2)
        driver.quit()

if __name__ == "__main__":
    capture_facebook_html()

import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

def fix_login():
    print("🔧 Facebook Login Fixer")
    print("=======================")
    print("This script will help fix the 'Too Many Redirects' error.")
    
    profile_path = os.path.abspath('chrome_profile_scraper')
    print(f"📂 Using profile: {profile_path}")
    
    options = Options()
    options.add_argument(f'--user-data-dir={profile_path}')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    print("\n🚀 Starting Chrome...")
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print("\n🧹 Step 1: Clearing Facebook Cookies...")
        driver.get("https://www.facebook.com")
        time.sleep(2)
        driver.delete_all_cookies()
        print("✅ Cookies cleared.")
        
        print("\n🔐 Step 2: Please Log In")
        print("   I will navigate to the login page now.")
        driver.get("https://www.facebook.com/login")
        
        print("\n👉 ACTION REQUIRED:")
        print("   1. Look at the Chrome window.")
        print("   2. Log in to Facebook manually.")
        print("   3. If asked to 'Save Browser', say YES.")
        print("   4. Wait until you see your News Feed.")
        
        input("\n⌨️  Press ENTER here once you are fully logged in...")
        
        print("\n🔍 Verifying access...")
        driver.get("https://www.facebook.com/marketplace/inbox")
        time.sleep(3)
        
        if "login" not in driver.current_url:
            print("✅ SUCCESS! You can now run the monitor.")
        else:
            print("❌ Still seeing login page. Please try running this script again.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        print("\n👋 Closing browser...")
        driver.quit()

if __name__ == "__main__":
    fix_login()

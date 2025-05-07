from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def test_chrome_setup():
    print("Starting Chrome/ChromeDriver test...")
    
    # Set up Chrome options for headless operation
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    try:
        # Initialize the driver
        print("Initializing Chrome driver...")
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to a test page
        print("Navigating to python.org...")
        driver.get("https://www.python.org")
        
        # Wait for and find an element
        wait = WebDriverWait(driver, 10)
        element = wait.until(
            EC.presence_of_element_located((By.ID, "about"))
        )
        
        # Get the page title
        title = driver.title
        print(f"Successfully loaded page. Title: {title}")
        
        # Take a screenshot
        driver.save_screenshot("python_org.png")
        print("Screenshot saved as python_org.png")
        
        print("Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Test failed with error: {str(e)}")
        return False
        
    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    test_chrome_setup() 
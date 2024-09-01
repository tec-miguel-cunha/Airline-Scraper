import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

def setup_chrome_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # No GUI will be opened
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-http2")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("window-size=1920x1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36")
    chrome_service = Service("/usr/local/bin/chromedriver")
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
    driver.implicitly_wait(30)

    return driver

if __name__ == "__main__":
    driver = setup_chrome_driver()
    driver.get("https://www.aireuropa.com/pt/en/home")
    print(driver.title)
    time.sleep(10)
    driver.save_screenshot('Screenshot_test_1.png')
    driver.refresh()
    time.sleep(10)
    driver.quit()
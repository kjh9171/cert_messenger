from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

def test():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36')
    driver = webdriver.Chrome(options=options)
    
    try:
        print("--- Naver Stock AI News ---")
        driver.get('https://stock.naver.com/')
        time.sleep(5)
        items = driver.find_elements(By.CSS_SELECTOR, '[class*="HomeAIMarketInsights_item"]')
        print('Naver Count:', len(items))
        for item in items[:3]:
            try:
                title = item.find_element(By.TAG_NAME, 'p').text
                link = item.get_attribute('href')
                print(f'Title: {title}\nLink: {link}')
            except Exception as e: print(f"Error in Naver item: {e}")
        
        print("\n--- Ddanzi News ---")
        driver.get('https://www.ddanzi.com/ddanziNews')
        time.sleep(5)
        # 딴지뉴스 게시판과 구조가 다를 수 있어 모든 'a' 태그 출력 시도
        items = driver.find_elements(By.CSS_SELECTOR, 'a')
        news_items = [i for i in items if i.get_attribute('href') and '/ddanziNews/' in i.get_attribute('href')]
        print('Ddanzi Count candidate:', len(news_items))
        for item in news_items[:5]:
            txt = item.text.strip()
            if txt:
                print(f"Title: {txt}\nLink: {item.get_attribute('href')}")
    except Exception as e:
        print(f"Global error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test()

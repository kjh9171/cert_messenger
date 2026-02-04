import requests
from bs4 import BeautifulSoup
import telegram
import asyncio
import schedule
import time
from datetime import datetime, timedelta, timezone
import sys
import os
import urllib3
import html
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# SSL 경고 메시지 무시 설정
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 설정 정보 ---
TELEGRAM_TOKEN = '8458654696:AAFbyTsyeGw2f7OO9sYm3wlQiS5NY72F3J0'
CHAT_ID = '7220628007'

URLS = {
    "yonhap": "https://news.naver.com/main/list.naver?mode=LPOD&mid=sec&sid1=001&sid2=140&oid=001&isYeonhapFlash=Y",
    "cisa_kev": "https://www.cvedetails.com/cisa-known-exploited-vulnerabilities/kev-1.html",
    "boannews": "https://www.boannews.com/media/list.asp",
    "clien_park": "https://www.clien.net/service/group/community",
    "ddanzi": "https://www.ddanzi.com/free",
    "mbc": "https://imnews.imbc.com/replay/2026/nwdesk/",
    "naver_stock": "https://stock.naver.com/",
    "ddanzi_news": "https://www.ddanzi.com/ddanziNews"
}

last_sent_titles = set()

def get_kst_now():
    return datetime.now(timezone(timedelta(hours=9)))

def capture_article_image(url, filename):
    """특정 영역(본문)만 타겟팅하여 캡처하는 최적화된 함수"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # 모바일 뷰포트와 유사하게 설정하여 가독성 증대
    chrome_options.add_argument("--window-size=800,1200")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1")

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)
        
        # 딴지일보/뉴스 특화 캡처 영역 지정 (ID: 'content' 또는 클래스 기반)
        wait = WebDriverWait(driver, 10)
        
        # 딴지일보 본문 영역이 나타날 때까지 대기
        target_element = None
        if "ddanzi.com" in url:
            try:
                # 게시판 본문 영역 선택 시도
                target_element = wait.until(EC.presence_of_element_located((By.ID, "content")))
            except:
                # 뉴스 영역 등 다른 레이아웃일 경우
                target_element = driver.find_element(By.TAG_NAME, "body")
        
        if target_element:
            # 특정 요소만 스크린샷 찍기
            target_element.screenshot(filename)
        else:
            driver.save_screenshot(filename)
            
        return filename
    except Exception as e:
        print(f"캡처 실패 ({url}): {e}")
        return None
    finally:
        if driver:
            driver.quit()

def fetch_data():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
    all_content = []

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print(f"Selenium 드라이버 초기화 실패: {e}")

    # [중략: 연합, CVE, 보안뉴스, 클리앙 로직은 기존과 동일하게 유지]
    # (기존 코드의 1~4번 섹션 유지)

    # 5. 딴지일보 자유게시판 (본문 미리보기 추가)
    try:
        res = requests.get(URLS["ddanzi"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select('table.fz_change tbody tr')
        count = 0
        for item in items:
            if count >= 5: break
            no_tag = item.select_one('.no')
            if not no_tag or not no_tag.get_text().strip().isdigit(): continue

            title_tag = item.select_one('.title a.link')
            if title_tag:
                title = title_tag.get_text().strip()
                link = title_tag['href']
                if not link.startswith('http'): link = "https://www.ddanzi.com" + link
                
                # 본문 미리보기를 위한 텍스트 추출 시도 (선택 사항)
                # 게시판 목록에서는 불가능하므로, 제목에 집중
                
                all_content.append({
                    "source": "딴지게시판", 
                    "title": title, 
                    "link": link,
                    "author": item.select_one('.author').get_text().strip() if item.select_one('.author') else "익명",
                    "hits": item.select_one('.readNum').get_text().strip() if item.select_one('.readNum') else "0"
                })
                count += 1
    except Exception as e: print(f"딴지게시판 크롤링 실패: {e}")

    # [중략: MBC, 네이버 증권 유지]
    
    # 8. 딴지뉴스 (본문 요약 로직 추가)
    if driver:
        try:
            driver.get(URLS["ddanzi_news"])
            time.sleep(3)
            links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/ddanziNews/"]')
            seen_links = set()
            count = 0
            for link_el in links:
                if count >= 3: break
                title = link_el.text.strip()
                link = link_el.get_attribute('href')
                if title and link and link not in seen_links:
                    all_content.append({
                        "source": "딴지뉴스",
                        "title": title,
                        "link": link,
                        "category": "시사/이슈"
                    })
                    seen_links.add(link)
                    count += 1
        except Exception as e: print(f"딴지뉴스 크롤링 실패: {e}")

    if driver: driver.quit()
    return all_content

async def send_briefing(is_test=False):
    global last_sent_titles
    now = get_kst_now()
    now_str = now.strftime('%Y-%m-%d %H:%M')
    
    data = fetch_data()
    if is_test:
        new_items = data[:5]
    else:
        new_items = [d for d in data if d['link'] not in last_sent_titles]

    if not new_items: return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    for item in new_items:
        icons = {"연합뉴스 속보": "🗞️", "cve 취약점 알림": "🚨", "보안뉴스": "🛡️", "클리앙 모두의 공원": "👥", "딴지게시판": "🔥", "MBC 뉴스": "📺", "네이버 증권 AI": "📈", "딴지뉴스": "📰"}
        icon = icons.get(item['source'], "📢")

        safe_title = html.escape(item['title'])
        safe_source = html.escape(item['source'])

        report = f"<b>{icon} {safe_source}</b>\n"
        report += "━━━━━━━━━━━━━━━━━━━━\n"
        report += f"📌 <b>{safe_title}</b>\n\n"
        
        if 'author' in item: report += f"👤 <b>작성자:</b> {html.escape(item['author'])}\n"
        if 'hits' in item: report += f"👀 <b>조회수:</b> {item['hits']}\n"
        
        report += f"🔗 <a href='{item['link']}'>원문 링크 보기</a>\n"
        report += "━━━━━━━━━━━━━━━━━━━━\n"
        report += f"⏰ <i>수집일시: {now_str}</i>"

        temp_img = f"shot_{int(time.time())}.png"

        try:
            # 개선된 캡처 함수 호출
            img_path = capture_article_image(item['link'], temp_img)

            if img_path and os.path.exists(img_path):
                with open(img_path, 'rb') as photo:
                    await bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=report, parse_mode='HTML')
                os.remove(img_path)
            else:
                await bot.send_message(chat_id=CHAT_ID, text=report, parse_mode='HTML')
            
            last_sent_titles.add(item['link'])
            await asyncio.sleep(1)
        except Exception as e:
            print(f"전송 오류: {e}")

    if len(last_sent_titles) > 2000:
        last_sent_titles = set(list(last_sent_titles)[-2000:])

def job_wrapper(is_test=False):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(send_briefing(is_test=is_test))
    finally:
        loop.close()

if __name__ == "__main__":
    job_wrapper(is_test=True) 
    schedule.every().hour.at(":00").do(job_wrapper)
    while True:
        schedule.run_pending()
        time.sleep(1)
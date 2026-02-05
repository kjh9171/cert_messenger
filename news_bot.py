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

# SSL 경고 메시지 무시 설정
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 설정 정보 ---
TELEGRAM_TOKEN = '8458654696:AAFbyTsyeGw2f7OO9sYm3wlQiS5NY72F3J0'
CHAT_ID = '7220628007'

# 수집 대상 URL (원본 목록 유지)
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
    """한국 표준시를 반환합니다."""
    return datetime.now(timezone(timedelta(hours=9)))

def capture_article_image(url, filename):
    """Selenium을 사용하여 페이지 전체를 캡처합니다."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1280,1024")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)
        driver.get(url)
        time.sleep(5) 
        driver.save_screenshot(filename)
        return filename
    except Exception as e:
        print(f"캡처 실패: {e}")
        return None
    finally:
        if driver: driver.quit()

def fetch_data():
    """모든 소스에서 데이터를 수집합니다."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
    all_content = []

    # 1. 연합뉴스 속보
    try:
        res = requests.get(URLS["yonhap"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('.list_body li')[:5]:
            title_tag = item.select_one('a')
            if title_tag:
                link = title_tag['href']
                if not link.startswith('http'): link = "https://news.naver.com" + link
                all_content.append({"source": "연합뉴스 속보", "title": title_tag.get_text().strip(), "link": link})
    except: pass

    # 2. CISA CVE 취약점
    try:
        res = requests.get(URLS["cisa_kev"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.select('table.searchresults tr')[1:6]
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 2:
                title = f"[{cols[1].get_text().strip()}] {cols[2].get_text().strip()}"
                all_content.append({"source": "cve 취약점 알림", "title": title, "link": URLS["cisa_kev"]})
    except: pass

    # 3. 보안뉴스
    try:
        res = requests.get(URLS["boannews"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('.news_list')[:5]:
            title_tag = item.select_one('.news_txt')
            link_tag = item.select_one('a')
            if title_tag and link_tag:
                all_content.append({"source": "보안뉴스", "title": title_tag.get_text().strip(), "link": "https://www.boannews.com" + link_tag['href']})
    except: pass

    # 4. 클리앙 모두의 공원
    try:
        res = requests.get(URLS["clien_park"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('.list_content .list_item')[:5]:
            title_tag = item.select_one('.list_title .list_subject')
            if title_tag:
                all_content.append({"source": "클리앙", "title": title_tag.get_text().strip(), "link": "https://www.clien.net" + title_tag['href']})
    except: pass

    # 5. 딴지일보 자유게시판
    try:
        res = requests.get(URLS["ddanzi"], headers=headers, timeout=10, verify=False)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('table.fz_change tbody tr')[:5]:
            title_tag = item.select_one('.title a.link')
            if title_tag:
                link = title_tag['href']
                if not link.startswith('http'): link = "https://www.ddanzi.com" + link
                all_content.append({"source": "딴지게시판", "title": title_tag.get_text().strip(), "link": link})
    except: pass

    # 6. MBC 뉴스
    try:
        res = requests.get(URLS["mbc"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('.item')[:5]:
            title_tag = item.select_one('.tit')
            link_tag = item.select_one('a')
            if title_tag and link_tag:
                link = link_tag['href']
                if not link.startswith('http'): link = "https://imnews.imbc.com" + link
                all_content.append({"source": "MBC 뉴스", "title": title_tag.get_text().strip(), "link": link})
    except: pass

    return all_content

async def send_briefing(is_test=False):
    global last_sent_titles
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    data = fetch_data()
    now_str = get_kst_now().strftime('%Y-%m-%d %H:%M')

    # 테스트 시 상위 5개, 일반 시 신규 기사만 전송
    new_items = data[:5] if is_test else [d for d in data if d['link'] not in last_sent_titles]

    if not new_items:
        print(f"[{now_str}] 새로운 정보가 없습니다.")
        return

    for item in new_items:
        safe_title = html.escape(item['title'])
        report = f"<b>📢 {item['source']}</b>\n"
        report += "━━━━━━━━━━━━━━━━━━━━\n"
        report += f"📌 <b>{safe_title}</b>\n\n"
        report += f"🔗 <a href='{item['link']}'>원문 링크 보기</a>\n"
        report += "━━━━━━━━━━━━━━━━━━━━\n"
        report += f"⏰ <i>수집일시: {now_str}</i>"

        temp_img = f"shot_{int(time.time())}.png"
        try:
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

def job_wrapper(is_test=False):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(send_briefing(is_test=is_test))
    finally:
        loop.close()

if __name__ == "__main__":
    print("통합 뉴스 브리핑 시스템 원복 가동 시작...")
    # 초기 실행 시 소스별 기사 테스트 발송
    job_wrapper(is_test=True) 
    
    schedule.every().hour.at(":00").do(job_wrapper)
    while True:
        schedule.run_pending()
        time.sleep(1)
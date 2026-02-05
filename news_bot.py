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
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 설정 정보 ---
TELEGRAM_TOKEN = '8458654696:AAFbyTsyeGw2f7OO9sYm3wlQiS5NY72F3J0'
CHAT_ID = '7220628007'
DB_FILE = "last_sent_links.txt"

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

def load_sent_links():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_sent_link(link):
    with open(DB_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")

last_sent_links = load_sent_links()

def get_kst_now():
    return datetime.now(timezone(timedelta(hours=9)))

def get_article_summary(url, source):
    """뉴스 소스별 맞춤형 본문 요약 추출"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(url, headers=headers, timeout=8, verify=False)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 소스별 본문 영역 지정
        if "ddanzi" in source:
            content_area = soup.select_one('#content_1') or soup.select_one('.read_body')
        elif "clien" in source:
            content_area = soup.select_one('.post_article')
        elif "naver" in url:
            content_area = soup.select_one('#dic_area') or soup.select_one('#articleBodyContents')
        else:
            content_area = soup.select_one('article') or soup.select_one('.news_content')

        if content_area:
            text = content_area.get_text(separator=' ', strip=True)
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 5]
            summary = " ".join(sentences[:3])
            return summary if summary else "본문을 요약할 수 없습니다."
    except:
        pass
    return "원문 링크를 참조해 주세요."

def capture_article_image(url, filename):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1080,1300")

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)
        driver.get(url)
        time.sleep(5)
        driver.save_screenshot(filename)
        return filename
    except:
        return None
    finally:
        if driver: driver.quit()

def fetch_data():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    all_content = []

    # 1. 연합뉴스
    try:
        res = requests.get(URLS["yonhap"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('.list_body li')[:3]:
            title_tag = item.select_one('a')
            if title_tag:
                link = title_tag['href']
                if not link.startswith('http'): link = "https://news.naver.com" + link
                if link not in last_sent_links:
                    all_content.append({"source": "연합뉴스 속보", "title": title_tag.get_text().strip(), "link": link})
    except Exception as e: print(f"연합뉴스 에러: {e}")

    # 2. 보안뉴스
    try:
        res = requests.get(URLS["boannews"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('.news_list')[:3]:
            title_tag = item.select_one('.news_txt')
            link_tag = item.select_one('a')
            if title_tag and link_tag:
                link = "https://www.boannews.com" + link_tag['href']
                if link not in last_sent_links:
                    all_content.append({"source": "보안뉴스", "title": title_tag.get_text().strip(), "link": link})
    except Exception as e: print(f"보안뉴스 에러: {e}")

    # 3. 클리앙
    try:
        res = requests.get(URLS["clien_park"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('.list_content .list_item')[:3]:
            title_tag = item.select_one('.list_title .list_subject')
            if title_tag:
                link = "https://www.clien.net" + title_tag['href']
                if link not in last_sent_links:
                    all_content.append({"source": "클리앙", "title": title_tag.get_text().strip(), "link": link})
    except Exception as e: print(f"클리앙 에러: {e}")

    # 4. 딴지게시판
    try:
        res = requests.get(URLS["ddanzi"], headers=headers, timeout=10, verify=False)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('table.fz_change tbody tr')[:5]:
            title_tag = item.select_one('.title a.link')
            if title_tag:
                link = title_tag['href']
                if not link.startswith('http'): link = "https://www.ddanzi.com" + link
                if link not in last_sent_links:
                    title = re.sub(r'\[\d+\]$', '', title_tag.get_text().strip())
                    all_content.append({"source": "딴지게시판", "title": title, "link": link})
    except Exception as e: print(f"딴지 에러: {e}")

    return all_content

async def send_briefing():
    global last_sent_links
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    data = fetch_data()
    now_str = get_kst_now().strftime('%Y-%m-%d %H:%M')

    if not data:
        print(f"[{now_str}] 새로운 뉴스가 없습니다.")
        return

    for item in data:
        summary = get_article_summary(item['link'], item['source'])
        safe_title = html.escape(item['title'])
        safe_summary = html.escape(summary)
        
        report = f"<b>📢 {item['source']}</b>\n"
        report += "━━━━━━━━━━━━━━━━━━━━\n"
        report += f"📌 <b>{safe_title}</b>\n\n"
        report += f"📝 <b>내용 요약:</b>\n"
        report += f"<blockquote>{safe_summary}</blockquote>\n\n"
        report += f"🔗 <a href='{item['link']}'>원문 보기</a>\n"
        report += "━━━━━━━━━━━━━━━━━━━━\n"

        temp_img = f"shot_{int(time.time())}.png"
        try:
            img_path = capture_article_image(item['link'], temp_img)
            if img_path and os.path.exists(img_path):
                with open(img_path, 'rb') as photo:
                    await bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=report, parse_mode='HTML')
                os.remove(img_path)
            else:
                await bot.send_message(chat_id=CHAT_ID, text=report, parse_mode='HTML')
            
            last_sent_links.add(item['link'])
            save_sent_link(item['link'])
            await asyncio.sleep(2)
        except Exception as e:
            print(f"전송 에러: {e}")

def job_wrapper():
    asyncio.run(send_briefing())

if __name__ == "__main__":
    print("통합 뉴스 브리핑 시스템 복구 가동...")
    job_wrapper() # 실행 즉시 수집 시작
    
    schedule.every(30).minutes.do(job_wrapper)
    while True:
        schedule.run_pending()
        time.sleep(1)
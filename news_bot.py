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
import re  # 문장 분리를 위한 정규표현식 추가
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

def get_article_summary(url):
    """기사 원문에서 첫 3문장을 추출하여 요약본을 반환합니다."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 딴지일보 게시판 및 뉴스 본문 영역 타겟팅
        content_area = soup.select_one('#content_1') or soup.select_one('.read_body') or soup.select_one('.view_content')
        
        if content_area:
            # 텍스트만 추출 후 정제
            text = content_area.get_text(separator=' ', strip=True)
            # 마침표, 물음표, 느낌표를 기준으로 문장 분리
            sentences = re.split(r'(?<=[.!?])\s+', text)
            # 첫 3문장만 추출 (빈 문장 제외)
            summary = " ".join([s for s in sentences if len(s) > 5][:3])
            return summary if summary else "본문 내용을 추출할 수 없습니다."
    except Exception as e:
        print(f"요약 추출 실패: {e}")
    return "미리보기를 지원하지 않는 페이지입니다."

def capture_article_image(url, filename):
    """본문 영역만 정밀 타겟팅하여 캡처"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=800,1000") # 세로형 뷰포트

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)
        time.sleep(3) # 렌더링 대기
        
        # 본문 핵심 요소 찾기
        try:
            target = driver.find_element(By.CSS_SELECTOR, "#content_1")
            target.screenshot(filename)
        except:
            driver.save_screenshot(filename)
        return filename
    except Exception as e:
        print(f"캡처 실패: {e}")
        return None
    finally:
        if driver: driver.quit()

def fetch_data():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
    all_content = []

    # 5. 딴지일보 자유게시판 (요약 로직 연동)
    try:
        res = requests.get(URLS["ddanzi"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select('table.fz_change tbody tr')
        count = 0
        for item in items:
            if count >= 3: break # 효율을 위해 상위 3개만
            no_tag = item.select_one('.no')
            if not no_tag or not no_tag.get_text().strip().isdigit(): continue

            title_tag = item.select_one('.title a.link')
            if title_tag:
                link = title_tag['href']
                if not link.startswith('http'): link = "https://www.ddanzi.com" + link
                
                # 상세 페이지에서 3문장 요약 추출
                summary = get_article_summary(link)
                
                all_content.append({
                    "source": "딴지게시판", 
                    "title": title_tag.get_text().strip(), 
                    "link": link,
                    "summary": summary,
                    "author": item.select_one('.author').get_text().strip() if item.select_one('.author') else "익명"
                })
                count += 1
    except Exception as e: print(f"딴지 크롤링 실패: {e}")

    # [다른 소스 생략 - 기존 로직 유지]
    return all_content

async def send_briefing(is_test=False):
    global last_sent_titles
    now = get_kst_now()
    now_str = now.strftime('%Y-%m-%d %H:%M')
    
    data = fetch_data()
    new_items = data[:3] if is_test else [d for d in data if d['link'] not in last_sent_titles]

    if not new_items: return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    for item in new_items:
        safe_title = html.escape(item['title'])
        safe_summary = html.escape(item.get('summary', '내용 없음'))
        
        # 메시지 구성 (요약본 포함)
        report = f"<b>🔥 {item['source']}</b>\n"
        report += "━━━━━━━━━━━━━━━━━━━━\n"
        report += f"📌 <b>{safe_title}</b>\n\n"
        report += f"📝 <b>주요 내용 (3문장 요약):</b>\n"
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
            
            last_sent_titles.add(item['link'])
            await asyncio.sleep(1)
        except Exception as e: print(f"전송 오류: {e}")

def job_wrapper():
    asyncio.run(send_briefing())

if __name__ == "__main__":
    print("시스템 가동... 딴지일보 3문장 요약 모드 활성화")
    asyncio.run(send_briefing(is_test=True))
    schedule.every().hour.at(":00").do(job_wrapper)
    while True:
        schedule.run_pending()
        time.sleep(1)
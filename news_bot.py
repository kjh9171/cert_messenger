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
import json
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SSL 경고 메시지 무시 설정
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 설정 정보 ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '8458654696:AAFbyTsyeGw2f7OO9sYm3wlQiS5NY72F3J0')
CHAT_ID = os.getenv('CHAT_ID', '7220628007')

# 수집 대상 URL (원본 목록 유지)
URLS = {
    "clien_news": "https://www.clien.net/service/board/park",
    "naver_yonhap": "https://news.naver.com/main/list.naver?mode=LPOD&mid=sec&sid1=001&sid2=140&oid=001&isYeonhapFlash=Y",
    "boannews": "https://www.boannews.com/media/t_list.asp",
    "krcert": "https://krcert.or.kr/kr/bbs/list.do?menuNo=205020&bbsId=B0000133"
}

SENT_TITLES_FILE = 'sent_titles.json'

def load_sent_titles():
    if os.path.exists(SENT_TITLES_FILE) and os.path.isfile(SENT_TITLES_FILE):
        try:
            with open(SENT_TITLES_FILE, 'r') as f:
                return set(json.load(f))
        except Exception as e:
            logger.error(f"Failed to load sent titles: {e}")
    return set()

def save_sent_titles(titles):
    try:
        with open(SENT_TITLES_FILE, 'w') as f:
            json.dump(list(titles), f)
    except Exception as e:
        logger.error(f"Failed to save sent titles: {e}")

last_sent_titles = load_sent_titles()

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
        logger.info(f"Screenshot captured: {filename}")
        return filename
    except Exception as e:
        logger.error(f"캡처 실패: {e}")
        return None
    finally:
        if driver: 
            driver.quit()

def fetch_data():
    """클리앙의 유용한 사이트와 새로운 소식 게시판에서 데이터를 수집합니다."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
    all_content = []

    # 1. 클리앙 유용한 사이트
    try:
        res = requests.get(URLS["clien_useful"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 공지사항 제외하고 일반 게시글만 수집 (보통 공지사항은 .list_notice 클래스가 있거나 순서가 앞임)
        # 하지만 기존 로직을 따라 상위 5개를 가져옴
        for item in soup.select('.list_content .list_item')[:5]:
            title_tag = item.select_one('.list_title .list_subject')
            if title_tag:
                all_content.append({
                    "source": "클리앙 유용한 사이트",
                    "title": title_tag.get_text().strip(),
                    "link": "https://www.clien.net" + title_tag['href']
                })
        logger.info(f"클리앙 유용한 사이트: {len([x for x in all_content if x['source'] == '클리앙 유용한 사이트'])} items")
    except Exception as e:
        logger.error(f"클리앙 유용한 사이트 수집 실패: {e}")

    # 2. 클리앙 새로운 소식
    try:
        res = requests.get(URLS["clien_news"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('.list_content .list_item')[:5]:
            title_tag = item.select_one('.list_title .list_subject')
            if title_tag:
                all_content.append({
                    "source": "클리앙 새로운 소식",
                    "title": title_tag.get_text().strip(),
                    "link": "https://www.clien.net" + title_tag['href']
                })
        logger.info(f"클리앙 새로운 소식: {len([x for x in all_content if x['source'] == '클리앙 새로운 소식'])} items")
    except Exception as e:
        logger.error(f"클리앙 새로운 소식 수집 실패: {e}")

    # 3. 네이버 연합뉴스 속보
    try:
        res = requests.get(URLS["naver_yonhap"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('.list_body li')[:5]:
            title_tag = item.select_one('a')
            if title_tag:
                link = title_tag['href']
                if not link.startswith('http'): link = "https://news.naver.com" + link
                all_content.append({
                    "source": "네이버 연합뉴스 속보",
                    "title": title_tag.get_text().strip(),
                    "link": link
                })
        logger.info(f"네이버 연합뉴스 속보: {len([x for x in all_content if x['source'] == '네이버 연합뉴스 속보'])} items")
    except Exception as e:
        logger.error(f"네이버 연합뉴스 수집 실패: {e}")

    # 4. 보안뉴스
    try:
        res = requests.get(URLS["boannews"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 보안뉴스는 .news_list a.news_content 또는 a 내부의 span으로 식별 가능
        for item in soup.select('.news_list a')[:10]: # 링크가 여러개일 수 있어 넉넉히 탐색
            title_tag = item.select_one('span')
            if title_tag and item.get('href'):
                link = item['href']
                if not link.startswith('http'): link = "https://www.boannews.com" + link
                all_content.append({
                    "source": "보안뉴스",
                    "title": title_tag.get_text().strip(),
                    "link": link
                })
        # 중복 제거 (a 태그가 여러개 잡힐 수 있음)
        seen_links = set()
        temp_content = []
        for c in all_content:
            if c['source'] == "보안뉴스":
                if c['link'] not in seen_links:
                    seen_links.add(c['link'])
                    temp_content.append(c)
            else:
                temp_content.append(c)
        all_content = temp_content
        logger.info(f"보안뉴스: {len([x for x in all_content if x['source'] == '보안뉴스'])} items")
    except Exception as e:
        logger.error(f"보안뉴스 수집 실패: {e}")

    # 5. KISA 보안공지 (KRCERT)
    try:
        res = requests.get(URLS["krcert"], headers=headers, timeout=10, verify=False)
        soup = BeautifulSoup(res.text, 'html.parser')
        # .bbsList 대신 .tbl table 또는 .board .tbl table 사용
        for item in soup.select('.tbl table tbody tr')[:5]:
            title_tag = item.select_one('td.sbj a')
            if title_tag:
                link = title_tag['href']
                if not link.startswith('http'): link = "https://krcert.or.kr" + link
                all_content.append({
                    "source": "KISA 보안공지",
                    "title": title_tag.get_text().strip(),
                    "link": link
                })
        logger.info(f"KISA 보안공지: {len([x for x in all_content if x['source'] == 'KISA 보안공지'])} items")
    except Exception as e:
        logger.error(f"KISA 보안공지 수집 실패: {e}")

    return all_content

async def send_briefing(is_test=False):
    global last_sent_titles
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    data = fetch_data()
    now_str = get_kst_now().strftime('%Y-%m-%d %H:%M')

    # 테스트 시 상위 5개, 일반 시 신규 기사만 전송
    new_items = data[:5] if is_test else [d for d in data if d['link'] not in last_sent_titles]

    if not new_items:
        logger.info(f"[{now_str}] 새로운 정보가 없습니다.")
        return

    logger.info(f"[{now_str}] {len(new_items)} 개의 새로운 정보를 전송합니다.")

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
            save_sent_titles(last_sent_titles)
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"전송 오류: {e}")

def job_wrapper(is_test=False):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(send_briefing(is_test=is_test))
    finally:
        loop.close()

if __name__ == "__main__":
    logger.info("통합 뉴스 브리핑 시스템 원복 가동 시작...")
    # 초기 실행 시 소스별 기사 테스트 발송
    job_wrapper(is_test=True) 
    
    schedule.every(5).minutes.do(job_wrapper)
    while True:
        schedule.run_pending()
        time.sleep(1)
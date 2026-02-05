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
    """기사 원문에서 첫 3문장을 안전하게 추출합니다."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
    try:
        # 응답 시간을 5초로 제한하여 시스템 지연 방지
        res = requests.get(url, headers=headers, timeout=5, verify=False)
        res.encoding = 'utf-8' # 인코딩 명시
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 딴지일보 본문 영역의 다양한 선택자 대응
        content_area = soup.select_one('#content_1') or soup.select_one('.read_body') or soup.select_one('.view_content')
        
        if content_area:
            # 불필요한 스크립트나 스타일 태그 제거
            for s in content_area(['script', 'style']):
                s.decompose()
            
            text = content_area.get_text(separator=' ', strip=True)
            # 문장 부호 뒤 공백을 기준으로 분리
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 5]
            summary = " ".join(sentences[:3])
            return summary if summary else "본문 요약을 가져올 수 없습니다."
    except Exception as e:
        print(f"요약 추출 중 오류 발생: {e}")
    return "미리보기를 지원하지 않는 페이지입니다."

def capture_article_image(url, filename):
    """안정적인 캡처를 위한 타겟 영역 설정"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1080,1200")

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(20)
        driver.get(url)
        time.sleep(3) # 동적 요소 로딩 대기
        
        # 캡처 실패 방지를 위해 바디 전체 캡처를 기본값으로 설정
        driver.save_screenshot(filename)
        return filename
    except Exception as e:
        print(f"이미지 캡처 실패: {e}")
        return None
    finally:
        if driver: driver.quit()

def fetch_data():
    """데이터 수집 로직 복구 및 안정화"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
    all_content = []

    # 5. 딴지일보 자유게시판 수집부 (복구)
    try:
        res = requests.get(URLS["ddanzi"], headers=headers, timeout=10, verify=False)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select('table.fz_change tbody tr')
        count = 0
        for item in items:
            if count >= 3: break
            
            title_tag = item.select_one('.title a.link')
            if title_tag:
                link = title_tag['href']
                if not link.startswith('http'): link = "https://www.ddanzi.com" + link
                
                title = title_tag.get_text().strip()
                # 괄호 안의 댓글 수 등 불필요 텍스트 정제
                title = re.sub(r'\[\d+\]$', '', title).strip()
                
                all_content.append({
                    "source": "딴지게시판", 
                    "title": title, 
                    "link": link,
                    "summary": get_article_summary(link),
                    "author": item.select_one('.author').get_text().strip() if item.select_one('.author') else "익명"
                })
                count += 1
    except Exception as e:
        print(f"딴지게시판 크롤링 복구 실패: {e}")

    # 다른 뉴스 소스들도 위와 유사하게 summary 필드를 추가하여 유지 가능
    return all_content

async def send_briefing(is_test=False):
    global last_sent_titles
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    now_str = get_kst_now().strftime('%Y-%m-%d %H:%M')
    
    data = fetch_data()
    # 테스트 모드 시 무조건 전송, 일반 모드 시 중복 체크
    new_items = data if is_test else [d for d in data if d['link'] not in last_sent_titles]

    if not new_items:
        print(f"[{now_str}] 새로운 뉴스가 없습니다.")
        return

    for item in new_items:
        # HTML 태그 충돌 방지를 위한 철저한 이스케이프
        safe_title = html.escape(item['title'])
        safe_summary = html.escape(item.get('summary', '내용 요약 없음'))
        
        report = f"<b>🔥 {item['source']}</b>\n"
        report += "━━━━━━━━━━━━━━━━━━━━\n"
        report += f"📌 <b>{safe_title}</b>\n\n"
        report += f"📝 <b>3문장 요약:</b>\n"
        report += f"<blockquote>{safe_summary}</blockquote>\n\n"
        report += f"🔗 <a href='{item['link']}'>원문 읽기</a>\n"
        report += "━━━━━━━━━━━━━━━━━━━━\n"
        report += f"⏰ <i>수집: {now_str}</i>"

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
            await asyncio.sleep(2) # 전송 안정성을 위해 대기 시간 상향
        except Exception as e:
            print(f"전송 단계 오류: {e}")

def job_wrapper(is_test=False):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(send_briefing(is_test=is_test))
    finally:
        loop.close()

if __name__ == "__main__":
    print("뉴스봇 복구 모드 가동 중...")
    # 즉시 테스트 발송을 수행하여 복구 확인
    job_wrapper(is_test=True)
    
    schedule.every().hour.at(":00").do(job_wrapper)
    while True:
        schedule.run_pending()
        time.sleep(1)
import requests
from bs4 import BeautifulSoup
import telegram
import asyncio
import schedule
import time
from datetime import datetime, timedelta, timezone
import sys
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# --- 설정 정보 ---
TELEGRAM_TOKEN = '8458654696:AAFbyTsyeGw2f7OO9sYm3wlQiS5NY72F3J0'
CHAT_ID = '7220628007'

# 수집 대상 URL
URLS = {
    "yonhap": "https://news.naver.com/main/list.naver?mode=LPOD&mid=sec&sid1=001&sid2=140&oid=001&isYeonhapFlash=Y",
    "kisa_notice": "https://krcert.or.kr/kr/bbs/list.do?menuNo=205022&bbsId=B0000132",
    "kisa_security": "https://krcert.or.kr/kr/bbs/list.do?menuNo=205020&bbsId=B0000133",
    "boannews": "https://www.boannews.com/media/list.asp",
    "clien_park": "https://www.clien.net/service/group/community"
}

last_sent_titles = set()

def get_kst_now():
    """UTC 기반 환경에서도 정확한 한국 시간을 반환합니다."""
    return datetime.now(timezone(timedelta(hours=9)))

def capture_article_image(url, filename="screenshot.png"):
    """Selenium을 사용하여 기사 페이지의 주요 부분을 캡처합니다."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 창 없는 모드
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1080,1200") # 기사 상단이 잘 보이도록 설정

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    try:
        driver.get(url)
        time.sleep(2) # 페이지 로딩 대기
        
        # 기사 본문 영역 또는 상단 영역 캡처 (네이버 뉴스 등 주요 사이트 대응)
        driver.save_screenshot(filename)
        return filename
    except Exception as e:
        print(f"캡처 실패 ({url}): {e}")
        return None
    finally:
        driver.quit()

def fetch_data():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
    all_content = []

    # 1. 연합뉴스 속보
    try:
        res = requests.get(URLS["yonhap"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('.list_body li')[:5]:
            title = item.select_one('a').get_text().strip()
            link = item.select_one('a')['href']
            if not link.startswith('http'): link = "https://news.naver.com" + link
            all_content.append({"source": "연합뉴스 속보", "title": title, "link": link})
    except Exception as e: print(f"연합뉴스 크롤링 실패: {e}")

    # 2. KISA 공지사항 & 보안공지
    for key in ["kisa_notice", "kisa_security"]:
        try:
            res = requests.get(URLS[key], headers=headers, timeout=10, verify=False)
            soup = BeautifulSoup(res.text, 'html.parser')
            for row in soup.select('table.basic_list tbody tr')[:3]:
                title_tag = row.select_one('td.subject a')
                if title_tag:
                    title = title_tag.get_text().strip()
                    link = "https://krcert.or.kr" + title_tag['href']
                    source_name = "KISA 공지사항" if key == "kisa_notice" else "KISA 보안공지"
                    all_content.append({"source": source_name, "title": title, "link": link})
        except Exception as e: print(f"{key} 크롤링 실패: {e}")

    # 3. 보안뉴스
    try:
        res = requests.get(URLS["boannews"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('.news_list')[:5]:
            title_tag = item.select_one('.news_txt')
            link_tag = item.select_one('a')
            if title_tag and link_tag:
                title = title_tag.get_text().strip()
                link = "https://www.boannews.com" + link_tag['href']
                all_content.append({"source": "보안뉴스", "title": title, "link": link})
    except Exception as e: print(f"보안뉴스 크롤링 실패: {e}")

    # 4. 클리앙 모두의 공원
    try:
        res = requests.get(URLS["clien_park"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select('.list_content .list_item')
        count = 0
        for item in items:
            if count >= 5: break
            title_tag = item.select_one('.list_title .list_subject')
            if title_tag:
                title = title_tag.get_text().strip()
                link = "https://www.clien.net" + title_tag['href']
                all_content.append({"source": "클리앙 모두의 공원", "title": title, "link": link})
                count += 1
    except Exception as e: print(f"클리앙 크롤링 실패: {e}")

    return all_content

async def send_briefing():
    global last_sent_titles
    now = get_kst_now()
    now_str = now.strftime('%Y-%m-%d %H:%M')
    
    data = fetch_data()
    new_items = [d for d in data if d['title'] not in last_sent_titles]

    if not new_items:
        print(f"[{now_str}] 업데이트된 새로운 정보가 없습니다.")
        return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    for item in new_items:
        # 1. 텍스트 리포트 생성
        report = f"[{item['source']}]\n"
        report += f"제목: {item['title']}\n"
        report += f"원문: {item['link']}\n"
        report += f"수집일시: {now_str}\n"

        # 2. 이미지 캡처
        img_path = capture_article_image(item['link'], filename=f"temp_{int(time.time())}.png")

        try:
            if img_path and os.path.exists(img_path):
                # 이미지가 있을 경우 이미지와 텍스트를 함께 전송
                with open(img_path, 'rb') as photo:
                    await bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=report)
                os.remove(img_path) # 전송 후 임시 파일 삭제
            else:
                # 이미지 캡처 실패 시 텍스트만 전송
                await bot.send_message(chat_id=CHAT_ID, text=report)
            
            last_sent_titles.add(item['title'])
        except Exception as e:
            print(f"전송 오류: {e}")

    # 메모리 관리
    if len(last_sent_titles) > 2000:
        last_sent_titles = set(list(last_sent_titles)[-2000:])
    print(f"[{now_str}] 브리핑 전송 완료.")

def job_wrapper():
    asyncio.run(send_briefing())

# 정각마다 실행
schedule.every().hour.at(":00").do(job_wrapper)

if __name__ == "__main__":
    print("이미지 포함 통합 뉴스 브리핑 시스템 가동 시작...")
    job_wrapper() 
    while True:
        schedule.run_pending()
        time.sleep(1)
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
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# SSL 경고 메시지 무시 설정
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 설정 정보 ---
TELEGRAM_TOKEN = '8458654696:AAFbyTsyeGw2f7OO9sYm3wlQiS5NY72F3J0'
CHAT_ID = '7220628007'

# 수집 대상 URL (KISA 대신 CVE 취약점 사이트 추가)
URLS = {
    "yonhap": "https://news.naver.com/main/list.naver?mode=LPOD&mid=sec&sid1=001&sid2=140&oid=001&isYeonhapFlash=Y",
    "cisa_kev": "https://www.cvedetails.com/cisa-known-exploited-vulnerabilities/kev-1.html",
    "boannews": "https://www.boannews.com/media/list.asp",
    "clien_park": "https://www.clien.net/service/group/community"
}

last_sent_titles = set()

def get_kst_now():
    """UTC 기반 환경에서도 정확한 한국 시간을 반환합니다."""
    return datetime.now(timezone(timedelta(hours=9)))

def capture_article_image(url, filename):
    """Selenium을 사용하여 기사 페이지의 주요 부분을 캡처합니다."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1280,1024")
    chrome_options.add_argument("--disable-gpu")
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
        print(f"캡처 실패 ({url}): {e}")
        return None
    finally:
        if driver:
            driver.quit()

def fetch_data():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
    all_content = []

    # 1. 연합뉴스 속보
    try:
        res = requests.get(URLS["yonhap"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('.list_body li')[:5]:
            title_tag = item.select_one('a')
            if title_tag:
                title = title_tag.get_text().strip()
                link = title_tag['href']
                if not link.startswith('http'): link = "https://news.naver.com" + link
                all_content.append({"source": "연합뉴스 속보", "title": title, "link": link})
    except Exception as e: print(f"연합뉴스 크롤링 실패: {e}")

    # 2. CISA Known Exploited Vulnerabilities (CVE 업데이트)
    try:
        res = requests.get(URLS["cisa_kev"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 테이블 내의 CVE ID와 제목 추출
        rows = soup.select('table.searchresults tr')[1:6] # 헤더 제외 상위 5개
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 2:
                cve_id = cols[1].get_text().strip()
                vendor_product = cols[2].get_text().strip()
                vulnerability_name = cols[3].get_text().strip()
                title = f"[{cve_id}] {vendor_product} - {vulnerability_name}"
                # 상세 정보 링크 생성
                link_tag = cols[1].find('a')
                link = "https://www.cvedetails.com" + link_tag['href'] if link_tag else URLS["cisa_kev"]
                all_content.append({"source": "CISA 취약점 알림", "title": title, "link": link})
    except Exception as e: print(f"CISA CVE 크롤링 실패: {e}")

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
        report = f"[{item['source']}]\n"
        report += f"제목: {item['title']}\n"
        report += f"원문: {item['link']}\n"
        report += f"수집일시: {now_str}"

        temp_img = f"shot_{int(time.time())}_{new_items.index(item)}.png"

        try:
            img_path = capture_article_image(item['link'], temp_img)

            if img_path and os.path.exists(img_path):
                with open(img_path, 'rb') as photo:
                    await bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=report)
                os.remove(img_path)
            else:
                await bot.send_message(chat_id=CHAT_ID, text=report)
            
            last_sent_titles.add(item['title'])
            await asyncio.sleep(1)
        except Exception as e:
            print(f"전송 오류: {e}")

    if len(last_sent_titles) > 2000:
        last_sent_titles = set(list(last_sent_titles)[-2000:])
    print(f"[{now_str}] 모든 알림 전송 완료.")

def job_wrapper():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(send_briefing())
    finally:
        loop.close()

if __name__ == "__main__":
    print("취약점 및 뉴스 통합 브리핑 시스템 가동 시작...")
    job_wrapper() 
    schedule.every().hour.at(":00").do(job_wrapper)
    while True:
        schedule.run_pending()
        time.sleep(1)
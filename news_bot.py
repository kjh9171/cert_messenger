import requests
from bs4 import BeautifulSoup
import telegram
import asyncio
import schedule
import time
from datetime import datetime, timedelta, timezone
import sys # 시스템 관련 모듈
import os # 파일 경로 및 환경 변수 관련 모듈
import urllib3 # HTTP 요청 시 경고 무시 등을 위한 모듈
import html # HTML 특수 문자 이스케이프 처리를 위한 모듈
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
                all_content.append({"source": "cve 취약점 알림", "title": title, "link": link})
    except Exception as e: print(f"CVE 크롤링 실패: {e}")

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

    # 4. 클리앙 모두의 공원 크롤링
    try:
        # 클리앙 '모두의 공원' 페이지 요청
        res = requests.get(URLS["clien_park"], headers=headers, timeout=10)
        # 응답 받은 HTML 소스를 파싱 가능한 객체로 변환
        soup = BeautifulSoup(res.text, 'html.parser')
        # 게시글 리스트 항목들을 선택
        items = soup.select('.list_content .list_item')
        count = 0
        for item in items:
            if count >= 5: break # 상위 5개 항목만 수집
            # 제목과 링크가 포함된 요소 선택
            title_tag = item.select_one('.list_title .list_subject')
            if title_tag:
                # 게시글 제목 추출
                title = title_tag.get_text().strip()
                # 게시글 상세 링크 생성
                link = "https://www.clien.net" + title_tag['href']
                
                # [고도화] 작성자 정보 추출 시도
                author_tag = item.select_one('.nickname')
                author = author_tag.get_text().strip() if author_tag else "익명"
                
                # [고도화] 조회수 정보 추출 시도
                hit_tag = item.select_one('.hit')
                hits = hit_tag.get_text().strip() if hit_tag else "0"
                
                # 수집된 정보를 상세 데이터와 함께 리스트에 추가
                all_content.append({
                    "source": "클리앙 모두의 공원", 
                    "title": title, 
                    "link": link,
                    "author": author,
                    "hits": hits
                })
                count += 1
    except Exception as e: print(f"클리앙 크롤링 실패: {e}")

    return all_content

async def send_briefing():
    """수집된 데이터를 브리핑 형식으로 포맷팅하여 텔레그램으로 전송합니다."""
    global last_sent_titles
    # 현재 한국 시간 정보 획득
    now = get_kst_now()
    # 전송 시각 문자열 생성
    now_str = now.strftime('%Y-%m-%d %H:%M')
    
    # 각 사이트로부터 최신 데이터 호출
    data = fetch_data()
    # [고도화] 링크를 기준으로 중복 여부 판단 (제목 변경 시 중복 전송 방지)
    new_items = [d for d in data if d['link'] not in last_sent_titles]

    if not new_items:
        # 새로운 항목이 없으면 로그 남기고 종료
        print(f"[{now_str}] 업데이트된 새로운 정보가 없습니다.")
        return

    # 텔레그램 봇 객체 생성
    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    for item in new_items:
        # [고도화] 소스별 이모지 설정으로 시인성 강화
        icons = {"연합뉴스 속보": "🗞️", "cve 취약점 알림": "🚨", "보안뉴스": "🛡️", "클리앙 모두의 공원": "👥"}
        icon = icons.get(item['source'], "📢")

        # [고도화] HTML 특수 문자 이스케이프 처리 (태그 충돌 방지)
        safe_title = html.escape(item['title'])
        safe_source = html.escape(item['source'])

        # [고도화] 프리미엄 스타일의 HTML 메시지 구성
        report = f"<b>{icon} {safe_source}</b>\n"
        report += "━━━━━━━━━━━━━━━━━━━━\n"
        report += f"📌 <b>{safe_title}</b>\n\n"
        
        # 추가 메타데이터가 있는 경우 (클리앙 등) 출력 내용 보강
        if 'author' in item:
            report += f"👤 <b>작성자:</b> {html.escape(item['author'])}\n"
        if 'hits' in item:
            report += f"👀 <b>조회수:</b> {item['hits']}\n"
            
        # 원문 링크를 버튼 형태의 텍스트로 제공
        report += f"🔗 <a href='{item['link']}'>원문 링크 보기</a>\n"
        report += "━━━━━━━━━━━━━━━━━━━━\n"
        report += f"⏰ <i>수집일시: {now_str}</i>"

        # 스크린샷 캡처를 위한 임시 파일명 생성
        temp_img = f"shot_{int(time.time())}_{new_items.index(item)}.png"

        try:
            # 기사 페이지 캡처 시도
            img_path = capture_article_image(item['link'], temp_img)

            if img_path and os.path.exists(img_path):
                # 사진이 성공적으로 캡처된 경우 캡션과 함께 전송 (HTML 파싱 모드 적용)
                with open(img_path, 'rb') as photo:
                    await bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=report, parse_mode='HTML')
                # 전송 후 임시 파일 삭제
                os.remove(img_path)
            else:
                # 캡처 실패 시 텍스트 메시지만 전송 (HTML 파싱 모드 적용)
                await bot.send_message(chat_id=CHAT_ID, text=report, parse_mode='HTML')
            
            # [고도화] 전송 완료된 항목의 링크를 저장하여 중복 전송 방지
            last_sent_titles.add(item['link'])
            # 연속 전송 시 텔레그램 속도 제한 방지를 위해 1초 대기
            await asyncio.sleep(1)
        except Exception as e:
            print(f"전송 오류: {e}")

    # 기록이 너무 많아지면 메모리 관리를 위해 최근 2000개만 유지
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
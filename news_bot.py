import requests
from bs4 import BeautifulSoup
import telegram
import asyncio
import schedule
import time
from datetime import datetime
import google.generativeai as genai

# --- 설정 정보 ---
# 텔레그램 봇 토큰 및 채팅 ID
TELEGRAM_TOKEN = '8458654696:AAFbyTsyeGw2f7OO9sYm3wlQiS5NY72F3J0'
CHAT_ID = '7220628007'

# 네이버 뉴스 연합뉴스 속보 페이지 URL
NEWS_URL = "https://news.naver.com/main/list.naver?mode=LPOD&mid=sec&sid1=001&sid2=140&oid=001&isYeonhapFlash=Y"

# Gemini API 설정 (이미지 생성 및 분석용)
GEMINI_API_KEY = 'AIzaSyA1kHWHYG8MUHXh2aUaDho6WBeeyMSuBpM'
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# 중복 발송 방지를 위한 저장 변수
last_news_titles = set()

def fetch_yonhap_flash_news():
    """네이버 연합뉴스 속보 리스트 수집 (필터링 없음)"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/110.0.0.0"}
    news_list = []
    
    try:
        response = requests.get(NEWS_URL, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 속보 리스트 영역 선택
        articles = soup.select('.list_body li')
        
        for article in articles:
            title_tag = article.select_one('a')
            if title_tag:
                title = title_tag.get_text().strip()
                link = title_tag['href']
                
                # 가공되지 않은 텍스트 정제 및 제외 항목 필터링
                if not title or len(title) < 5 or title.startswith("동영상"):
                    continue
                
                if not link.startswith('http'):
                    link = "https://news.naver.com" + link
                
                news_list.append({"title": title, "link": link})
    except Exception as e:
        print(f"속보 크롤링 중 오류 발생: {e}")
        
    return news_list

async def analyze_and_report():
    """연합뉴스 속보 수집 후 리포트 전송"""
    global last_news_titles
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    current_news = fetch_yonhap_flash_news()
    # 신규 뉴스만 추출
    new_articles = [n for n in current_news if n['title'] not in last_news_titles]
    
    if not new_articles:
        print(f"[{now_str}] 새로운 속보가 없습니다.")
        return

    # 브리핑 리포트 구성
    # 
    
    report = f"<b>🚨 실시간 연합뉴스 속보 브리핑</b>\n"
    report += f"📅 {now_str} 기준\n"
    report += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    report += "<b>📌 최신 주요 속보 목록</b>\n"
    # 최대 12개 뉴스까지만 노출하여 가독성 유지
    for i, article in enumerate(new_articles[:12], 1): 
        report += f"{i}. <a href='{article['link']}'>{article['title']}</a>\n"
        report += f"🔗 기사 원문 확인\n\n"
    
    report += "━━━━━━━━━━━━━━━━━━━━\n"
    report += "<i>※ 네이버 연합뉴스 속보를 실시간으로 자동 전달합니다.</i>"
    
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    try:
        # 메시지 전송
        await bot.send_message(chat_id=CHAT_ID, text=report, parse_mode='HTML', disable_web_page_preview=True)
        
        # 발송된 제목 업데이트 (누적 관리)
        last_news_titles.update([n['title'] for n in new_articles])
        print(f"[{now_str}] 속보 {len(new_articles[:12])}건 발송 완료.")
        
        # 메모리 관리를 위해 최근 500개 제목만 유지
        if len(last_news_titles) > 500:
            last_news_titles = set(list(last_news_titles)[-500:])
            
    except Exception as e:
        print(f"텔레그램 전송 오류: {e}")

def job_wrapper():
    """비동기 실행을 위한 래퍼"""
    asyncio.run(analyze_and_report())

# 매시 정각마다 자동 실행 스케줄 (원하는 주기로 변경 가능)
schedule.every().hour.at(":00").do(job_wrapper)

if __name__ == "__main__":
    print("연합뉴스 속보 자동 발송 서비스 가동 시작...")
    
    # 실행 즉시 첫 번째 테스트 발송 수행
    job_wrapper() 
    
    while True:
        schedule.run_pending()
        time.sleep(1)
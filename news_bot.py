import requests
from bs4 import BeautifulSoup
import telegram
import asyncio
import schedule
import time
from datetime import datetime
import google.generativeai as genai

# --- 설정 정보 ---
# 수정된 봇 이름: newsletter (@kjh_news_bot)
TELEGRAM_TOKEN = '8458654696:AAFbyTsyeGw2f7OO9sYm3wlQiS5NY72F3J0'
CHAT_ID = '7220628007'

# 수집 대상 뉴스 섹션 (IT/과학 및 사회)
NEWS_URLS = [
    "https://news.naver.com/main/list.naver?mode=LS2D&mid=shm&sid1=105&sid2=732", # 보안/해킹
    "https://news.naver.com/main/list.naver?mode=LS2D&mid=shm&sid1=105&sid2=283", # 컴퓨터/AI
    "https://news.naver.com/main/list.naver?mode=LS2D&mid=shm&sid1=102&sid2=249"  # 사건사고
]

GEMINI_API_KEY = 'AIzaSyA1kHWHYG8MUHXh2aUaDho6WBeeyMSuBpM'
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# 필터링 키워드 리스트
TARGET_KEYWORDS = ['정보보호', 'AI', '인공지능', '해킹', '개인정보', '보안', '유출', '사건', '사고', '피습', '경찰', '수사', '랜섬웨어', '피싱']
last_news_titles = set()

def fetch_filtered_news():
    """지정된 섹션에서 키워드에 맞는 뉴스 리스트 수집"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/110.0.0.0"}
    filtered_news = []
    
    for url in NEWS_URLS:
        try:
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            # 네이버 뉴스 리스트 태그 탐색
            articles = soup.select('.list_body li') or soup.select('.newsct_list li')
            
            for article in articles:
                title_tag = article.select_one('a')
                if title_tag:
                    title = title_tag.get_text().strip()
                    link = title_tag['href']
                    if not title or len(title) < 5: continue
                    
                    # 제목에 키워드가 포함된 경우만 추출
                    if any(keyword in title for keyword in TARGET_KEYWORDS):
                        if not link.startswith('http'):
                            link = "https://news.naver.com" + link
                        filtered_news.append({"title": title, "link": link})
        except Exception as e:
            print(f"크롤링 중 오류 발생: {e}")
    
    # 중복 뉴스 제거
    unique_news = {n['title']: n for n in filtered_news}.values()
    return list(unique_news)

async def analyze_and_report():
    """뉴스 수집 후 이미지와 함께 보고서 전송 (AI 요약 생략)"""
    global last_news_titles
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    current_news = fetch_filtered_news()
    new_articles = [n for n in current_news if n['title'] not in last_news_titles]
    
    if not new_articles:
        print(f"[{now_str}] 조건에 맞는 새로운 뉴스가 없습니다.")
        return

    # 브리핑 리포트 구성
    # 
    
    report = f"<b>🛡️ 뉴스레터 실시간 속보 브리핑</b>\n"
    report += f"📅 {now_str} 기준\n"
    report += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    report += "<b>📌 최신 속보 목록 (정보보호/AI/사건사고)</b>\n"
    for i, article in enumerate(new_articles[:10], 1): # 최대 10개 표시
        report += f"{i}. <a href='{article['link']}'>{article['title']}</a>\n"
        report += f"🔗 기사 원문 확인\n\n"
    
    report += "━━━━━━━━━━━━━━━━━━━━\n"
    report += "<i>※ 실시간 키워드 필터링을 통해 수집된 정보입니다.</i>"
    
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    try:
        # 메시지 전송
        await bot.send_message(chat_id=CHAT_ID, text=report, parse_mode='HTML', disable_web_page_preview=True)
        # 발송된 뉴스 제목 저장 (중복 방지)
        last_news_titles.update([n['title'] for n in new_articles])
        print(f"[{now_str}] 텔레그램 발송 완료.")
    except Exception as e:
        print(f"텔레그램 전송 중 오류 발생: {e}")

def job_wrapper():
    """비동기 실행을 위한 래퍼 함수"""
    asyncio.run(analyze_and_report())

# 매시 정각마다 실행 스케줄 등록
schedule.every().hour.at(":00").do(job_wrapper)

if __name__ == "__main__":
    print("시스템 환경에서 뉴스 브리핑 봇 가동 시작...")
    # 프로그램 실행 즉시 테스트 발송 수행
    job_wrapper() 
    
    while True:
        schedule.run_pending()
        time.sleep(1)
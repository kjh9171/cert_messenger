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

# 수집 대상 뉴스 섹션 (IT/과학 및 사회 섹션 전체)
NEWS_URLS = [
    "https://news.naver.com/main/list.naver?mode=LS2D&mid=shm&sid1=105&sid2=732", # 보안/해킹
    "https://news.naver.com/main/list.naver?mode=LS2D&mid=shm&sid1=105&sid2=283", # 컴퓨터/AI
    "https://news.naver.com/main/list.naver?mode=LS2D&mid=shm&sid1=102&sid2=249"  # 사건사고
]

GEMINI_API_KEY = 'AIzaSyA1kHWHYG8MUHXh2aUaDho6WBeeyMSuBpM'
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# 중복 발송 방지를 위한 저장 변수
last_news_titles = set()

def fetch_all_news():
    """지정된 섹션의 모든 최신 뉴스 리스트 수집 (필터링 없음)"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/110.0.0.0"}
    all_news = []
    
    for url in NEWS_URLS:
        try:
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            # 네이버 뉴스 리스트 태그 탐색
            articles = soup.select('.list_body li') or soup.select('.newsct_list li')
            
            for article in articles:
                title_tag = article.select_one('a')
                if title_tag:
                    # 텍스트가 비어있거나 동영상 기사 등 제외 로직
                    title = title_tag.get_text().strip()
                    link = title_tag['href']
                    if not title or len(title) < 5 or title.startswith("동영상"): 
                        continue
                    
                    if not link.startswith('http'):
                        link = "https://news.naver.com" + link
                    all_news.append({"title": title, "link": link})
        except Exception as e:
            print(f"크롤링 중 오류 발생: {e}")
    
    # 중복 제거 및 최신순 유지
    seen = set()
    unique_news = []
    for n in all_news:
        if n['title'] not in seen:
            unique_news.append(n)
            seen.add(n['title'])
            
    return unique_news

async def analyze_and_report():
    """뉴스 수집 후 리포트 전송 (키워드 필터링 없이 진행)"""
    global last_news_titles
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    current_news = fetch_all_news()
    # 이미 보낸 뉴스 제외
    new_articles = [n for n in current_news if n['title'] not in last_news_titles]
    
    if not new_articles:
        print(f"[{now_str}] 업데이트된 새로운 뉴스가 없습니다.")
        return

    # 브리핑 리포트 구성
    report = f"<b>🚀 뉴스레터 실시간 속보 브리핑</b>\n"
    report += f"📅 {now_str} 기준\n"
    report += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    report += "<b>📌 최신 속보 목록</b>\n"
    # 너무 길어지지 않게 상위 10개 혹은 15개까지만 노출
    for i, article in enumerate(new_articles[:12], 1): 
        report += f"{i}. <a href='{article['link']}'>{article['title']}</a>\n"
        report += f"🔗 기사 원문 확인\n\n"
    
    report += "━━━━━━━━━━━━━━━━━━━━\n"
    report += "<i>※ 해당 섹션의 최신 뉴스 리스트를 실시간으로 전달합니다.</i>"
    
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    try:
        await bot.send_message(chat_id=CHAT_ID, text=report, parse_mode='HTML', disable_web_page_preview=True)
        # 발송 완료 타이틀 업데이트
        last_news_titles.update([n['title'] for n in new_articles])
        print(f"[{now_str}] 텔레그램 발송 완료 (신규 {len(new_articles[:12])}건).")
    except Exception as e:
        print(f"텔레그램 전송 중 오류 발생: {e}")

def job_wrapper():
    asyncio.run(analyze_and_report())

# 매시 정각마다 실행 스케줄
schedule.every().hour.at(":00").do(job_wrapper)

if __name__ == "__main__":
    print("시스템 환경에서 필터링 없는 뉴스 브리핑 가동 시작...")
    # 실행 즉시 테스트 발송
    job_wrapper() 
    
    while True:
        schedule.run_pending()
        time.sleep(1)
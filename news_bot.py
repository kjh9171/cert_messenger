import requests
from bs4 import BeautifulSoup
import telegram
import asyncio
import schedule
import time
from datetime import datetime
import google.generativeai as genai

# --- 설정 정보 ---
TELEGRAM_TOKEN = '8458654696:AAFbyTsyeGw2f7OO9sYm3wlQiS5NY72F3J0'
CHAT_ID = '7220628007'
# 네이버 뉴스 'IT/과학' 및 '사회' 섹션 위주로 탐색하기 위해 URL 리스트 구성
NEWS_URLS = [
    "https://news.naver.com/main/list.naver?mode=LS2D&mid=shm&sid1=105&sid2=732", # 보안/해킹
    "https://news.naver.com/main/list.naver?mode=LS2D&mid=shm&sid1=105&sid2=283", # 컴퓨터/AI
    "https://news.naver.com/main/list.naver?mode=LS2D&mid=shm&sid1=102&sid2=249"  # 사건사고
]

GEMINI_API_KEY = 'AIzaSyA1kHWHYG8MUHXh2aUaDho6WBeeyMSuBpM'
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# 키워드 필터링 (정보보호, AI, 해킹, 개인정보, 사건, 사고)
TARGET_KEYWORDS = ['정보보호', 'AI', '인공지능', '해킹', '개인정보', '보안', '유출', '사건', '사고', '피습', '경찰', '수사']
last_news_titles = set()

def fetch_filtered_news():
    """지정된 섹션에서 키워드에 맞는 뉴스만 수집"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/110.0.0.0"}
    filtered_news = []
    
    for url in NEWS_URLS:
        try:
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            # 네이버 뉴스 목록 구조 (섹션별로 다를 수 있어 유연하게 선택)
            articles = soup.select('.list_body li') or soup.select('.newsct_list li')
            
            for article in articles:
                title_tag = article.select_one('a')
                if title_tag:
                    title = title_tag.get_text().strip()
                    link = title_tag['href']
                    if not title or len(title) < 5: continue
                    
                    # 키워드 매칭 검사
                    if any(keyword in title for keyword in TARGET_KEYWORDS):
                        if not link.startswith('http'):
                            link = "https://news.naver.com" + link
                        filtered_news.append({"title": title, "link": link})
        except Exception as e:
            print(f"크롤링 오류({url}): {e}")
    
    # 중복 제거 (여러 섹션에 걸친 뉴스 방지)
    unique_news = {n['title']: n for n in filtered_news}.values()
    return list(unique_news)

async def generate_comprehensive_summary(news_list):
    """수집된 뉴스 목록을 바탕으로 한 번에 종합 요약 생성"""
    if not news_list:
        return ""
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        news_context = "\n".join([f"- {n['title']}" for n in news_list])
        
        prompt = f"""
        당신은 정보보호 및 사회 이슈 전문 분석가입니다. 
        아래 뉴스 목록을 읽고, 현재의 주요 흐름을 3문장 이내로 종합 분석하세요.
        - 개별 기사 요약이 아닌 전체적인 '트렌드'와 '주의사항' 위주로 작성할 것.
        - 문체는 '~함', '~임'으로 간결하게 끝낼 것.
        - 불필요한 수식어나 마크다운(**)은 제외할 것.

        [뉴스 목록]
        {news_context}
        """
        
        response = await asyncio.to_thread(model.generate_content, prompt)
        return f"💡 <b>종합 분석:</b> {response.text.strip()}\n"
    except Exception as e:
        print(f"종합 요약 에러: {e}")
        return ""

async def analyze_and_report():
    """뉴스 필터링 및 종합 리포트 전송"""
    global last_news_titles
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    current_news = fetch_filtered_news()
    # 신규 뉴스만 추출
    new_articles = [n for n in current_news if n['title'] not in last_news_titles]
    
    if not new_articles:
        print(f"[{now_str}] 관련 신규 속보 없음.")
        return

    # 1. 종합 요약 생성 (종합 분석은 한 번만 수행)
    summary_text = await generate_comprehensive_summary(new_articles[:10])
    
    # 2. 메시지 구성
    report = f"<b>🛡️ 보안/AI/사건사고 주요 소식</b>\n"
    report += f"📅 {now_str} 기준\n"
    report += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if summary_text:
        report += f"{summary_text}\n"
        report += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    report += "<b>📌 최신 속보 목록</b>\n"
    for i, article in enumerate(new_articles[:8], 1): # 최대 8개 노출
        report += f"{i}. <a href='{article['link']}'>{article['title']}</a>\n"
    
    # 텔레그램 전송
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    try:
        await bot.send_message(chat_id=CHAT_ID, text=report, parse_mode='HTML', disable_web_page_preview=True)
        # 전송 성공 후 타이틀 업데이트
        last_news_titles.update([n['title'] for n in new_articles])
    except Exception as e:
        print(f"전송 오류: {e}")

def job_wrapper():
    asyncio.run(analyze_and_report())

# 매시 00분 실행
schedule.every().hour.at(":00").do(job_wrapper)

if __name__ == "__main__":
    print("특화 뉴스 분석 봇 가동 시작 (보안/AI/사건사고)...")
    job_wrapper() 
    while True:
        schedule.run_pending()
        time.sleep(1)
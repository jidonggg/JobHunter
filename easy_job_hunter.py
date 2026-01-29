#!/usr/bin/env python3
"""
🎯 초보자용 AI 부업 일자리 헌터 v5.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 쉬운 공고만 필터링 (난이도 1-2)
- Claude에게 시킬 프롬프트 포함
- 예상 결과물 형태 안내
- 예상 수익/작업시간 포함
- 4시간마다 자동 실행
"""

import requests
import json
import hashlib
import re
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
import xml.etree.ElementTree as ET

# ============ 설정 ============
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8147625350:AAH_S8Ma8qLCUTZ44NPSzRsQk_yh10UJ2A0')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '2136958929')

# 쉬운 작업 키워드 (이것만 검색)
EASY_KEYWORDS = [
    "n8n workflow",
    "zapier automation",
    "manychat",
    "simple chatbot",
    "csv script",
    "google sheets automation",
    "slack notification",
    "email automation simple",
    "chatgpt prompt",
    "data cleaning script",
]

SEEN_JOBS_FILE = Path("seen_jobs_v5.json")

# ============ 작업 유형 템플릿 ============
JOB_TEMPLATES = {
    "n8n_webhook_slack": {
        "keywords": ["n8n", "webhook", "slack", "notification", "form"],
        "name": "n8n 웹훅→슬랙 알림",
        "difficulty": 1,
        "price_range": "$50-100",
        "time": "30분",
        "what_client_wants": "폼 제출되면 슬랙에 알림 보내기",
        "prompt": """n8n 워크플로우 JSON 만들어줘.

기능:
1. 웹훅으로 폼 데이터 받기
2. 슬랙 채널에 메시지 보내기:
   "📬 새 폼 제출!
   이름: {{name}}
   이메일: {{email}}
   내용: {{message}}"

바로 import 가능한 JSON으로 줘.""",
        "output_type": "n8n JSON 파일",
        "delivery_msg": "n8n에서 Import → Credentials 연결 → 활성화"
    },
    
    "n8n_email_sheet": {
        "keywords": ["n8n", "email", "sheet", "google sheet", "gmail"],
        "name": "n8n 이메일→구글시트",
        "difficulty": 1,
        "price_range": "$75-150",
        "time": "30분",
        "what_client_wants": "특정 이메일 오면 구글시트에 자동 저장",
        "prompt": """n8n 워크플로우 JSON 만들어줘.

기능:
1. Gmail에서 새 이메일 감지
2. 발신자, 제목, 본문 추출
3. 구글시트에 새 행으로 추가

JSON으로 줘.""",
        "output_type": "n8n JSON 파일",
        "delivery_msg": "n8n Import → Gmail/Sheets 연결 → 활성화"
    },
    
    "n8n_ai_classify": {
        "keywords": ["n8n", "ai", "classify", "chatgpt", "categorize", "label"],
        "name": "n8n AI 분류 자동화",
        "difficulty": 2,
        "price_range": "$100-200",
        "time": "1시간",
        "what_client_wants": "AI로 이메일/데이터 자동 분류",
        "prompt": """n8n 워크플로우 JSON 만들어줘.

기능:
1. 데이터 입력 받기
2. OpenAI API로 분류 (카테고리 목록 제공)
3. 분류 결과에 따라 다른 액션

JSON으로 줘.""",
        "output_type": "n8n JSON 파일 (OpenAI 노드 포함)",
        "delivery_msg": "n8n Import → OpenAI API 키 연결 → 테스트"
    },
    
    "zapier_simple": {
        "keywords": ["zapier", "zap", "connect", "integration", "simple"],
        "name": "Zapier 연동 설정",
        "difficulty": 1,
        "price_range": "$30-75",
        "time": "30분",
        "what_client_wants": "두 앱 연결해서 자동화",
        "prompt": """Zapier 연동 가이드 만들어줘.

연동: [앱A] → [앱B]
트리거: [이벤트]
액션: [수행할 작업]

단계별 스크린샷 설명 포함해서 마크다운으로 줘.""",
        "output_type": "단계별 가이드 문서 (마크다운)",
        "delivery_msg": "PDF 또는 Notion 링크로 전달"
    },
    
    "manychat_flow": {
        "keywords": ["manychat", "instagram", "dm", "auto reply", "messenger"],
        "name": "ManyChat 자동응답",
        "difficulty": 1,
        "price_range": "$50-100",
        "time": "1시간",
        "what_client_wants": "인스타/메신저 DM 자동응답",
        "prompt": """ManyChat 자동응답 플로우 설계해줘.

키워드별 응답:
1. "price" → 가격 안내
2. "hours" → 영업시간
3. "book" → 예약 링크

각 키워드별 트리거 설정 방법 + 응답 메시지 텍스트 포함.
마크다운으로 줘.""",
        "output_type": "플로우 설계 문서 + 메시지 템플릿",
        "delivery_msg": "ManyChat에서 직접 설정하는 가이드 포함"
    },
    
    "csv_script": {
        "keywords": ["csv", "clean", "script", "python", "data", "excel", "duplicate"],
        "name": "CSV/데이터 정리 스크립트",
        "difficulty": 1,
        "price_range": "$30-75",
        "time": "30분",
        "what_client_wants": "지저분한 데이터 파일 정리",
        "prompt": """Python 스크립트 만들어줘.

기능:
1. CSV 파일 읽기
2. 중복 행 제거
3. 데이터 정리 (빈 값, 포맷 등)
4. 정리된 CSV/Excel 저장

사용법 설명 포함해서 줘.""",
        "output_type": "Python 스크립트 (.py)",
        "delivery_msg": "스크립트 파일 + 사용법 README"
    },
    
    "scraper_simple": {
        "keywords": ["scrape", "scraping", "extract", "website", "data"],
        "name": "웹 스크래핑 스크립트",
        "difficulty": 2,
        "price_range": "$50-150",
        "time": "1시간",
        "what_client_wants": "웹사이트에서 데이터 추출",
        "prompt": """Python 웹 스크래핑 스크립트 만들어줘.

타겟: [URL]
추출할 데이터: [항목들]
저장 형식: CSV/Excel

requests, beautifulsoup4 사용.
사용법 포함해서 줘.""",
        "output_type": "Python 스크립트 (.py)",
        "delivery_msg": "스크립트 + 실행 방법 + 샘플 출력"
    },
    
    "chatgpt_prompt": {
        "keywords": ["chatgpt", "prompt", "gpt", "ai prompt", "prompt engineering"],
        "name": "ChatGPT 프롬프트 작성",
        "difficulty": 1,
        "price_range": "$25-75",
        "time": "1시간",
        "what_client_wants": "특정 용도의 AI 프롬프트",
        "prompt": """[용도]용 ChatGPT 프롬프트 만들어줘.

포함할 것:
- 시스템 프롬프트
- 예시 입출력
- 톤/스타일 가이드
- 변형 버전 3개

마크다운으로 정리해줘.""",
        "output_type": "프롬프트 모음 문서",
        "delivery_msg": "마크다운/PDF로 전달"
    },
    
    "sheets_automation": {
        "keywords": ["google sheet", "spreadsheet", "formula", "automation", "apps script"],
        "name": "구글시트 자동화",
        "difficulty": 1,
        "price_range": "$30-100",
        "time": "30분-1시간",
        "what_client_wants": "스프레드시트 자동 계산/정리",
        "prompt": """구글시트 자동화 만들어줘.

기능: [원하는 기능]

Apps Script 코드 + 설정 방법 포함해서 줘.""",
        "output_type": "Apps Script 코드 + 설정 가이드",
        "delivery_msg": "코드 + 시트에 적용하는 방법"
    },
    
    "simple_bot": {
        "keywords": ["simple bot", "basic chatbot", "faq bot", "auto reply"],
        "name": "간단한 FAQ 봇",
        "difficulty": 2,
        "price_range": "$75-150",
        "time": "1-2시간",
        "what_client_wants": "자주 묻는 질문 자동응답",
        "prompt": """FAQ 챗봇 로직 만들어줘.

질문-답변 쌍:
1. [질문1] → [답변1]
2. [질문2] → [답변2]
...

키워드 매칭 방식으로 Python 코드 또는 n8n JSON으로 줘.""",
        "output_type": "Python 코드 또는 n8n JSON",
        "delivery_msg": "코드/JSON + 커스터마이징 방법"
    }
}

# ============ 유틸리티 ============

def load_seen_jobs():
    if SEEN_JOBS_FILE.exists():
        try:
            with open(SEEN_JOBS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_seen_jobs(seen):
    with open(SEEN_JOBS_FILE, 'w') as f:
        json.dump(seen[-500:], f)

def job_id(title, link):
    return hashlib.md5(f"{title}{link}".encode()).hexdigest()

def send_telegram(message):
    """텔레그램 메시지 전송 (4096자 제한 처리)"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ 텔레그램 설정 없음")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # 4096자 제한
    if len(message) > 4000:
        message = message[:3900] + "\n\n... (메시지가 잘렸습니다)"
    
    try:
        r = requests.post(url, json={
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }, timeout=30)
        return r.status_code == 200
    except Exception as e:
        print(f"❌ 텔레그램 오류: {e}")
        return False

def match_template(title, description):
    """공고에 맞는 템플릿 찾기"""
    text = (title + " " + description).lower()
    
    best_match = None
    best_score = 0
    
    for key, template in JOB_TEMPLATES.items():
        score = sum(1 for kw in template["keywords"] if kw in text)
        if score > best_score:
            best_score = score
            best_match = key
    
    if best_score >= 2:
        return JOB_TEMPLATES[best_match]
    elif best_score >= 1:
        return JOB_TEMPLATES.get(best_match)
    
    return None

def is_easy_job(title, description):
    """쉬운 작업인지 판단"""
    text = (title + " " + description).lower()
    
    # 어려운 키워드 (제외)
    hard_keywords = [
        "complex", "enterprise", "machine learning", "custom api",
        "voice ai", "real-time", "scalable", "multi-tenant",
        "blockchain", "crypto", "trading bot", "mobile app",
        "full stack", "backend developer", "senior"
    ]
    
    if any(kw in text for kw in hard_keywords):
        return False
    
    # 쉬운 키워드 (포함)
    easy_keywords = [
        "simple", "basic", "quick", "small", "easy",
        "straightforward", "beginner", "setup", "configure"
    ]
    
    # 템플릿 매칭되면 쉬움
    template = match_template(title, description)
    if template and template.get("difficulty", 5) <= 2:
        return True
    
    # 쉬운 키워드 있으면 쉬움
    if any(kw in text for kw in easy_keywords):
        return True
    
    return False

def extract_budget(text):
    """예산 추출"""
    patterns = [
        r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*[-–]\s*\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'Budget[:\s]*\$?(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            if len(match.groups()) == 2:
                return f"${match.group(1)}-${match.group(2)}"
            return f"${match.group(1)}"
    
    return "미정"

# ============ 플랫폼별 수집 ============

def fetch_upwork(keyword):
    """Upwork RSS에서 공고 수집"""
    url = f"https://www.upwork.com/ab/feed/jobs/rss?q={quote(keyword)}&sort=recency"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    jobs = []
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            for item in root.findall('.//item')[:10]:  # 최신 10개만
                title_elem = item.find('title')
                link_elem = item.find('link')
                desc_elem = item.find('description')
                
                if title_elem is not None and link_elem is not None:
                    title = title_elem.text or ""
                    link = link_elem.text or ""
                    desc = desc_elem.text if desc_elem is not None else ""
                    
                    # HTML 태그 제거
                    desc = re.sub(r'<[^>]+>', '', desc)
                    
                    jobs.append({
                        'platform': 'Upwork',
                        'title': title,
                        'link': link,
                        'description': desc[:500],
                        'budget': extract_budget(desc),
                        'keyword': keyword
                    })
    except Exception as e:
        print(f"  ❌ Upwork 오류: {e}")
    
    return jobs

def fetch_freelancer(keyword):
    """Freelancer API에서 공고 수집"""
    url = "https://www.freelancer.com/api/projects/0.1/projects/active/"
    params = {
        'query': keyword,
        'limit': 10,
        'sort_field': 'time_submitted',
    }
    
    jobs = []
    try:
        r = requests.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
        if r.status_code == 200:
            data = r.json()
            for project in data.get('result', {}).get('projects', []):
                budget_min = project.get('budget', {}).get('minimum', 0)
                budget_max = project.get('budget', {}).get('maximum', 0)
                budget = f"${int(budget_min)}-${int(budget_max)}" if budget_max else "미정"
                
                jobs.append({
                    'platform': 'Freelancer',
                    'title': project.get('title', ''),
                    'link': f"https://www.freelancer.com/projects/{project.get('seo_url', '')}",
                    'description': project.get('preview_description', '')[:500],
                    'budget': budget,
                    'keyword': keyword
                })
    except Exception as e:
        print(f"  ❌ Freelancer 오류: {e}")
    
    return jobs

# ============ 알림 포맷 ============

def format_easy_job_alert(job):
    """초보자 친화적 상세 알림 생성"""
    
    template = match_template(job['title'], job['description'])
    
    if not template:
        return None
    
    # 플랫폼 이모지
    platform_emoji = {'Upwork': '🟢', 'Freelancer': '🔵'}.get(job['platform'], '⚪')
    
    # 난이도 표시
    diff = template.get('difficulty', 3)
    diff_emoji = "🟢" if diff == 1 else "🟡" if diff == 2 else "🟠"
    diff_text = "매우 쉬움" if diff == 1 else "쉬움" if diff == 2 else "보통"
    
    message = f"""
{platform_emoji} <b>새 작업 발견!</b> | {job['platform']}

{'━'*25}
📌 <b>{template['name']}</b>
{diff_emoji} 난이도: {diff_text} | ⏱️ {template['time']}
💰 예상 수익: <b>{template['price_range']}</b>
{'━'*25}

📋 <b>원문 제목:</b>
{job['title'][:80]}

💵 <b>공고 예산:</b> {job['budget']}

{'━'*25}
🎯 <b>클라이언트가 원하는 것:</b>
{template['what_client_wants']}

{'━'*25}
💻 <b>Claude에게 이렇게 시켜:</b>
<code>{template['prompt'][:300]}...</code>

{'━'*25}
📦 <b>결과물 형태:</b>
{template['output_type']}

📤 <b>전달 방법:</b>
{template['delivery_msg']}

{'━'*25}
🔗 <a href="{job['link']}">지원하러 가기</a>
"""
    
    return message.strip()

# ============ 메인 ============

def main():
    print(f"\n{'='*50}")
    print(f"🎯 초보자용 일자리 검색 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}")
    
    seen = load_seen_jobs()
    easy_jobs = []
    
    # Upwork 검색
    print("\n🟢 Upwork 검색 중...")
    for kw in EASY_KEYWORDS:
        jobs = fetch_upwork(kw)
        print(f"   {kw}: {len(jobs)}개")
        
        for job in jobs:
            jid = job_id(job['title'], job['link'])
            if jid not in seen:
                if is_easy_job(job['title'], job['description']):
                    template = match_template(job['title'], job['description'])
                    if template:
                        job['template'] = template
                        easy_jobs.append(job)
                seen.append(jid)
        
        time.sleep(1)
    
    # Freelancer 검색
    print("\n🔵 Freelancer 검색 중...")
    for kw in EASY_KEYWORDS[:5]:  # API 제한
        jobs = fetch_freelancer(kw)
        print(f"   {kw}: {len(jobs)}개")
        
        for job in jobs:
            jid = job_id(job['title'], job['link'])
            if jid not in seen:
                if is_easy_job(job['title'], job['description']):
                    template = match_template(job['title'], job['description'])
                    if template:
                        job['template'] = template
                        easy_jobs.append(job)
                seen.append(jid)
        
        time.sleep(1)
    
    save_seen_jobs(seen)
    
    # 난이도순 정렬 (쉬운 것 먼저)
    easy_jobs.sort(key=lambda x: x.get('template', {}).get('difficulty', 5))
    
    # 알림 전송
    sent = 0
    for job in easy_jobs[:5]:  # 최대 5개
        msg = format_easy_job_alert(job)
        if msg and send_telegram(msg):
            print(f"   ✅ {job['title'][:40]}...")
            sent += 1
            time.sleep(2)  # 텔레그램 rate limit
    
    print(f"\n{'='*50}")
    print(f"✅ 완료! 쉬운 공고 {len(easy_jobs)}개 발견, {sent}개 알림")
    print(f"{'='*50}")
    
    # 요약 알림
    if sent > 0:
        summary = f"""
📊 <b>검색 완료!</b>

🆕 쉬운 공고 발견: {len(easy_jobs)}개
📤 알림 전송: {sent}개

💡 <b>작업 순서:</b>
1. 공고 확인
2. Claude에게 프롬프트 복붙
3. 결과물 받기
4. 클라이언트에게 전달
5. 💰 돈 받기!

⏰ 다음 검색: 4시간 후
"""
        send_telegram(summary)
    elif len(easy_jobs) == 0:
        send_telegram(f"""
📊 <b>검색 완료</b>

이번엔 새로운 쉬운 공고가 없어요.

⏰ 다음 검색: 4시간 후
""")

if __name__ == "__main__":
    main()

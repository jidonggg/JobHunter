#!/usr/bin/env python3
"""
🤖 AI 부업 일자리 헌터 v4.0
- 추천도 / 난이도 각각 5점
- 전체 한글 번역
- 내가 할 일 / Claude가 할 일
- 예상 작업 시간
- Claude에게 시킬 프롬프트 (구현 방법)
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

# ============ 설정 ============
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8147625350:AAH_S8Ma8qLCUTZ44NPSzRsQk_yh10UJ2A0')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '2136958929')

KEYWORDS = [
    "chatbot", "ai chatbot", "n8n", "manychat",
    "whatsapp bot", "automation", "voiceflow",
    "botpress", "gohighlevel", "zapier",
]

KOREAN_KEYWORDS = ["챗봇", "카카오톡 봇", "자동화"]

SEEN_JOBS_FILE = Path("seen_jobs.json")
if not SEEN_JOBS_FILE.exists():
    SEEN_JOBS_FILE = Path.home() / ".job_hunter_seen.json"

# ============ 작업 유형별 정보 ============
JOB_TYPES = {
    "manychat": {
        "name": "ManyChat 챗봇",
        "korean_desc": "인스타/페북 자동응답 봇",
        "difficulty": 2,
        "my_time": "1-2시간",
        "my_tasks": ["ManyChat 계정 접근권한 받기", "테스트 메시지 확인", "클라이언트에게 전달"],
        "claude_tasks": ["플로우 설계 (JSON)", "자동응답 스크립트", "키워드별 트리거 설정"],
        "prompt": "ManyChat 인스타 자동응답 봇 만들어줘. 키워드: [가격, 예약, 문의]. 각 키워드별 응답이랑 플로우 설명해줘.",
    },
    "n8n": {
        "name": "n8n 자동화",
        "korean_desc": "앱 연결 워크플로우 자동화",
        "difficulty": 3,
        "my_time": "2-3시간",
        "my_tasks": ["클라이언트에게 API 키 받기", "n8n에서 Import JSON", "Credentials 연결", "테스트 실행"],
        "claude_tasks": ["워크플로우 JSON 전체 생성", "노드 연결 로직", "에러 처리 추가"],
        "prompt": "n8n 워크플로우 만들어줘. [트리거]→[처리]→[저장]. Import 가능한 JSON으로 줘.",
    },
    "whatsapp": {
        "name": "WhatsApp 챗봇",
        "korean_desc": "왓츠앱 자동응답 봇",
        "difficulty": 3,
        "my_time": "2-4시간",
        "my_tasks": ["WhatsApp Business API 키 받기", "서버 배포 (Railway 무료)", "테스트 메시지 확인"],
        "claude_tasks": ["봇 응답 로직 코드", "Twilio/360dialog 연동", "FAQ 자동응답 스크립트"],
        "prompt": "WhatsApp 자동응답 챗봇 만들어줘. Twilio API 사용. FAQ 5개 자동응답 + 상담원 연결. Python Flask 코드로 줘.",
    },
    "voiceflow": {
        "name": "Voiceflow 챗봇",
        "korean_desc": "노코드 대화형 챗봇",
        "difficulty": 2,
        "my_time": "1-2시간",
        "my_tasks": ["Voiceflow 계정 설정", "플로우 블록 연결", "테스트"],
        "claude_tasks": ["대화 플로우 설계", "인텐트/응답 스크립트", "변수 설정 가이드"],
        "prompt": "Voiceflow 챗봇 대화 플로우 설계해줘. [인사]→[질문]→[상품추천]→[구매링크]. 블록별 설정 방법 알려줘.",
    },
    "botpress": {
        "name": "Botpress 챗봇",
        "korean_desc": "기업용 고급 AI 챗봇",
        "difficulty": 4,
        "my_time": "4-6시간",
        "my_tasks": ["Botpress Cloud 계정 설정", "봇 배포", "Knowledge Base 업로드", "통합 테스트"],
        "claude_tasks": ["봇 전체 코드/설정", "커스텀 액션 작성", "AI 응답 로직"],
        "prompt": "Botpress 고객지원 챗봇 만들어줘. FAQ 자동응답 + 상담원 에스컬레이션. 전체 설정 방법이랑 코드 줘.",
    },
    "gohighlevel": {
        "name": "GoHighLevel 자동화",
        "korean_desc": "CRM 마케팅 자동화",
        "difficulty": 3,
        "my_time": "2-3시간",
        "my_tasks": ["GHL 서브계정 접근권한 받기", "Workflows에서 설정", "테스트 리드로 확인"],
        "claude_tasks": ["워크플로우 설계", "트리거/액션 설정 가이드", "SMS/이메일 템플릿"],
        "prompt": "GoHighLevel 워크플로우 만들어줘. 새 리드→자동 SMS→캘린더 예약→팔로업. 단계별 설정 방법 알려줘.",
    },
    "zapier": {
        "name": "Zapier 연동",
        "korean_desc": "앱 연결 자동화 (가장 쉬움)",
        "difficulty": 1,
        "my_time": "30분-1시간",
        "my_tasks": ["Zapier에서 앱 연결", "테스트 실행"],
        "claude_tasks": ["Zap 단계별 설명", "필터/조건 설정 가이드"],
        "prompt": "Zapier Zap 만드는 법 알려줘. [앱A]→[앱B]→[앱C] 연결. 단계별 설정 방법 설명해줘.",
    },
    "make": {
        "name": "Make.com 자동화",
        "korean_desc": "시나리오 기반 자동화",
        "difficulty": 2,
        "my_time": "1-2시간",
        "my_tasks": ["Make.com에서 앱 연결", "시나리오 테스트"],
        "claude_tasks": ["시나리오 설계", "모듈 설정 가이드", "에러 핸들링"],
        "prompt": "Make.com 시나리오 만들어줘. [트리거]→[데이터처리]→[저장]. 모듈별 설정 방법 알려줘.",
    },
    "chatgpt_api": {
        "name": "ChatGPT API 연동",
        "korean_desc": "AI 기능 연동 개발",
        "difficulty": 3,
        "my_time": "2-3시간",
        "my_tasks": ["OpenAI API 키 설정", "서버 배포", "프롬프트 테스트/튜닝"],
        "claude_tasks": ["API 연동 코드 전체", "시스템 프롬프트 작성", "응답 처리 로직"],
        "prompt": "ChatGPT API로 고객지원 챗봇 만들어줘. 시스템 프롬프트 포함. Python 코드로 줘.",
    },
    "lead_automation": {
        "name": "리드 자동화",
        "korean_desc": "리드 수집/관리 자동화",
        "difficulty": 2,
        "my_time": "2-3시간",
        "my_tasks": ["CRM 접근권한 받기", "웹훅 연결", "테스트"],
        "claude_tasks": ["워크플로우 설계", "CRM 연동 코드", "알림 설정"],
        "prompt": "리드 자동화 워크플로우 만들어줘. 폼 제출→CRM 저장→슬랙 알림. n8n JSON으로 줘.",
    },
    "email_automation": {
        "name": "이메일 자동화",
        "korean_desc": "이메일 발송 자동화",
        "difficulty": 2,
        "my_time": "1-2시간",
        "my_tasks": ["이메일 계정 연결", "템플릿 확인", "테스트 발송"],
        "claude_tasks": ["자동화 로직", "이메일 템플릿", "스케줄 설정"],
        "prompt": "이메일 자동화 만들어줘. [트리거]→[개인화]→[발송]. n8n 또는 Make.com으로.",
    },
    "default": {
        "name": "일반 챗봇/자동화",
        "korean_desc": "챗봇 또는 자동화 작업",
        "difficulty": 3,
        "my_time": "2-4시간",
        "my_tasks": ["요구사항 정리", "설정/배포", "테스트"],
        "claude_tasks": ["코드/설정 작성", "로직 설계", "문서화"],
        "prompt": "요구사항 그대로 Claude에게 전달하면 됨. 구체적으로 설명할수록 좋음.",
    }
}

# ============ 난이도 키워드 ============
HARD_KEYWORDS = ["complex", "enterprise", "custom api", "machine learning", "ai model", "scalable", "real-time", "voice ai", "nlp", "multi-platform"]
EASY_KEYWORDS = ["simple", "basic", "quick", "small", "easy", "straightforward"]

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
        json.dump(seen[-1000:], f)

def job_id(title, link):
    return hashlib.md5(f"{title}{link}".encode()).hexdigest()

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ 텔레그램 설정 없음")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
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

def detect_job_type(title, desc):
    """작업 유형 감지"""
    text = (title + " " + desc).lower()
    
    if "manychat" in text:
        return "manychat"
    if "n8n" in text:
        return "n8n"
    if "whatsapp" in text:
        return "whatsapp"
    if "voiceflow" in text:
        return "voiceflow"
    if "botpress" in text:
        return "botpress"
    if "gohighlevel" in text or "ghl " in text or " ghl" in text:
        return "gohighlevel"
    if "zapier" in text:
        return "zapier"
    if "make.com" in text or "integromat" in text:
        return "make"
    if any(k in text for k in ["chatgpt api", "openai api", "gpt-4 api", "gpt api"]):
        return "chatgpt_api"
    if "lead" in text and any(k in text for k in ["automat", "generat", "nurtur"]):
        return "lead_automation"
    if "email" in text and "automat" in text:
        return "email_automation"
    return "default"

def calculate_difficulty(job):
    """난이도 계산 (1-5) - 1이 쉬움"""
    job_type = detect_job_type(job.get('title', ''), job.get('description', ''))
    base = JOB_TYPES.get(job_type, JOB_TYPES['default'])['difficulty']
    
    text = (job.get('title', '') + " " + job.get('description', '')).lower()
    
    # 어려운 키워드 있으면 +1
    if sum(1 for k in HARD_KEYWORDS if k in text) >= 2:
        base += 1
    
    # 쉬운 키워드 있으면 -1
    if any(k in text for k in EASY_KEYWORDS):
        base -= 1
    
    return min(5, max(1, base))

def calculate_recommendation(job):
    """추천도 계산 (1-5) - 돈 많이 + 쉬우면 높음"""
    score = 3.0
    budget = str(job.get('budget', '')).lower()
    
    # 예산 점수
    if any(x in budget for x in ['2000', '3000', '5000']):
        score += 1.5
    elif any(x in budget for x in ['1000', '1500']):
        score += 1
    elif any(x in budget for x in ['500', '800']):
        score += 0.5
    elif any(x in budget for x in ['50-', '100-']) and '500' not in budget:
        score -= 0.5
    
    # 난이도 반영 (핵심!)
    diff = calculate_difficulty(job)
    if diff >= 5:
        score -= 1.5  # 매우 어려움
    elif diff >= 4:
        score -= 1    # 어려움
    elif diff <= 2:
        score += 0.5  # 쉬움
    
    return min(5, max(1, round(score)))

def translate_to_korean(title, desc):
    """제목+설명 한글 번역"""
    text = (title + " " + desc).lower()
    
    # 패턴 매칭으로 한글 설명 생성
    if "whatsapp" in text and "chatbot" in text:
        if "lead" in text:
            return "왓츠앱 리드 수집 챗봇 만들기"
        if "support" in text or "customer" in text:
            return "왓츠앱 고객지원 챗봇 만들기"
        return "왓츠앱 자동응답 챗봇 만들기"
    
    if "instagram" in text and ("dm" in text or "chatbot" in text or "automat" in text):
        return "인스타그램 DM 자동응답 봇 만들기"
    
    if "manychat" in text:
        if "instagram" in text:
            return "ManyChat 인스타 자동응답 설정"
        return "ManyChat 챗봇 설정"
    
    if "n8n" in text:
        if "workflow" in text:
            return "n8n 워크플로우 자동화 구축"
        if "ai agent" in text:
            return "n8n AI 에이전트 구축"
        if "lead" in text:
            return "n8n 리드 자동화 구축"
        if "email" in text:
            return "n8n 이메일 자동화 구축"
        return "n8n 자동화 워크플로우 구축"
    
    if "zapier" in text:
        return "Zapier 앱 연동 자동화"
    
    if "make.com" in text or "integromat" in text:
        return "Make.com 시나리오 자동화"
    
    if "gohighlevel" in text or "ghl" in text:
        return "GoHighLevel CRM 자동화 설정"
    
    if "voiceflow" in text:
        return "Voiceflow 대화형 챗봇 만들기"
    
    if "botpress" in text:
        return "Botpress 기업용 챗봇 구축"
    
    if "chatgpt" in text or "openai" in text:
        if "api" in text:
            return "ChatGPT API 연동 개발"
        return "ChatGPT 기반 챗봇 만들기"
    
    if "lead" in text and "automat" in text:
        return "리드 수집/관리 자동화"
    
    if "email" in text and "automat" in text:
        return "이메일 자동 발송 시스템"
    
    if "crm" in text and "automat" in text:
        return "CRM 연동 자동화"
    
    if "appointment" in text or "booking" in text:
        return "예약 시스템 자동화"
    
    if "customer support" in text or "support chatbot" in text:
        return "고객지원 챗봇 만들기"
    
    if "chatbot" in text:
        return "챗봇 제작"
    
    if "automation" in text or "workflow" in text:
        return "업무 자동화 구축"
    
    return "챗봇/자동화 작업"

def stars(score):
    return "⭐" * score + "☆" * (5 - score)

def difficulty_text(level):
    texts = {1: "매우 쉬움", 2: "쉬움", 3: "보통", 4: "어려움", 5: "매우 어려움"}
    return texts.get(level, "보통")

def difficulty_emoji(level):
    if level <= 2:
        return "🟢"
    elif level == 3:
        return "🟡"
    elif level == 4:
        return "🟠"
    else:
        return "🔴"

# ============ 플랫폼별 fetch ============

def fetch_upwork(keyword):
    import xml.etree.ElementTree as ET
    
    url = f"https://www.upwork.com/ab/feed/jobs/rss?q={quote(keyword)}&sort=recency"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    jobs = []
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            for item in root.findall('.//item'):
                title = item.find('title')
                link = item.find('link')
                desc = item.find('description')
                
                if title is not None and link is not None:
                    desc_text = desc.text if desc is not None else ""
                    budget = ""
                    
                    budget_match = re.search(r'Budget[:\s]*\$?([\d,]+)', desc_text)
                    hourly_match = re.search(r'\$(\d+)\s*-\s*\$(\d+)', desc_text)
                    
                    if budget_match:
                        budget = f"${budget_match.group(1)}"
                    elif hourly_match:
                        budget = f"시급 ${hourly_match.group(1)}-{hourly_match.group(2)}"
                    elif "Hourly" in desc_text:
                        budget = "시급제"
                    
                    jobs.append({
                        'platform': 'Upwork',
                        'title': title.text,
                        'link': link.text,
                        'description': desc_text[:500],
                        'budget': budget,
                        'keyword': keyword
                    })
    except Exception as e:
        print(f"  ❌ Upwork: {e}")
    
    return jobs

def fetch_freelancer(keyword):
    url = "https://www.freelancer.com/api/projects/0.1/projects/active/"
    params = {'query': keyword, 'limit': 15, 'sort_field': 'time_submitted'}
    
    jobs = []
    try:
        r = requests.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
        if r.status_code == 200:
            data = r.json()
            for p in data.get('result', {}).get('projects', []):
                b_min = p.get('budget', {}).get('minimum', 0)
                b_max = p.get('budget', {}).get('maximum', 0)
                budget = f"${int(b_min)}-{int(b_max)}" if b_max else ""
                
                jobs.append({
                    'platform': 'Freelancer',
                    'title': p.get('title', ''),
                    'link': f"https://www.freelancer.com/projects/{p.get('seo_url', '')}",
                    'description': p.get('preview_description', '')[:500],
                    'budget': budget,
                    'keyword': keyword
                })
    except Exception as e:
        print(f"  ❌ Freelancer: {e}")
    
    return jobs

def fetch_kmong(keyword):
    return [{
        'platform': '크몽',
        'title': f'[크몽] {keyword} 의뢰',
        'link': f"https://kmong.com/requests?keyword={quote(keyword)}",
        'description': f'크몽에서 "{keyword}" 관련 의뢰 확인',
        'budget': '확인필요',
        'keyword': keyword
    }]

# ============ 알림 포맷 ============

def format_alert(job):
    """완전한 한글 알림 메시지"""
    
    rec = calculate_recommendation(job)
    diff = calculate_difficulty(job)
    job_type = detect_job_type(job['title'], job['description'])
    info = JOB_TYPES.get(job_type, JOB_TYPES['default'])
    
    korean_title = translate_to_korean(job['title'], job['description'])
    
    # 플랫폼 이모지
    p_emoji = {'Upwork': '🟢', 'Freelancer': '🔵', '크몽': '🟠'}.get(job['platform'], '⚪')
    
    # 추천 코멘트
    if rec >= 5:
        rec_comment = "🔥 강력 추천!"
    elif rec >= 4:
        rec_comment = "💎 추천"
    elif rec >= 3:
        rec_comment = "👍 해볼만함"
    else:
        rec_comment = "🤔 신중히"
    
    msg = f"""
{p_emoji} <b>{info['name']}</b> | {job['platform']}

{'━'*20}
⭐ <b>추천도:</b> {stars(rec)} {rec}/5 {rec_comment}
{difficulty_emoji(diff)} <b>난이도:</b> {stars(diff)} {diff}/5 ({difficulty_text(diff)})
{'━'*20}

📌 <b>{job['title'][:60]}</b>
🇰🇷 <b>{korean_title}</b>

💰 예산: <b>{job['budget'] or '미정'}</b>
⏱️ 예상 시간: <b>{info['my_time']}</b>

{'━'*20}
👤 <b>내가 할 일:</b>
{chr(10).join('  • ' + t for t in info['my_tasks'])}

🤖 <b>Claude가 해줄 일:</b>
{chr(10).join('  • ' + t for t in info['claude_tasks'])}

💡 <b>Claude에게 이렇게 시켜:</b>
<i>"{info['prompt']}"</i>
{'━'*20}

🔗 <a href="{job['link']}">지원하러 가기</a>
"""
    return msg.strip(), rec, diff

# ============ 메인 ============

def main():
    print(f"\n{'='*50}")
    print(f"🔍 일자리 검색 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}")
    
    seen = load_seen_jobs()
    all_new = []
    
    # Upwork
    print("\n🟢 Upwork 검색 중...")
    for kw in KEYWORDS:
        jobs = fetch_upwork(kw)
        print(f"   {kw}: {len(jobs)}개")
        for job in jobs:
            jid = job_id(job['title'], job['link'])
            if jid not in seen:
                all_new.append(job)
                seen.append(jid)
        time.sleep(1)
    
    # Freelancer
    print("\n🔵 Freelancer 검색 중...")
    for kw in KEYWORDS[:5]:
        jobs = fetch_freelancer(kw)
        print(f"   {kw}: {len(jobs)}개")
        for job in jobs:
            jid = job_id(job['title'], job['link'])
            if jid not in seen:
                all_new.append(job)
                seen.append(jid)
        time.sleep(1)
    
    # 크몽
    print("\n🟠 크몽 검색 중...")
    for kw in KOREAN_KEYWORDS:
        jobs = fetch_kmong(kw)
        for job in jobs:
            jid = job_id(job['title'], job['link'])
            if jid not in seen:
                all_new.append(job)
                seen.append(jid)
    
    save_seen_jobs(seen)
    
    # 정렬: 추천도 높고 + 난이도 낮은 것 우선
    def sort_score(job):
        rec = calculate_recommendation(job)
        diff = calculate_difficulty(job)
        return (rec * 2) - diff
    
    all_new.sort(key=sort_score, reverse=True)
    
    # 필터링: 추천도 3이상 AND 난이도 4이하
    sent = 0
    for job in all_new:
        rec = calculate_recommendation(job)
        diff = calculate_difficulty(job)
        
        if rec >= 3 and diff <= 4:
            msg, _, _ = format_alert(job)
            if send_telegram(msg):
                print(f"   ✅ {job['title'][:30]}... (추천:{rec} 난이도:{diff})")
                sent += 1
                time.sleep(1.5)
        
        if sent >= 10:
            break
    
    print(f"\n{'='*50}")
    print(f"✅ 완료! {len(all_new)}개 중 {sent}개 알림")
    print(f"{'='*50}")
    
    if sent > 0:
        send_telegram(f"""
📊 <b>검색 완료!</b>

🆕 발견: {len(all_new)}개
📤 알림: {sent}개

💡 추천 ⭐4 이상 + 난이도 🟢🟡 위주로 지원하세요!
        """)

if __name__ == "__main__":
    main()

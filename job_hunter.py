#!/usr/bin/env python3
"""
🤖 AI 부업 통합 일자리 헌터
- Upwork, Freelancer.com, 크몽 모니터링
- 1시간마다 새 일자리 체크
- 텔레그램으로 알림 + 추천도 표시

작성일: 2026-01-28
"""

import requests
import json
import hashlib
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

# ============ 설정 ============
TELEGRAM_BOT_TOKEN = "8147625350:AAH_S8Ma8qLCUTZ44NPSzRsQk_yh10UJ2A0"
TELEGRAM_CHAT_ID = "2136958929"

# 검색 키워드
KEYWORDS = [
    "chatbot",
    "ai chatbot", 
    "n8n",
    "manychat",
    "whatsapp bot",
    "automation",
    "voiceflow",
    "botpress",
    "gohighlevel",
    "zapier",
]

# 한글 키워드 (크몽용)
KOREAN_KEYWORDS = [
    "챗봇",
    "카카오톡 봇",
    "자동화",
    "n8n",
    "AI 상담",
]

# 이미 본 일자리 저장
SEEN_JOBS_FILE = Path.home() / ".job_hunter_seen.json"

# ============ 유틸리티 ============

def load_seen_jobs():
    if SEEN_JOBS_FILE.exists():
        with open(SEEN_JOBS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_seen_jobs(seen):
    with open(SEEN_JOBS_FILE, 'w') as f:
        json.dump(seen[-1000:], f)

def job_id(title, link):
    return hashlib.md5(f"{title}{link}".encode()).hexdigest()

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }, timeout=30)
        return r.status_code == 200
    except:
        return False

def calculate_score(job):
    """추천도 계산 (1-5점)"""
    score = 3  # 기본점수
    title = job.get('title', '').lower()
    desc = job.get('description', '').lower()
    budget = job.get('budget', '')
    
    # 고가 프로젝트 +1
    if any(x in str(budget).lower() for x in ['1000', '2000', '3000', '5000']):
        score += 1
    if any(x in str(budget) for x in ['500', '800']):
        score += 0.5
    
    # 핫 키워드 +1
    hot_keywords = ['n8n', 'manychat', 'whatsapp', 'gohighlevel', 'ai agent']
    if any(k in title or k in desc for k in hot_keywords):
        score += 1
    
    # 쉬운 작업 +0.5
    easy_keywords = ['simple', 'basic', 'quick', '간단', '빠른']
    if any(k in title or k in desc for k in easy_keywords):
        score += 0.5
    
    # 복잡한 작업 -0.5
    hard_keywords = ['complex', 'enterprise', 'custom api', 'machine learning']
    if any(k in title or k in desc for k in hard_keywords):
        score -= 0.5
    
    return min(5, max(1, round(score)))

def score_stars(score):
    """점수를 별로 표시"""
    return "⭐" * score + "☆" * (5 - score)

# ============ UPWORK ============

def fetch_upwork(keyword):
    """Upwork RSS 피드"""
    import xml.etree.ElementTree as ET
    
    url = f"https://www.upwork.com/ab/feed/jobs/rss?q={quote(keyword)}&sort=recency"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
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
                    # 예산 추출 시도
                    desc_text = desc.text if desc is not None else ""
                    budget = ""
                    if "Budget" in desc_text:
                        budget_match = re.search(r'Budget[:\s]*\$?([\d,]+)', desc_text)
                        if budget_match:
                            budget = f"${budget_match.group(1)}"
                    elif "Hourly" in desc_text:
                        budget = "시급제"
                    
                    jobs.append({
                        'platform': 'Upwork',
                        'title': title.text,
                        'link': link.text,
                        'description': desc_text[:400],
                        'budget': budget,
                        'keyword': keyword
                    })
    except Exception as e:
        print(f"  ❌ Upwork 오류: {e}")
    
    return jobs

# ============ FREELANCER.COM ============

def fetch_freelancer(keyword):
    """Freelancer.com API (공개)"""
    url = "https://www.freelancer.com/api/projects/0.1/projects/active/"
    params = {
        'query': keyword,
        'limit': 20,
        'sort_field': 'time_submitted',
        'job_details': 'true',
        'compact': 'false'
    }
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    jobs = []
    try:
        r = requests.get(url, params=params, headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            for project in data.get('result', {}).get('projects', []):
                budget_min = project.get('budget', {}).get('minimum', 0)
                budget_max = project.get('budget', {}).get('maximum', 0)
                budget = f"${budget_min}-{budget_max}" if budget_max else ""
                
                jobs.append({
                    'platform': 'Freelancer',
                    'title': project.get('title', ''),
                    'link': f"https://www.freelancer.com/projects/{project.get('seo_url', '')}",
                    'description': project.get('preview_description', '')[:400],
                    'budget': budget,
                    'keyword': keyword
                })
    except Exception as e:
        print(f"  ❌ Freelancer 오류: {e}")
    
    return jobs

# ============ 크몽 ============

def fetch_kmong(keyword):
    """크몽 검색 (웹 스크래핑)"""
    url = f"https://kmong.com/search?q={quote(keyword)}&tab=category"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'ko-KR,ko;q=0.9'
    }
    
    jobs = []
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            # 간단한 파싱 (의뢰 요청 찾기)
            # 크몽은 주로 판매자 마켓이라 의뢰는 별도 섹션
            # 여기서는 기본 정보만 제공
            
            # 크몽 의뢰하기 페이지
            request_url = f"https://kmong.com/requests?keyword={quote(keyword)}"
            jobs.append({
                'platform': '크몽',
                'title': f'[크몽 의뢰 검색] {keyword}',
                'link': request_url,
                'description': f'크몽에서 "{keyword}" 관련 의뢰를 확인하세요.',
                'budget': '확인필요',
                'keyword': keyword
            })
    except Exception as e:
        print(f"  ❌ 크몽 오류: {e}")
    
    return jobs

# ============ 메인 로직 ============

def format_job_alert(job):
    """알림 메시지 포맷"""
    score = calculate_score(job)
    stars = score_stars(score)
    
    # 설명 정리
    desc = job['description']
    desc = re.sub(r'<[^>]+>', '', desc)  # HTML 태그 제거
    desc = desc[:250] + "..." if len(desc) > 250 else desc
    
    platform_emoji = {
        'Upwork': '🟢',
        'Freelancer': '🔵', 
        '크몽': '🟠'
    }
    emoji = platform_emoji.get(job['platform'], '⚪')
    
    msg = f"""
{emoji} <b>[{job['platform']}] 새 일자리!</b>

{stars} 추천도: {score}/5

📌 <b>{job['title']}</b>

💰 예산: {job['budget'] or '미정'}
🏷️ 키워드: #{job['keyword'].replace(' ', '_')}

📝 {desc}

🔗 <a href="{job['link']}">바로가기</a>
"""
    return msg.strip(), score

def check_all_platforms():
    """모든 플랫폼 체크"""
    print(f"\n{'='*60}")
    print(f"🔍 일자리 검색 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    seen = load_seen_jobs()
    all_new_jobs = []
    
    # 1. Upwork
    print("\n🟢 Upwork 검색 중...")
    for kw in KEYWORDS:
        print(f"   → {kw}")
        jobs = fetch_upwork(kw)
        for job in jobs:
            jid = job_id(job['title'], job['link'])
            if jid not in seen:
                all_new_jobs.append(job)
                seen.append(jid)
        time.sleep(1)
    
    # 2. Freelancer
    print("\n🔵 Freelancer.com 검색 중...")
    for kw in KEYWORDS[:5]:  # 주요 키워드만
        print(f"   → {kw}")
        jobs = fetch_freelancer(kw)
        for job in jobs:
            jid = job_id(job['title'], job['link'])
            if jid not in seen:
                all_new_jobs.append(job)
                seen.append(jid)
        time.sleep(1)
    
    # 3. 크몽
    print("\n🟠 크몽 검색 중...")
    for kw in KOREAN_KEYWORDS[:3]:
        print(f"   → {kw}")
        jobs = fetch_kmong(kw)
        for job in jobs:
            jid = job_id(job['title'], job['link'])
            if jid not in seen:
                all_new_jobs.append(job)
                seen.append(jid)
        time.sleep(1)
    
    save_seen_jobs(seen)
    
    # 추천도 높은 순으로 정렬
    scored_jobs = [(job, calculate_score(job)) for job in all_new_jobs]
    scored_jobs.sort(key=lambda x: x[1], reverse=True)
    
    # 알림 전송 (상위 10개만)
    sent_count = 0
    for job, score in scored_jobs[:10]:
        msg, _ = format_job_alert(job)
        if send_telegram(msg):
            print(f"   ✅ 알림: [{job['platform']}] {job['title'][:30]}... (추천:{score})")
            sent_count += 1
            time.sleep(1)
    
    print(f"\n{'='*60}")
    print(f"✅ 완료! 총 {len(all_new_jobs)}개 발견, {sent_count}개 알림 전송")
    print(f"{'='*60}")
    
    return sent_count

def run_hourly():
    """1시간마다 실행"""
    print("""
╔════════════════════════════════════════════════════════════╗
║        🤖 AI 부업 통합 일자리 헌터 시작!                  ║
║                                                            ║
║   📍 모니터링 플랫폼:                                      ║
║      • Upwork (메인)                                       ║
║      • Freelancer.com (보조)                               ║
║      • 크몽 (한국)                                         ║
║                                                            ║
║   ⏰ 1시간마다 자동 체크                                   ║
║   📱 텔레그램으로 알림 (추천도 포함)                       ║
║                                                            ║
║   Ctrl+C 로 종료                                           ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    # 시작 알림
    send_telegram("""
🚀 <b>일자리 헌터 시작!</b>

📍 모니터링 중:
• 🟢 Upwork
• 🔵 Freelancer.com  
• 🟠 크몽

🏷️ 키워드: chatbot, n8n, manychat, automation 등

⏰ 1시간마다 체크
⭐ 추천도 높은 순으로 알림
    """)
    
    while True:
        try:
            check_all_platforms()
            print(f"\n⏰ 다음 체크: 1시간 후...")
            time.sleep(3600)  # 1시간
        except KeyboardInterrupt:
            print("\n\n👋 종료!")
            send_telegram("🛑 일자리 헌터 종료됨")
            break
        except Exception as e:
            print(f"\n❌ 오류: {e}")
            time.sleep(60)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        check_all_platforms()
    else:
        run_hourly()

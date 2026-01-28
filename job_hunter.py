#!/usr/bin/env python3
"""
🤖 AI 부업 통합 일자리 헌터 (GitHub Actions 버전)
- Upwork, Freelancer.com, 크몽 모니터링
- 1시간마다 자동 실행 (GitHub Actions)
- 텔레그램으로 알림 + 추천도 표시
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

# ============ 설정 (환경변수에서 읽기) ============
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

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
]

# 이미 본 일자리 저장 (GitHub Actions에서는 현재 디렉토리)
SEEN_JOBS_FILE = Path("seen_jobs.json")

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

def calculate_score(job):
    """추천도 계산 (1-5점)"""
    score = 3
    title = job.get('title', '').lower()
    desc = job.get('description', '').lower()
    budget = str(job.get('budget', '')).lower()
    
    # 고가 프로젝트
    if any(x in budget for x in ['1000', '2000', '3000', '5000']):
        score += 1
    if any(x in budget for x in ['500', '800']):
        score += 0.5
    
    # 핫 키워드
    hot = ['n8n', 'manychat', 'whatsapp', 'gohighlevel', 'ai agent', 'make.com']
    if any(k in title or k in desc for k in hot):
        score += 1
    
    # 쉬운 작업
    easy = ['simple', 'basic', 'quick', 'small', '간단', '빠른']
    if any(k in title or k in desc for k in easy):
        score += 0.5
    
    # 어려운 작업
    hard = ['complex', 'enterprise', 'machine learning', 'custom api']
    if any(k in title or k in desc for k in hard):
        score -= 0.5
    
    return min(5, max(1, round(score)))

def score_stars(score):
    return "⭐" * score + "☆" * (5 - score)

# ============ UPWORK ============

def fetch_upwork(keyword):
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
                    desc_text = desc.text if desc is not None else ""
                    budget = ""
                    if "Budget" in desc_text:
                        match = re.search(r'Budget[:\s]*\$?([\d,]+)', desc_text)
                        if match:
                            budget = f"${match.group(1)}"
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

# ============ FREELANCER ============

def fetch_freelancer(keyword):
    url = "https://www.freelancer.com/api/projects/0.1/projects/active/"
    params = {
        'query': keyword,
        'limit': 20,
        'sort_field': 'time_submitted',
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
    jobs = []
    try:
        request_url = f"https://kmong.com/requests?keyword={quote(keyword)}"
        jobs.append({
            'platform': '크몽',
            'title': f'[크몽] {keyword} 의뢰 검색',
            'link': request_url,
            'description': f'크몽에서 "{keyword}" 관련 의뢰를 확인하세요.',
            'budget': '확인필요',
            'keyword': keyword
        })
    except Exception as e:
        print(f"  ❌ 크몽 오류: {e}")
    
    return jobs

# ============ 메인 ============

def format_alert(job):
    score = calculate_score(job)
    stars = score_stars(score)
    
    desc = re.sub(r'<[^>]+>', '', job['description'])
    desc = desc[:250] + "..." if len(desc) > 250 else desc
    
    emoji = {'Upwork': '🟢', 'Freelancer': '🔵', '크몽': '🟠'}.get(job['platform'], '⚪')
    
    msg = f"""
{emoji} <b>[{job['platform']}] 새 일자리!</b>

{stars} 추천도: {score}/5

📌 <b>{job['title'][:80]}</b>

💰 예산: {job['budget'] or '미정'}
🏷️ #{job['keyword'].replace(' ', '_')}

📝 {desc}

🔗 <a href="{job['link']}">바로가기</a>
"""
    return msg.strip(), score

def main():
    print(f"🔍 일자리 검색 시작 - {datetime.now().isoformat()}")
    
    seen = load_seen_jobs()
    all_new = []
    
    # Upwork
    print("\n🟢 Upwork...")
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
    print("\n🔵 Freelancer...")
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
    print("\n🟠 크몽...")
    for kw in KOREAN_KEYWORDS:
        jobs = fetch_kmong(kw)
        for job in jobs:
            jid = job_id(job['title'], job['link'])
            if jid not in seen:
                all_new.append(job)
                seen.append(jid)
    
    save_seen_jobs(seen)
    
    # 추천도순 정렬
    scored = [(job, calculate_score(job)) for job in all_new]
    scored.sort(key=lambda x: x[1], reverse=True)
    
    # 상위 10개 알림
    sent = 0
    for job, score in scored[:10]:
        if score >= 3:  # 추천도 3점 이상만
            msg, _ = format_alert(job)
            if send_telegram(msg):
                print(f"   ✅ [{job['platform']}] {job['title'][:30]}... (⭐{score})")
                sent += 1
                time.sleep(1)
    
    print(f"\n✅ 완료! {len(all_new)}개 발견, {sent}개 알림")
    
    # 요약 알림
    if sent > 0:
        send_telegram(f"📊 이번 시간 검색 완료!\n\n🆕 새 일자리: {len(all_new)}개\n📤 알림 전송: {sent}개")

if __name__ == "__main__":
    main()

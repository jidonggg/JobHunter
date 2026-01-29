#!/usr/bin/env python3
"""
🧠 스마트 일자리 헌터 v6.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 키워드 1차 필터링
- Claude API로 공고 상세 분석
- 진짜 쉬운 것만 필터링
- 해결 방법 + 코드/JSON까지 생성
- 텔레그램 전송
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# 검색 키워드
SEARCH_KEYWORDS = [
    "n8n workflow",
    "zapier automation", 
    "make automation",
    "manychat",
    "chatbot simple",
    "google sheets script",
    "slack bot",
    "telegram bot",
    "email automation",
    "chatgpt prompt",
    "csv python",
    "data cleaning",
    "web scraping simple",
]

SEEN_JOBS_FILE = Path("seen_jobs_v6.json")

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
    """텔레그램 메시지 전송"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ 텔레그램 설정 없음")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # 4096자 제한
    if len(message) > 4000:
        message = message[:3900] + "\n\n... (더 보기: 링크 클릭)"
    
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

def extract_budget(text):
    """예산 추출"""
    patterns = [
        r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*[-–]\s*\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'Budget[:\s]*\$?(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if len(match.groups()) == 2:
                return f"${match.group(1)}-${match.group(2)}"
            return f"${match.group(1)}"
    
    return "미정"

# ============ Claude API 분석 ============

def analyze_job_with_claude(job):
    """Claude API로 공고 분석 및 솔루션 생성"""
    
    if not ANTHROPIC_API_KEY:
        print("⚠️ ANTHROPIC_API_KEY 없음")
        return None
    
    prompt = f"""당신은 프리랜서 일자리 분석가입니다.

아래 공고를 분석해서 JSON으로 답변해주세요.

## 공고 정보
- 플랫폼: {job['platform']}
- 제목: {job['title']}
- 설명: {job['description']}
- 예산: {job['budget']}

## 분석 기준

### 쉬운 작업 (is_easy: true)
- n8n/Zapier/Make 워크플로우 (단순 연동)
- ManyChat/Chatbot 플로우 설정
- Google Sheets 스크립트
- 간단한 Python 스크립트 (CSV 정리, 데이터 처리)
- ChatGPT 프롬프트 작성
- 단순 웹 스크래핑
- Slack/Telegram 봇 (단순 알림)
- API 연동 (1-2개 서비스)

### 어려운 작업 (is_easy: false)
- 복잡한 백엔드 개발
- 모바일 앱 개발
- ML/AI 모델 학습
- 실시간 시스템
- 복잡한 인증/보안
- 대규모 데이터 처리
- 여러 시스템 통합
- 유지보수/지속 작업

## 응답 형식 (JSON만 출력)

쉬운 작업인 경우:
```json
{{
  "is_easy": true,
  "confidence": 0.9,
  "category": "n8n workflow",
  "summary_ko": "구글폼 제출시 슬랙 알림 보내기",
  "requirements": [
    "웹훅으로 폼 데이터 받기",
    "슬랙 채널에 메시지 전송"
  ],
  "estimated_time": "30분-1시간",
  "estimated_price": "$50-100",
  "difficulty": 1,
  "solution_type": "n8n_json",
  "solution_description": "n8n 워크플로우 JSON 파일",
  "claude_prompt": "n8n 워크플로우 JSON 만들어줘.\\n\\n기능:\\n1. 웹훅 트리거\\n2. 슬랙 메시지 전송\\n\\nJSON으로 줘.",
  "delivery_guide": "1. n8n에서 Import\\n2. Credentials 연결\\n3. 활성화"
}}
```

어려운 작업인 경우:
```json
{{
  "is_easy": false,
  "confidence": 0.8,
  "reason": "복잡한 실시간 데이터 처리와 ML 모델 필요"
}}
```

JSON만 출력하세요. 다른 텍스트 없이."""

    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1500,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=60
        )
        
        if r.status_code == 200:
            content = r.json()['content'][0]['text']
            
            # JSON 추출
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
        else:
            print(f"❌ Claude API 오류: {r.status_code} - {r.text[:200]}")
            
    except Exception as e:
        print(f"❌ Claude 분석 오류: {e}")
    
    return None

# ============ 플랫폼별 수집 ============

def fetch_upwork(keyword):
    """Upwork RSS"""
    url = f"https://www.upwork.com/ab/feed/jobs/rss?q={quote(keyword)}&sort=recency"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    jobs = []
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            for item in root.findall('.//item')[:8]:
                title_elem = item.find('title')
                link_elem = item.find('link')
                desc_elem = item.find('description')
                
                if title_elem is not None and link_elem is not None:
                    title = title_elem.text or ""
                    link = link_elem.text or ""
                    desc = desc_elem.text if desc_elem is not None else ""
                    desc = re.sub(r'<[^>]+>', '', desc)
                    
                    jobs.append({
                        'platform': 'Upwork',
                        'title': title,
                        'link': link,
                        'description': desc[:1000],
                        'budget': extract_budget(desc)
                    })
    except Exception as e:
        print(f"  ❌ Upwork 오류: {e}")
    
    return jobs

def fetch_freelancer(keyword):
    """Freelancer API"""
    url = "https://www.freelancer.com/api/projects/0.1/projects/active/"
    params = {'query': keyword, 'limit': 8, 'sort_field': 'time_submitted'}
    
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
                    'description': project.get('preview_description', '')[:1000],
                    'budget': budget
                })
    except Exception as e:
        print(f"  ❌ Freelancer 오류: {e}")
    
    return jobs

def fetch_peopleperhour(keyword):
    """PeoplePerHour RSS"""
    url = f"https://www.peopleperhour.com/freelance-jobs/rss?q={quote(keyword)}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    jobs = []
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            for item in root.findall('.//item')[:8]:
                title_elem = item.find('title')
                link_elem = item.find('link')
                desc_elem = item.find('description')
                
                if title_elem is not None and link_elem is not None:
                    title = title_elem.text or ""
                    link = link_elem.text or ""
                    desc = desc_elem.text if desc_elem is not None else ""
                    desc = re.sub(r'<[^>]+>', '', desc)
                    
                    jobs.append({
                        'platform': 'PeoplePerHour',
                        'title': title,
                        'link': link,
                        'description': desc[:1000],
                        'budget': extract_budget(desc)
                    })
    except Exception as e:
        print(f"  ❌ PeoplePerHour 오류: {e}")
    
    return jobs

def fetch_remoteok(keyword):
    """RemoteOK API"""
    url = "https://remoteok.com/api"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    jobs = []
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            keyword_lower = keyword.lower()
            
            for job in data[1:30]:
                title = job.get('position', '')
                desc = job.get('description', '')
                tags = ' '.join(job.get('tags', []))
                
                if keyword_lower in title.lower() or keyword_lower in desc.lower() or keyword_lower in tags.lower():
                    salary = job.get('salary_min', '')
                    budget = f"${salary}+" if salary else "미정"
                    
                    jobs.append({
                        'platform': 'RemoteOK',
                        'title': title,
                        'link': job.get('url', ''),
                        'description': re.sub(r'<[^>]+>', '', desc)[:1000],
                        'budget': budget
                    })
                    
                    if len(jobs) >= 8:
                        break
    except Exception as e:
        print(f"  ❌ RemoteOK 오류: {e}")
    
    return jobs

def fetch_kmong(keyword):
    """크몽 검색"""
    keyword_map = {
        "n8n workflow": "n8n 자동화",
        "zapier automation": "자동화",
        "make automation": "자동화",
        "manychat": "챗봇",
        "chatbot simple": "챗봇",
        "google sheets script": "구글시트",
        "slack bot": "슬랙",
        "telegram bot": "텔레그램 봇",
        "email automation": "이메일 자동화",
        "chatgpt prompt": "ChatGPT",
        "csv python": "파이썬",
        "data cleaning": "데이터 정리",
        "web scraping simple": "크롤링",
    }
    
    kr_keyword = keyword_map.get(keyword, keyword)
    url = f"https://kmong.com/search?type=gig&keyword={quote(kr_keyword)}"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'ko-KR,ko;q=0.9'}
    
    jobs = []
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            titles = re.findall(r'"title":"([^"]+)"', r.text)
            links = re.findall(r'"url":"(/gig/[^"]+)"', r.text)
            prices = re.findall(r'"price":(\d+)', r.text)
            
            for i, (title, link) in enumerate(zip(titles[:8], links[:8])):
                price = prices[i] if i < len(prices) else 0
                
                jobs.append({
                    'platform': '크몽',
                    'title': title,
                    'link': f"https://kmong.com{link}",
                    'description': title,
                    'budget': f"₩{int(price):,}" if price else "가격문의"
                })
    except Exception as e:
        print(f"  ❌ 크몽 오류: {e}")
    
    return jobs

# ============ 알림 포맷 ============

def format_smart_alert(job, analysis):
    """분석 결과 기반 상세 알림"""
    
    platform_emoji = {
        'Upwork': '🟢', 
        'Freelancer': '🔵',
        'PeoplePerHour': '🟣',
        'RemoteOK': '🟠',
        '크몽': '🟤'
    }.get(job['platform'], '⚪')
    
    diff = analysis.get('difficulty', 3)
    diff_bar = "🟢" * diff + "⚪" * (5 - diff)
    diff_text = ["", "매우 쉬움", "쉬움", "보통", "어려움", "매우 어려움"][min(diff, 5)]
    
    confidence = int(analysis.get('confidence', 0) * 100)
    
    requirements = analysis.get('requirements', [])
    req_text = "\n".join([f"  • {r}" for r in requirements[:5]])
    
    message = f"""
{platform_emoji} <b>✅ 쉬운 작업 발견!</b> | {job['platform']}

{'━'*28}
📌 <b>{analysis.get('summary_ko', job['title'][:50])}</b>
{'━'*28}

🎯 <b>카테고리:</b> {analysis.get('category', '기타')}
{diff_bar} 난이도: {diff_text}
🎲 <b>확신도:</b> {confidence}%

⏱️ <b>예상 시간:</b> {analysis.get('estimated_time', '미정')}
💰 <b>예상 수익:</b> {analysis.get('estimated_price', job['budget'])}

{'━'*28}
📋 <b>요구사항:</b>
{req_text}

{'━'*28}
📦 <b>결과물:</b> {analysis.get('solution_description', '코드/문서')}

{'━'*28}
💻 <b>Claude에게 이렇게 시켜:</b>
<code>{analysis.get('claude_prompt', '...')[:500]}</code>

{'━'*28}
📤 <b>전달 방법:</b>
{analysis.get('delivery_guide', '파일 전달')}

{'━'*28}
📝 <b>원문 제목:</b>
{job['title'][:80]}

🔗 <a href="{job['link']}">지원하러 가기</a>
"""
    
    return message.strip()

# ============ 메인 ============

def main():
    print(f"\n{'='*50}")
    print(f"🧠 스마트 일자리 헌터 v6 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}")
    
    if not ANTHROPIC_API_KEY:
        print("❌ ANTHROPIC_API_KEY 환경변수 필요!")
        send_telegram("❌ ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        return
    
    seen = load_seen_jobs()
    all_jobs = []
    
    # ===== 1단계: 공고 수집 =====
    print("\n📥 1단계: 공고 수집")
    
    print("\n🟢 Upwork...")
    for kw in SEARCH_KEYWORDS[:6]:
        jobs = fetch_upwork(kw)
        all_jobs.extend(jobs)
        print(f"   {kw}: {len(jobs)}개")
        time.sleep(0.5)
    
    print("\n🔵 Freelancer...")
    for kw in SEARCH_KEYWORDS[:4]:
        jobs = fetch_freelancer(kw)
        all_jobs.extend(jobs)
        print(f"   {kw}: {len(jobs)}개")
        time.sleep(0.5)
    
    print("\n🟣 PeoplePerHour...")
    for kw in SEARCH_KEYWORDS[:4]:
        jobs = fetch_peopleperhour(kw)
        all_jobs.extend(jobs)
        print(f"   {kw}: {len(jobs)}개")
        time.sleep(0.5)
    
    print("\n🟠 RemoteOK...")
    for kw in SEARCH_KEYWORDS[:3]:
        jobs = fetch_remoteok(kw)
        all_jobs.extend(jobs)
        print(f"   {kw}: {len(jobs)}개")
        time.sleep(0.5)
    
    print("\n🟤 크몽...")
    for kw in SEARCH_KEYWORDS[:4]:
        jobs = fetch_kmong(kw)
        all_jobs.extend(jobs)
        print(f"   {kw}: {len(jobs)}개")
        time.sleep(0.5)
    
    print(f"\n   총 수집: {len(all_jobs)}개")
    
    # 중복 제거 및 새 공고 필터링
    new_jobs = []
    for job in all_jobs:
        jid = job_id(job['title'], job['link'])
        if jid not in seen:
            new_jobs.append(job)
            seen.append(jid)
    
    print(f"   새 공고: {len(new_jobs)}개")
    save_seen_jobs(seen)
    
    if not new_jobs:
        print("\n✅ 새 공고 없음")
        send_telegram(f"""
📊 <b>검색 완료</b> - {datetime.now().strftime('%H:%M')}

새로운 공고가 없습니다.

⏰ 다음 검색: 4시간 후
""")
        return
    
    # ===== 2단계: Claude 분석 =====
    print(f"\n🧠 2단계: Claude 분석 (최대 15개)")
    
    easy_jobs = []
    analyzed = 0
    
    for job in new_jobs[:15]:  # API 비용 절약
        print(f"\n   분석 중: {job['title'][:40]}...")
        
        analysis = analyze_job_with_claude(job)
        analyzed += 1
        
        if analysis and analysis.get('is_easy') and analysis.get('confidence', 0) >= 0.7:
            print(f"   ✅ 쉬운 작업! (확신도: {analysis.get('confidence', 0)*100:.0f}%)")
            easy_jobs.append({'job': job, 'analysis': analysis})
        else:
            reason = analysis.get('reason', '기준 미달') if analysis else '분석 실패'
            print(f"   ❌ 제외: {reason[:30]}")
        
        time.sleep(1)  # API rate limit
    
    # ===== 3단계: 알림 전송 =====
    print(f"\n📤 3단계: 알림 전송")
    
    sent = 0
    for item in easy_jobs[:5]:  # 최대 5개
        msg = format_smart_alert(item['job'], item['analysis'])
        if send_telegram(msg):
            print(f"   ✅ 전송: {item['job']['title'][:30]}...")
            sent += 1
            time.sleep(2)
    
    # 요약 알림
    summary = f"""
📊 <b>검색 완료!</b> - {datetime.now().strftime('%H:%M')}

📥 수집: {len(all_jobs)}개
🆕 새 공고: {len(new_jobs)}개
🧠 분석: {analyzed}개
✅ 쉬운 작업: {len(easy_jobs)}개
📤 알림: {sent}개

{'━'*20}
💡 <b>작업 순서:</b>
1. 공고 확인
2. Claude 프롬프트 복붙
3. 결과물 받기
4. 클라이언트에게 전달
5. 💰 돈 받기!

⏰ 다음 검색: 4시간 후
"""
    send_telegram(summary)
    
    print(f"\n{'='*50}")
    print(f"✅ 완료! 쉬운 작업 {len(easy_jobs)}개 발견, {sent}개 알림")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()

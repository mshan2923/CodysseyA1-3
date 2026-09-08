# TripCanvas

날짜와 여행 스타일만 입력하면 AI가 국내 여행지를 추천하고 일정을 만든 뒤 실제 장소를 지도에 표시하는 바닐라 HTML/CSS/JavaScript 웹 서비스입니다.

## 구조
```text
tripcanvas/
├── index.html
├── css/style.css
├── js/app.js
├── api/plan.py
├── PLAN.md
├── README.md
├── requirements.txt
└── .env.example
```

## 기술
- Frontend: HTML / CSS / JavaScript
- Backend: Vercel Python Serverless Function
- AI: Codyssey Chat Completions API (`gpt-5-mini`)
- 장소: Kakao Local REST API
- 지도: Kakao Maps JavaScript SDK
- 경로: Kakao Mobility Directions API

## 키 설정
로컬에서는 `.env`에 `CODYSSEY_API_KEY`, `KAKAO_REST_API_KEY`를 설정합니다. Vercel에서는 Project Settings > Environment Variables에 등록합니다. `.env`는 GitHub에 올리지 않습니다.

`index.html`의 `KAKAO_JAVASCRIPT_KEY`는 Kakao의 **JavaScript 플랫폼 키**로 교체하고 Web 도메인 제한을 설정합니다. REST API 키와는 다른 키입니다.

## 실행
Vercel Python Function을 포함하므로 일반 `python -m http.server`만으로는 `/api/plan`이 실행되지 않습니다.
```bash
pip install -r requirements.txt
npm i -g vercel
vercel dev
```

## 배포
GitHub에 push → Vercel에서 Import → 환경 변수 설정 → Deploy. 배포 URL에서 네비게이션, 모바일, AI 일정, 지도 표시를 확인합니다.

## AI 흐름
```text
Browser
  -> POST /api/plan
  -> Vercel Python
  -> Codyssey: 여행지 + 일정 JSON
  -> Kakao Local: 장소명 -> 좌표
  -> Kakao Mobility: 경로 요약(가능한 경우)
  -> Browser: 일정 카드 + Kakao Maps
```

## 테스트
- 정상 날짜 + 스타일 → 일정 생성
- 날짜 누락 → 입력 오류
- 8일 이상 → 기간 오류
- 외부 API 실패/지연 → 사용자 오류 메시지

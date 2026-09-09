# TripCanvas

날짜와 여행 스타일만 입력하면 AI가 국내 여행지 한 곳을 추천하고, 날짜별 일정을 만들어 실제 장소 좌표로 확인한 뒤 지도 위에 시각화하는 AI 여행 플래너입니다.

## 1. 서비스 소개

- **서비스명**: TripCanvas
- **타겟 사용자**: 여행 계획에 시간을 많이 쓰고 싶지 않고, 텍스트보다 지도와 일정이 함께 보이는 결과를 선호하는 사용자
- **목적**: 시작일/종료일과 원하는 여행 스타일만 입력하면, AI가 국내 여행지 한 곳과 날짜별 방문 순서를 구성하고, 실제로 존재하는 장소인지 확인해 지도 위에 동선까지 그려준다.

### 페이지/섹션 구성
메인 페이지 하나에 스크롤/앵커 이동으로 구성된 4개 섹션(메뉴 이동 가능):
- **홈** — 서비스 소개, 시작하기 CTA
- **여행 만들기** — 날짜·스타일 입력 폼 (AI 기능 UI)
- **여행 지도** — AI가 만든 일정 + 실시간 지도 시각화 (AI 기능 결과)
- **만드는 방법** — 4단계 프로세스 설명

### AI 기능 설계
- **입력**: 여행 시작일/종료일(필수), 여행 스타일 다중 선택(선택), 자유 텍스트 추가 요청(선택, 최대 300자)
- **처리**: LLM이 여행지 1곳과 날짜별 방문 장소(장소명/카테고리/시간/추천 이유)를 JSON으로 생성 → 각 장소를 Kakao Local API로 검색해 실존 여부와 좌표를 확인 → Kakao Mobility로 하루 동선의 이동 거리/시간을 계산
- **출력**: 여행지 추천 이유, 날짜별 장소 카드(주소·시간·추천 이유·카카오맵 링크), 지도 위 마커와 이동 경로선
- **실패 처리**:
  - 빈 날짜 입력 → "여행 시작일과 종료일을 선택해주세요."
  - 여행 기간 1~7일 범위 초과 → "여행 기간은 1~7일로 설정해주세요."
  - AI/외부 API 오류(4xx/5xx) → "여행 계획을 만들지 못했습니다." 등 원인별 메시지
  - 응답 지연/타임아웃 → "외부 API 응답이 늦습니다. 잠시 후 다시 시도해주세요."
  - AI가 만든 장소를 실제 위치로 확인하지 못한 경우 → 목록에 "⚠ 실제 장소 확인 실패" 표시, 지도에는 표시하지 않음 (유효 좌표 0개면 지도 위에 별도 안내 배너 표시)

## 2. 기술 스택

| 영역 | 사용 기술 |
|---|---|
| 프론트엔드 | HTML / CSS / Vanilla JavaScript (프레임워크 미사용) |
| 지도 시각화 | Kakao Maps JavaScript SDK |
| 백엔드 | Python (`http.server` 기반, Vercel Serverless Functions 배포 대상) |
| AI 일정 생성 | OpenAI 호환 Chat Completions API (Codyssey 프록시 또는 로컬 Ollama) |
| 장소 검증 | Kakao Local API (키워드 검색) |
| 경로 계산 | Kakao Mobility Directions API |

## 3. 프로젝트 구조

```
tripcanvas/
├─ api/
│  └─ plan.py        # AI 일정 생성 + 장소 검증 + 경로 계산 (Vercel Serverless Function)
├─ public/
│  ├─ index.html
│  ├─ css/style.css
│  └─ js/app.js      # 폼 처리, 지도 렌더링(Kakao Maps)
├─ server.py          # 로컬 개발 전용: 정적 파일 서빙 + /api/plan 라우팅 (api/plan.py 재사용)
├─ requirements.txt
├─ vercel.json        # 정적 출력 디렉터리를 public/으로 지정
├─ .gitignore         # .env 등 민감 파일 커밋 방지
└─ README.md
```

`api/plan.py`는 `http.server.BaseHTTPRequestHandler`를 상속한 `handler` 클래스 형태로 작성되어 있어, Vercel Python 런타임이 파일 경로(`api/plan.py` → `/api/plan`)만으로 자동으로 서버리스 함수로 인식합니다. 별도 프레임워크 코드 변환 없이 로컬(`server.py`)과 Vercel 배포 양쪽에서 동일한 파일을 그대로 씁니다.

## 4. 실행 방법 (로컬)

### 준비물
- Python 3.9+
- `pip install requests`

### 환경 변수 설정
프로젝트 루트에 `.env` 파일을 만들고 아래 값을 채운다 (`server.py`가 실행 시 자동으로 읽어 환경 변수로 등록):

```
CODYSSEY_API_KEY=발급받은_codyssey_키          # 원격 AI API 사용 시
KAKAO_REST_API_KEY=발급받은_카카오_REST_키      # Kakao Local / Mobility 호출용
AI_URL=http://localhost:11434/v1/chat/completions  # 선택, 기본값: 로컬 Ollama
AI_MODEL=llama3.1                                  # 선택, 기본값: llama3.1
```

- `CODYSSEY_API_KEY`가 없으면 인증 헤더 없이 `AI_URL`로 요청합니다 (로컬 Ollama처럼 키가 필요 없는 경우).
- `AI_URL` / `AI_MODEL`을 지정하지 않으면 로컬 Ollama(`http://localhost:11434`)를 기본으로 사용합니다.
- **API 키는 절대 코드/README/스크린샷에 노출하지 않으며, 반드시 `.env`(gitignore 처리)로만 관리합니다.**

### 실행
```
python server.py
```
브라우저에서 `http://localhost:8000` 접속.

### Kakao Maps 지도가 안 보일 때
Kakao Developers 콘솔 → 앱 설정 → **플랫폼 → Web 사이트 도메인**에 접속 주소(`http://localhost:8000` 등)를 정확히 등록해야 지도 타일이 표시됩니다.

## 5. 배포 (Vercel)

1. GitHub 저장소에 코드 푸시 (`.env`는 `.gitignore`에 포함되어 있어 커밋되지 않음)
2. Vercel에서 저장소 연동 → Import (프레임워크 프리셋: **Other**)
3. Vercel 프로젝트 설정 → **Environment Variables**에 `.env`와 동일한 키/값 등록 (`CODYSSEY_API_KEY`, `KAKAO_REST_API_KEY`, 필요 시 `AI_URL`, `AI_MODEL`)
4. `requirements.txt`(`requests`)는 그대로 두면 Vercel이 빌드 시 자동 설치
5. 배포되면 `api/plan.py`가 자동으로 `/api/plan` 엔드포인트가 되고, `public/` 아래 정적 파일이 사이트 루트로 서빙됨 (`vercel.json`의 `outputDirectory` 설정)
6. 배포 후 URL에서 네비게이션 이동 / 반응형 / AI 기능(일정 생성 → 지도 표시)이 정상 동작하는지 확인
7. Kakao Developers 콘솔 → 플랫폼 → Web 사이트 도메인에 **배포된 Vercel URL**도 추가 등록 (안 하면 지도 타일이 안 뜸)

**배포 URL**: _(배포 후 여기에 기입)_

## 6. 제약 사항 준수

- API 키는 환경 변수로만 관리하며 저장소·문서·스크린샷에 노출하지 않는다.
- AI/외부 API는 과금·쿼터가 발생할 수 있으므로 호출 실패 시 사용자에게 안내 메시지를 표시하고 재시도를 유도한다.
- 키 유출이 의심되는 경우 즉시 폐기·재발급하고, 노출된 커밋 이력을 정리한다.

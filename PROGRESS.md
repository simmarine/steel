# Steel 프로젝트 리팩토링 진행 현황

> 최종 업데이트: 2026-04-16  
> 작업 목적: 프로토타입 → 포트폴리오 수준으로 리팩토링

---

## 전체 작업 현황

| # | 작업 | 상태 |
|---|------|------|
| 1 | 자격증명 처리 (보안) | ✅ 완료 |
| 2 | DB 설계 및 데이터 적재 | 🔄 진행 중 |
| 3 | 웹페이지 재구성 | ⬜ 미착수 |
| 4 | 크롤링 리팩토링 | ⬜ 미착수 |
| 5 | 백엔드 DB 연동 | ⬜ 미착수 |
| 6 | 모델 재개발 | ⬜ 미착수 |

---

## ✅ 1. 자격증명 처리 (완료)

### 문제
- 소스 코드에 아이디/비밀번호가 하드코딩되어 GitHub 업로드 시 유출 위험
- 서버 IP(`203.253.181.161`)도 소스 코드 곳곳에 직접 기재

### 처리 내용

#### 생성된 파일
| 파일 | 내용 |
|------|------|
| `flask/.env` | steelprice / steeldaily / steelin 자격증명 + 서버 설정 |
| `flask/.env.example` | 빈 값 템플릿 (커밋용) |
| `node/.env` | MySQL 자격증명 + 서버 IP + Flask API URL |
| `node/.env.example` | 빈 값 템플릿 (커밋용) |

#### 수정된 파일
| 파일 | 처리 내용 |
|------|-----------|
| `flask/crawl.py` | `kisco2` / `Kisco4528` → `STEEL_PRICE_ID` / `STEEL_PRICE_PW` (8곳) |
| `flask/steeldaily_Crawling.py` | `bigdata2024` / `bigdata1!` → `STEELDAILY_ID` / `STEELDAILY_PW` |
| `flask/steelin_ver2.py` | `bigdata2024` / `bigdata1!` → `STEELIN_ID` / `STEELIN_PW` |
| `node/steeldaily_Crawling.py` | 동일 처리 |
| `node/steelin_ver2.py` | 동일 처리 |
| `flask/app_test.py` | `host='203.253.181.161'` → `FLASK_HOST` / `FLASK_PORT` 환경변수 |
| `node/server.js` | MySQL 비밀번호, 서버 IP → 환경변수 / `/js/config.js` 동적 엔드포인트 추가 |
| `node/package.json` | `express`, `mysql2`, `cors`, `dotenv` 의존성 추가 |
| `requirements.txt` | `python-dotenv==1.0.1` 추가 |

#### 프론트엔드 IP 제거
- `node/pubulic/js/demo/index.js`
- `node/pubulic/js/demo/craw.js`
- `node/pubulic/js/demo/dashboard.js`
- `node/pubulic/js/demo/news.js`
- `node/pubulic/js/demo/date.js`
- `node/pubulic/js/demo/test.js`
  - 모든 `http://203.253.181.161:5050` → `${API_CONFIG.FLASK_API}`
  - 모든 `http://203.253.181.161:8080` → `${API_CONFIG.NODE_API}`
- `index.html`, `craw.html`, `test.html`, `tables.html` → `<script src="/js/config.js">` 추가

#### 미처리 항목 (낮은 우선순위)
- `flask/crawl.py` URL 파라미터 내 `nd_id=bigdata2024-79456363` — 로그인 자격증명이 아닌 구독 URL 식별자이므로 보류

---

## 🔄 2. DB 설계 및 데이터 적재 (진행 중)

### 확정된 테이블 구조

```
steel_features_wide   ← RAW 원본 백업 (읽기 전용, 절대 수정 금지)
crawl_data            ← 신규 크롤링 데이터 전용
steel_data_merged     ← RAW + 크롤링 합본 (모델 학습/예측에 사용)
predictions           ← 모델 예측 결과 이력
```

### 생성된 스크립트
| 파일 | 역할 |
|------|------|
| `database/schema.sql` | 기존 보조 테이블 DDL (news_articles, crawl_logs, model_registry 등) |
| `database/create_wide_table.py` | Excel → `steel_features_wide` wide 테이블 생성 |
| `database/setup_tables.py` | `crawl_data`, `steel_data_merged`, `predictions` 테이블 생성 |
| `database/migrate_from_excel.py` | 기존 Excel/CSV → DB 마이그레이션 (보조) |
| `database/column_mapping.csv` | 한글 컬럼명 → DB 컬럼명 대조표 (create_wide_table.py 실행 시 자동 생성) |

### 완료 항목
- [x] MySQL Workbench에서 `steel_db` 데이터베이스 생성
- [x] `schema.sql` 실행 (보조 테이블 생성)
- [x] `create_wide_table.py` 실행 → `steel_features_wide` 생성 (2,663행, 166컬럼)

### 남은 항목
- [ ] `setup_tables.py` 실행 → `crawl_data`, `steel_data_merged`, `predictions` 생성
- [ ] `steel_data_merged` 데이터 정합성 검증 (Workbench에서 SELECT로 확인)
- [ ] `node/.env`의 `MYSQL_DATABASE` 값을 `steel_db`로 수정 (현재 `db`로 되어 있음)

---

## ⬜ 3. 웹페이지 재구성 (미착수)

### 해야 할 작업

#### 3-1. 대외비 정보 제거
- [ ] `index.html` — `Kisco` 텍스트, `kisco_logo.png`, `kisco_steel` footer 제거
- [ ] `craw.html`, `tables.html`, `test.html` — 동일 처리
- [ ] `Copyright &copy; kisco_steel 2024` → 중립적 텍스트로 교체
- [ ] `img/kisco_logo.png` → 새 로고 또는 아이콘으로 교체

#### 3-2. 폴더명 오타 수정
- [ ] `node/pubulic/` → `node/public/` 으로 rename
  - `server.js` 내 경로도 함께 수정

#### 3-3. 페이지 재설계
- [ ] `/` (대시보드) — 예측 결과 차트, 주요 지표 요약
- [ ] `/predict` — 기간별 예측 조회
- [ ] `/data` — 데이터 관리 (크롤링 실행, 현황 테이블)
- [ ] `/model` — 모델 성능 비교 (MAE, RMSE, 방향 정확도)

#### 3-4. 서버 통합 검토 (선택)
- [ ] Flask + Node.js 이중 서버 구조 유지 또는 단일 서버로 통합 여부 결정

---

## ⬜ 4. 크롤링 리팩토링 (미착수)

### 현재 문제
- `crawl.py` 에 비슷한 구조의 함수 38개 (~2,500줄) 중복
- 크롤링 결과를 CSV/Excel 파일로 저장 → DB 직접 저장으로 전환 필요
- 직렬 실행으로 전체 크롤링 수십 분 소요
- 에러 처리 없음 (한 곳 실패 시 전체 중단)

### 해야 할 작업

#### 4-1. 크롤러 추상화
- [ ] `BaseCrawler` 추상 클래스 작성
- [ ] `RequestsCrawler` (JS 불필요 사이트용)
- [ ] `SeleniumCrawler` (로그인/JS 필요 사이트용)
- [ ] 사이트별 설정을 `crawl_config.yaml` 파일로 분리

#### 4-2. 병렬 크롤링
- [ ] `concurrent.futures.ThreadPoolExecutor` 적용 (Selenium)
- [ ] `asyncio` + `aiohttp` 적용 (Requests)

#### 4-3. DB 직접 저장
- [ ] 크롤링 결과 → `crawl_data` 테이블에 INSERT
- [ ] 크롤링 완료 후 `setup_tables.py`의 `rebuild_merged()` 자동 호출

#### 4-4. 뉴스 크롤러 통합
- [ ] `flask/steeldaily_Crawling.py` + `flask/steelin_ver2.py`
      → `crawlers/news_crawler.py` 단일 파일로 통합
- [ ] 뉴스 크롤링 결과 → `news_articles` 테이블에 저장
- [ ] `node/steeldaily_Crawling.py`, `node/steelin_ver2.py` 제거 (중복)

#### 4-5. 안정성 강화
- [ ] 재시도 로직 (최대 3회, Exponential Backoff)
- [ ] 크롤링 시작/종료/실패 → `crawl_logs` 테이블에 기록
- [ ] 수집된 값 범위 검증 (이상치 감지)

---

## ⬜ 5. 백엔드 DB 연동 (미착수)

### 현재 문제
- `app_test.py` 가 매 요청마다 Excel 파일 전체 로드 (병목)
- 예측 결과를 `excel2/` 폴더 xlsx 파일로 저장
- Windows 역슬래시 절대경로 하드코딩 (`r'.\pickle\...'`)

### 해야 할 작업

#### 5-1. Excel I/O → DB 쿼리 전환
- [ ] `data_2024_11.xlsx` 로드 → `steel_data_merged` SELECT 로 교체
- [ ] `data_2024_11_특.xlsx` 로드 → 동일 테이블 `price_special` 컬럼 사용
- [ ] 서버 시작 시 1회 DB에서 데이터 로드 후 메모리 캐싱

#### 5-2. 예측 결과 저장
- [ ] `excel2/*.xlsx` 저장 → `predictions` 테이블 INSERT 로 교체
- [ ] 예측 완료 후 `actual_value` 사후 업데이트 기능 추가

#### 5-3. 경로 처리 개선
- [ ] `r'.\pickle\...'` → `pathlib.Path` 기반 상대경로로 교체
- [ ] 모델/스케일러/레이블 서버 시작 시 1회 로드 (현재도 로드하나 경로 문제)

#### 5-4. node/server.js DB 연동 정리
- [ ] `kisco` 테이블 → `news_articles` 테이블로 쿼리 변경
- [ ] `MYSQL_DATABASE=steel_db` 로 통일

---

## ⬜ 6. 모델 재개발 (미착수)

### 현재 문제
- 수동 보정값 다수 포함된 프로토타입 모델
- XGBoost 단일 모델만 사용
- Walk-Forward Validation 미적용 (시계열 데이터 누수 가능성)
- 점 예측만 제공 (신뢰 구간 없음)
- 모델 버전 관리 없음 (pkl 파일 덮어쓰기)

### 해야 할 작업

#### 6-1. 데이터 파이프라인 정비
- [ ] `steel_data_merged` 기반 학습 데이터 로더 작성
- [ ] Walk-Forward Validation 구현 (미래 데이터 누수 방지)
- [ ] 피처 중요도 분석 후 불필요 피처 제거
- [ ] 결측값/이상치 처리 자동화

#### 6-2. 모델 후보 실험
- [ ] XGBoost (기존 모델, 기준선)
- [ ] LightGBM
- [ ] LSTM / GRU
- [ ] Temporal Fusion Transformer (TFT)
- [ ] 앙상블 (상위 2~3개 모델 결합)

#### 6-3. 예측 불확실성 추가
- [ ] Conformal Prediction 으로 신뢰 구간 제공
- [ ] 방향 정확도 (상승/하락) 별도 메트릭 추적

#### 6-4. 실험 관리
- [ ] MLflow 도입 (하이퍼파라미터, 메트릭, 모델 파일 로깅)
- [ ] `model_registry` 테이블 연동 (학습 완료 시 자동 등록)
- [ ] 신/구 모델 성능 비교 후 배포 여부 결정

---

## 프로젝트 파일 구조 (현재)

```
steel/
├── PROGRESS.md                      ← 이 파일
├── requirements.txt                 ✅ python-dotenv 추가됨
├── database/
│   ├── schema.sql                   ✅ 보조 테이블 DDL
│   ├── create_wide_table.py         ✅ steel_features_wide 생성
│   ├── setup_tables.py              ✅ crawl_data / merged / predictions 생성
│   ├── migrate_from_excel.py        ✅ 보조 마이그레이션 스크립트
│   └── column_mapping.csv           ✅ 한글→DB 컬럼명 대조표 (실행 후 생성)
├── flask/
│   ├── .env                         ✅ 자격증명 (gitignore 적용)
│   ├── .env.example                 ✅ 템플릿
│   ├── app_test.py                  ✅ 서버 호스트 환경변수화 / ⬜ DB 연동 미완
│   ├── crawl.py                     ✅ 자격증명 환경변수화 / ⬜ 리팩토링 미완
│   ├── steeldaily_Crawling.py       ✅ 자격증명 환경변수화
│   ├── steelin_ver2.py              ✅ 자격증명 환경변수화
│   └── predict.py                   ⬜ DB 연동 미완
└── node/
    ├── .env                         ✅ 자격증명 (gitignore 적용)
    ├── .env.example                 ✅ 템플릿
    ├── package.json                 ✅ express/mysql2/cors/dotenv 추가
    ├── server.js                    ✅ 환경변수화 + config.js 동적 제공
    ├── steeldaily_Crawling.py       ✅ 자격증명 환경변수화
    ├── steelin_ver2.py              ✅ 자격증명 환경변수화
    └── pubulic/                     ⬜ 폴더명 오타 (pubulic → public)
        ├── index.html               ✅ config.js 추가 / ⬜ 브랜딩 미교체
        ├── craw.html                ✅ config.js 추가 / ⬜ 브랜딩 미교체
        ├── tables.html              ✅ config.js 추가 / ⬜ 브랜딩 미교체
        ├── test.html                ✅ config.js 추가 / ⬜ 브랜딩 미교체
        └── js/demo/
            ├── index.js             ✅ API_CONFIG 적용
            ├── craw.js              ✅ API_CONFIG 적용
            ├── dashboard.js         ✅ API_CONFIG 적용
            ├── news.js              ✅ API_CONFIG 적용
            ├── date.js              ✅ API_CONFIG 적용
            └── test.js              ✅ API_CONFIG 적용
```

---

## 다음 작업 추천 순서

```
[현재 위치]
2단계 DB 작업 마무리
    └─ setup_tables.py 실행
    └─ node/.env MYSQL_DATABASE=steel_db 확인

        ↓

3단계 웹페이지 재구성
    └─ Kisco 브랜딩 제거 (index.html 등)
    └─ pubulic → public 폴더명 수정

        ↓

4단계 크롤링 리팩토링
    └─ BaseCrawler 추상화
    └─ crawl_data 테이블 직접 저장

        ↓

5단계 백엔드 DB 연동
    └─ app_test.py Excel I/O → DB 쿼리

        ↓

6단계 모델 재개발
```

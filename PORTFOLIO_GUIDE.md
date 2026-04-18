# SteelAI — 포트폴리오 가이드
> 철강 시장 가격 예측 AI 시스템  
> 작성일: 2026-04-18

---

## 1. 프로젝트 한 줄 요약

국내 철강 유통 현물 단가를 대상으로 **다중 외부 데이터를 자동 수집·가공**하여  
**10일 / 30일 / 60일** 후의 가격 방향(상승/하락)과 실제 예측 단가를 제공하는  
AI 기반 의사결정 지원 시스템.

---

## 2. 기술 스택

### 2-1. 백엔드
| 범주 | 기술 | 용도 |
|------|------|------|
| API 서버 | **Python Flask** | ML 예측 API, 크롤링 트리거 |
| 웹 서버 | **Node.js + Express** | 정적 파일 서빙, DB 조회 API |
| 데이터베이스 | **MySQL** | 시계열 가격·피처 데이터 저장 |
| ORM / 쿼리 | **SQLAlchemy** | Python ↔ MySQL 연결 |
| DB 드라이버 | **mysql-connector-python**, **mysql2(Node)** | |

### 2-2. 머신러닝
| 범주 | 기술 | 용도 |
|------|------|------|
| 앙상블 트리 | **XGBoost** | 10일 방향 분류, 가격 회귀 |
| 앙상블 트리 | **LightGBM** | 60일 앙상블 구성원 |
| 선형 모델 | **Logistic Regression** | 30일 / 60일 앙상블 구성원 |
| 가격 회귀 | **Ridge, Random Forest** | 10~60일 가격 수준 예측 |
| 전처리 | **StandardScaler** | LogReg 입력 정규화 |
| 피처 중요도 | **RandomForest feature_importances_, XGBoost gain** | 피처 선택 |
| 검증 | **TimeSeriesSplit (Walk-Forward)** | 시계열 누수 없는 교차 검증 |
| 라이브러리 | **scikit-learn, xgboost, lightgbm, joblib** | |

### 2-3. 데이터 수집 (크롤링)
| 소스 | 방법 | 데이터 종류 |
|------|------|------------|
| steelprice.co.kr | **Selenium** 로그인 자동화 | 국내 철강 현물 가격 |
| steeldaily.co.kr | **Selenium** | 해외 철강 시황 |
| steelin.co.kr | **Selenium** | 국내 유통 가격 |
| ECOS (한국은행) | **REST API** | 금리, 환율, 통화량 등 거시경제 |
| KOSIS (통계청) | **REST API** | 건설수주, 생산지수, 설비가동률 |
| Requests + BeautifulSoup | HTML 파싱 | 선박운임(BDI), 원자재 가격 |

### 2-4. 프론트엔드
| 기술 | 용도 |
|------|------|
| **HTML / CSS / JavaScript** | 단일 페이지 대시보드 |
| **Bootstrap 4 (SB Admin 2)** | UI 컴포넌트 프레임워크 |
| **Chart.js** | 예측 결과 시각화 (라인·바 차트) |
| **jQuery + AJAX** | Flask API 비동기 호출 |

### 2-5. 분석 환경
| 기술 | 용도 |
|------|------|
| **Jupyter Notebook** | EDA, 피처 엔지니어링 실험 |
| **pandas, numpy** | 데이터 전처리, 시계열 조작 |
| **matplotlib, seaborn** | 시각화 |
| **statsmodels** | STL 분해, ACF/PACF 분석 |

### 2-6. DevOps / 인프라
| 기술 | 용도 |
|------|------|
| **dotenv (.env)** | 환경변수 관리 |
| **Git / GitHub** | 버전 관리 |
| **webdriver-manager** | Chrome Driver 자동 관리 |

---

## 3. 시스템 아키텍처

```
[외부 데이터 소스]
  ├─ steelprice.co.kr (Selenium)
  ├─ ECOS API (한국은행)
  ├─ KOSIS API (통계청)
  └─ 기타 (Requests/BS4)
         │
         ▼
[Flask 서버 :5050]
  ├─ /crawl/start  → 크롤링 실행
  ├─ /predict/all  → 가격 수준 예측 (회귀)
  └─ /predict/binary → 방향 예측 (분류)
         │
         ▼
[MySQL DB: steel_db]
  ├─ steel_prices        (가격 시계열)
  ├─ steel_features      (외부 피처 long format)
  ├─ binary_predictions  (방향 예측 결과)
  └─ crawl_logs          (크롤링 이력)
         │
         ▼
[Node.js 서버 :8080]
  ├─ /api/price      → 가격 데이터 조회
  ├─ /api/news       → 뉴스 조회
  └─ 정적 파일 서빙 (HTML/CSS/JS)
         │
         ▼
[프론트엔드 대시보드]
  ├─ index.html     (대시보드: 최신 가격 + 예측 카드)
  ├─ test.html      (AI 예측 성능 분석)
  ├─ tables.html    (철강 뉴스)
  └─ craw.html      (데이터 수집 관리)
```

---

## 4. ML 모델 상세 — 이진 분류 (방향 예측)

### 4-1. 문제 정의
- **입력**: 현재까지의 철강 가격 + 외부 경제 지표 (80여 개 피처)
- **출력**: N일 후 가격 방향 (1=상승, 0=하락)
- **기간**: 10일 / 30일 / 60일 3가지

### 4-2. 피처 구성 (총 111개)
```
avail (79개)   : 실제 수집 가능한 외부 경제 지표
lag (6개)      : 1/3/5/10/20/30일 전 가격 (데이터 누수 방지)
rolling (8개)  : 이동 평균/표준편차 (5/10/20/30일)
directional (18개) : 수익률, 모멘텀, MA 크로스, 상승 비율, 가속도
```

### 4-3. 데이터 누수(Leakage) 방지 전략
- 모든 lag/rolling 피처는 `.shift(1)` 적용 → 당일 가격 미사용
- 라벨 생성: `future = df[TARGET].shift(-h)` → h일 후 가격
- 검증: `TimeSeriesSplit` → 미래 데이터가 학습에 포함되지 않도록

### 4-4. 모델 선택 근거 (Walk-Forward 검증 결과)
| 기간 | 선택 모델 | AUC | Accuracy |
|------|-----------|-----|----------|
| 10일 | XGBoost | 0.859 | 76.9% |
| 30일 | LogisticRegression | 0.728 | 64.3% |
| 60일 | Ensemble (LR+XGB+LGB) | 0.741 | 53.4% |

- **10일**: 단기 패턴 포착에 트리 기반 모델이 우수
- **30일**: 중기는 선형 모델이 과적합 없이 안정적
- **60일**: 장기는 모델 다양성으로 편향-분산 균형

### 4-5. 피처 선택 방법
1. RandomForest + XGBoost gain으로 **ensemble_score** 계산
2. 83개 후보 피처 → DB에 없는 피처 자동 제외
3. 결측률 ≥ 80% 피처 자동 제외
4. 최종 79개 avail 피처 확정

---

## 5. ML 모델 상세 — 가격 수준 예측 (회귀)

### 5-1. 문제 정의
- **출력**: N일 후 구체적인 단가 (원/ton)
- **모델**: XGBoost Regressor (MAPE 기준 최적)

### 5-2. 검증 결과 (Walk-Forward)
| 기간 | RMSE | MAE | MAPE |
|------|------|-----|------|
| 10일 | 59.9 | 47.9 | 10.75% |
| 20일 | 70.x | 54.x | ~13% |
| 30일 | 129.6 | 108.5 | 24.14% |

---

## 6. 데이터 파이프라인

### 6-1. 크롤링 구조
```
flask/crawlers/
├── base.py        # DB 엔진, retry 데코레이터, 환경변수 로드
├── ecos.py        # 한국은행 ECOS API 통합 수집
├── kosis.py       # 통계청 KOSIS API 통합 수집
├── steelprice.py  # Selenium 가격 크롤러
├── steeldaily.py  # Selenium 해외 시황 크롤러
└── misc.py        # 원자재(BDI, WTI 등) 수집
```

### 6-2. Retry 전략
```python
@retry(max_tries=3, wait_base=2)  # Exponential Backoff
def crawl_feature():
    ...
```

### 6-3. DB 저장 구조
- **steel_prices**: wide format (날짜 × 가격 칼럼)
- **steel_features**: long format (date, feature_name, value)
  - long format → 피처 추가 시 스키마 변경 불필요

---

## 7. 주요 기술적 의사결정 및 근거

### Q. 왜 long format으로 피처를 저장했나?
피처 종류가 계속 추가/변경될 수 있어 wide format은 스키마 마이그레이션이 필요하다.  
long format은 `(date, feature_name, value)` 3컬럼으로 어떤 피처도 추가 가능.  
예측 시 `pivot`으로 wide로 변환해 모델에 입력.

### Q. Walk-Forward Validation이란?
일반 K-Fold는 미래 데이터를 학습에 포함하는 **시간 누수(leakage)** 문제가 발생한다.  
Walk-Forward는 항상 과거 → 미래 방향으로만 분할하여 실제 운용 시나리오를 시뮬레이션.  
`TimeSeriesSplit(n_splits=5)` 사용 → 전체 기간을 5구간으로 확장하며 검증.

### Q. 왜 60일은 앙상블인가?
장기 예측일수록 단일 모델의 편향이 커진다.  
LogReg(선형), XGBoost(비선형), LightGBM(비선형) 세 모델의 예측 확률을 평균내면  
각 모델의 과적합이 상쇄되어 AUC가 단독 모델보다 높아진다.

### Q. 피처 중요도로 피처를 줄였을 때 왜 성능이 떨어졌나?
XGBoost 같은 트리 기반 모델은 **낮은 중요도 피처도 상호작용(interaction)에 기여**한다.  
임계값 기준 필터링으로 79개 → 35개로 줄이자 10일 모델 AUC가 0.859 → 0.663으로 하락.  
결론: 피처 수가 적절하면 트리 기반 모델은 자체적으로 중요하지 않은 피처를 무시하므로,  
강제 제거보다 전체 피처를 유지하는 것이 유리.

### Q. 왜 LogReg에는 StandardScaler를 적용하고 XGBoost에는 안 하나?
LogReg는 경사 하강법 기반이라 피처 스케일에 민감 (큰 값 피처가 학습을 지배).  
XGBoost는 분기점(threshold) 기반이라 스케일 불변성(scale-invariant) — 정규화 불필요.

### Q. Selenium을 사용하는 이유?
steelprice.co.kr 등 대상 사이트들이 JavaScript 렌더링 + 로그인 인증이 필요.  
정적 크롤러(requests)로는 로그인 세션 유지가 어려워 브라우저 자동화 선택.

### Q. Flask와 Node.js를 분리한 이유?
- **Flask**: Python ML 생태계(scikit-learn, xgboost)와의 통합이 필수
- **Node.js**: 프론트엔드 정적 파일 서빙 + MySQL 직접 조회에 적합  
두 서버를 분리하면 ML 작업 부하가 프론트엔드 응답에 영향을 주지 않음.

---

## 8. 데이터베이스 스키마 핵심

```sql
-- 철강 가격 시계열
CREATE TABLE steel_prices (
    date DATE PRIMARY KEY,
    price_standard   DECIMAL(10,2),  -- 중A (시장 단가)
    price_special    DECIMAL(10,2),  -- 특별구매 단가
    region_central   DECIMAL(10,2),
    region_south     DECIMAL(10,2),
    ...
);

-- 외부 경제 피처 (long format)
CREATE TABLE steel_features (
    date         DATE,
    feature_name VARCHAR(100),
    value        DECIMAL(15,4),
    PRIMARY KEY (date, feature_name)
);

-- 이진 분류 예측 결과
CREATE TABLE binary_predictions (
    base_date    DATE,
    horizon      INT,             -- 10/30/60
    direction    VARCHAR(4),      -- UP/DOWN
    probability  DECIMAL(8,6),
    model_name   VARCHAR(20),
    PRIMARY KEY (base_date, horizon)
);
```

---

## 9. 폴더 구조

```
steel/
├── analysis/           # 분석 스크립트 & Jupyter Notebooks
│   ├── 01~08_*.ipynb   # EDA → 피처선택 → 모델 비교 → 이진분류
│   ├── model_train_binary.py   # 최종 모델 학습 스크립트
│   ├── validate_binary.py      # Walk-Forward 성능 검증
│   └── utils.py                # 공통 load_data()
│
├── flask/              # Flask API 서버
│   ├── app_test.py     # Flask 메인 앱
│   ├── predict.py      # 가격 수준 예측 (회귀)
│   ├── predict_binary.py  # 방향 예측 (분류)
│   ├── crawl.py        # 크롤링 함수 모음 (레거시)
│   └── crawlers/       # 리팩토링된 크롤러 모듈
│       ├── base.py     # DB 엔진, retry, 자격증명
│       ├── ecos.py     # ECOS API
│       ├── kosis.py    # KOSIS API
│       ├── steelprice.py
│       ├── steeldaily.py
│       └── misc.py
│
├── node/               # Node.js 프론트엔드 서버
│   ├── server.js       # Express 서버
│   └── pubulic/        # 정적 파일
│       ├── index.html  # 메인 대시보드
│       ├── test.html   # AI 성능 분석
│       ├── tables.html # 뉴스
│       └── craw.html   # 데이터 관리
│
├── database/           # DB 초기화 스크립트
│   ├── schema.sql
│   └── setup_tables.py
│
└── requirements.txt    # Python 의존성
```

---

## 10. 성능 요약 (포트폴리오 강조 포인트)

| 모델 유형 | 기간 | 핵심 지표 | 수치 |
|-----------|------|-----------|------|
| 방향 분류 | 10일 | AUC | **0.859** |
| 방향 분류 | 10일 | Accuracy | **76.9%** |
| 방향 분류 | 30일 | AUC | 0.728 |
| 방향 분류 | 60일 | AUC (Ensemble) | 0.741 |
| 가격 예측 | 10일 | MAPE | **10.75%** |
| 가격 예측 | 30일 | MAPE | 24.14% |

> Walk-Forward Validation (TimeSeriesSplit n=5) 기준, 데이터 누수 없는 실운용 시뮬레이션

---

## 11. 면접 예상 Q&A

**Q. AUC가 무엇인가요?**  
ROC 곡선의 면적(Area Under Curve). 0.5=랜덤 예측, 1.0=완벽한 분류.  
임계값에 무관하게 모델의 분류 능력 자체를 평가하는 지표.  
AUC=0.859란 랜덤으로 상승·하락 샘플을 뽑았을 때 85.9% 확률로 상승 샘플의 확률이 더 높다는 의미.

**Q. F1 Score란?**  
Precision(예측한 양성 중 실제 양성 비율)과 Recall(실제 양성 중 예측 양성 비율)의 조화평균.  
상승/하락 클래스 불균형 상황에서 Accuracy만으로는 성능을 과대평가할 수 있어 F1 보완 사용.

**Q. 데이터 누수(Data Leakage)란?**  
학습 시 미래 정보가 사용되어 실제보다 높은 성능이 나오는 현상.  
예: 평가 세트의 평균으로 전체 데이터 정규화 시 발생.  
본 프로젝트에서는 모든 피처를 `.shift(1)` 처리 + TimeSeriesSplit으로 방지.

**Q. 왜 결측값을 `.interpolate(method='time')`으로 처리했나?**  
월별 발표 지표(건설수주, 생산지수 등)는 일별 시계열에서 중간이 NaN.  
선형 보간이 아닌 time 인덱스 기반 보간 → 날짜 간격 불균일(주말 제외)에도 정확한 보간.

**Q. Exponential Backoff란?**  
크롤링 실패 시 재시도 대기 시간을 지수적으로 늘리는 전략 (1초 → 2초 → 4초).  
서버 과부하나 일시적 오류에 효과적. `time.sleep(wait_base ** attempt)` 구현.

**Q. 피처 엔지니어링에서 rolling std를 사용한 이유?**  
가격 변동성(volatility)이 방향 예측에 중요한 신호. 변동성이 높을 때 추세 전환 가능성 증가.  
`roll_std_Nd` = 지난 N일간 가격의 표준편차 → 현재 시장 불확실성 척도.

**Q. 앙상블 평균 확률 방식의 장점?**  
각 모델이 서로 다른 패턴을 학습하므로, 단순 다수결보다 확률 평균이 불확실성을 더 잘 표현.  
특히 soft voting은 확신도(높은 확률)가 있는 모델에 자동으로 가중치가 쏠리는 효과.

# 철강 단가 예측 — 데이터 분석

## 실행 순서

```
01_data_overview.ipynb      → 데이터 구조·기간·피처 카테고리
02_missing_outlier.ipynb    → 결측치 패턴·이상치·시장 충격 구간
03_distribution.ipynb       → 분포·정상성·계절성·ACF/PACF
04_correlation.ipynb        → 피처-타겟 상관관계·Lag 분석·VIF
05_feature_selection.ipynb  → MI + XGBoost + LASSO 앙상블 피처 선택
```

## 사전 설치

```bash
pip install pandas numpy matplotlib seaborn scipy statsmodels xgboost scikit-learn openpyxl sqlalchemy mysql-connector-python python-dotenv
```

## 실행

```bash
cd steel/analysis
jupyter notebook
```

## 데이터 소스

- `steel_prices` 테이블: 일별 단가·물동량 (DB)
- `steel_features` 테이블: 크롤링 피처 시계열 EAV (DB)

## 결과물

- `outputs/*.png` : 각 단계 시각화 파일
- `outputs/final_features.csv` : 05번에서 선택된 최종 피처 목록

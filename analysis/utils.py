"""
analysis/utils.py
데이터 분석 공통 유틸리티 — DB에서 데이터 로드

사용법:
    from utils import load_data, load_prices, load_features

경로: steel/analysis/ 기준으로 실행
"""
import sys
from pathlib import Path

import pandas as pd
import numpy as np

# ── flask/ 모듈 경로 등록 ─────────────────────────────────────
_ANALYSIS_DIR = Path(__file__).parent
_FLASK_DIR    = _ANALYSIS_DIR.parent / 'flask'
if str(_FLASK_DIR) not in sys.path:
    sys.path.insert(0, str(_FLASK_DIR))

# ── DB 엔진 (lazy: 첫 사용 시 생성) ──────────────────────────
_engine = None

def _get_engine():
    global _engine
    if _engine is None:
        from crawlers.base import get_engine
        _engine = get_engine()
    return _engine


# ── 기본 로더 ─────────────────────────────────────────────────

def load_prices() -> pd.DataFrame:
    """steel_prices → 날짜·단가·물동량 DataFrame"""
    df = pd.read_sql("""
        SELECT
            date             AS 일자,
            price_standard   AS 중A,
            price_special    AS `중A_특`,
            volume_incoming  AS 입고량,
            volume_stock     AS 재고량,
            volume_rate      AS 입고율,
            steel_production AS 제강생산량,
            scrap_input      AS 고철투입량,
            region_central   AS 중부권,
            region_south     AS 남부권,
            region_total     AS 총계
        FROM steel_prices
        ORDER BY date
    """, _get_engine())
    df['일자'] = pd.to_datetime(df['일자'])
    return df


def load_features() -> pd.DataFrame:
    """steel_features (EAV) → wide format DataFrame"""
    df = pd.read_sql(
        "SELECT date AS 일자, feature_name, value FROM steel_features ORDER BY date",
        _get_engine(),
    )
    if df.empty:
        return pd.DataFrame()
    df['일자'] = pd.to_datetime(df['일자'])
    wide = df.pivot(index='일자', columns='feature_name', values='value').reset_index()
    wide.columns.name = None
    return wide


def load_data() -> pd.DataFrame:
    """steel_prices + steel_features 통합 wide DataFrame"""
    prices   = load_prices()
    features = load_features()
    if features.empty:
        return prices
    merged = pd.merge(prices, features, on='일자', how='left')
    return merged.sort_values('일자').reset_index(drop=True)


# ── 피처 그룹 분류 ────────────────────────────────────────────

FEATURE_GROUPS = {
    '타겟':       ['중A', '중A_특'],
    '내부물동량': ['입고량', '재고량', '입고율', '제강생산량', '고철투입량', '중부권', '남부권', '총계'],
    '고철가격':   ['일본H2', '일본HMS', '미국HMS', '한국H2', '일본', '미국', '터키', '러시아', 'H2', '수입가'],
    '원자재':     ['철광석', '원료탄'],
    '에너지':     ['Dubai', 'Brent', 'WTI', '두바이', '유가'],
    '거시경제':   ['환율', '달러', '통화', 'M1', 'M2', '물가지수', 'PPI', 'CPI'],
    '경기지표':   ['선행', '동행', '후행', 'BSI', 'CBSI', '뉴스심리', 'NSI', '심리지수'],
    '건설수요':   ['건설수주', '건설기성', '착공', '수주'],
    '철강생산':   ['조강', '전로', '전기로', '철근', '형강', '강판'],
    '해운':       ['BDI', '벌크선', '컨테이너선', '해운'],
    '금속시세':   ['LME', '구리', '아연', '알루미늄', '니켈'],
    '증시':       ['KOSPI', 'KOSDAQ', 'S&P', 'NASDAQ'],
}


def classify_feature(col_name: str) -> str:
    """컬럼명을 받아 속하는 그룹명 반환 (매칭 안되면 '기타')"""
    for group, keywords in FEATURE_GROUPS.items():
        for kw in keywords:
            if kw in col_name:
                return group
    return '기타'


# ── 기술 통계 요약 ────────────────────────────────────────────

def missing_summary(df: pd.DataFrame) -> pd.DataFrame:
    """컬럼별 결측치 현황 요약"""
    total = len(df)
    miss  = df.isnull().sum()
    pct   = (miss / total * 100).round(2)
    return (
        pd.DataFrame({'결측수': miss, '결측률(%)': pct, 'dtype': df.dtypes})
        .query('결측수 > 0')
        .sort_values('결측률(%)', ascending=False)
    )


def outlier_bounds(series: pd.Series, method: str = 'iqr') -> tuple:
    """이상치 경계값 반환 (method: 'iqr' | 'zscore')"""
    s = series.dropna()
    if method == 'iqr':
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        return q1 - 1.5 * iqr, q3 + 1.5 * iqr
    else:  # zscore
        mu, sigma = s.mean(), s.std()
        return mu - 3 * sigma, mu + 3 * sigma


# ── outputs 폴더 보장 ─────────────────────────────────────────

def ensure_outputs() -> Path:
    """outputs/ 폴더 생성 후 Path 반환"""
    out = _ANALYSIS_DIR / 'outputs'
    out.mkdir(exist_ok=True)
    return out

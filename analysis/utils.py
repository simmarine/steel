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
            price_standard,
            price_special,
            volume_incoming,
            volume_stock,
            volume_rate,
            steel_production,
            scrap_input,
            region_central,
            region_south,
            region_total
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

# 피처 그룹 분류 키워드는 대외비로 공개되지 않습니다.
# 모델 학습에 사용된 외부 경제 지표의 상세 항목은 공개 불가능합니다.
FEATURE_GROUPS: dict = {
    'target':           [],
    'internal':         [],
    'raw_material':     [],
    'energy':           [],
    'macro':            [],
    'sentiment':        [],
    'construction':     [],
    'steel_production': [],
    'shipping':         [],
    'metal':            [],
    'equity':           [],
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

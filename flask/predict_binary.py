"""
predict_binary.py
이진 분류 예측 모듈 — 상승(UP) / 하락(DOWN).

모델:
  10일 → XGBoost   (AUC=0.859, Acc=76.9%)
  30일 → LogReg    (AUC=0.728, Acc=48.9%)
  60일 → Ensemble  LogReg+XGBoost+LightGBM (AUC=0.741, Acc=53.4%)

예측 결과는 binary_predictions 테이블에 UPSERT.
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import text

from crawlers.base import get_engine

# ── 경로 ─────────────────────────────────────────────────────
BASE_DIR            = Path(__file__).parent
BINARY_MODELS_DIR   = BASE_DIR / 'binary_models'
BINARY_SCALER_DIR   = BASE_DIR / 'binary_scaler'
BINARY_FEATURES_DIR = BASE_DIR / 'binary_features'

HORIZONS    = [10, 30, 60]
TARGET      = '중A'
MODEL_NAMES = {10: 'XGBoost', 30: 'LogReg', 60: 'Ensemble'}

# ── DB ───────────────────────────────────────────────────────
_engine = get_engine()


# ── 피처 목록 로드 ────────────────────────────────────────────
def _load_features_meta() -> dict:
    path = BINARY_FEATURES_DIR / 'features_list.json'
    if not path.exists():
        raise FileNotFoundError(
            f"피처 목록 없음: {path}\n"
            "analysis/model_train_binary.py 를 먼저 실행하세요."
        )
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


# ── DB 데이터 로드 ────────────────────────────────────────────
def _load_wide_data() -> pd.DataFrame:
    prices = pd.read_sql("""
        SELECT
            date             AS 일자,
            price_standard   AS `중A`,
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
    """, _engine)
    prices['일자'] = pd.to_datetime(prices['일자'])

    features = pd.read_sql(
        "SELECT date AS 일자, feature_name, value FROM steel_features", _engine
    )
    if features.empty:
        return prices
    features['일자'] = pd.to_datetime(features['일자'])
    wide = features.pivot(
        index='일자', columns='feature_name', values='value'
    ).reset_index()
    wide.columns.name = None
    return pd.merge(prices, wide, on='일자', how='left')


# ── 피처 엔지니어링 ───────────────────────────────────────────
def _engineer_features(raw: pd.DataFrame, selected: list) -> tuple[pd.DataFrame, list]:
    """DB 데이터 → 전체 111개 피처 생성 후 (df, all_features) 반환"""
    avail = [c for c in selected if c in raw.columns and c != TARGET]

    df = raw[['일자', TARGET] + avail].copy()
    df = df.set_index('일자').sort_index()
    df = df.interpolate(method='time')
    df = df.dropna(subset=[TARGET])

    # Lag / Rolling
    for lag in [1, 3, 5, 10, 20, 30]:
        df[f'lag_{lag}d'] = df[TARGET].shift(lag)
    for win in [5, 10, 20, 30]:
        df[f'roll_mean_{win}d'] = df[TARGET].shift(1).rolling(win).mean()
        df[f'roll_std_{win}d']  = df[TARGET].shift(1).rolling(win).std()

    # 방향성 피처
    for n in [1, 3, 5, 10, 20]:
        df[f'ret_{n}d'] = df[TARGET].pct_change(n).shift(1) * 100
    for n in [3, 5, 10, 20]:
        df[f'mom_{n}d'] = (df[TARGET] - df[TARGET].shift(n)).shift(1)
    for short, long_ in [(5, 20), (5, 30), (10, 30)]:
        ma_s = df[TARGET].shift(1).rolling(short).mean()
        ma_l = df[TARGET].shift(1).rolling(long_).mean()
        df[f'ma_cross_{short}_{long_}'] = ma_s / ma_l - 1
    for n in [5, 10, 20]:
        daily_up = (df[TARGET].diff().shift(1) > 0).astype(int)
        df[f'up_ratio_{n}d'] = daily_up.rolling(n).mean()
    df['accel_5_20']    = df['ret_5d']  - df['ret_20d']
    df['accel_3_10']    = df['ret_3d']  - df['ret_10d']
    df['vol_ratio_5_20'] = (df[TARGET].shift(1).rolling(5).std() /
                             df[TARGET].shift(1).rolling(20).std())

    lag_roll_cols = (
        [f'lag_{n}d'       for n in [1, 3, 5, 10, 20, 30]] +
        [f'roll_mean_{n}d' for n in [5, 10, 20, 30]] +
        [f'roll_std_{n}d'  for n in [5, 10, 20, 30]]
    )
    dir_cols = (
        [f'ret_{n}d'  for n in [1, 3, 5, 10, 20]] +
        [f'mom_{n}d'  for n in [3, 5, 10, 20]] +
        [f'ma_cross_{s}_{l}' for s, l in [(5, 20), (5, 30), (10, 30)]] +
        [f'up_ratio_{n}d' for n in [5, 10, 20]] +
        ['accel_5_20', 'accel_3_10', 'vol_ratio_5_20']
    )

    all_features = avail + lag_roll_cols + dir_cols
    df.dropna(subset=all_features, inplace=True)

    return df, all_features


# ── DB UPSERT ─────────────────────────────────────────────────
def _upsert_binary_predictions(rows: list):
    if not rows:
        return
    with _engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO binary_predictions
                (base_date, horizon, direction, probability, model_name)
            VALUES
                (:base_date, :horizon, :direction, :probability, :model_name)
            ON DUPLICATE KEY UPDATE
                direction   = VALUES(direction),
                probability = VALUES(probability),
                model_name  = VALUES(model_name),
                updated_at  = CURRENT_TIMESTAMP
        """), rows)
        conn.commit()


# ── 단일 기간 예측 ─────────────────────────────────────────────
def predict_binary(horizon: int) -> dict:
    """
    horizon 일 후 방향 예측.

    Returns:
        {
          'base_date':   'YYYY-MM-DD',  # 예측 기준일 (최신 데이터 날짜)
          'target_date': 'YYYY-MM-DD',  # 예측 목표일
          'horizon':     10,
          'direction':   'UP' | 'DOWN',
          'probability': 0.7234,        # 상승 확률
          'model':       'XGBoost',
        }
    """
    if horizon not in HORIZONS:
        raise ValueError(f"지원하지 않는 horizon: {horizon}. 가능: {HORIZONS}")

    meta = _load_features_meta()
    selected        = meta['selected']
    all_features_ref = meta['all_features']  # 학습 시 111개 피처 (순서 포함)

    raw = _load_wide_data()
    if raw.empty:
        raise ValueError("DB에 데이터 없음")

    df, _ = _engineer_features(raw, selected)
    if df.empty:
        raise ValueError("피처 엔지니어링 후 유효 데이터 없음")

    # 학습 기준 111개 피처 순서로 X 구성 — 없는 컬럼은 0 패딩
    missing = [f for f in all_features_ref if f not in df.columns]
    if missing:
        print(f"[predict_binary h={horizon}] 누락 피처 {len(missing)}개 → 0 패딩: {missing[:5]}")
        for f in missing:
            df[f] = 0.0

    X_last = df[all_features_ref].values[-1:]  # (1, 111)
    base_date = df.index[-1].date()

    # ── 모델별 예측 ───────────────────────────────────────────
    if horizon == 10:
        model = joblib.load(BINARY_MODELS_DIR / 'xgboost_10d.pkl')
        prob  = float(model.predict_proba(X_last)[:, 1][0])

    elif horizon == 30:
        scaler = joblib.load(BINARY_SCALER_DIR / 'scaler_30d.pkl')
        model  = joblib.load(BINARY_MODELS_DIR / 'logreg_30d.pkl')
        prob   = float(model.predict_proba(scaler.transform(X_last))[:, 1][0])

    else:  # 60
        scaler = joblib.load(BINARY_SCALER_DIR / 'scaler_60d.pkl')
        lr     = joblib.load(BINARY_MODELS_DIR / 'ens_logreg_60d.pkl')
        xgb_m  = joblib.load(BINARY_MODELS_DIR / 'ens_xgboost_60d.pkl')
        lgb_m  = joblib.load(BINARY_MODELS_DIR / 'ens_lgbm_60d.pkl')
        prob   = (
            float(lr.predict_proba(scaler.transform(X_last))[:, 1][0]) +
            float(xgb_m.predict_proba(X_last)[:, 1][0]) +
            float(lgb_m.predict_proba(X_last)[:, 1][0])
        ) / 3

    direction = 'UP' if prob >= 0.5 else 'DOWN'
    target_date = pd.to_datetime(base_date) + pd.Timedelta(days=horizon)

    row = {
        'base_date':   base_date,
        'horizon':     horizon,
        'direction':   direction,
        'probability': round(prob, 6),
        'model_name':  MODEL_NAMES[horizon],
    }
    _upsert_binary_predictions([row])

    return {
        'base_date':   str(base_date),
        'target_date': str(target_date.date()),
        'horizon':     horizon,
        'direction':   direction,
        'probability': round(prob, 4),
        'model':       MODEL_NAMES[horizon],
    }


# ── 전체 기간 예측 ─────────────────────────────────────────────
def predict_all_binary() -> list:
    """10일·30일·60일 전부 예측, 결과 리스트 반환."""
    results = []
    for h in HORIZONS:
        try:
            r = predict_binary(h)
            results.append(r)
            arrow = '▲' if r['direction'] == 'UP' else '▼'
            print(f"[{h:2d}일] {arrow} {r['direction']}  확률={r['probability']:.1%}  "
                  f"기준={r['base_date']} → 목표={r['target_date']}")
        except Exception as e:
            print(f"[{h:2d}일] 오류: {e}")
            results.append({'horizon': h, 'error': str(e)})
    return results


if __name__ == '__main__':
    print('이진 분류 예측 실행...')
    for r in predict_all_binary():
        print(r)

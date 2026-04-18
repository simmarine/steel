"""
model_train_binary.py — 원본 피처 복원 + 이진 분류 최종 모델 학습

선택 전략:
  1. final_features.csv 의 전체 피처 목록 사용 (score 임계값 없음)
  2. DB에 컬럼이 존재하고 실제 데이터가 있는 피처만 사용
     - DB에 없는 피처 → 제외
     - DB에 있으나 결측률 >= NULL_THRESHOLD → 데이터 없는 것으로 판단, 제외
     - (예: 특정 컬럼은 있지만 데이터 없으면 자동 제외)
  3. lag/rolling/directional 피처는 항상 포함
  4. 최종 피처로 10/30/60일 모델 재학습

저장 경로:
  ../flask/binary_models/    모델 pkl
  ../flask/binary_scaler/    스케일러 pkl
  ../flask/binary_features/  피처 목록 json
"""

import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import lightgbm as lgb

# ── 경로 설정 ─────────────────────────────────────────────────
_here = Path(__file__).parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

FLASK_DIR           = _here.parent / 'flask'
BINARY_MODELS_DIR   = FLASK_DIR / 'binary_models'
BINARY_SCALER_DIR   = FLASK_DIR / 'binary_scaler'
BINARY_FEATURES_DIR = FLASK_DIR / 'binary_features'

for d in [BINARY_MODELS_DIR, BINARY_SCALER_DIR, BINARY_FEATURES_DIR]:
    d.mkdir(exist_ok=True)

from utils import load_data  # noqa: E402

TARGET       = 'price_standard'
HORIZONS     = [10, 30, 60]
NULL_THRESHOLD = 0.80   # 결측률 이 이상이면 "데이터 없음"으로 판단

# ── 데이터 로드 ───────────────────────────────────────────────
print('=' * 60)
print('  원본 피처 복원 + 이진 분류 모델 재학습')
print('=' * 60)
print('\n데이터 로드...')
df_raw = load_data().sort_values('일자').reset_index(drop=True)
print(f'원본 데이터: {df_raw.shape[0]:,}행 x {df_raw.shape[1]}컬럼')
print(f'기간: {df_raw["일자"].min().date()} ~ {df_raw["일자"].max().date()}')

# ── 피처 선택: final_features.csv 전체 사용 ──────────────────
print('\n피처 선택 (final_features.csv 전체)...')
feat_csv = pd.read_csv(_here / 'outputs/final_features.csv', encoding='utf-8-sig')
all_from_csv = feat_csv['feature'].tolist()  # 83개

avail              = []
excluded_not_in_db = []
excluded_no_data   = []

for f in all_from_csv:
    if f == TARGET:
        continue
    if f not in df_raw.columns:
        excluded_not_in_db.append(f)
        continue
    null_rate = df_raw[f].isna().mean()
    if null_rate >= NULL_THRESHOLD:
        excluded_no_data.append((f, null_rate))
    else:
        avail.append(f)

print(f'  전체 후보: {len(all_from_csv)}개')
if excluded_not_in_db:
    print(f'  DB에 컬럼 없음 ({len(excluded_not_in_db)}개): {excluded_not_in_db}')
if excluded_no_data:
    print(f'  컬럼은 있으나 데이터 없음 ({len(excluded_no_data)}개):')
    for f, nr in excluded_no_data:
        print(f'    - {f}  (결측률 {nr:.1%})')
print(f'  최종 avail: {len(avail)}개')

# ── 피처 엔지니어링 ───────────────────────────────────────────
print('\n피처 엔지니어링...')
df = df_raw[['일자', TARGET] + avail].copy()
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
df['accel_5_20']     = df['ret_5d']  - df['ret_20d']
df['accel_3_10']     = df['ret_3d']  - df['ret_10d']
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

# 이진 라벨 생성
for h in HORIZONS:
    future = df[TARGET].shift(-h)
    df[f'label_{h}d'] = np.where(
        future > df[TARGET], 1,
        np.where(future < df[TARGET], 0, np.nan)
    )

df.dropna(subset=all_features, inplace=True)
print(f'유효 샘플: {len(df):,}행')
print(f'최종 피처: {len(all_features)}개  '
      f'(avail {len(avail)} + lag/roll {len(lag_roll_cols)} + dir {len(dir_cols)})')

# ── 피처 목록 저장 ────────────────────────────────────────────
features_meta = {
    'selected':              avail,
    'avail':                 avail,
    'lag_roll':              lag_roll_cols,
    'directional':           dir_cols,
    'all_features':          all_features,
    'excluded_not_in_db':    excluded_not_in_db,
    'excluded_no_data':      [f for f, _ in excluded_no_data],
}
with open(BINARY_FEATURES_DIR / 'features_list.json', 'w', encoding='utf-8') as f:
    json.dump(features_meta, f, ensure_ascii=False, indent=2)
print(f'피처 목록 저장: binary_features/features_list.json')

# ── 모델 학습 ─────────────────────────────────────────────────
for h in HORIZONS:
    print(f'\n{"─"*60}')
    print(f'[{h}일] 최종 모델 학습...')
    sub = df[all_features + [f'label_{h}d']].dropna()
    X   = sub[all_features].values
    y   = sub[f'label_{h}d'].values.astype(int)
    n_up   = y.sum()
    n_down = (y == 0).sum()
    print(f'  학습 샘플: {len(X):,}행  '
          f'상승: {n_up:,}건({n_up/len(X):.1%})  하락: {n_down:,}건({n_down/len(X):.1%})')

    if h == 10:
        model = xgb.XGBClassifier(
            n_estimators=400, learning_rate=0.05,
            max_depth=4, subsample=0.8, colsample_bytree=0.7,
            random_state=42, verbosity=0, n_jobs=-1, eval_metric='logloss',
        ).fit(X, y)
        joblib.dump(model, BINARY_MODELS_DIR / 'xgboost_10d.pkl')
        print(f'  XGBoost 저장 -> binary_models/xgboost_10d.pkl')

    elif h == 30:
        sc    = StandardScaler().fit(X)
        model = LogisticRegression(
            class_weight='balanced', max_iter=2000, random_state=42, C=0.1,
        ).fit(sc.transform(X), y)
        joblib.dump(sc,    BINARY_SCALER_DIR / 'scaler_30d.pkl')
        joblib.dump(model, BINARY_MODELS_DIR / 'logreg_30d.pkl')
        print(f'  LogReg 저장  -> binary_models/logreg_30d.pkl')
        print(f'  Scaler 저장  -> binary_scaler/scaler_30d.pkl')

    elif h == 60:
        sc    = StandardScaler().fit(X)
        lr    = LogisticRegression(
            class_weight='balanced', max_iter=2000, random_state=42, C=0.1,
        ).fit(sc.transform(X), y)
        xgb_m = xgb.XGBClassifier(
            n_estimators=400, learning_rate=0.05, max_depth=4,
            subsample=0.8, colsample_bytree=0.7,
            random_state=42, verbosity=0, n_jobs=-1, eval_metric='logloss',
        ).fit(X, y)
        lgb_m = lgb.LGBMClassifier(
            n_estimators=400, learning_rate=0.05, num_leaves=31,
            subsample=0.8, colsample_bytree=0.7,
            class_weight='balanced', random_state=42, verbose=-1, n_jobs=-1,
        ).fit(X, y)
        joblib.dump(sc,     BINARY_SCALER_DIR / 'scaler_60d.pkl')
        joblib.dump(lr,     BINARY_MODELS_DIR / 'ens_logreg_60d.pkl')
        joblib.dump(xgb_m,  BINARY_MODELS_DIR / 'ens_xgboost_60d.pkl')
        joblib.dump(lgb_m,  BINARY_MODELS_DIR / 'ens_lgbm_60d.pkl')
        print(f'  Ensemble 저장 -> binary_models/ens_logreg/xgboost/lgbm_60d.pkl')
        print(f'  Scaler 저장   -> binary_scaler/scaler_60d.pkl')

print(f'\n{"="*60}')
print(f'  모든 모델 저장 완료!')
print(f'  최종 피처: {len(all_features)}개  (avail {len(avail)} + ts {len(lag_roll_cols)+len(dir_cols)})')
print(f'  저장 경로: {FLASK_DIR}')
print(f'{"="*60}')

"""
validate_binary.py
재학습된 이진 분류 모델 Walk-Forward 성능 검증
새 모델(62개 피처) vs 기존 모델(111개 피처) 비교 출력
"""
import sys, json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score,
    recall_score, roc_auc_score
)
from sklearn.model_selection import TimeSeriesSplit
import xgboost as xgb
import lightgbm as lgb

_here = Path(__file__).parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

from utils import load_data

TARGET   = 'price_standard'
HORIZONS = [10, 30, 60]
N_SPLITS = 5

FLASK_DIR    = _here.parent / 'flask'
FEATURES_JSON = FLASK_DIR / 'binary_features' / 'features_list.json'
OLD_RESULTS   = _here / 'outputs' / '08_binary_results.csv'

# ── 피처 목록 로드 (재학습된 모델 기준) ──────────────────────
with open(FEATURES_JSON, encoding='utf-8') as f:
    meta = json.load(f)

selected_avail = meta['selected']
lag_roll_cols  = meta['lag_roll']
dir_cols       = meta['directional']
all_features   = meta['all_features']

print('=' * 62)
print('  재학습 모델 Walk-Forward 검증')
print('=' * 62)
print(f'피처 수: {len(all_features)}개  '
      f'(avail {len(selected_avail)} + lag/roll {len(lag_roll_cols)} + dir {len(dir_cols)})')

# ── 데이터 로드 & 피처 엔지니어링 ────────────────────────────
print('\n데이터 로드...')
df_raw = load_data().sort_values('일자').reset_index(drop=True)

df = df_raw[['일자', TARGET] + selected_avail].copy()
df = df.set_index('일자').sort_index()
df = df.interpolate(method='time')
df = df.dropna(subset=[TARGET])

for lag in [1, 3, 5, 10, 20, 30]:
    df[f'lag_{lag}d'] = df[TARGET].shift(lag)
for win in [5, 10, 20, 30]:
    df[f'roll_mean_{win}d'] = df[TARGET].shift(1).rolling(win).mean()
    df[f'roll_std_{win}d']  = df[TARGET].shift(1).rolling(win).std()

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

for h in HORIZONS:
    future = df[TARGET].shift(-h)
    df[f'label_{h}d'] = np.where(
        future > df[TARGET], 1,
        np.where(future < df[TARGET], 0, np.nan)
    )

df.dropna(subset=all_features, inplace=True)
print(f'유효 샘플: {len(df):,}행  기간: {df.index.min().date()} ~ {df.index.max().date()}')

# ── Walk-Forward 함수 ─────────────────────────────────────────
def walk_forward(model_fn, X, y, scale=False):
    tscv = TimeSeriesSplit(n_splits=N_SPLITS)
    accs, f1s, precs, recs, aucs = [], [], [], [], []
    for tr, val in tscv.split(X):
        Xtr, Xv = X[tr], X[val]
        ytr, yv = y[tr], y[val]
        if scale:
            sc = StandardScaler()
            Xtr = sc.fit_transform(Xtr)
            Xv  = sc.transform(Xv)
        m = model_fn(); m.fit(Xtr, ytr)
        pred = m.predict(Xv)
        prob = m.predict_proba(Xv)[:, 1]
        accs.append(accuracy_score(yv, pred))
        f1s.append(f1_score(yv, pred, zero_division=0))
        precs.append(precision_score(yv, pred, zero_division=0))
        recs.append(recall_score(yv, pred, zero_division=0))
        aucs.append(roc_auc_score(yv, prob))
    return dict(acc=np.mean(accs), f1=np.mean(f1s),
                prec=np.mean(precs), rec=np.mean(recs), auc=np.mean(aucs))


def walk_forward_ensemble(X, y):
    tscv = TimeSeriesSplit(n_splits=N_SPLITS)
    accs, f1s, precs, recs, aucs = [], [], [], [], []
    for tr, val in tscv.split(X):
        Xtr, Xv = X[tr], X[val]
        ytr, yv = y[tr], y[val]
        sc = StandardScaler()
        lr = LogisticRegression(
            class_weight='balanced', max_iter=2000, random_state=42, C=0.1
        ).fit(sc.fit_transform(Xtr), ytr)
        xb = xgb.XGBClassifier(
            n_estimators=400, learning_rate=0.05, max_depth=4,
            subsample=0.8, colsample_bytree=0.7,
            random_state=42, verbosity=0, n_jobs=-1, eval_metric='logloss'
        ).fit(Xtr, ytr)
        lb = lgb.LGBMClassifier(
            n_estimators=400, learning_rate=0.05, num_leaves=31,
            subsample=0.8, colsample_bytree=0.7,
            class_weight='balanced', random_state=42, verbose=-1, n_jobs=-1
        ).fit(Xtr, ytr)
        prob = (lr.predict_proba(sc.transform(Xv))[:, 1] +
                xb.predict_proba(Xv)[:, 1] +
                lb.predict_proba(Xv)[:, 1]) / 3
        pred = (prob >= 0.5).astype(int)
        accs.append(accuracy_score(yv, pred))
        f1s.append(f1_score(yv, pred, zero_division=0))
        precs.append(precision_score(yv, pred, zero_division=0))
        recs.append(recall_score(yv, pred, zero_division=0))
        aucs.append(roc_auc_score(yv, prob))
    return dict(acc=np.mean(accs), f1=np.mean(f1s),
                prec=np.mean(precs), rec=np.mean(recs), auc=np.mean(aucs))


# ── 검증 실행 ─────────────────────────────────────────────────
new_rows = []
for h in HORIZONS:
    print(f'\n[{h}일] 검증 중...')
    sub = df[all_features + [f'label_{h}d']].dropna()
    X   = sub[all_features].values
    y   = sub[f'label_{h}d'].values.astype(int)
    print(f'  샘플: {len(X):,}  상승: {y.sum():,}({y.mean():.1%})  하락: {(y==0).sum():,}')

    for model_name, fn, scale in [
        ('LogReg',   lambda: LogisticRegression(
                         class_weight='balanced', max_iter=2000,
                         random_state=42, C=0.1), True),
        ('XGBoost',  lambda: xgb.XGBClassifier(
                         n_estimators=400, learning_rate=0.05, max_depth=4,
                         subsample=0.8, colsample_bytree=0.7,
                         random_state=42, verbosity=0, n_jobs=-1,
                         eval_metric='logloss'), False),
        ('LightGBM', lambda: lgb.LGBMClassifier(
                         n_estimators=400, learning_rate=0.05, num_leaves=31,
                         subsample=0.8, colsample_bytree=0.7,
                         class_weight='balanced', random_state=42,
                         verbose=-1, n_jobs=-1), False),
    ]:
        r = walk_forward(fn, X, y, scale=scale)
        new_rows.append({
            '모델': model_name, '예측기간': f'{h}일',
            'Accuracy(%)': round(r['acc'] * 100, 1),
            'F1':          round(r['f1'], 3),
            'Precision':   round(r['prec'], 3),
            'Recall':      round(r['rec'], 3),
            'AUC':         round(r['auc'], 3),
        })
        print(f'  {model_name:<10} Acc={r["acc"]*100:.1f}%  '
              f'F1={r["f1"]:.3f}  AUC={r["auc"]:.3f}')

    r = walk_forward_ensemble(X, y)
    new_rows.append({
        '모델': 'Ensemble', '예측기간': f'{h}일',
        'Accuracy(%)': round(r['acc'] * 100, 1),
        'F1':          round(r['f1'], 3),
        'Precision':   round(r['prec'], 3),
        'Recall':      round(r['rec'], 3),
        'AUC':         round(r['auc'], 3),
    })
    print(f'  Ensemble   Acc={r["acc"]*100:.1f}%  '
          f'F1={r["f1"]:.3f}  AUC={r["auc"]:.3f}')

new_df = pd.DataFrame(new_rows)

# ── 기존 결과 로드 & 비교 ─────────────────────────────────────
old_df = pd.read_csv(OLD_RESULTS, encoding='utf-8-sig')
old_df.rename(columns={
    '모델': '모델', '예측기간': '예측기간',
    'Accuracy(%)': 'Accuracy(%)',
}, inplace=True)

# 컬럼명 통일
if 'Accuracy(%)' not in old_df.columns and 'Accuracy' in old_df.columns:
    old_df.rename(columns={'Accuracy': 'Accuracy(%)'}, inplace=True)

print('\n\n' + '=' * 62)
feat_count = len(all_features)
print(f'  성능 비교: 기존(111개) vs 재학습({feat_count}개) - Walk-Forward')
print('=' * 62)

METRICS = ['Accuracy(%)', 'F1', 'AUC']
MODELS  = ['LogReg', 'XGBoost', 'LightGBM', 'Ensemble']
PERIOD  = {10: '10일', 30: '30일', 60: '60일'}

for h in HORIZONS:
    period_str = PERIOD[h]
    print(f'\n  ── {period_str} 후 예측 ──')
    header = f'  {"모델":<12} {"기존Acc":>8} {"신Acc":>8} {"":>4} {"기존AUC":>8} {"신AUC":>8} {"":<4}'
    print(header)
    print('  ' + '-' * 56)
    for m in MODELS:
        old_r = old_df[(old_df['모델'] == m) & (old_df['예측기간'] == period_str)]
        new_r = new_df[(new_df['모델'] == m) & (new_df['예측기간'] == period_str)]
        if old_r.empty or new_r.empty:
            continue
        oa  = old_r['Accuracy(%)'].values[0]
        na  = new_r['Accuracy(%)'].values[0]
        oau = old_r['AUC'].values[0]
        nau = new_r['AUC'].values[0]
        da  = na - oa
        dau = nau - oau
        da_str  = f'({da:+.1f})' if da != 0 else '(=)'
        dau_str = f'({dau:+.3f})' if dau != 0 else '(=)'
        print(f'  {m:<12} {oa:>7.1f}% {na:>7.1f}% {da_str:>6}  '
              f'{oau:>8.3f} {nau:>8.3f} {dau_str:<8}')

# ── 재학습 결과 저장 ──────────────────────────────────────────
out_path = _here / 'outputs' / '08_binary_results_new.csv'
new_df.to_csv(out_path, index=False, encoding='utf-8-sig')
print(f'\n재학습 검증 결과 저장: {out_path}')

# ── 최적 모델 요약 ────────────────────────────────────────────
print('\n' + '=' * 62)
print('  최적 모델 요약 (AUC 기준)')
print('=' * 62)
print(f'  {"기간":<6} {"모델":<12} {"기존AUC":>8} {"신AUC":>8} {"변화":>8} {"기존Acc":>8} {"신Acc":>8}')
print('  ' + '-' * 60)
for h in HORIZONS:
    period_str = PERIOD[h]
    # 기존 최적
    old_sub = old_df[old_df['예측기간'] == period_str]
    best_old = old_sub.loc[old_sub['AUC'].idxmax()]
    # 새 모델 중 동일 모델명 기준
    new_sub = new_df[new_df['예측기간'] == period_str]
    same_m  = new_sub[new_sub['모델'] == best_old['모델']]
    if not same_m.empty:
        new_r = same_m.iloc[0]
        delta_auc = new_r['AUC'] - best_old['AUC']
        delta_acc = new_r['Accuracy(%)'] - best_old['Accuracy(%)']
        sign_auc  = '+' if delta_auc >= 0 else ''
        sign_acc  = '+' if delta_acc >= 0 else ''
        print(f'  {period_str:<6} {best_old["모델"]:<12} '
              f'{best_old["AUC"]:>8.3f} {new_r["AUC"]:>8.3f} '
              f'{sign_auc}{delta_auc:>+6.3f}  '
              f'{best_old["Accuracy(%)"]:>7.1f}% {new_r["Accuracy(%)"]:>7.1f}% '
              f'({sign_acc}{delta_acc:+.1f}%)')
print('=' * 62)

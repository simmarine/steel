"""
predict.py
모든 버전(2_10 ~ 4_60) 예측 처리 모듈.

변경 이력:
  - DB 연동: 데이터 로드 → steel_prices + steel_features
             예측 결과 저장 → predictions 테이블 (+ excel2/ fallback 유지)
"""
import os
import pickle
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import text

from crawlers.base import get_engine

# ── 경로 ─────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
FEATURES_DIR = BASE_DIR / 'features'
SCALER_DIR   = BASE_DIR / 'scaler'
PICKLE_DIR   = BASE_DIR / 'pickle'
LABELS_DIR   = BASE_DIR / 'labels'
EXCEL2_DIR   = BASE_DIR / 'excel2'

# ── DB ───────────────────────────────────────────────────────
_engine = get_engine()


# ── DB 데이터 로드 ────────────────────────────────────────────
def _load_wide_data() -> pd.DataFrame:
    """steel_prices + steel_features → wide DataFrame (일자 컬럼 포함)"""
    prices = pd.read_sql("""
        SELECT
            date             AS 일자,
            price_standard,
            price_special,
            volume_incoming,
            volume_stock,
            volume_rate,
            steel_production,
            scrap_input
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
    wide = features.pivot(index='일자', columns='feature_name', values='value').reset_index()
    wide.columns.name = None
    return pd.merge(prices, wide, on='일자', how='left')


# ── predictions 테이블 UPSERT ─────────────────────────────────
def _upsert_predictions(new_z_df: pd.DataFrame, model_type: int, horizon: int):
    """new_z_df(일자=목표날짜, pred=예측값)를 predictions 테이블에 저장"""
    rows = []
    for _, row in new_z_df.iterrows():
        target_dt = pd.to_datetime(row['일자'])
        base_date = (target_dt - pd.Timedelta(days=horizon)).date()
        rows.append({
            'base_date':       base_date,
            'model_type':      model_type,
            'horizon':         horizon,
            'predicted_value': float(row['pred']),
        })
    if not rows:
        return
    with _engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO predictions (base_date, model_type, horizon, predicted_value)
            VALUES (:base_date, :model_type, :horizon, :predicted_value)
            ON DUPLICATE KEY UPDATE predicted_value = VALUES(predicted_value)
        """), rows)
        conn.commit()


# ── excel2/ 저장 (fallback / 하위호환) ───────────────────────
def _save_excel2(df: pd.DataFrame, version: str):
    """예측 결과를 excel2/{version}.xlsx에도 저장 (get-chart-data 등 하위호환)"""
    EXCEL2_DIR.mkdir(exist_ok=True)
    output_file = EXCEL2_DIR / f"{version}.xlsx"

    if output_file.exists():
        existing = pd.read_excel(output_file, engine='openpyxl')
        existing['일자'] = pd.to_datetime(existing['일자'], errors='coerce')
        df['일자']       = pd.to_datetime(df['일자'],       errors='coerce')
        merged = pd.merge(existing, df, on='일자', how='outer', suffixes=('_old', '_new'))
        if 'pred_new' in merged.columns and 'pred_old' in merged.columns:
            merged['pred'] = merged['pred_new'].combine_first(merged['pred_old'])
            merged.drop(columns=['pred_old', 'pred_new'], inplace=True)
        merged.sort_values(by='일자', inplace=True)
        merged.to_excel(output_file, index=False, engine='openpyxl')
    else:
        df.to_excel(output_file, index=False, engine='openpyxl')


# ── 예측 비교 (특구가 ≥ 단가 보정) ───────────────────────────
def compare_and_update_special_price(
    price_version: str, special_price_version: str, new_dates: list
):
    """특구가 예측값이 단가 예측값보다 낮으면 단가 예측값으로 덮어씀 (DB 기준)"""
    price_type   = int(price_version.split('_')[0])
    special_type = int(special_price_version.split('_')[0])
    horizon      = int(price_version.split('_')[1])

    if not new_dates:
        return

    base_dates = set(
        (pd.to_datetime(d) - pd.Timedelta(days=horizon)).date() for d in new_dates
    )

    # int 리터럴로 쿼리 구성 (SQL injection 위험 없음)
    price_df = pd.read_sql(
        f"SELECT base_date, predicted_value FROM predictions "
        f"WHERE model_type = {price_type} AND horizon = {horizon}",
        _engine,
    )
    special_df = pd.read_sql(
        f"SELECT base_date, predicted_value FROM predictions "
        f"WHERE model_type = {special_type} AND horizon = {horizon}",
        _engine,
    )

    if price_df.empty or special_df.empty:
        return

    price_df['base_date']   = pd.to_datetime(price_df['base_date']).dt.date
    special_df['base_date'] = pd.to_datetime(special_df['base_date']).dt.date

    price_df   = price_df[price_df['base_date'].isin(base_dates)]
    special_df = special_df[special_df['base_date'].isin(base_dates)]

    price_map   = dict(zip(price_df['base_date'],   price_df['predicted_value']))
    special_map = dict(zip(special_df['base_date'], special_df['predicted_value']))

    update_rows = []
    for bd, sp_val in special_map.items():
        p_val = price_map.get(bd)
        if p_val is not None and sp_val < p_val:
            update_rows.append({
                'base_date':       bd,
                'model_type':      special_type,
                'horizon':         horizon,
                'predicted_value': float(p_val),
            })

    if not update_rows:
        return

    with _engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO predictions (base_date, model_type, horizon, predicted_value)
            VALUES (:base_date, :model_type, :horizon, :predicted_value)
            ON DUPLICATE KEY UPDATE predicted_value = VALUES(predicted_value)
        """), update_rows)
        conn.commit()

    print(f"Updated {len(update_rows)} special price rows for {special_price_version}")


# ── 단일 버전 처리 ─────────────────────────────────────────────
_VERSION_PARAMS = {
    "2_10": {"w": 100, "h": 10,  "window_size": 60,  "diff_size": 200},
    "2_20": {"w": 100, "h": 20,  "window_size": 50,  "diff_size": 200},
    "2_30": {"w": 200, "h": 30,  "window_size": 5,   "diff_size": 200},
    "2_45": {"w": 100, "h": 45,  "window_size": 30,  "diff_size": 40},
    "2_60": {"w": 80,  "h": 60,  "window_size": 30,  "diff_size": 40},
    "4_10": {"w": 200, "h": 10,  "window_size": 50,  "diff_size": 80},
    "4_20": {"w": 200, "h": 20,  "window_size": 50,  "diff_size": 200},
    "4_30": {"w": 200, "h": 30,  "window_size": 40,  "diff_size": 100},
    "4_45": {"w": 100, "h": 45,  "window_size": 40,  "diff_size": 70},
    "4_60": {"w": 80,  "h": 60,  "window_size": 30,  "diff_size": 10},
}


def process_version(version: str) -> pd.DataFrame:
    params      = _VERSION_PARAMS.get(version, {"w": 100, "h": 10, "window_size": 60, "diff_size": 200})
    w           = params["w"]
    h           = params["h"]
    window_size = params["window_size"]
    diff_size   = params["diff_size"]
    model_type  = int(version.split('_')[0])

    target_col = 'price_standard' if version.startswith('2_') else 'price_special'

    # ── 데이터 로드 (DB → fallback Excel) ────────────────────
    try:
        data = _load_wide_data()
        if data.empty:
            raise ValueError("DB 데이터 없음")
    except Exception as e:
        print(f"[DB 로드 실패, Excel fallback] {e}")
        fb_file = BASE_DIR / 'data' / (
            'data_2024_11.xlsx' if version.startswith('2_') else 'data_2024_11_특.xlsx'
        )
        if not fb_file.exists():
            raise FileNotFoundError(f"Fallback file not found: {fb_file}")
        data = pd.read_excel(fb_file)

    if '일자' not in data.columns:
        raise ValueError(f"'일자' column not found in data for {version}")
    if target_col not in data.columns:
        raise ValueError(f"'{target_col}' column not found in data for {version}")

    # ── 피처 로드 ─────────────────────────────────────────────
    train_features_path = FEATURES_DIR / f'train_features({version}).csv'
    if not train_features_path.exists():
        raise FileNotFoundError(f"Train features file not found: {train_features_path}")

    train_features_list = pd.read_csv(train_features_path)['Feature'].tolist()

    missing_cols = set(train_features_list) - set(data.columns)
    if missing_cols:
        raise ValueError(f"Missing columns for {version}: {missing_cols}")

    data_x = data[train_features_list]
    data_z = data[['일자', target_col]]

    # ── 전처리 ────────────────────────────────────────────────
    data_x = data_x.ewm(window_size).mean()
    data_x = data_x.diff(diff_size)
    data_x.dropna(inplace=True)
    data_z = data_z.loc[data_x.index]

    # ── 스케일러 + 모델 로드 ──────────────────────────────────
    scaler_path = SCALER_DIR / f'scaler_x({version}).pkl'
    model_path  = PICKLE_DIR / f'xgboost_model({version}).pkl'

    scaler_x = joblib.load(scaler_path)
    new_x_data = scaler_x.transform(data_x)

    new_x, new_z = [], []
    for i in range(len(new_x_data) - w + 1):
        new_x.append(new_x_data[i:i + w])
        new_z.append(data_z.iloc[i + w - 1].values)

    new_x = np.array(new_x)
    new_z = np.array(new_z)

    with open(model_path, 'rb') as mf:
        model = pickle.load(mf)

    raw_preds = model.predict(new_x.reshape(new_x.shape[0], -1))

    label_encoder = joblib.load(LABELS_DIR / f'label_encoder({version}).pkl')
    pred_labels   = label_encoder.inverse_transform(raw_preds)

    new_z_df = pd.DataFrame(new_z, columns=['일자', target_col])
    new_z_df['pred'] = new_z_df[target_col] + pred_labels
    new_z_df['일자'] = pd.to_datetime(new_z_df['일자']) + pd.Timedelta(days=h)
    new_z_df = new_z_df.drop(columns=[target_col])

    # 2_20 보정
    if version == "2_20":
        new_z_df['pred'] = new_z_df['pred'] + 10

    # ── 결과 저장 ─────────────────────────────────────────────
    _upsert_predictions(new_z_df, model_type=model_type, horizon=h)
    _save_excel2(new_z_df, version)

    print(f"[{version}] {len(new_z_df)}행 예측 완료 → DB + excel2 저장")
    return new_z_df


# ── 전체 버전 처리 ─────────────────────────────────────────────
def process_all_versions():
    price_versions         = ["2_10", "2_20", "2_30", "2_45", "2_60"]
    special_price_versions = ["4_10", "4_20", "4_30", "4_45", "4_60"]

    new_dates = []

    for price_ver, special_ver in zip(price_versions, special_price_versions):
        price_data   = process_version(price_ver)
        special_data = process_version(special_ver)

        if price_data is not None and '일자' in price_data.columns:
            new_dates += price_data['일자'].tolist()
        else:
            print(f"Warning: No '일자' data for {price_ver}")

        compare_and_update_special_price(price_ver, special_ver, new_dates)
        print(f"Processed: {price_ver} & {special_ver}")


if __name__ == "__main__":
    process_all_versions()

import io
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import joblib
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
import numpy as np
from sklearn.preprocessing import StandardScaler
from datetime import timedelta
import json
import os
from datetime import datetime
from sqlalchemy import text

from predict import process_all_versions
from predict_binary import predict_all_binary, predict_binary
from crawlers import (
    crawl_feature_2,  crawl_feature_3,  crawl_feature_4,
    crawl_feature_5,  crawl_feature_6,  crawl_feature_7,
    crawl_feature_8,  crawl_feature_10, crawl_feature_12,
    crawl_feature_13, crawl_feature_15, crawl_feature_16,
    crawl_feature_17, crawl_feature_18, crawl_feature_19,
    crawl_feature_20, crawl_feature_21, crawl_feature_22,
    crawl_feature_23, crawl_feature_24, crawl_feature_25,
    crawl_feature_26, crawl_feature_29, crawl_feature_30,
    crawl_feature_31, crawl_feature_32, crawl_feature_33,
    crawl_feature_34, crawl_feature_35, crawl_feature_36,
    crawl_feature_37, crawl_feature_38,
)
from crawlers.base import get_engine, log_crawl

# ── 경로 상수 ─────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent
PICKLE_DIR      = BASE_DIR / 'pickle'
FEATURES_DIR    = BASE_DIR / 'features'
LABELS_DIR      = BASE_DIR / 'labels'
EXCEL_FILES_DIR = BASE_DIR / 'excel'
EXCEL_FILES_DIR2= BASE_DIR / 'excel2'
DATA_FILE       = BASE_DIR / 'data' / 'data_2024_11.xlsx'
DATA_FILE_SPECIAL = BASE_DIR / 'data' / 'data_2024_11_특.xlsx'

# ── DB 엔진 ───────────────────────────────────────────────────
_engine = get_engine()

app = Flask(__name__)
CORS(app)

# ── 모델 설정 ─────────────────────────────────────────────────
price_models_config = {
    "10": {
        "model_path":   str(PICKLE_DIR / 'xgboost_model(2_10).pkl'),
        "feature_path": str(FEATURES_DIR / 'train_features(2_10).csv'),
        "window": 100, "horizon": 10, "model_key": "2_10",
    },
    "20": {
        "model_path":   str(PICKLE_DIR / 'xgboost_model(2_20).pkl'),
        "feature_path": str(FEATURES_DIR / 'train_features(2_20).csv'),
        "window": 100, "horizon": 20, "model_key": "2_20",
    },
    "30": {
        "model_path":   str(PICKLE_DIR / 'xgboost_model(2_30).pkl'),
        "feature_path": str(FEATURES_DIR / 'train_features(2_30).csv'),
        "window": 200, "horizon": 30, "model_key": "2_30",
    },
    "45": {
        "model_path":   str(PICKLE_DIR / 'xgboost_model(2_45).pkl'),
        "feature_path": str(FEATURES_DIR / 'train_features(2_45).csv'),
        "window": 100, "horizon": 45, "model_key": "2_45",
    },
    "60": {
        "model_path":   str(PICKLE_DIR / 'xgboost_model(2_60).pkl'),
        "feature_path": str(FEATURES_DIR / 'train_features(2_60).csv'),
        "window": 80,  "horizon": 60, "model_key": "2_60",
    },
}

special_price_models_config = {
    "10": {
        "model_path":   str(PICKLE_DIR / 'xgboost_model(4_10).pkl'),
        "feature_path": str(FEATURES_DIR / 'train_features(4_10).csv'),
        "window": 200, "horizon": 10, "model_key": "4_10",
    },
    "20": {
        "model_path":   str(PICKLE_DIR / 'xgboost_model(4_20).pkl'),
        "feature_path": str(FEATURES_DIR / 'train_features(4_20).csv'),
        "window": 200, "horizon": 20, "model_key": "4_20",
    },
    "30": {
        "model_path":   str(PICKLE_DIR / 'xgboost_model(4_30).pkl'),
        "feature_path": str(FEATURES_DIR / 'train_features(4_30).csv'),
        "window": 200, "horizon": 30, "model_key": "4_30",
    },
    "45": {
        "model_path":   str(PICKLE_DIR / 'xgboost_model(4_45).pkl'),
        "feature_path": str(FEATURES_DIR / 'train_features(4_45).csv'),
        "window": 100, "horizon": 45, "model_key": "4_45",
    },
    "60": {
        "model_path":   str(PICKLE_DIR / 'xgboost_model(4_60).pkl'),
        "feature_path": str(FEATURES_DIR / 'train_features(4_60).csv'),
        "window": 80,  "horizon": 60, "model_key": "4_60",
    },
}

volume_models_config = {
    "10": {
        "model_path":   str(PICKLE_DIR / 'xgboost_model(3_10).pkl'),
        "feature_path": str(FEATURES_DIR / 'train_features(3_10).csv'),
        "window": 10, "horizon": 10,
    },
    "20": {
        "model_path":   str(PICKLE_DIR / 'xgboost_model(3_20).pkl'),
        "feature_path": str(FEATURES_DIR / 'train_features(3_20).csv'),
        "window": 30, "horizon": 20,
    },
    "30": {
        "model_path":   str(PICKLE_DIR / 'xgboost_model(3_30).pkl'),
        "feature_path": str(FEATURES_DIR / 'train_features(3_30).csv'),
        "window": 50, "horizon": 30,
    },
}


# ── 모델 · 피처 로드 ──────────────────────────────────────────
def load_models_and_features(model_dict):
    models   = {}
    features = {}
    for key, config in model_dict.items():
        models[key]   = joblib.load(config["model_path"])
        features[key] = pd.read_csv(config["feature_path"])["Feature"].tolist()
    return models, features


price_models,         price_features         = load_models_and_features(price_models_config)
special_price_models, special_price_features = load_models_and_features(special_price_models_config)
volume_models,        volume_features        = load_models_and_features(volume_models_config)


# ── DB 데이터 로드 헬퍼 ───────────────────────────────────────
_PRICES_QUERY = """
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
"""

def _load_prices_from_db() -> pd.DataFrame:
    df = pd.read_sql(_PRICES_QUERY, _engine)
    df['일자'] = pd.to_datetime(df['일자'])
    return df


def _load_features_from_db() -> pd.DataFrame:
    df = pd.read_sql(
        "SELECT date AS 일자, feature_name, value FROM steel_features", _engine
    )
    if df.empty:
        return pd.DataFrame()
    wide = df.pivot(index='일자', columns='feature_name', values='value').reset_index()
    wide.columns.name = None
    wide['일자'] = pd.to_datetime(wide['일자'])
    return wide


def _load_main_data() -> pd.DataFrame:
    """steel_prices + steel_features → wide DataFrame"""
    prices   = _load_prices_from_db()
    features = _load_features_from_db()
    if features.empty:
        return prices
    return pd.merge(prices, features, on='일자', how='left')


# ── startup: 전역 데이터 로드 (DB → fallback Excel) ───────────
def _startup_load():
    try:
        raw = _load_main_data()
        d       = raw.drop(columns=['price_special'], errors='ignore').copy()
        d_spec  = raw.drop(columns=['price_standard'], errors='ignore').copy()

        # price_features에 필요한 컬럼이 data에 있는지 검증
        all_needed = set()
        for key in price_features:
            all_needed.update(price_features[key])
        missing = all_needed - set(d.columns)
        if missing:
            raise ValueError(f'DB 피처 부족: {len(missing)}개 컬럼 없음 ({list(missing)[:5]}…)')

        return d, d_spec
    except Exception as e:
        print(f'[DB 로드 실패, Excel fallback] {e}')
        return pd.read_excel(DATA_FILE), pd.read_excel(DATA_FILE_SPECIAL)


data, special_data = _startup_load()


# ── binary_predictions 테이블 자동 생성 ──────────────────────
def _ensure_binary_predictions_table():
    with _engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS binary_predictions (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                base_date   DATE         NOT NULL COMMENT '예측 기준일',
                horizon     INT          NOT NULL COMMENT '예측 기간(일)',
                direction   VARCHAR(4)   NOT NULL COMMENT 'UP / DOWN',
                probability FLOAT        NOT NULL COMMENT '상승 확률 (0~1)',
                model_name  VARCHAR(20)  NOT NULL COMMENT '사용 모델명',
                updated_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uq_base_horizon (base_date, horizon)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='이진 분류 예측 결과';
        """))
        conn.commit()

try:
    _ensure_binary_predictions_table()
    print('[startup] binary_predictions 테이블 준비 완료')
except Exception as _e:
    print(f'[startup] binary_predictions 테이블 생성 실패: {_e}')


# ── 전처리 ───────────────────────────────────────────────────
def preprocess_data(df):
    df.columns = df.columns.str.replace(r'\s+', '_', regex=True)
    df.columns = df.columns.str.strip()
    df['일자'] = pd.to_datetime(df['일자'])
    df.set_index('일자', inplace=True)
    df.index = df.index.normalize()


preprocess_data(data)
preprocess_data(special_data)


def preprocess_data_with_new_logic(df, window_size, diff_size):
    ewm_data  = df.ewm(span=window_size).mean()
    diff_data = ewm_data.diff(diff_size)
    diff_data.dropna(inplace=True)
    return diff_data


def seq2dataset(d_x, window):
    X = []
    for i in range(len(d_x) - window + 1):
        X.append(d_x[i:i + window])
    return np.array(X)


def load_index_to_label(model_key):
    file_path = LABELS_DIR / f'index_to_label({model_key}).json'
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Index-to-label JSON not found for model key: {model_key} at {file_path}"
        )


def predict_for_model(model, scaler_x, train_features, window,
                      input_date, target_column, data_source, key, model_key=None):
    if target_column == "volume_incoming":
        try:
            data_source = _load_main_data()
        except Exception:
            data_source = pd.read_excel(DATA_FILE)
        data_source['일자'] = pd.to_datetime(data_source['일자'])
        data_source.set_index('일자', inplace=True)
        data_source.index = data_source.index.normalize()

    window_start_date = input_date - timedelta(days=window)
    window_data = data_source.loc[window_start_date:input_date]

    if len(window_data) < window:
        raise ValueError("Insufficient historical data")

    try:
        current_price = data_source.loc[input_date, target_column]
    except KeyError:
        raise ValueError(f"No price data available for the date: {input_date}")

    feature_data   = window_data[train_features]
    processed_data = preprocess_data_with_new_logic(feature_data, window_size=1, diff_size=1)
    scaled_features = scaler_x[key].transform(processed_data)
    X_input    = seq2dataset(scaled_features, window)
    input_data = X_input[-1].reshape(1, -1)

    if model_key:
        index_to_label  = load_index_to_label(model_key)
        predicted_index = int(model.predict(input_data)[0])
        if str(predicted_index) not in index_to_label:
            raise ValueError(
                f"Predicted index {predicted_index} not found in index_to_label "
                f"for model {model_key}"
            )
        predicted_change = float(index_to_label[str(predicted_index)])
    else:
        predicted_change = float(model.predict(input_data)[0])

    return current_price + predicted_change


# ── 스케일러 ──────────────────────────────────────────────────
scaler_x_price   = {}
scaler_x_special = {}
scaler_x_volume  = {}

for key in price_models_config.keys():
    ws, ds = {
        "10": (60, 200), "20": (50, 200),
        "30": (5,  200), "45": (30, 40), "60": (30, 40),
    }[key]
    scaler_x_price[key] = StandardScaler().fit(
        preprocess_data_with_new_logic(data[price_features[key]], window_size=ws, diff_size=ds)
    )

for key in special_price_models_config.keys():
    ws, ds = {
        "10": (50, 80), "20": (50, 200),
        "30": (40, 100), "45": (40, 70), "60": (30, 10),
    }[key]
    scaler_x_special[key] = StandardScaler().fit(
        preprocess_data_with_new_logic(
            special_data[special_price_features[key]], window_size=ws, diff_size=ds
        )
    )

for key in volume_models_config.keys():
    scaler_x_volume[key] = StandardScaler().fit(
        preprocess_data_with_new_logic(data[volume_features[key]], window_size=5, diff_size=1)
    )


# ── DB UPSERT 헬퍼 ────────────────────────────────────────────
_PRICE_COL_MAP = {
    'price_standard': 'price_standard',
    'price_special':  'price_special',
    'volume_incoming': 'volume_incoming',
    'volume_stock':   'volume_stock',
    'volume_rate':    'volume_rate',
    'steel_production': 'steel_production',
    'scrap_input':    'scrap_input',
    'region_central': 'region_central',
    'region_south':   'region_south',
    'region_total':   'region_total',
}


def _upsert_steel_prices(row: dict):
    """steel_prices 단일 행 UPSERT"""
    with _engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO steel_prices
                (date, price_standard, price_special,
                 volume_incoming, volume_stock, volume_rate,
                 steel_production, scrap_input,
                 region_central, region_south, region_total)
            VALUES
                (:date, :price_standard, :price_special,
                 :volume_incoming, :volume_stock, :volume_rate,
                 :steel_production, :scrap_input,
                 :region_central, :region_south, :region_total)
            ON DUPLICATE KEY UPDATE
                price_standard   = COALESCE(VALUES(price_standard),   price_standard),
                price_special    = COALESCE(VALUES(price_special),    price_special),
                volume_incoming  = COALESCE(VALUES(volume_incoming),  volume_incoming),
                volume_stock     = COALESCE(VALUES(volume_stock),     volume_stock),
                volume_rate      = COALESCE(VALUES(volume_rate),      volume_rate),
                steel_production = COALESCE(VALUES(steel_production), steel_production),
                scrap_input      = COALESCE(VALUES(scrap_input),      scrap_input),
                region_central   = COALESCE(VALUES(region_central),   region_central),
                region_south     = COALESCE(VALUES(region_south),     region_south),
                region_total     = COALESCE(VALUES(region_total),     region_total),
                updated_at       = CURRENT_TIMESTAMP
        """), {
            'date':             row.get('date'),
            'price_standard':   row.get('price_standard'),
            'price_special':    row.get('price_special'),
            'volume_incoming':  row.get('volume_incoming'),
            'volume_stock':     row.get('volume_stock'),
            'volume_rate':      row.get('volume_rate'),
            'steel_production': row.get('steel_production'),
            'scrap_input':      row.get('scrap_input'),
            'region_central':   row.get('region_central'),
            'region_south':     row.get('region_south'),
            'region_total':     row.get('region_total'),
        })
        conn.commit()


def _upsert_steel_features(date_val, features_dict: dict):
    """steel_features 다중 행 UPSERT"""
    rows = [
        {'date': date_val, 'feature_name': k,
         'value': None if (v is None or (isinstance(v, float) and np.isnan(v))) else v}
        for k, v in features_dict.items()
    ]
    if not rows:
        return
    with _engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO steel_features (date, feature_name, value)
            VALUES (:date, :feature_name, :value)
            ON DUPLICATE KEY UPDATE value = VALUES(value)
        """), rows)
        conn.commit()


_PRICE_COL_SET = set(_PRICE_COL_MAP.keys())


def save_or_update_excel(df: pd.DataFrame) -> str:
    """크롤링 결과를 DB에 저장 (steel_prices + steel_features)"""
    skip = _PRICE_COL_SET | {'일자'}
    for _, row in df.iterrows():
        date_val = pd.to_datetime(row['일자']).date()
        price_row = {'date': date_val}
        for col, db_col in _PRICE_COL_MAP.items():
            if col in row:
                v = row[col]
                price_row[db_col] = None if (pd.isna(v) if isinstance(v, float) else False) else v
        _upsert_steel_prices(price_row)

        feat_dict = {}
        for k, v in row.items():
            if k in skip:
                continue
            feat_dict[k] = None if (isinstance(v, float) and np.isnan(v)) else v
        _upsert_steel_features(date_val, feat_dict)
    return 'DB'


def save_or_update_excel_special(df: pd.DataFrame) -> str:
    """특별단가 포함 크롤링 결과 DB 저장 (save_or_update_excel 공용)"""
    return save_or_update_excel(df)


# ── 라우트 ───────────────────────────────────────────────────

@app.route("/transfer-predict", methods=["POST"])
def transfer_prediction():
    try:
        received_data = request.get_json()
        selected_date = received_data.get('date')
        if not selected_date:
            return jsonify({"error": "No date provided"}), 400

        input_date = pd.to_datetime(selected_date).normalize()

        predictions = {"price": {}, "special_price": {}, "volume": {}}

        try:
            predictions["price"] = {
                key: predict_for_model(
                    model=price_models[key],
                    scaler_x=scaler_x_price,
                    train_features=price_features[key],
                    window=price_models_config[key]["window"],
                    input_date=input_date,
                    target_column="price_standard",
                    data_source=data,
                    key=key,
                    model_key=price_models_config[key]["model_key"],
                ) for key in price_models
            }
        except Exception as e:
            print("Error in price prediction:", str(e))

        try:
            for key in special_price_models:
                predictions["special_price"][key] = predict_for_model(
                    model=special_price_models[key],
                    scaler_x=scaler_x_special,
                    train_features=special_price_features[key],
                    window=special_price_models_config[key]["window"],
                    input_date=input_date,
                    target_column="price_special",
                    data_source=special_data,
                    key=key,
                    model_key=special_price_models_config[key]["model_key"],
                )
        except Exception as e:
            print(f"Error in special price prediction: {e}")

        try:
            predictions["volume"] = {
                key: predict_for_model(
                    model=volume_models[key],
                    scaler_x=scaler_x_volume,
                    train_features=volume_features[key],
                    window=volume_models_config[key]["window"],
                    input_date=input_date,
                    target_column="volume_incoming",
                    data_source=data,
                    key=key,
                ) for key in volume_models
            }
        except Exception as e:
            print("Error in volume prediction:", str(e))

        return jsonify(predictions)

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/get-chart-data", methods=["POST"])
def get_chart_data():
    try:
        req = request.get_json()
        file_name = req.get("file_name")
        if not file_name:
            return jsonify({"error": "No file_name provided"}), 400

        file_path = EXCEL_FILES_DIR / f"{file_name}.xlsx"
        if not file_path.exists():
            return jsonify({"error": f"File {file_name}.xlsx not found"}), 404

        df = pd.read_excel(file_path)
        if "true" not in df.columns or "pred" not in df.columns:
            return jsonify({"error": "File does not contain required columns ('true', 'pred')"}), 400

        return jsonify({"true": df["true"].tolist(), "pred": df["pred"].tolist()})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def load_model_predictions(model_key: str, selected_date: str) -> dict:
    """predictions 테이블에서 예측값 조회"""
    model_type_str, horizon_str = model_key.split("_")
    model_type = int(model_type_str)
    horizon    = int(horizon_str)

    selected_dt = pd.to_datetime(selected_date)
    target_date = selected_dt + pd.Timedelta(days=horizon)

    with _engine.connect() as conn:
        row = conn.execute(text("""
            SELECT predicted_value
            FROM predictions
            WHERE model_type = :model_type
              AND horizon    = :horizon
              AND base_date  = :base_date
            LIMIT 1
        """), {
            'model_type': model_type,
            'horizon':    horizon,
            'base_date':  selected_dt.date(),
        }).fetchone()

    if row is None:
        # DB에 없으면 excel2 fallback
        file_path = EXCEL_FILES_DIR2 / f"{model_key}.xlsx"
        if not file_path.exists():
            raise FileNotFoundError(f"No prediction for {model_key} on {selected_dt.date()}")
        df = pd.read_excel(file_path)
        if "pred" not in df.columns or "일자" not in df.columns:
            raise ValueError(f"File {model_key}.xlsx missing required columns")
        pred_row = df[df["일자"] == target_date]
        if pred_row.empty:
            raise ValueError(f"No data for target date {target_date.date()} in {model_key}")
        pred_value = pred_row["pred"].iloc[0]
    else:
        pred_value = row[0]

    return {"date": target_date.strftime("%Y-%m-%d"), "pred": int(pred_value)}


@app.route('/download-data-file', methods=['GET'])
def download_data_file():
    """기본 데이터 파일 다운로드 (DB → Excel 변환)"""
    try:
        df = _load_prices_from_db().drop(columns=['price_special'], errors='ignore')
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine='openpyxl')
        buf.seek(0)
        return send_file(
            buf,
            as_attachment=True,
            download_name='data_2024_11.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/download-special-data-file', methods=['GET'])
def download_special_data_file():
    """특구가 데이터 파일 다운로드 (DB → Excel 변환)"""
    try:
        df = _load_prices_from_db().drop(columns=['price_standard'], errors='ignore')
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine='openpyxl')
        buf.seek(0)
        return send_file(
            buf,
            as_attachment=True,
            download_name='data_2024_11_특.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get-recent-data', methods=['GET'])
def get_recent_data():
    try:
        df = pd.read_sql("""
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
            ORDER BY date DESC
            LIMIT 5
        """, _engine)
        df['일자'] = pd.to_datetime(df['일자'])
        df.fillna('-', inplace=True)
        return jsonify({"recent": df.to_dict(orient='records')}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/save-data', methods=['POST'])
def save_data():
    try:
        req = request.json
        vol_in   = float(req.get("volume_incoming", 0))
        vol_stk  = float(req.get("volume_stock", 0))
        stl_prod = float(req.get("steel_production", 0))
        scrap    = float(req.get("scrap_input", 0))
        price_st = int(float(req.get("price_standard", 0))) if req.get("price_standard") else None
        price_sp = int(float(req.get("price_special",  0))) if req.get("price_special")  else None
        date_str = req.get("일자", "")

        vol_rate = (vol_in / scrap) if scrap != 0 else None

        date_val = pd.to_datetime(date_str).date()

        _upsert_steel_prices({
            'date':             date_val,
            'price_standard':   price_st,
            'price_special':    price_sp,
            'volume_incoming':  vol_in,
            'volume_stock':     vol_stk,
            'volume_rate':      round(vol_rate, 6) if vol_rate is not None else None,
            'steel_production': stl_prod,
            'scrap_input':      scrap,
        })

        return jsonify({"message": "Data saved successfully!"}), 200

    except Exception as e:
        print("Error saving data:", str(e))
        return jsonify({"error": str(e)}), 500


@app.route('/save-time', methods=['POST'])
def save_time():
    now = datetime.now().strftime('%Y-%m-%d')
    try:
        log_crawl(_engine, crawl_type='manual_update',
                  start_date=now, end_date=now, status='success')
    except Exception as e:
        print(f"[save-time] crawl_log 기록 실패: {e}")
    return jsonify({'status': 'saved', 'date': now})


@app.route('/get-time', methods=['GET'])
def get_time():
    try:
        with _engine.connect() as conn:
            row = conn.execute(text("""
                SELECT DATE_FORMAT(executed_at, '%Y-%m-%d') AS last_update
                FROM crawl_logs
                WHERE crawl_type = 'manual_update'
                ORDER BY executed_at DESC
                LIMIT 1
            """)).fetchone()
        return jsonify({'lastUpdate': row[0] if row else '-'})
    except Exception as e:
        print(f"[get-time] {e}")
        return jsonify({'lastUpdate': '-'})


@app.route('/run-crawling', methods=['POST'])
def run_crawling():
    try:
        request_data = request.get_json()
        start_date   = request_data.get('start_date', '20240101')
        end_date     = request_data.get('end_date',   '20250124')
        start_month  = start_date[:6]
        end_month    = end_date[:6]

        data_2  = crawl_feature_2(start_date, end_date)
        data_3  = crawl_feature_3(start_date, end_date)
        data_4  = crawl_feature_4(start_date, end_date)
        data_6  = crawl_feature_6(start_date, end_date)
        data_7  = crawl_feature_7(start_date, end_date)
        data_8  = crawl_feature_8(start_date, end_date)
        data_10 = crawl_feature_10(start_date, end_date)
        data_12 = crawl_feature_12(start_date, end_date)
        data_13 = crawl_feature_13(start_month, end_month)
        data_15 = crawl_feature_15()
        data_16 = crawl_feature_16()
        data_17 = crawl_feature_17()
        data_18 = crawl_feature_18()
        data_19 = crawl_feature_19()
        data_20 = crawl_feature_20()
        data_21 = crawl_feature_21()
        data_22 = crawl_feature_22(start_date, end_date)
        data_24 = crawl_feature_24()
        data_25 = crawl_feature_25()
        data_26 = crawl_feature_26()
        data_29 = crawl_feature_29(start_date, end_date)
        data_30 = crawl_feature_30(start_month, end_month)
        data_31 = crawl_feature_31(start_month, end_month)
        data_32 = crawl_feature_32(start_month, end_month)
        data_33 = crawl_feature_33(start_month, end_month)
        data_34 = crawl_feature_34(start_month, end_month)
        data_35 = crawl_feature_35(start_month, end_month)
        data_36 = crawl_feature_36(start_month, end_month)
        data_37 = crawl_feature_37(start_date, end_date)
        data_38 = crawl_feature_38(start_date, end_date)

        data_frames = [
            data_2,  data_3,  data_4,  data_6,  data_7,  data_8,
            data_10, data_12, data_13, data_15, data_16, data_17,
            data_18, data_19, data_20, data_21, data_22, data_24,
            data_25, data_26, data_29, data_30, data_31, data_32,
            data_33, data_34, data_35, data_36, data_37, data_38,
        ]
        valid = [df for df in data_frames if df is not None and not df.empty]

        if not valid:
            return jsonify({"error": "No valid data found for the given date range."}), 404

        for idx, df in enumerate(valid):
            if '일자' not in df.columns:
                return jsonify({"error": f"DataFrame[{idx}] missing '일자' column."}), 500

        combined = pd.concat(valid, ignore_index=True)

        for col in combined.columns:
            if col != '일자':
                combined[col] = pd.to_numeric(combined[col], errors='coerce')

        combined = combined.groupby('일자', as_index=False).agg(
            lambda x: x.dropna().iloc[0] if x.dropna().size > 0 else None
        )

        save_or_update_excel(combined)

        log_crawl(
            _engine,
            crawl_type='run_crawling',
            start_date=start_date,
            end_date=end_date,
            status='success',
            rows_fetched=len(combined),
        )

        return jsonify({
            "message": "Crawling and saving completed successfully!",
            "rows_saved": len(combined),
        }), 200

    except Exception as e:
        print(f"Error during crawling: {e}")
        log_crawl(_engine, crawl_type='run_crawling',
                  start_date=None, end_date=None,
                  status='failed', error_msg=str(e)[:500])
        return jsonify({"error": str(e)}), 500


@app.route('/interpolate-data', methods=['POST'])
def interpolate_data():
    """
    steel_prices 전체 날짜 범위를 재구성하고 결측값을 보간.
    price_standard / price_special은 5단위 정수로 반올림.
    """
    try:
        df = _load_prices_from_db()
        if df.empty:
            return jsonify({"message": "No data to interpolate"}), 200

        df = df.drop_duplicates(subset=['일자'], keep='last')
        df = df.set_index('일자')
        full_range = pd.date_range(df.index.min(), df.index.max(), freq='D')
        df = df.reindex(full_range)

        numeric_cols = df.select_dtypes(include=[float, int]).columns
        df[numeric_cols] = df[numeric_cols].interpolate(method='time')
        df = df.reset_index().rename(columns={'index': '일자'})

        if 'price_standard' in df.columns:
            df['price_standard'] = df['price_standard'].apply(
                lambda x: 5 * round(x / 5) if pd.notna(x) else None)
        if 'price_special' in df.columns:
            df['price_special'] = df['price_special'].apply(
                lambda x: 5 * round(x / 5) if pd.notna(x) else None)

        # 보간된 데이터를 DB에 다시 저장
        for _, row in df.iterrows():
            _upsert_steel_prices({
                'date':             row['일자'].date(),
                'price_standard':   row.get('price_standard'),
                'price_special':    row.get('price_special'),
                'volume_incoming':  row.get('volume_incoming'),
                'volume_stock':     row.get('volume_stock'),
                'volume_rate':      row.get('volume_rate'),
                'steel_production': row.get('steel_production'),
                'scrap_input':      row.get('scrap_input'),
            })

        return jsonify({"message": "Interpolation completed successfully!"}), 200

    except Exception as e:
        print("Error during interpolation:", e)
        return jsonify({"error": str(e)}), 500


@app.route('/run-all-versions', methods=['POST'])
def run_all_versions_endpoint():
    try:
        process_all_versions()
        return jsonify({"message": "All versions processed successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/get-model-prediction", methods=["POST"])
def get_model_prediction():
    try:
        req = request.get_json()
        model_key     = req.get("model_key")
        selected_date = req.get("date")

        if not model_key:
            return jsonify({"error": "No model_key provided"}), 400
        if not selected_date:
            return jsonify({"error": "No date provided"}), 400

        result = load_model_predictions(model_key, selected_date)
        return jsonify(result)

    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route("/get-dashboard-data", methods=["POST"])
def get_dashboard_data():
    try:
        req         = request.get_json()
        target_date = req.get("date")
        if not target_date:
            return jsonify({"error": "No date provided"}), 400

        target_date = pd.to_datetime(target_date).date()

        with _engine.connect() as conn:
            row = conn.execute(text("""
                SELECT price_standard, price_special, volume_incoming
                FROM steel_prices
                WHERE date = :date
                LIMIT 1
            """), {'date': target_date}).fetchone()

        if row is None:
            return jsonify({"price": "N/A", "special_price": "N/A", "volume": "N/A"}), 200

        return jsonify({
            "price":         f"{row[0]} 원" if row[0] is not None else "N/A",
            "special_price": f"{row[1]} 원" if row[1] is not None else "N/A",
            "volume":        f"{row[2]} kg"  if row[2] is not None else "N/A",
        }), 200

    except Exception as e:
        print(f"Error in /get-dashboard-data: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/get-last-date', methods=['GET'])
def get_last_date():
    try:
        with _engine.connect() as conn:
            row = conn.execute(
                text("SELECT MAX(date) FROM steel_prices")
            ).fetchone()

        if row is None or row[0] is None:
            return jsonify({"error": "No valid dates found."}), 404

        return jsonify({"last_date": str(row[0])}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


# ── 이진 분류 예측 엔드포인트 ────────────────────────────────

@app.route('/run-binary-predict', methods=['POST'])
def run_binary_predict():
    """
    10일·30일·60일 이진 분류 예측 실행 후 binary_predictions 테이블에 저장.

    Request body (선택): {"horizon": 10}  # 생략 시 전체(10/30/60) 실행
    Response:
        {"results": [
            {"base_date": "...", "target_date": "...",
             "horizon": 10, "direction": "UP", "probability": 0.72, "model": "XGBoost"},
            ...
        ]}
    """
    try:
        req     = request.get_json(silent=True) or {}
        horizon = req.get('horizon')

        if horizon is not None:
            horizon = int(horizon)
            result  = predict_binary(horizon)
            return jsonify({'results': [result]}), 200
        else:
            results = predict_all_binary()
            return jsonify({'results': results}), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f'[/run-binary-predict] {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/get-binary-prediction', methods=['POST'])
def get_binary_prediction():
    """
    특정 base_date + horizon 의 이진 분류 예측 결과 조회.

    Request body: {"date": "2025-04-18", "horizon": 10}
    Response:
        {"base_date": "...", "target_date": "...",
         "horizon": 10, "direction": "UP", "probability": 0.72, "model": "XGBoost"}
    """
    try:
        req     = request.get_json()
        date    = req.get('date')
        horizon = req.get('horizon')

        if not date or horizon is None:
            return jsonify({'error': 'date 와 horizon 필드가 필요합니다'}), 400

        horizon    = int(horizon)
        base_date  = pd.to_datetime(date).date()
        target_date = (pd.to_datetime(base_date) + pd.Timedelta(days=horizon)).date()

        with _engine.connect() as conn:
            row = conn.execute(text("""
                SELECT direction, probability, model_name
                FROM binary_predictions
                WHERE base_date = :base_date AND horizon = :horizon
                LIMIT 1
            """), {'base_date': base_date, 'horizon': horizon}).fetchone()

        if row is None:
            return jsonify({'error': f'{base_date} 기준 {horizon}일 예측 결과 없음'}), 404

        return jsonify({
            'base_date':   str(base_date),
            'target_date': str(target_date),
            'horizon':     horizon,
            'direction':   row[0],
            'probability': round(float(row[1]), 4),
            'model':       row[2],
        }), 200

    except Exception as e:
        print(f'[/get-binary-prediction] {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/get-all-binary-predictions', methods=['GET'])
def get_all_binary_predictions():
    """
    저장된 이진 분류 예측 전체 목록 반환 (최신 순, 각 horizon 별 최신 1건).

    Response:
        {"predictions": [
            {"base_date": "...", "target_date": "...",
             "horizon": 10, "direction": "UP", "probability": 0.72, "model": "XGBoost"},
            ...
        ]}
    """
    try:
        with _engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT b1.base_date, b1.horizon, b1.direction,
                       b1.probability, b1.model_name
                FROM binary_predictions b1
                INNER JOIN (
                    SELECT horizon, MAX(base_date) AS max_date
                    FROM binary_predictions
                    GROUP BY horizon
                ) b2 ON b1.horizon = b2.horizon AND b1.base_date = b2.max_date
                ORDER BY b1.horizon
            """)).fetchall()

        predictions = []
        for r in rows:
            base_date   = r[0]
            horizon     = r[1]
            target_date = (pd.to_datetime(base_date) + pd.Timedelta(days=horizon)).date()
            predictions.append({
                'base_date':   str(base_date),
                'target_date': str(target_date),
                'horizon':     horizon,
                'direction':   r[2],
                'probability': round(float(r[3]), 4),
                'model':       r[4],
            })

        return jsonify({'predictions': predictions}), 200

    except Exception as e:
        print(f'[/get-all-binary-predictions] {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/price-history', methods=['GET'])
def price_history():
    """
    최근 N일간의 실제 가격 히스토리 반환.
    Query param: days (기본 90)

    Response:
        {"history": [{"date": "YYYY-MM-DD", "price": 123.4, "special_price": 120.0}, ...]}
    """
    try:
        days = int(request.args.get('days', 90))
        days = max(10, min(days, 365))   # 10~365 범위 제한

        with _engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT date, price_standard, price_special
                FROM steel_prices
                WHERE price_standard IS NOT NULL
                ORDER BY date DESC
                LIMIT :lim
            """), {'lim': days}).fetchall()

        history = [
            {
                'date':          str(r[0]),
                'price':         round(float(r[1]), 2) if r[1] is not None else None,
                'special_price': round(float(r[2]), 2) if r[2] is not None else None,
            }
            for r in reversed(rows)   # 날짜 오름차순
        ]
        return jsonify({'history': history}), 200

    except Exception as e:
        print(f'[/price-history] {e}')
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    host  = os.getenv('FLASK_HOST',  '0.0.0.0')
    port  = int(os.getenv('FLASK_PORT', 5050))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug, threaded=False, host=host, port=port)

# import csv
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import joblib
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from datetime import timedelta
import json
import os
import requests
from datetime import datetime
from bs4 import BeautifulSoup as bs
from predict import process_all_versions
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException
)
from crawl import (crawl_feature_2, crawl_feature_8, crawl_feature_13, crawl_feature_15, crawl_feature_16,
                    crawl_feature_17, crawl_feature_18, crawl_feature_19, crawl_feature_20, crawl_feature_21,
                    crawl_feature_22, crawl_feature_24, crawl_feature_25, crawl_feature_26, crawl_feature_29,
                    crawl_feature_30, crawl_feature_31, crawl_feature_32, crawl_feature_33, crawl_feature_34,
                    crawl_feature_35, crawl_feature_36, crawl_feature_37, crawl_feature_38, crawl_feature_23,
                    crawl_feature_3, crawl_feature_4, crawl_feature_5, crawl_feature_6, crawl_feature_7, 
                    crawl_feature_10, crawl_feature_12) 

app = Flask(__name__)
CORS(app)

# 단가 예측 모델 설정
price_models_config = {
    "10": {
        "model_path": r'.\pickle\xgboost_model(2_10).pkl',
        "feature_path": r'.\features\train_features(2_10).csv',
        "window": 100,
        "horizon": 10,
        "model_key": "2_10"  # 모델 키 추가
    },
    "20": {
        "model_path": r'.\pickle\xgboost_model(2_20).pkl',
        "feature_path": r'.\features\train_features(2_20).csv',
        "window": 100,
        "horizon": 20,
        "model_key": "2_20"
    },
    "30": {
        "model_path": r'.\pickle\xgboost_model(2_30).pkl',
        "feature_path": r'.\features\train_features(2_30).csv',
        "window": 200,
        "horizon": 30,
        "model_key": "2_30"
    },
    "45": {
        "model_path": r'.\pickle\xgboost_model(2_45).pkl',
        "feature_path": r'.\features\train_features(2_45).csv',
        "window": 100,
        "horizon": 45,
        "model_key": "2_45"
    },
    "60": {
        "model_path": r'.\pickle\xgboost_model(2_60).pkl',
        "feature_path": r'.\features\train_features(2_60).csv',
        "window": 80,
        "horizon": 60,
        "model_key": "2_60"
    }
}

# 특별 구매 단가 예측 모델 설정
special_price_models_config = {
    "10": {
        "model_path": r'.\pickle\xgboost_model(4_10).pkl',
        "feature_path": r'.\features\train_features(4_10).csv',
        "window": 200,
        "horizon": 10,
        "model_key": "4_10"
    },
    "20": {
        "model_path": r'.\pickle\xgboost_model(4_20).pkl',
        "feature_path": r'.\features\train_features(4_20).csv',
        "window": 200,
        "horizon": 20,
        "model_key": "4_20"
    },
    "30": {
        "model_path": r'.\pickle\xgboost_model(4_30).pkl',
        "feature_path": r'.\features\train_features(4_30).csv',
        "window": 200,
        "horizon": 30,
        "model_key": "4_30"
    },
    "45": {
        "model_path": r'.\pickle\xgboost_model(4_45).pkl',
        "feature_path": r'.\features\train_features(4_45).csv',
        "window": 100,
        "horizon": 45,
        "model_key": "4_45"
    },
    "60": {
        "model_path": r'.\pickle\xgboost_model(4_60).pkl',
        "feature_path": r'.\features\train_features(4_60).csv',
        "window": 80,
        "horizon": 60,
        "model_key": "4_60"
    }
}

# 물동량 예측 모델 설정
volume_models_config = {
    "10": {
        "model_path": r'.\pickle\xgboost_model(3_10).pkl',
        "feature_path": r'.\features\train_features(3_10).csv',
        "window": 10,
        "horizon": 10,
    },
    "20": {
        "model_path": r'.\pickle\xgboost_model(3_20).pkl',
        "feature_path": r'.\features\train_features(3_20).csv',
        "window": 30,
        "horizon": 20,
    },
    "30": {
        "model_path": r'.\pickle\xgboost_model(3_30).pkl',
        "feature_path": r'.\features\train_features(3_30).csv',
        "window": 50,
        "horizon": 30,
    }
}

# 모델 및 피처 로드
def load_models_and_features(model_dict):
    models = {}
    features = {}
    for key, config in model_dict.items():
        models[key] = joblib.load(config["model_path"])  # 모델 로드
        features[key] = pd.read_csv(config["feature_path"])["Feature"].tolist()  # 피처 로드
    return models, features

price_models, price_features = load_models_and_features(price_models_config)
special_price_models, special_price_features = load_models_and_features(special_price_models_config)
volume_models, volume_features = load_models_and_features(volume_models_config)

# 데이터 로드
# file_path = r'.\data\data_2024_08_date.xlsx'
file_path = r'.\data\data_2024_11.xlsx'
special_file_path = r'.\data\data_2024_11_특.xlsx'

data = pd.read_excel(file_path)
special_data = pd.read_excel(special_file_path)

def preprocess_data(data):
    """
    데이터 전처리: 피처 이름을 학습된 모델과 일치시키도록 변환
    """
    data.columns = data.columns.str.replace(r'\s+', '_', regex=True)  # 공백 제거
    data.columns = data.columns.str.replace('_특', '_특', regex=False)  # '_특' 유지
    data.columns = data.columns.str.strip()  # 앞뒤 공백 제거
    data['일자'] = pd.to_datetime(data['일자'])
    data.set_index('일자', inplace=True)
    data.index = data.index.normalize()

preprocess_data(data)
preprocess_data(special_data)

# 새로운 전처리 로직
def preprocess_data_with_new_logic(data, window_size, diff_size):
    """
    새로운 전처리 로직:
    - 지수 이동 평균 적용
    - 차분 계산
    """
    ewm_data = data.ewm(span=window_size).mean()

    # 차분 계산
    diff_data = ewm_data.diff(diff_size)

    # 인덱스를 동기화
    diff_data.dropna(inplace=True)

    return diff_data

def seq2dataset(d_x, window):
    """
    시계열 데이터를 윈도우 단위로 변환 (예측 시에도 horizon을 포함)
    """
    X = []
    for i in range(len(d_x) - (window) + 1):
        x = d_x[i:(i + window)]
        X.append(x)
    return np.array(X)

def load_index_to_label(model_key):
    """
    모델 키에 해당하는 index_to_label JSON 파일을 로드합니다.
    """
    # 절대 경로 생성 (슬래시로 통일)
    base_path = r'.\labels'
    file_path = f"{base_path}/index_to_label({model_key}).json"
    # 경로 디버깅 출력
    # print(f"Attempting to load JSON file from: {file_path}")
    
    try:
        with open(file_path, "r") as f:
            index_to_label = json.load(f)
        return index_to_label
    except FileNotFoundError:
        # print(file_path)
        raise FileNotFoundError(f"Index-to-label JSON file not found for model key: {model_key} at path: {file_path}")
    
def predict_for_model(model, scaler_x, train_features, window, input_date, target_column, data_source, key, model_key=None):
    # 만약 target_column이 "입고량"인 경우 최신 데이터를 새로 읽고 인덱스를 '일자'로 설정
    if target_column == "입고량":
        file_path = r'.\data\data_2024_11.xlsx'
        data_source = pd.read_excel(file_path)
        # '일자' 컬럼을 DatetimeIndex로 변환
        data_source['일자'] = pd.to_datetime(data_source['일자'])
        data_source.set_index('일자', inplace=True)
        data_source.index = data_source.index.normalize()
    
    # 윈도우 범위 데이터 추출
    window_start_date = input_date - timedelta(days=window)
    window_data = data_source.loc[window_start_date:input_date]

    if len(window_data) < window:
        raise ValueError("Insufficient historical data")

    # 금일 값 가져오기 (단가 또는 물동량 등)
    try:
        current_price = data_source.loc[input_date, target_column]
    except KeyError:
        raise ValueError(f"No price data available for the date: {input_date}")

    # 피처 데이터 준비
    feature_data = window_data[train_features]
    processed_data = preprocess_data_with_new_logic(feature_data, window_size=1, diff_size=1)
    scaled_features = scaler_x[key].transform(processed_data)
    X_input = seq2dataset(scaled_features, window)
    input_data = X_input[-1].reshape(1, -1)

    # 예측 수행
    if model_key:
        index_to_label = load_index_to_label(model_key)
        predicted_index = int(model.predict(input_data)[0])
        if str(predicted_index) not in index_to_label:
            raise ValueError(f"Predicted index {predicted_index} not found in index_to_label mapping for model {model_key}")
        predicted_change = float(index_to_label[str(predicted_index)])
    else:
        predicted_change = float(model.predict(input_data)[0])

    predicted_value = current_price + predicted_change
    return predicted_value

# def predict_for_model(model, scaler_x, train_features, window, input_date, target_column, data_source, key, model_key=None):
#     # 만약 target_column이 "입고량"인 경우, 최신 데이터를 불러오도록 처리
#     if target_column == "입고량":
#         # 매 요청마다 최신 파일을 읽어오기 (파일 경로는 data 변수와 동일한 file_path)
#         file_path = r'.\data\data_2024_11.xlsx'
#         data_source = pd.read_excel(file_path)
#         # 만약 데이터 전처리가 필요하다면 여기에 추가 처리

#     # 윈도우 범위 데이터 추출
#     window_start_date = input_date - timedelta(days=window)
#     window_data = data_source.loc[window_start_date:input_date]

#     if len(window_data) < window:
#         raise ValueError("Insufficient historical data")

#     # 금일 값 가져오기
#     try:
#         current_price = data_source.loc[input_date, target_column]
#     except KeyError:
#         raise ValueError(f"No price data available for the date: {input_date}")

#     # 피처 데이터 준비
#     feature_data = window_data[train_features]
#     processed_data = preprocess_data_with_new_logic(feature_data, window_size=1, diff_size=1)

#     # 스케일러 변환
#     scaled_features = scaler_x[key].transform(processed_data)

#     # 입력 데이터 생성
#     X_input = seq2dataset(scaled_features, window)
#     input_data = X_input[-1].reshape(1, -1)

#     # 예측 수행
#     if model_key:
#         index_to_label = load_index_to_label(model_key)
#         predicted_index = int(model.predict(input_data)[0])
#         if str(predicted_index) not in index_to_label:
#             raise ValueError(f"Predicted index {predicted_index} not found in index_to_label mapping for model {model_key}")
#         predicted_change = float(index_to_label[str(predicted_index)])
#     else:
#         predicted_change = float(model.predict(input_data)[0])

#     predicted_price = current_price + predicted_change
#     return predicted_price

# def predict_for_model(model, scaler_x, train_features, window, input_date, target_column, data_source, key, model_key=None):
#     """
#     특정 모델에 대해 새로운 전처리 로직 기반으로 예측 수행
#     """
#     # 윈도우 범위 데이터 추출
#     window_start_date = input_date - timedelta(days=window)
#     window_data = data_source.loc[window_start_date:input_date]

#     if len(window_data) < window:
#         raise ValueError("Insufficient historical data")

#     # 금일 값 가져오기 (단가 또는 물동량 등)
#     try:
#         current_price = data_source.loc[input_date, target_column]
#     except KeyError:
#         raise ValueError(f"No price data available for the date: {input_date}")

#     # 피처 데이터 준비
#     feature_data = window_data[train_features]
#     processed_data = preprocess_data_with_new_logic(feature_data, window_size=1, diff_size=1)

#     # 특정 키에 해당하는 스케일러 사용
#     scaled_features = scaler_x[key].transform(processed_data)

#     # 입력 데이터 생성
#     X_input = seq2dataset(scaled_features, window)
#     input_data = X_input[-1].reshape(1, -1)

#     # 예측 수행
#     if model_key:
#         # 라벨링된 변화량 매핑
#         index_to_label = load_index_to_label(model_key)
#         predicted_index = int(model.predict(input_data)[0])
#         if str(predicted_index) not in index_to_label:
#             raise ValueError(f"Predicted index {predicted_index} not found in index_to_label mapping for model {model_key}")

#         predicted_change = float(index_to_label[str(predicted_index)])
#     else:
#         # 물동량 모델의 경우
#         predicted_change = float(model.predict(input_data)[0])

#     # 최종 가격 계산
#     predicted_price = current_price + predicted_change

#     return predicted_price

# 스케일러 설정
scaler_x_price = {}
scaler_x_special = {}
# ?
scaler_x_volume ={}

# 단가 예측 스케일러 설정
for key in price_models_config.keys():
    if key == "10":
        window_size, diff_size = 60, 200
    elif key == "20":
        window_size, diff_size = 50, 200
    elif key == "30":
        window_size, diff_size = 5, 200
    elif key == "45":
        window_size, diff_size = 30, 40
    elif key == "60":
        window_size, diff_size = 30, 40

    scaler_x_price[key] = StandardScaler().fit(
        preprocess_data_with_new_logic(data[price_features[key]], window_size=window_size, diff_size=diff_size)
    )

    # 특별 구매 단가 예측 스케일러 설정
for key in special_price_models_config.keys():
    if key == "10":
        window_size, diff_size = 50, 80
    elif key == "20":
        window_size, diff_size = 50, 200
    elif key == "30":
        window_size, diff_size = 40, 100
    elif key == "45":
        window_size, diff_size = 40, 70
    elif key == "60":
        window_size, diff_size = 30, 10

    scaler_x_special[key] = StandardScaler().fit(
        preprocess_data_with_new_logic(special_data[special_price_features[key]], window_size=window_size, diff_size=diff_size)
    )

for key in volume_models_config.keys():
    # key에 따라 window_size와 diff_size 설정
    if key == "10":
        window_size, diff_size = 5, 1
    elif key == "20":
        window_size, diff_size = 5, 1
    elif key == "30":
        window_size, diff_size = 5, 1

    # 스케일러 생성 및 저장
    scaler_x_volume[key] = StandardScaler().fit(
        preprocess_data_with_new_logic(data[volume_features[key]], window_size=window_size, diff_size=diff_size)
    )
@app.route("/transfer-predict", methods=["POST"])
def transfer_prediction():
    try:
        received_data = request.get_json()
        print("Received data:", received_data)  # 요청 데이터 확인

        selected_date = received_data.get('date')
        if not selected_date:
            print("No date provided.")  # 날짜가 없을 경우 디버깅 출력
            return jsonify({"error": "No date provided"}), 400

        input_date = pd.to_datetime(selected_date).normalize()
        print("Normalized input date:", input_date)  # 변환된 날짜 확인

        # 예측 결과 저장
        predictions = {
            "price": {},
            "special_price": {},
            "volume": {}
        }

        # 단가 예측
        try:
            predictions["price"] = {
                key: predict_for_model(
                    model=price_models[key],
                    scaler_x=scaler_x_price,
                    train_features=price_features[key],
                    window=price_models_config[key]["window"],
                    input_date=input_date,
                    target_column="중A",
                    data_source=data,
                    key=key,
                    model_key=price_models_config[key]["model_key"]
                ) for key in price_models
            }
            print("Price predictions:", predictions["price"])  # 단가 예측 확인
        except Exception as e:
            print("Error in price prediction:", str(e))

        # 특단가 예측
        try:
            predictions["special_price"] = {}
            for key in special_price_models:
                # 입력 데이터 크기 확인
                input_features = predict_for_model(
                    model=special_price_models[key],
                    scaler_x=scaler_x_special,
                    train_features=special_price_features[key],
                    window=special_price_models_config[key]["window"],
                    input_date=input_date,
                    target_column="중A_특",
                    data_source=special_data,
                    key=key,
                    model_key=special_price_models_config[key]["model_key"]
                    )
                print(f"Special price input feature size for {key}: {len(input_features)}")  # 피처 크기 확인
                predictions["special_price"][key] = input_features
            print("Special price predictions:", predictions["special_price"])  # 특단가 예측 확인
        except Exception as e:
            print(f"Error in special price prediction for {key}: {str(e)}")

        # 물동량 예측
        try:
            predictions["volume"] = {
                key: predict_for_model(
                    model=volume_models[key],
                    scaler_x=scaler_x_volume,
                    train_features=volume_features[key],
                    window=volume_models_config[key]["window"],
                    input_date=input_date,
                    target_column="입고량",
                    data_source=data,
                    key=key
                ) for key in volume_models
            }
            print("Volume predictions:", predictions["volume"])  # 물동량 예측 확인
        except Exception as e:
            print("Error in volume prediction:", str(e))

        # `predicted_price`만 반환
        response_data = {
            "price": predictions["price"],
            "special_price": predictions["special_price"],
            "volume": predictions["volume"]
        }
        print("Response data:", response_data)  # 최종 응답 데이터 확인
        return jsonify(response_data)

    except ValueError as ve:
        print("ValueError occurred:", str(ve))
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        print("Error occurred:", str(e))
        return jsonify({"error": str(e)}), 500

EXCEL_FILES_DIR = r'.\excel'
@app.route("/get-chart-data", methods=["POST"])
def get_chart_data():
    try:
        # 클라이언트에서 전달받은 파일명
        data = request.get_json()
        print(f"Received data: {data}")  # 디버깅 출력
        file_name = data.get("file_name")

        if not file_name:
            return jsonify({"error": "No file_name provided"}), 400

        # 엑셀 파일 경로
        file_path = os.path.join(EXCEL_FILES_DIR, f"{file_name}.xlsx")

        if not os.path.exists(file_path):
            return jsonify({"error": f"File {file_name}.xlsx not found"}), 404

        # 엑셀 파일 읽기
        df = pd.read_excel(file_path)

        if "true" not in df.columns or "pred" not in df.columns:
            return jsonify({"error": f"File {file_name}.xlsx does not contain required columns ('true', 'pred')"}), 400

        # 데이터를 JSON 형식으로 반환
        return jsonify({
            "true": df["true"].tolist(),
            "pred": df["pred"].tolist()
        })

    except Exception as e:
        print(f"Error: {str(e)}")  # 디버깅 출력
        return jsonify({"error": str(e)}), 500
    

EXCEL_FILES_DIR2 = r'.\excel2'

def load_model_predictions(model_key, selected_date):
    """
    주어진 모델 키와 날짜에 해당하는 엑셀 데이터를 로드하고,
    선택된 날짜를 기준으로 목표 날짜 데이터를 반환합니다.

    Args:
        model_key (str): 모델 키 (예: "2_10", "4_20").
        selected_date (str): 선택된 기준 날짜 (YYYY-MM-DD 형식).

    Returns:
        dict: 목표 날짜와 예측값이 포함된 딕셔너리.
    """
    file_path = os.path.join(EXCEL_FILES_DIR2, f"{model_key}.xlsx")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Excel file for model {model_key} not found at {file_path}")
    
    # 엑셀 데이터 로드
    df = pd.read_excel(file_path)
    
    # 데이터 검증
    if "pred" not in df.columns or "일자" not in df.columns:
        raise ValueError(f"Excel file for model {model_key} does not contain required columns 'pred' or '일자'")
    
    # 선택된 날짜와 모델 키 기반 목표 날짜 계산
    selected_date = pd.to_datetime(selected_date)  # 선택 날짜를 datetime 형식으로 변환
    days_ahead = int(model_key.split("_")[1])  # 모델 키에서 예측 일수를 추출 (예: "2_10" → 10)
    target_date = selected_date + pd.Timedelta(days=days_ahead)  # 목표 날짜 계산

    # 목표 날짜에 해당하는 데이터 필터링
    pred_row = df[df["일자"] == target_date]

    if pred_row.empty:
        raise ValueError(f"No data found for the target date {target_date.date()} in model {model_key}")

    # 목표 날짜와 예측값 반환
    pred_value = pred_row["pred"].iloc[0]
    return {"date": target_date.strftime("%Y-%m-%d"), "pred": int(pred_value)}

DATA_FILE = r'.\data\data_2024_11.xlsx'         # 기본데이터+기본단가 저장용
DATA_FILE_SPECIAL = r'.\data\data_2024_11_특.xlsx'  # 기본데이터+특별구매단가 저장용

@app.route('/download-data-file', methods=['GET'])
def download_data_file():
    """
    기본 데이터 파일 (DATA_FILE)을 다운로드합니다.
    """
    try:
        if os.path.exists(DATA_FILE):
            return send_file(
                DATA_FILE,
                as_attachment=True,
                download_name='data_2024_11.xlsx'  # 파일 이름 설정
            )
        else:
            return jsonify({"error": "Data file not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/download-special-data-file', methods=['GET'])
def download_special_data_file():
    """
    특구가 데이터 파일 (DATA_FILE_SPECIAL)을 다운로드합니다.
    """
    try:
        if os.path.exists(DATA_FILE_SPECIAL):
            return send_file(
                DATA_FILE_SPECIAL,
                as_attachment=True,
                download_name='data_2024_11_특.xlsx'  # 파일 이름 설정
            )
        else:
            return jsonify({"error": "Special data file not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-recent-data', methods=['GET'])
def get_recent_data():
    try:
        # 데이터 불러오기
        price_data = pd.read_excel(DATA_FILE, engine='openpyxl')
        special_price_data = pd.read_excel(DATA_FILE_SPECIAL, engine='openpyxl')

        # 날짜 정렬 후 최근 5일 데이터 선택
        price_data['일자'] = pd.to_datetime(price_data['일자'])
        special_price_data['일자'] = pd.to_datetime(special_price_data['일자'])

        price_data = price_data.sort_values(by='일자', ascending=False).head(5)
        special_price_data = special_price_data.sort_values(by='일자', ascending=False).head(5)

        # 데이터 병합
        recent_data = pd.merge(price_data, special_price_data, on='일자', how='outer')

        # 열 이름 간소화
        recent_data.rename(columns={
            '중A': '중A',
            '중A_특': '중A_특',
            '입고량_x': '입고량',
            '재고량_x': '재고량',
            '입고율_x': '입고율',
            '제강생산량_x': '제강생산량',
            '고철투입량_x': '고철투입량',

        }, inplace=True)

        # NaN을 '-'로 대체
        recent_data.fillna('-', inplace=True)

        # JSON 반환
        return jsonify({"recent": recent_data.to_dict(orient='records')}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

    
def save_or_update_excel(new_data):
    # 기존 데이터 로드
    if os.path.exists(DATA_FILE):
        existing_data = pd.read_excel(DATA_FILE, engine='openpyxl')
    else:
        existing_data = pd.DataFrame()

    # '일자'가 없는 경우 대비
    if '일자' not in new_data.columns:
        # '일자' 없는 데이터라면 처리 불가하거나, 에러 반환
        # 여기서는 단순 에러 처리
        print("New data has no '일자' column")
        return DATA_FILE

    # 일자를 datetime으로 변환해 정렬 및 중복 제거 (원한다면)
    # 단순히 merge 전에 일자를 datetime으로 통일
    existing_data['일자'] = pd.to_datetime(existing_data['일자'], errors='coerce')
    new_data['일자'] = pd.to_datetime(new_data['일자'], errors='coerce')

    # '일자' 기준으로 outer join
    # suffixes를 통해 기존 데이터와 new_data에서 같은 컬럼이 있을 때 구분할 수 있음
    merged = pd.merge(existing_data, new_data, on='일자', how='outer', suffixes=('_old', '_new'))

    # 이제 merged에는 기존데이터 + 새데이터가 '일자' 기준으로 합쳐져있음
    # old/new로 분리된 컬럼명을 처리해야 함.
    # 방법 1: 특정 컬럼만 업데이트하고 싶다면, new_data에 있는 컬럼만 별도로 처리.

    # 예를 들어 new_data의 컬럼 목록을 가져와서(old/new 구분 전)
    new_cols = [c for c in new_data.columns if c != '일자']

    # 각 new_cols에 대해:
    # - merged에 c_new와 c_old 컬럼이 있을 것
    # - c_new가 우선순위, c_new가 NaN이면 c_old값 유지
    # - c_new가 존재하는데 c_old만 있거나 둘다 있으면 c_new값이 우선
    for c in new_cols:
        c_new = c + '_new'
        c_old = c + '_old'
        if c_new in merged.columns and c_old in merged.columns:
            # new 값이 있으면 그 값 사용, 없으면 old 값
            merged[c] = merged[c_new].combine_first(merged[c_old])
            merged.drop(columns=[c_old, c_new], inplace=True)
        elif c_new in merged.columns:
            # 기존 데이터에 없는 새로운 컬럼일 경우
            merged.rename(columns={c_new: c}, inplace=True)
        elif c_old in merged.columns:
            # 새로운 데이터에 해당 컬럼이 없으면 그냥 old 유지
            merged.rename(columns={c_old: c}, inplace=True)

    # new_data에 없는 컬럼(기존 데이터에만 있는 컬럼)은 old suffix로 남아있을 수 있으므로 처리
    for c in merged.columns:
        if c.endswith('_old') and c[:-4] not in merged.columns:
            merged.rename(columns={c: c[:-4]}, inplace=True)

    merged = merged.copy()

    # 일자 정렬 (원하면)
    merged.sort_values(by='일자', inplace=True)

    # 엑셀로 저장
    merged.to_excel(DATA_FILE, index=False, engine='openpyxl')
    return DATA_FILE



def save_or_update_excel_special(new_data):
    if os.path.exists(DATA_FILE_SPECIAL):
        existing_data = pd.read_excel(DATA_FILE_SPECIAL, engine='openpyxl')
    else:
        existing_data = pd.DataFrame()

    # '일자' 컬럼 검사
    if '일자' not in new_data.columns:
        print("New data has no '일자' column")
        return DATA_FILE_SPECIAL

    # 일자 형식 통일
    existing_data['일자'] = pd.to_datetime(existing_data['일자'], errors='coerce')
    new_data['일자'] = pd.to_datetime(new_data['일자'], errors='coerce')

    # 일자 기준 outer merge
    merged = pd.merge(existing_data, new_data, on='일자', how='outer', suffixes=('_old', '_new'))

    # new_data에 있는 컬럼 목록 추출 (일자 제외)
    new_cols = [c for c in new_data.columns if c != '일자']

    # 컬럼 업데이트 로직
    for c in new_cols:
        c_new = c + '_new'
        c_old = c + '_old'
        if c_new in merged.columns and c_old in merged.columns:
            # 새 데이터가 있는 경우 c_new 우선 적용
            # c_new가 NaN이면 c_old 유지
            merged[c] = merged[c_new].combine_first(merged[c_old])
            merged.drop(columns=[c_old, c_new], inplace=True)
        elif c_new in merged.columns:
            # 기존에 없던 컬럼이 새로 추가된 경우
            merged.rename(columns={c_new: c}, inplace=True)
        elif c_old in merged.columns:
            # 새 데이터에 해당 컬럼이 없고, 기존에만 있던 컬럼 유지
            merged.rename(columns={c_old: c}, inplace=True)

    # 여전히 '_old'가 남아있는 컬럼 처리 (new_data에 없는 기존 컬럼)
    for c in merged.columns:
        if c.endswith('_old') and c[:-4] not in merged.columns:
            merged.rename(columns={c: c[:-4]}, inplace=True)

    # 필요하다면 일자 정렬
    # merged.sort_values(by='일자', inplace=True)

    merged.to_excel(DATA_FILE_SPECIAL, index=False, engine='openpyxl')
    return DATA_FILE_SPECIAL


@app.route('/save-data', methods=['POST'])
def save_data():
    try:
        data = request.json
        print("Received data:", data)  # 디버깅용 출력

        # 숫자형으로 변환
        입고량 = float(data.get("입고량", 0))  # 기본값 0
        재고량 = float(data.get("재고량", 0))
        제강생산량 = float(data.get("제강생산량", 0))
        고철투입량 = float(data.get("고철투입량", 0))
        중A = int(float(data.get("중A", 0))) if data.get("중A") else None  # 정수형 변환
        중A_특 = int(float(data.get("중A_특", 0))) if data.get("중A_특") else None  # 정수형 변환
        일자 = data.get("일자", "")

        # 입고율 계산 (입고량 / 고철투입량)
        if 고철투입량 != 0:
            입고율 = 입고량 / 고철투입량
        else:
            입고율 = None  # 고철투입량이 0이면 None 처리

        # 새로운 데이터 생성
        new_data = {
            "일자": pd.to_datetime(일자).strftime("%Y-%m-%d %I:%M:%S %p"),  # 원하는 형식으로 변환
            "중A": 중A,
            "중A_특": 중A_특,
            "입고량": 입고량,
            "재고량": 재고량,
            "입고율": round(입고율, 2) if 입고율 is not None else None,  # 소수점 2자리로 반올림
            "제강생산량": 제강생산량,
            "고철투입량": 고철투입량
        }
        df_new = pd.DataFrame([new_data])

        # 1. DATA_FILE에 저장 (중A_특 제외)
        # 1. DATA_FILE에 저장 (중A_특 제외)
        df_for_data_file = df_new.drop(columns=["중A_특"])
        if os.path.exists(DATA_FILE):
            df_existing = pd.read_excel(DATA_FILE, engine='openpyxl')
            
            # 일자를 datetime 형식으로 변환
            df_existing["일자"] = pd.to_datetime(df_existing["일자"])
            new_data["일자"] = pd.to_datetime(new_data["일자"])
            
            # 동일한 "일자"가 있으면 업데이트
            if new_data["일자"] in df_existing["일자"].values:
                # 조건에 맞는 행을 업데이트
                df_existing.loc[df_existing["일자"] == new_data["일자"], df_for_data_file.columns] = df_for_data_file.values[0]
            else:
                # 없으면 새로 추가
                df_existing = pd.concat([df_existing, df_for_data_file], ignore_index=True)
        else:
            # 파일이 없으면 새로 생성
            df_existing = df_for_data_file

        df_existing.to_excel(DATA_FILE, index=False, engine='openpyxl')

        # 2. DATA_FILE_SPECIAL에 저장 (중A 제외)
        df_for_data_file_special = df_new.drop(columns=["중A"])
        if os.path.exists(DATA_FILE_SPECIAL):
            df_existing_special = pd.read_excel(DATA_FILE_SPECIAL, engine='openpyxl')
            
            # 일자를 datetime 형식으로 변환
            df_existing_special["일자"] = pd.to_datetime(df_existing_special["일자"])
            new_data["일자"] = pd.to_datetime(new_data["일자"])
            
            # 동일한 "일자"가 있으면 업데이트
            if new_data["일자"] in df_existing_special["일자"].values:
                # 조건에 맞는 행을 업데이트
                df_existing_special.loc[df_existing_special["일자"] == new_data["일자"], df_for_data_file_special.columns] = df_for_data_file_special.values[0]
            else:
                # 없으면 새로 추가
                df_existing_special = pd.concat([df_existing_special, df_for_data_file_special], ignore_index=True)
        else:
            # 파일이 없으면 새로 생성
            df_existing_special = df_for_data_file_special

        df_existing_special.to_excel(DATA_FILE_SPECIAL, index=False, engine='openpyxl')

        return jsonify({"message": "Data saved successfully!"}), 200


    except Exception as e:
        print("Error saving data:", str(e))
        return jsonify({"error": str(e)}), 500

TIME_FILE = 'time.txt'
# 데이터 추가 페이지 업데이트 일자 라우트
@app.route('/save-time', methods=['POST'])
def save_time():
    now = datetime.now().strftime('%Y-%m-%d')
    with open(TIME_FILE, 'w') as f:
        f.write(now)
    return jsonify({'status': 'saved', 'date': now})

@app.route('/get-time', methods=['GET'])
def get_time():
    if os.path.exists(TIME_FILE):
        with open(TIME_FILE, 'r') as f:
            saved_time = f.read().strip()
        return jsonify({'lastUpdate': saved_time})
    else:
        return jsonify({'lastUpdate': '-'})
# 해당까지

@app.route('/run-crawling', methods=['POST'])
def run_crawling():
    try:
        request_data = request.get_json()
        start_date = request_data.get('start_date', '20240101')
        end_date = request_data.get('end_date', '20250124')

        start_month = start_date[:6]
        end_month = end_date[:6]

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'}
      
        data_2 = crawl_feature_2(start_date, end_date)
        data_3 = crawl_feature_3(start_date, end_date)
        data_4 = crawl_feature_4(start_date, end_date)
        # data_5 = crawl_feature_5(start_date, end_date)
        data_6 = crawl_feature_6(start_date, end_date)
        data_7 = crawl_feature_7(start_date, end_date)
        data_8 = crawl_feature_8(start_date, end_date, headers)
        data_10 = crawl_feature_10(start_date, end_date)
        data_12 = crawl_feature_12(start_date, end_date)
        data_13 = crawl_feature_13(start_month, end_month)
        data_15 = crawl_feature_15(headers)
        data_16 = crawl_feature_16(headers)
        data_17 = crawl_feature_17(headers)
        data_18 = crawl_feature_18(headers)
        data_19 = crawl_feature_19(headers)
        data_20 = crawl_feature_20(headers)
        data_21 = crawl_feature_21(headers)
        data_22 = crawl_feature_22(start_date, end_date)
        # data_23 = crawl_feature_23(start_date)
        data_24 = crawl_feature_24(headers)
        data_25 = crawl_feature_25(headers)
        data_26 = crawl_feature_26(headers)
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

        data_frame = [data_2, data_3, data_4, data_6, data_7, data_8, data_10, data_12, 
                    data_13, data_15, data_16, data_17, data_18, data_19, data_20, data_21, 
                    data_22, data_24, data_25, data_26, data_29, data_30, data_31, data_32, 
                    data_33, data_34, data_35, data_36, data_37, data_38]
        valid_data_frames = [df for df in data_frame if not df.empty]
        
        if not valid_data_frames:
            return jsonify({"error": "No valid data found for the given date range."}), 404

        for idx, df in enumerate(valid_data_frames):
            if '일자' not in df.columns:
                print(f"Dataframe at index {idx} does not have '일자' column: {df.columns}")
                return jsonify({"error": "A dataframe is missing '일자' column."}), 500

        combined_data = pd.concat(valid_data_frames, ignore_index=True)

        if '일자' not in combined_data.columns:
            print("No '일자' column in combined_data after merging.")
            return jsonify({"error": "No '일자' column found in merged data."}), 500

        for column in combined_data.columns:
            if column != '일자':
                combined_data[column] = pd.to_numeric(combined_data[column], errors='coerce')

        combined_data = combined_data.groupby('일자', as_index=False).agg(lambda x: x.dropna().iloc[0] if x.dropna().size > 0 else None)

        # 크롤링 결과를 두 파일에 동일하게 저장
        combined_data.to_excel('sampl.xlsx', index=False, engine='openpyxl')
        saved_file_basic = save_or_update_excel(combined_data)          # data_2024_11.xlsx에 저장
        saved_file_special = save_or_update_excel_special(combined_data) # data_2024_11_특.xlsx에 저장

        return jsonify({
            "message": "Crawling and saving completed successfully!",
            "saved_files": [saved_file_basic, saved_file_special]
        }), 200
    except Exception as e:
        print(f"Error during crawling: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/interpolate-data', methods=['POST'])
def interpolate_data():
    """
    input_data.xlsx와 input_data_특.xlsx를 읽어서 '일자' 기준 전체 날짜 범위를 재구성하고
    결측값을 보간(interpolation)한 뒤, 단가(중A) 또는 특별구매단가(중A_특)가 있다면
    해당 컬럼을 5단위 정수값으로 반올림 처리.
    """
    try:
        # input_data.xlsx 처리
        if os.path.exists(DATA_FILE):
            df = pd.read_excel(DATA_FILE, engine='openpyxl')
            if '일자' in df.columns and not df.empty:
                df['일자'] = pd.to_datetime(df['일자'], errors='coerce')
                df.dropna(subset=['일자'], inplace=True)
                # 중복 제거
                df.drop_duplicates(subset=['일자'], keep='last', inplace=True)

                full_range = pd.date_range(df['일자'].min(), df['일자'].max(), freq='D')
                # 인덱스 설정 후 중복 인덱스 제거
                df = df.set_index('일자')
                df = df[~df.index.duplicated(keep='last')]
                df = df.reindex(full_range)

                numeric_cols = df.select_dtypes(include=[float,int]).columns
                df[numeric_cols] = df[numeric_cols].interpolate(method='time')
                df = df.reset_index().rename(columns={'index':'일자'})

                # 중A 컬럼이 있으면 5단위로 반올림
                if '중A' in df.columns:
                    df['중A'] = df['중A'].apply(lambda x: 5*round(x/5))

                df.to_excel(DATA_FILE, index=False, engine='openpyxl')

        # input_data_특.xlsx 처리
        if os.path.exists(DATA_FILE_SPECIAL):
            df_special = pd.read_excel(DATA_FILE_SPECIAL, engine='openpyxl')
            if '일자' in df_special.columns and not df_special.empty:
                df_special['일자'] = pd.to_datetime(df_special['일자'], errors='coerce')
                df_special.dropna(subset=['일자'], inplace=True)
                # 중복 제거
                df_special.drop_duplicates(subset=['일자'], keep='last', inplace=True)

                full_range_sp = pd.date_range(df_special['일자'].min(), df_special['일자'].max(), freq='D')
                df_special = df_special.set_index('일자')
                df_special = df_special[~df_special.index.duplicated(keep='last')]
                df_special = df_special.reindex(full_range_sp)

                numeric_cols_sp = df_special.select_dtypes(include=[float,int]).columns
                df_special[numeric_cols_sp] = df_special[numeric_cols_sp].interpolate(method='time')
                df_special = df_special.reset_index().rename(columns={'index':'일자'})

                # 중A_특 컬럼이 있으면 5단위로 반올림
                if '중A_특' in df_special.columns:
                    df_special['중A_특'] = df_special['중A_특'].apply(lambda x: 5*round(x/5))

                df_special.to_excel(DATA_FILE_SPECIAL, index=False, engine='openpyxl')

        return jsonify({"message": "Interpolation completed successfully!"}), 200
    except Exception as e:
        print("Error during interpolation:", e)
        return jsonify({"error": str(e)}), 500
    
@app.route('/run-all-versions', methods=['POST'])
def run_all_versions_endpoint():
    try:
        process_all_versions()  # 모든 버전을 처리
        return jsonify({"message": "All versions processed successfully!"}), 200
    except Exception as e:
        print("Error during all versions processing:", e)
        return jsonify({"error": str(e)}), 500

# Flask API
@app.route("/get-model-prediction", methods=["POST"])
def get_model_prediction():
    """
    특정 모델 키와 날짜에 해당하는 pred 값을 반환합니다.
    """
    try:
        # 클라이언트 요청 데이터 받기
        data = request.get_json()
        model_key = data.get("model_key")
        selected_date = data.get("date")

        if not model_key:
            return jsonify({"error": "No model_key provided"}), 400
        if not selected_date:
            return jsonify({"error": "No date provided"}), 400

        # 모델 데이터 로드 및 목표 날짜 예측값 가져오기
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
        # 요청에서 날짜 받기
        request_data = request.get_json()
        target_date = request_data.get("date")

        if not target_date:
            return jsonify({"error": "No date provided"}), 400

        # 날짜를 Datetime 형식으로 변환
        target_date = pd.to_datetime(target_date).normalize()

        # 파일 경로 설정
        file_path = r'.\data\data_2024_11.xlsx'
        special_file_path = r'.\data\data_2024_11_특.xlsx'

        # 엑셀 파일 읽기
        data = pd.read_excel(file_path)
        special_data = pd.read_excel(special_file_path)

        # 데이터 전처리
        data['일자'] = pd.to_datetime(data['일자']).dt.normalize()
        special_data['일자'] = pd.to_datetime(special_data['일자']).dt.normalize()

        # 날짜를 기준으로 데이터 필터링
        target_data = data[data['일자'] == target_date]
        target_special_data = special_data[special_data['일자'] == target_date]

        # 필터링된 데이터가 비어 있을 경우
        if target_data.empty or target_special_data.empty:
            print(f"No data found for the date: {target_date}")  # 디버깅용
            return jsonify({
                "price": "N/A",
                "special_price": "N/A",
                "volume": "N/A"
            }), 200

        # 단가 및 물동량 데이터 추출
        price = target_data['중A'].iloc[0]
        special_price = target_special_data['중A_특'].iloc[0]
        volume = target_data['입고량'].iloc[0]

        # 결과 반환
        return jsonify({
            "price": f"{price} 원",
            "special_price": f"{special_price} 원",
            "volume": f"{volume} kg"
        }), 200

    except Exception as e:
        print(f"Error in /get-dashboard-data: {str(e)}")  # 에러 로그
        return jsonify({"error": str(e)}), 500

@app.route('/get-last-date', methods=['GET'])
def get_last_date():
    try:
        # 엑셀 파일에서 데이터 로드
        if os.path.exists(DATA_FILE):
            data = pd.read_excel(DATA_FILE, engine='openpyxl')
            # '일자' 컬럼을 datetime 형식으로 변환
            data['일자'] = pd.to_datetime(data['일자'], errors='coerce')
            # 마지막 날짜 찾기
            last_date = data['일자'].max()
            if pd.isnull(last_date):
                return jsonify({"error": "No valid dates found."}), 404
            return jsonify({"last_date": last_date.strftime('%Y-%m-%d')}), 200
        else:
            return jsonify({"error": "Data file not found."}), 404
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=False, threaded=False, host='203.253.181.161', port=5050)




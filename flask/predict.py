import pandas as pd
import numpy as np
import joblib
import pickle
import os

DATA_FILE = r'.\data\data_2024_11.xlsx'          # 2_**용 기본파일
DATA_FILE_SPECIAL = r'.\data\data_2024_11_특.xlsx'  # 4_**용 기본파일

def save_or_update_excel(new_data, output_file):
    if os.path.exists(output_file):
        existing_data = pd.read_excel(output_file, engine='openpyxl')
    else:
        existing_data = pd.DataFrame()

    if '일자' not in new_data.columns:
        print("New data has no '일자' column.")
        return output_file

    existing_data['일자'] = pd.to_datetime(existing_data['일자'], errors='coerce')
    new_data['일자'] = pd.to_datetime(new_data['일자'], errors='coerce')

    merged = pd.merge(existing_data, new_data, on='일자', how='outer', suffixes=('_old', '_new'))

    new_cols = [c for c in new_data.columns if c != '일자']
    for c in new_cols:
        c_new = c + '_new'
        c_old = c + '_old'
        if c_new in merged.columns and c_old in merged.columns:
            merged[c] = merged[c_new].combine_first(merged[c_old])
            merged.drop(columns=[c_old, c_new], inplace=True)
        elif c_new in merged.columns:
            merged.rename(columns={c_new: c}, inplace=True)
        elif c_old in merged.columns:
            merged.rename(columns={c_old: c}, inplace=True)

    for c in merged.columns:
        if c.endswith('_old') and c[:-4] not in merged.columns:
            merged.rename(columns={c: c[:-4]}, inplace=True)

    merged.sort_values(by='일자', inplace=True)

    merged.to_excel(output_file, index=False, engine='openpyxl')
    return output_file


def compare_and_update_special_price(price_version, special_price_version, new_dates):
    """
    특정 날짜에 대해 단가와 특구가 예측 데이터를 비교하여 특구가가 단가보다 낮은 경우 업데이트.

    Args:
        price_version (str): 단가 모델 키 (예: "2_10").
        special_price_version (str): 특구가 모델 키 (예: "4_10").
        new_dates (list): 업데이트 날짜 리스트.
    """
    price_file_path = os.path.join('excel2', f"{price_version}.xlsx")
    special_price_file_path = os.path.join('excel2', f"{special_price_version}.xlsx")

    if not os.path.exists(price_file_path) or not os.path.exists(special_price_file_path):
        print(f"File not found for {price_version} or {special_price_version}")
        return

    price_df = pd.read_excel(price_file_path)
    special_price_df = pd.read_excel(special_price_file_path)

    # '일자'와 'pred' 컬럼이 있는지 확인
    if '일자' not in price_df.columns or 'pred' not in price_df.columns:
        print(f"'일자' or 'pred' column missing in {price_file_path}")
        return
    if '일자' not in special_price_df.columns or 'pred' not in special_price_df.columns:
        print(f"'일자' or 'pred' column missing in {special_price_file_path}")
        return

    # 날짜 기준으로 병합
    price_df['일자'] = pd.to_datetime(price_df['일자'])
    special_price_df['일자'] = pd.to_datetime(special_price_df['일자'])
    merged = pd.merge(price_df, special_price_df, on='일자', suffixes=('_price', '_special'))

    # 새로 추가된 날짜 데이터 필터링
    merged_new = merged[merged['일자'].isin(new_dates)]

    if merged_new.empty:
        print(f"No new data to update for {special_price_version}")
        return

    # 특구가가 단가보다 낮은 경우 업데이트
    special_price_updated = merged_new['pred_special'] < merged_new['pred_price']
    merged_new.loc[special_price_updated, 'pred_special'] = merged_new.loc[special_price_updated, 'pred_price']

    # 업데이트된 특구가 저장
    updated_special_price_df = merged_new[['일자', 'pred_special']].rename(columns={'pred_special': 'pred'})
    save_or_update_excel(updated_special_price_df, special_price_file_path)

    print(f"Updated special prices for {special_price_version} on new dates only.")

def process_version(version):
    version_params = {
        "2_10": {"w": 100, "h": 10, "window_size": 60, "diff_size": 200},
        "2_20": {"w": 100, "h": 20, "window_size": 50, "diff_size": 200},
        "2_30": {"w": 200, "h": 30, "window_size": 5, "diff_size": 200},
        "2_45": {"w": 100, "h": 45, "window_size": 30, "diff_size": 40},
        "2_60": {"w": 80,  "h": 60, "window_size": 30, "diff_size": 40},
        "4_10": {"w": 200, "h": 10, "window_size": 50, "diff_size": 80},
        "4_20": {"w": 200, "h": 20, "window_size": 50, "diff_size": 200},
        "4_30": {"w": 200, "h": 30, "window_size": 40, "diff_size": 100},
        "4_45": {"w": 100, "h": 45, "window_size": 40, "diff_size": 70},
        "4_60": {"w": 80,  "h": 60, "window_size": 30, "diff_size": 10}
    }

    params = version_params.get(version, {"w": 100, "h": 10, "window_size": 60, "diff_size": 200})
    w = params["w"]
    h = params["h"]
    window_size = params["window_size"]
    diff_size = params["diff_size"]

    if version.startswith('2_'):
        file_path = DATA_FILE
        target_col = '중A'
    else:
        file_path = DATA_FILE_SPECIAL
        target_col = '중A_특'

    # 먼저 data 로드
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Data file not found: {file_path}")

    data = pd.read_excel(file_path)
    if data.empty:
        raise ValueError(f"Data is empty for version {version}")

    # train_features 로드 및 컬럼 재정렬
    print(f"Loading train features for version: {version}")
    train_features_path = f'features/train_features({version}).csv'
    if not os.path.exists(train_features_path):
        raise FileNotFoundError(f"Train features file not found for version: {version}")

    train_df = pd.read_csv(train_features_path)
    train_features_list = train_df['Feature'].tolist()
    print("Train features list loaded:", train_features_list)

    # target_col과 일자 컬럼이 데이터에 존재하는지 체크
    if '일자' not in data.columns:
        raise ValueError(f"'일자' column not found in {file_path} for version {version}")
    if target_col not in data.columns:
        raise ValueError(f"'{target_col}' column not found in {file_path} for version {version}")

    # missing_cols 체크 (train_features에 없는 컬럼은 무시)
    missing_cols = set(train_features_list) - set(data.columns)
    if missing_cols:
        raise ValueError(f"Missing columns in data for version {version}: {missing_cols}")

    # data_x: 학습했던 피처들만
    data_x = data[train_features_list]

    # data_z: 일자와 target_col만
    data_z = data[['일자', target_col]]

    # ewm, diff 적용 후 index alignment
    data_x = data_x.ewm(window_size).mean()
    data_x = data_x.diff(diff_size)
    data_x.dropna(inplace=True)
    # data_z도 data_x와 인덱스 맞춤
    data_z = data_z.loc[data_x.index]

    scaler_x = joblib.load(f'scaler/scaler_x({version}).pkl')
    new_x_data = scaler_x.transform(data_x)

    new_x = []
    new_z = []
    for i in range(len(new_x_data) - w + 1):
        x = new_x_data[i:i + w]
        z = data_z.iloc[i + w - 1].values
        new_x.append(x)
        new_z.append(z)
    new_x = np.array(new_x)
    new_z = np.array(new_z)

    columns = data_z.columns
    new_z_df = pd.DataFrame(new_z, columns=columns)

    with open(f'pickle/xgboost_model({version}).pkl', 'rb') as model_file:
        model = pickle.load(model_file)

    new_x_reshaped = new_x.reshape(new_x.shape[0], -1)
    predictions = model.predict(new_x_reshaped)

    label_encoder = joblib.load(f'labels/label_encoder({version}).pkl')
    pred_labels = label_encoder.inverse_transform(predictions)

    df = pd.DataFrame()
    df['pred'] = pred_labels

    new_z_df['pred'] = new_z_df[target_col] + df['pred'].values
    new_z_df['일자'] = pd.to_datetime(new_z_df['일자'])
    new_z_df['일자'] = new_z_df['일자'] + pd.Timedelta(days=h)
    new_z_df = new_z_df.drop(columns=[target_col])

    # 2_20 모델일 경우 예측값에 +10
    if version == "2_20":
        new_z_df['pred'] = new_z_df['pred'] + 10

    output_file = f"excel2/{version}.xlsx"
    if not os.path.exists('excel2'):
        os.makedirs('excel2')

    save_or_update_excel(new_z_df, output_file)

    # ★ 여기서 예측 결과 DataFrame(new_z_df)을 반환하도록 함 ★
    return new_z_df


def process_all_versions():
    price_versions = ["2_10", "2_20", "2_30", "2_45", "2_60"]
    special_price_versions = ["4_10", "4_20", "4_30", "4_45", "4_60"]

    new_dates = []  # 업데이트된 새로운 날짜를 추적하기 위한 리스트

    for price_version, special_price_version in zip(price_versions, special_price_versions):
        # 단가 및 특구가 각각 처리 (각각의 예측 결과 DataFrame을 반환받음)
        price_data = process_version(price_version)
        special_price_data = process_version(special_price_version)

        # 예측 결과 DataFrame에서 '일자' 컬럼이 있는지 확인 후, 새로운 날짜 저장
        if price_data is not None and '일자' in price_data.columns:
            new_dates += price_data['일자'].tolist()
        else:
            print(f"Warning: No '일자' data for version {price_version}")

        # 단가와 특구가 비교 및 업데이트
        compare_and_update_special_price(price_version, special_price_version, new_dates)

        print(f"Processed and compared versions: {price_version} & {special_price_version}")

if __name__ == "__main__":
    process_all_versions()
"""
mask_images.py
피처명이 포함된 분석 이미지의 축 레이블/범례 영역을 마스킹 처리
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUT = Path(__file__).parent
MASK_COLOR = (220, 220, 220)   # 밝은 회색
TEXT_COLOR = (100, 100, 100)   # 어두운 회색 (대체 텍스트)


def add_masked_label(draw, x, y, w, h, text, fontsize=11):
    """박스 채우기 + 중앙 텍스트"""
    draw.rectangle([x, y, x + w, y + h], fill=MASK_COLOR, outline=(180, 180, 180))
    try:
        font = ImageFont.truetype("arial.ttf", fontsize)
    except Exception:
        font = ImageFont.load_default()
    # 텍스트 중앙 정렬
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = x + (w - tw) // 2
    ty = y + (h - th) // 2
    draw.text((tx, ty), text, fill=TEXT_COLOR, font=font)


def mask_horizontal_bar(path: Path, label_width_ratio=0.18):
    """
    가로 막대 차트의 y축 레이블(좌측) 마스킹.
    label_width_ratio: 이미지 너비 대비 레이블 영역 비율
    """
    img = Image.open(path).convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)
    label_w = int(w * label_width_ratio)
    # 상단 여백(제목) 제외하고 플롯 영역만
    top_margin = int(h * 0.06)
    bot_margin = int(h * 0.06)
    draw.rectangle([0, top_margin, label_w, h - bot_margin], fill=MASK_COLOR,
                   outline=(180, 180, 180))
    # 중앙에 안내 텍스트
    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except Exception:
        font = ImageFont.load_default()
    draw.text((4, h // 2), "Feature Names\n(masked)", fill=TEXT_COLOR, font=font)
    img.save(path)
    print(f"  [완료] {path.name}  ({w}x{h})")


def mask_correlation_heatmap(path: Path):
    """
    삼각형 상관관계 히트맵 — 좌측 y축 레이블 + 하단 x축 레이블 마스킹.
    """
    img = Image.open(path).convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)
    # 좌측 y축 레이블
    left_w  = int(w * 0.16)
    top_m   = int(h * 0.06)
    bot_m   = int(h * 0.12)
    draw.rectangle([0, top_m, left_w, h - bot_m], fill=MASK_COLOR,
                   outline=(180, 180, 180))
    # 하단 x축 레이블
    left_m2 = int(w * 0.10)
    draw.rectangle([left_m2, h - bot_m, w - int(w * 0.04), h],
                   fill=MASK_COLOR, outline=(180, 180, 180))
    try:
        font = ImageFont.truetype("arial.ttf", 11)
    except Exception:
        font = ImageFont.load_default()
    draw.text((4, h // 2), "Labels\n(masked)", fill=TEXT_COLOR, font=font)
    img.save(path)
    print(f"  [완료] {path.name}  ({w}x{h})")


def mask_legend(path: Path):
    """
    범례(legend)에 피처명이 있는 차트 — 우측 범례 박스 마스킹.
    """
    img = Image.open(path).convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)
    # 범례는 우측 ~20% 영역
    legend_x = int(w * 0.80)
    legend_y = int(h * 0.55)
    draw.rectangle([legend_x, legend_y, w - 5, h - int(h * 0.05)],
                   fill=MASK_COLOR, outline=(180, 180, 180))
    try:
        font = ImageFont.truetype("arial.ttf", 11)
    except Exception:
        font = ImageFont.load_default()
    draw.text((legend_x + 5, legend_y + 5), "Legend\n(masked)", fill=TEXT_COLOR, font=font)
    img.save(path)
    print(f"  [완료] {path.name}  ({w}x{h})")


def mask_missing_heatmap(path: Path):
    """결측 히트맵 — 좌측 y축(피처명) 마스킹"""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)
    left_w = int(w * 0.14)
    top_m  = int(h * 0.07)
    draw.rectangle([0, top_m, left_w, h - int(h * 0.1)], fill=MASK_COLOR,
                   outline=(180, 180, 180))
    try:
        font = ImageFont.truetype("arial.ttf", 11)
    except Exception:
        font = ImageFont.load_default()
    draw.text((4, h // 2 - 20), "Feature\nNames\n(masked)", fill=TEXT_COLOR, font=font)
    img.save(path)
    print(f"  [완료] {path.name}  ({w}x{h})")


if __name__ == "__main__":
    print("=== 이미지 피처명 마스킹 시작 ===\n")

    # 1. 가로 막대 피처 중요도 차트 (y축 = 피처명)
    bar_charts = [
        "07_xgb_importance.png",
        "07_ensemble_importance.png",
        "07_lasso.png",
        "07_mutual_information.png",
        "08_feature_importance_10d.png",
    ]
    for fname in bar_charts:
        p = OUT / fname
        if p.exists():
            mask_horizontal_bar(p)

    # 2. 상관관계 히트맵 (양 축 = 피처명)
    p = OUT / "06_correlation_heatmap.png"
    if p.exists():
        mask_correlation_heatmap(p)

    # 3. Lag 상관관계 — 범례에 피처명
    p = OUT / "06_lag_correlation.png"
    if p.exists():
        mask_legend(p)

    # 4. 결측 히트맵 — y축에 피처명
    p = OUT / "02_missing_heatmap.png"
    if p.exists():
        mask_missing_heatmap(p)

    print("\n=== 마스킹 완료 ===")

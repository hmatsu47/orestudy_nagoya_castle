"""
名古屋城とデータセンター LT 用の地図画像を生成する。

サンドボックス環境では地理院/OSMタイルが使えないため、
緯度経度に基づいた幾何学的な模式図を PIL で直接描画する。
熱田台地の概形・河川（堀川／新堀川）・主要拠点（名古屋城・名古屋駅・栄・熱田神宮）・
データセンター位置を、メルカトル投影で正しい地理関係を保ちながら配置する。
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "images")
os.makedirs(OUT_DIR, exist_ok=True)

# 表示範囲
LAT_MIN, LAT_MAX = 35.110, 35.210
LON_MIN, LON_MAX = 136.855, 136.945

# 出力解像度
IMG_W = 1400
IMG_H = 1600

TITLE_BAND_H = 90
MAP_MARGIN = 40

FONT_PATH = "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf"
FONT_BOLD_PATH = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"


def get_font(size, bold=False):
    path = FONT_BOLD_PATH if bold else FONT_PATH
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def lonlat_to_px(lat, lon):
    map_w = IMG_W - 2 * MAP_MARGIN
    map_h = IMG_H - TITLE_BAND_H - MAP_MARGIN

    def merc_y(lat_deg):
        lat_rad = math.radians(lat_deg)
        return math.log(math.tan(math.pi / 4 + lat_rad / 2))

    y_min = merc_y(LAT_MIN)
    y_max = merc_y(LAT_MAX)
    y = merc_y(lat)

    x = MAP_MARGIN + (lon - LON_MIN) / (LON_MAX - LON_MIN) * map_w
    py = TITLE_BAND_H + (y_max - y) / (y_max - y_min) * map_h
    return (x, py)


# 熱田台地のおおよその輪郭
PLATEAU_POLYGON = [
    (35.198, 136.895), (35.198, 136.913), (35.180, 136.922),
    (35.165, 136.928), (35.150, 136.928), (35.135, 136.920),
    (35.123, 136.913), (35.123, 136.898), (35.140, 136.892),
    (35.158, 136.890), (35.180, 136.890), (35.195, 136.892),
]

LANDMARKS = [
    ("名古屋城",  35.1856, 136.8997, "#c00000", (14, -10)),
    ("名古屋駅",  35.1709, 136.8815, "#0050a0", (-130, -10)),
    ("栄",        35.1707, 136.9088, "#1f7a1f", (14, -28)),
    ("熱田神宮",  35.1280, 136.9075, "#c00000", (-110, -10)),
]

DATA_CENTERS = [
    ("ctc 名古屋丸の内",   35.1810, 136.8965, "#7030a0", (14, 6)),
    ("ctc 名古屋栄",       35.1690, 136.9075, "#7030a0", (14, 6)),
    ("メイテツコム熱田DC", 35.1295, 136.9085, "#7030a0", (14, 16)),
]

HORIKAWA = [
    (35.196, 136.890), (35.182, 136.889), (35.170, 136.886),
    (35.155, 136.886), (35.140, 136.886), (35.125, 136.888),
    (35.115, 136.890),
]
SHIN_HORIKAWA = [
    (35.165, 136.926), (35.150, 136.926), (35.140, 136.922),
    (35.130, 136.918), (35.120, 136.916),
]


def draw_filled_polygon(base, points_latlon, fill, outline=None, outline_width=3):
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    pts = [lonlat_to_px(lat, lon) for lat, lon in points_latlon]
    od.polygon(pts, fill=fill)
    base.alpha_composite(overlay)
    if outline:
        d = ImageDraw.Draw(base)
        d.line(pts + [pts[0]], fill=outline, width=outline_width)


def draw_river(draw, points_latlon, color, width=6):
    pts = [lonlat_to_px(lat, lon) for lat, lon in points_latlon]
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=color, width=width)


def draw_marker_with_label(draw, lat, lon, name, color, font, offset):
    px, py = lonlat_to_px(lat, lon)
    r = 9
    draw.ellipse((px - r, py - r, px + r, py + r), fill=color, outline="white", width=2)
    lx, ly = px + offset[0], py + offset[1]
    draw.text((lx, ly), name, fill="black", font=font,
              stroke_width=4, stroke_fill="white")


def draw_label(draw, lat, lon, text, font, color, offset=(0, 0)):
    px, py = lonlat_to_px(lat, lon)
    draw.text((px + offset[0], py + offset[1]), text, fill=color, font=font,
              stroke_width=5, stroke_fill="white")


def draw_title(img, title, subtitle=None):
    draw = ImageDraw.Draw(img)
    title_font = get_font(36, bold=True)
    sub_font = get_font(22)
    draw.rectangle((0, 0, img.width, TITLE_BAND_H), fill=(245, 245, 248))
    draw.line((0, TITLE_BAND_H, img.width, TITLE_BAND_H), fill=(50, 50, 50), width=2)
    draw.text((24, 12), title, fill="black", font=title_font)
    if subtitle:
        draw.text((24, 54), subtitle, fill="#444444", font=sub_font)


def draw_credit(img, text):
    draw = ImageDraw.Draw(img)
    f = get_font(13)
    bbox = draw.textbbox((0, 0), text, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 6
    cx = img.width - tw - pad * 2 - 12
    cy = img.height - th - pad * 2 - 12
    draw.rectangle((cx, cy, cx + tw + pad * 2, cy + th + pad * 2),
                   fill=(255, 255, 255), outline=(80, 80, 80), width=1)
    draw.text((cx + pad, cy + pad), text, fill="#222222", font=f)


def draw_compass(img, x, y, size=80):
    draw = ImageDraw.Draw(img)
    f = get_font(18, bold=True)
    draw.line((x, y - size // 2, x, y + size // 2), fill="black", width=3)
    draw.line((x - size // 2, y, x + size // 2, y), fill="black", width=2)
    draw.polygon([(x, y - size // 2 - 8), (x - 8, y - size // 2 + 4), (x + 8, y - size // 2 + 4)], fill="black")
    draw.text((x - 6, y - size // 2 - 32), "N", fill="black", font=f, stroke_width=3, stroke_fill="white")


def draw_scale_bar(img, x, y, length_km=1.0):
    draw = ImageDraw.Draw(img)
    px_per_deg = abs(lonlat_to_px(35.150, 136.900)[1] - lonlat_to_px(35.160, 136.900)[1]) / 0.010
    bar_px = int(px_per_deg * (length_km / 111.0))
    draw.rectangle((x, y, x + bar_px, y + 10), fill="black")
    f = get_font(16, bold=True)
    draw.text((x, y + 14), f"{length_km:g} km", fill="black", font=f,
              stroke_width=3, stroke_fill="white")


def render_topographic_map():
    img = Image.new("RGBA", (IMG_W, IMG_H), (250, 250, 252, 255))

    # 背景全体を沖積低地の色（薄水色）で塗る
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, TITLE_BAND_H, IMG_W, IMG_H), fill=(190, 218, 240))

    # 熱田台地を上に重ねる
    draw_filled_polygon(img, PLATEAU_POLYGON,
                        fill=(255, 200, 110, 255),
                        outline=(180, 90, 0), outline_width=4)

    draw = ImageDraw.Draw(img)

    # 河川
    draw_river(draw, HORIKAWA, color=(0, 100, 220), width=6)
    draw_river(draw, SHIN_HORIKAWA, color=(0, 100, 220), width=6)

    # 河川ラベル
    river_font = get_font(22, bold=True)
    draw_label(draw, 35.150, 136.880, "堀川", river_font, (0, 60, 160), offset=(0, -10))
    draw_label(draw, 35.155, 136.928, "新堀川", river_font, (0, 60, 160), offset=(10, -10))

    # 台地ラベル
    plateau_font = get_font(48, bold=True)
    draw_label(draw, 35.158, 136.910, "熱田台地", plateau_font, (140, 60, 0), offset=(-100, -30))
    plateau_sub_font = get_font(22, bold=True)
    draw_label(draw, 35.150, 136.910, "（洪積層 / 標高約10〜15m）",
               plateau_sub_font, (120, 60, 0), offset=(-130, 30))

    # 低地ラベル（西・東）— 凡例と被らない位置に
    lowland_font = get_font(26, bold=True)
    draw_label(draw, 35.150, 136.870, "沖積低地\n（旧低湿地）",
               lowland_font, (30, 70, 130), offset=(-80, -20))
    draw_label(draw, 35.180, 136.935, "沖積低地",
               lowland_font, (30, 70, 130), offset=(-50, -10))

    # ランドマーク
    landmark_font = get_font(22, bold=True)
    for name, lat, lon, color, off in LANDMARKS:
        draw_marker_with_label(draw, lat, lon, name, color, landmark_font, off)

    # データセンター
    dc_font = get_font(20, bold=True)
    for name, lat, lon, color, off in DATA_CENTERS:
        draw_marker_with_label(draw, lat, lon, name, color, dc_font, off)

    # 凡例（下端）
    legend_x = MAP_MARGIN + 10
    legend_y = IMG_H - 280
    legend_w = 320
    legend_h = 240
    draw.rectangle((legend_x, legend_y, legend_x + legend_w, legend_y + legend_h),
                   fill=(255, 255, 255), outline="black", width=2)
    legend_title_font = get_font(20, bold=True)
    draw.text((legend_x + 12, legend_y + 8), "凡例", fill="black", font=legend_title_font)

    fl = get_font(17, bold=True)
    items = [
        ((255, 200, 110), "熱田台地（洪積層）", "fill"),
        ((190, 218, 240), "沖積低地（液状化リスク高）", "fill"),
        ((0, 100, 220),  "河川（堀川／新堀川）", "line"),
        ((192, 0, 0),    "主要ランドマーク", "marker"),
        ((112, 48, 160), "データセンター", "marker"),
    ]
    yy = legend_y + 38
    for color, label, kind in items:
        if kind == "fill":
            draw.rectangle((legend_x + 14, yy, legend_x + 38, yy + 24), fill=color, outline="black")
        elif kind == "line":
            draw.line((legend_x + 14, yy + 12, legend_x + 38, yy + 12), fill=color, width=5)
        elif kind == "marker":
            cx, cy = legend_x + 26, yy + 12
            draw.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=color, outline="white", width=2)
        draw.text((legend_x + 50, yy + 2), label, fill="black", font=fl)
        yy += 36

    draw_compass(img, IMG_W - 90, TITLE_BAND_H + 70, size=60)
    draw_scale_bar(img, IMG_W - 200, IMG_H - 80, length_km=1.0)

    draw_title(img, "熱田台地と名古屋の主要拠点・データセンター",
               "経緯度に基づく模式図（堀川・新堀川を境界に台地と低地を表現）")
    draw_credit(img, "作図：本LT資料用 概念図（地形は模式化）")

    out = os.path.join(OUT_DIR, "map_atsuta_plateau.png")
    img.convert("RGB").save(out, "PNG", optimize=True)
    print(f"[topo] saved → {out}")


def render_liquefaction_map():
    img = Image.new("RGBA", (IMG_W, IMG_H), (250, 250, 252, 255))

    # 背景全体をリスク高（赤）で塗る
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, TITLE_BAND_H, IMG_W, IMG_H), fill=(225, 110, 110))

    # 台地（リスク低 = 緑）を重ねる
    draw_filled_polygon(img, PLATEAU_POLYGON,
                        fill=(110, 200, 130, 255),
                        outline=(20, 110, 40), outline_width=4)

    draw = ImageDraw.Draw(img)

    # 河川
    draw_river(draw, HORIKAWA, color=(0, 100, 220), width=5)
    draw_river(draw, SHIN_HORIKAWA, color=(0, 100, 220), width=5)

    # 大ラベル
    big_font = get_font(44, bold=True)
    sub_font = get_font(24, bold=True)

    draw_label(draw, 35.158, 136.910, "リスク低",
               big_font, (10, 90, 30), offset=(-90, -30))
    draw_label(draw, 35.148, 136.910, "（熱田台地 / 洪積層）",
               sub_font, (10, 90, 30), offset=(-130, 30))

    draw_label(draw, 35.180, 136.870, "リスク高",
               big_font, (140, 20, 20), offset=(-80, -10))
    draw_label(draw, 35.172, 136.870, "（沖積低地 + 地盤沈下）",
               sub_font, (140, 20, 20), offset=(-140, 35))

    draw_label(draw, 35.180, 136.935, "リスク高",
               big_font, (140, 20, 20), offset=(-80, -10))

    # ランドマーク
    landmark_font = get_font(22, bold=True)
    for name, lat, lon, color, off in LANDMARKS:
        draw_marker_with_label(draw, lat, lon, name, color, landmark_font, off)

    # 凡例
    legend_x = MAP_MARGIN + 10
    legend_y = IMG_H - 180
    legend_w = 300
    legend_h = 130
    draw.rectangle((legend_x, legend_y, legend_x + legend_w, legend_y + legend_h),
                   fill=(255, 255, 255), outline="black", width=2)
    fl = get_font(20, bold=True)
    draw.text((legend_x + 12, legend_y + 8), "液状化リスク", fill="black", font=fl)
    fl_item = get_font(18, bold=True)
    draw.rectangle((legend_x + 14, legend_y + 44, legend_x + 38, legend_y + 68),
                   fill=(110, 200, 130), outline="black")
    draw.text((legend_x + 50, legend_y + 46), "低（洪積層）", fill="black", font=fl_item)
    draw.rectangle((legend_x + 14, legend_y + 80, legend_x + 38, legend_y + 104),
                   fill=(225, 110, 110), outline="black")
    draw.text((legend_x + 50, legend_y + 82), "高（沖積低地）", fill="black", font=fl_item)

    draw_compass(img, IMG_W - 90, TITLE_BAND_H + 70, size=60)

    draw_title(img, "名古屋中心部の液状化リスク概念図",
               "熱田台地（洪積層）と沖積低地のリスク差を模式的に表現")
    draw_credit(img, "出典：名古屋市の液状化ハザード傾向に基づく概念図")

    out = os.path.join(OUT_DIR, "map_liquefaction_risk.png")
    img.convert("RGB").save(out, "PNG", optimize=True)
    print(f"[liquefaction] saved → {out}")


if __name__ == "__main__":
    render_topographic_map()
    render_liquefaction_map()

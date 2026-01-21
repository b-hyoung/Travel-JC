import importlib.util
import json
import math
import os
import re
import sqlite3
import ssl
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from pathlib import Path

from PyQt5.QtCore import Qt, QEvent, QSize, QRect, pyqtSignal, QTimer
from PyQt5.QtGui import (
    QFont,
    QFontDatabase,
    QColor,
    QIcon,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPalette,
    QPixmap,
)
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStyle,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from .helpers import (
    LANGUAGES,
    LANG_INFO,
    _get_cached_pixmap,
    _lang_value,
    _place_lang_code,
    _resolve_place_image_path,
    _set_back_button_icon,
    _menu_lang_code,
    _build_qr_pixmap,
    STAMP_QR_URL,
)
from .tour_page import TourPage
from .stamp_page import TravelStampPage

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
if load_dotenv:
    load_dotenv(PROJECT_DIR / ".env")
KIOSK_DB_FILE = PROJECT_DIR / "db-server" / "kiosk.db"
KIOSK_DATA_FILE = PROJECT_DIR / "db-server" / "kiosk_data.json"
MENU_DESCRIPTION_FILE = PROJECT_DIR / "db-server" / "menu_description_i18n.json"
DEFAULT_KIOSK_ID = "KIOSK_001"
KIOSK_LOCATION = {
    "name": {
        "ko": "전주역",
        "en": "Jeonju Station",
    },
    "lat": 35.8499,
    "lng": 127.1316,
}
KIOSK_LOCATION_LABELS = {
    "ko": "현재 위치",
    "en": "Location",
}
FONT_DIR = PROJECT_DIR / "fonts"
TITLE_IMAGE = PROJECT_DIR / "title.png"
PREFERRED_FAMILIES = [
    "Noto Sans CJK KR",
    "Noto Sans CJK JP",
    "Noto Sans CJK SC",
    "Noto Sans CJK TC",
    "Noto Sans",
    "Noto Serif KR",
    "Nanum Myeongjo",
    "Gowun Batang",
]
FALLBACK_FAMILIES = [
    "Apple SD Gothic Neo",
    "Malgun Gothic",
    "Yu Gothic",
    "Hiragino Sans",
    "PingFang SC",
    "Microsoft YaHei",
    "Segoe UI",
    "Arial",
    "DejaVu Sans",
]
_GEOCODE_CACHE = {}
_WEATHER_ICON_CACHE = {}
KMA_ULTRA_FCST_URL = (
    "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst"
)
KMA_VILLAGE_FCST_URL = (
    "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
)
_SEOUL_TZ = ZoneInfo("Asia/Seoul") if ZoneInfo else None


def _load_app_fonts() -> None:
    if not FONT_DIR.exists():
        return
    for ext in ("*.ttf", "*.otf", "*.ttc"):
        for font_path in FONT_DIR.glob(ext):
            QFontDatabase.addApplicationFont(str(font_path))


def _resolve_font_family() -> str:
    _load_app_fonts()
    available = set(QFontDatabase().families())
    for family in PREFERRED_FAMILIES + FALLBACK_FAMILIES:
        if family in available:
            return family
    return QApplication.font().family()


_TOUR_MODULE = None


def _load_tour_window(parent=None, on_back=None):
    global _TOUR_MODULE
    project_dir = str(PROJECT_DIR)
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)
    module_path = PROJECT_DIR / "rootgui" / "rootgut.py"
    if not module_path.exists():
        return None
    if _TOUR_MODULE is None:
        spec = importlib.util.spec_from_file_location("rootgui_rootgut", module_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _TOUR_MODULE = module
    window_cls = getattr(_TOUR_MODULE, "RouteGuideWindow", None)
    if window_cls is None:
        return None
    window = window_cls()
    if on_back is not None:
        setattr(window, "on_back", on_back)
    if parent is not None:
        window.setParent(parent)
        window.setWindowFlags(Qt.Widget)
    return window


def _display_menu_name(menu_name: str, engname: str, lang: str) -> str:
    if not menu_name:
        return _lang_value(lang, "food_menu_fallback", "Menu")
    if _place_lang_code(lang) == "ko":
        return menu_name
    return engname or _romanize_korean(menu_name)


def _parse_price_value(price: str):
    if not price:
        return None
    match = re.search(r"\d[\d,]*", price)
    if not match:
        return None
    value = match.group(0).replace(",", "")
    try:
        return int(value)
    except ValueError:
        return None


def _format_price_display(range_value, price_texts):
    if range_value:
        low, high = range_value
        if low == high:
            return f"\u20a9{low:,}"
        return f"\u20a9{low:,}~{high:,}"
    if price_texts:
        return next(iter(price_texts))
    return ""


def _romanize_korean(text: str) -> str:
    if not text:
        return text
    choseong = [
        "g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s",
        "ss", "", "j", "jj", "ch", "k", "t", "p", "h",
    ]
    jungseong = [
        "a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa",
        "wae", "oe", "yo", "u", "wo", "we", "wi", "yu", "eu", "ui", "i",
    ]
    jongseong = [
        "", "k", "k", "k", "n", "n", "n", "t", "l", "k",
        "m", "l", "l", "l", "p", "l", "m", "p", "p", "t",
        "t", "ng", "t", "t", "k", "t", "p", "t",
    ]
    result = []
    for char in text:
        code = ord(char)
        if 0xAC00 <= code <= 0xD7A3:
            syllable = code - 0xAC00
            cho = syllable // 588
            jung = (syllable % 588) // 28
            jong = syllable % 28
            result.append(choseong[cho] + jungseong[jung] + jongseong[jong])
        else:
            result.append(char)
    return "".join(result)


def _current_location_text(lang: str) -> str:
    lang_code = _place_lang_code(lang)
    label = _lang_value(lang, "location_label", "Location")
    names = KIOSK_LOCATION.get("name", {})
    name = names.get(lang_code) or names.get("en")
    if not name and names:
        name = next(iter(names.values()))
    if not name:
        return label
    return f"{label}: {name}"


def _build_directions_url(destination: dict) -> str:
    names = KIOSK_LOCATION.get("name", {})
    if isinstance(names, dict):
        origin_text = names.get("ko") or names.get("en")
        if not origin_text and names:
            origin_text = next(iter(names.values()))
    else:
        origin_text = str(names) if names else ""
    origin_lat = KIOSK_LOCATION.get("lat")
    origin_lng = KIOSK_LOCATION.get("lng")
    origin_lat, origin_lng = _resolve_destination_coords(origin_lat, origin_lng, origin_text)
    dest_lat = destination.get("lat") if destination else None
    dest_lng = destination.get("lng") if destination else None
    dest_addr = destination.get("address") if destination else None
    dest_lat, dest_lng = _resolve_destination_coords(dest_lat, dest_lng, dest_addr)
    if origin_lat is None or origin_lng is None or dest_lat is None or dest_lng is None:
        return ""
    params = {
        "api": 1,
        "origin": f"{origin_lat},{origin_lng}",
        "destination": f"{dest_lat},{dest_lng}",
        "travelmode": "walking",
    }
    return "https://www.google.com/maps/dir/?" + urllib.parse.urlencode(params)


def _google_maps_api_key() -> str:
    return os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()


def _geocode_address(address: str):
    if not address:
        return None
    query = address.strip()
    if not query:
        return None
    if query in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[query]
    api_key = _google_maps_api_key()
    if not api_key:
        return None
    params = {"address": query, "key": api_key}
    url = "https://maps.googleapis.com/maps/api/geocode/json?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=6) as response:
            data = response.read()
        payload = json.loads(data.decode("utf-8"))
        results = payload.get("results", [])
        if not results:
            _GEOCODE_CACHE[query] = None
            return None
        location = results[0].get("geometry", {}).get("location", {})
        lat = location.get("lat")
        lng = location.get("lng")
        if lat is None or lng is None:
            _GEOCODE_CACHE[query] = None
            return None
        result = (lat, lng)
        _GEOCODE_CACHE[query] = result
        return result
    except Exception:
        return None


def _resolve_destination_coords(lat, lng, address):
    if lat is not None and lng is not None:
        return lat, lng
    resolved = _geocode_address(address)
    if not resolved:
        return None, None
    return resolved


def _kma_service_key() -> str:
    return os.environ.get("KMA_SERVICE_KEY", "").strip()


def _kma_base_datetime(now: Optional[datetime] = None) -> Tuple[str, str]:
    if now is None:
        now = datetime.now()
    base = now.replace(second=0, microsecond=0)
    if base.minute < 30:
        base -= timedelta(hours=1)
    base = base.replace(minute=30)
    return base.strftime("%Y%m%d"), base.strftime("%H%M")


def _kma_village_base_datetime(now: Optional[datetime] = None) -> Tuple[str, str]:
    if now is None:
        now = _seoul_now()
    base_times = [2, 5, 8, 11, 14, 17, 20, 23]
    current_hour = now.hour
    current_minute = now.minute
    base_hour = None
    for hour in reversed(base_times):
        if current_hour > hour or (current_hour == hour and current_minute >= 10):
            base_hour = hour
            break
    if base_hour is None:
        base_hour = 23
        now = now - timedelta(days=1)
    return now.strftime("%Y%m%d"), f"{base_hour:02d}00"


def _latlng_to_grid(lat: float, lng: float):
    RE = 6371.00877
    GRID = 5.0
    SLAT1 = 30.0
    SLAT2 = 60.0
    OLON = 126.0
    OLAT = 38.0
    XO = 43
    YO = 136

    deg_to_rad = math.pi / 180.0
    re = RE / GRID
    slat1 = SLAT1 * deg_to_rad
    slat2 = SLAT2 * deg_to_rad
    olon = OLON * deg_to_rad
    olat = OLAT * deg_to_rad

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = math.pow(sf, sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / math.pow(ro, sn)

    ra = math.tan(math.pi * 0.25 + lat * deg_to_rad * 0.5)
    ra = re * sf / math.pow(ra, sn)
    theta = lng * deg_to_rad - olon
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn

    x = ra * math.sin(theta) + XO
    y = ro - ra * math.cos(theta) + YO
    return int(x + 0.5), int(y + 0.5)


def _weather_summary_labels(pty: Optional[int], sky: Optional[int]):
    if pty is None:
        pty = 0
    if pty in (1, 4, 5):
        return "Rain", "비", "rain"
    if pty in (2, 6, 7):
        return "Rain/Snow", "비/눈", "sleet"
    if pty == 3:
        return "Snow", "눈", "snow"
    if sky == 1:
        return "Clear", "맑음", "clear"
    if sky == 3:
        return "Mostly Cloudy", "구름많음", "cloudy"
    if sky == 4:
        return "Overcast", "흐림", "overcast"
    return "Cloudy", "흐림", "cloudy"


def _precip_level(pop: Optional[int]) -> Optional[str]:
    if pop is None:
        return None
    if pop >= 75:
        return "very_high"
    if pop >= 51:
        return "high"
    if pop >= 21:
        return "moderate"
    return "low"


def _precip_label(lang: str, pty: Optional[int]) -> str:
    if pty and pty != 0:
        return "있음" if _place_lang_code(lang) == "ko" else "Yes"
    return "없음" if _place_lang_code(lang) == "ko" else "No"


def _format_weather_line(lang: str, summary_en: str, summary_ko: str, temp_c, humidity, pty, pop):
    is_ko = _place_lang_code(lang) == "ko"
    summary = summary_ko if is_ko else summary_en
    precip_text = _precip_label(lang, pty)
    parts = []
    if summary:
        parts.append(summary)
    if temp_c is not None:
        parts.append(f"{temp_c}°C")
    if humidity is not None:
        if is_ko:
            parts.append(f"습도 {humidity}%")
        else:
            parts.append(f"Humidity {humidity}%")
    if pop is not None:
        level = _precip_level(pop)
        if level == "very_high":
            level_en = "Very high"
            level_ko = "매우높음"
        elif level == "high":
            level_en = "High"
            level_ko = "높음"
        elif level == "moderate":
            level_en = "Moderate"
            level_ko = "보통"
        else:
            level_en = "Low"
            level_ko = "낮음"
        if is_ko:
            parts.append(f"강수확률 {pop}% ({level_ko})")
        else:
            parts.append(f"Precip {pop}% ({level_en})")
    else:
        if is_ko:
            parts.append(f"비 {precip_text}")
        else:
            parts.append(f"Rain {precip_text}")
    if parts:
        return " | ".join(parts)
    return "날씨 정보 없음" if is_ko else "Weather unavailable"


def _fetch_kma_ultra_forecast(lat: float, lng: float):
    api_key = _kma_service_key()
    if not api_key:
        return None
    nx, ny = _latlng_to_grid(lat, lng)
    base_date, base_time = _kma_base_datetime()
    params = {
        "serviceKey": api_key,
        "pageNo": 1,
        "numOfRows": 1000,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }
    url = KMA_ULTRA_FCST_URL + "?" + urllib.parse.urlencode(params, safe="%")
    try:
        with urllib.request.urlopen(url, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    items = payload.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    if not items:
        return None
    by_time = {}
    for item in items:
        fcst_time = item.get("fcstTime")
        category = item.get("category")
        value = item.get("fcstValue")
        if not fcst_time or not category:
            continue
        by_time.setdefault(fcst_time, {})[category] = value
    if not by_time:
        return None
    target_time = sorted(by_time.keys())[0]
    values = by_time[target_time]
    return {
        "T1H": values.get("T1H"),
        "REH": values.get("REH"),
        "PTY": values.get("PTY"),
        "SKY": values.get("SKY"),
    }


def _fetch_kma_village_forecast(lat: float, lng: float):
    api_key = _kma_service_key()
    if not api_key:
        return None
    nx, ny = _latlng_to_grid(lat, lng)
    base_date, base_time = _kma_village_base_datetime()
    params = {
        "serviceKey": api_key,
        "pageNo": 1,
        "numOfRows": 2000,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }
    url = KMA_VILLAGE_FCST_URL + "?" + urllib.parse.urlencode(params, safe="%")
    try:
        with urllib.request.urlopen(url, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    items = payload.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    if not items:
        return None
    today = _seoul_now().strftime("%Y%m%d")
    by_time = {}
    for item in items:
        fcst_date = item.get("fcstDate")
        fcst_time = item.get("fcstTime")
        category = item.get("category")
        value = item.get("fcstValue")
        if not fcst_date or not fcst_time or not category:
            continue
        if fcst_date != today:
            continue
        by_time.setdefault(fcst_time, {})[category] = value
    if not by_time:
        return None
    now_time = _seoul_now().strftime("%H%M")
    candidate_times = sorted(by_time.keys())
    target_time = None
    for t in candidate_times:
        if t >= now_time:
            target_time = t
            break
    if target_time is None:
        target_time = candidate_times[0]
    values = by_time[target_time]
    return {
        "POP": values.get("POP"),
    }


def _build_weather_icon(kind: str, size: int) -> QPixmap:
    key = (kind, size)
    cached = _WEATHER_ICON_CACHE.get(key)
    if cached:
        return cached
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    cloud_color = QColor(189, 196, 205)
    sun_color = QColor(253, 224, 71)
    rain_color = QColor(96, 165, 250)
    snow_color = QColor(229, 231, 235)

    def draw_cloud(offset_x=0, offset_y=0):
        painter.setPen(Qt.NoPen)
        painter.setBrush(cloud_color)
        base_w = int(size * 0.7)
        base_h = int(size * 0.26)
        base_x = int(size * 0.15) + offset_x
        base_y = int(size * 0.52) + offset_y
        painter.drawRoundedRect(base_x, base_y, base_w, base_h, base_h // 2, base_h // 2)
        painter.drawEllipse(int(size * 0.2) + offset_x, int(size * 0.42) + offset_y, int(size * 0.28), int(size * 0.28))
        painter.drawEllipse(int(size * 0.38) + offset_x, int(size * 0.36) + offset_y, int(size * 0.32), int(size * 0.32))
        painter.drawEllipse(int(size * 0.58) + offset_x, int(size * 0.44) + offset_y, int(size * 0.24), int(size * 0.24))

    if kind == "clear":
        painter.setPen(Qt.NoPen)
        painter.setBrush(sun_color)
        radius = int(size * 0.26)
        center = int(size * 0.5)
        painter.drawEllipse(center - radius, center - radius, radius * 2, radius * 2)
    else:
        draw_cloud()
        if kind in ("rain", "sleet"):
            painter.setPen(QPen(rain_color, max(1, int(size * 0.06))))
            for idx in range(3):
                x = int(size * (0.32 + idx * 0.16))
                y1 = int(size * 0.75)
                y2 = int(size * 0.9)
                painter.drawLine(x, y1, x - int(size * 0.03), y2)
        if kind in ("snow", "sleet"):
            painter.setPen(QPen(snow_color, max(1, int(size * 0.05))))
            for idx in range(2):
                x = int(size * (0.35 + idx * 0.22))
                y = int(size * 0.82)
                painter.drawLine(x - int(size * 0.04), y - int(size * 0.04), x + int(size * 0.04), y + int(size * 0.04))
                painter.drawLine(x - int(size * 0.04), y + int(size * 0.04), x + int(size * 0.04), y - int(size * 0.04))

    painter.end()
    _WEATHER_ICON_CACHE[key] = pixmap
    return pixmap


def _seoul_now():
    if _SEOUL_TZ:
        return datetime.now(_SEOUL_TZ)
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9)))


def _build_static_map_url(lat: float, lng: float, width: int, height: int) -> str:
    api_key = _google_maps_api_key()
    if not api_key:
        return ""
    size_w = min(640, max(120, int(width * 1.5)))
    size_h = min(640, max(120, int(height * 1.5)))
    markers = [f"color:red|{lat},{lng}"]
    params = {
        "size": f"{size_w}x{size_h}",
        "scale": 2,
        "maptype": "roadmap",
        "format": "png",
        "markers": markers,
        "key": api_key,
    }
    params["center"] = f"{lat},{lng}"
    params["zoom"] = 15
    return "https://maps.googleapis.com/maps/api/staticmap?" + urllib.parse.urlencode(params, doseq=True)


def _fetch_static_map_pixmap(lat: float, lng: float, width: int, height: int):
    url = _build_static_map_url(lat, lng, width, height)
    if not url:
        if os.environ.get("GOOGLE_MAPS_DEBUG", "").strip().lower() in ("1", "true", "yes"):
            print("[map] Missing GOOGLE_MAPS_API_KEY", file=sys.stderr)
        return None
    verify_ssl = os.environ.get("GOOGLE_MAPS_SSL_NO_VERIFY", "").strip().lower() not in ("1", "true", "yes")
    ssl_context = None
    if not verify_ssl:
        ssl_context = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(url, timeout=6, context=ssl_context) as response:
            data = response.read()
    except Exception as exc:
        if os.environ.get("GOOGLE_MAPS_DEBUG", "").strip().lower() in ("1", "true", "yes"):
            if isinstance(exc, urllib.error.HTTPError):
                try:
                    body = exc.read().decode("utf-8", errors="replace")
                except Exception:
                    body = ""
                print(f"[map] Static map request failed: {exc}", file=sys.stderr)
                if body:
                    print(f"[map] Static map response body: {body}", file=sys.stderr)
            else:
                print(f"[map] Static map request failed: {exc}", file=sys.stderr)
        return None
    image = QImage.fromData(data)
    if image.isNull():
        if os.environ.get("GOOGLE_MAPS_DEBUG", "").strip().lower() in ("1", "true", "yes"):
            print("[map] Static map response is not a valid image", file=sys.stderr)
        return None
    return QPixmap.fromImage(image)


def _crop_pixmap_to_size(pixmap: QPixmap, size: QSize) -> QPixmap:
    if pixmap.isNull() or not size.isValid():
        return pixmap
    scaled = pixmap.scaled(size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    if scaled.size() == size:
        return scaled
    x = max(0, (scaled.width() - size.width()) // 2)
    y = max(0, (scaled.height() - size.height()) // 2)
    return scaled.copy(x, y, size.width(), size.height())


def _compute_zoom_for_bounds(lat1: float, lng1: float, lat2: float, lng2: float, width: int, height: int) -> int:
    def _lat_rad(lat: float) -> float:
        sin = max(min(math.sin(math.radians(lat)), 0.9999), -0.9999)
        return math.log((1 + sin) / (1 - sin)) / 2

    lat_frac = abs(_lat_rad(lat2) - _lat_rad(lat1)) / math.pi
    lng_diff = abs(lng2 - lng1)
    lng_diff = min(lng_diff, 360 - lng_diff)
    lng_frac = lng_diff / 360.0
    if lat_frac == 0 and lng_frac == 0:
        return 16
    zoom_x = math.log2(width / 256 / max(lng_frac, 1e-6))
    zoom_y = math.log2(height / 256 / max(lat_frac, 1e-6))
    zoom = int(min(zoom_x, zoom_y)) - 1
    return max(1, min(20, zoom))


def _load_kiosk_data_from_db(db_path: Path) -> dict:
    if not db_path.exists():
        return {}
    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        kiosks = [
            dict(row)
            for row in cursor.execute(
                """
                SELECT kiosk_id, lat, lng, radius_m, default_lang, address_text
                FROM kiosks
                """
            )
        ]
        kiosk_i18n = [
            dict(row)
            for row in cursor.execute(
                """
                SELECT kiosk_id, lang, name
                FROM kiosk_i18n
                """
            )
        ]
        place_i18n = [
            dict(row)
            for row in cursor.execute(
                """
                SELECT place_id, lang, name, short_desc, address_text, hours_text
                FROM place_i18n
                """
            )
        ]
        place_images = [
            dict(row)
            for row in cursor.execute(
                """
                SELECT image_id, place_id, kind, url, storage_key, mime, width, height,
                       bytes_len, is_primary, sort_order
                FROM place_images
                ORDER BY place_id, is_primary DESC, sort_order ASC, image_id ASC
                """
            )
        ]
        place_rows = [
            dict(row)
            for row in cursor.execute(
                """
                SELECT place_id, type, category, lat, lng, tags_json, is_halal, is_vegan,
                       priority_score, cover_image_id
                FROM places
                """
            )
        ]
        menus_by_place = {}
        for row in cursor.execute(
            """
            SELECT place_id, menu_id, name, engname, description, price, image_id, sort_order
            FROM place_menus
            ORDER BY place_id, sort_order ASC, menu_id ASC
            """
        ):
            item = dict(row)
            place_id = item.get("place_id")
            if place_id is not None:
                menus_by_place.setdefault(place_id, []).append(item)
        food_info_by_place = {}
        for row in cursor.execute(
            """
            SELECT place_id, info_key, info_value
            FROM place_food_info
            """
        ):
            item = dict(row)
            place_id = item.get("place_id")
            info_key = item.get("info_key")
            if place_id is None or not info_key:
                continue
            food_info_by_place.setdefault(place_id, {})[info_key] = item.get("info_value")
        places = []
        for place in place_rows:
            tags_json = place.pop("tags_json", None)
            if tags_json:
                try:
                    tags = json.loads(tags_json)
                except json.JSONDecodeError:
                    tags = []
            else:
                tags = []
            place["tags"] = tags
            place_id = place.get("place_id")
            place["menus"] = menus_by_place.get(place_id, [])
            place["food_info"] = food_info_by_place.get(place_id, {})
            places.append(place)
        landmarks = [
            {"place_id": place.get("place_id")}
            for place in places
            if place.get("type") == "TOUR" and place.get("place_id") is not None
        ]
        return {
            "dataset_version": 0,
            "kiosk": kiosks,
            "kiosk_i18n": kiosk_i18n,
            "landmarks": landmarks,
            "place_i18n": place_i18n,
            "place_images": place_images,
            "places": places,
        }
    except Exception:
        return {}
    finally:
        if conn:
            conn.close()


def _resolve_kiosk_db_path() -> Path:
    candidates = [
        PROJECT_DIR / "db-server" / "kiosk.db",
        PROJECT_DIR / "kiosk.db",
    ]
    existing = [path for path in candidates if path.exists()]
    if not existing:
        return candidates[0]
    return max(existing, key=lambda path: path.stat().st_mtime)


def _load_kiosk_data(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def _load_menu_descriptions(path: Path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []


def _load_kiosk_location(data: dict, kiosk_id: str):
    kiosk_info = None
    for entry in data.get("kiosk", []):
        if entry.get("kiosk_id") == kiosk_id:
            kiosk_info = entry
            break
    if not kiosk_info:
        return
    names_by_lang = {}
    for entry in data.get("kiosk_i18n", []):
        if entry.get("kiosk_id") != kiosk_id:
            continue
        lang = entry.get("lang")
        name = entry.get("name")
        if lang and name:
            names_by_lang[lang] = name
    if names_by_lang:
        KIOSK_LOCATION["name"] = names_by_lang
    if "lat" in kiosk_info:
        KIOSK_LOCATION["lat"] = kiosk_info.get("lat")
    if "lng" in kiosk_info:
        KIOSK_LOCATION["lng"] = kiosk_info.get("lng")
    address_text = kiosk_info.get("address_text")
    if address_text:
        resolved = _geocode_address(address_text)
        if resolved:
            lat, lng = resolved
            if lat is not None and lng is not None:
                KIOSK_LOCATION["lat"] = lat
                KIOSK_LOCATION["lng"] = lng


def _collect_places_by_type(data: dict, place_type: str):
    place_i18n = data.get("place_i18n", [])
    places = {
        entry.get("place_id"): entry
        for entry in data.get("places", [])
        if entry.get("place_id") is not None and entry.get("type") == place_type
    }
    images = data.get("place_images", [])
    images_by_id = {entry.get("image_id"): entry for entry in images if entry.get("image_id") is not None}
    images_by_place = {}
    for entry in images:
        place_id = entry.get("place_id")
        if place_id is None:
            continue
        images_by_place.setdefault(place_id, []).append(entry)
    names_by_place = {}
    addresses_by_place = {}
    desc_by_place = {}
    for entry in place_i18n:
        place_id = entry.get("place_id")
        name = entry.get("name")
        address = entry.get("address") or entry.get("address_text")
        short_desc = entry.get("short_desc")
        if place_id is None or not name:
            continue
        names_by_place.setdefault(place_id, {})[entry.get("lang")] = name
        if address:
            addresses_by_place.setdefault(place_id, {})[entry.get("lang")] = address
        if short_desc:
            desc_by_place.setdefault(place_id, {})[entry.get("lang")] = short_desc

    items = []
    for place_id, place in places.items():
        names = names_by_place.get(place_id, {})
        addresses = addresses_by_place.get(place_id, {})
        descriptions = desc_by_place.get(place_id, {})
        cover_image_id = place.get("cover_image_id")
        cover_image_url = None
        if cover_image_id is not None:
            cover_image = images_by_id.get(cover_image_id)
            if cover_image:
                cover_image_url = cover_image.get("url")
        if not cover_image_url:
            for entry in images_by_place.get(place_id, []):
                cover_image_url = entry.get("url")
                if cover_image_url:
                    break
        fallback_name = names.get("en") or names.get("ko")
        if not fallback_name and names:
            fallback_name = next(iter(names.values()))
        fallback_address = addresses.get("en") or addresses.get("ko")
        if not fallback_address and addresses:
            fallback_address = next(iter(addresses.values()))
        fallback_desc = descriptions.get("en") or descriptions.get("ko")
        if not fallback_desc and descriptions:
            fallback_desc = next(iter(descriptions.values()))
        if not fallback_name:
            fallback_name = f"Place {place_id}"
        items.append(
            {
                "place_id": place_id,
                "names": names,
                "addresses": addresses,
                "descriptions": descriptions,
                "lat": place.get("lat"),
                "lng": place.get("lng"),
                "fallback_name": fallback_name,
                "fallback_address": fallback_address,
                "fallback_desc": fallback_desc,
                "image_url": cover_image_url,
                "priority_score": place.get("priority_score", 0),
            }
        )
    items.sort(key=lambda item: item.get("place_id", 0))
    return items


def _collect_tour_places(data: dict):
    return _collect_places_by_type(data, "TOUR")


def _collect_food_places(data: dict):
    return _collect_places_by_type(data, "FOOD")


def _collect_menu_items(menu_data, food_items, data):
    menu_order_map = {}
    menu_image_map = {}
    menu_price_values = {}
    menu_price_texts = {}
    menu_map = {}
    images_by_id = {
        entry.get("image_id"): entry.get("url")
        for entry in data.get("place_images", [])
        if entry.get("image_id") is not None
    }
    for place in data.get("places", []):
        if place.get("type") != "FOOD":
            continue
        place_id = place.get("place_id")
        for menu in place.get("menus", []):
            name = menu.get("name")
            if not name:
                continue
            engname = menu.get("engname")
            menu_id = menu.get("menu_id")
            if menu_id is not None:
                current = menu_order_map.get(name)
                if current is None or menu_id < current:
                    menu_order_map[name] = menu_id
            image_id = menu.get("image_id")
            if image_id is not None and name not in menu_image_map:
                image_url = images_by_id.get(image_id)
                if image_url:
                    menu_image_map[name] = image_url
            price = (menu.get("price") or "").strip()
            if price:
                menu_price_texts.setdefault(name, set()).add(price)
                value = _parse_price_value(price)
                if value is not None:
                    current = menu_price_values.get(name)
                    if current is None:
                        menu_price_values[name] = [value, value]
                    else:
                        current[0] = min(current[0], value)
                        current[1] = max(current[1], value)
            item = menu_map.setdefault(
                name,
                {
                    "menu_name": name,
                    "engname": engname,
                    "place_ids": set(),
                    "descriptions": {},
                },
            )
            if engname and not item.get("engname"):
                item["engname"] = engname
            if place_id is not None:
                item["place_ids"].add(place_id)
            desc = menu.get("description")
            if desc:
                item["descriptions"].setdefault("ko", desc)
    food_place_ids = {item.get("place_id") for item in food_items if item.get("place_id") is not None}
    for entry in menu_data:
        place_id = entry.get("place_id")
        if place_id not in food_place_ids:
            continue
        menu_name = entry.get("menu_name")
        if not menu_name:
            continue
        if "가격은 변동" in menu_name or "메뉴는 음식점 사정에 따라 변동" in menu_name:
            continue
        lang = entry.get("lang")
        description = entry.get("description")
        item = menu_map.setdefault(
            menu_name,
            {
                "menu_name": menu_name,
                "engname": None,
                "place_ids": set(),
                "descriptions": {},
            },
        )
        item["place_ids"].add(place_id)
        if lang and description:
            item["descriptions"].setdefault(lang, description)
    items = []
    for value in menu_map.values():
        menu_name = value["menu_name"]
        items.append(
            {
                "menu_name": menu_name,
                "place_ids": sorted(value["place_ids"]),
                "descriptions": value["descriptions"],
                "image_url": menu_image_map.get(menu_name),
                "engname": value.get("engname"),
                "price_display": _format_price_display(menu_price_values.get(menu_name), menu_price_texts.get(menu_name)),
            }
        )
    items.sort(key=lambda item: (menu_order_map.get(item.get("menu_name"), float("inf")), item.get("menu_name", "")))
    return items


class LanguagePage(QFrame):
    def __init__(self, on_select):
        super().__init__()
        self.on_select = on_select
        self.title_label = None
        self.grid_layout = None
        self.layout_root = None
        self._build()

    def _build(self):
        self.layout_root = QVBoxLayout(self)
        self.layout_root.setContentsMargins(24, 24, 24, 24)
        self.layout_root.setSpacing(18)

        self.title_label = QLabel("Language")
        self.title_label.setObjectName("title")
        self.title_label.setAlignment(Qt.AlignCenter)

        self.panel = QFrame()
        self.panel.setObjectName("panel")
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(18, 18, 18, 18)
        panel_layout.setSpacing(12)

        grid_wrap = QWidget()
        self.grid_layout = QGridLayout(grid_wrap)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setHorizontalSpacing(12)
        self.grid_layout.setVerticalSpacing(4)

        for idx, lang in enumerate(LANGUAGES):
            btn = QPushButton(lang)
            btn.setObjectName("langBtn")
            btn.clicked.connect(lambda _checked, value=lang: self.on_select(value))
            row, col = divmod(idx, 2)
            self.grid_layout.addWidget(btn, row, col)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(grid_wrap)
        panel_layout.addWidget(scroll, 1)

        self.layout_root.addWidget(self.title_label)
        self.layout_root.addWidget(self.panel, 1)

    def set_language(self, lang: str):
        title = _lang_value(lang, "language_title", "Language")
        self.title_label.setText(title)

    def apply_scale(self, scale: float):
        if self.layout_root:
            margin = max(12, int(24 * scale))
            spacing = max(8, int(18 * scale))
            self.layout_root.setContentsMargins(margin, margin, margin, margin)
            self.layout_root.setSpacing(spacing)
        if self.grid_layout:
            self.grid_layout.setHorizontalSpacing(max(6, int(12 * scale)))
            self.grid_layout.setVerticalSpacing(max(2, int(4 * scale)))
            min_height = max(46, int(64 * scale))
            for idx in range(self.grid_layout.count()):
                item = self.grid_layout.itemAt(idx)
                widget = item.widget() if item else None
                if widget:
                    widget.setMinimumHeight(min_height)


class MenuPage(QFrame):
    def __init__(self, on_language_click, on_route_click, on_tour_click=None, on_stamp_click=None):
        super().__init__()
        self.on_language_click = on_language_click
        self.on_route_click = on_route_click
        self.on_tour_click = on_tour_click
        self.on_stamp_click = on_stamp_click
        self.card_labels = {}
        self.lang_button = None
        self.location_label = None
        self.time_label = None
        self.weather_icon = None
        self.weather_label = None
        self._weather_kind = None
        self._weather_icon_size = 0
        self._weather_payload = None
        self._current_language = "English"
        self.qr_title = None
        self.qr_label = None
        self.qr_size = 260
        self.layout_root = None
        self.cards_layout = None
        self.cards = []
        self._build()

    def _build(self):
        self.layout_root = QVBoxLayout(self)
        self.layout_root.setContentsMargins(24, 24, 24, 24)
        self.layout_root.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)

        self.lang_button = QPushButton("Language")
        self.lang_button.setObjectName("langPill")
        self.lang_button.clicked.connect(self.on_language_click)
        header.addWidget(self.lang_button, 0, alignment=Qt.AlignLeft)

        header.addStretch(1)

        right_box = QWidget()
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)

        self.location_label = QLabel("")
        self.location_label.setObjectName("locationLabel")
        self.location_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        right_layout.addWidget(self.location_label, 0, alignment=Qt.AlignRight)

        self.time_label = QLabel("")
        self.time_label.setObjectName("timeLabel")
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        right_layout.addWidget(self.time_label, 0, alignment=Qt.AlignRight)

        weather_row = QHBoxLayout()
        weather_row.setContentsMargins(0, 0, 0, 0)
        weather_row.setSpacing(6)

        self.weather_icon = QLabel()
        self.weather_icon.setObjectName("weatherIcon")
        self.weather_icon.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        weather_row.addWidget(self.weather_icon, 0, alignment=Qt.AlignRight)

        self.weather_label = QLabel("")
        self.weather_label.setObjectName("weatherLabel")
        self.weather_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        weather_row.addWidget(self.weather_label, 0, alignment=Qt.AlignRight)

        right_layout.addLayout(weather_row)
        header.addWidget(right_box, 0, alignment=Qt.AlignRight)

        self.layout_root.addLayout(header)

        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(16)

        top_card = self._build_card("tour")
        left_card = self._build_card("route")
        right_card = self._build_qr_card()
        self.cards = [top_card, left_card, right_card]

        self.cards_layout.addWidget(top_card, 1)
        self.cards_layout.addWidget(left_card, 1)
        self.cards_layout.addWidget(right_card, 1)

        self.layout_root.addStretch(1)
        self.layout_root.addLayout(self.cards_layout, 0)
        self.layout_root.addStretch(1)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def _build_card(self, key: str) -> QFrame:
        card = ClickableCard()
        card.setObjectName(f"card{key.capitalize()}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(12)

        label = QLabel("")
        label.setObjectName("cardTitle")
        label.setAlignment(Qt.AlignCenter)

        self.card_labels[key] = label
        card.clicked.connect(lambda _key=key: self._on_card_clicked(_key))

        card_layout.addStretch(1)
        card_layout.addWidget(label)
        card_layout.addStretch(1)
        return card

    def _build_qr_card(self) -> QFrame:
        card = ClickableCard()
        card.setObjectName("cardQr")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(12)

        self.qr_title = QLabel("Travel Stamp")
        self.qr_title.setObjectName("cardTitle")
        self.qr_title.setAlignment(Qt.AlignCenter)

        self.qr_label = QLabel()
        self.qr_label.setObjectName("qrLabel")
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        qr_pixmap = self._build_qr_pixmap(STAMP_QR_URL, self.qr_size)
        if qr_pixmap:
            self.qr_label.setPixmap(qr_pixmap)
        else:
            self.qr_label.setText(_lang_value("English", "route_qr_unavailable", "QR unavailable."))

        card.clicked.connect(self._handle_stamp_click)
        card_layout.addStretch(1)
        card_layout.addWidget(self.qr_label, 0, alignment=Qt.AlignCenter)
        card_layout.addStretch(1)
        card_layout.addWidget(self.qr_title, 0, alignment=Qt.AlignCenter)
        return card

    def _build_qr_pixmap(self, url: str, size: int):
        return _build_qr_pixmap(url, size)

    def set_language(self, lang: str):
        self._current_language = lang
        info = LANG_INFO.get(lang, LANG_INFO["English"])
        self.lang_button.setText(f"{lang}")
        self.card_labels["tour"].setText(info["tour"])
        self.card_labels["route"].setText(info["route"])
        if self.location_label:
            self.location_label.setText(_current_location_text(lang))
        self._update_weather_text()
        if self.qr_title:
            self.qr_title.setText(_lang_value(lang, "travel_stamp_title", "Travel Stamp"))
        if self.qr_label:
            current_pixmap = self.qr_label.pixmap()
            if current_pixmap is None or current_pixmap.isNull():
                self.qr_label.setText(_lang_value(lang, "route_qr_unavailable", "QR unavailable."))

    def _on_card_clicked(self, key: str):
        if key == "route" and self.on_route_click:
            self.on_route_click()
            return
        if key == "tour" and self.on_tour_click:
            self.on_tour_click()
            return
        # Placeholder for navigation; wire to the actual pages later.

    def _handle_stamp_click(self):
        if self.on_stamp_click:
            self.on_stamp_click()

    def set_time_text(self, text: str):
        if self.time_label:
            self.time_label.setText(text)

    def set_weather(self, payload: Optional[dict]):
        self._weather_payload = payload
        self._update_weather_text()

    def _apply_weather_level_color(self, level: Optional[str]):
        if not self.weather_label:
            return
        if level == "very_high":
            color = "#ef4444"
        elif level == "high":
            color = "#f97316"
        elif level == "moderate":
            color = "#f59e0b"
        elif level == "low":
            color = "#6b7280"
        else:
            self.weather_label.setStyleSheet("")
            return
        self.weather_label.setStyleSheet(f"color: {color};")

    def _update_weather_text(self):
        if not self.weather_label or not self.weather_icon:
            return
        if not self._weather_payload:
            is_ko = _place_lang_code(self._current_language) == "ko"
            self.weather_label.setText("날씨 정보 없음" if is_ko else "Weather unavailable")
            self.weather_icon.setPixmap(QPixmap())
            self._apply_weather_level_color(None)
            return
        summary_en = self._weather_payload.get("summary_en")
        summary_ko = self._weather_payload.get("summary_ko")
        temp_c = self._weather_payload.get("temp_c")
        humidity = self._weather_payload.get("humidity")
        pty = self._weather_payload.get("pty")
        pop = self._weather_payload.get("pop")
        level = self._weather_payload.get("pop_level")
        kind = self._weather_payload.get("icon_kind")
        text = _format_weather_line(
            self._current_language,
            summary_en,
            summary_ko,
            temp_c,
            humidity,
            pty,
            pop,
        )
        self.weather_label.setText(text)
        self._apply_weather_level_color(level)
        if kind and self._weather_icon_size:
            if kind != self._weather_kind:
                self._weather_kind = kind
            icon = _build_weather_icon(kind, self._weather_icon_size)
            self.weather_icon.setPixmap(icon)

    def apply_scale(self, scale: float):
        if self.layout_root:
            margin = max(12, int(24 * scale))
            spacing = max(8, int(16 * scale))
            self.layout_root.setContentsMargins(margin, margin, margin, margin)
            self.layout_root.setSpacing(spacing)
        icon_size = max(16, int(22 * scale))
        if self.weather_icon:
            if icon_size != self._weather_icon_size:
                self._weather_icon_size = icon_size
            self.weather_icon.setFixedSize(icon_size, icon_size)
            if self._weather_payload and self._weather_payload.get("icon_kind"):
                self.weather_icon.setPixmap(_build_weather_icon(self._weather_payload["icon_kind"], icon_size))
        if self.cards_layout:
            self.cards_layout.setSpacing(max(8, int(16 * scale)))
        side_target = max(120, int(400 * scale))
        margin = max(12, int(24 * scale))
        available_width = max(0, self.width() - (margin * 2))
        spacing = self.cards_layout.spacing() if self.cards_layout else 0
        max_side_from_width = (available_width - spacing * 2) // 3 if available_width > 0 else side_target
        lang_height = 0
        if self.lang_button:
            lang_height = max(self.lang_button.height(), self.lang_button.sizeHint().height())
        layout_spacing = self.layout_root.spacing() if self.layout_root else 0
        available_height = self.height() - (margin * 2) - lang_height - (layout_spacing * 2)
        max_side_from_height = max(0, available_height)
        width_limit = max_side_from_width if max_side_from_width > 0 else side_target
        height_limit = max_side_from_height if max_side_from_height > 0 else side_target
        side = min(side_target, width_limit, height_limit)
        side = max(80, side)
        for card in self.cards:
            card.setFixedSize(side, side)
        qr_target = max(100, int(260 * scale))
        qr_limit = max(48, side - max(24, int(36 * scale)))
        self.qr_size = min(qr_target, qr_limit)
        if self.qr_label:
            qr_pixmap = self._build_qr_pixmap(STAMP_QR_URL, self.qr_size)
            if qr_pixmap:
                self.qr_label.setPixmap(qr_pixmap)




class MainWindow(QMainWindow):
    BASE_WIDTH = 1280
    BASE_HEIGHT = 720
    IDLE_TIMEOUT_MS = 10000
    DEFAULT_LANGUAGE = "English"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kiosk UI")
        self.resize(1280, 720)
        self.font_family = _resolve_font_family()
        self.current_language = self.DEFAULT_LANGUAGE
        self._last_route_page = None
        self._tour_window = None
        self.idle_timer = QTimer(self)
        self.idle_timer.setSingleShot(True)
        self.idle_timer.timeout.connect(self._show_standby)
        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self._update_seoul_clock)
        self._seoul_clock_midnight = None
        self._seoul_clock_offset = 0
        self._seoul_clock_start = None
        self.weather_timer = QTimer(self)
        self.weather_timer.setInterval(15 * 60 * 1000)
        self.weather_timer.timeout.connect(self._refresh_weather)
        self._build_ui()
        self._apply_style(1.0)
        self._apply_scale()
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)
        self._reset_idle_timer()
        self._show_standby()
        self._init_seoul_clock()
        self._update_seoul_clock()
        self.clock_timer.start()
        self._refresh_weather()
        self.weather_timer.start()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.standby_page = StandbyPage(self._show_language)
        self.language_page = LanguagePage(self._on_language_select)
        db_path = _resolve_kiosk_db_path()
        kiosk_data = _load_kiosk_data_from_db(db_path) or _load_kiosk_data(KIOSK_DATA_FILE)
        menu_data = _load_menu_descriptions(MENU_DESCRIPTION_FILE)
        _load_kiosk_location(kiosk_data, DEFAULT_KIOSK_ID)
        landmark_items = _collect_tour_places(kiosk_data)
        food_items = _collect_food_places(kiosk_data)
        menu_items = _collect_menu_items(menu_data, food_items, kiosk_data)
        self.route_input_page = RouteInputPage(
            on_submit=self._show_route_result,
            on_back=self._show_menu,
            on_category_select=self._show_category,
        )
        self.food_menu_page = MenuListPage(
            on_select=self._show_food_detail,
            on_back=self._show_route_input,
            items=menu_items,
        )
        self.food_detail_page = FoodDetailPage(
            on_back=self._show_food_menu,
            kiosk_data=kiosk_data,
            menu_data=menu_data,
        )
        self.food_restaurant_page = FoodRestaurantPage(
            on_submit=self._show_route_result,
            on_back=self._show_food_menu,
            items=food_items,
        )
        self.landmark_category_page = LandmarkCategoryPage(
            on_submit=self._show_route_result,
            on_back=self._show_route_input,
            items=landmark_items,
        )
        self.route_result_page = RouteResultPage(on_back=self._show_previous_route)
        self.travel_stamp_page = TravelStampPage(self._show_menu)
        self.menu_page = MenuPage(
            self._back_to_language,
            self._show_route_input,
            self._show_tour_kiosk,
            self._show_travel_stamp,
        )

        self.stack.addWidget(self.standby_page)
        self.stack.addWidget(self.language_page)
        self.stack.addWidget(self.route_input_page)
        self.stack.addWidget(self.food_menu_page)
        self.stack.addWidget(self.food_detail_page)
        self.stack.addWidget(self.food_restaurant_page)
        self.stack.addWidget(self.landmark_category_page)
        self.stack.addWidget(self.route_result_page)
        self.stack.addWidget(self.travel_stamp_page)
        self.stack.addWidget(self.menu_page)

    def _apply_style(self, scale: float):
        font = QFont(self.font_family)
        font.setPointSizeF(max(8, 10 * scale))
        self.setFont(font)
        self.setStyleSheet(
            f"""
            QMainWindow {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f5efe6, stop:0.55 #f1f4ff, stop:1 #e7f6f3);
            }}
            QWidget {{
                color: #111827;
            }}
            #title {{
                font-size: {max(16, int(26 * scale))}px;
                font-weight: 700;
                color: #111827;
            }}
            #heroTitle {{
                font-size: {max(18, int(30 * scale))}px;
                font-weight: 700;
                color: #111827;
            }}
            #sectionTitle {{
                font-size: {max(13, int(18 * scale))}px;
                font-weight: 700;
                color: #111827;
            }}
            #panel {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ffffff, stop:1 #f8fafc);
                border-radius: {max(12, int(18 * scale))}px;
                border: 1px solid #e5e7eb;
            }}
            #langBtn {{
                background: #111827;
                color: #ffffff;
                border-radius: {max(14, int(20 * scale))}px;
                padding: {max(16, int(24 * scale))}px {max(12, int(18 * scale))}px;
                font-weight: 700;
            }}
            #langBtn:hover {{
                background: #1f2937;
            }}
            #card {{
                border-radius: {max(12, int(20 * scale))}px;
            }}
            #cardTour {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #fde68a, stop:1 #fb7185);
                border-radius: {max(16, int(24 * scale))}px;
                border: 1px solid #e5e7eb;
            }}
            #cardRoute {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #93c5fd, stop:1 #34d399);
                border-radius: {max(16, int(24 * scale))}px;
                border: 1px solid #e5e7eb;
            }}
            #cardQr {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #c4b5fd, stop:1 #f9a8d4);
                border-radius: {max(16, int(24 * scale))}px;
                border: 1px solid #e5e7eb;
            }}
            #cardTitle {{
                font-size: {max(14, int(20 * scale))}px;
                font-weight: 700;
                color: #111827;
            }}
            #navBtn {{
                background: #1d4ed8;
                color: #ffffff;
                border-radius: {max(12, int(16 * scale))}px;
                padding: {max(8, int(12 * scale))}px {max(14, int(20 * scale))}px;
                font-weight: 700;
            }}
            #navBtn:hover {{
                background: #2563eb;
            }}
            #langPill {{
                background: #111827;
                color: #ffffff;
                border-radius: {max(12, int(16 * scale))}px;
                padding: {max(8, int(10 * scale))}px {max(12, int(16 * scale))}px;
                font-weight: 700;
            }}
            #langPill:hover {{
                background: #1f2937;
            }}
            #qrLabel {{
                color: #94a3b8;
                font-size: {max(11, int(16 * scale))}px;
                font-weight: 600;
            }}
            #qrCard {{
                background: #ffffff;
                border-radius: {max(10, int(16 * scale))}px;
                border: 1px solid #e5e7eb;
            }}
            #mapCard {{
                background: #ffffff;
                border-radius: {max(10, int(16 * scale))}px;
                border: 1px solid #e5e7eb;
            }}
            #mapLabel {{
                color: #94a3b8;
                font-size: {max(10, int(14 * scale))}px;
                font-weight: 600;
            }}
            #infoCard {{
                background: #ffffff;
                border-radius: {max(10, int(16 * scale))}px;
                border: 1px solid #e5e7eb;
            }}
            #infoDesc {{
                color: #111827;
                font-size: {max(11, int(15 * scale))}px;
            }}
            #menuCard {{
                background: #ffffff;
                border-radius: {max(12, int(18 * scale))}px;
                border: 1px solid #e5e7eb;
            }}
            #menuName {{
                color: #111827;
                font-size: {max(12, int(16 * scale))}px;
                font-weight: 700;
            }}
            #menuSubtitle {{
                color: #6b7280;
                font-size: {max(10, int(13 * scale))}px;
            }}
            #menuPrice {{
                color: #111827;
                font-size: {max(11, int(14 * scale))}px;
                font-weight: 600;
            }}
            #menuImage {{
                background: #f3f4f6;
                border-radius: {max(6, int(10 * scale))}px;
            }}
            #menuDesc {{
                color: #374151;
                font-size: {max(11, int(15 * scale))}px;
            }}
            #menuDesc[style="notice"] {{
                color: #dc2626;
            }}
            #menuListCard {{
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-left: {max(3, int(4 * scale))}px solid #93c5fd;
                border-radius: {max(12, int(18 * scale))}px;
            }}
            #menuListName {{
                color: #111827;
                font-size: {max(12, int(16 * scale))}px;
                font-weight: 700;
            }}
            #menuListPrice {{
                color: #1f2937;
                font-size: {max(11, int(14 * scale))}px;
                font-weight: 600;
            }}
            #menuListDesc {{
                color: #374151;
                font-size: {max(11, int(14 * scale))}px;
            }}
            #menuDetail {{
                background: #ffffff;
                border-radius: {max(10, int(16 * scale))}px;
                border: 1px solid #e5e7eb;
            }}
            #menuDetailTitle {{
                font-size: {max(12, int(18 * scale))}px;
                font-weight: 600;
            }}
            #menuDetailImage {{
                border-radius: {max(8, int(12 * scale))}px;
                background: #f3f4f6;
            }}
            #menuDetailText {{
                color: #4b5563;
                font-size: {max(10, int(14 * scale))}px;
            }}
            #keyBtn {{
                background: #ffffff;
                color: #111827;
                border: 1px solid #d1d5db;
                border-radius: {max(12, int(16 * scale))}px;
                padding: {max(10, int(16 * scale))}px {max(8, int(12 * scale))}px;
                min-height: {max(36, int(48 * scale))}px;
                font-weight: 700;
            }}
            #keyBtn:hover {{
                background: #f3f4f6;
            }}
            #inputField {{
                background: #ffffff;
                color: #111827;
                border: 1px solid #d1d5db;
                border-radius: {max(12, int(16 * scale))}px;
                padding: {max(10, int(14 * scale))}px;
                font-size: {max(12, int(18 * scale))}px;
            }}
            #statusLabel {{
                color: #6b7280;
                font-size: {max(10, int(14 * scale))}px;
            }}
            #locationLabel {{
                color: #6b7280;
                font-size: {max(10, int(16 * scale))}px;
                font-weight: 600;
            }}
            #timeLabel {{
                color: #6b7280;
                font-size: {max(10, int(16 * scale))}px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            #weatherLabel {{
                color: #6b7280;
                font-size: {max(9, int(14 * scale))}px;
                font-weight: 600;
            }}
            #categoryBtn {{
                border-radius: {max(16, int(22 * scale))}px;
                padding: {max(16, int(24 * scale))}px;
                font-size: {max(14, int(22 * scale))}px;
                font-weight: 700;
                color: #111827;
                border: 1px solid #e5e7eb;
                min-height: {max(60, int(90 * scale))}px;
            }}
            #categoryBtn[category="food"] {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #fed7aa, stop:1 #fda4af);
            }}
            #categoryBtn[category="landmark"] {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #bfdbfe, stop:1 #a7f3d0);
            }}
            #categoryBtn[category="restroom"] {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #e9d5ff, stop:1 #c7d2fe);
            }}
            #categoryBtn[category="info"] {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #fde68a, stop:1 #fdba74);
            }}
            #subcategoryBtn {{
                border-radius: {max(16, int(22 * scale))}px;
                padding: {max(14, int(22 * scale))}px;
                font-size: {max(14, int(20 * scale))}px;
                font-weight: 700;
                color: #111827;
                border: 1px solid #e5e7eb;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #fecaca, stop:1 #fde68a);
            }}
            #destinationLabel {{
                color: #111827;
                font-size: {max(12, int(20 * scale))}px;
                font-weight: 600;
            }}
            #routeQr {{
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: {max(10, int(14 * scale))}px;
                padding: 0;
            }}
            #routeQrHint {{
                color: #6b7280;
                font-size: {max(10, int(14 * scale))}px;
                font-weight: 600;
            }}
            QScrollArea {{
                background: transparent;
                border: 0;
            }}
            QTextEdit {{
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: {max(12, int(16 * scale))}px;
                padding: {max(10, int(14 * scale))}px;
                font-size: {max(11, int(15 * scale))}px;
            }}
            QScrollBar:vertical {{
                width: {max(12, int(16 * scale))}px;
                background: #e5e7eb;
                border-radius: {max(6, int(8 * scale))}px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: #9ca3af;
                border-radius: {max(6, int(8 * scale))}px;
                min-height: {max(24, int(40 * scale))}px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: none;
            }}
            """
        )

    def _on_language_select(self, lang: str):
        self.current_language = lang
        self.menu_page.set_language(lang)
        self.language_page.set_language(lang)
        self.route_input_page.set_language(lang)
        self.food_menu_page.set_language(lang)
        self.food_detail_page.set_language(lang)
        self.food_restaurant_page.set_language(lang)
        self.landmark_category_page.set_language(lang)
        self.route_result_page.set_language(lang)
        self.travel_stamp_page.set_language(lang)
        self.stack.setCurrentWidget(self.menu_page)
        QTimer.singleShot(0, self._apply_scale)

    def _back_to_language(self):
        self.stack.setCurrentWidget(self.language_page)

    def _show_menu(self):
        self.stack.setCurrentWidget(self.menu_page)
        QTimer.singleShot(0, self._apply_scale)

    def _init_seoul_clock(self):
        now = _seoul_now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        self._seoul_clock_midnight = midnight
        self._seoul_clock_offset = (now - midnight).total_seconds()
        self._seoul_clock_start = time.monotonic()

    def _current_seoul_time(self):
        if not self._seoul_clock_midnight or self._seoul_clock_start is None:
            self._init_seoul_clock()
        elapsed = self._seoul_clock_offset + (time.monotonic() - self._seoul_clock_start)
        if elapsed >= 86400:
            self._init_seoul_clock()
            elapsed = self._seoul_clock_offset + (time.monotonic() - self._seoul_clock_start)
        return self._seoul_clock_midnight + timedelta(seconds=int(elapsed))

    def _update_seoul_clock(self):
        now = self._current_seoul_time()
        weekday_map = ["월", "화", "수", "목", "금", "토", "일"]
        weekday = weekday_map[now.weekday()]
        self.menu_page.set_time_text(f"{now.strftime('%H:%M:%S')} {weekday}요일")

    def _refresh_weather(self):
        lat = KIOSK_LOCATION.get("lat")
        lng = KIOSK_LOCATION.get("lng")
        if lat is None or lng is None:
            self.menu_page.set_weather(None)
            return
        data = _fetch_kma_ultra_forecast(float(lat), float(lng))
        pop_data = _fetch_kma_village_forecast(float(lat), float(lng))
        if not data:
            self.menu_page.set_weather(None)
            return

        def _safe_int(value):
            try:
                return int(round(float(value)))
            except (TypeError, ValueError):
                return None

        temp_c = _safe_int(data.get("T1H"))
        humidity = _safe_int(data.get("REH"))
        pty = _safe_int(data.get("PTY"))
        sky = _safe_int(data.get("SKY"))
        pop = _safe_int(pop_data.get("POP")) if pop_data else None
        pop_level = _precip_level(pop)
        summary_en, summary_ko, icon_kind = _weather_summary_labels(pty, sky)
        payload = {
            "summary_en": summary_en,
            "summary_ko": summary_ko,
            "temp_c": temp_c,
            "humidity": humidity,
            "pty": pty,
            "pop": pop,
            "pop_level": pop_level,
            "icon_kind": icon_kind,
        }
        self.menu_page.set_weather(payload)

    def _show_route_input(self):
        self.stack.setCurrentWidget(self.route_input_page)
        QTimer.singleShot(0, self._apply_scale)

    def _show_tour_kiosk(self):
        if self._tour_window is None:
            self._tour_window = _load_tour_window(self.stack, self._show_menu)
            if self._tour_window:
                self.stack.addWidget(self._tour_window)
        if self._tour_window:
            self.stack.setCurrentWidget(self._tour_window)
            QTimer.singleShot(0, self._apply_scale)
        else:
            print("[tour] rootgut.py not available.", file=sys.stderr)

    def _show_travel_stamp(self):
        self.stack.setCurrentWidget(self.travel_stamp_page)
        QTimer.singleShot(0, self._apply_scale)

    def _show_category(self, category: str):
        if category == "food":
            self._show_food_category(category)
            return
        if category == "landmark":
            self.stack.setCurrentWidget(self.landmark_category_page)
            QTimer.singleShot(0, self._apply_scale)

    def _show_food_category(self, _category: str):
        self.stack.setCurrentWidget(self.food_menu_page)
        QTimer.singleShot(0, self._apply_scale)

    def _show_food_menu(self):
        self.stack.setCurrentWidget(self.food_menu_page)
        QTimer.singleShot(0, self._apply_scale)

    def _show_food_detail(self, menu_item: dict):
        if self.food_detail_page:
            self.food_detail_page.set_filter(menu_item.get("menu_name") if menu_item else None)
        self.stack.setCurrentWidget(self.food_detail_page)
        QTimer.singleShot(0, self._apply_scale)

    def _show_route_result(self, destination):
        self._last_route_page = self.stack.currentWidget()
        if isinstance(destination, dict):
            label = destination.get("label", "")
            self.route_result_page.set_destination(label)
            self.route_result_page.set_route_url(_build_directions_url(destination))
            self.route_result_page.set_destination_location(
                destination.get("lat"),
                destination.get("lng"),
                destination.get("address"),
            )
            self.route_result_page.set_destination_details(
                destination.get("description"),
                destination.get("image_url"),
            )
        else:
            self.route_result_page.set_destination(destination)
            self.route_result_page.set_route_url("")
            self.route_result_page.set_destination_location(None, None, None)
            self.route_result_page.set_destination_details(None, None)
        self.stack.setCurrentWidget(self.route_result_page)
        QTimer.singleShot(0, self._apply_scale)

    def _show_previous_route(self):
        target = self._last_route_page if self._last_route_page else self.route_input_page
        self.stack.setCurrentWidget(target)
        QTimer.singleShot(0, self._apply_scale)

    def _show_language(self):
        self.stack.setCurrentWidget(self.language_page)
        QTimer.singleShot(0, self._apply_scale)

    def _show_standby(self):
        self._reset_to_initial_state()
        self.stack.setCurrentWidget(self.standby_page)
        QTimer.singleShot(0, self._apply_scale)

    def _reset_to_initial_state(self):
        self.current_language = self.DEFAULT_LANGUAGE
        self._last_route_page = None
        self.menu_page.set_language(self.DEFAULT_LANGUAGE)
        self.language_page.set_language(self.DEFAULT_LANGUAGE)
        self.route_input_page.reset_state()
        self.route_input_page.set_language(self.DEFAULT_LANGUAGE)
        self.food_menu_page.reset_state()
        self.food_menu_page.set_language(self.DEFAULT_LANGUAGE)
        self.food_detail_page.reset_state()
        self.food_detail_page.set_language(self.DEFAULT_LANGUAGE)
        self.food_restaurant_page.reset_state()
        self.food_restaurant_page.set_language(self.DEFAULT_LANGUAGE)
        self.landmark_category_page.reset_state()
        self.landmark_category_page.set_language(self.DEFAULT_LANGUAGE)
        self.route_result_page.set_language(self.DEFAULT_LANGUAGE)
        self.travel_stamp_page.set_language(self.DEFAULT_LANGUAGE)

    def _reset_idle_timer(self):
        self.idle_timer.start(self.IDLE_TIMEOUT_MS)

    def eventFilter(self, source, event):
        if event.type() in (
            QEvent.MouseButtonPress,
            QEvent.MouseMove,
            QEvent.Wheel,
            QEvent.TouchBegin,
            QEvent.KeyPress,
        ):
            self._reset_idle_timer()
        return super().eventFilter(source, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_scale()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._apply_scale)

    def _apply_scale(self):
        w = max(1, self.width())
        h = max(1, self.height())
        outer_margin = 32
        available_w = max(1, w - outer_margin)
        available_h = max(1, h - outer_margin)
        scale = min(available_w / self.BASE_WIDTH, available_h / self.BASE_HEIGHT)
        scale = min(scale, 1.0)
        self._apply_style(scale)
        self.standby_page.apply_scale(scale)
        self.language_page.apply_scale(scale)
        self.route_input_page.apply_scale(scale)
        self.food_menu_page.apply_scale(scale)
        self.food_detail_page.apply_scale(scale)
        self.food_restaurant_page.apply_scale(scale)
        self.landmark_category_page.apply_scale(scale)
        self.route_result_page.apply_scale(scale)
        self.travel_stamp_page.apply_scale(scale)
        self.menu_page.apply_scale(scale)


class SquareCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return width


class ClickableCard(SquareCard):
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class KeyboardButton(QPushButton):
    def __init__(self, label: str):
        super().__init__(label)
        self.setObjectName("keyBtn")
        self.setCursor(Qt.PointingHandCursor)


class OnScreenKeyboard(QFrame):
    def __init__(self, on_key, on_backspace, on_clear, on_enter):
        super().__init__()
        self.on_key = on_key
        self.on_backspace = on_backspace
        self.on_clear = on_clear
        self.on_enter = on_enter
        self.space_btn = None
        self.back_btn = None
        self.clear_btn = None
        self.enter_btn = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        rows = [
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", ("Back", "backspace")],
            list("QWERTYUIOP[]\\"),
            list("ASDFGHJKL;'") + [("Enter", "enter")],
            list("ZXCVBNM,./"),
        ]
        row_padding = {
            2: 1,
            3: 2,
        }
        for row_index, row in enumerate(rows):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(6)
            pad = row_padding.get(row_index, 0)
            if pad:
                row_layout.addStretch(pad)
            for key in row:
                if isinstance(key, tuple):
                    label, action = key
                    btn = KeyboardButton(label)
                    if action == "backspace":
                        self.back_btn = btn
                        btn.clicked.connect(self.on_backspace)
                    elif action == "enter":
                        self.enter_btn = btn
                        btn.clicked.connect(self.on_enter)
                    row_layout.addWidget(btn, 1)
                else:
                    btn = KeyboardButton(key)
                    btn.clicked.connect(lambda _checked, value=key: self.on_key(value))
                    row_layout.addWidget(btn, 1)
            if pad:
                row_layout.addStretch(pad)
            layout.addLayout(row_layout)

        action_row = QHBoxLayout()
        action_row.setSpacing(6)

        self.space_btn = KeyboardButton("Space")
        self.space_btn.clicked.connect(lambda: self.on_key(" "))
        action_row.addWidget(self.space_btn, 4)

        self.clear_btn = KeyboardButton("Clear")
        self.clear_btn.clicked.connect(self.on_clear)
        action_row.addWidget(self.clear_btn, 1)

        layout.addLayout(action_row)


class RouteInputPage(QFrame):
    CATEGORIES = [
        ("route_category_food", "Food", "food"),
        ("route_category_landmark", "Landmarks", "landmark"),
        ("route_category_restroom", "Restrooms", "restroom"),
        ("route_category_info", "Tourist Info", "info"),
    ]

    def __init__(self, on_submit, on_back, on_category_select=None):
        super().__init__()
        self.on_submit = on_submit
        self.on_back = on_back
        self.on_category_select = on_category_select
        self.title_label = None
        self.back_button = None
        self.category_buttons = {}
        self._current_language = "English"
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(12)
        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("navBtn")
        _set_back_button_icon(self.back_button, "Back")
        self.back_button.clicked.connect(self._handle_back)
        header.addWidget(self.back_button, 0)

        self.title_label = QLabel("Destination Input")
        self.title_label.setObjectName("title")
        self.title_label.setAlignment(Qt.AlignCenter)
        header.addWidget(self.title_label, 1)
        header.addSpacing(60)
        layout.addLayout(header)

        list_wrap = QFrame()
        list_wrap.setObjectName("panel")
        list_layout = QGridLayout(list_wrap)
        list_layout.setContentsMargins(18, 18, 18, 18)
        list_layout.setHorizontalSpacing(12)
        list_layout.setVerticalSpacing(12)

        for index, (key, default, category) in enumerate(self.CATEGORIES):
            btn = QPushButton(default)
            btn.setObjectName("categoryBtn")
            btn.setProperty("category", category)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(
                lambda _checked, value_key=key, fallback=default, value_category=category: self._handle_category(
                    value_key, fallback, value_category
                )
            )
            self.category_buttons[key] = btn
            row, col = divmod(index, 2)
            list_layout.addWidget(btn, row, col)

        layout.addWidget(list_wrap, 1)

        self.set_language("English")

    def apply_scale(self, scale: float):
        margin = max(12, int(24 * scale))
        spacing = max(8, int(12 * scale))
        layout = self.layout()
        if layout:
            layout.setContentsMargins(margin, margin, margin, margin)
            layout.setSpacing(spacing)
        min_height = max(90, int(160 * scale))
        for btn in self.category_buttons.values():
            btn.setMinimumHeight(min_height)

    def reset_state(self):
        return

    def set_language(self, lang: str):
        self._current_language = lang
        title = _lang_value(lang, "route_input_title", "Destination Input")
        back = _lang_value(lang, "route_back", "Back")
        if self.title_label:
            self.title_label.setText(title)
        if self.back_button:
            _set_back_button_icon(self.back_button, back)
        for key, default, _category in self.CATEGORIES:
            btn = self.category_buttons.get(key)
            if btn:
                btn.setText(_lang_value(lang, key, default))

    def _handle_back(self):
        if self.on_back:
            self.on_back()

    def _handle_category(self, key: str, fallback: str, category: str):
        label = _lang_value(self._current_language, key, fallback)
        if category in ("food", "landmark") and self.on_category_select:
            self.on_category_select(category)
            return
        if self.on_submit:
            self.on_submit(label)


class MenuListPage(QFrame):
    def __init__(self, on_select, on_back, items):
        super().__init__()
        self.on_select = on_select
        self.on_back = on_back
        self.items = items
        self.items_by_name = {item.get("menu_name"): item for item in items if item.get("menu_name")}
        self.columns = 4
        self.title_label = None
        self.back_button = None
        self.header_spacer = None
        self.notice_label = None
        self.item_buttons = {}
        self.item_image_urls = {}
        self.empty_label = None
        self.scroll_area = None
        self.grid_wrap = None
        self.grid_layout = None
        self._current_language = "English"
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(12)
        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("navBtn")
        _set_back_button_icon(self.back_button, "Back")
        self.back_button.clicked.connect(self._handle_back)
        header.addWidget(self.back_button, 0)

        self.title_label = QLabel("Food Categories")
        self.title_label.setObjectName("title")
        self.title_label.setAlignment(Qt.AlignCenter)
        header.addWidget(self.title_label, 1)

        self.header_spacer = QWidget()
        self.header_spacer.setFixedWidth(self.back_button.sizeHint().width())
        header.addWidget(self.header_spacer, 0)
        layout.addLayout(header)

        if not self.items:
            self.empty_label = QLabel("No menus available.")
            self.empty_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.empty_label, 1)
        else:
            self.scroll_area = QScrollArea()
            self.scroll_area.setWidgetResizable(True)
            self.scroll_area.setFrameShape(QFrame.NoFrame)
            self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

            self.grid_wrap = QWidget()
            self.grid_layout = QGridLayout(self.grid_wrap)
            self.grid_layout.setSpacing(12)
            self.grid_layout.setContentsMargins(0, 0, 0, 0)

            for index, item in enumerate(self.items):
                menu_name = item.get("menu_name") or "Menu"
                display_name = self._display_name(menu_name)
                card = ClickableCard()
                card.setObjectName("menuCard")
                card.setCursor(Qt.PointingHandCursor)
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(10, 10, 10, 10)
                card_layout.setSpacing(8)

                image = QLabel("")
                image.setObjectName("menuImage")
                image.setAlignment(Qt.AlignCenter)
                image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                card_layout.addWidget(image, 1)

                name_label = QLabel(display_name)
                name_label.setObjectName("menuName")
                name_label.setAlignment(Qt.AlignCenter)
                name_label.setWordWrap(True)
                card_layout.addWidget(name_label, 0)

                subtitle_label = QLabel(self._subtitle_for(menu_name))
                subtitle_label.setObjectName("menuSubtitle")
                subtitle_label.setAlignment(Qt.AlignCenter)
                subtitle_label.setWordWrap(True)
                card_layout.addWidget(subtitle_label, 0)

                price_label = QLabel(self._price_for(menu_name))
                price_label.setObjectName("menuPrice")
                price_label.setAlignment(Qt.AlignCenter)
                price_label.setVisible(bool(price_label.text()))
                card_layout.addWidget(price_label, 0)

                card.clicked.connect(lambda value_name=menu_name: self._handle_item(value_name))
                self.item_buttons[menu_name] = card
                self.item_image_urls[menu_name] = item.get("image_url")
                row = index // self.columns
                col = index % self.columns
                self.grid_layout.addWidget(card, row, col)

            self.scroll_area.setWidget(self.grid_wrap)
            layout.addWidget(self.scroll_area, 1)
        self.set_language("English")

    def apply_scale(self, scale: float):
        margin = max(12, int(24 * scale))
        spacing = max(8, int(12 * scale))
        layout = self.layout()
        if layout:
            layout.setContentsMargins(margin, margin, margin, margin)
            layout.setSpacing(spacing)
        if self.header_spacer and self.back_button:
            spacer_width = self.back_button.width() or self.back_button.sizeHint().width()
            self.header_spacer.setFixedWidth(spacer_width)
        available_width = max(0, self.width() - (margin * 2))
        grid_spacing = self.grid_layout.spacing() if self.grid_layout else 0
        min_card = max(140, int(180 * scale))
        if available_width and min_card:
            max_columns = max(2, min(4, available_width // max(min_card, 1)))
        else:
            max_columns = self.columns
        if max_columns != self.columns:
            self.columns = max_columns
            self._relayout_cards()
        total_spacing = grid_spacing * (self.columns - 1) if grid_spacing else 0
        column_width = (available_width - total_spacing) // self.columns if available_width else 0
        card_width = int(column_width) if column_width else min_card
        card_height = int(card_width * 1.18)
        for card in self.item_buttons.values():
            card.setFixedSize(card_width, card_height)
            image = card.findChild(QLabel, "menuImage")
            if image:
                image.setFixedHeight(max(60, int(card_height * 0.58)))
        self._refresh_menu_images()
        if self.grid_layout:
            self.grid_layout.setSpacing(max(6, int(10 * scale)))

    def reset_state(self):
        return

    def set_language(self, lang: str):
        self._current_language = lang
        if self.title_label:
            self.title_label.setText(_lang_value(lang, "food_category_title", "Food Categories"))
        if self.back_button:
            _set_back_button_icon(self.back_button, _lang_value(lang, "route_back", "Back"))
        if self.empty_label:
            self.empty_label.setText(_lang_value(lang, "food_no_menus", "No menus available."))
        for menu_name, btn in self.item_buttons.items():
            label = btn.findChild(QLabel, "menuName")
            if label and menu_name:
                label.setText(self._display_name(menu_name))
            subtitle = btn.findChild(QLabel, "menuSubtitle")
            if subtitle and menu_name:
                subtitle.setText(self._subtitle_for(menu_name))
            price_label = btn.findChild(QLabel, "menuPrice")
            if price_label and menu_name:
                price_text = self._price_for(menu_name)
                price_label.setText(price_text)
                price_label.setVisible(bool(price_text))

    def _handle_back(self):
        if self.on_back:
            self.on_back()

    def _handle_item(self, menu_name: str):
        item = self.items_by_name.get(menu_name)
        if item and self.on_select:
            self.on_select(item)

    def _display_name(self, menu_name: str) -> str:
        item = self.items_by_name.get(menu_name, {})
        engname = item.get("engname") if isinstance(item, dict) else None
        return _display_menu_name(menu_name, engname, self._current_language)

    def _subtitle_for(self, menu_name: str) -> str:
        if not menu_name:
            return ""
        item = self.items_by_name.get(menu_name, {})
        engname = item.get("engname") if isinstance(item, dict) else None
        if _place_lang_code(self._current_language) == "ko":
            romanized = engname or _romanize_korean(menu_name)
            return romanized if romanized != menu_name else ""
        return menu_name

    def _price_for(self, menu_name: str) -> str:
        item = self.items_by_name.get(menu_name, {})
        if not isinstance(item, dict):
            return ""
        return item.get("price_display") or ""

    def _relayout_cards(self):
        if not self.grid_layout:
            return
        for index, (menu_name, card) in enumerate(self.item_buttons.items()):
            row = index // self.columns
            col = index % self.columns
            self.grid_layout.addWidget(card, row, col)

    def _refresh_menu_images(self):
        for menu_name, card in self.item_buttons.items():
            image_label = card.findChild(QLabel, "menuImage")
            if not image_label:
                continue
            image_url = self.item_image_urls.get(menu_name)
            image_path = _resolve_place_image_path(image_url or "")
            if image_path:
                scaled = _get_cached_pixmap(image_path, image_label.size(), keep_aspect=True)
                if scaled:
                    image_label.setPixmap(scaled)
                    image_label.setText("")
                    continue
            image_label.setPixmap(QPixmap())
            image_label.setText("")


class FoodDetailPage(QFrame):
    def __init__(self, on_back, kiosk_data, menu_data):
        super().__init__()
        self.on_back = on_back
        self.kiosk_data = kiosk_data or {}
        self.menu_data = menu_data or []
        self._current_language = "English"
        self._filter_menu_name = None
        self._selected_key = None
        self._selected_menu_data = None
        self.menu_items = []
        self.images_by_id = {}
        self.images_by_place = {}
        self.place_details = {}
        self.menu_desc_map = {}
        self.menu_image_size = QSize(320, 220)
        self.place_image_size = QSize(380, 260)
        self.detail_name_label = None
        self.place_photo_frame = None
        self.route_qr_card = None
        self.route_qr_label = None
        self.route_qr_hint_label = None
        self.route_qr_size = 200
        self._route_destination = None
        self._route_qr_signature = None
        self.full_menu_thumb_size = 64
        self.full_menu_item_padding = 6
        self.full_menu_item_spacing = 8
        self._build_data()
        self._build()
        self.set_language("English")
        self.set_filter(None)

    def _build_data(self):
        images = self.kiosk_data.get("place_images", [])
        self.images_by_id = {
            entry.get("image_id"): entry.get("url")
            for entry in images
            if entry.get("image_id") is not None
        }
        self.images_by_place = {}
        for entry in images:
            place_id = entry.get("place_id")
            if place_id is None:
                continue
            self.images_by_place.setdefault(place_id, []).append(entry)

        places = self.kiosk_data.get("places", [])
        food_place_ids = set()
        for place in places:
            if place.get("type") != "FOOD":
                continue
            place_id = place.get("place_id")
            if place_id is None:
                continue
            food_place_ids.add(place_id)
            self.place_details[place_id] = {
                "menus": place.get("menus", []),
                "food_info": place.get("food_info", {}),
                "images": self.images_by_place.get(place_id, []),
                "names": {},
                "short_desc": {},
                "addresses": {},
                "hours": {},
                "lat": place.get("lat"),
                "lng": place.get("lng"),
            }

        for entry in self.kiosk_data.get("place_i18n", []):
            place_id = entry.get("place_id")
            if place_id not in food_place_ids:
                continue
            lang = entry.get("lang")
            if not lang:
                continue
            details = self.place_details.get(place_id)
            if not details:
                continue
            name = entry.get("name")
            if name:
                details["names"][lang] = name
            short_desc = entry.get("short_desc")
            if short_desc:
                details["short_desc"][lang] = short_desc
            address = entry.get("address_text") or entry.get("address")
            if address:
                details["addresses"][lang] = address
            hours = entry.get("hours_text")
            if hours:
                details["hours"][lang] = hours

        self.menu_desc_map = {}
        for place_id, details in self.place_details.items():
            for menu in details.get("menus", []):
                name = menu.get("name")
                desc = menu.get("description")
                if name and desc:
                    self.menu_desc_map.setdefault((place_id, name), {})["ko"] = desc

        for entry in self.menu_data:
            place_id = entry.get("place_id")
            if place_id not in food_place_ids:
                continue
            menu_name = entry.get("menu_name")
            if not menu_name:
                continue
            lang = entry.get("lang")
            desc = entry.get("description")
            if not lang or not desc:
                continue
            self.menu_desc_map.setdefault((place_id, menu_name), {})[lang] = desc

        self.menu_items = []
        for place_id, details in self.place_details.items():
            for index, menu in enumerate(details.get("menus", [])):
                name = menu.get("name") or "Menu"
                menu_id = menu.get("menu_id")
                order = menu_id if menu_id is not None else index
                image_url = self.images_by_id.get(menu.get("image_id"))
                self.menu_items.append(
                    {
                        "key": (place_id, order),
                        "place_id": place_id,
                        "menu_name": name,
                        "menu_price": menu.get("price") or "",
                        "menu_image_url": image_url,
                        "menu_engname": menu.get("engname"),
                        "order": order,
                    }
                )
        self.menu_items.sort(key=lambda item: (item.get("place_id", 0), item.get("order", 0)))

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(12)
        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("navBtn")
        _set_back_button_icon(self.back_button, "Back")
        self.back_button.clicked.connect(self._handle_back)
        header.addWidget(self.back_button, 0)

        self.title_label = QLabel("Foods")
        self.title_label.setObjectName("title")
        self.title_label.setAlignment(Qt.AlignCenter)
        header.addWidget(self.title_label, 1)
        header.addSpacing(60)
        layout.addLayout(header)

        content_grid = QGridLayout()
        content_grid.setSpacing(12)

        self.detail_name_label = QLabel("")
        self.detail_name_label.setObjectName("heroTitle")
        font = self.detail_name_label.font()
        font.setPointSize(22)
        font.setBold(True)
        self.detail_name_label.setFont(font)
        self.detail_name_label.setVisible(False)

        self.menu_detail_frame = QFrame()
        self.menu_detail_frame.setObjectName("panel")
        menu_detail_wrap = QVBoxLayout(self.menu_detail_frame)
        menu_detail_wrap.setContentsMargins(14, 14, 14, 14)
        menu_detail_wrap.setSpacing(10)
        menu_detail_wrap.addWidget(self.detail_name_label)

        self.menu_detail_widget = QWidget()
        self.menu_detail_layout = QHBoxLayout(self.menu_detail_widget)
        self.menu_detail_layout.setContentsMargins(0, 0, 0, 0)
        self.menu_detail_layout.setSpacing(15)

        self.menu_image_label = QLabel()
        self.menu_image_label.setFixedSize(self.menu_image_size)
        self.menu_image_label.setScaledContents(True)
        self.menu_detail_layout.addWidget(self.menu_image_label)

        self.menu_desc_text = QTextEdit()
        self.menu_desc_text.setReadOnly(True)
        self.menu_desc_text.setFrameShape(QFrame.NoFrame)
        self.menu_detail_layout.addWidget(self.menu_desc_text, 1)

        menu_detail_wrap.addWidget(self.menu_detail_widget)
        self.menu_detail_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.place_image_label = QLabel()
        self.place_image_label.setFixedSize(self.place_image_size)
        self.place_image_label.setScaledContents(True)

        self.place_photo_frame = QFrame()
        self.place_photo_frame.setObjectName("panel")
        place_photo_wrap = QVBoxLayout(self.place_photo_frame)
        place_photo_wrap.setContentsMargins(16, 16, 16, 16)
        place_photo_wrap.setSpacing(8)
        place_photo_wrap.addStretch(1)
        place_photo_wrap.addWidget(self.place_image_label, 0, alignment=Qt.AlignCenter)
        place_photo_wrap.addStretch(1)

        self.place_info_frame = QFrame()
        self.place_info_frame.setObjectName("panel")
        place_info_wrap = QVBoxLayout(self.place_info_frame)
        place_info_wrap.setContentsMargins(16, 16, 16, 16)
        place_info_wrap.setSpacing(12)

        self.place_info_title_label = QLabel("Restaurant Info")
        self.place_info_title_label.setObjectName("sectionTitle")
        font = self.place_info_title_label.font()
        font.setPointSize(14)
        font.setBold(True)
        self.place_info_title_label.setFont(font)
        place_info_wrap.addWidget(self.place_info_title_label)

        self.route_qr_card = QFrame()
        self.route_qr_card.setObjectName("qrCard")
        route_qr_layout = QVBoxLayout(self.route_qr_card)
        route_qr_layout.setContentsMargins(8, 8, 8, 8)
        route_qr_layout.setSpacing(6)

        self.route_qr_label = QLabel(_lang_value("English", "route_qr_unavailable", "QR unavailable."))
        self.route_qr_label.setObjectName("routeQr")
        self.route_qr_label.setAlignment(Qt.AlignCenter)
        self.route_qr_label.setContentsMargins(0, 0, 0, 0)
        route_qr_layout.addWidget(self.route_qr_label, 1)

        self.route_qr_hint_label = QLabel("")
        self.route_qr_hint_label.setObjectName("routeQrHint")
        self.route_qr_hint_label.setAlignment(Qt.AlignCenter)
        route_qr_layout.addWidget(self.route_qr_hint_label)

        self.place_info_text = QTextEdit()
        self.place_info_text.setReadOnly(True)
        self.place_info_text.setFrameShape(QFrame.NoFrame)

        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(12)
        bottom_row.addWidget(self.route_qr_card, 0, Qt.AlignLeft | Qt.AlignTop)
        bottom_row.addWidget(self.place_info_text, 1)

        place_info_wrap.addLayout(bottom_row)
        self.place_info_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        if self.place_photo_frame:
            self.place_photo_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.full_menu_card = QFrame()
        self.full_menu_card.setObjectName("panel")
        full_menu_wrap = QVBoxLayout(self.full_menu_card)
        full_menu_wrap.setContentsMargins(12, 10, 12, 10)
        full_menu_wrap.setSpacing(8)

        self.full_menu_title_label = QLabel("Full Menu")
        self.full_menu_title_label.setObjectName("sectionTitle")
        font = self.full_menu_title_label.font()
        font.setPointSize(14)
        font.setBold(True)
        self.full_menu_title_label.setFont(font)
        full_menu_wrap.addWidget(self.full_menu_title_label)

        self.full_menu_scroll = QScrollArea()
        self.full_menu_scroll.setWidgetResizable(True)
        self.full_menu_scroll.setFrameShape(QFrame.NoFrame)
        self.full_menu_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.full_menu_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.full_menu_grid_widget = QWidget()
        self.full_menu_grid_layout = QGridLayout(self.full_menu_grid_widget)
        self.full_menu_grid_layout.setContentsMargins(0, 0, 0, 0)
        self.full_menu_grid_layout.setSpacing(8)
        self.full_menu_grid_layout.setAlignment(Qt.AlignTop)
        self.full_menu_scroll.setWidget(self.full_menu_grid_widget)
        full_menu_wrap.addWidget(self.full_menu_scroll, 1)

        self.full_menu_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        content_grid.addWidget(self.menu_detail_frame, 0, 0, 1, 2)
        if self.place_photo_frame:
            content_grid.addWidget(self.place_photo_frame, 1, 0)
        content_grid.addWidget(self.place_info_frame, 2, 0)
        content_grid.addWidget(self.full_menu_card, 1, 1, 2, 1)
        content_grid.setRowStretch(0, 2)
        content_grid.setRowStretch(1, 1)
        content_grid.setRowStretch(2, 1)
        content_grid.setColumnStretch(0, 1)
        content_grid.setColumnStretch(1, 1)

        layout.addLayout(content_grid, 1)

    def apply_scale(self, scale: float):
        margin = max(12, int(24 * scale))
        layout = self.layout()
        if layout:
            layout.setContentsMargins(margin, margin, margin, margin)
            layout.setSpacing(max(8, int(12 * scale)))
        menu_size = QSize(max(220, int(320 * scale)), max(150, int(220 * scale)))
        place_size = QSize(max(260, int(380 * scale)), max(180, int(260 * scale)))
        self.menu_image_size = menu_size
        self.place_image_size = place_size
        if self.menu_image_label:
            self.menu_image_label.setFixedSize(menu_size)
        if self.place_image_label:
            self.place_image_label.setFixedSize(place_size)
        if self.menu_desc_text:
            self.menu_desc_text.setMinimumHeight(max(120, int(180 * scale)))
        if self.place_info_text:
            self.place_info_text.setMinimumHeight(max(140, int(200 * scale)))
        if self.menu_detail_frame:
            self.menu_detail_frame.setMinimumHeight(max(200, int(260 * scale)))
        if self.place_photo_frame:
            self.place_photo_frame.setMinimumHeight(max(180, int(220 * scale)))
        if self.place_info_frame:
            self.place_info_frame.setMinimumHeight(max(200, int(260 * scale)))
        if self.full_menu_card:
            self.full_menu_card.setMinimumWidth(max(260, int(360 * scale)))
        self.route_qr_size = max(110, int(160 * scale))
        if self.route_qr_label:
            self.route_qr_label.setFixedSize(self.route_qr_size, self.route_qr_size)
        if self.route_qr_card:
            self.route_qr_card.setFixedSize(self.route_qr_size + 16, self.route_qr_size + 44)
        self.full_menu_thumb_size = max(48, int(60 * scale))
        self.full_menu_item_padding = max(4, int(6 * scale))
        self.full_menu_item_spacing = max(6, int(8 * scale))
        if self.full_menu_grid_layout:
            self.full_menu_grid_layout.setSpacing(self.full_menu_item_spacing)
        self._refresh_selected_menu()

    def reset_state(self):
        self.set_filter(None)

    def set_language(self, lang: str):
        self._current_language = lang
        if self.back_button:
            _set_back_button_icon(self.back_button, _lang_value(lang, "route_back", "Back"))
        if self.title_label:
            if self._filter_menu_name:
                display = _display_menu_name(self._filter_menu_name, self._menu_engname(self._filter_menu_name), lang)
                self.title_label.setText(display)
            else:
                self.title_label.setText(_lang_value(lang, "route_category_food", "Food"))
        if self.place_info_title_label:
            self.place_info_title_label.setText(_lang_value(lang, "food_restaurant_info", "Restaurant Info"))
        if self.full_menu_title_label:
            self.full_menu_title_label.setText(_lang_value(lang, "food_full_menu", "Full Menu"))
        self._select_default_menu()
        self._refresh_selected_menu()
        self._refresh_route_qr()

    def set_filter(self, menu_name: str):
        self._filter_menu_name = menu_name
        self._selected_key = None
        if self.title_label:
            if menu_name:
                display = _display_menu_name(menu_name, self._menu_engname(menu_name), self._current_language)
                self.title_label.setText(display)
            else:
                self.title_label.setText(_lang_value(self._current_language, "route_category_food", "Food"))
        self._select_default_menu()
        self._refresh_selected_menu()

    def _handle_back(self):
        if self.on_back:
            self.on_back()

    def _select_default_menu(self):
        items = self.menu_items
        if self._filter_menu_name:
            items = [item for item in items if item.get("menu_name") == self._filter_menu_name]
        if not items:
            self._selected_menu_data = None
            if self.detail_name_label:
                self.detail_name_label.setText(
                    _lang_value(self._current_language, "food_no_foods", "No foods available.")
                )
            self.menu_desc_text.setText(_lang_value(self._current_language, "food_no_description", "No description"))
            self._set_image_label(self.menu_image_label, None, self.menu_image_size)
            self.place_info_text.setText(
                _lang_value(self._current_language, "food_no_additional_info", "No additional info.")
            )
            self._set_image_label(self.place_image_label, None, self.place_image_size)
            self._route_destination = None
            self._populate_full_menu_grid(None, [])
            self._refresh_route_qr()
            return
        if self._selected_key:
            for item in items:
                if item.get("key") == self._selected_key:
                    self.set_selected_menu(item)
                    return
        self.set_selected_menu(items[0])

    def set_selected_menu(self, menu_data: dict):
        self._selected_menu_data = menu_data
        place_id = menu_data.get("place_id")
        menu_name = menu_data.get("menu_name") or ""
        menu_price = menu_data.get("menu_price") or ""
        self._selected_key = menu_data.get("key")

        display_name = _display_menu_name(menu_name, menu_data.get("menu_engname"), self._current_language)
        title = f"{display_name} ({menu_price})" if menu_price else display_name
        if self.detail_name_label:
            self.detail_name_label.setText(
                title or _lang_value(self._current_language, "food_menu_fallback", "Menu")
            )

        desc = self._menu_description(place_id, menu_name)
        self.menu_desc_text.setText(
            desc or _lang_value(self._current_language, "food_no_description", "No description")
        )

        self._set_image_label(self.menu_image_label, menu_data.get("menu_image_url"), self.menu_image_size)

        details = self.place_details.get(place_id, {})
        info_lines = []
        place_name = self._place_name(place_id)
        if place_name:
            label = _lang_value(self._current_language, "food_restaurant_label", "Restaurant")
            info_lines.append(f"{label}: {place_name}")
        short_desc = self._place_text(details.get("short_desc", {}))
        if short_desc:
            info_lines.append(short_desc)
        hours = self._place_text(details.get("hours", {}))
        if hours:
            info_lines.append(
                f"{_lang_value(self._current_language, 'food_hours_label', 'Hours')}: {hours}"
            )
        food_info = details.get("food_info", {})
        phone = food_info.get("infocenterfood") if isinstance(food_info, dict) else None
        reservation = food_info.get("reservationfood") if isinstance(food_info, dict) else None
        if phone:
            info_lines.append(
                f"{_lang_value(self._current_language, 'food_phone_label', 'Phone')}: {phone}"
            )
        if reservation:
            info_lines.append(
                f"{_lang_value(self._current_language, 'food_reservation_label', 'Reservation')}: {reservation}"
            )
        address = self._place_text(details.get("addresses", {}))
        if address:
            info_lines.append(
                f"{_lang_value(self._current_language, 'food_address_label', 'Address')}: {address}"
            )
        self.place_info_text.setText(
            "\n".join(info_lines)
            if info_lines
            else _lang_value(self._current_language, "food_no_additional_info", "No additional info.")
        )

        place_image_url = self._place_image_url(place_id)
        self._set_image_label(self.place_image_label, place_image_url, self.place_image_size)

        menus = details.get("menus", [])
        self._populate_full_menu_grid(place_id, menus)
        self._route_destination = {
            "label": place_name,
            "lat": details.get("lat"),
            "lng": details.get("lng"),
            "address": self._place_text(details.get("addresses", {})),
        }
        self._refresh_route_qr()

    def _refresh_selected_menu(self):
        if self._selected_menu_data:
            self.set_selected_menu(self._selected_menu_data)
        else:
            self._select_default_menu()

    def _place_name(self, place_id: int) -> str:
        details = self.place_details.get(place_id, {})
        names = details.get("names", {})
        name = self._place_text(names)
        if name:
            return name
        if place_id is None:
            return ""
        return _lang_value(self._current_language, "place_fallback", "Place {id}").format(id=place_id)

    def _place_text(self, values: dict) -> str:
        if not values:
            return ""
        lang_code = _place_lang_code(self._current_language)
        return (
            values.get(lang_code)
            or values.get("en")
            or values.get("ko")
            or next(iter(values.values()), "")
        )

    def _menu_description(self, place_id: int, menu_name: str) -> str:
        if not place_id or not menu_name:
            return ""
        descriptions = self.menu_desc_map.get((place_id, menu_name), {})
        if not descriptions:
            return ""
        lang_code = _menu_lang_code(self._current_language)
        return (
            descriptions.get(lang_code)
            or descriptions.get("en")
            or descriptions.get("ko")
            or next(iter(descriptions.values()), "")
        )

    def _refresh_route_qr(self):
        if not self.route_qr_label:
            return
        if not self._route_destination:
            self._set_route_qr_unavailable()
            return
        url = _build_directions_url(self._route_destination)
        if not url:
            self._set_route_qr_unavailable()
            return
        signature = (url, self.route_qr_size)
        if signature == self._route_qr_signature:
            return
        pixmap = _build_qr_pixmap(url, self.route_qr_size)
        if pixmap:
            self.route_qr_label.setPixmap(pixmap)
            self.route_qr_label.setFixedSize(self.route_qr_size, self.route_qr_size)
            self.route_qr_label.setText("")
            if self.route_qr_hint_label:
                self.route_qr_hint_label.setText(
                    _lang_value(self._current_language, "route_google_maps", "Google Maps")
                )
            self._route_qr_signature = signature
        else:
            self._set_route_qr_unavailable()

    def _set_route_qr_unavailable(self):
        if not self.route_qr_label:
            return
        self.route_qr_label.setPixmap(QPixmap())
        self.route_qr_label.setText(_lang_value(self._current_language, "route_qr_unavailable", "QR unavailable."))
        if self.route_qr_hint_label:
            self.route_qr_hint_label.setText("")
        self._route_qr_signature = None

    def _menu_engname(self, menu_name: str):
        if not menu_name:
            return None
        for item in self.menu_items:
            if item.get("menu_name") == menu_name and item.get("menu_engname"):
                return item.get("menu_engname")
        return None

    def _place_image_url(self, place_id: int):
        for img in self.place_details.get(place_id, {}).get("images", []):
            if img.get("kind") in ("PHOTO", "THUMBNAIL"):
                url = img.get("url")
                if url:
                    return url
        return None

    def _set_image_label(self, label: QLabel, image_url: str, size: QSize):
        if not label:
            return
        image_path = _resolve_place_image_path(image_url or "")
        if image_path:
            pixmap = _get_cached_pixmap(image_path, size, keep_aspect=True)
            if pixmap:
                label.setPixmap(pixmap)
                return
        placeholder = QPixmap(size)
        placeholder.fill(QColor("lightgray"))
        label.setPixmap(placeholder)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

    def _populate_full_menu_grid(self, place_id, menus):
        self._clear_layout(self.full_menu_grid_layout)
        if not menus:
            self.full_menu_grid_layout.addWidget(
                QLabel(_lang_value(self._current_language, "food_no_menu_info", "No menu info")),
                0,
                0,
            )
            return

        row = 0
        col = 0
        for menu in menus:
            item = QFrame()
            item.setObjectName("menuListCard")
            item_layout = QHBoxLayout(item)
            item_layout.setContentsMargins(12, self.full_menu_item_padding, 12, self.full_menu_item_padding)
            item_layout.setSpacing(self.full_menu_item_spacing)

            thumb = QLabel()
            thumb.setFixedSize(self.full_menu_thumb_size, self.full_menu_thumb_size)
            thumb.setScaledContents(True)
            image_url = self.images_by_id.get(menu.get("image_id"))
            self._set_image_label(
                thumb,
                image_url,
                QSize(self.full_menu_thumb_size, self.full_menu_thumb_size),
            )
            item_layout.addWidget(thumb, 0)

            text_layout = QVBoxLayout()
            text_layout.setSpacing(4)

            name = menu.get("name") or _lang_value(self._current_language, "food_menu_fallback", "Menu")
            display_name = _display_menu_name(name, menu.get("engname"), self._current_language)
            price = menu.get("price") or ""
            price_label_text = _lang_value(self._current_language, "food_price_label", "Price")
            name_label = QLabel(display_name)
            name_label.setObjectName("menuListName")
            price_label = QLabel(
                f"{price_label_text}: {price}" if price else f"{price_label_text}: -"
            )
            price_label.setObjectName("menuListPrice")
            text_layout.addWidget(name_label)
            text_layout.addWidget(price_label)

            desc = self._menu_description(place_id, name) if place_id else ""
            if not desc:
                desc = menu.get("description") or ""
            if desc:
                desc_label = QLabel(desc)
                desc_label.setObjectName("menuListDesc")
                desc_label.setWordWrap(True)
                text_layout.addWidget(desc_label)

            text_layout.addStretch(1)
            item_layout.addLayout(text_layout, 1)

            item.setMinimumHeight(self.full_menu_thumb_size + self.full_menu_item_padding * 2)
            self.full_menu_grid_layout.addWidget(item, row, col)
            row += 1


class FoodRestaurantPage(QFrame):
    def __init__(self, on_submit, on_back, items):
        super().__init__()
        self.on_submit = on_submit
        self.on_back = on_back
        self.items = items
        self.items_by_id = {item["place_id"]: item for item in items}
        self.title_label = None
        self.back_button = None
        self.menu_image = None
        self.menu_desc = None
        self.item_buttons = {}
        self.empty_label = None
        self.scroll_area = None
        self.grid_wrap = None
        self.grid_layout = None
        self._current_language = "English"
        self._current_menu_name = None
        self._current_place_ids = []
        self._current_menu_descriptions = {}
        self._current_menu_image_url = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(12)
        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("navBtn")
        _set_back_button_icon(self.back_button, "Back")
        self.back_button.clicked.connect(self._handle_back)
        header.addWidget(self.back_button, 0)

        self.title_label = QLabel("Restaurants")
        self.title_label.setObjectName("title")
        self.title_label.setAlignment(Qt.AlignCenter)
        header.addWidget(self.title_label, 1)
        header.addSpacing(60)
        layout.addLayout(header)

        info_row = QHBoxLayout()
        info_row.setSpacing(8)

        self.menu_image = QLabel("")
        self.menu_image.setObjectName("menuImage")
        self.menu_image.setAlignment(Qt.AlignCenter)
        self.menu_image.setMinimumSize(140, 100)
        self.menu_image.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        info_row.addWidget(self.menu_image, 0)

        self.menu_desc = QLabel("")
        self.menu_desc.setObjectName("menuDesc")
        self.menu_desc.setWordWrap(True)
        self.menu_desc.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.menu_desc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        info_row.addWidget(self.menu_desc, 1)

        layout.addLayout(info_row)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.grid_wrap = QWidget()
        self.grid_layout = QGridLayout(self.grid_wrap)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area.setWidget(self.grid_wrap)
        layout.addWidget(self.scroll_area, 1)

        self.empty_label = QLabel("No restaurants available.")
        self.empty_label.setAlignment(Qt.AlignCenter)

        self._refresh_grid()
        self.set_language("English")

    def apply_scale(self, scale: float):
        margin = max(12, int(24 * scale))
        spacing = max(6, int(8 * scale))
        layout = self.layout()
        if layout:
            layout.setContentsMargins(margin, margin, margin, margin)
            layout.setSpacing(spacing)
        min_height = max(60, int(90 * scale))
        for btn in self.item_buttons.values():
            btn.setMinimumHeight(min_height)
            btn.setMaximumHeight(min_height)
        if self.grid_layout:
            self.grid_layout.setSpacing(max(8, int(12 * scale)))
        if self.menu_image:
            self.menu_image.setFixedSize(max(140, int(200 * scale)), max(100, int(150 * scale)))
        self._refresh_menu_image()

    def reset_state(self):
        self.set_menu(None)

    def set_language(self, lang: str):
        self._current_language = lang
        if self.title_label:
            title = self._current_menu_name or _lang_value(lang, "food_restaurants_title", "Restaurants")
            self.title_label.setText(title)
        if self.back_button:
            _set_back_button_icon(self.back_button, _lang_value(lang, "route_back", "Back"))
        if self.empty_label:
            self.empty_label.setText(_lang_value(lang, "food_no_restaurants", "No restaurants available."))
        for place_id, btn in self.item_buttons.items():
            btn.setText(self._label_for(place_id))
        if self.menu_desc is not None:
            self.menu_desc.setText(self._menu_description())

    def set_menu(self, menu_item: dict):
        self._current_menu_name = None
        self._current_place_ids = []
        self._current_menu_descriptions = {}
        self._current_menu_image_url = None
        if menu_item:
            self._current_menu_name = menu_item.get("menu_name")
            self._current_place_ids = menu_item.get("place_ids", [])
            self._current_menu_descriptions = menu_item.get("descriptions", {})
            self._current_menu_image_url = menu_item.get("image_url")
        self._refresh_grid()
        self.set_language(self._current_language)
        self._refresh_menu_image()

    def _refresh_grid(self):
        if not self.grid_layout:
            return
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        self.item_buttons = {}
        place_ids = [pid for pid in self._current_place_ids if pid in self.items_by_id]
        if not place_ids:
            if self.scroll_area and self.empty_label:
                self.scroll_area.setWidget(self.empty_label)
            return
        if self.scroll_area and self.grid_wrap:
            self.scroll_area.setWidget(self.grid_wrap)
        for index, place_id in enumerate(place_ids):
            btn = QPushButton(self._label_for(place_id))
            btn.setObjectName("subcategoryBtn")
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _checked, value_id=place_id: self._handle_item(value_id))
            self.item_buttons[place_id] = btn
            row = index // 2
            col = index % 2
            self.grid_layout.addWidget(btn, row, col)

    def _label_for(self, place_id: int) -> str:
        item = self.items_by_id.get(place_id)
        if not item:
            return _lang_value(self._current_language, "route_category_food", "Food")
        lang_code = _place_lang_code(self._current_language)
        names = item.get("names", {})
        return names.get(lang_code) or names.get("en") or names.get("ko") or item.get("fallback_name", "Food")

    def _address_for(self, place_id: int):
        item = self.items_by_id.get(place_id)
        if not item:
            return None
        lang_code = _place_lang_code(self._current_language)
        addresses = item.get("addresses", {})
        return (
            addresses.get(lang_code)
            or addresses.get("en")
            or addresses.get("ko")
            or item.get("fallback_address")
        )

    def _desc_for(self, place_id: int):
        item = self.items_by_id.get(place_id)
        if not item:
            return None
        lang_code = _place_lang_code(self._current_language)
        descriptions = item.get("descriptions", {})
        return (
            descriptions.get(lang_code)
            or descriptions.get("en")
            or descriptions.get("ko")
            or item.get("fallback_desc")
        )

    def _menu_description(self) -> str:
        if not self._current_menu_descriptions:
            return ""
        lang_code = _menu_lang_code(self._current_language)
        return (
            self._current_menu_descriptions.get(lang_code)
            or self._current_menu_descriptions.get("en")
            or next(iter(self._current_menu_descriptions.values()), "")
        )

    def _refresh_menu_image(self):
        if not self.menu_image:
            return
        image_path = _resolve_place_image_path(self._current_menu_image_url or "")
        if not image_path:
            self.menu_image.setPixmap(QPixmap())
            self.menu_image.setText("")
            return
        target_size = self.menu_image.size()
        pixmap = _get_cached_pixmap(image_path, target_size, keep_aspect=True)
        if not pixmap:
            self.menu_image.setPixmap(QPixmap())
            self.menu_image.setText("")
            return
        self.menu_image.setPixmap(pixmap)
        self.menu_image.setText("")

    def _handle_back(self):
        if self.on_back:
            self.on_back()

    def _handle_item(self, place_id: int):
        item = self.items_by_id.get(place_id, {})
        label = self._label_for(place_id)
        address = self._address_for(place_id)
        description = self._desc_for(place_id)
        if self.on_submit:
            self.on_submit(
                {
                    "label": label,
                    "lat": item.get("lat"),
                    "lng": item.get("lng"),
                    "address": address,
                    "description": description,
                    "image_url": item.get("image_url"),
                }
            )


class LandmarkCategoryPage(QFrame):
    def __init__(self, on_submit, on_back, items):
        super().__init__()
        self.on_submit = on_submit
        self.on_back = on_back
        self.items = items
        self.items_by_id = {item["place_id"]: item for item in items}
        self.title_label = None
        self.back_button = None
        self.item_buttons = {}
        self.empty_label = None
        self._current_language = "English"
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(12)
        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("navBtn")
        _set_back_button_icon(self.back_button, "Back")
        self.back_button.clicked.connect(self._handle_back)
        header.addWidget(self.back_button, 0)

        self.title_label = QLabel("Landmarks")
        self.title_label.setObjectName("title")
        self.title_label.setAlignment(Qt.AlignCenter)
        header.addWidget(self.title_label, 1)
        header.addSpacing(60)
        layout.addLayout(header)

        if not self.items:
            self.empty_label = QLabel("No landmarks available.")
            self.empty_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.empty_label, 1)
        else:
            grid = QGridLayout()
            grid.setSpacing(16)
            grid.setContentsMargins(0, 0, 0, 0)

            for index, item in enumerate(self.items):
                label = item.get("fallback_name", "Landmark")
                btn = QPushButton(label)
                btn.setObjectName("subcategoryBtn")
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                btn.setCursor(Qt.PointingHandCursor)
                place_id = item["place_id"]
                btn.clicked.connect(lambda _checked, value_id=place_id: self._handle_item(value_id))
                self.item_buttons[place_id] = btn
                row = index // 2
                col = index % 2
                grid.addWidget(btn, row, col)

            layout.addLayout(grid, 1)

        self.set_language("English")

    def apply_scale(self, scale: float):
        margin = max(12, int(24 * scale))
        spacing = max(8, int(12 * scale))
        layout = self.layout()
        if layout:
            layout.setContentsMargins(margin, margin, margin, margin)
            layout.setSpacing(spacing)
        min_height = max(70, int(110 * scale))
        for btn in self.item_buttons.values():
            btn.setMinimumHeight(min_height)

    def reset_state(self):
        return

    def set_language(self, lang: str):
        self._current_language = lang
        if self.title_label:
            self.title_label.setText(_lang_value(lang, "route_category_landmark", "Landmarks"))
        if self.back_button:
            _set_back_button_icon(self.back_button, _lang_value(lang, "route_back", "Back"))
        if self.empty_label:
            self.empty_label.setText(_lang_value(lang, "landmarks_empty", "No landmarks available."))
        for place_id, btn in self.item_buttons.items():
            btn.setText(self._label_for(place_id))

    def _label_for(self, place_id: int) -> str:
        item = self.items_by_id.get(place_id)
        if not item:
            return _lang_value(self._current_language, "route_category_landmark", "Landmark")
        lang_code = _place_lang_code(self._current_language)
        names = item.get("names", {})
        return names.get(lang_code) or names.get("en") or names.get("ko") or item.get("fallback_name", "Landmark")

    def _address_for(self, place_id: int):
        item = self.items_by_id.get(place_id)
        if not item:
            return None
        lang_code = _place_lang_code(self._current_language)
        addresses = item.get("addresses", {})
        return (
            addresses.get(lang_code)
            or addresses.get("en")
            or addresses.get("ko")
            or item.get("fallback_address")
        )

    def _desc_for(self, place_id: int):
        item = self.items_by_id.get(place_id)
        if not item:
            return None
        lang_code = _place_lang_code(self._current_language)
        descriptions = item.get("descriptions", {})
        return (
            descriptions.get(lang_code)
            or descriptions.get("en")
            or descriptions.get("ko")
            or item.get("fallback_desc")
        )

    def _handle_back(self):
        if self.on_back:
            self.on_back()

    def _handle_item(self, place_id: int):
        item = self.items_by_id.get(place_id, {})
        label = self._label_for(place_id)
        address = self._address_for(place_id)
        description = self._desc_for(place_id)
        if self.on_submit:
            self.on_submit(
                {
                    "label": label,
                    "lat": item.get("lat"),
                    "lng": item.get("lng"),
                    "address": address,
                    "description": description,
                    "image_url": item.get("image_url"),
                }
            )


class RouteResultPage(QFrame):
    def __init__(self, on_back):
        super().__init__()
        self.on_back = on_back
        self.title_label = None
        self.destination_label = None
        self.info_card = None
        self.info_image = None
        self.info_desc = None
        self.qr_label = None
        self.qr_hint_label = None
        self.qr_card = None
        self.map_card = None
        self.map_label = None
        self.qr_size = 240
        self.map_size = QSize(0, 0)
        self.info_image_size = QSize(0, 0)
        self._route_url = ""
        self._destination_lat = None
        self._destination_lng = None
        self._destination_address = None
        self._destination_description = None
        self._destination_image_url = None
        self._last_loaded_image = None
        self._map_signature = None
        self.back_button = None
        self._current_language = "English"
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("navBtn")
        _set_back_button_icon(self.back_button, "Back")
        self.back_button.clicked.connect(self._handle_back)
        layout.addWidget(self.back_button, alignment=Qt.AlignLeft)

        self.title_label = QLabel("Route Guidance")
        self.title_label.setObjectName("title")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        self.destination_label = QLabel("Destination: -")
        self.destination_label.setObjectName("destinationLabel")
        self.destination_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.destination_label)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(12)

        info_row = QHBoxLayout()
        info_row.setSpacing(12)
        self.info_card = QFrame()
        self.info_card.setObjectName("infoCard")
        info_layout = QHBoxLayout(self.info_card)
        info_layout.setContentsMargins(12, 12, 12, 12)
        info_layout.setSpacing(8)

        self.info_image = QLabel("No image.")
        self.info_image.setAlignment(Qt.AlignCenter)
        self.info_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        info_layout.addWidget(self.info_image)

        self.info_desc = QLabel("No description.")
        self.info_desc.setObjectName("infoDesc")
        self.info_desc.setWordWrap(True)
        self.info_desc.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.info_desc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        info_layout.addWidget(self.info_desc)

        info_row.addWidget(self.info_card, 1)
        content_layout.addLayout(info_row)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        self.qr_card = QFrame()
        self.qr_card.setObjectName("qrCard")
        qr_layout = QVBoxLayout(self.qr_card)
        qr_layout.setContentsMargins(8, 8, 8, 8)
        qr_layout.setSpacing(6)

        self.qr_label = QLabel("QR unavailable.")
        self.qr_label.setObjectName("routeQr")
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setContentsMargins(0, 0, 0, 0)
        qr_layout.addWidget(self.qr_label, 1)

        self.qr_hint_label = QLabel("")
        self.qr_hint_label.setObjectName("routeQrHint")
        self.qr_hint_label.setAlignment(Qt.AlignCenter)
        qr_layout.addWidget(self.qr_hint_label)

        self.map_card = QFrame()
        self.map_card.setObjectName("mapCard")
        map_layout = QVBoxLayout(self.map_card)
        map_layout.setContentsMargins(8, 8, 8, 8)
        map_layout.setSpacing(6)

        self.map_label = QLabel("Map unavailable.")
        self.map_label.setObjectName("mapLabel")
        self.map_label.setAlignment(Qt.AlignCenter)
        self.map_label.setContentsMargins(0, 0, 0, 0)
        self.map_label.setScaledContents(True)
        self.map_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.map_label.setMinimumSize(0, 0)
        map_layout.addWidget(self.map_label, 1)

        bottom_row.addWidget(self.qr_card, 1)
        bottom_row.addWidget(self.map_card, 2)
        content_layout.addLayout(bottom_row, 1)
        layout.addLayout(content_layout, 1)

    def apply_scale(self, scale: float):
        layout = self.layout()
        if layout:
            margin = max(12, int(24 * scale))
            spacing = max(8, int(12 * scale))
            layout.setContentsMargins(margin, margin, margin, margin)
            layout.setSpacing(spacing)
        else:
            margin = max(12, int(24 * scale))
            spacing = max(8, int(12 * scale))

        available_width = max(0, self.width() - (margin * 2))
        bottom_available = max(0, available_width - spacing)
        max_qr_card_width = max(120, bottom_available // 3) if bottom_available > 0 else 0
        max_qr_size = max(80, max_qr_card_width - 16) if max_qr_card_width else 0

        qr_target = max(160, int(260 * scale))
        if max_qr_size:
            self.qr_size = min(qr_target, max_qr_size)
        else:
            self.qr_size = qr_target

        qr_card_width = self.qr_size + 16
        qr_card_height = self.qr_size + 44
        map_width = max(120, bottom_available - qr_card_width) if bottom_available else max(240, int(460 * scale))
        map_height = max(140, qr_card_height)

        self.map_size = QSize(map_width, map_height)
        self.info_image_size = QSize(max(220, int(360 * scale)), max(140, int(220 * scale)))
        if self.qr_card:
            self.qr_card.setFixedSize(qr_card_width, qr_card_height)
        if self.map_card and self.qr_card:
            self.map_card.setFixedHeight(self.qr_card.height())
            self.map_card.setMaximumWidth(map_width)
        self._refresh_qr()
        self._refresh_map()
        self._refresh_info()

    def set_destination(self, destination: str):
        text = destination.strip() if destination else "-"
        template = _lang_value(self._current_language, "route_result_label", "Destination: {text}")
        self.destination_label.setText(template.format(text=text))
        if not destination:
            self.set_destination_details(None, None)

    def set_destination_details(self, description: str, image_url: str):
        self._destination_description = description
        self._destination_image_url = image_url
        self._refresh_info()

    def set_destination_location(self, lat, lng, address=None):
        self._destination_lat = lat
        self._destination_lng = lng
        self._destination_address = address
        self._refresh_map()

    def set_route_url(self, url: str):
        self._route_url = url or ""
        self._refresh_qr()

    def _refresh_qr(self):
        if not self.qr_label:
            return
        if not self._route_url:
            self.qr_label.setPixmap(QPixmap())
            self.qr_label.setText(_lang_value(self._current_language, "route_qr_unavailable", "QR unavailable."))
            if self.qr_card:
                self.qr_card.setFixedSize(self.qr_size + 16, self.qr_size + 44)
            if self.qr_hint_label:
                self.qr_hint_label.setText("")
            return
        pixmap = _build_qr_pixmap(self._route_url, self.qr_size)
        if pixmap:
            self.qr_label.setPixmap(pixmap)
            self.qr_label.setFixedSize(self.qr_size, self.qr_size)
            self.qr_label.setText("")
            if self.qr_card:
                self.qr_card.setFixedSize(self.qr_size + 16, self.qr_size + 44)
            if self.qr_hint_label:
                self.qr_hint_label.setText(
                    _lang_value(self._current_language, "route_google_maps", "Google Maps")
                )
        else:
            self.qr_label.setPixmap(QPixmap())
            self.qr_label.setText(_lang_value(self._current_language, "route_qr_unavailable", "QR unavailable."))
            if self.qr_card:
                self.qr_card.setFixedSize(self.qr_size + 16, self.qr_size + 44)
            if self.qr_hint_label:
                self.qr_hint_label.setText("")

    def _refresh_map(self):
        if not self.map_label:
            return
        lat, lng = _resolve_destination_coords(
            self._destination_lat,
            self._destination_lng,
            self._destination_address,
        )
        if lat is None or lng is None:
            if os.environ.get("GOOGLE_MAPS_DEBUG", "").strip().lower() in ("1", "true", "yes"):
                print("[map] Missing destination coords", file=sys.stderr)
            self.map_label.setPixmap(QPixmap())
            self.map_label.setText(
                _lang_value(self._current_language, "route_map_unavailable", "Map unavailable.")
            )
            self._map_signature = None
            return
        if self.map_label and self.map_label.size().isValid():
            target_size = self.map_label.size()
        else:
            target_size = self.map_size if self.map_size.isValid() else QSize(480, 260)
        signature = (lat, lng, target_size.width(), target_size.height())
        if signature == self._map_signature:
            return
        pixmap = _fetch_static_map_pixmap(
            lat,
            lng,
            target_size.width(),
            target_size.height(),
        )
        if pixmap:
            cropped = _crop_pixmap_to_size(pixmap, target_size)
            self.map_label.setPixmap(cropped)
            self.map_label.setText("")
            self._map_signature = signature
        else:
            self.map_label.setPixmap(QPixmap())
            self.map_label.setText(
                _lang_value(self._current_language, "route_map_unavailable", "Map unavailable.")
            )
            self._map_signature = None

    def _refresh_info(self):
        if not self.info_image or not self.info_desc:
            return
        description = (self._destination_description or "").strip()
        if description:
            self.info_desc.setText(description)
        else:
            self.info_desc.setText(_lang_value(self._current_language, "food_no_description", "No description"))
        image_path = _resolve_place_image_path(self._destination_image_url or "")
        if not image_path:
            self.info_image.setPixmap(QPixmap())
            self.info_image.setText(_lang_value(self._current_language, "route_no_image", "No image."))
            self._last_loaded_image = None
            return
        target_size = self.info_image_size if self.info_image_size.isValid() else QSize(360, 220)
        signature = (str(image_path), target_size.width(), target_size.height())
        if signature == self._last_loaded_image:
            return
        self.info_image.setFixedSize(target_size)
        pixmap = _get_cached_pixmap(image_path, target_size, keep_aspect=True)
        if not pixmap:
            self.info_image.setPixmap(QPixmap())
            self.info_image.setText(_lang_value(self._current_language, "route_no_image", "No image."))
            self._last_loaded_image = None
            return
        self.info_image.setPixmap(pixmap)
        self.info_image.setText("")
        self._last_loaded_image = signature

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_map()

    def set_language(self, lang: str):
        self._current_language = lang
        if self.title_label:
            self.title_label.setText(_lang_value(lang, "route_result_title", "Route Guidance"))
        if self.back_button:
            _set_back_button_icon(self.back_button, _lang_value(lang, "route_back", "Back"))
        current = self.destination_label.text() if self.destination_label else ""
        if current:
            if ":" in current:
                current_text = current.split(":", 1)[-1].strip()
            else:
                current_text = current
        else:
            current_text = "-"
        template = _lang_value(lang, "route_result_label", "Destination: {text}")
        if self.destination_label:
            self.destination_label.setText(template.format(text=current_text))
        self._refresh_qr()
        self._refresh_map()
        self._refresh_info()

    def _handle_back(self):
        if self.on_back:
            self.on_back()


class StandbyPage(QFrame):
    def __init__(self, on_activate):
        super().__init__()
        self.on_activate = on_activate
        self.image_label = None
        self._pixmap = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_label.setScaledContents(True)
        layout.addWidget(self.image_label, 1)

        if TITLE_IMAGE.exists():
            self._pixmap = QPixmap(str(TITLE_IMAGE))
        else:
            self.image_label.setText("Missing title.png")

    def apply_scale(self, scale: float):
        self._update_pixmap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_pixmap()

    def sizeHint(self):
        return QSize(0, 0)

    def minimumSizeHint(self):
        return QSize(0, 0)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.on_activate:
            self.on_activate()
        super().mousePressEvent(event)

    def _update_pixmap(self):
        if not self._pixmap or not self.image_label:
            return
        target_size = self.image_label.size()
        if target_size.width() <= 0 or target_size.height() <= 0:
            return
        scaled = self._pixmap.scaled(
            target_size,
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

import json
import math
import os
import ssl
import sys
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

from PyQt5.QtCore import Qt, QEvent, QSize, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QFontDatabase, QIcon, QImage, QPainter, QPainterPath, QPen, QPalette, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStyle,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
KIOSK_DATA_FILE = PROJECT_DIR / "db-server" / "kiosk_data.json"
DEFAULT_KIOSK_ID = "KIOSK_001"
PLACE_IMAGE_DIR = PROJECT_DIR / "place_images"
DEFAULT_IMAGE_DIR = PROJECT_DIR / "db-server"
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
FONT_DIR = APP_DIR / "fonts"
TITLE_IMAGE = PROJECT_DIR / "title.png"
PREFERRED_FAMILIES = [
    "Noto Sans CJK KR",
    "Noto Sans CJK JP",
    "Noto Sans CJK SC",
    "Noto Sans CJK TC",
    "Noto Sans",
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


LANGUAGES = [
    "한국어",
    "English",
    "日本語",
    "简体中文",
    "繁體中文",
    "Deutsch",
    "Nederlands",
    "Svenska",
    "Français",
    "Italiano",
    "Español",
    "Português",
    "Русский",
    "Polski",
    "Čeština",
    "Українська",
    "Lietuvių",
    "Latviešu",
]

LANG_INFO = {
    "한국어": {
        "flags": "KR",
        "language_title": "언어",
        "tour": "관광지",
        "route": "길안내",
        "qr": "QR",
        "open": "열기",
        "route_input_title": "목적지 입력",
        "route_input_hint": "키보드를 눌러 목적지를 입력하세요.",
        "route_back": "뒤로",
        "route_result_title": "길 안내",
        "route_result_label": "목적지: {text}",
        "route_keyboard_space": "공백",
        "route_keyboard_back": "삭제",
        "route_keyboard_clear": "초기화",
        "route_keyboard_enter": "확인",
        "route_category_food": "음식",
        "route_category_landmark": "랜드마크",
        "route_category_restroom": "화장실",
        "route_category_info": "관광안내소",
        "food_category_title": "음식 카테고리",
        "food_korean": "한식",
        "food_snack": "분식",
        "food_cafe": "카페/디저트",
        "food_fast": "패스트푸드",
        "food_japanese": "일식",
        "food_chinese": "중식",
        "food_western": "양식",
        "food_convenience": "편의점/간식",
        "food_vegan": "채식/비건",
        "food_bar": "주점/펍",
    },
    "English": {
        "flags": "US",
        "language_title": "Language",
        "tour": "Attractions",
        "route": "Directions",
        "qr": "QR",
        "open": "Open",
        "route_input_title": "Destination Input",
        "route_input_hint": "Tap keyboard to enter destination.",
        "route_back": "Back",
        "route_result_title": "Route Guidance",
        "route_result_label": "Destination: {text}",
        "route_keyboard_space": "Space",
        "route_keyboard_back": "Back",
        "route_keyboard_clear": "Clear",
        "route_keyboard_enter": "Enter",
        "route_category_food": "Food",
        "route_category_landmark": "Landmarks",
        "route_category_restroom": "Restrooms",
        "route_category_info": "Tourist Info",
        "food_category_title": "Food Categories",
        "food_korean": "Korean",
        "food_snack": "Street Food",
        "food_cafe": "Cafe/Dessert",
        "food_fast": "Fast Food",
        "food_japanese": "Japanese",
        "food_chinese": "Chinese",
        "food_western": "Western",
        "food_convenience": "Convenience/Snacks",
        "food_vegan": "Vegetarian/Vegan",
        "food_bar": "Bar/Pub",
    },
    "日本語": {
        "flags": "JP",
        "language_title": "言語",
        "tour": "観光地",
        "route": "道案内",
        "qr": "QR",
        "open": "開く",
        "route_input_title": "目的地入力",
        "route_input_hint": "キーボードをタップして目的地を入力してください。",
        "route_back": "戻る",
        "route_result_title": "道案内",
        "route_result_label": "目的地: {text}",
        "route_keyboard_space": "スペース",
        "route_keyboard_back": "削除",
        "route_keyboard_clear": "クリア",
        "route_keyboard_enter": "決定",
    },
    "简体中文": {
        "flags": "CN",
        "language_title": "语言",
        "tour": "景点",
        "route": "路线",
        "qr": "QR",
        "open": "打开",
        "route_input_title": "目的地输入",
        "route_input_hint": "点击键盘输入目的地。",
        "route_back": "返回",
        "route_result_title": "路线指引",
        "route_result_label": "目的地: {text}",
        "route_keyboard_space": "空格",
        "route_keyboard_back": "退格",
        "route_keyboard_clear": "清空",
        "route_keyboard_enter": "确定",
    },
    "繁體中文": {
        "flags": "TW",
        "language_title": "語言",
        "tour": "景點",
        "route": "路線",
        "qr": "QR",
        "open": "開啟",
        "route_input_title": "目的地輸入",
        "route_input_hint": "點擊鍵盤輸入目的地。",
        "route_back": "返回",
        "route_result_title": "路線指引",
        "route_result_label": "目的地: {text}",
        "route_keyboard_space": "空格",
        "route_keyboard_back": "退格",
        "route_keyboard_clear": "清除",
        "route_keyboard_enter": "確認",
    },
    "Deutsch": {
        "flags": "DE",
        "language_title": "Sprache",
        "tour": "Sehenswürdigkeiten",
        "route": "Wegbeschreibung",
        "qr": "QR",
        "open": "Öffnen",
        "route_input_title": "Ziel eingeben",
        "route_input_hint": "Tippen Sie auf die Tastatur, um das Ziel einzugeben.",
        "route_back": "Zurück",
        "route_result_title": "Routenführung",
        "route_result_label": "Ziel: {text}",
        "route_keyboard_space": "Leerzeichen",
        "route_keyboard_back": "Löschen",
        "route_keyboard_clear": "Leeren",
        "route_keyboard_enter": "Bestätigen",
    },
    "Nederlands": {
        "flags": "NL",
        "language_title": "Taal",
        "tour": "Bezienswaardigheden",
        "route": "Route",
        "qr": "QR",
        "open": "Openen",
        "route_input_title": "Bestemming invoeren",
        "route_input_hint": "Tik op het toetsenbord om de bestemming in te voeren.",
        "route_back": "Terug",
        "route_result_title": "Routebegeleiding",
        "route_result_label": "Bestemming: {text}",
        "route_keyboard_space": "Spatie",
        "route_keyboard_back": "Verwijder",
        "route_keyboard_clear": "Wissen",
        "route_keyboard_enter": "Bevestigen",
    },
    "Svenska": {
        "flags": "SE",
        "language_title": "Språk",
        "tour": "Sevärdheter",
        "route": "Vägbeskrivning",
        "qr": "QR",
        "open": "Öppna",
        "route_input_title": "Ange destination",
        "route_input_hint": "Tryck på tangentbordet för att ange destination.",
        "route_back": "Tillbaka",
        "route_result_title": "Vägbeskrivning",
        "route_result_label": "Destination: {text}",
        "route_keyboard_space": "Mellanslag",
        "route_keyboard_back": "Backsteg",
        "route_keyboard_clear": "Rensa",
        "route_keyboard_enter": "Bekräfta",
    },
    "Français": {
        "flags": "FR",
        "language_title": "Langue",
        "tour": "Sites touristiques",
        "route": "Itinéraire",
        "qr": "QR",
        "open": "Ouvrir",
        "route_input_title": "Saisir la destination",
        "route_input_hint": "Appuyez sur le clavier pour saisir la destination.",
        "route_back": "Retour",
        "route_result_title": "Guidage",
        "route_result_label": "Destination : {text}",
        "route_keyboard_space": "Espace",
        "route_keyboard_back": "Supprimer",
        "route_keyboard_clear": "Effacer",
        "route_keyboard_enter": "Valider",
    },
    "Italiano": {
        "flags": "IT",
        "language_title": "Lingua",
        "tour": "Attrazioni",
        "route": "Indicazioni",
        "qr": "QR",
        "open": "Apri",
        "route_input_title": "Inserisci destinazione",
        "route_input_hint": "Tocca la tastiera per inserire la destinazione.",
        "route_back": "Indietro",
        "route_result_title": "Indicazioni",
        "route_result_label": "Destinazione: {text}",
        "route_keyboard_space": "Spazio",
        "route_keyboard_back": "Cancella",
        "route_keyboard_clear": "Pulisci",
        "route_keyboard_enter": "Conferma",
    },
    "Español": {
        "flags": "ES",
        "language_title": "Idioma",
        "tour": "Atracciones",
        "route": "Indicaciones",
        "qr": "QR",
        "open": "Abrir",
        "route_input_title": "Ingresar destino",
        "route_input_hint": "Toque el teclado para introducir el destino.",
        "route_back": "Atrás",
        "route_result_title": "Guía de ruta",
        "route_result_label": "Destino: {text}",
        "route_keyboard_space": "Espacio",
        "route_keyboard_back": "Borrar",
        "route_keyboard_clear": "Limpiar",
        "route_keyboard_enter": "Aceptar",
    },
    "Português": {
        "flags": "PT",
        "language_title": "Idioma",
        "tour": "Atrações",
        "route": "Direções",
        "qr": "QR",
        "open": "Abrir",
        "route_input_title": "Inserir destino",
        "route_input_hint": "Toque no teclado para inserir o destino.",
        "route_back": "Voltar",
        "route_result_title": "Orientação de rota",
        "route_result_label": "Destino: {text}",
        "route_keyboard_space": "Espaço",
        "route_keyboard_back": "Apagar",
        "route_keyboard_clear": "Limpar",
        "route_keyboard_enter": "Confirmar",
    },
    "Русский": {
        "flags": "RU",
        "language_title": "Язык",
        "tour": "Достопримечательности",
        "route": "Маршрут",
        "qr": "QR",
        "open": "Открыть",
        "route_input_title": "Ввод пункта назначения",
        "route_input_hint": "Нажмите на клавиатуру, чтобы ввести пункт назначения.",
        "route_back": "Назад",
        "route_result_title": "Маршрут",
        "route_result_label": "Пункт назначения: {text}",
        "route_keyboard_space": "Пробел",
        "route_keyboard_back": "Удалить",
        "route_keyboard_clear": "Очистить",
        "route_keyboard_enter": "Подтвердить",
    },
    "Polski": {
        "flags": "PL",
        "language_title": "Język",
        "tour": "Atrakcje",
        "route": "Wskazówki",
        "qr": "QR",
        "open": "Otwórz",
        "route_input_title": "Wprowadź cel",
        "route_input_hint": "Dotknij klawiatury, aby wprowadzić cel.",
        "route_back": "Wstecz",
        "route_result_title": "Nawigacja",
        "route_result_label": "Cel: {text}",
        "route_keyboard_space": "Spacja",
        "route_keyboard_back": "Usuń",
        "route_keyboard_clear": "Wyczyść",
        "route_keyboard_enter": "Potwierdź",
    },
    "Čeština": {
        "flags": "CZ",
        "language_title": "Jazyk",
        "tour": "Památky",
        "route": "Trasa",
        "qr": "QR",
        "open": "Otevřít",
        "route_input_title": "Zadat cíl",
        "route_input_hint": "Klepněte na klávesnici a zadejte cíl.",
        "route_back": "Zpět",
        "route_result_title": "Navigace",
        "route_result_label": "Cíl: {text}",
        "route_keyboard_space": "Mezera",
        "route_keyboard_back": "Smazat",
        "route_keyboard_clear": "Vymazat",
        "route_keyboard_enter": "Potvrdit",
    },
    "Українська": {
        "flags": "UA",
        "language_title": "Мова",
        "tour": "Пам'ятки",
        "route": "Маршрут",
        "qr": "QR",
        "open": "Відкрити",
        "route_input_title": "Введення пункту призначення",
        "route_input_hint": "Натисніть клавіатуру, щоб ввести пункт призначення.",
        "route_back": "Назад",
        "route_result_title": "Маршрут",
        "route_result_label": "Пункт призначення: {text}",
        "route_keyboard_space": "Пробіл",
        "route_keyboard_back": "Видалити",
        "route_keyboard_clear": "Очистити",
        "route_keyboard_enter": "Підтвердити",
    },
    "Lietuvių": {
        "flags": "LT",
        "language_title": "Kalba",
        "tour": "Lankytinos vietos",
        "route": "Maršrutas",
        "qr": "QR",
        "open": "Atidaryti",
        "route_input_title": "Įvesti tikslą",
        "route_input_hint": "Palieskite klaviatūrą ir įveskite tikslą.",
        "route_back": "Atgal",
        "route_result_title": "Maršrutas",
        "route_result_label": "Tikslas: {text}",
        "route_keyboard_space": "Tarpas",
        "route_keyboard_back": "Trinti",
        "route_keyboard_clear": "Išvalyti",
        "route_keyboard_enter": "Patvirtinti",
    },
    "Latviešu": {
        "flags": "LV",
        "language_title": "Valoda",
        "tour": "Apskates vietas",
        "route": "Maršruts",
        "qr": "QR",
        "open": "Atvērt",
        "route_input_title": "Ievadīt galamērķi",
        "route_input_hint": "Pieskarieties tastatūrai, lai ievadītu galamērķi.",
        "route_back": "Atpakaļ",
        "route_result_title": "Maršruts",
        "route_result_label": "Galamērķis: {text}",
        "route_keyboard_space": "Atstarpe",
        "route_keyboard_back": "Dzēst",
        "route_keyboard_clear": "Notīrīt",
        "route_keyboard_enter": "Apstiprināt",
    },
}

LANG_FLAG_TO_PLACE_CODE = {
    "KR": "ko",
    "US": "en",
    "JP": "ja",
    "CN": "zh",
    "TW": "zh",
}


def _place_lang_code(lang: str) -> str:
    info = LANG_INFO.get(lang, LANG_INFO.get("English", {}))
    flag = info.get("flags", "")
    return LANG_FLAG_TO_PLACE_CODE.get(flag, "en")


def _current_location_text(lang: str) -> str:
    lang_code = _place_lang_code(lang)
    label = KIOSK_LOCATION_LABELS.get(lang_code, KIOSK_LOCATION_LABELS.get("en", "Location"))
    names = KIOSK_LOCATION.get("name", {})
    name = names.get(lang_code) or names.get("en")
    if not name and names:
        name = next(iter(names.values()))
    if not name:
        return label
    return f"{label}: {name}"


def _build_qr_pixmap(url: str, size: int):
    if not url:
        return None
    try:
        import qrcode
        from PIL import Image
    except Exception:
        return None

    qr = qrcode.QRCode(border=1, box_size=10)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img = img.resize((size, size), Image.NEAREST)
    img = img.convert("RGBA")
    data = img.tobytes("raw", "RGBA")
    qimage = QImage(data, img.size[0], img.size[1], QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimage)


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


def _build_static_map_url(lat: float, lng: float, width: int, height: int) -> str:
    api_key = _google_maps_api_key()
    if not api_key:
        return ""
    size_w = min(640, max(120, int(width * 1.5)))
    size_h = min(640, max(120, int(height * 1.5)))
    markers = [f"color:red|{lat},{lng}"]
    origin_lat = KIOSK_LOCATION.get("lat")
    origin_lng = KIOSK_LOCATION.get("lng")
    params = {
        "size": f"{size_w}x{size_h}",
        "scale": 2,
        "maptype": "roadmap",
        "format": "png",
        "markers": markers,
        "key": api_key,
    }
    if origin_lat is not None and origin_lng is not None:
        markers.append(f"color:blue|label:K|{origin_lat},{origin_lng}")
        center_lat = (lat + origin_lat) / 2
        center_lng = (lng + origin_lng) / 2
        zoom = _compute_zoom_for_bounds(
            lat,
            lng,
            origin_lat,
            origin_lng,
            max(120, int(size_w * 0.9)),
            max(120, int(size_h * 0.9)),
        )
        params["center"] = f"{center_lat},{center_lng}"
        params["zoom"] = zoom
    else:
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


def _resolve_place_image_path(url: str):
    if not url:
        return None
    path = Path(url)
    if path.is_absolute():
        return path if path.exists() else None
    base_dir = PLACE_IMAGE_DIR if PLACE_IMAGE_DIR.exists() else DEFAULT_IMAGE_DIR
    candidate = (base_dir / path).resolve()
    if candidate.exists():
        return candidate
    return None


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
    return max(1, min(20, int(min(zoom_x, zoom_y))))


def _load_kiosk_data(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


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


def _collect_tour_places(data: dict):
    place_i18n = data.get("place_i18n", [])
    places = {
        entry.get("place_id"): entry
        for entry in data.get("places", [])
        if entry.get("place_id") is not None and entry.get("type") == "TOUR"
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
    items.sort(key=lambda item: (-item.get("priority_score", 0), item.get("place_id", 0)))
    return items


def _lang_value(lang: str, key: str, default: str) -> str:
    fallback = LANG_INFO.get("English", {})
    info = LANG_INFO.get(lang, fallback)
    return info.get(key, fallback.get(key, default))


def _set_back_button_icon(button: QPushButton, tooltip: str) -> None:
    size = 24
    ratio = button.devicePixelRatioF() if hasattr(button, "devicePixelRatioF") else 1.0
    pixmap = QPixmap(int(size * ratio), int(size * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.transparent)

    color = button.palette().color(QPalette.ButtonText)
    pen = QPen(color, 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(pen)

    path = QPainterPath()
    path.moveTo(size * 0.65, size * 0.2)
    path.lineTo(size * 0.35, size * 0.5)
    path.lineTo(size * 0.65, size * 0.8)
    painter.drawPath(path)
    painter.end()

    button.setIcon(QIcon(pixmap))
    button.setIconSize(QSize(size, size))
    button.setText("")
    button.setToolTip(tooltip)


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

        grid_wrap = QFrame()
        self.grid_layout = QGridLayout(grid_wrap)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setHorizontalSpacing(12)
        self.grid_layout.setVerticalSpacing(4)

        for idx, lang in enumerate(LANGUAGES):
            btn = QPushButton(lang)
            btn.setObjectName("langBtn")
            btn.clicked.connect(lambda _checked, value=lang: self.on_select(value))
            row, col = divmod(idx, 3)
            self.grid_layout.addWidget(btn, row, col)

        self.layout_root.addWidget(self.title_label)
        self.layout_root.addWidget(grid_wrap, 1)

    def set_language(self, lang: str):
        info = LANG_INFO.get(lang, LANG_INFO["English"])
        self.title_label.setText(info["language_title"])

    def apply_scale(self, scale: float):
        if self.layout_root:
            margin = max(12, int(24 * scale))
            spacing = max(8, int(18 * scale))
            self.layout_root.setContentsMargins(margin, margin, margin, margin)
            self.layout_root.setSpacing(spacing)
        if self.grid_layout:
            self.grid_layout.setHorizontalSpacing(max(6, int(12 * scale)))
            self.grid_layout.setVerticalSpacing(max(2, int(4 * scale)))


class MenuPage(QFrame):
    def __init__(self, on_language_click, on_route_click):
        super().__init__()
        self.on_language_click = on_language_click
        self.on_route_click = on_route_click
        self.cards = []
        self.card_labels = {}
        self.lang_button = None
        self.location_label = None
        self.qr_title = None
        self.qr_label = None
        self.qr_size = 260
        self.layout_root = None
        self.cards_layout = None
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

        self.location_label = QLabel("")
        self.location_label.setObjectName("locationLabel")
        self.location_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(self.location_label, 0, alignment=Qt.AlignRight)

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
        card = SquareCard()
        card.setObjectName("cardQr")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(12)

        self.qr_title = QLabel("QR")
        self.qr_title.setObjectName("cardTitle")
        self.qr_title.setAlignment(Qt.AlignCenter)

        self.qr_label = QLabel()
        self.qr_label.setObjectName("qrLabel")
        self.qr_label.setAlignment(Qt.AlignCenter)
        qr_pixmap = self._build_qr_pixmap("https://www.google.com", self.qr_size)
        if qr_pixmap:
            self.qr_label.setPixmap(qr_pixmap)
        else:
            self.qr_label.setText("QR ?ï¿½ì± ë¶ï¿½?")

        card_layout.addStretch(1)
        card_layout.addWidget(self.qr_label, 0, alignment=Qt.AlignCenter)
        card_layout.addStretch(1)
        card_layout.addWidget(self.qr_title, 0, alignment=Qt.AlignCenter)
        return card

    def _build_qr_pixmap(self, url: str, size: int):
        return _build_qr_pixmap(url, size)

    def set_language(self, lang: str):
        info = LANG_INFO.get(lang, LANG_INFO["English"])
        self.lang_button.setText(f"{lang}")
        self.card_labels["tour"].setText(info["tour"])
        self.card_labels["route"].setText(info["route"])
        if self.location_label:
            self.location_label.setText(_current_location_text(lang))
        if self.qr_title:
            self.qr_title.setText(info["qr"])

    def _on_card_clicked(self, key: str):
        if key == "route" and self.on_route_click:
            self.on_route_click()
            return
        # Placeholder for navigation; wire to the actual pages later.

    def apply_scale(self, scale: float):
        if self.layout_root:
            margin = max(12, int(24 * scale))
            spacing = max(8, int(16 * scale))
            self.layout_root.setContentsMargins(margin, margin, margin, margin)
            self.layout_root.setSpacing(spacing)
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
            qr_pixmap = self._build_qr_pixmap("https://www.google.com", self.qr_size)
            if qr_pixmap:
                self.qr_label.setPixmap(qr_pixmap)


class MainWindow(QMainWindow):
    BASE_WIDTH = 1100
    BASE_HEIGHT = 760
    IDLE_TIMEOUT_MS = 10000
    DEFAULT_LANGUAGE = "English"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kiosk UI")
        self.resize(1100, 760)
        self.font_family = _resolve_font_family()
        self.current_language = self.DEFAULT_LANGUAGE
        self._last_route_page = None
        self.idle_timer = QTimer(self)
        self.idle_timer.setSingleShot(True)
        self.idle_timer.timeout.connect(self._show_standby)
        self._build_ui()
        self._apply_style(1.0)
        self._apply_scale()
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)
        self._reset_idle_timer()
        self._show_standby()

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
        kiosk_data = _load_kiosk_data(KIOSK_DATA_FILE)
        _load_kiosk_location(kiosk_data, DEFAULT_KIOSK_ID)
        landmark_items = _collect_tour_places(kiosk_data)
        self.route_input_page = RouteInputPage(
            on_submit=self._show_route_result,
            on_back=self._show_menu,
            on_category_select=self._show_category,
        )
        self.food_category_page = FoodCategoryPage(
            on_submit=self._show_route_result,
            on_back=self._show_route_input,
        )
        self.landmark_category_page = LandmarkCategoryPage(
            on_submit=self._show_route_result,
            on_back=self._show_route_input,
            items=landmark_items,
        )
        self.route_result_page = RouteResultPage(on_back=self._show_previous_route)
        self.menu_page = MenuPage(self._back_to_language, self._show_route_input)

        self.stack.addWidget(self.standby_page)
        self.stack.addWidget(self.language_page)
        self.stack.addWidget(self.route_input_page)
        self.stack.addWidget(self.food_category_page)
        self.stack.addWidget(self.landmark_category_page)
        self.stack.addWidget(self.route_result_page)
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
            #title {{
                font-size: {max(14, int(22 * scale))}px;
                font-weight: 600;
                color: #111827;
            }}
            #langBtn {{
                background: #111827;
                color: #ffffff;
                border-radius: {max(8, int(12 * scale))}px;
                padding: {max(14, int(22 * scale))}px {max(8, int(13 * scale))}px;
                font-weight: 600;
            }}
            #langBtn:hover {{
                background: #1f2937;
            }}
            #card {{
                border-radius: {max(10, int(18 * scale))}px;
            }}
            #cardTour {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #fde68a, stop:1 #fb7185);
            }}
            #cardRoute {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #93c5fd, stop:1 #34d399);
            }}
            #cardQr {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #c4b5fd, stop:1 #f9a8d4);
            }}
            #cardTitle {{
                font-size: {max(12, int(18 * scale))}px;
                font-weight: 600;
                color: #111827;
            }}
            #navBtn {{
                background: #1d4ed8;
                color: #ffffff;
                border-radius: {max(8, int(12 * scale))}px;
                padding: {max(6, int(10 * scale))}px {max(10, int(16 * scale))}px;
                font-weight: 600;
            }}
            #navBtn:hover {{
                background: #2563eb;
            }}
            #langPill {{
                background: #111827;
                color: #ffffff;
                border-radius: {max(10, int(14 * scale))}px;
                padding: {max(6, int(8 * scale))}px {max(10, int(14 * scale))}px;
                font-weight: 600;
            }}
            #langPill:hover {{
                background: #1f2937;
            }}
            #qrLabel {{
                color: #94a3b8;
                font-size: {max(10, int(16 * scale))}px;
                font-weight: 600;
            }}
            #qrCard {{
                background: #ffffff;
                border-radius: {max(8, int(14 * scale))}px;
            }}
            #mapCard {{
                background: #ffffff;
                border-radius: {max(8, int(14 * scale))}px;
            }}
            #mapLabel {{
                color: #94a3b8;
                font-size: {max(10, int(14 * scale))}px;
                font-weight: 600;
            }}
            #infoCard {{
                background: #ffffff;
                border-radius: {max(8, int(14 * scale))}px;
            }}
            #infoDesc {{
                color: #111827;
                font-size: {max(10, int(14 * scale))}px;
            }}
            #keyBtn {{
                background: #ffffff;
                color: #111827;
                border: 1px solid #d1d5db;
                border-radius: {max(6, int(10 * scale))}px;
                padding: {max(10, int(16 * scale))}px {max(8, int(12 * scale))}px;
                min-height: {max(36, int(48 * scale))}px;
                font-weight: 600;
            }}
            #keyBtn:hover {{
                background: #f3f4f6;
            }}
            #inputField {{
                background: #ffffff;
                color: #111827;
                border: 1px solid #d1d5db;
                border-radius: {max(8, int(12 * scale))}px;
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
            #categoryBtn {{
                border-radius: {max(10, int(18 * scale))}px;
                padding: {max(16, int(24 * scale))}px;
                font-size: {max(12, int(20 * scale))}px;
                font-weight: 600;
                color: #111827;
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
                border-radius: {max(10, int(18 * scale))}px;
                padding: {max(14, int(22 * scale))}px;
                font-size: {max(12, int(18 * scale))}px;
                font-weight: 600;
                color: #111827;
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
                border: 0;
                border-radius: {max(8, int(14 * scale))}px;
                padding: 0;
            }}
            #routeQrHint {{
                color: #6b7280;
                font-size: {max(10, int(14 * scale))}px;
                font-weight: 600;
            }}
            """
        )

    def _on_language_select(self, lang: str):
        self.current_language = lang
        self.menu_page.set_language(lang)
        self.language_page.set_language(lang)
        self.route_input_page.set_language(lang)
        self.food_category_page.set_language(lang)
        self.landmark_category_page.set_language(lang)
        self.route_result_page.set_language(lang)
        self.stack.setCurrentWidget(self.menu_page)
        QTimer.singleShot(0, self._apply_scale)

    def _back_to_language(self):
        self.stack.setCurrentWidget(self.language_page)

    def _show_menu(self):
        self.stack.setCurrentWidget(self.menu_page)
        QTimer.singleShot(0, self._apply_scale)

    def _show_route_input(self):
        self.stack.setCurrentWidget(self.route_input_page)
        QTimer.singleShot(0, self._apply_scale)

    def _show_category(self, category: str):
        if category == "food":
            self._show_food_category(category)
            return
        if category == "landmark":
            self.stack.setCurrentWidget(self.landmark_category_page)
            QTimer.singleShot(0, self._apply_scale)

    def _show_food_category(self, _category: str):
        self.stack.setCurrentWidget(self.food_category_page)
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
        self.food_category_page.reset_state()
        self.food_category_page.set_language(self.DEFAULT_LANGUAGE)
        self.landmark_category_page.reset_state()
        self.landmark_category_page.set_language(self.DEFAULT_LANGUAGE)
        self.route_result_page.set_language(self.DEFAULT_LANGUAGE)

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
        self._apply_style(scale)
        self.standby_page.apply_scale(scale)
        self.language_page.apply_scale(scale)
        self.route_input_page.apply_scale(scale)
        self.food_category_page.apply_scale(scale)
        self.landmark_category_page.apply_scale(scale)
        self.route_result_page.apply_scale(scale)
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
        layout.setSpacing(12)

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

        grid = QGridLayout()
        grid.setSpacing(16)
        grid.setContentsMargins(0, 0, 0, 0)

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
        min_height = max(90, int(140 * scale))
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


class FoodCategoryPage(QFrame):
    ITEMS = [
        ("food_korean", "Korean"),
        ("food_snack", "Street Food"),
        ("food_cafe", "Cafe/Dessert"),
        ("food_fast", "Fast Food"),
        ("food_japanese", "Japanese"),
        ("food_chinese", "Chinese"),
        ("food_western", "Western"),
        ("food_convenience", "Convenience/Snacks"),
        ("food_vegan", "Vegetarian/Vegan"),
        ("food_bar", "Bar/Pub"),
    ]

    def __init__(self, on_submit, on_back):
        super().__init__()
        self.on_submit = on_submit
        self.on_back = on_back
        self.title_label = None
        self.back_button = None
        self.item_buttons = {}
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
        header.addSpacing(60)
        layout.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(16)
        grid.setContentsMargins(0, 0, 0, 0)

        for index, (key, default) in enumerate(self.ITEMS):
            btn = QPushButton(default)
            btn.setObjectName("subcategoryBtn")
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _checked, value_key=key, fallback=default: self._handle_item(value_key, fallback))
            self.item_buttons[key] = btn
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
            self.title_label.setText(_lang_value(lang, "food_category_title", "Food Categories"))
        if self.back_button:
            _set_back_button_icon(self.back_button, _lang_value(lang, "route_back", "Back"))
        for key, default in self.ITEMS:
            btn = self.item_buttons.get(key)
            if btn:
                btn.setText(_lang_value(lang, key, default))

    def _handle_back(self):
        if self.on_back:
            self.on_back()

    def _handle_item(self, key: str, fallback: str):
        label = _lang_value(self._current_language, key, fallback)
        if self.on_submit:
            self.on_submit(label)


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
        for place_id, btn in self.item_buttons.items():
            btn.setText(self._label_for(place_id))

    def _label_for(self, place_id: int) -> str:
        item = self.items_by_id.get(place_id)
        if not item:
            return "Landmark"
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
            self.qr_label.setText("QR unavailable.")
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
                self.qr_hint_label.setText("Google Maps")
        else:
            self.qr_label.setPixmap(QPixmap())
            self.qr_label.setText("QR unavailable.")
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
            self.map_label.setText("Map unavailable.")
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
            scaled = pixmap.scaled(target_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            self.map_label.setPixmap(scaled)
            self.map_label.setText("")
            self._map_signature = signature
        else:
            self.map_label.setPixmap(QPixmap())
            self.map_label.setText("Map unavailable.")
            self._map_signature = None

    def _refresh_info(self):
        if not self.info_image or not self.info_desc:
            return
        description = (self._destination_description or "").strip()
        if description:
            self.info_desc.setText(description)
        else:
            self.info_desc.setText("No description.")
        image_path = _resolve_place_image_path(self._destination_image_url or "")
        if not image_path:
            self.info_image.setPixmap(QPixmap())
            self.info_image.setText("No image.")
            self._last_loaded_image = None
            return
        target_size = self.info_image_size if self.info_image_size.isValid() else QSize(360, 220)
        signature = (str(image_path), target_size.width(), target_size.height())
        if signature == self._last_loaded_image:
            return
        self.info_image.setFixedSize(target_size)
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            self.info_image.setPixmap(QPixmap())
            self.info_image.setText("No image.")
            self._last_loaded_image = None
            return
        scaled = pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.info_image.setPixmap(scaled)
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

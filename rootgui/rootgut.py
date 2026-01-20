# -*- coding: utf-8 -*-
import json
import re
import sys
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontDatabase, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
KIOSK_DATA_FILE = PROJECT_DIR / "db-server" / "kiosk_data.json"
BUS_MAPPING_FILE = PROJECT_DIR / "bus_api_work" / "bus_mapping.json"
MANUAL_BUS_ROUTES_FILE = PROJECT_DIR / "bus_api_work" / "manual_bus_routes.json"
ROOTGUI_DIR = APP_DIR
TIMETABLE_FILE = ROOTGUI_DIR / "bus_timetable_eta.json"
BUS_SCHEDULE_FILE = ROOTGUI_DIR / "bus_schedule.json"
RESOLVED_ROUTES_FILE = ROOTGUI_DIR / "jjtour_routes_resolved.json"
ROUTES_FILE = ROOTGUI_DIR / "routes.json"

ORIGIN_NAME_OVERRIDE = {"전주역": "동부대로전주역"}
MANUAL_NAME_ALIASES = {
    "동부대로전주역": "전주역",
    "전주 한옥마을": "전주한옥마을",
}

BUS_SPEED_KMPH = 18.0
WALK_SPEED_KMPH = 4.2
TAXI_SPEED_KMPH = 25.0


def load_kiosk_data(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def build_name_map(data: dict, lang: str = "ko"):
    names = {}
    for entry in data.get("place_i18n", []):
        if entry.get("lang") != lang:
            continue
        place_id = entry.get("place_id")
        name = entry.get("name")
        if place_id is None or not name:
            continue
        names[place_id] = name
    return names


def _set_back_button_icon(button: QPushButton, tooltip: str) -> None:
    size = 24
    ratio = button.devicePixelRatioF() if hasattr(button, "devicePixelRatioF") else 1.0
    pixmap = QPixmap(int(size * ratio), int(size * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.transparent)

    color = button.palette().color(button.palette().ButtonText)
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
    button.setIconSize(pixmap.size() / pixmap.devicePixelRatio())
    button.setText("")
    button.setToolTip(tooltip)


def build_coord_map(data: dict, lang: str = "ko"):
    coords = {}
    place_index = {p.get("place_id"): p for p in data.get("places", [])}
    for entry in data.get("place_i18n", []):
        if entry.get("lang") != lang:
            continue
        place_id = entry.get("place_id")
        name = entry.get("name")
        place = place_index.get(place_id, {})
        lat = place.get("lat")
        lng = place.get("lng")
        if not name or lat is None or lng is None:
            continue
        coords[name] = (lat, lng)
    return coords


def pick_origin_name(data: dict, lang: str = "ko"):
    kiosks = data.get("kiosk", [])
    if not kiosks:
        return "Kiosk"
    kiosk_id = kiosks[0].get("kiosk_id")
    if not kiosk_id:
        return "Kiosk"
    for entry in data.get("kiosk_i18n", []):
        if entry.get("kiosk_id") == kiosk_id and entry.get("lang") == lang:
            return entry.get("name") or "Kiosk"
    return "Kiosk"


def build_routes(data: dict, lang: str = "ko"):
    origin = "전주역" # Hardcode to 전주역 as per user request

    if not ROUTES_FILE.exists():
        return []

    try:
        with ROUTES_FILE.open("r", encoding="utf-8") as handle:
            routes_data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    for route in routes_data:
        if route.get("stops") and route["stops"][0] == "__ORIGIN__":
            route["stops"][0] = origin
        
        tour_stops = route.get("stops", [])[1:]
        stops_str = ", ".join(tour_stops)
        route["description"] = f"{stops_str} 등을 둘러보는 코스입니다."
    
    return routes_data


def normalize_manual_name(name):
    if not name:
        return name
    name = str(name).strip()
    return MANUAL_NAME_ALIASES.get(name, name)


def normalize_pair_key(text):
    if text is None:
        return ""
    value = normalize_manual_name(text)
    value = re.sub(r"[\s·.()/-]", "", value)
    return value


def normalize_bus_no(bus_no):
    if not bus_no:
        return ""
    return str(bus_no).strip()


def load_timetable_eta():
    if not TIMETABLE_FILE.exists():
        return {"by_segment": {}}
    try:
        raw = TIMETABLE_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        try:
            raw = TIMETABLE_FILE.read_text(encoding="utf-8-sig")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return {"by_segment": {}}

    by_segment = {}
    for item in data.get("items", []):
        start = normalize_pair_key(item.get("start_stop_name"))
        end = normalize_pair_key(item.get("end_stop_name"))
        if not start or not end:
            continue
        key = (start, end)
        by_segment.setdefault(key, []).append(item)
    return {"by_segment": by_segment}


def load_resolved_routes():
    if not RESOLVED_ROUTES_FILE.exists():
        return {}
    try:
        raw = RESOLVED_ROUTES_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        try:
            raw = RESOLVED_ROUTES_FILE.read_text(encoding="utf-8-sig")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return {}
    by_segment = {}
    for item in data:
        start = normalize_pair_key(item.get("start_stop_name"))
        end = normalize_pair_key(item.get("end_stop_name"))
        if not start or not end:
            continue
        key = (start, end)
        by_segment.setdefault(key, []).append(item)
    return by_segment


def format_hhmm(value):
    try:
        val = int(value)
    except (TypeError, ValueError):
        return None
    hh = val // 100
    mm = val % 100
    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
        return None
    return f"{hh:02d}:{mm:02d}"


def load_bus_schedule():
    if not BUS_SCHEDULE_FILE.exists():
        return {}
    try:
        raw = BUS_SCHEDULE_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        try:
            raw = BUS_SCHEDULE_FILE.read_text(encoding="utf-8-sig")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return {}
    schedule = {}
    for bus_no, items in data.get("results", {}).items():
        for item in items:
            summary = item.get("route_summary") or {}
            if not summary:
                continue
            first_time = format_hhmm(summary.get("first_time"))
            last_time = format_hhmm(summary.get("last_time"))
            if first_time or last_time:
                schedule[normalize_bus_no(bus_no)] = {
                    "first_bus": first_time,
                    "last_bus": last_time,
                }
                break
    return schedule


def load_manual_bus_pairs():
    if not MANUAL_BUS_ROUTES_FILE.exists():
        return {}
    try:
        raw = MANUAL_BUS_ROUTES_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        try:
            raw = MANUAL_BUS_ROUTES_FILE.read_text(encoding="utf-8-sig")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return {}
    pairs = {}
    for entry in data.get("pairs", []):
        start = entry.get("from")
        end = entry.get("to")
        if not start or not end:
            continue
        pairs[(start, end)] = entry
        norm_key = (normalize_pair_key(start), normalize_pair_key(end))
        if norm_key != (start, end) and norm_key not in pairs:
            pairs[norm_key] = entry
    return pairs





def haversine_km(start, end):
    if not start or not end:
        return None
    lat1, lon1 = start
    lat2, lon2 = end
    radius = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    return 2 * radius * atan2(sqrt(a), sqrt(1 - a))


def build_segment_data(
    stops,
    coord_map,
    bus_mapping_data,
    manual_pairs,
    origin_name=None,
    resolved_routes=None,
    timetable_data=None,
    schedule_data=None,
):
    segments = []
    
    segment_routes_from_map = bus_mapping_data.get("segment_routes", {})
    route_info_from_map = bus_mapping_data.get("route_info", {})

    for idx in range(len(stops) - 1):
        start = stops[idx]
        end = stops[idx + 1]
        start_coord = coord_map.get(start)
        end_coord = coord_map.get(end)
        distance_km = haversine_km(start_coord, end_coord)

        # 1. Set default calculated times
        if distance_km:
            walk_min = max(3, round(distance_km / WALK_SPEED_KMPH * 60))
            bus_min = max(3, round(distance_km / BUS_SPEED_KMPH * 60))
            taxi_min = max(3, round(distance_km / TAXI_SPEED_KMPH * 60))
        else:
            # Fallback if no distance data
            walk_min = 12 + idx * 3
            bus_min = 8 + idx * 2
            taxi_min = 6 + idx * 2

        bus_no = None
        bus_list = []
        bus_note = None
        taxi_price = None

        headway_min = None
        first_bus = None
        last_bus = None

        # 2. Check for manual overrides from manual_bus_routes.json
        manual = manual_pairs.get((normalize_pair_key(start), normalize_pair_key(end)))
        if manual:
            walk_min = manual.get("walk_minutes", walk_min)
            bus_min = manual.get("bus_minutes", bus_min)
            if "taxi_minutes" in manual:
                taxi_min = manual["taxi_minutes"]
            taxi_price = manual.get("taxi_price")
            
            bus_list = manual.get("bus_numbers") or []
            if bus_list:
                bus_no = ", ".join(bus_list)

            bus_note = manual.get("note")

            # Handle the "WALK" fallback for bus_no display if no bus numbers are provided
            fallback = (manual.get("fallback") or "").upper()
            if not bus_list and (fallback == "WALK" or manual.get("same_zone")):
                bus_no = "도보"
        if not bus_list and resolved_routes:
            segment_key = (normalize_pair_key(start), normalize_pair_key(end))
            resolved = resolved_routes.get(segment_key, [])
            if resolved:
                bus_list = [r.get("bus_no") for r in resolved if r.get("bus_no")]
                if bus_list:
                    bus_no = ", ".join(bus_list)

        # 3. Get actual bus schedule data from bus_mapping.json if bus_list is available
        if bus_list:
            found_schedule_data = None
            for bus_num_str in bus_list:
                for brt_stdid, info in route_info_from_map.items():
                    if info.get("brtId") == bus_num_str:
                        found_schedule_data = info
                        break # Found schedule for this bus number
                if found_schedule_data:
                    break # Found schedule for a bus in bus_list
            
            if found_schedule_data:
                headway_min = found_schedule_data.get("brtMininTerval") or found_schedule_data.get("brtMaxinTerval")
                first_bus = found_schedule_data.get("brtFirstTime")
                last_bus = found_schedule_data.get("brtLastTime")

        if schedule_data and bus_list and (not first_bus or not last_bus):
            for candidate in bus_list:
                sched = schedule_data.get(normalize_bus_no(candidate))
                if sched:
                    first_bus = first_bus or sched.get("first_bus")
                    last_bus = last_bus or sched.get("last_bus")
                    break

        eta_item = None
        if timetable_data:
            segment_key = (normalize_pair_key(start), normalize_pair_key(end))
            candidates = timetable_data.get("by_segment", {}).get(segment_key, [])
            if candidates and bus_list:
                for candidate in candidates:
                    if normalize_bus_no(candidate.get("bus_no")) in [
                        normalize_bus_no(b) for b in bus_list
                    ]:
                        eta_item = candidate
                        break
            if not eta_item and candidates:
                eta_item = candidates[0]

        segments.append(
            {
                "start": start,
                "end": end,
                "walk_min": walk_min,
                "bus_min": bus_min,
                "taxi_min": taxi_min,
                "taxi_price": taxi_price,
                "bus_no": bus_no or "정보 준비 중",
                "bus_list": bus_list,
                "bus_note": bus_note,
                "eta_item": eta_item,
                "headway_min": headway_min,
                "first_bus": first_bus,
                "last_bus": last_bus,
            }
        )
    return segments


def format_route(route):
    return " → ".join(route.get("stops", []))


def summarize_time(segments):
    walk = sum(seg["walk_min"] for seg in segments if seg.get("walk_min") is not None)
    bus = sum(seg["bus_min"] for seg in segments if seg.get("bus_min") is not None)
    taxi = sum(seg["taxi_min"] for seg in segments if seg.get("taxi_min") is not None)
    return walk, bus, taxi


def estimate_prices(seg):
    walk_price = 0
    bus_price = 1400
    manual_taxi_price = seg.get("taxi_price")
    if manual_taxi_price is not None:
        taxi_price = manual_taxi_price
    elif seg.get("taxi_min") is not None:
        taxi_price = 3800 + seg["taxi_min"] * 200
    else:
        taxi_price = 0
    return walk_price, bus_price, taxi_price


def summarize_costs(segments):
    walk_total = 0
    bus_total = 0
    taxi_total = 0
    for seg in segments:
        walk_price, bus_price, taxi_price = estimate_prices(seg)
        walk_total += walk_price
        bus_total += bus_price
        taxi_total += taxi_price
    return walk_total, bus_total, taxi_total


def format_price(value):
    return f"{value:,}원"


def format_minutes(minutes):
    if not isinstance(minutes, (int, float)) or minutes < 0:
        return f"{minutes}분" # Fallback for unexpected types
    minutes = round(minutes)
    if minutes < 60:
        return f"{minutes}분"
    
    hours = minutes // 60
    mins = minutes % 60
    
    if mins == 0:
        return f"{hours}시간"
    else:
        return f"{hours}시간 {mins}분"


class RouteGuideWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kiosk Route Guide")
        self.setGeometry(80, 80, 1600, 900)
        self.setObjectName("routeGuide")
        self._apply_fonts()

        data = load_kiosk_data(KIOSK_DATA_FILE)
        self.coord_map = build_coord_map(data, "ko")
        self.origin_name = "전주역" # Hardcode to 전주역 as per user request
        self.routes = build_routes(data, "ko")
        
        bus_mapping_raw_data = {}
        if BUS_MAPPING_FILE.exists():
            try:
                bus_mapping_raw_data = json.loads(BUS_MAPPING_FILE.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        self.bus_mapping_data = bus_mapping_raw_data
        
        self.manual_pairs = load_manual_bus_pairs()
        self.resolved_routes = load_resolved_routes()
        self.timetable_data = load_timetable_eta()
        self.schedule_data = load_bus_schedule()

        self.route_card_map = {}
        self.selected_card = None

        self.back_button = None
        self.root = QWidget()
        self.root.setObjectName("routeRoot")
        self.setCentralWidget(self.root)
        root_layout = QVBoxLayout(self.root)
        root_layout.setContentsMargins(22, 22, 22, 22)
        root_layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)
        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("navBtn")
        _set_back_button_icon(self.back_button, "Back")
        self.back_button.clicked.connect(self._handle_back)
        header.addWidget(self.back_button, 0, alignment=Qt.AlignLeft)
        header.addStretch(1)
        root_layout.addLayout(header, 0)

        self.detail_panel = self.build_detail_panel()
        self.list_panel = self.build_route_list_panel()

        main_row = QHBoxLayout()
        main_row.setSpacing(20)
        main_row.addWidget(self.list_panel, 2)
        main_row.addWidget(self.detail_panel, 3)
        root_layout.addLayout(main_row, 1)

        if self.routes:
            first_route = self.routes[0]
            first_card = self.route_card_map.get(first_route["title"])
            self.show_detail(first_route, first_card)
        self._apply_style()

    def _handle_back(self):
        on_back = getattr(self, "on_back", None)
        if callable(on_back):
            on_back()
            return
        self.hide()

    def _apply_fonts(self):
        font_path = APP_DIR / "fonts" / "NotoSansCJKkr-Regular.otf"
        font_family = None
        if font_path.exists():
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    font_family = families[0]
        if font_family:
            self.setFont(QFont(font_family, 10))

    def _apply_style(self):
        self.setStyleSheet(
            """
            QWidget#routeGuide {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f5efe6, stop:0.55 #f1f4ff, stop:1 #e7f6f3);
            }
            QWidget#routeRoot { color: #111827; }
            QScrollArea { border: none; }

            QPushButton#navBtn {
                background: #1d4ed8;
                color: #ffffff;
                border-radius: 16px;
                padding: 10px 16px;
                font-weight: bold;
            }
            QPushButton#navBtn:hover {
                background: #2563eb;
            }

            QWidget#listPanel {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
            }

            QFrame#routeCard {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 14px;
            }
            QFrame#routeCard:hover {
                border-color: #cbd5e1;
            }
            QFrame#routeCard[selected="true"] {
                border-color: #2563eb;
                background-color: #eff6ff;
            }
            QLabel#percentBadge {
                background-color: #fde68a;
                color: #92400e;
                border-radius: 30px;
                font-size: 16px;
                font-weight: bold;
            }
            QLabel#routeCardTitle {
                font-size: 18px;
                font-weight: bold;
                color: #111827;
            }
            QLabel#routeCardPath {
                font-size: 13px;
                color: #4b5563;
            }
            QLabel#routeCardDescription {
                font-size: 12px;
                color: #6b7280;
                padding-top: 5px;
            }

            QWidget#detailPanel {
                background-color: #ffffff;
                border-radius: 16px;
                border: 1px solid #e5e7eb;
            }
            QLabel#detailTitle {
                font-size: 24px;
                font-weight: bold;
                color: #111827;
            }
            QLabel#detailPath {
                font-size: 14px;
                color: #4b5563;
            }
            QLabel#detailDescription {
                font-size: 13px;
                color: #374151;
                padding-top: 5px;
                padding-bottom: 5px;
            }
            QLabel#detailTotal {
                font-size: 13px;
                color: #374151;
                background-color: #f8fafc;
                border-radius: 10px;
                padding: 10px;
            }
            QFrame#segmentCard {
                background-color: #f8fafc;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
            }
            QLabel#segmentTitle {
                font-size: 15px;
                font-weight: bold;
                color: #1f2937;
            }
            QLabel {
                font-size: 13px;
            }
            """
        )

    def build_route_list_panel(self):
        container = QWidget()
        container.setObjectName("listPanel")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("전주역 출발 인기 관광 루트")
        title_font = title.font()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)

        subtitle = QLabel("카드를 누르면 오른쪽에 상세 정보가 표시됩니다.")
        subtitle.setStyleSheet("color: #6b7280;")
        subtitle_font = subtitle.font()
        subtitle_font.setPointSize(14)
        subtitle.setFont(subtitle_font)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        layout.addWidget(scroll, 1)

        grid_wrapper = QWidget()
        grid_layout = QGridLayout(grid_wrapper)
        grid_layout.setContentsMargins(0, 10, 10, 10)
        grid_layout.setSpacing(16)
        scroll.setWidget(grid_wrapper)

        columns = 1
        for idx, route in enumerate(self.routes):
            row = idx // columns
            col = idx % columns
            card = self.create_route_card(route)
            self.route_card_map[route["title"]] = card
            card.mousePressEvent = lambda event, r=route, c=card: self.show_detail(
                r, c, event
            )
            grid_layout.addWidget(card, row, col)

        return container

    def create_route_card(self, route):
        card = QFrame()
        card.setObjectName("routeCard")
        card.setCursor(Qt.PointingHandCursor)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(10)

        title_row = QWidget()
        title_layout = QHBoxLayout(title_row)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(12)

        percent_badge = QLabel(f"{route['percent']}%")
        percent_badge.setObjectName("percentBadge")
        percent_badge.setAlignment(Qt.AlignCenter)
        percent_badge.setFixedSize(60, 60)

        title_label = QLabel(route["title"])
        title_label.setObjectName("routeCardTitle")

        title_layout.addWidget(percent_badge)
        title_layout.addWidget(title_label, 1)

        path = QLabel(format_route(route))
        path.setWordWrap(True)
        path.setObjectName("routeCardPath")
        
        description = QLabel(route.get("description", ""))
        description.setWordWrap(True)
        description.setObjectName("routeCardDescription")

        card_layout.addWidget(title_row)
        card_layout.addWidget(path)
        card_layout.addWidget(description)
        return card

    def build_detail_panel(self):
        container = QWidget()
        container.setObjectName("detailPanel")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        self.detail_title_label = QLabel("")
        self.detail_title_label.setObjectName("detailTitle")

        self.detail_path_label = QLabel("")
        self.detail_path_label.setWordWrap(True)
        self.detail_path_label.setObjectName("detailPath")

        self.detail_description_label = QLabel("")
        self.detail_description_label.setWordWrap(True)
        self.detail_description_label.setObjectName("detailDescription")

        self.detail_total_label = QLabel("")
        self.detail_total_label.setObjectName("detailTotal")
        self.detail_total_label.setWordWrap(True)

        header_layout.addWidget(self.detail_title_label)
        header_layout.addWidget(self.detail_path_label)
        header_layout.addWidget(self.detail_description_label)
        header_layout.addSpacing(10)
        header_layout.addWidget(self.detail_total_label)
        layout.addWidget(header)

        self.detail_scroll = QScrollArea()
        self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setFrameShape(QFrame.NoFrame)
        self.detail_scroll.setObjectName("detailScroll")
        layout.addWidget(self.detail_scroll, 1)

        self.detail_body = QWidget()
        self.detail_layout = QVBoxLayout(self.detail_body)
        self.detail_layout.setContentsMargins(0, 5, 5, 5)
        self.detail_layout.setSpacing(14)
        self.detail_scroll.setWidget(self.detail_body)

        return container

    def show_detail(self, route, card=None, event=None):
        if self.selected_card:
            self.selected_card.setProperty("selected", False)
            self.selected_card.style().unpolish(self.selected_card)
            self.selected_card.style().polish(self.selected_card)

        if card:
            card.setProperty("selected", True)
            card.style().unpolish(card)
            card.style().polish(card)
            self.selected_card = card

        self.detail_title_label.setText(route["title"])
        self.detail_path_label.setText(format_route(route))
        self.detail_description_label.setText(route.get("description", ""))

        segments = build_segment_data(
            route.get("stops", []),
            self.coord_map,
            self.bus_mapping_data, # Pass entire bus_mapping_data
            self.manual_pairs,
            self.origin_name,
            self.resolved_routes,
            self.timetable_data,
            self.schedule_data,
        )
        walk, bus, taxi = summarize_time(segments)
        walk_cost, bus_cost, taxi_cost = summarize_costs(segments)

        cost_style = "color:#b58a52; font-weight:bold;"
        summary_parts = [
            f"<b>도보:</b> {format_minutes(walk)}, <span style='{cost_style}'>{format_price(walk_cost)}</span>",
            f"<b>버스:</b> {format_minutes(bus)}, <span style='{cost_style}'>{format_price(bus_cost)}</span>",
        ]
        if taxi > 0 or taxi_cost > 0:
            summary_parts.append(
                f"<b>택시:</b> {format_minutes(taxi)}, 약 <span style='{cost_style}'>{format_price(taxi_cost)}</span>"
            )

        self.detail_total_label.setText(
            f"<b>전체 예상 비용 및 시간</b><br>" + " | ".join(summary_parts)
        )

        self.clear_layout(self.detail_layout)
        for seg in segments:
            self.detail_layout.addWidget(self.build_segment_card(seg))
        self.detail_layout.addStretch(1)

        if event:
            event.accept()

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def build_segment_card(self, seg):
        card = QFrame()
        card.setObjectName("segmentCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(f"{seg['start']} → {seg['end']}")
        title.setObjectName("segmentTitle")
        layout.addWidget(title)

        grid = QWidget()
        grid_layout = QGridLayout(grid)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setHorizontalSpacing(15)
        grid_layout.setVerticalSpacing(10)
        layout.addWidget(grid)

        walk_price, bus_price, taxi_price = estimate_prices(seg)
        cost_style = "color:#b58a52; font-weight:bold;"
        
        current_row = 0

        # Walk
        if seg.get("walk_min") is not None:
            grid_layout.addWidget(QLabel("🚶️"), current_row, 0)
            grid_layout.addWidget(QLabel("<b>도보</b>"), current_row, 1)
            grid_layout.addWidget(QLabel(format_minutes(seg['walk_min'])), current_row, 2)
            walk_cost_text = f"<span style='{cost_style}'>{format_price(walk_price)}</span>"
            grid_layout.addWidget(QLabel(walk_cost_text), current_row, 3, Qt.AlignRight)
            current_row += 1

        # Bus
        if seg.get("bus_min") is not None:
            grid_layout.addWidget(QLabel("🚌"), current_row, 0)
            grid_layout.addWidget(QLabel("<b>버스</b>"), current_row, 1)
            grid_layout.addWidget(QLabel(format_minutes(seg['bus_min'])), current_row, 2)
            bus_cost_text = f"<span style='{cost_style}'>{format_price(bus_price)}</span>"
            grid_layout.addWidget(QLabel(bus_cost_text), current_row, 3, Qt.AlignRight)
            
            bus_details_widget = QWidget()
            bus_details_layout = QVBoxLayout(bus_details_widget)
            bus_details_layout.setContentsMargins(0, 0, 0, 0)
            bus_details_layout.setSpacing(4)
            
            bus_no_text = "도보 이동 구간" if seg["bus_no"] == "도보" else seg["bus_no"]
            if seg.get("bus_list"):
                bus_no_text = ", ".join(seg["bus_list"])
            
            if seg["bus_no"] != "도보":
                bus_num_label = QLabel(f"<b>번호:</b> {bus_no_text}")
                bus_details_layout.addWidget(bus_num_label)

                if seg.get("headway_min") and seg.get("first_bus") and seg.get("last_bus"):
                    headway_label = QLabel(f"<b>배차:</b> 약 {seg['headway_min']}분 (첫차 {seg['first_bus']} / 막차 {seg['last_bus']})")
                    bus_details_layout.addWidget(headway_label)
                eta_item = seg.get("eta_item")
                if eta_item and eta_item.get("status", {}).get("code") == "000":
                    next_in = eta_item.get("next_in_minutes")
                    next_times = eta_item.get("next_times") or []
                    if next_in is not None:
                        eta_label = QLabel(f"<b>?? ??:</b> {next_in}? ?")
                        bus_details_layout.addWidget(eta_label)
                    if next_times:
                        times_label = QLabel(f"<b>?? ??:</b> {', '.join(next_times[:3])}")
                        bus_details_layout.addWidget(times_label)
            
            if seg.get("bus_note"):
                note_label = QLabel(f"<b>안내:</b> {seg['bus_note']}")
                note_label.setWordWrap(True)
                bus_details_layout.addWidget(note_label)

            if bus_details_layout.count() > 0:
                current_row += 1
                grid_layout.addWidget(bus_details_widget, current_row, 1, 1, 3)
            
            current_row += 1

        # Taxi
        if seg.get("taxi_min") is not None:
            grid_layout.addWidget(QLabel("🚕"), current_row, 0)
            grid_layout.addWidget(QLabel("<b>택시</b>"), current_row, 1)
            grid_layout.addWidget(QLabel(format_minutes(seg['taxi_min'])), current_row, 2)
            taxi_cost_text = f"약 <span style='{cost_style}'>{format_price(taxi_price)}</span>"
            grid_layout.addWidget(QLabel(taxi_cost_text), current_row, 3, Qt.AlignRight)
            current_row += 1

        grid_layout.setColumnStretch(2, 1)
        return card


def main():
    app = QApplication(sys.argv)

    font_db = QFontDatabase()
    font_path = str(APP_DIR / "fonts" / "NotoSansCJKkr-Regular.otf")
    font_id = font_db.addApplicationFont(font_path)
    if font_id != -1:
        font_families = QFontDatabase.applicationFontFamilies(font_id)
        if font_families:
            app.setFont(QFont(font_families[0], 10))

    app.setStyleSheet(
        """
        QWidget#routeGuide {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #f5efe6, stop:0.55 #f1f4ff, stop:1 #e7f6f3);
        }
        QWidget#routeRoot { color: #111827; }
        QScrollArea { border: none; }

        QWidget#listPanel {
            background-color: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 16px;
        }

        QFrame#routeCard {
            background-color: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
        }
        QFrame#routeCard:hover {
            border-color: #cbd5e1;
        }
        QFrame#routeCard[selected="true"] {
            border-color: #2563eb;
            background-color: #eff6ff;
        }
        QLabel#percentBadge {
            background-color: #fde68a;
            color: #92400e;
            border-radius: 30px;
            font-size: 16px;
            font-weight: bold;
        }
        QLabel#routeCardTitle {
            font-size: 18px;
            font-weight: bold;
            color: #111827;
        }
        QLabel#routeCardPath {
            font-size: 13px;
            color: #4b5563;
        }
        QLabel#routeCardDescription {
            font-size: 12px;
            color: #6b7280;
            padding-top: 5px;
        }

        QWidget#detailPanel {
            background-color: #ffffff;
            border-radius: 16px;
            border: 1px solid #e5e7eb;
        }
        QLabel#detailTitle {
            font-size: 24px;
            font-weight: bold;
            color: #111827;
        }
        QLabel#detailPath {
            font-size: 14px;
            color: #4b5563;
        }
        QLabel#detailDescription {
            font-size: 13px;
            color: #374151;
            padding-top: 5px;
            padding-bottom: 5px;
        }
        QLabel#detailTotal {
            font-size: 13px;
            color: #374151;
            background-color: #f8fafc;
            border-radius: 10px;
            padding: 10px;
        }
        QFrame#segmentCard {
            background-color: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
        }
        QLabel#segmentTitle {
            font-size: 15px;
            font-weight: bold;
            color: #1f2937;
        }
        QLabel {
            font-size: 13px;
        }
        """
    )
    window = RouteGuideWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

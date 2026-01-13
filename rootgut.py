# -*- coding: utf-8 -*-
import json
import os
import sys
from datetime import datetime, timedelta
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR
KIOSK_DATA_FILE = PROJECT_DIR / "db-server" / "kiosk_data.json"
ENV_FILE = PROJECT_DIR / ".env"
BUS_MAPPING_FILE = PROJECT_DIR / "bus_api_work" / "bus_mapping.json"
MANUAL_ROUTES_FILE = PROJECT_DIR / "bus_api_work" / "manual_routes.json"

BUS_API_URLS = [
    "https://openapi.jeonju.go.kr/jeonjubus/openApi/traffic/"
    "bus_location_bus_position_common.do",
    "https://openapi.jeonju.go.kr/jeonjubus/openApi/traffic/"
    "bus_location_bus_position.do",
    "http://openapi.jeonju.go.kr/jeonjubus/openApi/traffic/"
    "bus_location_bus_position_common.do",
    "http://openapi.jeonju.go.kr/jeonjubus/openApi/traffic/"
    "bus_location_bus_position.do",
]
BUS_SPEED_KMPH = 18.0
WALK_SPEED_KMPH = 4.2
TAXI_SPEED_KMPH = 25.0
BUS_CACHE_SECONDS = 30


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


def load_service_key():
    key = os.environ.get("JEONJU_BUS_SERVICE_KEY", "").strip()
    if key:
        return key
    if ENV_FILE.exists():
        with ENV_FILE.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                env_key, value = line.split("=", 1)
                env_key = env_key.strip()
                value = value.strip().strip('"').strip("'")
                if env_key and env_key not in os.environ:
                    os.environ[env_key] = value
    return os.environ.get("JEONJU_BUS_SERVICE_KEY", "").strip()


def load_bus_route_map():
    if not BUS_MAPPING_FILE.exists():
        return {}
    try:
        data = json.loads(BUS_MAPPING_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    segment_routes = data.get("segment_routes", {})
    mapping = {}
    for key, entry in segment_routes.items():
        if not isinstance(entry, dict):
            continue
        route_title, _, seg_idx = key.partition("-")
        try:
            seg_idx = int(seg_idx)
        except ValueError:
            continue
        route_ids = entry.get("route_ids", [])
        if not route_ids:
            continue
        mapping.setdefault(route_title, {})[seg_idx] = route_ids[0]
    return mapping


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


def estimate_eta_minutes(start_coord, end_coord, bus_positions=None, speed_kmph=BUS_SPEED_KMPH):
    distance_km = None
    if bus_positions:
        distances = [
            haversine_km((pos["lat"], pos["lng"]), end_coord)
            for pos in bus_positions
            if pos.get("lat") is not None and pos.get("lng") is not None
        ]
        distances = [d for d in distances if d is not None]
        if distances:
            distance_km = min(distances)
    if distance_km is None:
        distance_km = haversine_km(start_coord, end_coord)
    if distance_km is None:
        return None
    eta = max(1, round(distance_km / speed_kmph * 60))
    return eta


def extract_positions(root):
    lat_tags = {"gpsY", "posY", "lat", "latitude", "y"}
    lon_tags = {"gpsX", "posX", "lng", "lon", "longitude", "x"}
    positions = []

    def parse_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    for parent in root.iter():
        lat = None
        lon = None
        for child in list(parent):
            tag = child.tag.split("}")[-1]
            if tag in lat_tags:
                lat = parse_float(child.text)
            if tag in lon_tags:
                lon = parse_float(child.text)
        if lat is not None and lon is not None:
            positions.append({"lat": lat, "lng": lon})
    return positions


def fetch_bus_positions(service_key, route_id):
    if not service_key or not route_id:
        return []
    params_list = [
        urlencode(
            {"ServiceKey": service_key, "brtStdid": route_id},
            safe="%",
        ),
        urlencode(
            {"openApiAuthKey": service_key, "brtStdid": route_id},
            safe="%",
        ),
        urlencode(
            {"openapiAuthKey": service_key, "brtStdid": route_id},
            safe="%",
        ),
    ]
    payload = None
    for base in BUS_API_URLS:
        for params in params_list:
            url = f"{base}?{params}"
            try:
                req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urlopen(req, timeout=6) as resp:
                    payload = resp.read()
            except Exception:
                continue
            try:
                root = ET.fromstring(payload)
            except ET.ParseError:
                payload = None
                continue
            status = parse_status_from_xml(root)
            if status.get("code") == "000":
                return extract_positions(root)
    return []


def parse_status_from_xml(root):
    code = None
    msg = None
    for child in root.iter():
        tag = child.tag.split("}")[-1]
        if tag == "code" and child.text:
            code = child.text.strip()
        if tag == "msg" and child.text:
            msg = child.text.strip()
    if code or msg:
        return {"code": code, "msg": msg}
    return {"code": None, "msg": None}


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
    manual_routes = load_manual_routes()
    if manual_routes:
        return manual_routes
    places = [p for p in data.get("places", []) if p.get("type") == "TOUR"]
    places = sorted(places, key=lambda p: p.get("priority_score") or 0, reverse=True)
    name_map = build_name_map(data, lang)
    origin = pick_origin_name(data, lang)

    tour_names = []
    for place in places:
        place_id = place.get("place_id")
        name = name_map.get(place_id)
        if name:
            tour_names.append(name)
    if not tour_names:
        tour_names = ["Spot A", "Spot B", "Spot C", "Spot D", "Spot E"]

    base = tour_names[:5]
    if len(base) < 5:
        base = (base + tour_names)[0:5]

    return [
        {"title": "루트 A", "percent": 40, "stops": [origin, base[0], base[1], base[2]]},
        {"title": "루트 B", "percent": 25, "stops": [origin, base[2], base[3], base[1]]},
        {"title": "루트 C", "percent": 15, "stops": [origin, base[1], base[4], base[0]]},
        {"title": "루트 D", "percent": 12, "stops": [origin, base[3], base[4], base[2]]},
        {"title": "루트 E", "percent": 8, "stops": [origin, base[4], base[0], base[3]]},
    ]


def load_manual_routes():
    if not MANUAL_ROUTES_FILE.exists():
        return []
    try:
        raw = json.loads(MANUAL_ROUTES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    routes = []
    for entry in raw if isinstance(raw, list) else []:
        if not isinstance(entry, dict):
            continue
        stops = entry.get("stops", [])
        if not stops or not isinstance(stops, list):
            continue
        routes.append(
            {
                "title": entry.get("title", "루트"),
                "percent": entry.get("percent", 0),
                "stops": stops,
            }
        )
    return routes


def sanitize_stop_name(name):
    if not name or not str(name).strip():
        return "미정"
    return str(name)


def build_segment_data(stops, coord_map, bus_route_ids=None):
    segments = []
    for idx in range(len(stops) - 1):
        start = stops[idx]
        end = stops[idx + 1]
        start_coord = coord_map.get(start)
        end_coord = coord_map.get(end)
        distance_km = haversine_km(start_coord, end_coord)
        if distance_km:
            walk_min = max(3, round(distance_km / WALK_SPEED_KMPH * 60))
            bus_min = max(3, round(distance_km / BUS_SPEED_KMPH * 60))
            taxi_min = max(3, round(distance_km / TAXI_SPEED_KMPH * 60))
        else:
            walk_min = 12 + idx * 3
            bus_min = 8 + idx * 2
            taxi_min = 6 + idx * 2
        bus_route_id = None
        if bus_route_ids and idx in bus_route_ids:
            bus_route_id = bus_route_ids.get(idx)

        segments.append(
            {
                "start": start,
                "end": end,
                "start_coord": start_coord,
                "end_coord": end_coord,
                "distance_km": distance_km,
                "walk_min": walk_min,
                "bus_min": bus_min,
                "taxi_min": taxi_min,
                "bus_no": f"{70 + idx}",
                "bus_route_id": bus_route_id,
                "headway_min": 8 + idx * 2,
                "first_bus": "06:00",
                "last_bus": "22:30",
            }
        )
    return segments


def format_route(route):
    return " → ".join(sanitize_stop_name(s) for s in route.get("stops", []))


def summarize_time(segments):
    walk = sum(seg["walk_min"] for seg in segments)
    bus = sum(seg["bus_min"] for seg in segments)
    taxi = sum(seg["taxi_min"] for seg in segments)
    return walk, bus, taxi


def estimate_prices(seg):
    walk_price = 0
    bus_price = 1250
    taxi_price = 3800 + seg["taxi_min"] * 200
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
    return f"₩{value:,}"


def next_bus_times(headway_min, count=3):
    now = datetime.now()
    first = now + timedelta(minutes=max(1, headway_min))
    times = [first + timedelta(minutes=headway_min * i) for i in range(count)]
    return now, [t.strftime("%H:%M") for t in times]


class RouteGuideWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kiosk Route Guide")
        self.setGeometry(80, 80, 1600, 900)

        data = load_kiosk_data(KIOSK_DATA_FILE)
        self.coord_map = build_coord_map(data, "ko")
        self.service_key = load_service_key()
        self.bus_cache = {}
        self.bus_route_map = load_bus_route_map()
        self.routes = build_routes(data, "ko")

        self.root = QWidget()
        self.setCentralWidget(self.root)
        root_layout = QVBoxLayout(self.root)
        root_layout.setContentsMargins(22, 22, 22, 22)
        root_layout.setSpacing(12)

        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack, 1)

        self.main_view = self.build_main_view()
        self.detail_view = self.build_detail_view()
        self.stack.addWidget(self.main_view)
        self.stack.addWidget(self.detail_view)
        self.stack.setCurrentWidget(self.main_view)

    def build_main_view(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        title = QLabel("전주역 출발 인기 관광 루트")
        title_font = title.font()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)

        subtitle = QLabel("다른 사람들은 이렇게 이동했어요 · 카드 선택 시 상세")
        subtitle_font = subtitle.font()
        subtitle_font.setPointSize(11)
        subtitle.setFont(subtitle_font)
        subtitle.setStyleSheet("color: #6b5a44;")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        layout.addWidget(scroll, 1)

        grid_wrapper = QWidget()
        grid_layout = QGridLayout(grid_wrapper)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(12)
        scroll.setWidget(grid_wrapper)

        columns = 2
        for idx, route in enumerate(self.routes):
            row = idx // columns
            col = idx % columns
            card = self.create_route_card(route)
            grid_layout.addWidget(card, row, col)

        return container

    def create_route_card(self, route):
        card = QFrame()
        card.setObjectName("routeCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)

        summary_row = QWidget()
        summary_layout = QHBoxLayout(summary_row)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(12)

        percent_badge = QLabel(f"{route['percent']}%")
        percent_badge.setObjectName("percentBadge")
        percent_badge.setAlignment(Qt.AlignCenter)
        percent_badge.setFixedSize(56, 56)
        badge_font = percent_badge.font()
        badge_font.setPointSize(13)
        badge_font.setBold(True)
        percent_badge.setFont(badge_font)

        text_col = QWidget()
        text_layout = QVBoxLayout(text_col)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)

        title_label = QLabel(route["title"])
        title_font = title_label.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)

        path = QLabel(format_route(route))
        path.setWordWrap(True)
        path.setStyleSheet("color: #4a4a4a;")

        desc_map = {
            "루트 A": "전주 핵심 명소를 균형 있게 둘러보는 루트예요.",
            "루트 B": "역사 스팟 위주로 차분하게 걷는 루트예요.",
            "루트 C": "사진 명소를 중심으로 이동하는 루트예요.",
            "루트 D": "가족·친구와 가볍게 즐기기 좋은 루트예요.",
            "루트 E": "한옥 감성을 느끼기 좋은 루트예요.",
        }
        desc_text = desc_map.get(
            route["title"],
            "이 루트는 인기 관광지를 균형 있게 둘러보는 동선이에요.",
        )
        desc_label = QLabel(desc_text)
        desc_label.setStyleSheet("color: #6b5a44;")

        text_layout.addWidget(title_label)
        text_layout.addWidget(path)
        text_layout.addWidget(desc_label)

        summary_layout.addWidget(percent_badge)
        summary_layout.addWidget(text_col, 1)
        card_layout.addWidget(summary_row)

        card.mousePressEvent = lambda event, r=route: self.show_detail(r, event)
        return card

    def build_detail_view(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)

        back_btn = QPushButton("← 루트 목록")
        back_btn.clicked.connect(self.show_main)
        back_btn.setFixedWidth(140)

        title_col = QWidget()
        title_layout = QVBoxLayout(title_col)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(4)

        self.detail_title_label = QLabel("")
        title_font = self.detail_title_label.font()
        title_font.setPointSize(20)
        title_font.setBold(True)
        self.detail_title_label.setFont(title_font)

        self.detail_path_label = QLabel("")
        self.detail_path_label.setWordWrap(True)
        self.detail_path_label.setStyleSheet("color: #4a4a4a;")

        self.detail_total_label = QLabel("")
        self.detail_total_label.setStyleSheet("color: #6b5a44;")

        title_layout.addWidget(self.detail_title_label)
        title_layout.addWidget(self.detail_path_label)
        title_layout.addWidget(self.detail_total_label)

        top_layout.addWidget(back_btn)
        top_layout.addWidget(title_col, 1)

        layout.addWidget(top_row)

        self.detail_diagram_container = QWidget()
        self.detail_diagram_layout = QVBoxLayout(self.detail_diagram_container)
        self.detail_diagram_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_diagram_layout.setSpacing(0)
        layout.addWidget(self.detail_diagram_container, 1)

        return container

    def show_main(self):
        self.stack.setCurrentWidget(self.main_view)

    def show_detail(self, route, event=None):
        self.detail_title_label.setText(route["title"])
        self.detail_path_label.setText(format_route(route))

        segments = build_segment_data(
            route.get("stops", [])[:3],
            self.coord_map,
            self.bus_route_map.get(route["title"], {}),
        )
        walk, bus, taxi = summarize_time(segments)
        walk_cost, bus_cost, taxi_cost = summarize_costs(segments)
        self.detail_total_label.setText(
            f"예상 소요: 도보 {walk}분 {format_price(walk_cost)} | "
            f"버스 {bus}분 {format_price(bus_cost)} | "
            f"택시 {taxi}분 {format_price(taxi_cost)}"
        )

        self.clear_layout(self.detail_diagram_layout)
        self.detail_diagram_layout.addWidget(self.build_route_diagram(route))
        self.stack.setCurrentWidget(self.detail_view)
        if event:
            event.accept()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

    def build_segment_info_box(self, seg):
        box = QFrame()
        box.setObjectName("segmentBox")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        if not seg:
            empty = QLabel("구간 정보 없음")
            layout.addWidget(empty)
            return box

        seg_title = QLabel(
            f"{sanitize_stop_name(seg['start'])} → {sanitize_stop_name(seg['end'])}"
        )
        seg_title.setStyleSheet("color: #2f2318;")

        walk_price, bus_price, taxi_price = estimate_prices(seg)
        fastest_time = min(seg["walk_min"], seg["bus_min"], seg["taxi_min"])
        cheapest_price = min(walk_price, bus_price, taxi_price)

        chips_row = QWidget()
        chips_layout = QGridLayout(chips_row)
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(6)

        def make_chip(label, minutes, price):
            is_fastest = minutes == fastest_time
            is_cheapest = price == cheapest_price
            chip = QLabel(f"{label} {minutes}분 · {format_price(price)}")
            if is_fastest:
                chip.setObjectName("modeChipFast")
            elif is_cheapest:
                chip.setObjectName("modeChipCheap")
            else:
                chip.setObjectName("modeChip")
            return chip

        chips_layout.addWidget(make_chip("도보", seg["walk_min"], walk_price), 0, 0)
        chips_layout.addWidget(make_chip("버스", seg["bus_min"], bus_price), 0, 1)
        chips_layout.addWidget(make_chip("택시", seg["taxi_min"], taxi_price), 1, 0)
        chips_layout.setColumnStretch(0, 1)
        chips_layout.setColumnStretch(1, 1)

        bus_row = QWidget()
        bus_row_layout = QHBoxLayout(bus_row)
        bus_row_layout.setContentsMargins(0, 0, 0, 0)
        bus_row_layout.setSpacing(6)

        bus_label = f"버스 {seg['bus_no']}" if seg.get("bus_no") else "버스"
        bus_btn = QPushButton(bus_label)
        bus_btn.setFixedWidth(86)
        now, next_times = next_bus_times(seg["headway_min"], 3)
        bus_positions = self.get_bus_positions(seg)
        eta = estimate_eta_minutes(
            seg.get("start_coord"),
            seg.get("end_coord"),
            bus_positions,
        )
        detail_lines = []
        if eta:
            if bus_positions:
                detail_lines.append(
                    f"다음 도착 예상 시간 : {eta}분 · 감지 {len(bus_positions)}대"
                )
            else:
                detail_lines.append(f"다음 도착 예상 시간 : {eta}분")
        else:
            detail_lines.append("다음 도착 예상 시간 : 정보 준비 중")
        detail_lines.append(f"배차 {seg['headway_min']}분")
        detail_lines.append(
            f"현재 {now.strftime('%H:%M')} 기준 다음 {', '.join(next_times)}"
        )
        detail_lines.append(f"첫차 {seg['first_bus']} | 막차 {seg['last_bus']}")
        bus_detail = QLabel("\n".join(detail_lines))
        bus_detail.setStyleSheet("color: #6b6b6b;")
        bus_detail.setWordWrap(True)
        bus_detail.setVisible(False)
        bus_btn.clicked.connect(lambda _checked, lbl=bus_detail: self.toggle_bus_detail(lbl))

        bus_row_layout.addWidget(bus_btn)
        bus_row_layout.addWidget(bus_detail, 1)

        layout.addWidget(seg_title)
        layout.addWidget(chips_row)
        layout.addWidget(bus_row)
        return box

    def toggle_bus_detail(self, label):
        if label:
            label.setVisible(not label.isVisible())

    def get_bus_positions(self, seg):
        route_id = seg.get("bus_route_id")
        if not route_id or not self.service_key:
            return []
        cached = self.bus_cache.get(route_id)
        now = datetime.now()
        if cached:
            age = (now - cached["ts"]).total_seconds()
            if age < BUS_CACHE_SECONDS:
                return cached["positions"]
        positions = fetch_bus_positions(self.service_key, route_id)
        self.bus_cache[route_id] = {"ts": now, "positions": positions}
        return positions

    def build_route_diagram(self, route):
        stops = route.get("stops", [])
        if len(stops) > 3:
            stops = stops[:3]

        segments = build_segment_data(
            stops, self.coord_map, self.bus_route_map.get(route["title"], {})
        )
        diagram = QWidget()
        diagram_layout = QGridLayout(diagram)
        diagram_layout.setContentsMargins(0, 4, 0, 0)
        diagram_layout.setSpacing(6)

        bus_label = QLabel("버스")
        bus_label.setAlignment(Qt.AlignCenter)
        diagram_layout.addWidget(bus_label, 0, 0, 1, 5)

        stop_boxes = []
        for stop in stops:
            box = QLabel(stop)
            box.setObjectName("stopBox")
            box.setAlignment(Qt.AlignCenter)
            box.setFixedSize(140, 72)
            stop_boxes.append(box)

        if len(stop_boxes) < 3:
            for _ in range(3 - len(stop_boxes)):
                filler = QLabel("다음")
                filler.setObjectName("stopBox")
                filler.setAlignment(Qt.AlignCenter)
                filler.setFixedSize(140, 72)
                stop_boxes.append(filler)

        connector_a = QFrame()
        connector_a.setFrameShape(QFrame.HLine)
        connector_a.setStyleSheet("color: #3a2c1f;")
        connector_b = QFrame()
        connector_b.setFrameShape(QFrame.HLine)
        connector_b.setStyleSheet("color: #3a2c1f;")

        diagram_layout.addWidget(stop_boxes[0], 1, 0)
        diagram_layout.addWidget(connector_a, 1, 1)
        diagram_layout.addWidget(stop_boxes[1], 1, 2)
        diagram_layout.addWidget(connector_b, 1, 3)
        diagram_layout.addWidget(stop_boxes[2], 1, 4)

        vline_left = QFrame()
        vline_left.setFrameShape(QFrame.VLine)
        vline_left.setStyleSheet("color: #3a2c1f;")
        vline_right = QFrame()
        vline_right.setFrameShape(QFrame.VLine)
        vline_right.setStyleSheet("color: #3a2c1f;")

        info_left = self.build_segment_info_box(segments[0] if segments else None)
        info_right = self.build_segment_info_box(segments[1] if len(segments) > 1 else None)

        diagram_layout.addWidget(vline_left, 2, 1, 1, 1, Qt.AlignHCenter)
        diagram_layout.addWidget(vline_right, 2, 3, 1, 1, Qt.AlignHCenter)
        diagram_layout.addWidget(info_left, 3, 0, 1, 2)
        diagram_layout.addWidget(info_right, 3, 2, 1, 3)
        return diagram


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(
        """
        QMainWindow { background-color: #f6f1e6; }
        QLabel { color: #2f2318; }
        QFrame#routeCard {
            background: #ffffff;
            border: 1px solid #d8c9b3;
            border-radius: 12px;
        }
        QLabel#percentBadge {
            background: #e4b573;
            color: #2f2318;
            border-radius: 28px;
        }
        QFrame#segmentBox {
            background: #fff8ec;
            border: 1px solid #e0d2bd;
            border-radius: 10px;
        }
        QLabel#stopBox {
            background: #fffaf2;
            border: 2px solid #3a2c1f;
            border-radius: 8px;
        }
        QLabel#modeChip {
            background: #f7efe2;
            border: 1px solid #e0d2bd;
            border-radius: 8px;
            padding: 4px 8px;
        }
        QLabel#modeChipFast {
            background: #f6c27b;
            border: 1px solid #e0b16f;
            border-radius: 8px;
            padding: 4px 8px;
        }
        QLabel#modeChipCheap {
            background: #e7d4b2;
            border: 1px solid #d5c3a2;
            border-radius: 8px;
            padding: 4px 8px;
        }
        QPushButton {
            background: #f0e3d0;
            border: 1px solid #d8c9b3;
            border-radius: 8px;
            padding: 4px 8px;
        }
        QPushButton:pressed {
            background: #e7d7c1;
        }
        """
    )
    window = RouteGuideWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

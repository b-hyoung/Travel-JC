import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from math import atan2, cos, radians, sin, sqrt

PROJECT_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_DIR / ".env"
KIOSK_DATA_FILE = PROJECT_DIR / "db-server" / "kiosk_data.json"
OUTPUT_FILE = Path(__file__).resolve().parent / "bus_mapping.json"
FALLBACK_FILE = Path(__file__).resolve().parent / "fallback_bus_data.json"
MANUAL_ROUTES_FILE = Path(__file__).resolve().parent / "manual_routes.json"

BASE_URLS = [
    "https://openapi.jeonju.go.kr/jeonjubus/openApi/traffic",
    "http://openapi.jeonju.go.kr/jeonjubus/openApi/traffic",
]
ROUTE_LIST_ENDPOINTS = [
    "bus_location_all_common.do",
    "bus_location_all.do",
]
ROUTE_STOPS_ENDPOINTS = [
    "bus_location_busstop_list_common.do",
    "bus_location_busstop_list.do",
]
STOP_SEARCH_ENDPOINTS = [
    "bus_location2_stopnm_common.do",
    "bus_location2_stopnm.do",
]


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
                value = value.strip().strip("\"").strip("'")
                if env_key and env_key not in os.environ:
                    os.environ[env_key] = value
    return os.environ.get("JEONJU_BUS_SERVICE_KEY", "").strip()


def fetch_xml(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=10) as resp:
        return resp.read()


def parse_status(xml_bytes):
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return {"code": None, "msg": "Invalid XML response"}
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


def fetch_with_fallback(endpoints, param_variants):
    last_status = {"code": None, "msg": None}
    last_url = None
    for base in BASE_URLS:
        for endpoint in endpoints:
            for params in param_variants:
                url = f"{base}/{endpoint}?{params}"
                last_url = url
                try:
                    xml_bytes = fetch_xml(url)
                except Exception:
                    continue
                status = parse_status(xml_bytes)
                last_status = status
                if status.get("code") == "000":
                    return xml_bytes, status, url
    return None, last_status, last_url


def redact_service_key(url):
    if not url:
        return url
    key_names = ("ServiceKey=", "openApiAuthKey=", "openapiAuthKey=")
    marker = None
    for name in key_names:
        if name in url:
            marker = name
            break
    if not marker:
        return url
    before, after = url.split(marker, 1)
    if "&" in after:
        _, tail = after.split("&", 1)
        return f"{before}{marker}***&{tail}"
    return f"{before}{marker}***"


def build_param_variants(service_key, extra=None):
    extra = extra or {}
    params = {"ServiceKey": service_key}
    params.update(extra)
    return [urlencode(params, safe="%")]


def parse_route_list(xml_bytes):
    root = ET.fromstring(xml_bytes)
    routes = []
    for item in root.iter():
        tag = item.tag.split("}")[-1]
        if tag != "list":
            continue
        data = {}
        for child in item:
            ctag = child.tag.split("}")[-1]
            if child.text:
                data[ctag] = child.text.strip()
        if "brtStdid" in data:
            routes.append(data)
    return routes


def parse_stop_list(xml_bytes):
    root = ET.fromstring(xml_bytes)
    stops = []
    for item in root.iter():
        tag = item.tag.split("}")[-1]
        if tag != "list":
            continue
        data = {}
        for child in item:
            ctag = child.tag.split("}")[-1]
            if child.text:
                data[ctag] = child.text.strip()
        if "stopKname" in data:
            stops.append(data)
    return stops


def haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    return 2 * radius * atan2(sqrt(a), sqrt(1 - a))


def build_routes_from_kiosk():
    manual = load_manual_routes()
    if manual:
        return manual
    try:
        with KIOSK_DATA_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    def build_name_map(data, lang="ko"):
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

    def pick_origin_name(data, lang="ko"):
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

    places = [p for p in data.get("places", []) if p.get("type") == "TOUR"]
    places = sorted(places, key=lambda p: p.get("priority_score") or 0, reverse=True)
    name_map = build_name_map(data, "ko")
    origin = pick_origin_name(data, "ko")

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
        {"title": "루트 A", "stops": [origin, base[0], base[1], base[2]]},
        {"title": "루트 B", "stops": [origin, base[2], base[3], base[1]]},
        {"title": "루트 C", "stops": [origin, base[1], base[4], base[0]]},
        {"title": "루트 D", "stops": [origin, base[3], base[4], base[2]]},
        {"title": "루트 E", "stops": [origin, base[4], base[0], base[3]]},
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
                "stops": stops,
            }
        )
    return routes


def load_kiosk_origin(data, keyword):
    kiosk_map = {k.get("kiosk_id"): k for k in data.get("kiosk", [])}
    for entry in data.get("kiosk_i18n", []):
        if entry.get("lang") == "ko" and entry.get("name") == keyword:
            kiosk_id = entry.get("kiosk_id")
            kiosk = kiosk_map.get(kiosk_id)
            if kiosk and kiosk.get("lat") is not None and kiosk.get("lng") is not None:
                return {
                    "kiosk_id": kiosk_id,
                    "name": keyword,
                    "lat": kiosk.get("lat"),
                    "lng": kiosk.get("lng"),
                }
    return {}


def main():
    service_key = load_service_key()
    if not service_key:
        print("Missing JEONJU_BUS_SERVICE_KEY in .env")
        return 1

    params = build_param_variants(service_key)
    routes_xml, route_status, route_url = fetch_with_fallback(
        ROUTE_LIST_ENDPOINTS, params
    )
    routes = []
    if routes_xml and route_status.get("code") == "000":
        routes = parse_route_list(routes_xml)

    keyword = "전주역"
    max_routes = int(os.environ.get("JEONJU_MAX_ROUTES", "200"))

    matched_stops = {}
    route_stop_names = {}

    try:
        with KIOSK_DATA_FILE.open("r", encoding="utf-8") as handle:
            kiosk_data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        kiosk_data = {}

    origin_info = load_kiosk_origin(kiosk_data, keyword)
    nearest_stops = []
    stop_search_status = {"code": None, "msg": None}
    if origin_info:
        stop_params = build_param_variants(
            service_key,
            {
                "searchFld": "stopnm",
                "searchNm": keyword,
            },
        )
        search_xml, stop_search_status, stop_search_url = fetch_with_fallback(
            STOP_SEARCH_ENDPOINTS, stop_params
        )
        if stop_search_status.get("code") != "000" or not search_xml:
            search_stops = []
        else:
            search_stops = parse_stop_list(search_xml)
        for stop in search_stops:
            try:
                stop_x = float(stop.get("stopX", ""))
                stop_y = float(stop.get("stopY", ""))
            except (TypeError, ValueError):
                continue
            distance_km = haversine_km(
                origin_info["lat"], origin_info["lng"], stop_y, stop_x
            )
            nearest_stops.append(
                {
                    "stopId": stop.get("stopId"),
                    "stopKname": stop.get("stopKname"),
                    "stopX": stop_x,
                    "stopY": stop_y,
                    "distance_km": round(distance_km, 3),
                }
            )
        nearest_stops = sorted(nearest_stops, key=lambda s: s["distance_km"])[:5]

    for idx, route in enumerate(routes[:max_routes]):
        brt_stdid = route.get("brtStdid")
        if not brt_stdid:
            continue
        stop_params = build_param_variants(
            service_key,
            {"brtStdid": brt_stdid},
        )
        stops_xml, stop_list_status, stop_list_url = fetch_with_fallback(
            ROUTE_STOPS_ENDPOINTS, stop_params
        )
        if stop_list_status.get("code") != "000" or not stops_xml:
            continue
        stops = parse_stop_list(stops_xml)
        stop_names = [s.get("stopKname") for s in stops if s.get("stopKname")]
        route_stop_names[brt_stdid] = stop_names
        for stop in stops:
            name = stop.get("stopKname")
            stop_id = stop.get("stopId")
            if not name or not stop_id:
                continue
            if keyword in name:
                matched_stops.setdefault(name, set()).add(stop_id)

    routes_def = build_routes_from_kiosk()
    segment_map = {}
    for route in routes_def:
        stops = route.get("stops", [])
        for seg_idx in range(len(stops) - 1):
            start = stops[seg_idx]
            end = stops[seg_idx + 1]
            candidates = []
            for brt_stdid, names in route_stop_names.items():
                if start in names and end in names:
                    candidates.append(brt_stdid)
            key = f"{route['title']}-{seg_idx}"
            segment_map[key] = {
                "from": start,
                "to": end,
                "route_ids": candidates[:10],
            }

    output = {
        "keyword": keyword,
        "origin_kiosk": origin_info,
        "nearest_stops": nearest_stops,
        "matched_stops": {k: sorted(list(v)) for k, v in matched_stops.items()},
        "segment_routes": segment_map,
        "max_routes_checked": max_routes,
        "total_routes": len(routes),
        "api_status": {
            "route_list": route_status,
            "stop_search": stop_search_status,
            "route_list_url": redact_service_key(route_url),
            "stop_search_url": (
                redact_service_key(stop_search_url) if origin_info else None
            ),
        },
    }
    api_ok = (
        output["api_status"]["route_list"].get("code") == "000"
        or output["api_status"]["stop_search"].get("code") == "000"
    )
    output["api_mode"] = "live" if api_ok else "fallback"
    if output["api_mode"] == "fallback" and FALLBACK_FILE.exists():
        try:
            fallback = json.loads(FALLBACK_FILE.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            fallback = {}
        if fallback.get("origin_kiosk"):
            output["origin_kiosk"] = fallback["origin_kiosk"]
        if not output["nearest_stops"] and fallback.get("nearest_stops"):
            output["nearest_stops"] = fallback["nearest_stops"]
        if fallback.get("segment_routes"):
            for key, entry in fallback["segment_routes"].items():
                if key in output["segment_routes"] and output["segment_routes"][key].get(
                    "route_ids"
                ):
                    continue
                if isinstance(entry, dict) and entry.get("route_ids"):
                    output["segment_routes"][key] = {
                        "from": output["segment_routes"].get(key, {}).get("from"),
                        "to": output["segment_routes"].get(key, {}).get("to"),
                        "route_ids": entry["route_ids"],
                    }

    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print("API status:")
    print(json.dumps(output["api_status"], ensure_ascii=False, indent=2))
    print(f"API mode: {output['api_mode']}")
    print(f"Wrote {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from math import atan2, cos, radians, sin, sqrt
import time

PROJECT_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_DIR / ".env"
KIOSK_DATA_FILE = PROJECT_DIR / "db-server" / "kiosk_data.json"
OUTPUT_FILE = Path(__file__).resolve().parent / "bus_mapping.json"

BASE_URLS = ["http://openapi.jeonju.go.kr/jeonjubus/openApi/traffic"]
ROUTE_LIST_ENDPOINTS = ["bus_location_all_common.do"]
ROUTE_INFO_ENDPOINTS = ["bus_location1_common.do"]
ROUTE_STOPS_ENDPOINTS = ["bus_location_busstop_list_common.do"]
ROUTE_DETAIL_INFO_ENDPOINTS = ["bus_location_busstop_info.do"]
STOP_SEARCH_ENDPOINTS = ["bus_location2_stopnm_common.do"]
ORIGIN_STOP_ALIASES = {
    "전주역": [
        "동부대로전주역",
        "장재마을",
        "전주역첫마중길",
    ],
    "전주한옥마을": [
        "오목대.한옥마을",
        "전동성당.한옥마을",
    ],
    "전주 동물원": [
        "전주동물원",
        "체련공원 소리문화의전당",
    ],
    "덕진공원": [
        "전주덕진공원",
        "전북대 종점",
        "기린대로 덕진공원",
    ],
    "경기전": [
        "동부시장",
        "외환은행",
        "전북 예술회관",
    ],
    "전동성당": [
        "전동성당.한옥마을",
        "전라감영.완산경찰서",
        "외환은행",
    ],
    "전주 남부시장": [
        "전동성당.한옥마을",
        "완산동시외버스정류소",
    ],
    "자만벽화마을": [
        "한벽루자만벽화마을",
        "기린대로병무청",
    ],
    "오목대": [
        "오목대.한옥마을",
        "기린대로 병무청",
    ],
    "아중호수": [
        "인교마을.아중요양병원",
        "아중제일 2차아파트",
    ],
}
ORIGIN_DISPLAY_NAME = "동부대로전주역"
STOP_ID_OVERRIDES = {
    "전주역": ["31109", "31093"],
    "동부대로전주역": ["31109", "31093"],
    "전주한옥마을": ["30704", "30703"],
    "전주 남부시장": ["30601", "30602"],
    "전동성당": ["30601", "30602"],
    "자만벽화마을": ["30704", "30703"],
    "오목대": ["30704", "30703"],
    "아중호수": ["30825"],
}


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
    key_names = ("serviceKey=", "ServiceKey=", "openApiAuthKey=", "openapiAuthKey=")
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
    params = {"serviceKey": service_key}
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


def parse_route_list_basic(xml_bytes):
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
        if "brtId" in data:
            routes.append(data)
    return routes


def fetch_route_stdid(service_key, brt_id, brt_class, retry_sleep=0.5, retries=2):
    attempt = 0
    while True:
        params = build_param_variants(
            service_key,
            {"brtId": brt_id, "brtClass": brt_class or "0"},
        )
        xml_bytes, status, _url = fetch_with_fallback(ROUTE_INFO_ENDPOINTS, params)
        if status.get("msg") and "LIMITED NUMBER" in status.get("msg"):
            attempt += 1
            if attempt > retries:
                raise RuntimeError("rate_limited")
            time.sleep(retry_sleep)
            continue
        if not xml_bytes or status.get("code") != "000":
            if brt_class and brt_class != "0":
                params = build_param_variants(
                    service_key,
                    {"brtId": brt_id, "brtClass": "0"},
                )
                xml_bytes, status, _url = fetch_with_fallback(
                    ROUTE_INFO_ENDPOINTS, params
                )
                if status.get("msg") and "LIMITED NUMBER" in status.get("msg"):
                    attempt += 1
                    if attempt > retries:
                        raise RuntimeError("rate_limited")
                    time.sleep(retry_sleep)
                    continue
                if not xml_bytes or status.get("code") != "000":
                    return None
            else:
                return None
        root = ET.fromstring(xml_bytes)
        break
    for item in root.iter():
        tag = item.tag.split("}")[-1]
        if tag != "list":
            continue
        for child in item:
            ctag = child.tag.split("}")[-1]
            if ctag == "brtStdid" and child.text:
                return child.text.strip()
    return None


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


def parse_route_detail_info(xml_bytes):
    root = ET.fromstring(xml_bytes)
    info = {}
    for item in root.iter():
        tag = item.tag.split("}")[-1]
        if tag == "list":
            for child in item:
                ctag = child.tag.split("}")[-1]
                if child.text:
                    info[ctag] = child.text.strip()
            break
    return info


def build_stop_name_variants(stops):
    variants = set()
    for stop in stops:
        name = stop.get("stopKname")
        if name:
            variants.add(name.strip())
    return variants


def build_stop_id_variants(stops):
    variants = set()
    for stop in stops:
        stop_id = stop.get("stopId")
        if stop_id:
            variants.add(stop_id.strip())
    return variants


def build_search_terms(name):
    terms = []
    base = name.strip()
    if base:
        terms.append(base)
    for alias in ORIGIN_STOP_ALIASES.get(base, []):
        if alias and alias not in terms:
            terms.append(alias)
    no_space = base.replace(" ", "")
    if no_space and no_space not in terms:
        terms.append(no_space)
    if base.startswith("전주 "):
        trimmed = base.replace("전주 ", "", 1)
        if trimmed and trimmed not in terms:
            terms.append(trimmed)
        trimmed_no_space = trimmed.replace(" ", "")
        if trimmed_no_space and trimmed_no_space not in terms:
            terms.append(trimmed_no_space)
    return terms


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

    return generate_routes(origin, base)


def generate_routes(origin, base):
    if not base:
        base = ["Spot A", "Spot B", "Spot C", "Spot D", "Spot E"]
    if len(base) < 5:
        base = (base + base)[0:5]
    return [
        {"title": "루트 A", "stops": [origin, base[0], base[1], base[2]]},
        {"title": "루트 B", "stops": [origin, base[2], base[3], base[1]]},
        {"title": "루트 C", "stops": [origin, base[1], base[4], base[0]]},
        {"title": "루트 D", "stops": [origin, base[3], base[4], base[2]]},
        {"title": "루트 E", "stops": [origin, base[4], base[0], base[3]]},
    ]


def load_kiosk_origin(data, keyword):
    candidates = [keyword]
    for alias in ORIGIN_STOP_ALIASES.get(keyword, []):
        if alias not in candidates:
            candidates.append(alias)
    for alias in ORIGIN_STOP_ALIASES.get("전주역", []):
        if alias not in candidates:
            candidates.append(alias)
    if "전주역" not in candidates:
        candidates.append("전주역")
    kiosk_map = {k.get("kiosk_id"): k for k in data.get("kiosk", [])}
    for entry in data.get("kiosk_i18n", []):
        if entry.get("lang") != "ko":
            continue
        if entry.get("name") not in candidates:
            continue
        kiosk_id = entry.get("kiosk_id")
        kiosk = kiosk_map.get(kiosk_id)
        if kiosk and kiosk.get("lat") is not None and kiosk.get("lng") is not None:
            return {
                "kiosk_id": kiosk_id,
                "name": entry.get("name"),
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
        routes = parse_route_list_basic(routes_xml)

    keyword = ORIGIN_DISPLAY_NAME
    max_routes = int(os.environ.get("JEONJU_MAX_ROUTES", "200"))
    api_sleep = float(os.environ.get("JEONJU_API_SLEEP", "0.15"))
    max_matches = int(os.environ.get("JEONJU_MAX_MATCHES", "3"))
    min_matches = int(os.environ.get("JEONJU_MIN_MATCHES", "10"))

    matched_stops = {}
    route_stop_names = {}
    route_stop_ids = {}
    stop_variants = {}
    stop_id_variants = {}

    try:
        with KIOSK_DATA_FILE.open("r", encoding="utf-8") as handle:
            kiosk_data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        kiosk_data = {}

    origin_info = load_kiosk_origin(kiosk_data, keyword)
    nearest_stops = []
    stop_search_status = {"code": None, "msg": None}
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
        stop_variants[keyword] = build_stop_name_variants(search_stops)
        stop_id_variants[keyword] = build_stop_id_variants(search_stops)
        if STOP_ID_OVERRIDES.get(keyword):
            stop_id_variants[keyword].update(STOP_ID_OVERRIDES[keyword])
    if origin_info:
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

    name_map = {
        e.get("place_id"): e.get("name")
        for e in kiosk_data.get("place_i18n", [])
        if e.get("lang") == "ko"
    }
    tour_places = [p for p in kiosk_data.get("places", []) if p.get("type") == "TOUR"]
    tour_places = sorted(
        tour_places, key=lambda p: p.get("priority_score") or 0, reverse=True
    )
    tour_names = []
    for place in tour_places:
        name = name_map.get(place.get("place_id"))
        if name:
            tour_names.append(name)

    for name in tour_names:
        if name in stop_variants:
            continue
        variants = set()
        for term in build_search_terms(name):
            stop_params = build_param_variants(
                service_key,
                {
                    "searchFld": "stopnm",
                    "searchNm": term,
                },
            )
            search_xml, status, _url = fetch_with_fallback(
                STOP_SEARCH_ENDPOINTS, stop_params
            )
            if status.get("code") != "000" or not search_xml:
                continue
            parsed = parse_stop_list(search_xml)
            variants.update(build_stop_name_variants(parsed))
            stop_id_variants.setdefault(name, set()).update(build_stop_id_variants(parsed))
        if variants:
            stop_variants[name] = variants
        if STOP_ID_OVERRIDES.get(name):
            stop_id_variants.setdefault(name, set()).update(STOP_ID_OVERRIDES[name])

    filtered_tours = [
        name
        for name in tour_names
        if stop_variants.get(name) or stop_id_variants.get(name)
    ]
    base_names = filtered_tours or tour_names
    origin_name = ORIGIN_DISPLAY_NAME if keyword == "전주역" else keyword or "Kiosk"
    routes_def = generate_routes(origin_name, base_names)

    resolved_routes = []
    rate_limit_hits = 0
    for idx, route in enumerate(routes[:max_routes]):
        brt_id = route.get("brtId")
        brt_class = route.get("brtClass", "0")
        if not brt_id:
            continue
        try:
            brt_stdid = fetch_route_stdid(
                service_key, brt_id, brt_class, retry_sleep=api_sleep
            )
        except RuntimeError:
            rate_limit_hits += 1
            print("Rate limit hit while resolving brtStdid; stopping early.")
            break
        if not brt_stdid:
            continue
        route["brtStdid"] = brt_stdid
        
        # New: Fetch detailed route info
        route_detail_params = build_param_variants(
            service_key,
            {"stdId": brt_stdid}, # Use stdId as per documentation
        )
        detail_xml, detail_status, _ = fetch_with_fallback(
            ROUTE_DETAIL_INFO_ENDPOINTS, route_detail_params
        )
        detailed_info = {}
        if detail_status.get("code") == "000" and detail_xml:
            detailed_info = parse_route_detail_info(detail_xml)
            route["detailed_info"] = detailed_info

        resolved_routes.append(route)
        if api_sleep:
            time.sleep(api_sleep)
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
        stop_ids = [s.get("stopId") for s in stops if s.get("stopId")]
        route_stop_names[brt_stdid] = stop_names
        route_stop_ids[brt_stdid] = stop_ids
        if api_sleep:
            time.sleep(api_sleep)
        for stop in stops:
            name = stop.get("stopKname")
            stop_id = stop.get("stopId")
            if not name or not stop_id:
                continue
            if keyword in name:
                matched_stops.setdefault(name, set()).add(stop_id)

    segment_map = {}
    for route in routes_def:
        stops = route.get("stops", [])
        for seg_idx in range(len(stops) - 1):
            start = stops[seg_idx]
            end = stops[seg_idx + 1]
            start_variants = stop_variants.get(start) or {start}
            end_variants = stop_variants.get(end) or {end}
            start_ids = stop_id_variants.get(start, set())
            end_ids = stop_id_variants.get(end, set())
            candidates = []
            for brt_stdid, names in route_stop_names.items():
                name_set = set(names)
                id_set = set(route_stop_ids.get(brt_stdid, []))
                if start_ids and end_ids:
                    if id_set.intersection(start_ids) and id_set.intersection(end_ids):
                        candidates.append(brt_stdid)
                        continue
                if name_set.intersection(start_variants) and name_set.intersection(
                    end_variants
                ):
                    candidates.append(brt_stdid)
            key = f"{route['title']}-{seg_idx}"
            segment_map[key] = {
                "from": start,
                "to": end,
                "route_ids": candidates[:max_matches],
            }
    filled = [v for v in segment_map.values() if v.get("route_ids")]
    if len(filled) < min_matches:
        print(
            f"Warning: only {len(filled)} segments matched. "
            f"Increase JEONJU_MAX_ROUTES or lower JEONJU_MIN_MATCHES."
        )

    route_info = {}
    for r in resolved_routes:
        brt_stdid = r.get("brtStdid")
        if brt_stdid:
            info_data = {
                "brtId": r.get("brtId"),
                "brtClass": r.get("brtClass"),
            }
            if r.get("detailed_info"):
                info_data.update(r["detailed_info"])
            route_info[brt_stdid] = info_data

    output = {
        "keyword": keyword,
        "origin_kiosk": origin_info,
        "nearest_stops": nearest_stops,
        "matched_stops": {k: sorted(list(v)) for k, v in matched_stops.items()},
        "routes": routes_def,
        "segment_routes": segment_map,
        "route_info": route_info,
        "route_ids": [r.get("brtStdid") for r in resolved_routes if r.get("brtStdid")],
        "max_routes_checked": max_routes,
        "total_routes": len(resolved_routes),
        "api_status": {
            "route_list": route_status,
            "stop_search": stop_search_status,
            "route_list_url": redact_service_key(route_url),
            "stop_search_url": (
                redact_service_key(stop_search_url) if stop_search_url else None
            ),
        },
    }
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    if rate_limit_hits:
        print(f"Rate limit hits: {rate_limit_hits}")
    print("API status:")
    print(json.dumps(output["api_status"], ensure_ascii=False, indent=2))
    print(f"Wrote {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

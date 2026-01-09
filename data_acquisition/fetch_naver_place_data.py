import argparse
import json
import os
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import requests

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KIOSK_DATA_PATH = os.path.join(PROJECT_ROOT, "db-server", "kiosk_data.json")
DEFAULT_MAPPING_PATH = os.path.join(os.path.dirname(__file__), "naver_place_ids.json")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

REQUEST_TIMEOUT = 10
REQUEST_SLEEP = 0.2
MAX_MENU_IMAGES = 20
MAX_PHOTO_IMAGES = 20


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def build_mapping_template(kiosk_data: Dict[str, Any], output_path: str) -> None:
    places = [
        p for p in kiosk_data.get("places", [])
        if p.get("type") == "FOOD"
    ]
    name_by_id = {
        i["place_id"]: i["name"]
        for i in kiosk_data.get("place_i18n", [])
        if i.get("lang") == "ko"
    }
    template = []
    for place in places:
        place_id = place["place_id"]
        template.append({
            "place_id": place_id,
            "name": name_by_id.get(place_id, ""),
            "naver_place_id": ""
        })
    save_json(output_path, template)


def load_mapping(path: str) -> Dict[int, str]:
    data = load_json(path)
    mapping = {}
    if isinstance(data, list):
        for entry in data:
            try:
                place_id = int(entry.get("place_id"))
            except (TypeError, ValueError):
                continue
            naver_place_id = str(entry.get("naver_place_id") or "").strip()
            if naver_place_id:
                mapping[place_id] = naver_place_id
    return mapping


def fetch_html(url: str) -> Optional[str]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        print(f"Failed to fetch {url}: {exc}")
        return None


def extract_next_data(html: str) -> Optional[Dict[str, Any]]:
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def walk_nodes(node: Any) -> Iterable[Any]:
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        if isinstance(current, dict):
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)


def collect_menu_items(node: Any) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    for item in walk_nodes(node):
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("menuName")
        price = item.get("price") or item.get("menuPrice")
        desc = item.get("description") or item.get("desc") or item.get("menuDesc")
        if name and isinstance(name, str):
            results.append({
                "name": name.strip(),
                "price": str(price).strip() if price is not None else "",
                "description": desc.strip() if isinstance(desc, str) else ""
            })
    seen = set()
    deduped = []
    for item in results:
        key = (item["name"], item["price"], item["description"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def collect_image_urls(node: Any) -> Set[str]:
    urls: Set[str] = set()
    for item in walk_nodes(node):
        if isinstance(item, dict):
            for key in ("originUrl", "imageUrl", "url", "imgUrl", "photoUrl", "thumbUrl"):
                value = item.get(key)
                if isinstance(value, str) and value.startswith("http"):
                    urls.add(value)
        elif isinstance(item, str) and item.startswith("http"):
            if "img" in item or "image" in item or "photo" in item:
                urls.add(item)
    return urls


def fetch_place_data(naver_place_id: str) -> Tuple[List[Dict[str, str]], Set[str], Set[str]]:
    menu_url = f"https://pcmap.place.naver.com/restaurant/{naver_place_id}/menu"
    photo_url = f"https://pcmap.place.naver.com/restaurant/{naver_place_id}/photo"
    home_url = f"https://pcmap.place.naver.com/restaurant/{naver_place_id}/home"
    entry_url = f"https://map.naver.com/p/entry/place/{naver_place_id}"

    menu_items: List[Dict[str, str]] = []
    menu_images: Set[str] = set()
    photos: Set[str] = set()

    menu_html = fetch_html(menu_url)
    if menu_html:
        menu_data = extract_next_data(menu_html)
        if menu_data:
            menu_items = collect_menu_items(menu_data)
            menu_images = collect_image_urls(menu_data)

    time.sleep(REQUEST_SLEEP)

    photo_html = fetch_html(photo_url)
    if photo_html:
        photo_data = extract_next_data(photo_html)
        if photo_data:
            photos = collect_image_urls(photo_data)

    menu_images = set(list(menu_images)[:MAX_MENU_IMAGES])
    photos = set(list(photos)[:MAX_PHOTO_IMAGES])

    if not menu_images and not photos:
        for fallback_url in (home_url, entry_url):
            fallback_html = fetch_html(fallback_url)
            if not fallback_html:
                continue
            og_match = re.search(r'<meta property=\"og:image\" content=\"([^\"]+)\"', fallback_html)
            if not og_match:
                og_match = re.search(r'<meta property=\"og:image:url\" content=\"([^\"]+)\"', fallback_html)
            if not og_match:
                og_match = re.search(r'<meta name=\"twitter:image\" content=\"([^\"]+)\"', fallback_html)
            if og_match:
                photos.add(og_match.group(1))
                break

    return menu_items, menu_images, photos


def add_images(
    place_images: List[Dict[str, Any]],
    place_id: int,
    start_image_id: int,
    urls: Iterable[str],
    kind: str,
) -> int:
    image_id = start_image_id
    for url in urls:
        place_images.append({
            "image_id": image_id,
            "place_id": place_id,
            "kind": kind,
            "url": url,
            "storage_key": None,
            "mime": "image/jpeg",
            "width": 0,
            "height": 0,
            "bytes_len": 0,
            "is_primary": 0,
            "sort_order": 0,
        })
        image_id += 1
    return image_id


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping", default=DEFAULT_MAPPING_PATH)
    parser.add_argument("--template", action="store_true", help="write mapping template and exit")
    args = parser.parse_args()

    kiosk_data = load_json(KIOSK_DATA_PATH)

    if args.template:
        build_mapping_template(kiosk_data, args.mapping)
        print(f"Wrote mapping template to {args.mapping}")
        return

    if not os.path.exists(args.mapping):
        print(f"Mapping file not found: {args.mapping}")
        print("Run with --template to create a template.")
        return

    mapping = load_mapping(args.mapping)
    if not mapping:
        print("No place_id -> naver_place_id mappings found.")
        return

    places = kiosk_data.get("places", [])
    place_images = kiosk_data.get("place_images", [])
    max_image_id = max((img.get("image_id", 0) for img in place_images), default=0)
    image_id_counter = max_image_id + 1

    place_by_id = {p["place_id"]: p for p in places}

    for place_id, naver_place_id in mapping.items():
        place = place_by_id.get(place_id)
        if not place:
            continue
        print(f"Fetching Naver Place data for place_id={place_id}, naver_place_id={naver_place_id}")
        menu_items, menu_images, photo_images = fetch_place_data(naver_place_id)

        if menu_items:
            place["menus"] = [
                {
                    "name": item["name"],
                    "description": item["description"],
                    "price": item["price"],
                    "image_id": None,
                }
                for item in menu_items
            ]

        if menu_images:
            image_id_counter = add_images(place_images, place_id, image_id_counter, menu_images, "MENU")

        if photo_images:
            image_id_counter = add_images(place_images, place_id, image_id_counter, photo_images, "PHOTO")

        food_info = place.get("food_info", {})
        food_info["naver_place_id"] = naver_place_id
        place["food_info"] = food_info

        time.sleep(REQUEST_SLEEP)

    kiosk_data["place_images"] = place_images
    save_json(KIOSK_DATA_PATH, kiosk_data)
    print("Done. Updated kiosk_data.json.")


if __name__ == "__main__":
    main()

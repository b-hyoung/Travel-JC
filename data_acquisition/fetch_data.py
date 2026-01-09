import requests
import json
import os
import re
import time

# 사용자로부터 받은 서비스 키
SERVICE_KEY = "f737e05448f75416ea44e38eded5a059a4e28c857b61e08262d416db7d6e63c4"

# TourAPI 설정
API_ENDPOINT = "https://apis.data.go.kr/B551011/KorService2/areaBasedList2"
DETAIL_INTRO_ENDPOINT = "https://apis.data.go.kr/B551011/KorService2/detailIntro2"
DETAIL_IMAGE_ENDPOINT = "https://apis.data.go.kr/B551011/KorService2/detailImage2"
CONTENT_TYPE_ID = "39"  # 음식점
KEYWORD = "전주"       # (검색용으로는 사용하지 않음, 로그용 유지)
AREA_CODE = "37"       # 전북
SIGUNGU_CODE = "12"    # 전주시
NUM_OF_ROWS = 40
MOBILE_APP_NAME = "JeonjuKiosk"
MOBILE_OS = "ETC"
REQUEST_TIMEOUT = 10
DETAIL_REQUEST_SLEEP = 0.1
ADDRESS_PREFIXES = ("전북 전주시", "전라북도 전주시", "전북특별자치도 전주시")

# 출력 파일 경로
OUTPUT_JSON_PATH = os.path.join(os.path.dirname(__file__), '..', 'db-server', 'kiosk_data.json')

def is_success_response(api_data):
    return api_data and api_data.get('response', {}).get('header', {}).get('resultCode') == '0000'


def request_tour_api(endpoint, params):
    try:
        response = requests.get(endpoint, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        if not is_success_response(data):
            result_msg = data.get('response', {}).get('header', {}).get('resultMsg') if data else 'Unknown error'
            print(f"API Error from {endpoint}: {result_msg}")
            return None
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        if 'response' in locals() and response is not None:
            print("Raw Response:", response.text)
    except json.JSONDecodeError:
        print("Error: API response is not valid JSON.")
        print("Raw Response:", response.text)
    return None


def parse_items(api_data):
    items_data = api_data.get('response', {}).get('body', {}).get('items', {})
    if isinstance(items_data, str) and not items_data:
        return []
    if isinstance(items_data, dict):
        items = items_data.get('item', [])
        if items and not isinstance(items, list):
            items = [items]
        return items
    return []


def fetch_tour_api_data():
    """Fetches restaurant data from the TourAPI based on area codes."""
    params = {
        'serviceKey': SERVICE_KEY,
        'contentTypeId': CONTENT_TYPE_ID,
        'areaCode': AREA_CODE,
        'sigunguCode': SIGUNGU_CODE,
        'numOfRows': NUM_OF_ROWS,
        'pageNo': 1,
        'MobileOS': MOBILE_OS,
        'MobileApp': MOBILE_APP_NAME,
        '_type': 'json',
        'arrange': 'P'  # P: 인기순
    }

    print(f"Requesting data from TourAPI with endpoint: {API_ENDPOINT} (areaCode={AREA_CODE}, sigunguCode={SIGUNGU_CODE})...")
    data = request_tour_api(API_ENDPOINT, params)
    if data:
        print("Successfully received data.")
    return data


def fetch_detail_intro(content_id):
    params = {
        'serviceKey': SERVICE_KEY,
        'contentId': content_id,
        'contentTypeId': CONTENT_TYPE_ID,
        'MobileOS': MOBILE_OS,
        'MobileApp': MOBILE_APP_NAME,
        '_type': 'json'
    }
    data = request_tour_api(DETAIL_INTRO_ENDPOINT, params)
    if not data:
        return {}
    items = parse_items(data)
    return items[0] if items else {}


def fetch_detail_images(content_id):
    params = {
        'serviceKey': SERVICE_KEY,
        'contentId': content_id,
        'imageYN': 'Y',
        'subImageYN': 'Y',
        'MobileOS': MOBILE_OS,
        'MobileApp': MOBILE_APP_NAME,
        '_type': 'json'
    }
    data = request_tour_api(DETAIL_IMAGE_ENDPOINT, params)
    if not data:
        return []
    return parse_items(data)


def normalize_text(text):
    if not isinstance(text, str):
        return ''
    cleaned = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    return cleaned.strip()


def split_menu_items(text):
    if not text:
        return []
    normalized = normalize_text(text)
    parts = [part.strip() for part in normalized.replace('\r', '\n').split('\n')]
    return [part for part in parts if part]

def transform_data(api_data):
    """Transforms the API response into the kiosk_data.json format."""
    new_places = []
    new_place_i18n_ko = []
    new_place_i18n_en = []
    new_place_images = []

    items = parse_items(api_data)
        
    if not items:
        print("Warning: No items found in the API response.")
        return None

    place_id_counter = 8000
    image_id_counter = 80000

    print(f"Transforming {len(items)} items...")

    for item in items:
        if not item.get('mapy') or not item.get('mapx'):
            continue
        addr1 = item.get('addr1', '')
        if addr1 and not (addr1.startswith(ADDRESS_PREFIXES) or "전주시" in addr1):
            continue

        content_id = item.get('contentid')
        detail_intro = fetch_detail_intro(content_id) if content_id else {}
        detail_images = fetch_detail_images(content_id) if content_id else []
        if DETAIL_REQUEST_SLEEP > 0:
            time.sleep(DETAIL_REQUEST_SLEEP)

        hours_text = normalize_text(detail_intro.get('opentimefood')) or "영업시간 정보 없음"
        en_hours_text = hours_text if hours_text != "영업시간 정보 없음" else "No hours information"

        menu_names = []
        for field_name in ("firstmenu", "treatmenu"):
            menu_names.extend(split_menu_items(detail_intro.get(field_name, "")))
        seen_menu_names = set()
        menus = []
        for name in menu_names:
            if name in seen_menu_names:
                continue
            seen_menu_names.add(name)
            menus.append({
                "name": name,
                "description": "",
                "price": "",
                "image_id": None
            })

        food_info = {}
        for field_name in ("treatmenu", "firstmenu", "infocenterfood", "reservationfood"):
            value = normalize_text(detail_intro.get(field_name))
            if value:
                food_info[field_name] = value

        place_id = place_id_counter
        image_id = image_id_counter

        new_place = {
            "place_id": place_id,
            "type": "FOOD",
            "category": "restaurant",
            "lat": float(item.get('mapy')),
            "lng": float(item.get('mapx')),
            "tags": [], "is_halal": None, "is_vegan": None, "priority_score": 0,
            "cover_image_id": image_id if item.get('firstimage') else None,
            "menus": menus
        }
        if food_info:
            new_place["food_info"] = food_info
        new_places.append(new_place)

        new_i18n_ko = {
            "place_id": place_id, "lang": "ko", "name": item.get('title', '이름 없음'),
            "short_desc": item.get('addr1', ''), "address_text": item.get('addr1', ''),
            "hours_text": hours_text
        }
        new_place_i18n_ko.append(new_i18n_ko)
        
        new_i18n_en = {
            "place_id": place_id, "lang": "en", "name": f"[EN] {item.get('title', 'No Name')}",
            "short_desc": "", "address_text": "", "hours_text": en_hours_text
        }
        new_place_i18n_en.append(new_i18n_en)

        place_image_urls = set()
        menu_image_ids = []

        if item.get('firstimage'):
            new_image = {
                "image_id": image_id, "place_id": place_id, "kind": "PHOTO",
                "url": item.get('firstimage'), "storage_key": None, "mime": "image/jpeg",
                "width": 0, "height": 0, "bytes_len": 0, "is_primary": 1, "sort_order": 0
            }
            new_place_images.append(new_image)
            place_image_urls.add(item.get('firstimage'))
            image_id_counter += 1

        sort_order = 1 if item.get('firstimage') else 0
        for image in detail_images:
            url = image.get('originimgurl') or image.get('smallimageurl')
            if not url or url in place_image_urls:
                continue
            imgtype = str(image.get('imgtype')) if image.get('imgtype') is not None else ''
            kind = "MENU" if imgtype == "2" else "PHOTO"
            new_image = {
                "image_id": image_id_counter, "place_id": place_id, "kind": kind,
                "url": url, "storage_key": None, "mime": "image/jpeg",
                "width": 0, "height": 0, "bytes_len": 0, "is_primary": 0, "sort_order": sort_order
            }
            new_place_images.append(new_image)
            place_image_urls.add(url)
            if kind == "MENU":
                menu_image_ids.append(image_id_counter)
            image_id_counter += 1
            sort_order += 1

        if menus and menu_image_ids:
            for menu, menu_image_id in zip(menus, menu_image_ids):
                menu["image_id"] = menu_image_id
        
        place_id_counter += 1

    return {
        "places": new_places, "place_i18n": new_place_i18n_ko + new_place_i18n_en,
        "place_images": new_place_images
    }

def main():
    api_data = fetch_tour_api_data()
    if api_data is None:
        print("API data fetch failed.")
        return

    if 'response' not in api_data or 'header' not in api_data['response']:
        print("Invalid API response format. Full response:", api_data)
        return

    result_code = api_data['response']['header'].get('resultCode')
    if result_code != '0000':
        print(f"API Error: {api_data['response']['header'].get('resultMsg')} (Code: {result_code})")
        return

    transformed_data = transform_data(api_data)
    if not transformed_data:
        return
        
    try:
        with open(OUTPUT_JSON_PATH, 'r', encoding='utf-8') as f:
            kiosk_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        kiosk_data = { "dataset_version": 1, "kiosk": [], "kiosk_i18n": [] }

    existing_tour_places = [p for p in kiosk_data.get("places", []) if p.get("type") == "TOUR"]
    kiosk_data["places"] = existing_tour_places + transformed_data["places"]
    
    existing_tour_place_ids = {p["place_id"] for p in existing_tour_places}
    
    existing_i18n = [i for i in kiosk_data.get("place_i18n", []) if i.get("place_id") in existing_tour_place_ids]
    kiosk_data["place_i18n"] = existing_i18n + transformed_data["place_i18n"]

    existing_images = [img for img in kiosk_data.get("place_images", []) if img.get("place_id") in existing_tour_place_ids]
    kiosk_data["place_images"] = existing_images + transformed_data["place_images"]
    
    kiosk_data["dataset_version"] = kiosk_data.get("dataset_version", 1) + 1

    with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(kiosk_data, f, indent=2, ensure_ascii=False)

    print(f"Successfully updated {OUTPUT_JSON_PATH} with {len(transformed_data['places'])} new food places.")

if __name__ == '__main__':
    main()

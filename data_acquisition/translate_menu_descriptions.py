import argparse
import json
import os
import time
from typing import Dict, List, Tuple

import requests

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_INPUT = os.path.join(PROJECT_ROOT, "db-server", "kiosk_data.json")
DEFAULT_OUTPUT = os.path.join(PROJECT_ROOT, "db-server", "menu_description_i18n.json")

API_ENDPOINT = "https://translation.googleapis.com/language/translate/v2"
REQUEST_TIMEOUT = 15
REQUEST_SLEEP = 0.2
MAX_BATCH_SIZE = 100

LANGUAGE_MAP = {
    "한국어": "ko",
    "English": "en",
    "日本語": "ja",
    "简体中文": "zh-CN",
    "繁體中文": "zh-TW",
    "Deutsch": "de",
    "Nederlands": "nl",
    "Svenska": "sv",
    "Français": "fr",
    "Italiano": "it",
    "Español": "es",
    "Português": "pt",
    "Русский": "ru",
    "Polski": "pl",
    "Čeština": "cs",
    "Українська": "uk",
    "Lietuvių": "lt",
    "Latviešu": "lv",
}

ENV_PATH = os.path.join(PROJECT_ROOT, ".env")


def load_env(path: str) -> None:
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        return


def chunk_list(items: List[Tuple[dict, str]], size: int) -> List[List[Tuple[dict, str]]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def translate_batch(texts: List[str], source: str, target: str, api_key: str) -> List[str]:
    payload = {
        "q": texts,
        "source": source,
        "target": target,
        "format": "text",
        "key": api_key,
    }
    response = requests.post(API_ENDPOINT, data=payload, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    translations = data.get("data", {}).get("translations", [])
    return [t.get("translatedText", "") for t in translations]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--source", default="ko")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env(ENV_PATH)
    api_key = os.environ.get("GOOGLE_TRANSLATE_API_KEY", "")
    if not api_key:
        print("GOOGLE_TRANSLATE_API_KEY 환경 변수가 필요합니다.")
        return

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    items: List[Tuple[dict, str]] = []
    for place in data.get("places", []):
        if place.get("type") != "FOOD":
            continue
        for idx, menu in enumerate(place.get("menus", [])):
            description = (menu.get("description") or "").strip()
            if not description:
                continue
            meta = {
                "place_id": place.get("place_id"),
                "menu_index": idx,
                "menu_name": menu.get("name", ""),
            }
            items.append((meta, description))

    if args.limit and args.limit > 0:
        items = items[: args.limit]

    targets = [code for code in LANGUAGE_MAP.values() if code != args.source]
    output_rows = []

    for target in targets:
        batches = chunk_list(items, MAX_BATCH_SIZE)
        for batch in batches:
            batch_meta = [meta for meta, _ in batch]
            batch_texts = [text for _, text in batch]
            if args.dry_run:
                translated = [f"[{target}] {text}" for text in batch_texts]
            else:
                translated = translate_batch(batch_texts, args.source, target, api_key)
            for meta, translated_text in zip(batch_meta, translated):
                output_rows.append({
                    "place_id": meta["place_id"],
                    "menu_index": meta["menu_index"],
                    "menu_name": meta["menu_name"],
                    "lang": target,
                    "description": translated_text,
                })
            time.sleep(REQUEST_SLEEP)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_rows, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(output_rows)} translations to {args.output}")


if __name__ == "__main__":
    main()

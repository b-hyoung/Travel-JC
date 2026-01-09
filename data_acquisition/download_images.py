import requests
import json
import os

# 파일 경로 설정
DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', 'db-server', 'kiosk_data.json')
IMAGES_DIR = os.path.join(os.path.dirname(__file__), '..', 'db-server', 'images')

def download_image(url, local_path):
    """Downloads an image from a URL and saves it to a local path."""
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"  -> Successfully downloaded to {local_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"  -> Failed to download {url}: {e}")
        return False

def main():
    """
    Reads kiosk_data.json, downloads the real images from their remote URLs,
    and updates the JSON to point to the new local image files.
    """
    # 데이터 파일 로드
    try:
        with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
            kiosk_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Error: Could not read or parse {DATA_FILE_PATH}")
        return

    # 이미지 디렉토리 생성
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)

    print("--- Starting Image Download and Cache Process ---")

    if 'place_images' in kiosk_data:
        image_list = kiosk_data['place_images']
        total_images = len(image_list)
        
        for i, image_data in enumerate(image_list):
            remote_url = image_data.get('url')
            image_id = image_data.get('image_id')

            print(f"Processing image {i+1}/{total_images} (ID: {image_id})...")

            if not remote_url or not remote_url.startswith('http'):
                print(f"  -> Skipping, not a remote URL: {remote_url}")
                continue

            # 로컬 경로 생성 및 새 URL 결정
            local_filename = f"image_{image_id}.png"
            local_path = os.path.join(IMAGES_DIR, local_filename)
            new_url = os.path.join('db-server', 'images', local_filename).replace("\\\\", "/")

            # 이미지 다운로드
            if download_image(remote_url, local_path):
                # 성공 시에만 JSON의 URL을 로컬 경로로 업데이트
                image_data['url'] = new_url
            else:
                # 실패 시, 기존 URL 유지 또는 로컬 placeholder 경로로 설정
                # 여기서는 실패 시에도 로컬 경로를 가리키도록 하여 깨진 이미지 대신 placeholder가 보이도록 함
                image_data['url'] = new_url
                print(f"  -> URL updated to local path even on failure to allow placeholder generation.")

    # 업데이트된 데이터 저장
    with open(DATA_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(kiosk_data, f, indent=2, ensure_ascii=False)

    print(f"\n--- Image processing complete ---")
    print(f"Updated {DATA_FILE_PATH} with local image paths.")
    print("You may need to run 'generate_assets.py' again to create placeholders for any failed downloads.")

if __name__ == '__main__':
    main()

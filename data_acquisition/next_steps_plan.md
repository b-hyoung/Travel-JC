# 다음 진행 계획: 메뉴 정보 및 추가 이미지 확보

## 목표
- 각 식당의 상세 메뉴 정보와 메뉴 사진을 확보합니다.
- 이미지가 없는 장소에 추가 이미지를 보강합니다.

## 사용 API 오퍼레이션
- `searchKeyword`: 현재 사용 중 (초기 식당 목록 검색)
- `detailIntro`: 각 식당의 상세 정보 (메뉴 텍스트, 영업시간 등) 조회
- `detailImage`: 각 식당의 추가 이미지 (메뉴 사진 포함) 조회

## `fetch_data.py` 스크립트 수정 계획

### 1단계: 초기 목록 가져오기 (기존 `searchKeyword` 방식 유지)
- `fetch_data.py`는 `searchKeyword` API를 통해 "전주" 키워드로 40개 식당의 기본 목록을 가져옵니다. (현재 스크립트와 동일)

### 2단계: 각 식당별 상세 정보 및 이미지 조회 (새로운 로직 추가)
- 1단계에서 가져온 각 식당(`item`)에 대해 다음 API를 추가로 호출합니다.
    - **`detailIntro` 호출**:
        - `contentId` (각 식당의 고유 ID)를 사용하여 `detailIntro` API를 호출합니다.
        - 응답에서 **'대표메뉴(`treatmenu`)'** 와 **'영업시간(`opentimefood`)'** 정보를 추출합니다.
        - 이 외에 `infocenterfood`, `firstmenu`, `reservationfood` 등 다른 관련 필드도 확인하여 데이터가 있으면 함께 가져옵니다.
    - **`detailImage` 호출**:
        - `contentId`를 사용하여 `detailImage` API를 호출합니다.
        - 응답에서 해당 식당에 등록된 모든 이미지 목록을 가져옵니다. 이 이미지들은 `이미지 타입(imgtype: 1=원본, 2=메뉴)`을 포함할 수 있으므로, 메뉴 사진을 구분하는 데 활용합니다.

### 3단계: `kiosk_data.json` 구조 업데이트 및 데이터 통합

- `transform_data` 함수를 수정하여 2단계에서 가져온 상세 정보를 통합합니다.
- `kiosk_data.json`의 `places` 항목 구조를 다음과 같이 확장합니다.
    - `places` 객체 내에 `menus`라는 새로운 배열을 추가합니다.
        ```json
        {
          "place_id": ...,
          "type": "FOOD",
          "category": "restaurant",
          // ... 기존 필드 ...
          "menus": [ // 새로운 필드
            {
              "name": "비빔밥",
              "description": "전주 전통 비빔밥",
              "price": "10,000원",
              "image_id": 12345 // 메뉴 사진이 있다면 연결
            },
            // ... 다른 메뉴들 ...
          ]
        }
        ```
    - `place_i18n` 항목에는 `hours_text`에 `opentimefood` 정보를 반영합니다.
    - `place_images` 항목에는 `detailImage`에서 가져온 추가 이미지들을 `kind` (예: `MENU_PHOTO`)와 함께 추가합니다. (기존 `cover_image_id`로 연결된 이미지는 `cover_image_id` 그대로 사용)

## 예상되는 고려사항 및 Trade-offs

-   **데이터 수집 시간:** 각 식당마다 2번의 API를 추가로 호출하므로, 전체 데이터 수집 시간이 40개 * 2회 = 80회 이상 추가로 증가하여 **상당히 길어질 수 있습니다.**
-   **API 응답:** `detailIntro`나 `detailImage` API가 모든 식당에 대해 메뉴 정보나 추가 이미지를 제공하지 않을 수 있습니다. 데이터가 없는 경우는 해당 항목을 비워두는 방식으로 처리합니다.
-   **API 요청 제한:** 단시간 내에 많은 API 호출을 하게 되므로, TourAPI의 일일 요청 제한에 유의해야 합니다.

## 실행 계획

1.  `fetch_data.py` 스크립트를 위 계획에 따라 수정합니다.
2.  수정된 스크립트를 실행하여 데이터를 수집합니다.
3.  `download_images.py`를 실행하여 새로운 이미지들을 다운로드합니다.
4.  `setup_database.py`를 실행하여 DB를 업데이트합니다.
5.  GUI를 실행하여 변경사항을 확인합니다.

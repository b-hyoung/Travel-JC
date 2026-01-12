# Kiosk Food Data Access Summary

## 접근 방식 요약
- 데이터 소스: `db-server/kiosk.db` (GUI에서 `db_manager.py` 사용)
- 필터 기준: `places.type == 'FOOD'`
- 접근 흐름:
  - `get_all_places()`로 FOOD 장소 목록 조회
  - 각 장소의 `place_id`로 `get_place_details(place_id)` 호출
  - `place_details`에서 `menus`, `images`, `food_info`, `i18n` 정보를 함께 사용
  - 좌측 리스트는 **메뉴 단위**로 구성, 클릭 시 선택된 메뉴의 `place_id`로 해당 식당 정보/전체 메뉴 표시

## 현재 GUI 동작 요약 (kiosk_gui.py)
- 좌측 리스트: 음식(메뉴) 아이템
  - `menu.name`, `menu.price`, 썸네일(`menu.image_id` → `place_images.url`)
- 클릭 시 우측 디테일:
  - 선택 메뉴 이미지 + 설명
  - 식당 사진/기본정보(설명, 영업시간, 연락처 등)
  - 하단 전체 메뉴(썸네일 + 이름 + 가격)

## AI용 프롬프트 예시
아래 형식으로 요약/설명 요청 가능:
"""
프로젝트의 키오스크 음식 데이터 접근 구조를 간단히 설명해줘.
- 필터 기준은 places.type == 'FOOD'
- 좌측은 메뉴 단위 리스트, 클릭 시 place_id로 식당 상세 및 전체 메뉴 표시
- 데이터 출처는 db-server/kiosk.db (db_manager.get_all_places / get_place_details)
- 결과는 5줄 이내로 요약
"""

또는 UI 기준 요약 요청:
"""
kiosk_gui.py 기준으로 데이터 흐름을 요약해줘.
1) 음식(메뉴) 리스트 구성 과정
2) 메뉴 클릭 후 상세 표시 과정
3) 이미지 매칭 방식 (menu.image_id → place_images.url)
"""

## ?? ??? ??
- DB ???? `db-server/kiosk_data.json` ??? ??? ???? ???
- ??? JSON ??? ??? ???? ??? ??/??? ???? ? ?? ??


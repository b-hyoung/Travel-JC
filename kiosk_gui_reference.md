# Kiosk GUI Reference Points

프론트 구현/연동 시 참고할 핵심 지점만 정리했습니다.

## 리스트 구성 (메뉴 리스트업)
- 함수: `KioskMainWindow.load_places()`
- 역할: `places.type == 'FOOD'`만 가져와 메뉴 단위 리스트를 구성
- 각 메뉴 아이템에 `menu_name`, `menu_price`, `menu_desc`, `menu_image_url`, `place_id`를 매핑

## 리스트 아이템 UI
- 클래스: `MenuListItem`
- 역할: 좌측 리스트에서 썸네일 + 메뉴명 + 가격/식당명 표시

## 클릭 → 상세 화면
- 함수: `KioskMainWindow.on_menu_item_clicked()`
- 함수: `KioskMainWindow.set_selected_menu()`
- 역할: 클릭된 메뉴로 디테일(사진/설명) + 식당 기본정보 + 전체 메뉴 렌더링

## 전체 메뉴 섹션
- 함수: `KioskMainWindow.populate_full_menu_grid()`
- 역할: 하단 전체 메뉴를 썸네일 + 이름 + 가격 카드로 표시

## 데이터 기준
- 구조: `db-server/kiosk_data.json` (DB 스키마는 동일 구조)

---
이 문서는 프론트 연동 시 필요한 흐름만 요약한 참고용입니다.

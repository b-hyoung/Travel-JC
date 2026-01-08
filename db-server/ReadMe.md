# 📍 Jeonju Smart Tourist Kiosk
### Offline-Resilient Location-Based Tourist Guidance System

외국인 관광객이 전주에서  
**지금 이 자리에서 무엇을 할지 즉시 결정할 수 있도록 돕는  
고정형 관광 안내 키오스크 시스템**

본 프로젝트의 핵심은  
**“어떤 상황에서도 관광 안내가 끊기지 않는 것”**이다.

---

## 1. 프로젝트 배경

전주를 방문하는 외국인 관광객 수는 지속적으로 증가하고 있으나,  
관광 콘텐츠에 **접근하는 방법의 부재**로 인해 실제 만족도는 높지 않은 문제가 발생하고 있다.

특히 다음과 같은 문제가 반복된다.

- 어디를 가야 할지 즉시 판단하기 어렵다
- 이동 과정(버스/도보)이 직관적이지 않다
- 언어 장벽으로 정보 탐색 비용이 크다
- 네트워크 환경에 따라 안내 품질이 급격히 저하된다

본 프로젝트는 관광 콘텐츠 자체가 아닌,  
**관광 정보에 접근하고 이동을 결정하는 과정**을 개선하는 것을 목표로 한다.

---

## 2. 프로젝트 목표

- 앱 설치 없이 즉시 사용 가능한 관광 안내
- 현재 위치 기준의 행동 결정 지원
- 온라인/오프라인 환경에서도 기본 안내 유지
- 검증된 DB 기반 정보 제공
- AI는 정보 생성이 아닌 **설명 보조 역할**만 수행

---

## 3. 시스템 전체 구조

### 키오스크 (Raspberry Pi)
- 화면 기반 UI
- 언어 선택
- 로컬 SQLite 캐시 DB
- 오프라인 기본 관광 안내
- 이벤트 Outbox 큐(네트워크 복구 시 업로드)

### 중앙 서버 (Django + PostgreSQL)
- 관광/장소/버스 원본 데이터 관리
- 사용자/인증 관리
- 동기화 API 제공
- QR 인증 및 퀘스트 관리
- 이벤트 집계

### AI (온라인)
- 자연어 질문 의도 해석
- 서버 DB 조회 결과 요약
- 정보 생성 ❌ / 설명만 수행 ⭕

---

## 4. 온라인 / 오프라인 동작 정책

### ONLINE 상태
- 자연어 질문 처리
- 서버 DB 기반 관광 안내
- 네이버 지도 API 연동
- 실시간 버스 도착 정보 제공
- QR 인증 즉시 서버 반영

### OFFLINE 상태
- 로컬 DB 기반 관광 안내 유지
- 근처 관광지 / 사람들이 자주 선택한 장소 제공
- 도보 / 버스 여부 안내
- 버스는 **배차 간격 기반 범위 안내**
- 이벤트는 로컬 Outbox에 저장 후 추후 업로드

### 절대 끊기면 안 되는 정보
- 지금 근처에 무엇이 있는지
- 다음에 선택할 수 있는 행동
- 도보인지 버스를 타야 하는지
- 가장 가까운 정류장은 어디인지

---

## 5. 데이터베이스 설계

### 서버 DB (PostgreSQL)
- 원본 데이터 관리
- 관리자 수정/삭제
- 동기화 기준 데이터 제공

주요 테이블:
- kiosks
- places
- place_i18n
- place_images
- bus_stops / bus_routes / route_stops
- offline_timetables
- events
- dataset_versions
- users (Django Auth)

### 로컬 DB (SQLite)
- 서버 데이터 캐시
- 오프라인 안내 유지

추가 테이블:
- local_meta (동기화 버전)
- outbox_events (오프라인 이벤트 큐)

---

## 6. 사용자 인증 및 계정 관리 (Django)

### Django 기반 로그인 시스템
- Django Auth 기반 사용자 관리
- 회원가입 / 로그인 / 로그아웃 CRUD
- 세션 + 쿠키 기반 로그인 유지

### 로그인 목적
- QR 인증 사용자 식별
- 퀘스트 진행 상태 관리
- 개인 정보 최소화 (식별 목적만 사용)

---

## 7. QR 기반 인증 및 관광 흐름

### QR 접근 흐름
1. 사용자가 키오스크 또는 관광지에서 QR 스캔
2. Django 서버 웹 페이지로 이동
3. 로그인 상태 확인 (비로그인 시 로그인 유도)
4. 현재 위치/지점 인증 처리

### QR 인증 시 제공 정보
- “현재 A 지점을 인증했습니다”
- 다음 추천 지점(B, C 등)
- 전체 추천 관광 루트
- 근처 관광지 요약 정보

### QR 인증 활용
- 관광 흐름 시각화
- 방문 완료 지점 표시
- 퀘스트형 관광 동선 구성 (선택 기능)

---

## 8. 지도 및 이동 정보 제공

### 네이버 지도 API 연동
- 도보 경로 안내
- 버스 이동 경로 안내
- 정류장 위치 표시

### 실시간 버스 정보
- A 정류장 → N분 뒤 도착
- 전주시 제공 Open API 또는 공공 데이터 활용 예정
- API 미지원 시 오프라인 배차 간격 기반 대체 안내

> 실시간 정보는 **보조 정보**이며,  
> 오프라인에서도 기본 이동 판단이 가능하도록 설계됨

---

## 9. 데모 및 검증 도구

### Local DB Viewer (tes.py)
- 로컬 SQLite DB GUI 확인 도구
- 장소 / 이미지 / 버스 / 이벤트 시각화
- 설계 검증 및 발표 시연용

---

## 10. 프로젝트 정체성 요약

이 프로젝트는  
관광 정보를 “많이 보여주는 시스템”이 아니라,

**외국인 관광객이 지금 이 순간  
무엇을 해야 할지 판단하도록 돕는  
끊기지 않는 관광 안내 인프라**를 만드는 프로젝트다.

---

## 11. 향후 확장 방향

- 관리자 웹 페이지
- 관광 루트 추천 고도화
- QR 기반 퀘스트/게이미피케이션
- 다국어 확장
- 관광 동선 통계 분석

모든 기능은 기존 구조를 깨지 않고 확장 가능하도록 설계되었다.

---

## 12. 데이터베이스 상세 정보

### `kiosks`
- `kiosk_id`: 키오스크 고유 ID (예: KIOSK_001)
- `name`: 관리용 이름 (예: 한옥마을 입구 1)
- `lat`: 설치 좌표
- `lng`: 설치 좌표
- `radius_m`: 근처 추천 반경(m)
- `default_lang`: 기본 언어

### places
- place_id: 장소 고유 ID (서버 place_id 와 동일해야 동기화 가능)
- type: TOUR/FOOD/FACILITY
- category: 하위 카테고리 (museum/cafe/restroom...)
- lat: 장소 좌표
- lng: 장소 좌표
- tags_json: 태그(JSON 문자열). 예: ["popular","traditional"]
- is_vegan: (선택) 비건/채식 옵션 여부: 1/0/NULL(미확인)
- priority_score: 운영자 추천 가중치(높을수록 상단)
- cover_image_id: 대표(커버) 이미지 지정용: place_images.image_id (없으면 NULL)

### place_i18n
- place_id: 어떤 장소의 번역인지 (places.place_id)
- lang: 언어 코드(ko/en/ja/zh)
- name: 언어별 장소명(카드 제목)
- short_desc: 짧은 설명(카드 요약 1~2줄)
- address_text: 사용자에게 보여줄 주소 문자열
- hours_text: (선택) 운영시간 표시용 텍스트(정교한 영업중 판정은 서버에서)

### place_images
- image_id: 이미지 고유 ID (서버 image_id 와 동일)
- place_id: 어떤 장소의 이미지인지
- kind: PHOTO/THUMBNAIL/MENU/MAP/ETC
- url: 접근 URL
- storage_key: (옵션) 스토리지 내부 키
- mime: MIME 타입
- width: (옵션) 가로 픽셀
- height: (옵션) 세로 픽셀
- bytes_len: (옵션) 파일 크기(byte)
- is_primary: 대표 이미지 여부(1/0)
- sort_order: 관리자 정렬용

### bus_stops
- stop_id: 정류장 고유 ID (서버 stop_id 와 동일)
- stop_code: (옵션) 실시간 버스 API 조회용 코드
- lat: 정류장 좌표
- lng: 정류장 좌표

### bus_routes
- route_id: 노선 고유 ID (서버 route_id 와 동일)
- route_no: 사용자에게 보여줄 버스 번호(핵심)

### route_stops
- route_id: 어떤 노선인지
- stop_id: 어떤 정류장인지
- seq: 노선 내 정류장 순번

### offline_timetables
- route_id: 어떤 노선의 오프라인 기준 정보인지
- day_type: WEEKDAY/WEEKEND
- headway_min: 평균 배차 간격(분) → 오프라인 시간은 "범위"로 안내
- first_time: (옵션) 첫차 표기
- last_time: (옵션) 막차 표기

### local_meta
- key: 예: dataset_version
- value: 예: 12

### outbox_events
- outbox_id: 로컬 큐 row ID
- kiosk_id: 어떤 키오스크에서 발생했는지
- event_type: 이벤트 종류
- place_id: (옵션) 관련 장소
- lang: (옵션) 사용 언어
- payload_json: 추가 데이터(JSON 문자열)
- created_at: 생성 시각(ISO 문자열 권장)
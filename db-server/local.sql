-- =========================================
-- Jeonju Smart Tourist Kiosk (Local SQLite)
-- 목적: 오프라인에서도 "끊기지 않는 안내"를 위한 로컬 캐시 DB
-- 원칙: 로컬 DB는 서버(PostgreSQL) 원본의 "부분 복제본" + 오프라인 outbox 큐
-- =========================================

PRAGMA foreign_keys = ON;

-- =========================================
-- 0) 키오스크(기기) 정보
--  - 보통 1개 row만 저장 (현재 기기 자체)
-- =========================================
CREATE TABLE IF NOT EXISTS kiosks (
  kiosk_id      TEXT PRIMARY KEY,                 -- 키오스크 고유 ID (예: KIOSK_001)
  name          TEXT NOT NULL,                    -- 관리용 이름 (예: 한옥마을 입구 1)
  lat           REAL NOT NULL,                    -- 설치 좌표
  lng           REAL NOT NULL,                    -- 설치 좌표
  radius_m      INTEGER NOT NULL DEFAULT 600,     -- 근처 추천 반경(m)
  default_lang  TEXT NOT NULL DEFAULT 'en'        -- 기본 언어
);

-- =========================================
-- 1) 장소(관광/맛집/편의) 캐시
--  - 서버 places 의 핵심 컬럼만 캐시
-- =========================================
CREATE TABLE IF NOT EXISTS places (
  place_id       INTEGER PRIMARY KEY,             -- 장소 고유 ID (서버 place_id 와 동일해야 동기화 가능)
  type           TEXT NOT NULL,                   -- TOUR/FOOD/FACILITY
  category       TEXT NOT NULL,                   -- 하위 카테고리 (museum/cafe/restroom...)
  lat            REAL NOT NULL,                   -- 장소 좌표
  lng            REAL NOT NULL,                   -- 장소 좌표
  tags_json      TEXT NOT NULL DEFAULT '[]',      -- 태그(JSON 문자열). 예: ["popular","traditional"]
  -- 아래 2개는 범위 밖이면 추후 제거 가능 (TRUE/FALSE/NULL 개념을 로컬에서는 1/0/NULL로 표현)
  is_halal       INTEGER,                         -- (선택) 할랄 옵션 여부: 1/0/NULL(미확인)
  is_vegan       INTEGER,                         -- (선택) 비건/채식 옵션 여부: 1/0/NULL(미확인)
  priority_score INTEGER NOT NULL DEFAULT 0,      -- 운영자 추천 가중치(높을수록 상단)
  cover_image_id INTEGER                          -- 대표(커버) 이미지 지정용: place_images.image_id (없으면 NULL)
);

-- 장소 다국어 텍스트
CREATE TABLE IF NOT EXISTS place_i18n (
  place_id     INTEGER NOT NULL,                  -- 어떤 장소의 번역인지 (places.place_id)
  lang         TEXT NOT NULL,                     -- 언어 코드(ko/en/ja/zh)
  name         TEXT NOT NULL,                     -- 언어별 장소명(카드 제목)
  short_desc   TEXT NOT NULL DEFAULT '',          -- 짧은 설명(카드 요약 1~2줄)
  address_text TEXT NOT NULL DEFAULT '',          -- 사용자에게 보여줄 주소 문자열
  hours_text   TEXT NOT NULL DEFAULT '',          -- (선택) 운영시간 표시용 텍스트(정교한 영업중 판정은 서버에서)
  PRIMARY KEY (place_id, lang),
  FOREIGN KEY (place_id) REFERENCES places(place_id) ON DELETE CASCADE
);

-- =========================================
-- 1-2) 장소 이미지(캐시)
--  - 로컬에는 파일 자체를 저장하지 않고, "접근 URL/메타"만 캐시
--  - 오프라인에서는 이미지 표시를 생략하거나, 썸네일만 별도 캐시하는 방식으로 확장 가능
-- =========================================
CREATE TABLE IF NOT EXISTS place_images (
  image_id     INTEGER PRIMARY KEY,               -- 이미지 고유 ID (서버 image_id 와 동일)
  place_id     INTEGER NOT NULL,                  -- 어떤 장소의 이미지인지
  kind         TEXT NOT NULL DEFAULT 'PHOTO',     -- PHOTO/THUMBNAIL/MENU/MAP/ETC
  url          TEXT NOT NULL,                     -- 접근 URL
  storage_key  TEXT,                              -- (옵션) 스토리지 내부 키
  mime         TEXT NOT NULL DEFAULT 'image/jpeg',-- MIME 타입
  width        INTEGER,                           -- (옵션) 가로 픽셀
  height       INTEGER,                           -- (옵션) 세로 픽셀
  bytes_len    INTEGER,                           -- (옵션) 파일 크기(byte)
  is_primary   INTEGER NOT NULL DEFAULT 0,         -- 대표 이미지 여부(1/0)
  sort_order   INTEGER NOT NULL DEFAULT 0,         -- 관리자 정렬용
  FOREIGN KEY (place_id) REFERENCES places(place_id) ON DELETE CASCADE
);

-- 대표 이미지 검색/정렬 최적화
CREATE INDEX IF NOT EXISTS idx_place_images_place_sort
  ON place_images(place_id, is_primary DESC, sort_order ASC, image_id ASC);

-- =========================================
-- 1-3) 장소 메뉴(캐시)
-- =========================================
CREATE TABLE IF NOT EXISTS place_menus (
  menu_id     INTEGER PRIMARY KEY AUTOINCREMENT,  -- 메뉴 고유 ID (로컬 전용)
  place_id    INTEGER NOT NULL,                   -- 어떤 장소의 메뉴인지
  name        TEXT NOT NULL,                      -- 메뉴명
  description TEXT NOT NULL DEFAULT '',           -- 메뉴 설명
  price       TEXT NOT NULL DEFAULT '',           -- 가격 텍스트
  image_id    INTEGER,                            -- 메뉴 이미지 (place_images.image_id)
  sort_order  INTEGER NOT NULL DEFAULT 0,          -- 메뉴 정렬용
  FOREIGN KEY (place_id) REFERENCES places(place_id) ON DELETE CASCADE,
  FOREIGN KEY (image_id) REFERENCES place_images(image_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_place_menus_place_sort
  ON place_menus(place_id, sort_order ASC, menu_id ASC);

-- =========================================
-- 1-4) 음식점 상세 정보(캐시)
-- =========================================
CREATE TABLE IF NOT EXISTS place_food_info (
  place_id   INTEGER NOT NULL,                    -- 어떤 장소의 정보인지
  info_key   TEXT NOT NULL,                       -- 정보 키(treatmenu/opentimefood 등)
  info_value TEXT NOT NULL,                       -- 정보 값
  PRIMARY KEY (place_id, info_key),
  FOREIGN KEY (place_id) REFERENCES places(place_id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS bus_routes (
  route_id  INTEGER PRIMARY KEY,                  -- 노선 고유 ID (서버 route_id 와 동일)
  route_no  TEXT NOT NULL                         -- 사용자에게 보여줄 버스 번호(핵심)
);

-- 노선-정류장 구성(순서)
CREATE TABLE IF NOT EXISTS route_stops (
  route_id INTEGER NOT NULL,                      -- 어떤 노선인지
  stop_id  INTEGER NOT NULL,                      -- 어떤 정류장인지
  seq      INTEGER NOT NULL,                      -- 노선 내 정류장 순번
  PRIMARY KEY (route_id, seq),
  FOREIGN KEY (route_id) REFERENCES bus_routes(route_id) ON DELETE CASCADE,
  FOREIGN KEY (stop_id)  REFERENCES bus_stops(stop_id)  ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_route_stops_stop
  ON route_stops(stop_id);

-- 오프라인 배차 안내(범위 안내용)
CREATE TABLE IF NOT EXISTS offline_timetables (
  route_id    INTEGER NOT NULL,                   -- 어떤 노선의 오프라인 기준 정보인지
  day_type    TEXT NOT NULL,                      -- WEEKDAY/WEEKEND
  headway_min INTEGER NOT NULL,                   -- 평균 배차 간격(분) → 오프라인 시간은 "범위"로 안내
  first_time  TEXT,                               -- (옵션) 첫차 표기
  last_time   TEXT,                               -- (옵션) 막차 표기
  PRIMARY KEY (route_id, day_type),
  FOREIGN KEY (route_id) REFERENCES bus_routes(route_id) ON DELETE CASCADE
);

-- =========================================
-- 3) 로컬 메타(동기화 버전 등)
-- =========================================
CREATE TABLE IF NOT EXISTS local_meta (
  key   TEXT PRIMARY KEY,                         -- 예: dataset_version
  value TEXT NOT NULL                             -- 예: 12
);

-- =========================================
-- 4) 오프라인 outbox (업로드 대기 큐)
--  - 네트워크 끊겨도 이벤트/QR 인증 요청을 잃지 않기 위함
--  - 온라인 복구 시 서버 /events/batch 로 전송 후 삭제
-- =========================================
CREATE TABLE IF NOT EXISTS outbox_events (
  outbox_id     INTEGER PRIMARY KEY AUTOINCREMENT, -- 로컬 큐 row ID
  kiosk_id      TEXT NOT NULL,                     -- 어떤 키오스크에서 발생했는지
  event_type    TEXT NOT NULL,                     -- 이벤트 종류
  place_id      INTEGER,                           -- (옵션) 관련 장소
  lang          TEXT,                              -- (옵션) 사용 언어
  payload_json  TEXT NOT NULL DEFAULT '{}',        -- 추가 데이터(JSON 문자열)
  created_at    TEXT NOT NULL                      -- 생성 시각(ISO 문자열 권장)
);

CREATE INDEX IF NOT EXISTS idx_outbox_events_time
  ON outbox_events(created_at);

-- =========================================
-- (권장) 조회 성능을 위한 기본 인덱스
-- =========================================
CREATE INDEX IF NOT EXISTS idx_places_type_cat
  ON places(type, category);

CREATE INDEX IF NOT EXISTS idx_places_lat_lng
  ON places(lat, lng);

CREATE INDEX IF NOT EXISTS idx_bus_stops_lat_lng
  ON bus_stops(lat, lng);
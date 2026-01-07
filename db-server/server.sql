-- ================
-- 0) 키오스크 관리
-- ================
CREATE TABLE kiosks (
  kiosk_id        TEXT PRIMARY KEY, -- 주체 식별 key KIOSK_001
  name            TEXT NOT NULL, -- 키오스크 위치 이름 -> 한옥 마을 입구 1
  lat             DOUBLE PRECISION NOT NULL, -- 좌표
  lng             DOUBLE PRECISION NOT NULL, -- 좌표
  radius_m        INTEGER NOT NULL DEFAULT 600, -- 추천 반경(미터)
  default_lang    TEXT NOT NULL DEFAULT 'en', -- 언어선택 없을때 기본(영어)
  is_active       BOOLEAN NOT NULL DEFAULT TRUE, -- 운영 여부 현재 정상작동기기인가?
  last_heartbeat_at TIMESTAMPTZ  -- 마지막 생존 수신 시간(장애 감지/모니터링)
);

-- ================
-- 1) 장소(관광/맛집/편의)
-- ================
CREATE TABLE places (
  place_id        BIGSERIAL PRIMARY KEY, -- 장소 고유 ID / i18n / 로그 / 퀘스트에서 참조
  type            TEXT NOT NULL CHECK (type IN ('TOUR','FOOD','FACILITY')), -- 상위 분류 관광 / 식품 / 편의
  category        TEXT NOT NULL, -- 하위 카테고리 (박물관 , 카페 / 휴게소 / 트랜디)
  lat             DOUBLE PRECISION NOT NULL, -- 좌표
  lng             DOUBLE PRECISION NOT NULL, -- 좌표
  tags            JSONB NOT NULL DEFAULT '[]'::jsonb, -- 태그
  is_halal        BOOLEAN, -- (선택) 할랄 옵션 여부: TRUE/ FALSE/ NULL(미확인). 범위 밖이면 나중에 제거 가능
  is_vegan        BOOLEAN, -- (선택) 비건/채식 옵션 여부: TRUE/ FALSE/ NULL(미확인). 범위 밖이면 나중에 제거 가능
  cover_image_id  BIGINT, -- 대표(커버) 이미지 지정용: place_images.image_id 참조 (없으면 NULL)
  priority_score  INTEGER NOT NULL DEFAULT 0, -- 운영자가 추천 우선순위를 수동 조절하는 가중치(높을수록 상단)
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(), -- 마지막 수정 시각(동기화 기준)
  deleted_at      TIMESTAMPTZ -- 소프트 삭제(동기화 시 삭제 반영용). NULL이면 정상 데이터
);

CREATE TABLE place_i18n (
  place_id     BIGINT NOT NULL REFERENCES places(place_id) ON DELETE CASCADE, -- 어떤 장소의 번역인지 (places.place_id)
  lang         TEXT NOT NULL CHECK (lang IN ('ko','en','ja','zh')), -- 언어 코드
  name         TEXT NOT NULL, -- 언어별 장소명(카드 제목)
  short_desc   TEXT NOT NULL DEFAULT '', -- 짧은 설명(카드 요약 1~2줄)
  address_text TEXT NOT NULL DEFAULT '', -- 사용자에게 보여줄 주소 문자열(언어별 표기)
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(), -- 마지막 수정 시각(동기화 기준)
  deleted_at   TIMESTAMPTZ, -- 소프트 삭제(번역 제거 반영)
  PRIMARY KEY (place_id, lang)
);

-- ================
-- 1-2) 장소 이미지(관리자 페이지용)
--  - DB에는 "파일 자체"가 아니라 "메타데이터 + 저장 위치"만 저장
--  - 실제 파일은 S3/Cloud Storage/서버 디스크 등에 저장 (권장: Object Storage)
-- ================
CREATE TABLE place_images (
  image_id     BIGSERIAL PRIMARY KEY, -- 이미지 고유 ID (관리자에서 수정/삭제/대표지정 시 식별)
  place_id     BIGINT NOT NULL REFERENCES places(place_id) ON DELETE CASCADE, -- 어떤 장소의 이미지인지
  kind         TEXT NOT NULL DEFAULT 'PHOTO' CHECK (kind IN ('PHOTO','THUMBNAIL','MENU','MAP','ETC')), -- 이미지 유형(썸네일/메뉴/지도 등)
  url          TEXT NOT NULL, -- 접근 URL (CDN/스토리지 public URL)
  storage_key  TEXT, -- 스토리지 내부 키(옵션). 예: S3 key, 서버 디스크 경로
  mime         TEXT NOT NULL DEFAULT 'image/jpeg', -- MIME 타입
  width        INTEGER, -- (옵션) 가로 픽셀
  height       INTEGER, -- (옵션) 세로 픽셀
  bytes_len    INTEGER, -- (옵션) 파일 크기(byte)
  is_primary   BOOLEAN NOT NULL DEFAULT FALSE, -- 대표 이미지 여부(장소당 1개만 허용)
  sort_order   INTEGER NOT NULL DEFAULT 0, -- 관리자 정렬용(오름차순)
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(), -- 등록 시각
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(), -- 수정 시각
  deleted_at   TIMESTAMPTZ -- 소프트 삭제
);

-- 한 장소당 대표 이미지는 1개만 허용(소프트삭제 제외)
CREATE UNIQUE INDEX uq_place_primary_image
  ON place_images(place_id)
  WHERE is_primary = TRUE AND deleted_at IS NULL;

CREATE INDEX idx_place_images_place_sort
  ON place_images(place_id, is_primary DESC, sort_order ASC, image_id ASC);

-- places.cover_image_id 가 place_images.image_id 를 참조 (커버 지정)
ALTER TABLE places
  ADD CONSTRAINT fk_places_cover_image
  FOREIGN KEY (cover_image_id)
  REFERENCES place_images(image_id)
  ON DELETE SET NULL;

-- ================
-- 2) 버스 정류장/노선(정적)
-- ================
CREATE TABLE bus_stops (
  stop_id     BIGSERIAL PRIMARY KEY, -- 정류장 고유 ID
  stop_code   TEXT, -- (옵션) 실시간 버스 API 조회용 코드
  lat         DOUBLE PRECISION NOT NULL, -- 정류장 좌표
  lng         DOUBLE PRECISION NOT NULL, -- 정류장 좌표
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(), -- 마지막 수정 시각(동기화 기준)
  deleted_at  TIMESTAMPTZ, -- 소프트 삭제
  UNIQUE (stop_code)
);

CREATE TABLE bus_routes (
  route_id     BIGSERIAL PRIMARY KEY, -- 노선 고유 ID
  route_no     TEXT NOT NULL UNIQUE, -- 사용자에게 보여줄 버스 번호(핵심)
  provider_key TEXT, -- (옵션) 외부 API에서 요구하는 노선 식별키
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(), -- 마지막 수정 시각(동기화 기준)
  deleted_at   TIMESTAMPTZ -- 소프트 삭제
);

CREATE TABLE route_stops (
  route_id  BIGINT NOT NULL REFERENCES bus_routes(route_id) ON DELETE CASCADE, -- 어떤 노선인지
  stop_id   BIGINT NOT NULL REFERENCES bus_stops(stop_id) ON DELETE CASCADE, -- 어떤 정류장인지
  seq       INTEGER NOT NULL, -- 노선 내 정류장 순번(진행 방향/정차 순서)
  PRIMARY KEY (route_id, seq)
);

-- (선택) 오프라인 배차/운행 범위 안내용
CREATE TABLE offline_timetables (
  route_id    BIGINT NOT NULL REFERENCES bus_routes(route_id) ON DELETE CASCADE, -- 어떤 노선의 오프라인 기준 정보인지
  day_type    TEXT NOT NULL CHECK (day_type IN ('WEEKDAY','WEEKEND')), -- 요일 타입(평일/주말)
  headway_min INTEGER NOT NULL CHECK (headway_min > 0), -- 평균 배차 간격(분) → 오프라인 시간은 "범위"로 안내
  first_time  TEXT, -- (옵션) 첫차 표기(예: 05:30)
  last_time   TEXT, -- (옵션) 막차 표기(예: 22:40)
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(), -- 마지막 수정 시각(동기화 기준)
  deleted_at  TIMESTAMPTZ, -- 소프트 삭제
  PRIMARY KEY (route_id, day_type)
);

-- ================
-- 3) 동기화 버전(간단 버전)
-- ================
CREATE TABLE dataset_versions (
  dataset_name TEXT PRIMARY KEY, -- 데이터 묶음 이름(예: 'core')
  version      BIGINT NOT NULL DEFAULT 1, -- 로컬 동기화 버전(증가)
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now() -- 버전 갱신 시각
);

-- ================
-- 4) 이벤트(중앙 집계)
-- ================
CREATE TABLE events (
  event_id    BIGSERIAL PRIMARY KEY, -- 이벤트 로그 고유 ID
  kiosk_id    TEXT NOT NULL REFERENCES kiosks(kiosk_id), -- 어떤 키오스크에서 발생했는지
  place_id    BIGINT REFERENCES places(place_id), -- (옵션) 어떤 장소와 관련된 이벤트인지
  event_type  TEXT NOT NULL, -- 이벤트 종류: VIEW/SELECT/ROUTE_SHOW/QUEST_START/QR_OPEN ...
  lang        TEXT, -- (옵션) 사용 언어
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now() -- 발생 시각
);

-- 성능 기본 인덱스
CREATE INDEX idx_places_type_cat ON places(type, category);
CREATE INDEX idx_places_updated ON places(updated_at);
CREATE INDEX idx_events_kiosk_time ON events(kiosk_id, created_at DESC);
# 전주버스 API 추출 메모

목적
- 전주버스 API에서 노선 ID, 정류장 ID를 수집한다.
- "전주역" 기준으로 가까운 정류장을 좌표로 추출한다.
- 현재 키오스크 루트 구간에 매칭되는 노선 ID 후보를 만든다.
- 전주역 → 관광지별 추천 노선 목록을 생성한다.
- 실시간 운행 버스가 있는 노선을 찾아 테스트한다.

파일
- fetch_bus_mappings.py: 전주버스 API를 호출해 bus_mapping.json을 생성한다.
- bus_mapping.json: "전주역" 정류장 후보/거리와 구간별 노선 ID 후보 목록을 담는다.
- test_live_time.py: 노선 ID 기준으로 버스 위치를 조회해 다음 도착 추정 시간을 출력한다.
- build_route_suggestions.py: 전주역 → 관광지별 추천 노선 목록(route_suggestions.json) 생성.
- find_active_routes.py: 실시간 운행 중인 노선을 찾아 active_routes.json 생성.

동작 흐름
1) 노선 목록 API 호출 → brtId/brtClass 수집.
2) 노선 정보 API로 brtStdid를 보강.
3) 노선별 경유 정류장 목록 API 호출 → stopKname/stopId 수집.
4) 승강장 검색 API 호출 → 전주역 및 목적지 정류장명 후보 수집.
5) db-server/kiosk_data.json의 TOUR 장소 기준으로 5개 루트를 만든 뒤
   각 구간의 stopKname 후보와 경유 정류장을 매칭해 brtStdid 후보를 생성.
6) 전주역 → 관광지별 추천 노선 목록을 생성.
7) 실시간 운행 중인 노선을 찾아 테스트한다.

실행 방법
- .env에 JEONJU_BUS_SERVICE_KEY가 있어야 함.
- 필요 시 JEONJU_MAX_ROUTES로 호출량 제한(기본 200).
- 필요 시 JEONJU_MAX_MATCHES로 구간별 후보 수 제한(기본 3).
- 필요 시 JEONJU_MIN_MATCHES로 최소 매칭 구간 수 경고 기준 설정(기본 10).
- 필요 시 JEONJU_API_SLEEP로 호출 간 대기 시간 설정(기본 0.15초).

예시 (PowerShell)
```
$env:JEONJU_MAX_ROUTES = "120"
$env:JEONJU_MAX_MATCHES = "3"
$env:JEONJU_MIN_MATCHES = "10"
$env:JEONJU_API_SLEEP = "0.2"
python bus_api_work\fetch_bus_mappings.py
python bus_api_work\test_live_time.py
python bus_api_work\build_route_suggestions.py
python bus_api_work\find_active_routes.py
```

출력
- bus_api_work\bus_mapping.json
  - origin_kiosk: 전주역 좌표 정보
  - nearest_stops: 전주역 기준 가까운 정류장 목록(거리 km 포함)
  - matched_stops: "전주역" 정류장 stopId 목록
  - routes: 현재 생성된 루트 목록
  - segment_routes: 구간별 노선 ID 후보 리스트
  - api_status: API 상태 코드/메시지 및 호출 URL(키는 마스킹됨)
- bus_api_work\route_suggestions.json
  - origin: 전주역
  - suggestions: 관광지별 추천 노선 목록
- bus_api_work\active_routes.json
  - 실시간 운행 중인 노선 ID 목록

메모
- ServiceKey만 사용하도록 설정되어 있다.
- 일일 트래픽 제한이 있으니 JEONJU_MAX_ROUTES를 조절하는 게 안전하다.
- ETA(도착예정시간)는 별도의 실시간 도착정보 API가 필요하다.
- api_status에 `SERVICE KEY IS NOT REGISTERED ERROR`가 뜨면
  해당 서비스에 대한 활용신청/승인이 필요하다.
- api_status에 `NO OPENAPI SERVICE ERROR`가 뜨면
  엔드포인트 경로가 바뀐 경우가 있으니 문서의 예시 URL을 확인해야 한다.

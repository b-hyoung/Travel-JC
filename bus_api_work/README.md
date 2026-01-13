# 전주버스 API 추출 메모

목적
- 전주버스 API에서 노선 ID, 정류장 ID를 수집한다.
- "전주역" 기준으로 가까운 정류장을 좌표로 추출한다.
- 현재 키오스크 루트 구간에 매칭되는 노선 ID 후보를 만든다.

파일
- fetch_bus_mappings.py: 전주버스 API를 호출해 bus_mapping.json을 생성한다.
- bus_mapping.json: "전주역" 정류장 후보/거리와 구간별 노선 ID 후보 목록을 담는다.
- fallback_bus_data.json: API 장애 시 사용되는 임시 데모 데이터.
- manual_routes.json: 네이버 기준 루트를 임시로 하드코딩한 목록.

동작 흐름
1) 노선 목록 API 호출 → brtStdid(노선 ID) 수집.
2) 노선별 경유 정류장 목록 API 호출 → stopKname/stopId 수집.
3) "전주역" 포함 정류장만 필터.
4) 승강장 검색 API 호출 → stopX/stopY 좌표 기반으로 전주역 인접 정류장 추출.
5) db-server/kiosk_data.json의 루트 구간(start/end)을 기준으로
   해당 노선을 통과하는 brtStdid 후보를 생성.
6) API 실패 시 fallback_bus_data.json 데이터로 대체.

실행 방법
- .env에 JEONJU_BUS_SERVICE_KEY가 있어야 함.
- 필요 시 JEONJU_MAX_ROUTES로 호출량 제한(기본 200).

예시 (PowerShell)
```
$env:JEONJU_MAX_ROUTES = "120"
python bus_api_work\fetch_bus_mappings.py
```

출력
- bus_api_work\bus_mapping.json
  - origin_kiosk: 전주역 좌표 정보
  - nearest_stops: 전주역 기준 가까운 정류장 목록(거리 km 포함)
  - matched_stops: "전주역" 정류장 stopId 목록
  - segment_routes: 구간별 노선 ID 후보 리스트
  - api_status: API 상태 코드/메시지 및 호출 URL(키는 마스킹됨)
  - api_mode: live 또는 fallback

메모
- ServiceKey만 사용하도록 설정되어 있다.
- 일일 트래픽 제한이 있으니 JEONJU_MAX_ROUTES를 조절하는 게 안전하다.
- ETA(도착예정시간)는 별도의 실시간 도착정보 API가 필요하다.
- api_status에 `SERVICE KEY IS NOT REGISTERED ERROR`가 뜨면
  해당 서비스에 대한 활용신청/승인이 필요하다.
- api_status에 `NO OPENAPI SERVICE ERROR`가 뜨면
  엔드포인트 경로가 바뀐 경우가 있으니 문서의 예시 URL을 확인해야 한다.

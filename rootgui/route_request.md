# 버스/노선 매칭용 요청 템플릿

아래 JSON 형식으로만 주세요. **한 노선(버스번호)당 1개 객체**가 기본입니다.

- `bus_no`: 화면에 표시할 버스번호 (예: "119", "3-1")
- `brtId`: API 조회용 노선번호 (예: "119", "3")
- `brtStdid`: API 노선ID (버스운행 식별자)
- `direction_label`: 방향 설명 (예: "전주역 → 한옥마을")
- `start_stop_name`: 출발 정류장명 (API 응답 기준)
- `end_stop_name`: 도착 정류장명 (API 응답 기준)

## JSON 예시

```json
[
  {
    "bus_no": "119",
    "brtId": "119",
    "brtStdid": "305001618",
    "direction_label": "전주역 → 전동성당·한옥마을",
    "start_stop_name": "동부대로전주역",
    "end_stop_name": "전동성당.한옥마을"
  },
  {
    "bus_no": "3-1",
    "brtId": "3",
    "brtStdid": "305001271",
    "direction_label": "전동성당 → 아중호수",
    "start_stop_name": "전동성당.한옥마을",
    "end_stop_name": "아중호수.인교마을입구.아중요양병원"
  }
]
```

이 JSON을 주면 내가 `bus_schedule.json`과 UI에 바로 연결해줄게.

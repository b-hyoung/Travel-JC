
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import ORJSONResponse

# OpenAI 연동 관련 모듈 (테스트를 위해 주석 처리)
# import os
# import openai
# import json as json_parser # json_parser 대신 그냥 json 사용

# FastAPI 앱 생성
app = FastAPI(default_response_class=ORJSONResponse)

# 시작 시 JSON 데이터 로드
DB = {}
try:
    with open("db-server/test.json", "r", encoding="utf-8") as f:
        DB = json.load(f)
except FileNotFoundError:
    print("Warning: db-server/test.json not found. API will return empty data.")
except json.JSONDecodeError:
    print("Warning: Could not decode db-server/test.json. API will return empty data.")


@app.get("/")
def read_root():
    """
    API 서버가 살아있는지 확인하는 간단한 엔드포인트입니다.
    """
    return {"message": "전주 관광 키오스크 Mock API 서버입니다. /docs 로 접속하여 개선된 API 문서를 확인하세요."}


@app.get("/api/v1/locations")
async def get_locations(lang: str = 'en'):
    """
    탐색의 기준이 될 수 있는 모든 주요 거점(키오스크 등)의 목록을 반환합니다.
    요청된 언어(lang)에 맞는 이름을 제공합니다.
    """
    if not DB:
        raise HTTPException(status_code=500, detail="서버 데이터를 로드하지 못했습니다.")

    locations_with_i18n = []
    kiosk_i18n_map = {}

    # kiosk_i18n 데이터를 맵으로 구성 (kiosk_id -> lang -> name)
    for i18n_item in DB.get("kiosk_i18n", []):
        k_id = i18n_item["kiosk_id"]
        if k_id not in kiosk_i18n_map:
            kiosk_i18n_map[k_id] = {}
        kiosk_i18n_map[k_id][i18n_item["lang"]] = i18n_item["name"]

    for kiosk_data in DB.get("kiosk", []):
        kiosk_id = kiosk_data["kiosk_id"]
        
        # 기본 키오스크 데이터 복사
        location_info = kiosk_data.copy()
        
        # 요청된 언어의 이름을 찾고, 없으면 기본 언어 또는 ID로 대체
        translated_name = kiosk_i18n_map.get(kiosk_id, {}).get(lang)
        if not translated_name: # 요청 언어로 된 이름이 없으면 기본 언어 이름 찾기
            default_lang = location_info.get("default_lang", "en")
            translated_name = kiosk_i18n_map.get(kiosk_id, {}).get(default_lang, kiosk_id) # 없으면 ID
            
        location_info["name"] = translated_name
        
        locations_with_i18n.append(location_info)
        
    return locations_with_i18n


@app.get("/api/v1/places/search")
async def search_places_by_location(lat: float, lng: float, lang: str = 'en', radius_m: int = 1000):
    """
    지정된 위도(lat), 경도(lng)를 중심으로 주변 장소를 검색하여 반환합니다.
    
    - **lat**: 검색 중심 위도
    - **lng**: 검색 중심 경도
    - **lang**: 반환될 언어
    - **radius_m**: 검색 반경 (미터)
    """
    if not DB:
        raise HTTPException(status_code=500, detail="서버 데이터를 로드하지 못했습니다.")

    # (Mock 구현)
    # 실제 구현 시에는 lat, lng, radius_m를 사용하여 DB에서 해당 범위 내의 장소를 쿼리해야 합니다.
    # 여기서는 데모를 위해 항상 test.json의 모든 장소를 가공하여 반환합니다.
    
    i18n_map = {}
    for item in DB.get('place_i18n', []):
        place_id = item['place_id']
        if place_id not in i18n_map:
            i18n_map[place_id] = {}
        i18n_map[place_id][item['lang']] = item

    processed_places = []
    for place in DB.get('places', []):
        place_id = place['place_id']
        
        new_place_data = place.copy()
        lang_data = i18n_map.get(place_id, {}).get(lang, {})
        new_place_data.update(lang_data)
        processed_places.append(new_place_data)

    return {
        "searched_places": processed_places,
        "bus_stops": DB.get("bus_stops", [])
    }


@app.post("/ai/ask")
async def ask_ai(request: dict):
    """
    사용자의 자연어 질문을 받아 의도를 분석하고 적절한 답변을 반환합니다.
    (테스트를 위해 실제 OpenAI 호출을 Mocking한 버전)
    """
    # 실제 OpenAI 연동 시 필요:
    # api_key = os.getenv("OPENAI_API_KEY")
    # if not api_key:
    #     raise HTTPException(status_code=500, detail="OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
    # openai.api_key = api_key

    query = request.get("query", "").lower()
    lang = request.get("lang", "en")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required.")

    # --- 1. AI 1차 분석: 의도 및 개체 파악 (Mocking) ---
    intent = "unknown"
    entities = {}

    # Mocking: lang 값에 따라 해당 언어의 장소 이름을 검색 및 의도 파악
    if "길안내" in query or "어떻게 가" in query or "가고 싶어" in query or "how to get" in query:
        intent = "route_guidance"
        for place in DB.get("place_i18n", []):
            if place["lang"] == lang and place["name"].lower() in query:
                entities["place_name"] = place["name"]
                break
    elif "추천" in query or "알려줘" in query or "recommend" in query:
        intent = "general_recommendation"
        if "맛집" in query or "food" in query or "restaurant" in query:
            entities["category"] = "FOOD"

    # --- 2. 분석된 의도에 따라 기능 실행 ---
    if intent == "route_guidance":
        if "place_name" not in entities:
            return {"answer": "어디로 가는 길을 알려드릴까요? 목적지를 말씀해주세요." if lang == "ko" else "Where do you want to go? Please tell me the destination."}
        
        place_name = entities["place_name"]
        
        place_info = None
        for place in DB.get("place_i18n", []):
            if place["lang"] == lang and place["name"].lower() == place_name.lower(): # 정확한 일치로 변경
                for p_detail in DB.get("places", []):
                    if p_detail["place_id"] == place["place_id"]:
                        place_info = {**p_detail, **place}
                        break
                break
        
        if not place_info:
            return {"answer": f"'{place_name}'이라는 장소를 찾을 수 없어요." if lang == "ko" else f"Sorry, I couldn't find a place called '{place_name}'."}

        message = f"'{place_info['name']}'까지의 길안내를 시작합니다. (Mock 데이터)" if lang == "ko" else f"Starting route guidance to '{place_info['name']}'. (Mock data)"
        return {
            "type": "guidance_info",
            "message": message,
            "destination": place_info
        }

    elif intent == "general_recommendation":
        # Mocking: 2차 AI 호출 (DB 검색 결과를 자연스러운 문장으로 요약)
        if entities.get("category") == "FOOD":
             return {"answer": "전주에는 맛있는 비빔밥과 칼국수 맛집이 많아요! '전주비빔밥집(예시)'을 추천해 드려요." if lang == "ko" else "Jeonju has many famous Bibimbap and Kalguksu restaurants! I recommend 'Jeonju Bibimbap (Sample)'."}
        else:
            return {"answer": "전주에는 한옥마을과 경기전 등 아름다운 곳이 많답니다. 어디부터 둘러보시겠어요?" if lang == "ko" else "Jeonju has many beautiful places like the Hanok Village and Gyeonggijeon Shrine. Where would you like to start?"}
    
    else: # intent == "unknown"
        return {"answer": "죄송해요, 질문을 잘 이해하지 못했어요. '경기전 가는 법 알려줘' 또는 '맛집 추천해줘' 와 같이 질문해 주시겠어요?" if lang == "ko" else "I'm sorry, I didn't quite understand your question. Could you ask something like 'How to get to Gyeonggijeon Shrine' or 'Recommend a restaurant'?"}


# 이 파일이 직접 실행될 때 uvicorn 서버를 구동시키려면 아래 코드를 추가할 수 있습니다.
# (터미널에서 'uvicorn mock_api:app --reload'를 실행하는 것과 동일)
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)
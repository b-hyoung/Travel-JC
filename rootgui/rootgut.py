# -*- coding: utf-8 -*-
import json
import math
import os
import re
import sys
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontDatabase, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

try:
    from gui.helpers import _place_lang_code
except Exception:  # pragma: no cover - fallback for standalone runs
    def _place_lang_code(_lang: str) -> str:
        return "en"

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
KIOSK_DATA_FILE = PROJECT_DIR / "db-server" / "kiosk_data.json"
BUS_MAPPING_FILE = PROJECT_DIR / "bus_api_work" / "bus_mapping.json"
MANUAL_BUS_ROUTES_FILE = PROJECT_DIR / "bus_api_work" / "manual_bus_routes.json"
ROOTGUI_DIR = APP_DIR
TIMETABLE_FILE = ROOTGUI_DIR / "bus_timetable_eta.json"
BUS_SCHEDULE_FILE = ROOTGUI_DIR / "bus_schedule.json"
RESOLVED_ROUTES_FILE = ROOTGUI_DIR / "jjtour_routes_resolved.json"
ROUTES_FILE = ROOTGUI_DIR / "routes.json"
KMA_ULTRA_FCST_URL = (
    "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst"
)

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv(PROJECT_DIR / ".env")

ORIGIN_NAME_OVERRIDE = {"전주역": "동부대로전주역"}
MANUAL_NAME_ALIASES = {
    "동부대로전주역": "전주역",
    "전주 한옥마을": "전주한옥마을",
}

BUS_SPEED_KMPH = 18.0
WALK_SPEED_KMPH = 4.2
TAXI_SPEED_KMPH = 25.0
WALK_SENTINEL = "WALK"

ROUTE_I18N = {
    "en": {
        "list_title": "Recommended routes from Jeonju Station",
        "list_subtitle": "Tap a card to see details on the right.",
        "chip_weather_rainy": "Rainy day",
        "chip_weather_clear": "Clear day",
        "chip_reason_rainy": "Indoor/market focus",
        "chip_reason_clear": "Popular & walk-friendly",
        "chip_count": "Today's picks: {count}",
        "recommend_badge": "Today's pick",
        "recommend_default": "Today's recommended route",
        "reason_rainy_indoor": "Rainy day: indoor/market route",
        "reason_rainy_short": "Rainy day: shorter route",
        "reason_popular": "Popular attractions route",
        "reason_walk": "Great for walking",
        "route_desc": "Route covering {stops}.",
        "detail_total": "Total time & cost",
        "bus_number": "Bus No.",
        "headway": "Headway",
        "note": "Note",
        "eta_next": "Next in",
        "eta_times": "Next buses",
        "bus_info_pending": "Info pending",
        "walk_segment": "Walk segment",
    },
    "ko": {
        "list_title": "전주역 출발 인기 관광 루트",
        "list_subtitle": "카드를 누르면 오른쪽에 상세 정보가 표시됩니다.",
        "chip_weather_rainy": "비 오는 날",
        "chip_weather_clear": "맑은 날",
        "chip_reason_rainy": "실내/시장 중심 추천",
        "chip_reason_clear": "인기/도보 기준 추천",
        "chip_count": "오늘의 추천 {count}개",
        "recommend_badge": "오늘의 추천",
        "recommend_default": "오늘 추천 코스",
        "reason_rainy_indoor": "비 오는 날 실내/시장 중심 코스",
        "reason_rainy_short": "비 오는 날 동선이 짧은 코스",
        "reason_popular": "인기 관광지 중심 코스",
        "reason_walk": "걷기 동선이 좋은 코스",
        "route_desc": "{stops} 등을 둘러보는 코스입니다.",
        "detail_total": "전체 예상 비용 및 시간",
        "bus_number": "번호",
        "headway": "배차",
        "note": "안내",
        "eta_next": "다음 버스",
        "eta_times": "다음 버스들",
        "bus_info_pending": "정보 준비 중",
        "walk_segment": "도보 이동 구간",
    },
    "ja": {
        "list_title": "全州駅発 人気観光ルート",
        "list_subtitle": "カードを押すと右側に詳細が表示されます。",
        "chip_weather_rainy": "雨の日",
        "chip_weather_clear": "晴れの日",
        "chip_reason_rainy": "屋内/市場中心",
        "chip_reason_clear": "人気/徒歩向き",
        "chip_count": "今日のおすすめ {count}件",
        "recommend_badge": "今日のおすすめ",
        "recommend_default": "今日のおすすめコース",
        "reason_rainy_indoor": "雨の日：屋内/市場中心コース",
        "reason_rainy_short": "雨の日：短い動線のコース",
        "reason_popular": "人気スポット中心コース",
        "reason_walk": "歩きやすいコース",
        "route_desc": "{stops} を巡るコースです。",
        "detail_total": "所要時間と費用合計",
        "bus_number": "番号",
        "headway": "運行間隔",
        "note": "案内",
        "eta_next": "次のバス",
        "eta_times": "次のバス一覧",
        "bus_info_pending": "情報準備中",
        "walk_segment": "徒歩区間",
    },
    "zh-CN": {
        "list_title": "全州站出发热门路线",
        "list_subtitle": "点击卡片，右侧显示详情。",
        "chip_weather_rainy": "雨天",
        "chip_weather_clear": "晴天",
        "chip_reason_rainy": "室内/市场优先",
        "chip_reason_clear": "热门/适合步行",
        "chip_count": "今日推荐 {count} 个",
        "recommend_badge": "今日推荐",
        "recommend_default": "今日推荐路线",
        "reason_rainy_indoor": "雨天：室内/市场路线",
        "reason_rainy_short": "雨天：动线较短路线",
        "reason_popular": "热门景点路线",
        "reason_walk": "适合步行路线",
        "route_desc": "游览 {stops} 的路线。",
        "detail_total": "总时间与费用",
        "bus_number": "线路",
        "headway": "发车间隔",
        "note": "提示",
        "eta_next": "下一班",
        "eta_times": "下一班列表",
        "bus_info_pending": "信息准备中",
        "walk_segment": "步行路段",
    },
    "zh-TW": {
        "list_title": "全州站出發熱門路線",
        "list_subtitle": "點選卡片，右側顯示詳細資訊。",
        "chip_weather_rainy": "雨天",
        "chip_weather_clear": "晴天",
        "chip_reason_rainy": "室內/市場為主",
        "chip_reason_clear": "熱門/步行友善",
        "chip_count": "今日推薦 {count} 個",
        "recommend_badge": "今日推薦",
        "recommend_default": "今日推薦路線",
        "reason_rainy_indoor": "雨天：室內/市場路線",
        "reason_rainy_short": "雨天：動線較短路線",
        "reason_popular": "熱門景點路線",
        "reason_walk": "適合步行路線",
        "route_desc": "巡遊 {stops} 的路線。",
        "detail_total": "總時間與費用",
        "bus_number": "路線",
        "headway": "班距",
        "note": "提示",
        "eta_next": "下一班",
        "eta_times": "下一班列表",
        "bus_info_pending": "資訊準備中",
        "walk_segment": "步行區段",
    },
    "de": {
        "list_title": "Beliebte Routen ab Bahnhof Jeonju",
        "list_subtitle": "Tippen Sie auf eine Karte für Details rechts.",
        "chip_weather_rainy": "Regentag",
        "chip_weather_clear": "Klarer Tag",
        "chip_reason_rainy": "Innen/Markt im Fokus",
        "chip_reason_clear": "Beliebt & gut zu Fuß",
        "chip_count": "Heutige Empfehlungen: {count}",
        "recommend_badge": "Heute empfohlen",
        "recommend_default": "Heutige Empfehlung",
        "reason_rainy_indoor": "Regentag: Innen/Markt-Route",
        "reason_rainy_short": "Regentag: kürzere Route",
        "reason_popular": "Beliebte Sehenswürdigkeiten",
        "reason_walk": "Gut zu Fuß begehbar",
        "route_desc": "Route über {stops}.",
        "detail_total": "Gesamtzeit & Kosten",
        "bus_number": "Linie",
        "headway": "Takt",
        "note": "Hinweis",
        "eta_next": "Nächster in",
        "eta_times": "Nächste Busse",
        "bus_info_pending": "Info folgt",
        "walk_segment": "Fußweg",
    },
    "nl": {
        "list_title": "Populaire routes vanaf Jeonju Station",
        "list_subtitle": "Tik op een kaart voor details rechts.",
        "chip_weather_rainy": "Regenachtig",
        "chip_weather_clear": "Helder",
        "chip_reason_rainy": "Binnen/markt focus",
        "chip_reason_clear": "Populair & wandelvriendelijk",
        "chip_count": "Aanraders van vandaag: {count}",
        "recommend_badge": "Vandaag aanbevolen",
        "recommend_default": "Aanrader van vandaag",
        "reason_rainy_indoor": "Regen: binnen/markt-route",
        "reason_rainy_short": "Regen: kortere route",
        "reason_popular": "Populaire bezienswaardigheden",
        "reason_walk": "Goed om te wandelen",
        "route_desc": "Route langs {stops}.",
        "detail_total": "Totale tijd & kosten",
        "bus_number": "Lijn",
        "headway": "Interval",
        "note": "Opmerking",
        "eta_next": "Volgende in",
        "eta_times": "Volgende bussen",
        "bus_info_pending": "Info volgt",
        "walk_segment": "Loopstuk",
    },
    "sv": {
        "list_title": "Populära rutter från Jeonju Station",
        "list_subtitle": "Tryck på ett kort för detaljer till höger.",
        "chip_weather_rainy": "Regnig dag",
        "chip_weather_clear": "Klar dag",
        "chip_reason_rainy": "Inomhus/marknad i fokus",
        "chip_reason_clear": "Populär & promenadvänlig",
        "chip_count": "Dagens tips: {count}",
        "recommend_badge": "Dagens tips",
        "recommend_default": "Dagens rekommendation",
        "reason_rainy_indoor": "Regn: inomhus/marknadsrutt",
        "reason_rainy_short": "Regn: kortare rutt",
        "reason_popular": "Populära sevärdheter",
        "reason_walk": "Bra för promenad",
        "route_desc": "Rutt som täcker {stops}.",
        "detail_total": "Total tid & kostnad",
        "bus_number": "Linje",
        "headway": "Turtäthet",
        "note": "Notis",
        "eta_next": "Nästa om",
        "eta_times": "Nästa bussar",
        "bus_info_pending": "Info saknas",
        "walk_segment": "Gåsträcka",
    },
    "fr": {
        "list_title": "Itinéraires populaires depuis la gare de Jeonju",
        "list_subtitle": "Touchez une carte pour voir les détails à droite.",
        "chip_weather_rainy": "Jour de pluie",
        "chip_weather_clear": "Temps clair",
        "chip_reason_rainy": "Intérieur/marché en focus",
        "chip_reason_clear": "Populaire & marche facile",
        "chip_count": "Recommandations du jour : {count}",
        "recommend_badge": "Recommandé aujourd'hui",
        "recommend_default": "Recommandation du jour",
        "reason_rainy_indoor": "Pluie : itinéraire intérieur/marché",
        "reason_rainy_short": "Pluie : itinéraire plus court",
        "reason_popular": "Itinéraire des lieux populaires",
        "reason_walk": "Idéal pour marcher",
        "route_desc": "Itinéraire passant par {stops}.",
        "detail_total": "Temps & coût totaux",
        "bus_number": "Ligne",
        "headway": "Fréquence",
        "note": "Note",
        "eta_next": "Prochain dans",
        "eta_times": "Prochains bus",
        "bus_info_pending": "Info à venir",
        "walk_segment": "Segment à pied",
    },
    "it": {
        "list_title": "Percorsi popolari dalla stazione di Jeonju",
        "list_subtitle": "Tocca una scheda per i dettagli a destra.",
        "chip_weather_rainy": "Giorno di pioggia",
        "chip_weather_clear": "Giorno sereno",
        "chip_reason_rainy": "Focus indoor/mercato",
        "chip_reason_clear": "Popolare & a piedi",
        "chip_count": "Consigli di oggi: {count}",
        "recommend_badge": "Consigliato oggi",
        "recommend_default": "Consiglio del giorno",
        "reason_rainy_indoor": "Pioggia: percorso indoor/mercato",
        "reason_rainy_short": "Pioggia: percorso più breve",
        "reason_popular": "Percorso dei luoghi popolari",
        "reason_walk": "Ottimo per camminare",
        "route_desc": "Percorso che include {stops}.",
        "detail_total": "Tempo e costo totali",
        "bus_number": "Linea",
        "headway": "Frequenza",
        "note": "Nota",
        "eta_next": "Prossimo tra",
        "eta_times": "Prossimi bus",
        "bus_info_pending": "Info in arrivo",
        "walk_segment": "Tratto a piedi",
    },
    "es": {
        "list_title": "Rutas populares desde la estación de Jeonju",
        "list_subtitle": "Toca una tarjeta para ver detalles a la derecha.",
        "chip_weather_rainy": "Día lluvioso",
        "chip_weather_clear": "Día despejado",
        "chip_reason_rainy": "Enfasis interior/mercado",
        "chip_reason_clear": "Popular y caminable",
        "chip_count": "Recomendadas hoy: {count}",
        "recommend_badge": "Recomendado hoy",
        "recommend_default": "Ruta recomendada de hoy",
        "reason_rainy_indoor": "Lluvia: ruta interior/mercado",
        "reason_rainy_short": "Lluvia: ruta más corta",
        "reason_popular": "Ruta de lugares populares",
        "reason_walk": "Ideal para caminar",
        "route_desc": "Ruta que recorre {stops}.",
        "detail_total": "Tiempo y costo total",
        "bus_number": "Línea",
        "headway": "Frecuencia",
        "note": "Nota",
        "eta_next": "Próximo en",
        "eta_times": "Próximos buses",
        "bus_info_pending": "Info pendiente",
        "walk_segment": "Tramo a pie",
    },
    "pt": {
        "list_title": "Rotas populares a partir da estação de Jeonju",
        "list_subtitle": "Toque no cartão para ver detalhes à direita.",
        "chip_weather_rainy": "Dia chuvoso",
        "chip_weather_clear": "Dia claro",
        "chip_reason_rainy": "Foco interior/mercado",
        "chip_reason_clear": "Popular e caminhável",
        "chip_count": "Recomendações de hoje: {count}",
        "recommend_badge": "Recomendado hoje",
        "recommend_default": "Rota recomendada de hoje",
        "reason_rainy_indoor": "Chuva: rota interior/mercado",
        "reason_rainy_short": "Chuva: rota mais curta",
        "reason_popular": "Rota de lugares populares",
        "reason_walk": "Boa para caminhar",
        "route_desc": "Rota passando por {stops}.",
        "detail_total": "Tempo e custo total",
        "bus_number": "Linha",
        "headway": "Intervalo",
        "note": "Nota",
        "eta_next": "Próximo em",
        "eta_times": "Próximos ônibus",
        "bus_info_pending": "Info pendente",
        "walk_segment": "Trecho a pé",
    },
    "ru": {
        "list_title": "Популярные маршруты от станции Чонджу",
        "list_subtitle": "Нажмите на карточку, чтобы увидеть детали справа.",
        "chip_weather_rainy": "Дождливый день",
        "chip_weather_clear": "Ясный день",
        "chip_reason_rainy": "Фокус: интерьер/рынок",
        "chip_reason_clear": "Популярно и удобно пешком",
        "chip_count": "Сегодня рекомендуем: {count}",
        "recommend_badge": "Рекомендовано сегодня",
        "recommend_default": "Маршрут дня",
        "reason_rainy_indoor": "Дождь: маршрут по интерьеру/рынку",
        "reason_rainy_short": "Дождь: более короткий маршрут",
        "reason_popular": "Маршрут популярных мест",
        "reason_walk": "Подходит для прогулки",
        "route_desc": "Маршрут по {stops}.",
        "detail_total": "Общее время и стоимость",
        "bus_number": "Маршрут",
        "headway": "Интервал",
        "note": "Примечание",
        "eta_next": "Следующий через",
        "eta_times": "Следующие автобусы",
        "bus_info_pending": "Информация скоро",
        "walk_segment": "Пеший участок",
    },
    "pl": {
        "list_title": "Popularne trasy z dworca Jeonju",
        "list_subtitle": "Dotknij karty, aby zobaczyć szczegóły po prawej.",
        "chip_weather_rainy": "Deszczowy dzień",
        "chip_weather_clear": "Pogodny dzień",
        "chip_reason_rainy": "Wnętrza/targ",
        "chip_reason_clear": "Popularne i piesze",
        "chip_count": "Dzisiaj polecamy: {count}",
        "recommend_badge": "Polecane dziś",
        "recommend_default": "Dzisiejsza rekomendacja",
        "reason_rainy_indoor": "Deszcz: trasa wnętrza/targ",
        "reason_rainy_short": "Deszcz: krótsza trasa",
        "reason_popular": "Trasa popularnych miejsc",
        "reason_walk": "Dobra na spacer",
        "route_desc": "Trasa obejmująca {stops}.",
        "detail_total": "Łączny czas i koszt",
        "bus_number": "Linia",
        "headway": "Częstotliwość",
        "note": "Uwaga",
        "eta_next": "Następny za",
        "eta_times": "Następne autobusy",
        "bus_info_pending": "Brak informacji",
        "walk_segment": "Odcinek pieszy",
    },
    "cs": {
        "list_title": "Populární trasy ze stanice Jeonju",
        "list_subtitle": "Klepněte na kartu pro detaily vpravo.",
        "chip_weather_rainy": "Deštivý den",
        "chip_weather_clear": "Jasný den",
        "chip_reason_rainy": "Interiér/trh",
        "chip_reason_clear": "Populární a pěší",
        "chip_count": "Dnešní tipy: {count}",
        "recommend_badge": "Dnes doporučeno",
        "recommend_default": "Dnešní doporučení",
        "reason_rainy_indoor": "Déšť: interiér/trh",
        "reason_rainy_short": "Déšť: kratší trasa",
        "reason_popular": "Trasa oblíbených míst",
        "reason_walk": "Skvělé na chůzi",
        "route_desc": "Trasa zahrnující {stops}.",
        "detail_total": "Celkový čas a cena",
        "bus_number": "Linka",
        "headway": "Interval",
        "note": "Poznámka",
        "eta_next": "Další za",
        "eta_times": "Další autobusy",
        "bus_info_pending": "Info není k dispozici",
        "walk_segment": "Pěší úsek",
    },
    "uk": {
        "list_title": "Популярні маршрути від станції Чонджу",
        "list_subtitle": "Натисніть на картку, щоб побачити деталі праворуч.",
        "chip_weather_rainy": "Дощовий день",
        "chip_weather_clear": "Ясний день",
        "chip_reason_rainy": "Фокус: інтер'єр/ринок",
        "chip_reason_clear": "Популярно й зручно пішки",
        "chip_count": "Рекомендації сьогодні: {count}",
        "recommend_badge": "Рекомендовано сьогодні",
        "recommend_default": "Рекомендація дня",
        "reason_rainy_indoor": "Дощ: маршрут інтер'єр/ринок",
        "reason_rainy_short": "Дощ: коротший маршрут",
        "reason_popular": "Маршрут популярних місць",
        "reason_walk": "Добре для прогулянки",
        "route_desc": "Маршрут через {stops}.",
        "detail_total": "Загальний час і вартість",
        "bus_number": "Маршрут",
        "headway": "Інтервал",
        "note": "Примітка",
        "eta_next": "Наступний через",
        "eta_times": "Наступні автобуси",
        "bus_info_pending": "Інформація скоро",
        "walk_segment": "Пішохідна ділянка",
    },
    "lt": {
        "list_title": "Populiarūs maršrutai iš Jeonju stoties",
        "list_subtitle": "Palieskite kortelę, kad matytumėte detales dešinėje.",
        "chip_weather_rainy": "Lietinga diena",
        "chip_weather_clear": "Giedra diena",
        "chip_reason_rainy": "Vidaus/turgus",
        "chip_reason_clear": "Populiaru ir patogu pėsčiomis",
        "chip_count": "Šiandienos rekomendacijos: {count}",
        "recommend_badge": "Šiandien rekomenduojama",
        "recommend_default": "Šiandienos rekomendacija",
        "reason_rainy_indoor": "Lietus: vidaus/turgaus maršrutas",
        "reason_rainy_short": "Lietus: trumpesnis maršrutas",
        "reason_popular": "Populiarių vietų maršrutas",
        "reason_walk": "Puikiai tinka pasivaikščiojimui",
        "route_desc": "Maršrutas per {stops}.",
        "detail_total": "Bendras laikas ir kaina",
        "bus_number": "Maršrutas",
        "headway": "Intervalas",
        "note": "Pastaba",
        "eta_next": "Kitas po",
        "eta_times": "Kiti autobusai",
        "bus_info_pending": "Informacija ruošiama",
        "walk_segment": "Pėsčiųjų atkarpa",
    },
    "lv": {
        "list_title": "Populāri maršruti no Jeonju stacijas",
        "list_subtitle": "Pieskarieties kartei, lai redzētu detaļas labajā pusē.",
        "chip_weather_rainy": "Lietains laiks",
        "chip_weather_clear": "Skaidrs laiks",
        "chip_reason_rainy": "Iekštelpas/tirgus",
        "chip_reason_clear": "Populārs un piemērots pastaigai",
        "chip_count": "Šodienas ieteikumi: {count}",
        "recommend_badge": "Ieteikts šodien",
        "recommend_default": "Šodienas ieteikums",
        "reason_rainy_indoor": "Lietus: iekštelpu/tirgus maršruts",
        "reason_rainy_short": "Lietus: īsāks maršruts",
        "reason_popular": "Populāro vietu maršruts",
        "reason_walk": "Lieliski pastaigai",
        "route_desc": "Maršruts caur {stops}.",
        "detail_total": "Kopējais laiks un izmaksas",
        "bus_number": "Līnija",
        "headway": "Intervāls",
        "note": "Piezīme",
        "eta_next": "Nākamais pēc",
        "eta_times": "Nākamie autobusi",
        "bus_info_pending": "Informācija nav pieejama",
        "walk_segment": "Gājiena posms",
    },
}


def _t(lang: str, key: str, default: str) -> str:
    code = _place_lang_code(lang)
    info = ROUTE_I18N.get(code, ROUTE_I18N["en"])
    if key in info:
        return info[key]
    return ROUTE_I18N["en"].get(key, default)


TIME_FORMATS = {
    "en": {"hour": ("hour", "hours"), "min": ("minute", "minutes"), "unit_sep": " ", "segment_sep": " "},
    "ko": {"hour": ("시간", "시간"), "min": ("분", "분"), "unit_sep": "", "segment_sep": " "},
    "ja": {"hour": ("時間", "時間"), "min": ("分", "分"), "unit_sep": "", "segment_sep": ""},
    "zh-CN": {"hour": ("小时", "小时"), "min": ("分钟", "分钟"), "unit_sep": "", "segment_sep": ""},
    "zh-TW": {"hour": ("小時", "小時"), "min": ("分鐘", "分鐘"), "unit_sep": "", "segment_sep": ""},
    "de": {"hour": ("Stunde", "Stunden"), "min": ("Minute", "Minuten"), "unit_sep": " ", "segment_sep": " "},
    "nl": {"hour": ("uur", "uur"), "min": ("minuut", "minuten"), "unit_sep": " ", "segment_sep": " "},
    "sv": {"hour": ("timme", "timmar"), "min": ("minut", "minuter"), "unit_sep": " ", "segment_sep": " "},
    "fr": {"hour": ("heure", "heures"), "min": ("minute", "minutes"), "unit_sep": " ", "segment_sep": " "},
    "it": {"hour": ("ora", "ore"), "min": ("minuto", "minuti"), "unit_sep": " ", "segment_sep": " "},
    "es": {"hour": ("hora", "horas"), "min": ("minuto", "minutos"), "unit_sep": " ", "segment_sep": " "},
    "pt": {"hour": ("hora", "horas"), "min": ("minuto", "minutos"), "unit_sep": " ", "segment_sep": " "},
    "ru": {"hour": ("ч", "ч"), "min": ("мин", "мин"), "unit_sep": " ", "segment_sep": " "},
    "pl": {"hour": ("godz.", "godz."), "min": ("min", "min"), "unit_sep": " ", "segment_sep": " "},
    "cs": {"hour": ("hod", "hod"), "min": ("min", "min"), "unit_sep": " ", "segment_sep": " "},
    "uk": {"hour": ("год", "год"), "min": ("хв", "хв"), "unit_sep": " ", "segment_sep": " "},
    "lt": {"hour": ("val.", "val."), "min": ("min", "min"), "unit_sep": " ", "segment_sep": " "},
    "lv": {"hour": ("st.", "st."), "min": ("min", "min"), "unit_sep": " ", "segment_sep": " "},
}


def _romanize_korean(text: str) -> str:
    if not text:
        return text
    choseong = [
        "g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s",
        "ss", "", "j", "jj", "ch", "k", "t", "p", "h",
    ]
    jungseong = [
        "a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa",
        "wae", "oe", "yo", "u", "wo", "we", "wi", "yu", "eu", "ui", "i",
    ]
    jongseong = [
        "", "k", "k", "k", "n", "n", "n", "t", "l", "k",
        "m", "l", "l", "l", "p", "l", "m", "p", "p", "t",
        "t", "ng", "t", "t", "k", "t", "p", "t",
    ]
    result = []
    for char in text:
        code = ord(char)
        if 0xAC00 <= code <= 0xD7A3:
            syllable = code - 0xAC00
            cho = syllable // 588
            jung = (syllable % 588) // 28
            jong = syllable % 28
            result.append(choseong[cho] + jungseong[jung] + jongseong[jong])
        else:
            result.append(char)
    return "".join(result)


def _display_place_name(name: str, lang: str) -> str:
    if not name:
        return name
    if _place_lang_code(lang) == "ko":
        return name
    romanized = _romanize_korean(name)
    return " ".join(part.capitalize() for part in romanized.split(" "))


def format_duration(minutes, lang="en"):
    if not isinstance(minutes, (int, float)) or minutes < 0:
        return str(minutes)
    total = int(round(minutes))
    hours = total // 60
    mins = total % 60
    code = _place_lang_code(lang)
    fmt = TIME_FORMATS.get(code, TIME_FORMATS["en"])
    hour_singular, hour_plural = fmt["hour"]
    min_singular, min_plural = fmt["min"]
    unit_sep = fmt.get("unit_sep", " ")
    segment_sep = fmt.get("segment_sep", " ")
    hour_label = hour_singular if hours == 1 else hour_plural
    min_label = min_singular if mins == 1 else min_plural
    if hours <= 0:
        return f"{mins}{unit_sep}{min_label}".strip()
    if mins <= 0:
        return f"{hours}{unit_sep}{hour_label}".strip()
    return (
        f"{hours}{unit_sep}{hour_label}{segment_sep}{mins}{unit_sep}{min_label}"
    ).strip()



def _kma_service_key() -> str:
    return os.environ.get("KMA_SERVICE_KEY", "").strip()


def _kma_base_datetime(now=None):
    if now is None:
        now = datetime.now()
    base = now.replace(second=0, microsecond=0)
    if base.minute < 30:
        base -= timedelta(hours=1)
    base = base.replace(minute=30)
    return base.strftime("%Y%m%d"), base.strftime("%H%M")


def _latlng_to_grid(lat: float, lng: float):
    RE = 6371.00877
    GRID = 5.0
    SLAT1 = 30.0
    SLAT2 = 60.0
    OLON = 126.0
    OLAT = 38.0
    XO = 43
    YO = 136

    deg_to_rad = 3.141592653589793 / 180.0
    re = RE / GRID
    slat1 = SLAT1 * deg_to_rad
    slat2 = SLAT2 * deg_to_rad
    olon = OLON * deg_to_rad
    olat = OLAT * deg_to_rad

    sn = (math.tan(3.141592653589793 * 0.25 + slat2 * 0.5) /
          math.tan(3.141592653589793 * 0.25 + slat1 * 0.5))
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(3.141592653589793 * 0.25 + slat1 * 0.5)
    sf = math.pow(sf, sn) * math.cos(slat1) / sn
    ro = math.tan(3.141592653589793 * 0.25 + olat * 0.5)
    ro = re * sf / math.pow(ro, sn)

    ra = math.tan(3.141592653589793 * 0.25 + lat * deg_to_rad * 0.5)
    ra = re * sf / math.pow(ra, sn)
    theta = lng * deg_to_rad - olon
    if theta > 3.141592653589793:
        theta -= 2.0 * 3.141592653589793
    if theta < -3.141592653589793:
        theta += 2.0 * 3.141592653589793
    theta *= sn

    x = ra * math.sin(theta) + XO
    y = ro - ra * math.cos(theta) + YO
    return int(x + 0.5), int(y + 0.5)


def _fetch_kma_ultra_forecast(lat: float, lng: float):
    api_key = _kma_service_key()
    if not api_key:
        return None
    nx, ny = _latlng_to_grid(lat, lng)
    base_date, base_time = _kma_base_datetime()
    params = {
        "serviceKey": api_key,
        "pageNo": 1,
        "numOfRows": 1000,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }
    url = KMA_ULTRA_FCST_URL + "?" + urllib.parse.urlencode(params, safe="%")
    try:
        with urllib.request.urlopen(url, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    items = payload.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    if not items:
        return None
    by_time = {}
    for item in items:
        fcst_time = item.get("fcstTime")
        category = item.get("category")
        value = item.get("fcstValue")
        if not fcst_time or not category:
            continue
        by_time.setdefault(fcst_time, {})[category] = value
    if not by_time:
        return None
    target_time = sorted(by_time.keys())[0]
    values = by_time[target_time]
    return {"PTY": values.get("PTY")}


def _is_rainy(lat: float, lng: float) -> bool:
    data = _fetch_kma_ultra_forecast(lat, lng)
    if not data:
        return False
    try:
        pty = int(float(data.get("PTY", 0)))
    except (TypeError, ValueError):
        pty = 0
    return pty != 0


def load_kiosk_data(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def build_name_map(data: dict, lang: str = "ko"):
    names = {}
    for entry in data.get("place_i18n", []):
        if entry.get("lang") != lang:
            continue
        place_id = entry.get("place_id")
        name = entry.get("name")
        if place_id is None or not name:
            continue
        names[place_id] = name
    return names


def _set_back_button_icon(button: QPushButton, tooltip: str) -> None:
    size = 24
    ratio = button.devicePixelRatioF() if hasattr(button, "devicePixelRatioF") else 1.0
    pixmap = QPixmap(int(size * ratio), int(size * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.transparent)

    color = button.palette().color(button.palette().ButtonText)
    pen = QPen(color, 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(pen)

    path = QPainterPath()
    path.moveTo(size * 0.65, size * 0.2)
    path.lineTo(size * 0.35, size * 0.5)
    path.lineTo(size * 0.65, size * 0.8)
    painter.drawPath(path)
    painter.end()

    button.setIcon(QIcon(pixmap))
    button.setIconSize(pixmap.size() / pixmap.devicePixelRatio())
    button.setText("")
    button.setToolTip(tooltip)


def build_coord_map(data: dict, lang: str = "ko"):
    coords = {}
    place_index = {p.get("place_id"): p for p in data.get("places", [])}
    for entry in data.get("place_i18n", []):
        if entry.get("lang") != lang:
            continue
        place_id = entry.get("place_id")
        name = entry.get("name")
        place = place_index.get(place_id, {})
        lat = place.get("lat")
        lng = place.get("lng")
        if not name or lat is None or lng is None:
            continue
        coords[name] = (lat, lng)
    return coords


def pick_origin_name(data: dict, lang: str = "ko"):
    kiosks = data.get("kiosk", [])
    if not kiosks:
        return "Kiosk"
    kiosk_id = kiosks[0].get("kiosk_id")
    if not kiosk_id:
        return "Kiosk"
    for entry in data.get("kiosk_i18n", []):
        if entry.get("kiosk_id") == kiosk_id and entry.get("lang") == lang:
            return entry.get("name") or "Kiosk"
    return "Kiosk"


def _contains_keyword(text: str, keywords):
    if not text:
        return False
    return any(keyword in text for keyword in keywords)


def _rainy_score(route: dict) -> int:
    positives = ["시장", "성당", "경기전", "박물관", "실내"]
    negatives = ["공원", "호수", "벽화", "동물원", "오목대", "야외"]
    score = 0
    texts = [route.get("title", "")]
    texts.extend(route.get("stops", []) or [])
    for text in texts:
        if _contains_keyword(text, positives):
            score += 2
        if _contains_keyword(text, negatives):
            score -= 1
    if _contains_keyword(route.get("title", ""), ["도보", "걷기"]):
        score -= 1
    return score


def build_routes(data: dict, lang: str = "ko", rainy: bool = False):
    origin = "전주역" # Hardcode to 전주역 as per user request

    if not ROUTES_FILE.exists():
        return []

    try:
        with ROUTES_FILE.open("r", encoding="utf-8") as handle:
            routes_data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    for idx, route in enumerate(routes_data):
        if route.get("stops") and route["stops"][0] == "__ORIGIN__":
            route["stops"][0] = origin
        
        tour_stops = route.get("stops", [])[1:]
        stops_str = ", ".join(tour_stops)
        route["description"] = f"{stops_str} 등을 둘러보는 코스입니다."

    if rainy:
        scored = []
        for route in routes_data:
            score = _rainy_score(route)
            percent = route.get("percent", 0)
            scored.append((score, percent, route))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        recommended_routes = {item[2]["title"] for item in scored[:2] if item[2].get("title")}
        for route in routes_data:
            route["recommended"] = route.get("title") in recommended_routes
            if route["recommended"] and not route.get("recommend_reason_key"):
                score = _rainy_score(route)
                if score >= 2:
                    route["recommend_reason_key"] = "rainy_indoor"
                else:
                    route["recommend_reason_key"] = "rainy_short"
    else:
        for idx, route in enumerate(routes_data):
            route["recommended"] = route.get("recommended", False) or idx < 2
            if route["recommended"] and not route.get("recommend_reason_key"):
                if idx == 0:
                    route["recommend_reason_key"] = "popular"
                else:
                    route["recommend_reason_key"] = "walk"
    
    return routes_data


def normalize_manual_name(name):
    if not name:
        return name
    name = str(name).strip()
    return MANUAL_NAME_ALIASES.get(name, name)


def normalize_pair_key(text):
    if text is None:
        return ""
    value = normalize_manual_name(text)
    value = re.sub(r"[\s·.()/-]", "", value)
    return value


def normalize_bus_no(bus_no):
    if not bus_no:
        return ""
    return str(bus_no).strip()


def load_timetable_eta():
    if not TIMETABLE_FILE.exists():
        return {"by_segment": {}}
    try:
        raw = TIMETABLE_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        try:
            raw = TIMETABLE_FILE.read_text(encoding="utf-8-sig")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return {"by_segment": {}}

    by_segment = {}
    for item in data.get("items", []):
        start = normalize_pair_key(item.get("start_stop_name"))
        end = normalize_pair_key(item.get("end_stop_name"))
        if not start or not end:
            continue
        key = (start, end)
        by_segment.setdefault(key, []).append(item)
    return {"by_segment": by_segment}


def load_resolved_routes():
    if not RESOLVED_ROUTES_FILE.exists():
        return {}
    try:
        raw = RESOLVED_ROUTES_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        try:
            raw = RESOLVED_ROUTES_FILE.read_text(encoding="utf-8-sig")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return {}
    by_segment = {}
    for item in data:
        start = normalize_pair_key(item.get("start_stop_name"))
        end = normalize_pair_key(item.get("end_stop_name"))
        if not start or not end:
            continue
        key = (start, end)
        by_segment.setdefault(key, []).append(item)
    return by_segment


def format_hhmm(value):
    try:
        val = int(value)
    except (TypeError, ValueError):
        return None
    hh = val // 100
    mm = val % 100
    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
        return None
    return f"{hh:02d}:{mm:02d}"


def load_bus_schedule():
    if not BUS_SCHEDULE_FILE.exists():
        return {}
    try:
        raw = BUS_SCHEDULE_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        try:
            raw = BUS_SCHEDULE_FILE.read_text(encoding="utf-8-sig")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return {}
    schedule = {}
    for bus_no, items in data.get("results", {}).items():
        for item in items:
            summary = item.get("route_summary") or {}
            if not summary:
                continue
            first_time = format_hhmm(summary.get("first_time"))
            last_time = format_hhmm(summary.get("last_time"))
            if first_time or last_time:
                schedule[normalize_bus_no(bus_no)] = {
                    "first_bus": first_time,
                    "last_bus": last_time,
                }
                break
    return schedule


def load_manual_bus_pairs():
    if not MANUAL_BUS_ROUTES_FILE.exists():
        return {}
    try:
        raw = MANUAL_BUS_ROUTES_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        try:
            raw = MANUAL_BUS_ROUTES_FILE.read_text(encoding="utf-8-sig")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return {}
    pairs = {}
    for entry in data.get("pairs", []):
        start = entry.get("from")
        end = entry.get("to")
        if not start or not end:
            continue
        pairs[(start, end)] = entry
        norm_key = (normalize_pair_key(start), normalize_pair_key(end))
        if norm_key != (start, end) and norm_key not in pairs:
            pairs[norm_key] = entry
    return pairs





def haversine_km(start, end):
    if not start or not end:
        return None
    lat1, lon1 = start
    lat2, lon2 = end
    radius = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    return 2 * radius * atan2(sqrt(a), sqrt(1 - a))


def build_segment_data(
    stops,
    coord_map,
    bus_mapping_data,
    manual_pairs,
    origin_name=None,
    resolved_routes=None,
    timetable_data=None,
    schedule_data=None,
):
    segments = []
    
    segment_routes_from_map = bus_mapping_data.get("segment_routes", {})
    route_info_from_map = bus_mapping_data.get("route_info", {})

    for idx in range(len(stops) - 1):
        start = stops[idx]
        end = stops[idx + 1]
        start_coord = coord_map.get(start)
        end_coord = coord_map.get(end)
        distance_km = haversine_km(start_coord, end_coord)

        # 1. Set default calculated times
        if distance_km:
            walk_min = max(3, round(distance_km / WALK_SPEED_KMPH * 60))
            bus_min = max(3, round(distance_km / BUS_SPEED_KMPH * 60))
            taxi_min = max(3, round(distance_km / TAXI_SPEED_KMPH * 60))
        else:
            # Fallback if no distance data
            walk_min = 12 + idx * 3
            bus_min = 8 + idx * 2
            taxi_min = 6 + idx * 2

        bus_no = None
        bus_list = []
        bus_note = None
        taxi_price = None

        headway_min = None
        first_bus = None
        last_bus = None

        # 2. Check for manual overrides from manual_bus_routes.json
        manual = manual_pairs.get((normalize_pair_key(start), normalize_pair_key(end)))
        if manual:
            walk_min = manual.get("walk_minutes", walk_min)
            bus_min = manual.get("bus_minutes", bus_min)
            if "taxi_minutes" in manual:
                taxi_min = manual["taxi_minutes"]
            taxi_price = manual.get("taxi_price")
            
            bus_list = manual.get("bus_numbers") or []
            if bus_list:
                bus_no = ", ".join(bus_list)

            bus_note = manual.get("note")

            # Handle the "WALK" fallback for bus_no display if no bus numbers are provided
            fallback = (manual.get("fallback") or "").upper()
            if not bus_list and (fallback == "WALK" or manual.get("same_zone")):
                bus_no = WALK_SENTINEL
        if not bus_list and resolved_routes:
            segment_key = (normalize_pair_key(start), normalize_pair_key(end))
            resolved = resolved_routes.get(segment_key, [])
            if resolved:
                bus_list = [r.get("bus_no") for r in resolved if r.get("bus_no")]
                if bus_list:
                    bus_no = ", ".join(bus_list)

        # 3. Get actual bus schedule data from bus_mapping.json if bus_list is available
        if bus_list:
            found_schedule_data = None
            for bus_num_str in bus_list:
                for brt_stdid, info in route_info_from_map.items():
                    if info.get("brtId") == bus_num_str:
                        found_schedule_data = info
                        break # Found schedule for this bus number
                if found_schedule_data:
                    break # Found schedule for a bus in bus_list
            
            if found_schedule_data:
                headway_min = found_schedule_data.get("brtMininTerval") or found_schedule_data.get("brtMaxinTerval")
                first_bus = found_schedule_data.get("brtFirstTime")
                last_bus = found_schedule_data.get("brtLastTime")

        if schedule_data and bus_list and (not first_bus or not last_bus):
            for candidate in bus_list:
                sched = schedule_data.get(normalize_bus_no(candidate))
                if sched:
                    first_bus = first_bus or sched.get("first_bus")
                    last_bus = last_bus or sched.get("last_bus")
                    break

        eta_item = None
        if timetable_data:
            segment_key = (normalize_pair_key(start), normalize_pair_key(end))
            candidates = timetable_data.get("by_segment", {}).get(segment_key, [])
            if candidates and bus_list:
                for candidate in candidates:
                    if normalize_bus_no(candidate.get("bus_no")) in [
                        normalize_bus_no(b) for b in bus_list
                    ]:
                        eta_item = candidate
                        break
            if not eta_item and candidates:
                eta_item = candidates[0]

        segments.append(
            {
                "start": start,
                "end": end,
                "walk_min": walk_min,
                "bus_min": bus_min,
                "taxi_min": taxi_min,
                "taxi_price": taxi_price,
                "bus_no": bus_no or "INFO_PENDING",
                "bus_list": bus_list,
                "bus_note": bus_note,
                "eta_item": eta_item,
                "headway_min": headway_min,
                "first_bus": first_bus,
                "last_bus": last_bus,
            }
        )
    return segments


def format_route(route):
    return " → ".join(route.get("stops", []))


def summarize_time(segments):
    walk = sum(seg["walk_min"] for seg in segments if seg.get("walk_min") is not None)
    bus = sum(seg["bus_min"] for seg in segments if seg.get("bus_min") is not None)
    taxi = sum(seg["taxi_min"] for seg in segments if seg.get("taxi_min") is not None)
    return walk, bus, taxi


def estimate_prices(seg):
    walk_price = 0
    bus_price = 1400
    manual_taxi_price = seg.get("taxi_price")
    if manual_taxi_price is not None:
        taxi_price = manual_taxi_price
    elif seg.get("taxi_min") is not None:
        taxi_price = 3800 + seg["taxi_min"] * 200
    else:
        taxi_price = 0
    return walk_price, bus_price, taxi_price


def summarize_costs(segments):
    walk_total = 0
    bus_total = 0
    taxi_total = 0
    for seg in segments:
        walk_price, bus_price, taxi_price = estimate_prices(seg)
        walk_total += walk_price
        bus_total += bus_price
        taxi_total += taxi_price
    return walk_total, bus_total, taxi_total


def format_price(value):
    return f"{value:,}원"


def format_minutes(minutes, lang="en"):
    return format_duration(minutes, lang)


class RouteGuideWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kiosk Route Guide")
        self.setGeometry(80, 80, 1600, 900)
        self.setObjectName("routeGuide")
        self._apply_fonts()
        self._current_language = "English"
        self.current_route = None

        data = load_kiosk_data(KIOSK_DATA_FILE)
        self.coord_map = build_coord_map(data, "ko")
        self.origin_name = "전주역" # Hardcode to 전주역 as per user request
        kiosk_info = (data.get("kiosk") or [{}])[0]
        lat = kiosk_info.get("lat")
        lng = kiosk_info.get("lng")
        rainy = False
        force_rainy = os.environ.get("FORCE_RAINY", "").strip().lower() in ("1", "true", "yes")
        if force_rainy:
            rainy = True
        elif lat is not None and lng is not None:
            try:
                rainy = _is_rainy(float(lat), float(lng))
            except (TypeError, ValueError):
                rainy = False
        self.is_rainy = rainy
        self.routes = build_routes(data, "ko", rainy=rainy)
        
        bus_mapping_raw_data = {}
        if BUS_MAPPING_FILE.exists():
            try:
                bus_mapping_raw_data = json.loads(BUS_MAPPING_FILE.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        self.bus_mapping_data = bus_mapping_raw_data
        
        self.manual_pairs = load_manual_bus_pairs()
        self.resolved_routes = load_resolved_routes()
        self.timetable_data = load_timetable_eta()
        self.schedule_data = load_bus_schedule()

        self.route_card_map = {}
        self.selected_card = None

        self.back_button = None
        self.root = QWidget()
        self.root.setObjectName("routeRoot")
        self.setCentralWidget(self.root)
        root_layout = QVBoxLayout(self.root)
        root_layout.setContentsMargins(22, 22, 22, 22)
        root_layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)
        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("navBtn")
        _set_back_button_icon(self.back_button, "Back")
        self.back_button.clicked.connect(self._handle_back)
        header.addWidget(self.back_button, 0, alignment=Qt.AlignLeft)
        header.addStretch(1)
        root_layout.addLayout(header, 0)

        self.detail_panel = self.build_detail_panel()
        self.list_panel = self.build_route_list_panel()

        self.main_row = QHBoxLayout()
        self.main_row.setSpacing(20)
        self.main_row.addWidget(self.list_panel, 2)
        self.main_row.addWidget(self.detail_panel, 4)
        root_layout.addLayout(self.main_row, 1)

        if self.routes:
            first_route = self.routes[0]
            first_card = self.route_card_map.get(first_route["title"])
            self.show_detail(first_route, first_card)
        self._apply_style()

    def set_language(self, lang: str):
        if not lang:
            return
        self._current_language = lang
        self._rebuild_panels()

    def _rebuild_panels(self):
        if self.list_panel:
            self.main_row.removeWidget(self.list_panel)
            self.list_panel.deleteLater()
        if self.detail_panel:
            self.main_row.removeWidget(self.detail_panel)
            self.detail_panel.deleteLater()
        self.list_panel = self.build_route_list_panel()
        self.detail_panel = self.build_detail_panel()
        self.main_row.insertWidget(0, self.list_panel, 2)
        self.main_row.insertWidget(1, self.detail_panel, 4)
        if self.current_route:
            route = next(
                (item for item in self.routes if item.get("title") == self.current_route.get("title")),
                self.routes[0] if self.routes else None,
            )
            if route:
                card = self.route_card_map.get(route.get("title"))
                self.show_detail(route, card)

    def _is_korean(self) -> bool:
        return _place_lang_code(self._current_language) == "ko"

    def _display_route_title(self, route: dict, index: int) -> str:
        if self._is_korean():
            return route.get("title", "")
        letter = chr(ord("A") + index)
        return f"Course {letter}"

    def _display_stop(self, name: str) -> str:
        return _display_place_name(name, self._current_language)

    def _format_route_path(self, route: dict) -> str:
        stops = route.get("stops", [])
        display = [self._display_stop(stop) for stop in stops if stop]
        return " \u2192 ".join(display)

    def _format_route_description(self, route: dict) -> str:
        if self._is_korean():
            return route.get("description", "")
        stops = route.get("stops", [])[1:]
        display = [self._display_stop(stop) for stop in stops if stop]
        template = _t(self._current_language, "route_desc", "Route covering {stops}.")
        return template.format(stops=" / ".join(display))

    def _recommend_reason_text(self, route: dict) -> str:
        key = route.get("recommend_reason_key")
        if key == "rainy_indoor":
            return _t(self._current_language, "reason_rainy_indoor", "Rainy day: indoor/market route")
        if key == "rainy_short":
            return _t(self._current_language, "reason_rainy_short", "Rainy day: shorter route")
        if key == "walk":
            return _t(self._current_language, "reason_walk", "Great for walking")
        if key == "popular":
            return _t(self._current_language, "reason_popular", "Popular attractions route")
        return _t(self._current_language, "recommend_default", "Today's recommended route")

    def _handle_back(self):
        on_back = getattr(self, "on_back", None)
        if callable(on_back):
            on_back()
            return
        self.hide()

    def _apply_fonts(self):
        font_path = APP_DIR / "fonts" / "NotoSansCJKkr-Regular.otf"
        font_family = None
        if font_path.exists():
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    font_family = families[0]
        if font_family:
            self.setFont(QFont(font_family, 10))

    def _apply_style(self):
        self.setStyleSheet(
            """
            QWidget#routeGuide {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f5efe6, stop:0.55 #f1f4ff, stop:1 #e7f6f3);
            }
            QWidget#routeRoot { color: #111827; }
            QScrollArea { border: none; }

            QPushButton#navBtn {
                background: #1d4ed8;
                color: #ffffff;
                border-radius: 16px;
                padding: 10px 16px;
                font-weight: bold;
            }
            QPushButton#navBtn:hover {
                background: #2563eb;
            }

            QWidget#listPanel {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
            }

            QFrame#routeCard {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 14px;
            }
            QFrame#routeCard:hover {
                border-color: #cbd5e1;
            }
            QFrame#routeCard[selected="true"] {
                border-color: #2563eb;
                background-color: #eff6ff;
            }
            QLabel#percentBadge {
                background-color: #fde68a;
                color: #92400e;
                border-radius: 30px;
                font-size: 15px;
                font-weight: bold;
            }
            QLabel#routeCardTitle {
                font-size: 18px;
                font-weight: bold;
                color: #111827;
            }
            QLabel#routeCardPath {
                font-size: 13px;
                color: #4b5563;
            }
            QLabel#routeCardDescription {
                font-size: 12px;
                color: #6b7280;
                padding-top: 5px;
            }
            QFrame#routeCard[recommended="true"] {
                border-color: #2563eb;
                background-color: #f8fbff;
            }
            QLabel#chipLabel {
                background-color: #eef2ff;
                color: #1e40af;
                border-radius: 10px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#recommendBadge {
                background-color: #2563eb;
                color: #ffffff;
                border-radius: 10px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QLabel#recommendDesc {
                font-size: 12px;
                color: #1d4ed8;
                font-weight: 600;
            }

            QWidget#detailPanel {
                background-color: #ffffff;
                border-radius: 16px;
                border: 1px solid #e5e7eb;
            }
            QLabel#detailTitle {
                font-size: 24px;
                font-weight: bold;
                color: #111827;
            }
            QLabel#detailPath {
                font-size: 14px;
                color: #4b5563;
            }
            QLabel#detailDescription {
                font-size: 13px;
                color: #374151;
                padding-top: 5px;
                padding-bottom: 5px;
            }
            QLabel#detailTotal {
                font-size: 13px;
                color: #374151;
                background-color: #f8fafc;
                border-radius: 10px;
                padding: 10px;
            }
            QFrame#segmentCard {
                background-color: #f8fafc;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
            }
            QLabel#segmentTitle {
                font-size: 15px;
                font-weight: bold;
                color: #1f2937;
            }
            QLabel {
                font-size: 13px;
            }
            """
        )

    def build_route_list_panel(self):
        container = QWidget()
        container.setObjectName("listPanel")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel(_t(self._current_language, "list_title", "Recommended routes from Jeonju Station"))
        title_font = title.font()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)

        subtitle = QLabel(_t(self._current_language, "list_subtitle", "Tap a card to see details on the right."))
        subtitle.setStyleSheet("color: #6b7280;")
        subtitle_font = subtitle.font()
        subtitle_font.setPointSize(14)
        subtitle.setFont(subtitle_font)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        chip_row = QHBoxLayout()
        chip_row.setSpacing(8)
        weather_chip = QLabel(
            _t(
                self._current_language,
                "chip_weather_rainy" if self.is_rainy else "chip_weather_clear",
                "Rainy day" if self.is_rainy else "Clear day",
            )
        )
        weather_chip.setObjectName("chipLabel")
        chip_row.addWidget(weather_chip)
        if self.is_rainy:
            reason_chip = QLabel(_t(self._current_language, "chip_reason_rainy", "Indoor/market focus"))
        else:
            reason_chip = QLabel(_t(self._current_language, "chip_reason_clear", "Popular & walk-friendly"))
        reason_chip.setObjectName("chipLabel")
        chip_row.addWidget(reason_chip)
        count_chip = QLabel(
            _t(self._current_language, "chip_count", "Today's picks: {count}").format(count=2)
        )
        count_chip.setObjectName("chipLabel")
        chip_row.addWidget(count_chip)
        chip_row.addStretch(1)
        layout.addLayout(chip_row)
        layout.addSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        layout.addWidget(scroll, 1)

        grid_wrapper = QWidget()
        grid_layout = QGridLayout(grid_wrapper)
        grid_layout.setContentsMargins(0, 10, 10, 10)
        grid_layout.setSpacing(16)
        scroll.setWidget(grid_wrapper)

        columns = 1
        for idx, route in enumerate(self.routes):
            row = idx // columns
            col = idx % columns
            route["_index"] = idx
            card = self.create_route_card(route, idx)
            self.route_card_map[route["title"]] = card
            card.mousePressEvent = lambda event, r=route, c=card: self.show_detail(
                r, c, event
            )
            grid_layout.addWidget(card, row, col)

        return container

    def create_route_card(self, route, index: int):
        card = QFrame()
        card.setObjectName("routeCard")
        card.setCursor(Qt.PointingHandCursor)
        if route.get("recommended"):
            card.setProperty("recommended", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(10)

        title_row = QWidget()
        title_layout = QHBoxLayout(title_row)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(12)

        percent_badge = QLabel(f"{route['percent']}%")
        percent_badge.setObjectName("percentBadge")
        percent_badge.setAlignment(Qt.AlignCenter)
        percent_badge.setFixedSize(52, 52)

        title_label = QLabel(self._display_route_title(route, index))
        title_label.setObjectName("routeCardTitle")
        title_label.setWordWrap(True)

        title_layout.addWidget(percent_badge)
        title_layout.addWidget(title_label, 1)

        path = QLabel(self._format_route_path(route))
        path.setWordWrap(True)
        path.setObjectName("routeCardPath")
        
        description = QLabel(self._format_route_description(route))
        description.setWordWrap(True)
        description.setObjectName("routeCardDescription")

        card_layout.addWidget(title_row)
        card_layout.addWidget(path)
        card_layout.addWidget(description)
        if route.get("recommended"):
            reason = self._recommend_reason_text(route)
            recommend_row = QHBoxLayout()
            recommend_row.setSpacing(6)
            recommend_badge = QLabel(_t(self._current_language, "recommend_badge", "Today's pick"))
            recommend_badge.setObjectName("recommendBadge")
            reason_label = QLabel(reason)
            reason_label.setObjectName("recommendDesc")
            reason_label.setWordWrap(True)
            recommend_row.addWidget(recommend_badge, 0)
            recommend_row.addWidget(reason_label, 1)
            card_layout.addLayout(recommend_row)
        return card

    def build_detail_panel(self):
        container = QWidget()
        container.setObjectName("detailPanel")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        self.detail_title_label = QLabel("")
        self.detail_title_label.setObjectName("detailTitle")

        self.detail_path_label = QLabel("")
        self.detail_path_label.setWordWrap(True)
        self.detail_path_label.setObjectName("detailPath")

        self.detail_description_label = QLabel("")
        self.detail_description_label.setWordWrap(True)
        self.detail_description_label.setObjectName("detailDescription")

        self.detail_total_label = QLabel("")
        self.detail_total_label.setObjectName("detailTotal")
        self.detail_total_label.setWordWrap(True)

        header_layout.addWidget(self.detail_title_label)
        header_layout.addWidget(self.detail_path_label)
        header_layout.addWidget(self.detail_description_label)
        header_layout.addSpacing(10)
        header_layout.addWidget(self.detail_total_label)
        layout.addWidget(header)

        self.detail_scroll = QScrollArea()
        self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setFrameShape(QFrame.NoFrame)
        self.detail_scroll.setObjectName("detailScroll")
        layout.addWidget(self.detail_scroll, 1)

        self.detail_body = QWidget()
        self.detail_layout = QVBoxLayout(self.detail_body)
        self.detail_layout.setContentsMargins(0, 5, 5, 5)
        self.detail_layout.setSpacing(14)
        self.detail_scroll.setWidget(self.detail_body)

        return container

    def show_detail(self, route, card=None, event=None):
        if self.selected_card:
            self.selected_card.setProperty("selected", False)
            self.selected_card.style().unpolish(self.selected_card)
            self.selected_card.style().polish(self.selected_card)

        if card:
            card.setProperty("selected", True)
            card.style().unpolish(card)
            card.style().polish(card)
            self.selected_card = card

        self.current_route = route
        index = route.get("_index", 0)
        self.detail_title_label.setText(self._display_route_title(route, index))
        self.detail_path_label.setText(self._format_route_path(route))
        self.detail_description_label.setText(self._format_route_description(route))

        segments = build_segment_data(
            route.get("stops", []),
            self.coord_map,
            self.bus_mapping_data, # Pass entire bus_mapping_data
            self.manual_pairs,
            self.origin_name,
            self.resolved_routes,
            self.timetable_data,
            self.schedule_data,
        )
        walk, bus, taxi = summarize_time(segments)
        walk_cost, bus_cost, taxi_cost = summarize_costs(segments)

        cost_style = "color:#b58a52; font-weight:bold;"
        summary_parts = [
            f"<b>Walk:</b> {format_minutes(walk, self._current_language)}, <span style='{cost_style}'>{format_price(walk_cost)}</span>",
            f"<b>Bus:</b> {format_minutes(bus, self._current_language)}, <span style='{cost_style}'>{format_price(bus_cost)}</span>",
        ]
        if taxi > 0 or taxi_cost > 0:
            summary_parts.append(
                f"<b>Taxi:</b> {format_minutes(taxi, self._current_language)}, about <span style='{cost_style}'>{format_price(taxi_cost)}</span>"
            )

        self.detail_total_label.setText(
            f"<b>{_t(self._current_language, 'detail_total', 'Total time & cost')}</b><br>"
            + " | ".join(summary_parts)
        )

        self.clear_layout(self.detail_layout)
        for seg in segments:
            self.detail_layout.addWidget(self.build_segment_card(seg))
        self.detail_layout.addStretch(1)

        if event:
            event.accept()

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def build_segment_card(self, seg):
        card = QFrame()
        card.setObjectName("segmentCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        start_name = self._display_stop(seg.get("start"))
        end_name = self._display_stop(seg.get("end"))
        title = QLabel(f"{start_name} → {end_name}")
        title.setObjectName("segmentTitle")
        layout.addWidget(title)

        grid = QWidget()
        grid_layout = QGridLayout(grid)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setHorizontalSpacing(15)
        grid_layout.setVerticalSpacing(10)
        layout.addWidget(grid)

        walk_price, bus_price, taxi_price = estimate_prices(seg)
        cost_style = "color:#b58a52; font-weight:bold;"
        
        current_row = 0

        # Walk
        if seg.get("walk_min") is not None:
            grid_layout.addWidget(QLabel("🚶️"), current_row, 0)
            grid_layout.addWidget(QLabel("<b>Walk</b>"), current_row, 1)
            grid_layout.addWidget(QLabel(format_minutes(seg['walk_min'], self._current_language)), current_row, 2)
            walk_cost_text = f"<span style='{cost_style}'>{format_price(walk_price)}</span>"
            grid_layout.addWidget(QLabel(walk_cost_text), current_row, 3, Qt.AlignRight)
            current_row += 1

        # Bus
        if seg.get("bus_min") is not None:
            grid_layout.addWidget(QLabel("🚌"), current_row, 0)
            grid_layout.addWidget(QLabel("<b>Bus</b>"), current_row, 1)
            grid_layout.addWidget(QLabel(format_minutes(seg['bus_min'], self._current_language)), current_row, 2)
            bus_cost_text = f"<span style='{cost_style}'>{format_price(bus_price)}</span>"
            grid_layout.addWidget(QLabel(bus_cost_text), current_row, 3, Qt.AlignRight)
            
            bus_details_widget = QWidget()
            bus_details_layout = QVBoxLayout(bus_details_widget)
            bus_details_layout.setContentsMargins(0, 0, 0, 0)
            bus_details_layout.setSpacing(4)
            
            bus_no_text = seg.get("bus_no")
            if bus_no_text == WALK_SENTINEL:
                bus_no_text = _t(self._current_language, "walk_segment", "Walk segment")
            if bus_no_text in (None, "", "INFO_PENDING"):
                bus_no_text = _t(self._current_language, "bus_info_pending", "Info pending")
            if seg.get("bus_list"):
                bus_no_text = ", ".join(seg["bus_list"])
            
            if seg.get("bus_no") != WALK_SENTINEL:
                bus_num_label = QLabel(
                    f"<b>{_t(self._current_language, 'bus_number', 'Bus No.')}:</b> {bus_no_text}"
                )
                bus_details_layout.addWidget(bus_num_label)

                if seg.get("headway_min") and seg.get("first_bus") and seg.get("last_bus"):
                    headway_label = QLabel(
                        f"<b>{_t(self._current_language, 'headway', 'Headway')}:</b> "
                        f"~{format_duration(seg['headway_min'], self._current_language)} "
                        f"(first {seg['first_bus']} / last {seg['last_bus']})"
                    )
                    bus_details_layout.addWidget(headway_label)
                eta_item = seg.get("eta_item")
                if eta_item and eta_item.get("status", {}).get("code") == "000":
                    next_in = eta_item.get("next_in_minutes")
                    next_times = eta_item.get("next_times") or []
                    if next_in is not None:
                        eta_label = QLabel(
                            f"<b>{_t(self._current_language, 'eta_next', 'Next in')}:</b> "
                            f"{format_duration(next_in, self._current_language)}"
                        )
                        bus_details_layout.addWidget(eta_label)
                    if next_times:
                        times_label = QLabel(
                            f"<b>{_t(self._current_language, 'eta_times', 'Next buses')}:</b> "
                            f"{', '.join(next_times[:3])}"
                        )
                        bus_details_layout.addWidget(times_label)
            
            if seg.get("bus_note"):
                note_label = QLabel(
                    f"<b>{_t(self._current_language, 'note', 'Note')}:</b> {seg['bus_note']}"
                )
                note_label.setWordWrap(True)
                bus_details_layout.addWidget(note_label)

            if bus_details_layout.count() > 0:
                current_row += 1
                grid_layout.addWidget(bus_details_widget, current_row, 1, 1, 3)
            
            current_row += 1

        # Taxi
        if seg.get("taxi_min") is not None:
            grid_layout.addWidget(QLabel("🚕"), current_row, 0)
            grid_layout.addWidget(QLabel("<b>Taxi</b>"), current_row, 1)
            grid_layout.addWidget(QLabel(format_minutes(seg['taxi_min'], self._current_language)), current_row, 2)
            taxi_cost_text = f"about <span style='{cost_style}'>{format_price(taxi_price)}</span>"
            grid_layout.addWidget(QLabel(taxi_cost_text), current_row, 3, Qt.AlignRight)
            current_row += 1

        grid_layout.setColumnStretch(2, 1)
        return card


def main():
    app = QApplication(sys.argv)

    font_db = QFontDatabase()
    font_path = str(APP_DIR / "fonts" / "NotoSansCJKkr-Regular.otf")
    font_id = font_db.addApplicationFont(font_path)
    if font_id != -1:
        font_families = QFontDatabase.applicationFontFamilies(font_id)
        if font_families:
            app.setFont(QFont(font_families[0], 10))

    app.setStyleSheet(
        """
        QWidget#routeGuide {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #f5efe6, stop:0.55 #f1f4ff, stop:1 #e7f6f3);
        }
        QWidget#routeRoot { color: #111827; }
        QScrollArea { border: none; }

        QWidget#listPanel {
            background-color: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 16px;
        }

        QFrame#routeCard {
            background-color: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
        }
        QFrame#routeCard:hover {
            border-color: #cbd5e1;
        }
        QFrame#routeCard[selected="true"] {
            border-color: #2563eb;
            background-color: #eff6ff;
        }
        QLabel#percentBadge {
            background-color: #fde68a;
            color: #92400e;
            border-radius: 30px;
            font-size: 16px;
            font-weight: bold;
        }
        QLabel#routeCardTitle {
            font-size: 18px;
            font-weight: bold;
            color: #111827;
        }
        QLabel#routeCardPath {
            font-size: 13px;
            color: #4b5563;
        }
        QLabel#routeCardDescription {
            font-size: 12px;
            color: #6b7280;
            padding-top: 5px;
        }

        QWidget#detailPanel {
            background-color: #ffffff;
            border-radius: 16px;
            border: 1px solid #e5e7eb;
        }
        QLabel#detailTitle {
            font-size: 24px;
            font-weight: bold;
            color: #111827;
        }
        QLabel#detailPath {
            font-size: 14px;
            color: #4b5563;
        }
        QLabel#detailDescription {
            font-size: 13px;
            color: #374151;
            padding-top: 5px;
            padding-bottom: 5px;
        }
        QLabel#detailTotal {
            font-size: 13px;
            color: #374151;
            background-color: #f8fafc;
            border-radius: 10px;
            padding: 10px;
        }
        QFrame#segmentCard {
            background-color: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
        }
        QLabel#segmentTitle {
            font-size: 15px;
            font-weight: bold;
            color: #1f2937;
        }
        QLabel {
            font-size: 13px;
        }
        """
    )
    window = RouteGuideWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

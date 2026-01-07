
import sys
import requests
import math  # 거리 계산을 위한 math 라이브러리 임포트
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame, QComboBox, QMessageBox, QDialog, QCheckBox
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

# --- 신규 추가: 거리 계산 함수 ---
def calculate_distance(lat1, lon1, lat2, lon2):
    """ 두 위도/경도 지점 간의 거리를 킬로미터(km) 단위로 반환 (Haversine formula) """
    R = 6371  # 지구의 반경 (km)
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (math.sin(dLat / 2) * math.sin(dLat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dLon / 2) * math.sin(dLon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance

class PlaceCard(QFrame):
    # (이전과 동일)
    def __init__(self, place_data, detail_callback):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QHBoxLayout()
        image_placeholder = QFrame()
        image_placeholder.setFixedSize(100, 100)
        color_val = (place_data.get('cover_image_id', 9000) * 10) % 255
        image_placeholder.setStyleSheet(f"background-color: hsl({color_val}, 150, 200); border-radius: 5px;")
        layout.addWidget(image_placeholder)
        text_layout = QVBoxLayout()
        name_label = QLabel(place_data.get('name', 'N/A'))
        name_label.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        type_category = f"[{place_data.get('type', 'N/A')}] {place_data.get('category', 'N/A')}"
        category_label = QLabel(type_category)
        category_label.setStyleSheet("color: gray;")
        desc_label = QLabel(place_data.get('short_desc', ''))
        desc_label.setWordWrap(True)
        tags_label = QLabel("Tags: " + ", ".join(place_data.get('tags', [])))
        tags_label.setStyleSheet("font-style: italic; color: #555;")
        text_layout.addWidget(name_label)
        text_layout.addWidget(category_label)
        text_layout.addWidget(desc_label)
        text_layout.addWidget(tags_label)
        text_layout.addStretch()
        layout.addLayout(text_layout)
        layout.addStretch()
        detail_button = QPushButton("Details")
        detail_button.setFixedWidth(80)
        detail_button.clicked.connect(lambda: detail_callback(place_data))
        layout.addWidget(detail_button)
        self.setLayout(layout)

# --- 신규 추가: 길안내 전용 다이얼로그 ---
class RouteGuidanceDialog(QDialog):
    def __init__(self, start_location, destination_place, bus_stops, parent=None):
        super().__init__(parent)
        self.start_loc = start_location
        self.dest_place = destination_place
        self.bus_stops = bus_stops

        self.setWindowTitle(f"{self.dest_place.get('name', 'N/A')} 길안내")
        self.setMinimumWidth(400)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # 거리 계산 및 도보/버스 분기
        distance = calculate_distance(
            self.start_loc['lat'], self.start_loc['lng'],
            self.dest_place['lat'], self.dest_place['lng']
        )
        
        title = QLabel(f"'{self.dest_place.get('name')}'까지의 거리: {distance:.2f} km")
        title.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        self.layout.addWidget(title)

        if distance < 1.5:  # 1.5km 미만은 도보 안내
            self.setup_walk_ui(distance)
        else:
            self.setup_bus_ui()

    def setup_walk_ui(self, distance):
        self.layout.addWidget(QLabel("✅ 추천 경로: 도보"))
        est_time = int(distance * 15) # 1km당 15분으로 계산
        self.layout.addWidget(QLabel(f"예상 소요 시간: 약 {est_time} 분"))

    def setup_bus_ui(self):
        self.layout.addWidget(QLabel("✅ 추천 경로: 버스"))

        # 가장 가까운 버스 정류장 찾기 (Mock)
        nearest_stop = None
        min_dist = float('inf')
        for stop in self.bus_stops:
            dist = calculate_distance(self.start_loc['lat'], self.start_loc['lng'], stop['lat'], stop['lng'])
            if dist < min_dist:
                min_dist = dist
                nearest_stop = stop
        
        # 실제로는 정류장 이름도 i18n 처리가 필요함
        stop_name = f"정류장 ID: {nearest_stop['stop_id']}" if nearest_stop else "주변에 없음"
        self.layout.addWidget(QLabel(f"가장 가까운 정류장: {stop_name} (약 {min_dist*1000:.0f}m)"))
        
        # 버스 번호 안내 (Mock)
        self.layout.addWidget(QLabel("탑승 버스 (예시): 79번, 165번"))

        # 온라인/오프라인 시뮬레이션
        self.net_checkbox = QCheckBox("네트워크 ON 시뮬레이션")
        self.net_checkbox.stateChanged.connect(self.update_bus_arrival_info)
        self.layout.addWidget(self.net_checkbox)

        self.arrival_info_label = QLabel()
        self.layout.addWidget(self.arrival_info_label)
        self.update_bus_arrival_info() # 초기 상태 설정

    def update_bus_arrival_info(self):
        if self.net_checkbox.isChecked():
            # Network On
            self.arrival_info_label.setText("[실시간 정보] 79번 버스: 5분 뒤 도착")
            self.arrival_info_label.setStyleSheet("color: blue;")
        else:
            # Network Off
            self.arrival_info_label.setText("[오프라인 정보] 15분 간격으로 운행")
            self.arrival_info_label.setStyleSheet("color: red;")


class KioskWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("전주 스마트 관광 키오스크 (API 연동 Demo)")
        self.setGeometry(100, 100, 700, 800)
        
        self.api_base_url = "http://127.0.0.1:8000"
        self.locations = []
        self.current_bus_stops = [] # 현재 지역의 버스 정류장 정보 저장
        self.current_lang = 'en'
        self.current_filter = "ALL"

        self.init_ui()
        self.load_initial_data()

    def init_ui(self):
        # (이전과 동일)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        header_layout = QHBoxLayout()
        self.location_combo = QComboBox()
        self.location_combo.currentTextChanged.connect(self.location_changed)
        lang_combo = QComboBox()
        lang_combo.addItems(['en', 'ko'])
        lang_combo.setCurrentText(self.current_lang)
        lang_combo.currentTextChanged.connect(self.lang_changed)
        header_layout.addWidget(QLabel("탐색 지역:"))
        header_layout.addWidget(self.location_combo, 1)
        header_layout.addWidget(QLabel("언어:"))
        header_layout.addWidget(lang_combo)
        main_layout.addLayout(header_layout)
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("필터:"))
        btn_all = QPushButton("전체 (All)"); btn_sights = QPushButton("관광 (Sights)"); btn_food = QPushButton("음식 (Food)")
        btn_all.clicked.connect(lambda: self.filter_changed("ALL"))
        btn_sights.clicked.connect(lambda: self.filter_changed("TOUR"))
        btn_food.clicked.connect(lambda: self.filter_changed("FOOD"))
        filter_layout.addWidget(btn_all); filter_layout.addWidget(btn_sights); filter_layout.addWidget(btn_food)
        filter_layout.addStretch()
        main_layout.addLayout(filter_layout)
        self.scroll_area = QScrollArea(); self.scroll_area.setWidgetResizable(True)
        main_layout.addWidget(self.scroll_area)
        self.scroll_content = QWidget()
        self.places_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)

    def load_initial_data(self):
        """
        앱 시작 시, /api/v1/locations API를 호출하여 지역 목록을 받아옵니다.
        """
        try:
            # --- 변경점: lang 파라미터 추가 ---
            response = requests.get(f"{self.api_base_url}/api/v1/locations", params={"lang": self.current_lang})
            response.raise_for_status()
            self.locations = response.json()
            
            # 콤보박스 내용 초기화 후 다시 채우기 (언어 변경 시에도 사용)
            self.location_combo.clear()
            for location in self.locations:
                self.location_combo.addItem(location['name'], userData=location)
            
            # 첫번째 지역으로 장소 목록 자동 로드 (연결된 location_changed가 호출됨)
            
        except requests.exceptions.RequestException as e:
            self.show_error_message(f"초기 지역 정보를 불러오는 데 실패했습니다.\nMock API 서버가 실행 중인지 확인하세요.\n\n오류: {e}")
            self.location_combo.addItem("서버 연결 실패")

    def lang_changed(self, lang):
        """언어 선택이 변경되었을 때 호출됩니다."""
        self.current_lang = lang
        self.load_initial_data() # --- 변경점: 언어 변경 시 지역 목록도 새로 로드 ---
        self.update_places_list() # 장소 목록도 새로 로드


    def update_places_list(self):
        # --- 변경점: 응답에서 버스 정류장 정보도 저장 ---
        current_idx = self.location_combo.currentIndex()
        if current_idx == -1: return
        selected_location = self.location_combo.itemData(current_idx)
        if not selected_location: return
        params = {"lat": selected_location.get('lat'), "lng": selected_location.get('lng'), "lang": self.current_lang}
        try:
            response = requests.get(f"{self.api_base_url}/api/v1/places/search", params=params)
            response.raise_for_status()
            data = response.json()
            places_data = data.get("searched_places", [])
            self.current_bus_stops = data.get("bus_stops", []) # 버스 정류장 정보 저장

            while self.places_layout.count():
                item = self.places_layout.takeAt(0)
                if item.widget(): item.widget().setParent(None)
            
            for place in places_data:
                 if self.current_filter == "ALL" or place.get('type') == self.current_filter:
                    card = PlaceCard(place, self.show_detail)
                    self.places_layout.addWidget(card)
            self.places_layout.addStretch()
        except requests.exceptions.RequestException as e:
            self.show_error_message(f"장소 정보를 불러오는 데 실패했습니다.\n\n오류: {e}")

    def show_detail(self, destination_place):
        """ --- 핵심 변경점: 길안내 다이얼로그 띄우기 --- """
        current_idx = self.location_combo.currentIndex()
        if current_idx == -1: return
        start_location = self.location_combo.itemData(current_idx)

        # 길안내 다이얼로그 생성 및 실행
        dialog = RouteGuidanceDialog(start_location, destination_place, self.current_bus_stops, self)
        dialog.exec()

    def show_error_message(self, message):
        # (이전과 동일)
        QMessageBox.critical(self, "API 연결 오류", message)

    def location_changed(self): self.update_places_list()
    def lang_changed(self, lang): self.current_lang = lang; self.update_places_list()
    def filter_changed(self, new_filter): self.current_filter = new_filter; self.update_places_list()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = KioskWindow()
    window.show()
    sys.exit(app.exec())

import sys
from pathlib import Path

from PyQt5.QtCore import Qt, QEvent, QSize, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QFontDatabase, QImage, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

APP_DIR = Path(__file__).resolve().parent
FONT_DIR = APP_DIR / "fonts"
TITLE_IMAGE = APP_DIR / "title.png"
PREFERRED_FAMILIES = [
    "Noto Sans CJK KR",
    "Noto Sans CJK JP",
    "Noto Sans CJK SC",
    "Noto Sans CJK TC",
    "Noto Sans",
]
FALLBACK_FAMILIES = [
    "Apple SD Gothic Neo",
    "Malgun Gothic",
    "Yu Gothic",
    "Hiragino Sans",
    "PingFang SC",
    "Microsoft YaHei",
    "Segoe UI",
    "Arial",
    "DejaVu Sans",
]


def _load_app_fonts() -> None:
    if not FONT_DIR.exists():
        return
    for ext in ("*.ttf", "*.otf", "*.ttc"):
        for font_path in FONT_DIR.glob(ext):
            QFontDatabase.addApplicationFont(str(font_path))


def _resolve_font_family() -> str:
    _load_app_fonts()
    available = set(QFontDatabase().families())
    for family in PREFERRED_FAMILIES + FALLBACK_FAMILIES:
        if family in available:
            return family
    return QApplication.font().family()


LANGUAGES = [
    "한국어",
    "English",
    "日本語",
    "简体中文",
    "繁體中文",
    "Deutsch",
    "Nederlands",
    "Svenska",
    "Français",
    "Italiano",
    "Español",
    "Português",
    "Русский",
    "Polski",
    "Čeština",
    "Українська",
    "Lietuvių",
    "Latviešu",
]

LANG_INFO = {
    "한국어": {
        "flags": "KR",
        "language_title": "언어",
        "tour": "관광지",
        "route": "길안내",
        "qr": "QR",
        "open": "열기",
        "route_input_title": "목적지 입력",
        "route_input_hint": "키보드를 눌러 목적지를 입력하세요.",
        "route_back": "뒤로",
        "route_result_title": "길 안내",
        "route_result_label": "목적지: {text}",
        "route_keyboard_space": "공백",
        "route_keyboard_back": "삭제",
        "route_keyboard_clear": "초기화",
        "route_keyboard_enter": "확인",
    },
    "English": {
        "flags": "US",
        "language_title": "Language",
        "tour": "Attractions",
        "route": "Directions",
        "qr": "QR",
        "open": "Open",
        "route_input_title": "Destination Input",
        "route_input_hint": "Tap keyboard to enter destination.",
        "route_back": "Back",
        "route_result_title": "Route Guidance",
        "route_result_label": "Destination: {text}",
        "route_keyboard_space": "Space",
        "route_keyboard_back": "Back",
        "route_keyboard_clear": "Clear",
        "route_keyboard_enter": "Enter",
    },
    "日本語": {
        "flags": "JP",
        "language_title": "言語",
        "tour": "観光地",
        "route": "道案内",
        "qr": "QR",
        "open": "開く",
        "route_input_title": "目的地入力",
        "route_input_hint": "キーボードをタップして目的地を入力してください。",
        "route_back": "戻る",
        "route_result_title": "道案内",
        "route_result_label": "目的地: {text}",
        "route_keyboard_space": "スペース",
        "route_keyboard_back": "削除",
        "route_keyboard_clear": "クリア",
        "route_keyboard_enter": "決定",
    },
    "简体中文": {
        "flags": "CN",
        "language_title": "语言",
        "tour": "景点",
        "route": "路线",
        "qr": "QR",
        "open": "打开",
        "route_input_title": "目的地输入",
        "route_input_hint": "点击键盘输入目的地。",
        "route_back": "返回",
        "route_result_title": "路线指引",
        "route_result_label": "目的地: {text}",
        "route_keyboard_space": "空格",
        "route_keyboard_back": "退格",
        "route_keyboard_clear": "清空",
        "route_keyboard_enter": "确定",
    },
    "繁體中文": {
        "flags": "TW",
        "language_title": "語言",
        "tour": "景點",
        "route": "路線",
        "qr": "QR",
        "open": "開啟",
        "route_input_title": "目的地輸入",
        "route_input_hint": "點擊鍵盤輸入目的地。",
        "route_back": "返回",
        "route_result_title": "路線指引",
        "route_result_label": "目的地: {text}",
        "route_keyboard_space": "空格",
        "route_keyboard_back": "退格",
        "route_keyboard_clear": "清除",
        "route_keyboard_enter": "確認",
    },
    "Deutsch": {
        "flags": "DE",
        "language_title": "Sprache",
        "tour": "Sehenswürdigkeiten",
        "route": "Wegbeschreibung",
        "qr": "QR",
        "open": "Öffnen",
        "route_input_title": "Ziel eingeben",
        "route_input_hint": "Tippen Sie auf die Tastatur, um das Ziel einzugeben.",
        "route_back": "Zurück",
        "route_result_title": "Routenführung",
        "route_result_label": "Ziel: {text}",
        "route_keyboard_space": "Leerzeichen",
        "route_keyboard_back": "Löschen",
        "route_keyboard_clear": "Leeren",
        "route_keyboard_enter": "Bestätigen",
    },
    "Nederlands": {
        "flags": "NL",
        "language_title": "Taal",
        "tour": "Bezienswaardigheden",
        "route": "Route",
        "qr": "QR",
        "open": "Openen",
        "route_input_title": "Bestemming invoeren",
        "route_input_hint": "Tik op het toetsenbord om de bestemming in te voeren.",
        "route_back": "Terug",
        "route_result_title": "Routebegeleiding",
        "route_result_label": "Bestemming: {text}",
        "route_keyboard_space": "Spatie",
        "route_keyboard_back": "Verwijder",
        "route_keyboard_clear": "Wissen",
        "route_keyboard_enter": "Bevestigen",
    },
    "Svenska": {
        "flags": "SE",
        "language_title": "Språk",
        "tour": "Sevärdheter",
        "route": "Vägbeskrivning",
        "qr": "QR",
        "open": "Öppna",
        "route_input_title": "Ange destination",
        "route_input_hint": "Tryck på tangentbordet för att ange destination.",
        "route_back": "Tillbaka",
        "route_result_title": "Vägbeskrivning",
        "route_result_label": "Destination: {text}",
        "route_keyboard_space": "Mellanslag",
        "route_keyboard_back": "Backsteg",
        "route_keyboard_clear": "Rensa",
        "route_keyboard_enter": "Bekräfta",
    },
    "Français": {
        "flags": "FR",
        "language_title": "Langue",
        "tour": "Sites touristiques",
        "route": "Itinéraire",
        "qr": "QR",
        "open": "Ouvrir",
        "route_input_title": "Saisir la destination",
        "route_input_hint": "Appuyez sur le clavier pour saisir la destination.",
        "route_back": "Retour",
        "route_result_title": "Guidage",
        "route_result_label": "Destination : {text}",
        "route_keyboard_space": "Espace",
        "route_keyboard_back": "Supprimer",
        "route_keyboard_clear": "Effacer",
        "route_keyboard_enter": "Valider",
    },
    "Italiano": {
        "flags": "IT",
        "language_title": "Lingua",
        "tour": "Attrazioni",
        "route": "Indicazioni",
        "qr": "QR",
        "open": "Apri",
        "route_input_title": "Inserisci destinazione",
        "route_input_hint": "Tocca la tastiera per inserire la destinazione.",
        "route_back": "Indietro",
        "route_result_title": "Indicazioni",
        "route_result_label": "Destinazione: {text}",
        "route_keyboard_space": "Spazio",
        "route_keyboard_back": "Cancella",
        "route_keyboard_clear": "Pulisci",
        "route_keyboard_enter": "Conferma",
    },
    "Español": {
        "flags": "ES",
        "language_title": "Idioma",
        "tour": "Atracciones",
        "route": "Indicaciones",
        "qr": "QR",
        "open": "Abrir",
        "route_input_title": "Ingresar destino",
        "route_input_hint": "Toque el teclado para introducir el destino.",
        "route_back": "Atrás",
        "route_result_title": "Guía de ruta",
        "route_result_label": "Destino: {text}",
        "route_keyboard_space": "Espacio",
        "route_keyboard_back": "Borrar",
        "route_keyboard_clear": "Limpiar",
        "route_keyboard_enter": "Aceptar",
    },
    "Português": {
        "flags": "PT",
        "language_title": "Idioma",
        "tour": "Atrações",
        "route": "Direções",
        "qr": "QR",
        "open": "Abrir",
        "route_input_title": "Inserir destino",
        "route_input_hint": "Toque no teclado para inserir o destino.",
        "route_back": "Voltar",
        "route_result_title": "Orientação de rota",
        "route_result_label": "Destino: {text}",
        "route_keyboard_space": "Espaço",
        "route_keyboard_back": "Apagar",
        "route_keyboard_clear": "Limpar",
        "route_keyboard_enter": "Confirmar",
    },
    "Русский": {
        "flags": "RU",
        "language_title": "Язык",
        "tour": "Достопримечательности",
        "route": "Маршрут",
        "qr": "QR",
        "open": "Открыть",
        "route_input_title": "Ввод пункта назначения",
        "route_input_hint": "Нажмите на клавиатуру, чтобы ввести пункт назначения.",
        "route_back": "Назад",
        "route_result_title": "Маршрут",
        "route_result_label": "Пункт назначения: {text}",
        "route_keyboard_space": "Пробел",
        "route_keyboard_back": "Удалить",
        "route_keyboard_clear": "Очистить",
        "route_keyboard_enter": "Подтвердить",
    },
    "Polski": {
        "flags": "PL",
        "language_title": "Język",
        "tour": "Atrakcje",
        "route": "Wskazówki",
        "qr": "QR",
        "open": "Otwórz",
        "route_input_title": "Wprowadź cel",
        "route_input_hint": "Dotknij klawiatury, aby wprowadzić cel.",
        "route_back": "Wstecz",
        "route_result_title": "Nawigacja",
        "route_result_label": "Cel: {text}",
        "route_keyboard_space": "Spacja",
        "route_keyboard_back": "Usuń",
        "route_keyboard_clear": "Wyczyść",
        "route_keyboard_enter": "Potwierdź",
    },
    "Čeština": {
        "flags": "CZ",
        "language_title": "Jazyk",
        "tour": "Památky",
        "route": "Trasa",
        "qr": "QR",
        "open": "Otevřít",
        "route_input_title": "Zadat cíl",
        "route_input_hint": "Klepněte na klávesnici a zadejte cíl.",
        "route_back": "Zpět",
        "route_result_title": "Navigace",
        "route_result_label": "Cíl: {text}",
        "route_keyboard_space": "Mezera",
        "route_keyboard_back": "Smazat",
        "route_keyboard_clear": "Vymazat",
        "route_keyboard_enter": "Potvrdit",
    },
    "Українська": {
        "flags": "UA",
        "language_title": "Мова",
        "tour": "Пам'ятки",
        "route": "Маршрут",
        "qr": "QR",
        "open": "Відкрити",
        "route_input_title": "Введення пункту призначення",
        "route_input_hint": "Натисніть клавіатуру, щоб ввести пункт призначення.",
        "route_back": "Назад",
        "route_result_title": "Маршрут",
        "route_result_label": "Пункт призначення: {text}",
        "route_keyboard_space": "Пробіл",
        "route_keyboard_back": "Видалити",
        "route_keyboard_clear": "Очистити",
        "route_keyboard_enter": "Підтвердити",
    },
    "Lietuvių": {
        "flags": "LT",
        "language_title": "Kalba",
        "tour": "Lankytinos vietos",
        "route": "Maršrutas",
        "qr": "QR",
        "open": "Atidaryti",
        "route_input_title": "Įvesti tikslą",
        "route_input_hint": "Palieskite klaviatūrą ir įveskite tikslą.",
        "route_back": "Atgal",
        "route_result_title": "Maršrutas",
        "route_result_label": "Tikslas: {text}",
        "route_keyboard_space": "Tarpas",
        "route_keyboard_back": "Trinti",
        "route_keyboard_clear": "Išvalyti",
        "route_keyboard_enter": "Patvirtinti",
    },
    "Latviešu": {
        "flags": "LV",
        "language_title": "Valoda",
        "tour": "Apskates vietas",
        "route": "Maršruts",
        "qr": "QR",
        "open": "Atvērt",
        "route_input_title": "Ievadīt galamērķi",
        "route_input_hint": "Pieskarieties tastatūrai, lai ievadītu galamērķi.",
        "route_back": "Atpakaļ",
        "route_result_title": "Maršruts",
        "route_result_label": "Galamērķis: {text}",
        "route_keyboard_space": "Atstarpe",
        "route_keyboard_back": "Dzēst",
        "route_keyboard_clear": "Notīrīt",
        "route_keyboard_enter": "Apstiprināt",
    },
}

def _lang_value(lang: str, key: str, default: str) -> str:
    fallback = LANG_INFO.get("English", {})
    info = LANG_INFO.get(lang, fallback)
    return info.get(key, fallback.get(key, default))


class LanguagePage(QFrame):
    def __init__(self, on_select):
        super().__init__()
        self.on_select = on_select
        self.title_label = None
        self.grid_layout = None
        self.layout_root = None
        self._build()

    def _build(self):
        self.layout_root = QVBoxLayout(self)
        self.layout_root.setContentsMargins(24, 24, 24, 24)
        self.layout_root.setSpacing(18)

        self.title_label = QLabel("Language")
        self.title_label.setObjectName("title")
        self.title_label.setAlignment(Qt.AlignCenter)

        grid_wrap = QFrame()
        self.grid_layout = QGridLayout(grid_wrap)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setHorizontalSpacing(12)
        self.grid_layout.setVerticalSpacing(4)

        for idx, lang in enumerate(LANGUAGES):
            btn = QPushButton(lang)
            btn.setObjectName("langBtn")
            btn.clicked.connect(lambda _checked, value=lang: self.on_select(value))
            row, col = divmod(idx, 3)
            self.grid_layout.addWidget(btn, row, col)

        self.layout_root.addWidget(self.title_label)
        self.layout_root.addWidget(grid_wrap, 1)

    def set_language(self, lang: str):
        info = LANG_INFO.get(lang, LANG_INFO["English"])
        self.title_label.setText(info["language_title"])

    def apply_scale(self, scale: float):
        if self.layout_root:
            margin = max(12, int(24 * scale))
            spacing = max(8, int(18 * scale))
            self.layout_root.setContentsMargins(margin, margin, margin, margin)
            self.layout_root.setSpacing(spacing)
        if self.grid_layout:
            self.grid_layout.setHorizontalSpacing(max(6, int(12 * scale)))
            self.grid_layout.setVerticalSpacing(max(2, int(4 * scale)))


class MenuPage(QFrame):
    def __init__(self, on_language_click, on_route_click):
        super().__init__()
        self.on_language_click = on_language_click
        self.on_route_click = on_route_click
        self.cards = []
        self.card_labels = {}
        self.lang_button = None
        self.qr_title = None
        self.qr_label = None
        self.qr_size = 260
        self.layout_root = None
        self.cards_layout = None
        self._build()

    def _build(self):
        self.layout_root = QVBoxLayout(self)
        self.layout_root.setContentsMargins(24, 24, 24, 24)
        self.layout_root.setSpacing(16)

        self.lang_button = QPushButton("Language")
        self.lang_button.setObjectName("langPill")
        self.lang_button.clicked.connect(self.on_language_click)
        self.layout_root.addWidget(self.lang_button, alignment=Qt.AlignLeft)

        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(16)

        top_card = self._build_card("tour")
        left_card = self._build_card("route")
        right_card = self._build_qr_card()
        self.cards = [top_card, left_card, right_card]

        self.cards_layout.addWidget(top_card, 1)
        self.cards_layout.addWidget(left_card, 1)
        self.cards_layout.addWidget(right_card, 1)

        self.layout_root.addStretch(1)
        self.layout_root.addLayout(self.cards_layout, 0)
        self.layout_root.addStretch(1)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def _build_card(self, key: str) -> QFrame:
        card = ClickableCard()
        card.setObjectName(f"card{key.capitalize()}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(12)

        label = QLabel("")
        label.setObjectName("cardTitle")
        label.setAlignment(Qt.AlignCenter)

        self.card_labels[key] = label
        card.clicked.connect(lambda _key=key: self._on_card_clicked(_key))

        card_layout.addStretch(1)
        card_layout.addWidget(label)
        card_layout.addStretch(1)
        return card

    def _build_qr_card(self) -> QFrame:
        card = SquareCard()
        card.setObjectName("cardQr")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(12)

        self.qr_title = QLabel("QR")
        self.qr_title.setObjectName("cardTitle")
        self.qr_title.setAlignment(Qt.AlignCenter)

        self.qr_label = QLabel()
        self.qr_label.setObjectName("qrLabel")
        self.qr_label.setAlignment(Qt.AlignCenter)
        qr_pixmap = self._build_qr_pixmap("https://www.google.com", self.qr_size)
        if qr_pixmap:
            self.qr_label.setPixmap(qr_pixmap)
        else:
            self.qr_label.setText("QR ?ï¿½ì± ë¶ï¿½?")

        card_layout.addStretch(1)
        card_layout.addWidget(self.qr_label, 0, alignment=Qt.AlignCenter)
        card_layout.addStretch(1)
        card_layout.addWidget(self.qr_title, 0, alignment=Qt.AlignCenter)
        return card

    def _build_qr_pixmap(self, url: str, size: int):
        try:
            import qrcode
            from PIL import Image
        except Exception:
            return None

        qr = qrcode.QRCode(border=1, box_size=10)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((size, size), Image.NEAREST)
        img = img.convert("RGBA")
        data = img.tobytes("raw", "RGBA")
        qimage = QImage(data, img.size[0], img.size[1], QImage.Format_RGBA8888)
        return QPixmap.fromImage(qimage)

    def set_language(self, lang: str):
        info = LANG_INFO.get(lang, LANG_INFO["English"])
        self.lang_button.setText(f"{lang}")
        self.card_labels["tour"].setText(info["tour"])
        self.card_labels["route"].setText(info["route"])
        if self.qr_title:
            self.qr_title.setText(info["qr"])

    def _on_card_clicked(self, key: str):
        if key == "route" and self.on_route_click:
            self.on_route_click()
            return
        # Placeholder for navigation; wire to the actual pages later.

    def apply_scale(self, scale: float):
        if self.layout_root:
            margin = max(12, int(24 * scale))
            spacing = max(8, int(16 * scale))
            self.layout_root.setContentsMargins(margin, margin, margin, margin)
            self.layout_root.setSpacing(spacing)
        if self.cards_layout:
            self.cards_layout.setSpacing(max(8, int(16 * scale)))
        side_target = max(120, int(400 * scale))
        margin = max(12, int(24 * scale))
        available_width = max(0, self.width() - (margin * 2))
        spacing = self.cards_layout.spacing() if self.cards_layout else 0
        max_side_from_width = (available_width - spacing * 2) // 3 if available_width > 0 else side_target
        lang_height = 0
        if self.lang_button:
            lang_height = max(self.lang_button.height(), self.lang_button.sizeHint().height())
        layout_spacing = self.layout_root.spacing() if self.layout_root else 0
        available_height = self.height() - (margin * 2) - lang_height - (layout_spacing * 2)
        max_side_from_height = max(0, available_height)
        width_limit = max_side_from_width if max_side_from_width > 0 else side_target
        height_limit = max_side_from_height if max_side_from_height > 0 else side_target
        side = min(side_target, width_limit, height_limit)
        side = max(80, side)
        for card in self.cards:
            card.setFixedSize(side, side)
        qr_target = max(100, int(260 * scale))
        qr_limit = max(48, side - max(24, int(36 * scale)))
        self.qr_size = min(qr_target, qr_limit)
        if self.qr_label:
            qr_pixmap = self._build_qr_pixmap("https://www.google.com", self.qr_size)
            if qr_pixmap:
                self.qr_label.setPixmap(qr_pixmap)


class MainWindow(QMainWindow):
    BASE_WIDTH = 1100
    BASE_HEIGHT = 760
    IDLE_TIMEOUT_MS = 10000
    DEFAULT_LANGUAGE = "English"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kiosk UI")
        self.resize(1100, 760)
        self.font_family = _resolve_font_family()
        self.current_language = self.DEFAULT_LANGUAGE
        self.idle_timer = QTimer(self)
        self.idle_timer.setSingleShot(True)
        self.idle_timer.timeout.connect(self._show_standby)
        self._build_ui()
        self._apply_style(1.0)
        self._apply_scale()
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)
        self._reset_idle_timer()
        self._show_standby()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.standby_page = StandbyPage(self._show_language)
        self.language_page = LanguagePage(self._on_language_select)
        self.route_input_page = RouteInputPage(
            on_submit=self._show_route_result,
            on_back=self._show_menu,
        )
        self.route_result_page = RouteResultPage(on_back=self._show_menu)
        self.menu_page = MenuPage(self._back_to_language, self._show_route_input)

        self.stack.addWidget(self.standby_page)
        self.stack.addWidget(self.language_page)
        self.stack.addWidget(self.route_input_page)
        self.stack.addWidget(self.route_result_page)
        self.stack.addWidget(self.menu_page)

    def _apply_style(self, scale: float):
        font = QFont(self.font_family)
        font.setPointSizeF(max(8, 10 * scale))
        self.setFont(font)
        self.setStyleSheet(
            f"""
            QMainWindow {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f5efe6, stop:0.55 #f1f4ff, stop:1 #e7f6f3);
            }}
            #title {{
                font-size: {max(14, int(22 * scale))}px;
                font-weight: 600;
                color: #111827;
            }}
            #langBtn {{
                background: #111827;
                color: #ffffff;
                border-radius: {max(8, int(12 * scale))}px;
                padding: {max(14, int(22 * scale))}px {max(8, int(13 * scale))}px;
                font-weight: 600;
            }}
            #langBtn:hover {{
                background: #1f2937;
            }}
            #card {{
                border-radius: {max(10, int(18 * scale))}px;
            }}
            #cardTour {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #fde68a, stop:1 #fb7185);
            }}
            #cardRoute {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #93c5fd, stop:1 #34d399);
            }}
            #cardQr {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #c4b5fd, stop:1 #f9a8d4);
            }}
            #cardTitle {{
                font-size: {max(12, int(18 * scale))}px;
                font-weight: 600;
                color: #111827;
            }}
            #navBtn {{
                background: #1d4ed8;
                color: #ffffff;
                border-radius: {max(8, int(12 * scale))}px;
                padding: {max(6, int(10 * scale))}px {max(10, int(16 * scale))}px;
                font-weight: 600;
            }}
            #navBtn:hover {{
                background: #2563eb;
            }}
            #langPill {{
                background: #111827;
                color: #ffffff;
                border-radius: {max(10, int(14 * scale))}px;
                padding: {max(6, int(8 * scale))}px {max(10, int(14 * scale))}px;
                font-weight: 600;
            }}
            #langPill:hover {{
                background: #1f2937;
            }}
            #qrLabel {{
                color: #94a3b8;
                font-size: {max(10, int(16 * scale))}px;
                font-weight: 600;
            }}
            #keyBtn {{
                background: #ffffff;
                color: #111827;
                border: 1px solid #d1d5db;
                border-radius: {max(6, int(10 * scale))}px;
                padding: {max(10, int(16 * scale))}px {max(8, int(12 * scale))}px;
                min-height: {max(36, int(48 * scale))}px;
                font-weight: 600;
            }}
            #keyBtn:hover {{
                background: #f3f4f6;
            }}
            #inputField {{
                background: #ffffff;
                color: #111827;
                border: 1px solid #d1d5db;
                border-radius: {max(8, int(12 * scale))}px;
                padding: {max(10, int(14 * scale))}px;
                font-size: {max(12, int(18 * scale))}px;
            }}
            #statusLabel {{
                color: #6b7280;
                font-size: {max(10, int(14 * scale))}px;
            }}
            #destinationLabel {{
                color: #111827;
                font-size: {max(12, int(20 * scale))}px;
                font-weight: 600;
            }}
            """
        )

    def _on_language_select(self, lang: str):
        self.current_language = lang
        self.menu_page.set_language(lang)
        self.language_page.set_language(lang)
        self.route_input_page.set_language(lang)
        self.route_result_page.set_language(lang)
        self.stack.setCurrentWidget(self.menu_page)
        QTimer.singleShot(0, self._apply_scale)

    def _back_to_language(self):
        self.stack.setCurrentWidget(self.language_page)

    def _show_menu(self):
        self.stack.setCurrentWidget(self.menu_page)
        QTimer.singleShot(0, self._apply_scale)

    def _show_route_input(self):
        self.stack.setCurrentWidget(self.route_input_page)
        QTimer.singleShot(0, self._apply_scale)

    def _show_route_result(self, destination: str):
        self.route_result_page.set_destination(destination)
        self.stack.setCurrentWidget(self.route_result_page)
        QTimer.singleShot(0, self._apply_scale)

    def _show_language(self):
        self.stack.setCurrentWidget(self.language_page)
        QTimer.singleShot(0, self._apply_scale)

    def _show_standby(self):
        self._reset_to_initial_state()
        self.stack.setCurrentWidget(self.standby_page)
        QTimer.singleShot(0, self._apply_scale)

    def _reset_to_initial_state(self):
        self.current_language = self.DEFAULT_LANGUAGE
        self.menu_page.set_language(self.DEFAULT_LANGUAGE)
        self.language_page.set_language(self.DEFAULT_LANGUAGE)
        self.route_input_page.reset_state()
        self.route_input_page.set_language(self.DEFAULT_LANGUAGE)
        self.route_result_page.set_language(self.DEFAULT_LANGUAGE)

    def _reset_idle_timer(self):
        self.idle_timer.start(self.IDLE_TIMEOUT_MS)

    def eventFilter(self, source, event):
        if event.type() in (
            QEvent.MouseButtonPress,
            QEvent.MouseMove,
            QEvent.Wheel,
            QEvent.TouchBegin,
            QEvent.KeyPress,
        ):
            self._reset_idle_timer()
        return super().eventFilter(source, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_scale()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._apply_scale)

    def _apply_scale(self):
        w = max(1, self.width())
        h = max(1, self.height())
        scale = min(w / self.BASE_WIDTH, h / self.BASE_HEIGHT)
        self._apply_style(scale)
        self.standby_page.apply_scale(scale)
        self.language_page.apply_scale(scale)
        self.route_input_page.apply_scale(scale)
        self.route_result_page.apply_scale(scale)
        self.menu_page.apply_scale(scale)


class SquareCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return width


class ClickableCard(SquareCard):
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class KeyboardButton(QPushButton):
    def __init__(self, label: str):
        super().__init__(label)
        self.setObjectName("keyBtn")
        self.setCursor(Qt.PointingHandCursor)


class OnScreenKeyboard(QFrame):
    def __init__(self, on_key, on_backspace, on_clear, on_enter):
        super().__init__()
        self.on_key = on_key
        self.on_backspace = on_backspace
        self.on_clear = on_clear
        self.on_enter = on_enter
        self.space_btn = None
        self.back_btn = None
        self.clear_btn = None
        self.enter_btn = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        rows = [
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", ("Back", "backspace")],
            list("QWERTYUIOP[]\\"),
            list("ASDFGHJKL;'") + [("Enter", "enter")],
            list("ZXCVBNM,./"),
        ]
        row_padding = {
            2: 1,
            3: 2,
        }
        for row_index, row in enumerate(rows):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(6)
            pad = row_padding.get(row_index, 0)
            if pad:
                row_layout.addStretch(pad)
            for key in row:
                if isinstance(key, tuple):
                    label, action = key
                    btn = KeyboardButton(label)
                    if action == "backspace":
                        self.back_btn = btn
                        btn.clicked.connect(self.on_backspace)
                    elif action == "enter":
                        self.enter_btn = btn
                        btn.clicked.connect(self.on_enter)
                    row_layout.addWidget(btn, 1)
                else:
                    btn = KeyboardButton(key)
                    btn.clicked.connect(lambda _checked, value=key: self.on_key(value))
                    row_layout.addWidget(btn, 1)
            if pad:
                row_layout.addStretch(pad)
            layout.addLayout(row_layout)

        action_row = QHBoxLayout()
        action_row.setSpacing(6)

        self.space_btn = KeyboardButton("Space")
        self.space_btn.clicked.connect(lambda: self.on_key(" "))
        action_row.addWidget(self.space_btn, 4)

        self.clear_btn = KeyboardButton("Clear")
        self.clear_btn.clicked.connect(self.on_clear)
        action_row.addWidget(self.clear_btn, 1)

        layout.addLayout(action_row)


class RouteInputPage(QFrame):
    def __init__(self, on_submit, on_back):
        super().__init__()
        self.on_submit = on_submit
        self.on_back = on_back
        self.title_label = None
        self.input_field = None
        self.keyboard = None
        self.back_button = None
        self._current_language = "English"
        self._hint_text = ""
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(12)
        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("navBtn")
        self.back_button.clicked.connect(self._handle_back)
        header.addWidget(self.back_button, 0)

        self.title_label = QLabel("Destination Input")
        self.title_label.setObjectName("title")
        self.title_label.setAlignment(Qt.AlignCenter)
        header.addWidget(self.title_label, 1)
        header.addSpacing(60)
        layout.addLayout(header)

        self.input_field = QLabel("")
        self.input_field.setObjectName("inputField")
        self.input_field.setMinimumHeight(52)
        self.input_field.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.input_field.setText("Tap keyboard to enter destination.")
        layout.addWidget(self.input_field)

        self.keyboard = OnScreenKeyboard(
            on_key=self._handle_key,
            on_backspace=self._handle_backspace,
            on_clear=self._handle_clear,
            on_enter=self._handle_enter,
        )
        layout.addWidget(self.keyboard, 1)

        self.set_language("English")

    def apply_scale(self, scale: float):
        margin = max(12, int(24 * scale))
        spacing = max(8, int(12 * scale))
        layout = self.layout()
        if layout:
            layout.setContentsMargins(margin, margin, margin, margin)
            layout.setSpacing(spacing)

    def reset_state(self):
        if self.input_field:
            self.input_field.setText(self._hint_text or "Tap keyboard to enter destination.")

    def set_language(self, lang: str):
        self._current_language = lang
        title = _lang_value(lang, "route_input_title", "Destination Input")
        hint = _lang_value(lang, "route_input_hint", "Tap keyboard to enter destination.")
        back = _lang_value(lang, "route_back", "Back")
        self._hint_text = hint
        if self.title_label:
            self.title_label.setText(title)
        if self.input_field:
            current = self._get_input_text()
            self.input_field.setText(current if current else hint)
        if self.back_button:
            self.back_button.setText(back)
        if self.keyboard:
            space = _lang_value(lang, "route_keyboard_space", "Space")
            back_key = _lang_value(lang, "route_keyboard_back", "Back")
            clear = _lang_value(lang, "route_keyboard_clear", "Clear")
            enter = _lang_value(lang, "route_keyboard_enter", "Enter")
            if self.keyboard.space_btn:
                self.keyboard.space_btn.setText(space)
            if self.keyboard.back_btn:
                self.keyboard.back_btn.setText(back_key)
            if self.keyboard.clear_btn:
                self.keyboard.clear_btn.setText(clear)
            if self.keyboard.enter_btn:
                self.keyboard.enter_btn.setText(enter)

    def _handle_back(self):
        if self.on_back:
            self.on_back()

    def _handle_key(self, value: str):
        if not self.input_field:
            return
        current = self._get_input_text()
        self.input_field.setText(f"{current}{value}")

    def _handle_backspace(self):
        if not self.input_field:
            return
        current = self._get_input_text()
        self.input_field.setText(current[:-1])

    def _handle_clear(self):
        if self.input_field:
            self.input_field.setText("")

    def _handle_enter(self):
        text = self._get_input_text()
        if self.on_submit:
            self.on_submit(text)

    def _get_input_text(self) -> str:
        text = self.input_field.text() if self.input_field else ""
        if text == self._hint_text or text == "Tap keyboard to enter destination.":
            return ""
        return text


class RouteResultPage(QFrame):
    def __init__(self, on_back):
        super().__init__()
        self.on_back = on_back
        self.title_label = None
        self.destination_label = None
        self.back_button = None
        self._current_language = "English"
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("navBtn")
        self.back_button.clicked.connect(self._handle_back)
        layout.addWidget(self.back_button, alignment=Qt.AlignLeft)

        self.title_label = QLabel("Route Guidance")
        self.title_label.setObjectName("title")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        self.destination_label = QLabel("Destination: -")
        self.destination_label.setObjectName("destinationLabel")
        self.destination_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.destination_label, 1)

    def apply_scale(self, scale: float):
        layout = self.layout()
        if layout:
            layout.setContentsMargins(max(12, int(24 * scale)), max(12, int(24 * scale)),
                                      max(12, int(24 * scale)), max(12, int(24 * scale)))
            layout.setSpacing(max(8, int(12 * scale)))

    def set_destination(self, destination: str):
        text = destination.strip() if destination else "-"
        template = _lang_value(self._current_language, "route_result_label", "Destination: {text}")
        self.destination_label.setText(template.format(text=text))

    def set_language(self, lang: str):
        self._current_language = lang
        if self.title_label:
            self.title_label.setText(_lang_value(lang, "route_result_title", "Route Guidance"))
        if self.back_button:
            self.back_button.setText(_lang_value(lang, "route_back", "Back"))
        current = self.destination_label.text() if self.destination_label else ""
        if current:
            if ":" in current:
                current_text = current.split(":", 1)[-1].strip()
            else:
                current_text = current
        else:
            current_text = "-"
        template = _lang_value(lang, "route_result_label", "Destination: {text}")
        if self.destination_label:
            self.destination_label.setText(template.format(text=current_text))

    def _handle_back(self):
        if self.on_back:
            self.on_back()


class StandbyPage(QFrame):
    def __init__(self, on_activate):
        super().__init__()
        self.on_activate = on_activate
        self.image_label = None
        self._pixmap = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_label.setScaledContents(True)
        layout.addWidget(self.image_label, 1)

        if TITLE_IMAGE.exists():
            self._pixmap = QPixmap(str(TITLE_IMAGE))
        else:
            self.image_label.setText("Missing title.png")

    def apply_scale(self, scale: float):
        self._update_pixmap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_pixmap()

    def sizeHint(self):
        return QSize(0, 0)

    def minimumSizeHint(self):
        return QSize(0, 0)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.on_activate:
            self.on_activate()
        super().mousePressEvent(event)

    def _update_pixmap(self):
        if not self._pixmap or not self.image_label:
            return
        target_size = self.image_label.size()
        if target_size.width() <= 0 or target_size.height() <= 0:
            return
        scaled = self._pixmap.scaled(
            target_size,
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())



import sys
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QImage, QPixmap
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
    "한국어": {"flags": "🇰🇷", "language_title": "언어 선택", "tour": "관광지 안내", "route": "길 안내", "qr": "QR", "open": "열기"},
    "English": {"flags": "🇺🇸", "language_title": "Language", "tour": "Attractions", "route": "Directions", "qr": "QR", "open": "Open"},
    "日本語": {"flags": "🇯🇵", "language_title": "言語", "tour": "観光案内", "route": "道案内", "qr": "QR", "open": "開く"},
    "简体中文": {"flags": "🇨🇳", "language_title": "语言", "tour": "景点导览", "route": "路线指引", "qr": "二维码", "open": "打开"},
    "繁體中文": {"flags": "🇹🇼", "language_title": "語言", "tour": "景點導覽", "route": "路線指引", "qr": "QR", "open": "開啟"},
    "Deutsch": {"flags": "🇩🇪", "language_title": "Sprache", "tour": "Sehenswürdigkeiten", "route": "Wegbeschreibung", "qr": "QR", "open": "Öffnen"},
    "Nederlands": {"flags": "🇳🇱", "language_title": "Taal", "tour": "Attracties", "route": "Route", "qr": "QR", "open": "Openen"},
    "Svenska": {"flags": "🇸🇪", "language_title": "Språk", "tour": "Sevärdheter", "route": "Vägbeskrivning", "qr": "QR", "open": "Öppna"},
    "Français": {"flags": "🇫🇷", "language_title": "Langue", "tour": "Sites touristiques", "route": "Itinéraire", "qr": "QR", "open": "Ouvrir"},
    "Italiano": {"flags": "🇮🇹", "language_title": "Lingua", "tour": "Attrazioni", "route": "Indicazioni", "qr": "QR", "open": "Apri"},
    "Español": {"flags": "🇪🇸", "language_title": "Idioma", "tour": "Atracciones", "route": "Indicaciones", "qr": "QR", "open": "Abrir"},
    "Português": {"flags": "🇵🇹", "language_title": "Idioma", "tour": "Atrações", "route": "Direções", "qr": "QR", "open": "Abrir"},
    "Русский": {"flags": "🇷🇺", "language_title": "Язык", "tour": "Достопримечательности", "route": "Маршрут", "qr": "QR", "open": "Открыть"},
    "Polski": {"flags": "🇵🇱", "language_title": "Język", "tour": "Atrakcje", "route": "Wskazówki", "qr": "QR", "open": "Otwórz"},
    "Čeština": {"flags": "🇨🇿", "language_title": "Jazyk", "tour": "Památky", "route": "Trasa", "qr": "QR", "open": "Otevřít"},
    "Українська": {"flags": "🇺🇦", "language_title": "Мова", "tour": "Пам’ятки", "route": "Маршрут", "qr": "QR", "open": "Відкрити"},
    "Lietuvių": {"flags": "🇱🇹", "language_title": "Kalba", "tour": "Lankytinos vietos", "route": "Maršrutas", "qr": "QR", "open": "Atidaryti"},
    "Latviešu": {"flags": "🇱🇻", "language_title": "Valoda", "tour": "Apskates vietas", "route": "Maršruts", "qr": "QR", "open": "Atvērt"},
}


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
    def __init__(self, on_language_click):
        super().__init__()
        self.on_language_click = on_language_click
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
            self.qr_label.setText("QR 생성 불가")

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
        # Placeholder for navigation; wire to the actual pages later.
        pass

    def apply_scale(self, scale: float):
        if self.layout_root:
            margin = max(12, int(24 * scale))
            spacing = max(8, int(16 * scale))
            self.layout_root.setContentsMargins(margin, margin, margin, margin)
            self.layout_root.setSpacing(spacing)
        if self.cards_layout:
            self.cards_layout.setSpacing(max(8, int(16 * scale)))
        side_target = max(240, int(400 * scale))
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
        side = min(side_target, max_side_from_width or side_target, max_side_from_height or side_target)
        for card in self.cards:
            card.setFixedSize(side, side)
        qr_target = max(160, int(260 * scale))
        qr_limit = max(60, side - max(24, int(36 * scale)))
        self.qr_size = min(qr_target, qr_limit)
        if self.qr_label:
            qr_pixmap = self._build_qr_pixmap("https://www.google.com", self.qr_size)
            if qr_pixmap:
                self.qr_label.setPixmap(qr_pixmap)


class MainWindow(QMainWindow):
    BASE_WIDTH = 1100
    BASE_HEIGHT = 760

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kiosk UI")
        self.resize(1100, 760)
        self._build_ui()
        self._apply_style(1.0)
        self._apply_scale()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.language_page = LanguagePage(self._on_language_select)
        self.menu_page = MenuPage(self._back_to_language)

        self.stack.addWidget(self.language_page)
        self.stack.addWidget(self.menu_page)

    def _apply_style(self, scale: float):
        font = QFont("Poppins")
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
            """
        )

    def _on_language_select(self, lang: str):
        self.menu_page.set_language(lang)
        self.language_page.set_language(lang)
        self.stack.setCurrentWidget(self.menu_page)
        QTimer.singleShot(0, self._apply_scale)

    def _back_to_language(self):
        self.stack.setCurrentWidget(self.language_page)

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
        self.language_page.apply_scale(scale)
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

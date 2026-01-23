
from pathlib import Path

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import (
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
)
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QWidget,
    QVBoxLayout,
)

from .helpers import (
    _get_cached_pixmap,
    _lang_value,
    _place_lang_code,
    _resolve_place_image_path,
    _set_back_button_icon,
)


class TourPage(QFrame):
    def __init__(self, on_back, on_select, places: list):
        super().__init__()
        self.on_back = on_back
        self.on_select = on_select
        self.places = places
        self.language = "English"
        self.back_button = None
        self.title_label = None
        self.scroll_area = None
        self.list_widget = None
        self.list_layout = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        self.back_button = QPushButton()
        self.back_button.setObjectName("backBtn")
        self.back_button.setFixedSize(48, 48)
        self.back_button.clicked.connect(self.on_back)
        _set_back_button_icon(self.back_button, "Back")
        header_layout.addWidget(self.back_button)

        self.title_label = QLabel("Tour")
        self.title_label.setObjectName("title")
        self.title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.title_label, 1)
        header_layout.addSpacing(48)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(12, 12, 12, 12)
        self.list_layout.setSpacing(16)
        self._render_places()

        self.scroll_area.setWidget(self.list_widget)

        layout.addWidget(header_frame)
        layout.addWidget(self.scroll_area, 1)

    def _category_title(self, category: str) -> str:
        is_ko = _place_lang_code(self.language) == "ko"
        labels = {
            "heritage": ("Heritage", "전통/역사"),
            "culture": ("Culture", "문화/체험"),
            "nature": ("Nature", "자연/공원"),
            "market": ("Market", "시장/먹거리"),
            "other": ("Other", "기타"),
        }
        en_label, ko_label = labels.get(category, labels["other"])
        return ko_label if is_ko else en_label

    def _group_places(self):
        order = ["heritage", "culture", "nature", "market", "other"]
        groups = {key: [] for key in order}
        for place in self.places:
            category = place.get("category") or "other"
            if category not in groups:
                category = "other"
            groups[category].append(place)
        return [(key, groups[key]) for key in order if groups[key]]

    def _clear_layout(self, layout: QVBoxLayout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _render_places(self):
        if not self.list_layout:
            return
        self._clear_layout(self.list_layout)
        grouped = self._group_places()
        num_cols = 3
        for category, places in grouped:
            title = QLabel(self._category_title(category))
            title.setObjectName("sectionTitle")
            self.list_layout.addWidget(title)

            grid_wrap = QWidget()
            grid_layout = QGridLayout(grid_wrap)
            grid_layout.setContentsMargins(0, 0, 0, 0)
            grid_layout.setSpacing(12)

            for idx, place in enumerate(places):
                item = self._build_place_item(place)
                row, col = divmod(idx, num_cols)
                grid_layout.addWidget(item, row, col)

            self.list_layout.addWidget(grid_wrap)

    def _build_place_item(self, place: dict):
        item = QFrame()
        item.setObjectName("placeCard")
        item.setMinimumSize(200, 220)
        item.mousePressEvent = lambda event: self.on_select(place, event)

        layout = QVBoxLayout(item)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        class ImageLabel(QLabel):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.pixmap = None
                self.setMinimumHeight(120)

            def set_pixmap(self, pixmap: QPixmap):
                self.pixmap = pixmap
                self.update()

            def paintEvent(self, event):
                if not self.pixmap:
                    return
                painter = QPainter(self)
                painter.setRenderHint(QPainter.Antialiasing, True)
                path = QPainterPath()
                path.addRoundedRect(0, 0, self.width(), self.height(), 10, 10)
                painter.setClipPath(path)
                scaled_pixmap = self.pixmap.scaled(
                    self.size(),
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation,
                )
                point = self.rect().center() - scaled_pixmap.rect().center()
                painter.drawPixmap(point, scaled_pixmap)

        image = ImageLabel()
        image.setObjectName("placeImage")
        image_path = _resolve_place_image_path(place.get("image_url"))
        if image_path:
            pixmap = _get_cached_pixmap(image_path, QSize(200, 120), keep_aspect=False)
            if pixmap:
                image.set_pixmap(pixmap)
        layout.addWidget(image, 1)

        text_frame = QFrame()
        text_layout = QVBoxLayout(text_frame)
        text_layout.setContentsMargins(10, 8, 10, 8)
        text_layout.setSpacing(4)

        name_label = QLabel(place.get("fallback_name"))
        name_label.setObjectName("placeName")
        name_label.setWordWrap(True)

        desc_label = QLabel(place.get("fallback_desc"))
        desc_label.setObjectName("placeDesc")
        desc_label.setWordWrap(True)
        desc_label.hide()

        text_layout.addWidget(name_label)
        text_layout.addWidget(desc_label)
        text_layout.addStretch(1)
        layout.addWidget(text_frame)

        item.setProperty("place_id", place.get("place_id"))
        return item

    def set_language(self, lang: str):
        self.language = lang
        title = _lang_value(lang, "tour", "Attractions")
        self.title_label.setText(title)
        back_tooltip = _lang_value(lang, "route_back", "Back")
        _set_back_button_icon(self.back_button, back_tooltip)
        self._render_places()

    def apply_scale(self, scale: float):
        self.layout().setContentsMargins(
            max(8, int(12 * scale)),
            max(8, int(12 * scale)),
            max(8, int(12 * scale)),
            max(8, int(12 * scale)),
        )
        self.layout().setSpacing(max(8, int(12 * scale)))
        header_layout = self.findChild(QFrame).layout()
        header_layout.setSpacing(max(8, int(12 * scale)))
        back_button = self.findChild(QPushButton, "backBtn")
        if back_button:
            size = max(36, int(48 * scale))
            back_button.setFixedSize(size, size)
        if self.list_layout:
            self.list_layout.setSpacing(max(10, int(16 * scale)))
        for i in range(self.list_widget.layout().count()):
            container = self.list_widget.layout().itemAt(i).widget()
            if not container:
                continue
            inner_layout = container.layout()
            if isinstance(inner_layout, QGridLayout):
                inner_layout.setSpacing(max(8, int(12 * scale)))
                for idx in range(inner_layout.count()):
                    item = inner_layout.itemAt(idx).widget()
                    if item:
                        item.setMinimumSize(max(160, int(200 * scale)), max(180, int(220 * scale)))

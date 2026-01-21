from PyQt5.QtCore import Qt, QSize, QRect
from PyQt5.QtGui import (
    QFont,
    QColor,
    QLinearGradient,
    QPainter,
    QPixmap,
    QPen,
)
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from .helpers import (
    _build_qr_pixmap,
    _lang_value,
    _set_back_button_icon,
    STAMP_POSTER_IMAGE,
    STAMP_QR_URL,
)


class TravelStampPage(QFrame):
    def __init__(self, on_back):
        super().__init__()
        self.on_back = on_back
        self.back_button = None
        self.title_label = None
        self.qr_card = None
        self.qr_label = None
        self.qr_hint_label = None
        self.poster_card = None
        self.poster_label = None
        self.desc_label = None
        self.content_layout = None
        self.qr_size = 220
        self._fallback_qr_size = 220
        self.poster_size = QSize(420, 520)
        self._poster_signature = None
        self._current_language = "English"
        self._build()
        self.set_language("English")

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(12)
        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("navBtn")
        _set_back_button_icon(self.back_button, "Back")
        self.back_button.clicked.connect(self._handle_back)
        header.addWidget(self.back_button, 0)

        self.title_label = QLabel("Travel Stamp")
        self.title_label.setObjectName("title")
        self.title_label.setAlignment(Qt.AlignCenter)
        header.addWidget(self.title_label, 1)
        header.addSpacing(60)
        layout.addLayout(header)

        self.content_layout = QHBoxLayout()
        self.content_layout.setSpacing(16)

        self.poster_card = QFrame()
        self.poster_card.setStyleSheet("background: transparent; border: none;")
        self.poster_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        poster_layout = QVBoxLayout(self.poster_card)
        poster_layout.setContentsMargins(0, 0, 0, 0)
        poster_layout.setSpacing(10)

        self.poster_label = QLabel()
        self.poster_label.setAlignment(Qt.AlignCenter)
        self.poster_label.setScaledContents(False)
        self.poster_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.poster_label.setMinimumSize(0, 0)
        poster_layout.addWidget(self.poster_label, 1, alignment=Qt.AlignCenter)

        self.qr_card = QFrame()
        self.qr_card.setObjectName("qrCard")
        self.qr_card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        qr_layout = QVBoxLayout(self.qr_card)
        qr_layout.setContentsMargins(12, 12, 12, 12)
        qr_layout.setSpacing(8)

        self.qr_label = QLabel(
            _lang_value("English", "route_qr_unavailable", "QR unavailable.")
        )
        self.qr_label.setObjectName("routeQr")
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.qr_label.setMinimumSize(0, 0)
        qr_layout.addWidget(self.qr_label, 1)

        self.qr_hint_label = QLabel("")
        self.qr_hint_label.setObjectName("routeQrHint")
        self.qr_hint_label.setAlignment(Qt.AlignCenter)
        self.qr_hint_label.setWordWrap(True)
        qr_layout.addWidget(self.qr_hint_label)

        self.desc_label = QLabel("")
        self.desc_label.setObjectName("infoDesc")
        self.desc_label.setWordWrap(True)
        self.desc_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        qr_layout.addWidget(self.desc_label, 0)

        self.content_layout.addWidget(self.poster_card, 3)
        self.content_layout.addWidget(self.qr_card, 2)
        layout.addLayout(self.content_layout, 1)

    def apply_scale(self, scale: float):
        layout = self.layout()
        if layout:
            margin = max(12, int(24 * scale))
            spacing = max(8, int(12 * scale))
            layout.setContentsMargins(margin, margin, margin, margin)
            layout.setSpacing(spacing)
        self._fallback_qr_size = max(180, int(240 * scale))
        self.qr_size = self._fallback_qr_size
        self.poster_size = QSize(
            max(260, int(420 * scale)), max(300, int(520 * scale))
        )
        self._refresh_qr()
        self._refresh_poster()

    def set_language(self, lang: str):
        self._current_language = lang
        if self.title_label:
            self.title_label.setText(
                _lang_value(lang, "travel_stamp_title", "Travel Stamp")
            )
        if self.back_button:
            _set_back_button_icon(
                self.back_button, _lang_value(lang, "route_back", "Back")
            )
        if self.qr_hint_label:
            self.qr_hint_label.setText(
                _lang_value(lang, "travel_stamp_qr_hint", "Scan to join")
            )
        if self.desc_label:
            lines = self._stamp_lines()
            self.desc_label.setText("\n".join(lines))
        self._refresh_poster()
        self._refresh_qr()

    def _stamp_lines(self):
        return [
            _lang_value(
                self._current_language,
                "travel_stamp_line1",
                "Scan the QR to start your stamp tour.",
            ),
            _lang_value(
                self._current_language,
                "travel_stamp_line2",
                "Collect stamps as you visit attractions.",
            ),
            _lang_value(
                self._current_language,
                "travel_stamp_line3",
                "Complete missions to earn rewards.",
            ),
        ]

    def _refresh_qr(self):
        if not self.qr_label:
            return
        target_size = self._calculate_qr_size()
        if target_size > 0:
            self.qr_size = target_size
        pixmap = _build_qr_pixmap(STAMP_QR_URL, self.qr_size)
        if pixmap:
            self.qr_label.setPixmap(pixmap)
            self.qr_label.setText("")
        else:
            self.qr_label.setPixmap(QPixmap())
            self.qr_label.setText(
                _lang_value(self._current_language, "route_qr_unavailable", "QR unavailable.")
            )

    def _refresh_poster(self):
        if not self.poster_label:
            return
        target_size = QSize(0, 0)
        if self.poster_card and self.poster_card.layout():
            card_size = self.poster_card.size()
            margins = self.poster_card.layout().contentsMargins()
            inner_w = card_size.width() - margins.left() - margins.right()
            inner_h = card_size.height() - margins.top() - margins.bottom()
            target_size = QSize(max(0, inner_w), max(0, inner_h))
        if (
            not target_size.isValid()
            or target_size.width() <= 0
            or target_size.height() <= 0
        ):
            target_size = self.poster_label.size()
        if (
            not target_size.isValid()
            or target_size.width() <= 0
            or target_size.height() <= 0
        ):
            target_size = self.poster_size if self.poster_size.isValid() else QSize(0, 0)
        if (
            not target_size.isValid()
            or target_size.width() <= 0
            or target_size.height() <= 0
        ):
            return
        signature = (target_size.width(), target_size.height(), self._current_language)
        if signature == self._poster_signature:
            return
        pixmap = self._load_poster_pixmap(target_size)
        if pixmap is None:
            pixmap = self._build_poster_pixmap(target_size)
        if pixmap:
            self.poster_label.setPixmap(pixmap)
            self._poster_signature = signature

    def _calculate_qr_size(self) -> int:
        if not self.qr_label:
            return self._fallback_qr_size
        label_size = self.qr_label.size()
        if (
            not label_size.isValid()
            or label_size.width() <= 0
            or label_size.height() <= 0
        ):
            return self._fallback_qr_size
        return max(80, int(min(label_size.width(), label_size.height())))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_qr()
        self._refresh_poster()

    def _load_poster_pixmap(self, size: QSize):
        if not STAMP_POSTER_IMAGE.exists():
            return None
        pixmap = QPixmap(str(STAMP_POSTER_IMAGE))
        if pixmap.isNull():
            return None
        return pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def _build_poster_pixmap(self, size: QSize) -> QPixmap:
        pixmap = QPixmap(size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = QRect(0, 0, size.width(), size.height())
        gradient = QLinearGradient(0, 0, 0, size.height())
        gradient.setColorAt(0, QColor("#fff7e1"))
        gradient.setColorAt(1, QColor("#e7f6f3"))
        painter.fillRect(rect, gradient)

        pen = QPen(QColor("#e5e7eb"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 18, 18)

        circle_size = int(min(size.width(), size.height()) * 0.22)
        circle_rect = QRect(
            int(size.width() * 0.08),
            int(size.height() * 0.08),
            circle_size,
            circle_size,
        )
        painter.setPen(QPen(QColor("#f97316"), 3))
        painter.setBrush(QColor("#ffedd5"))
        painter.drawEllipse(circle_rect)

        circle_font = QFont(self.font().family(), max(10, int(size.width() * 0.035)))
        circle_font.setBold(True)
        painter.setFont(circle_font)
        painter.setPen(QColor("#9a3412"))
        painter.drawText(circle_rect, Qt.AlignCenter, "STAMP")

        title_font = QFont(self.font().family(), max(14, int(size.width() * 0.055)))
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor("#111827"))
        title_rect = QRect(
            int(size.width() * 0.08),
            circle_rect.bottom() + int(size.height() * 0.04),
            int(size.width() * 0.84),
            int(size.height() * 0.18),
        )
        painter.drawText(
            title_rect,
            Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap,
            _lang_value(
                self._current_language, "travel_stamp_title", "Travel Stamp"
            ),
        )

        body_font = QFont(self.font().family(), max(10, int(size.width() * 0.035)))
        painter.setFont(body_font)
        painter.setPen(QColor("#374151"))
        body_rect = QRect(
            int(size.width() * 0.08),
            int(size.height() * 0.38),
            int(size.width() * 0.84),
            int(size.height() * 0.55),
        )
        lines = [f"• {line}" for line in self._stamp_lines()]
        painter.drawText(body_rect, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, "\n".join(lines))
        painter.end()
        return pixmap

    def _handle_back(self):
        if self.on_back:
            self.on_back()

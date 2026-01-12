import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QListWidget, QListWidgetItem,
                             QVBoxLayout, QHBoxLayout, QWidget, QLabel, QTextEdit, 
                             QScrollArea, QFrame, QSplitter, QGridLayout, QComboBox,
                             QStackedWidget, QPushButton, QSlider, QSizePolicy)
from PyQt5.QtGui import QPixmap, QColor, QIcon
from PyQt5.QtCore import Qt, QSize
import db_manager

class MenuListItem(QWidget):
    """Custom widget for an item in the menu list."""
    def __init__(self, menu_data):
        super().__init__()
        self.place_id = menu_data['place_id']
        self.menu_id = menu_data['menu_id']

        # Let the list widget handle clicks.
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Thumbnail
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(150, 100)
        self.thumbnail_label.setScaledContents(True)
        self.thumbnail_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        image_path = menu_data.get('menu_image_url')
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            self.thumbnail_label.setPixmap(pixmap)
        else:
            pixmap = QPixmap(150, 100)
            pixmap.fill(QColor('lightgray'))
            self.thumbnail_label.setPixmap(pixmap)
            # This can be noisy, enable if needed
            # print(f"List View: Image not found or path is null - {image_path}")

        layout.addWidget(self.thumbnail_label)

        # Text content
        text_layout = QVBoxLayout()
        self.name_label = QLabel(menu_data['menu_name'])
        font = self.name_label.font()
        font.setPointSize(16)
        font.setBold(True)
        self.name_label.setFont(font)
        self.name_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        place_name = menu_data.get('place_name') or ''
        price = menu_data.get('menu_price') or ''
        desc_parts = []
        if price:
            desc_parts.append(f"Price: {price}")
        if place_name:
            desc_parts.append(f"Restaurant: {place_name}")
        self.desc_label = QLabel(" | ".join(desc_parts))
        self.desc_label.setWordWrap(True)
        self.desc_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        text_layout.addWidget(self.name_label)
        text_layout.addWidget(self.desc_label)
        
        layout.addLayout(text_layout)
        layout.addStretch()

class KioskMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jeonju Smart Kiosk")
        self.setGeometry(100, 100, 1600, 900)

        self.splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.splitter)

        # --- Left Panel (List) ---
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        
        self.list_title_label = QLabel("Foods")
        font = self.list_title_label.font(); font.setPointSize(24); font.setBold(True)
        self.list_title_label.setFont(font)
        self.list_title_label.setAlignment(Qt.AlignCenter)
        self.left_layout.addWidget(self.list_title_label)

        self.ab_selector_row = QHBoxLayout()
        self.ab_selector_label = QLabel("Test Mode")
        self.ab_selector_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.ab_selector_row.addWidget(self.ab_selector_label)
        self.ab_selector = QComboBox()
        self.ab_selector.addItems(["1. Icon Filters", "2. Question Flow", "3. Price/Time", "4. Recommendation", "5. Photo Grid", "6. Diet Mode"])
        self.ab_selector.currentIndexChanged.connect(self.on_ab_mode_changed)
        self.ab_selector_row.addWidget(self.ab_selector, 1)
        self.left_layout.addLayout(self.ab_selector_row)

        self.ab_stack = QStackedWidget()
        self.ab_stack.addWidget(self.build_icon_filter_panel())
        self.ab_stack.addWidget(self.build_question_panel())
        self.ab_stack.addWidget(self.build_price_time_panel())
        self.ab_stack.addWidget(self.build_recommend_panel())
        self.ab_stack.addWidget(self.build_photo_grid_panel())
        self.ab_stack.addWidget(self.build_diet_panel())
        self.left_layout.addWidget(self.ab_stack)

        self.places_list_widget = QListWidget()
        self.places_list_widget.itemClicked.connect(self.on_menu_item_clicked)
        self.left_layout.addWidget(self.places_list_widget)
        self.splitter.addWidget(self.left_panel)

        # --- Right Panel (Details) ---
        self.right_panel = QWidget()
        self.right_panel.setStyleSheet("background-color: white;")
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(20, 20, 20, 20)

        self.detail_name_label = QLabel("Select a food to see details")
        font = self.detail_name_label.font(); font.setPointSize(28); font.setBold(True)
        self.detail_name_label.setFont(font)
        self.right_layout.addWidget(self.detail_name_label)

        self.menu_detail_widget = QWidget()
        self.menu_detail_layout = QHBoxLayout(self.menu_detail_widget)
        self.menu_detail_layout.setContentsMargins(0, 0, 0, 0)
        self.menu_detail_layout.setSpacing(15)

        self.menu_image_label = QLabel()
        self.menu_image_label.setFixedSize(320, 220)
        self.menu_image_label.setScaledContents(True)
        self.menu_detail_layout.addWidget(self.menu_image_label)

        self.menu_desc_text = QTextEdit()
        self.menu_desc_text.setReadOnly(True)
        self.menu_desc_text.setFrameShape(QFrame.NoFrame)
        self.menu_detail_layout.addWidget(self.menu_desc_text, 1)

        self.right_layout.addWidget(self.menu_detail_widget)

        self.place_info_title_label = QLabel("Restaurant Info")
        font = self.place_info_title_label.font(); font.setPointSize(14); font.setBold(True)
        self.place_info_title_label.setFont(font)
        self.right_layout.addWidget(self.place_info_title_label)

        self.place_info_widget = QWidget()
        self.place_info_layout = QHBoxLayout(self.place_info_widget)
        self.place_info_layout.setContentsMargins(0, 0, 0, 0)
        self.place_info_layout.setSpacing(15)

        self.place_image_label = QLabel()
        self.place_image_label.setFixedSize(380, 260)
        self.place_image_label.setScaledContents(True)
        self.place_info_layout.addWidget(self.place_image_label)

        self.place_info_text = QTextEdit()
        self.place_info_text.setReadOnly(True)
        self.place_info_text.setFrameShape(QFrame.NoFrame)
        self.place_info_layout.addWidget(self.place_info_text, 1)

        self.right_layout.addWidget(self.place_info_widget)
        self.full_menu_title_label = QLabel("Full Menu")
        font = self.full_menu_title_label.font(); font.setPointSize(14); font.setBold(True)
        self.full_menu_title_label.setFont(font)
        self.right_layout.addWidget(self.full_menu_title_label)

        self.full_menu_scroll = QScrollArea()
        self.full_menu_scroll.setWidgetResizable(True)
        self.full_menu_scroll.setFrameShape(QFrame.NoFrame)
        self.full_menu_grid_widget = QWidget()
        self.full_menu_grid_layout = QGridLayout(self.full_menu_grid_widget)
        self.full_menu_grid_layout.setContentsMargins(0, 0, 0, 0)
        self.full_menu_grid_layout.setSpacing(12)
        self.full_menu_scroll.setWidget(self.full_menu_grid_widget)
        self.right_layout.addWidget(self.full_menu_scroll)
        
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([600, 1000])

        self.place_cache = {}
        self.menu_items = []
        self.active_filters = {'taste': None, 'diet': None, 'recommend': None}
        self.load_places()

    def on_ab_mode_changed(self, index):
        if self.ab_stack:
            self.ab_stack.setCurrentIndex(index)
        self.apply_filters()

    def build_icon_filter_panel(self):
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        for label in ["Spicy", "Light", "Warm", "Cool"]:
            btn = QPushButton(label)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(lambda _checked, value=label: self.set_taste_filter(value))
            layout.addWidget(btn)
        return panel

    def build_question_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        title = QLabel("What do you want to eat?")
        title_font = title.font()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        btn_row = QHBoxLayout()
        for label in ["Warm", "Cool", "Spicy", "Light"]:
            btn = QPushButton(label)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(lambda _checked, value=label: self.set_taste_filter(value))
            btn_row.addWidget(btn)
        layout.addLayout(btn_row)
        return panel

    def build_price_time_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        price_label = QLabel("Price (?)")
        self.price_slider = QSlider(Qt.Horizontal)
        self.price_slider.setMinimum(0)
        self.price_slider.setMaximum(4)
        self.price_slider.setValue(2)
        self.price_slider.valueChanged.connect(self.apply_filters)
        time_label = QLabel("Time (minutes)")
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setMinimum(5)
        self.time_slider.setMaximum(20)
        self.time_slider.setValue(10)
        self.time_slider.valueChanged.connect(self.apply_filters)
        layout.addWidget(price_label)
        layout.addWidget(self.price_slider)
        layout.addWidget(time_label)
        layout.addWidget(self.time_slider)
        return panel

    def build_recommend_panel(self):
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        for label in ["Top Picks", "Popular for Tourists", "Light Meal"]:
            btn = QPushButton(label)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(lambda _checked, value=label: self.set_taste_filter(value))
            layout.addWidget(btn)
        return panel

    def build_photo_grid_panel(self):
        panel = QWidget()
        layout = QGridLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.photo_grid_buttons = []
        for i in range(6):
            btn = QPushButton("Photo")
            btn.setFixedSize(80, 80)
            btn.setIconSize(QSize(76, 76))
            btn.clicked.connect(lambda _checked, index=i: self.on_photo_grid_clicked(index))
            btn.setStyleSheet("background-color: #f2f2f2; border: 1px solid #cccccc;")
            layout.addWidget(btn, i // 3, i % 3)
            self.photo_grid_buttons.append(btn)
        return panel

    def build_diet_panel(self):
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        for label in ["Vegan", "Halal", "No Pork"]:
            btn = QPushButton(label)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(lambda _checked, value=label: self.set_taste_filter(value))
            layout.addWidget(btn)
        return panel

    def set_taste_filter(self, label):
        mapping = {"Spicy": 'spicy', "Light": 'light', "Warm": 'warm', "Cool": 'cool'}
        self.active_filters['taste'] = mapping.get(label)
        self.apply_filters()

    def set_diet_filter(self, label):
        mapping = {"Vegan": 'vegan', "Halal": 'halal', "No Pork": 'no_pork'}
        self.active_filters['diet'] = mapping.get(label)
        self.apply_filters()

    def set_recommend_filter(self, label):
        mapping = {"Top Picks": 'top', "Popular for Tourists": 'tourist', "Light Meal": 'light'}
        self.active_filters['recommend'] = mapping.get(label)
        self.apply_filters()

    def on_photo_grid_clicked(self, index):
        if not getattr(self, 'photo_grid_items', None):
            return
        if index < len(self.photo_grid_items):
            self.set_selected_menu(self.photo_grid_items[index])

    def apply_filters(self):
        mode_index = self.ab_selector.currentIndex() if self.ab_selector else 0
        items = list(self.menu_items)

        if mode_index in (0, 1):
            taste = self.active_filters.get('taste')
            if taste:
                items = [m for m in items if taste in m.get('tags', set())]

        if mode_index == 2:
            max_price = self.map_price_slider(self.price_slider.value() if self.price_slider else 2)
            max_time = self.time_slider.value() if self.time_slider else 10
            items = [
                m for m in items
                if (m.get('price_value') is None or m['price_value'] <= max_price)
                and (m.get('time_value') is None or m['time_value'] <= max_time)
            ]

        if mode_index == 3:
            recommend = self.active_filters.get('recommend')
            if recommend == 'top':
                items = sorted(items, key=lambda m: m.get('priority_score', 0), reverse=True)
            elif recommend == 'tourist':
                items = sorted(items, key=lambda m: m.get('priority_score', 0), reverse=True)
            elif recommend == 'light':
                items = [
                    m for m in items
                    if 'light' in m.get('tags', set())
                    or (m.get('price_value') is not None and m['price_value'] <= 12000)
                ]

        if mode_index == 4:
            # Photo grid only affects selection, keep list as-is.
            pass

        if mode_index == 5:
            diet = self.active_filters.get('diet')
            if diet == 'vegan':
                items = [m for m in items if 'vegan' in m.get('tags', set())]
            elif diet == 'halal':
                items = [m for m in items if 'halal' in m.get('tags', set())]
            elif diet == 'no_pork':
                items = [m for m in items if 'pork' not in m.get('tags', set())]

        self.render_menu_list(items)

    def render_menu_list(self, items):
        self.places_list_widget.clear()
        if not items:
            self.places_list_widget.addItem('No items match the filter.')
            self.refresh_photo_grid([])
            return
        for menu_item_data in items:
            list_item = QListWidgetItem(self.places_list_widget)
            custom_widget = MenuListItem(menu_item_data)
            list_item.setData(Qt.UserRole, menu_item_data)
            list_item.setSizeHint(custom_widget.sizeHint())
            self.places_list_widget.addItem(list_item)
            self.places_list_widget.setItemWidget(list_item, custom_widget)
        self.refresh_photo_grid(items)

    def refresh_photo_grid(self, items):
        self.photo_grid_items = items[:6]
        if not getattr(self, 'photo_grid_buttons', None):
            return
        for index, btn in enumerate(self.photo_grid_buttons):
            if index < len(self.photo_grid_items):
                item = self.photo_grid_items[index]
                image_path = item.get('menu_image_url')
                if image_path and os.path.exists(image_path):
                    pixmap = QPixmap(image_path)
                    btn.setIcon(QIcon(pixmap))
                    btn.setText('')
                else:
                    btn.setIcon(QIcon())
                    btn.setText('Photo')
            else:
                btn.setIcon(QIcon())
                btn.setText('Photo')

    def map_price_slider(self, value):
        steps = {0: 10000, 1: 15000, 2: 20000, 3: 25000, 4: 999999}
        return steps.get(value, 20000)

    def parse_price(self, price_text):
        if not price_text:
            return None
        cleaned = ''.join(ch for ch in price_text if ch.isdigit())
        return int(cleaned) if cleaned else None

    def infer_tags(self, name, description):
        text = f"{name or ''} {description or ''}".lower()
        tags = set()
        warm_keywords = ['??', '?', '??', '??', '?', 'soup', 'hot']
        cool_keywords = ['?', '??', '??', 'cold', 'ice']
        spicy_keywords = ['??', '?', 'spicy', 'hot spicy', '?']
        light_keywords = ['???', 'salad', 'light', '???']
        pork_keywords = ['??', '??', 'pork']
        vegan_keywords = ['??', 'vegan', 'vegetarian']
        if any(k in text for k in warm_keywords):
            tags.add('warm')
        if any(k in text for k in cool_keywords):
            tags.add('cool')
        if any(k in text for k in spicy_keywords):
            tags.add('spicy')
        if any(k in text for k in light_keywords):
            tags.add('light')
        if any(k in text for k in pork_keywords):
            tags.add('pork')
        if any(k in text for k in vegan_keywords):
            tags.add('vegan')
        return tags

    def infer_time(self, name, description):
        text = f"{name or ''} {description or ''}".lower()
        if any(k in text for k in ['??', '?', '??', '??', 'soup']):
            return 12
        if any(k in text for k in ['??', '??', 'noodle', '?', 'ramen']):
            return 8
        if any(k in text for k in ['??', 'fried']):
            return 6
        return 10

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

    def load_places(self):
        """Fetches menu items for food places and populates the list."""
        try:
            places = db_manager.get_all_places()
            food_places = [place for place in places if place.get('type') == 'FOOD']
            if not food_places:
                self.places_list_widget.addItem("No foods found in database.")
                return

            self.menu_items = []
            for place_data in food_places:
                place_id = place_data['place_id']
                details = db_manager.get_place_details(place_id)
                self.place_cache[place_id] = details
                images_by_id = {img.get('image_id'): img.get('url') for img in details.get('images', [])}
                place_name = details.get('name') or place_data.get('name') or ''
                priority_score = place_data.get('priority_score') or 0
                is_halal = place_data.get('is_halal') or 0

                for idx, menu in enumerate(details.get('menus', [])):
                    name = menu.get('name') or 'Menu item'
                    desc = menu.get('description') or ''
                    tags = self.infer_tags(name, desc)
                    if is_halal:
                        tags.add('halal')
                    menu_item_data = {
                        'menu_id': f"{place_id}:{idx}",
                        'place_id': place_id,
                        'place_name': place_name,
                        'menu_name': name,
                        'menu_price': menu.get('price') or '',
                        'menu_desc': desc,
                        'menu_image_url': images_by_id.get(menu.get('image_id')),
                        'price_value': self.parse_price(menu.get('price') or ''),
                        'time_value': self.infer_time(name, desc),
                        'tags': tags,
                        'priority_score': priority_score,
                    }

                    self.menu_items.append(menu_item_data)

            self.render_menu_list(self.menu_items)
        except Exception as e:
            self.places_list_widget.addItem("Error loading menu items.")
            print(f"Error in load_places: {e}")

    def on_menu_item_clicked(self, item):
        """Handles click events on the menu list."""
        menu_data = item.data(Qt.UserRole)
        if not menu_data:
            return
        self.set_selected_menu(menu_data)

    def set_selected_menu(self, menu_data):
        menu_name = menu_data.get('menu_name') or ''
        menu_price = menu_data.get('menu_price') or ''
        menu_desc = menu_data.get('menu_desc') or ''
        title = f"{menu_name} ({menu_price})" if menu_price else menu_name
        self.detail_name_label.setText(title or "Menu")
        self.menu_desc_text.setText(menu_desc or "No description")

        place_id = menu_data.get('place_id')
        details = self.place_cache.get(place_id)
        if not details and place_id:
            details = db_manager.get_place_details(place_id)
            self.place_cache[place_id] = details

        details = details or {}
        place_name = menu_data.get('place_name') or details.get('name') or ''
        address = details.get('address_text') or ''
        hours = details.get('hours_text') or ''
        food_info = details.get('food_info', {})
        phone = food_info.get('infocenterfood') or ''
        reservation = food_info.get('reservationfood') or ''

        self.set_image_label(self.menu_image_label, menu_data.get('menu_image_url'), 320, 220)

        info_lines = []
        if place_name:
            info_lines.append(f"Restaurant: {place_name}")
        if details.get('short_desc'):
            info_lines.append(details['short_desc'])
        if hours:
            info_lines.append(f"Hours: {hours}")
        if phone:
            info_lines.append(f"Phone: {phone}")
        if reservation:
            info_lines.append(f"Reservation: {reservation}")
        if address:
            info_lines.append(f"Address: {address}")
        self.place_info_text.setText("\n".join(info_lines) if info_lines else "No additional info.")

        image_path = self.get_place_image_path(details)
        self.set_image_label(self.place_image_label, image_path, 380, 260)

        menus = details.get('menus', [])
        images_by_id = {img.get('image_id'): img.get('url') for img in details.get('images', [])}
        self.populate_full_menu_grid(menus, images_by_id)

    def populate_full_menu_grid(self, menus, images_by_id):
        self.clear_layout(self.full_menu_grid_layout)
        if not menus:
            self.full_menu_grid_layout.addWidget(QLabel("No menu info"), 0, 0)
            return

        columns = 4
        row = 0
        col = 0
        for menu in menus:
            item = QWidget()
            item_layout = QGridLayout(item)
            item_layout.setContentsMargins(8, 8, 8, 8)
            item_layout.setSpacing(6)
            item.setFixedHeight(90)

            thumb = QLabel()
            thumb.setFixedSize(70, 70)
            thumb.setScaledContents(True)
            image_path = images_by_id.get(menu.get('image_id'))
            self.set_image_label(thumb, image_path, 70, 70)
            item_layout.addWidget(thumb, 0, 0, 2, 1)

            name = menu.get('name') or 'Menu item'
            price = menu.get('price') or ''
            name_label = QLabel(name)
            name_font = name_label.font()
            name_font.setPointSize(11)
            name_font.setBold(True)
            name_label.setFont(name_font)
            price_label = QLabel(f"Price: {price}" if price else "Price: -")
            item_layout.addWidget(name_label, 0, 1)
            item_layout.addWidget(price_label, 1, 1)
            item_layout.setColumnStretch(1, 1)

            self.full_menu_grid_layout.addWidget(item, row, col)
            col += 1
            if col >= columns:
                col = 0
                row += 1

    def get_place_image_path(self, details):
        for img in details.get('images', []):
            if img.get('kind') in ('PHOTO', 'THUMBNAIL'):
                image_path = img.get('url')
                if image_path and os.path.exists(image_path):
                    return image_path
        return None

    def set_image_label(self, label, image_path, width, height):
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
        else:
            pixmap = QPixmap(width, height)
            pixmap.fill(QColor('lightgray'))
        label.setPixmap(pixmap)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QMainWindow { background-color: #f0f0f0; }
        QWidget { color: #333333; }
        QListWidget { border: none; background-color: #ffffff; }
        QListWidget::item { border-bottom: 1px solid #e0e0e0; padding: 5px; }
        QListWidget::item:selected {
            background-color: #e6f2ff;
            color: #000000;
        }
        QScrollArea { border: none; }
        QTextEdit { background-color: white; border: none; }
        QLabel { color: #333333; }
    """)
    main_window = KioskMainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

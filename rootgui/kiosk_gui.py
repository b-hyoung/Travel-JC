import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QListWidget, QListWidgetItem,
                             QVBoxLayout, QHBoxLayout, QWidget, QLabel, QTextEdit, 
                             QScrollArea, QFrame, QSplitter, QGridLayout)
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtCore import Qt
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
        self.load_places()

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

            for place_data in food_places:
                place_id = place_data['place_id']
                details = db_manager.get_place_details(place_id)
                self.place_cache[place_id] = details
                images_by_id = {img.get('image_id'): img.get('url') for img in details.get('images', [])}
                place_name = details.get('name') or place_data.get('name') or ''

                for idx, menu in enumerate(details.get('menus', [])):
                    menu_item_data = {
                        'menu_id': f"{place_id}:{idx}",
                        'place_id': place_id,
                        'place_name': place_name,
                        'menu_name': menu.get('name') or 'Menu item',
                        'menu_price': menu.get('price') or '',
                        'menu_desc': menu.get('description') or '',
                        'menu_image_url': images_by_id.get(menu.get('image_id')),
                    }
                    list_item = QListWidgetItem(self.places_list_widget)
                    custom_widget = MenuListItem(menu_item_data)

                    list_item.setData(Qt.UserRole, menu_item_data)
                    list_item.setSizeHint(custom_widget.sizeHint())

                    self.places_list_widget.addItem(list_item)
                    self.places_list_widget.setItemWidget(list_item, custom_widget)
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

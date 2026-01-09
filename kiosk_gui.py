import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QListWidget, QListWidgetItem,
                             QVBoxLayout, QHBoxLayout, QWidget, QLabel, QTextEdit, 
                             QScrollArea, QFrame, QSplitter)
from PyQt5.QtGui import QPixmap, QFont, QColor
from PyQt5.QtCore import Qt, QSize
import db_manager

class PlaceListItem(QWidget):
    """Custom widget for an item in the places list."""
    def __init__(self, place_data):
        super().__init__()
        self.place_id = place_data['place_id']
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Thumbnail
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(150, 100)
        self.thumbnail_label.setScaledContents(True)
        
        image_path = place_data.get('cover_image_url')
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
        self.name_label = QLabel(place_data['name'])
        font = self.name_label.font()
        font.setPointSize(16)
        font.setBold(True)
        self.name_label.setFont(font)
        
        self.desc_label = QLabel(place_data['short_desc'])
        self.desc_label.setWordWrap(True)
        
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
        
        self.list_title_label = QLabel("Attractions & Places")
        font = self.list_title_label.font(); font.setPointSize(24); font.setBold(True)
        self.list_title_label.setFont(font)
        self.list_title_label.setAlignment(Qt.AlignCenter)
        self.left_layout.addWidget(self.list_title_label)
        
        self.places_list_widget = QListWidget()
        self.places_list_widget.itemClicked.connect(self.on_place_clicked)
        self.left_layout.addWidget(self.places_list_widget)
        self.splitter.addWidget(self.left_panel)

        # --- Right Panel (Details) ---
        self.right_panel = QWidget()
        self.right_panel.setStyleSheet("background-color: white;")
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(20, 20, 20, 20)

        self.detail_name_label = QLabel("Select a place to see details")
        font = self.detail_name_label.font(); font.setPointSize(28); font.setBold(True)
        self.detail_name_label.setFont(font)
        self.right_layout.addWidget(self.detail_name_label)

        self.detail_address_label = QLabel()
        font = self.detail_address_label.font(); font.setPointSize(12)
        self.detail_address_label.setFont(font)
        self.right_layout.addWidget(self.detail_address_label)
        
        self.detail_hours_label = QLabel()
        self.detail_hours_label.setFont(font)
        self.right_layout.addWidget(self.detail_hours_label)

        self.detail_desc_text = QTextEdit()
        self.detail_desc_text.setReadOnly(True)
        self.detail_desc_text.setFrameShape(QFrame.NoFrame)
        self.right_layout.addWidget(self.detail_desc_text)

        self.menu_title_label = QLabel("전체 메뉴")
        font = self.menu_title_label.font(); font.setPointSize(16); font.setBold(True)
        self.menu_title_label.setFont(font)
        self.right_layout.addWidget(self.menu_title_label)

        self.menu_list_scroll = QScrollArea()
        self.menu_list_scroll.setWidgetResizable(True)
        self.menu_list_scroll.setFrameShape(QFrame.NoFrame)
        self.menu_list_widget = QWidget()
        self.menu_list_layout = QVBoxLayout(self.menu_list_widget)
        self.menu_list_layout.setContentsMargins(0, 0, 0, 0)
        self.menu_list_layout.setSpacing(10)
        self.menu_list_scroll.setWidget(self.menu_list_widget)
        self.menu_list_scroll.setFixedHeight(220)
        self.right_layout.addWidget(self.menu_list_scroll)

        self.menu_images_title_label = QLabel("메뉴 사진")
        font = self.menu_images_title_label.font(); font.setPointSize(14); font.setBold(True)
        self.menu_images_title_label.setFont(font)
        self.right_layout.addWidget(self.menu_images_title_label)
        
        self.image_scroll_area = QScrollArea()
        self.image_scroll_area.setWidgetResizable(True)
        self.image_gallery_widget = QWidget()
        self.image_gallery_layout = QHBoxLayout(self.image_gallery_widget)
        self.image_scroll_area.setWidget(self.image_gallery_widget)
        self.image_scroll_area.setFixedHeight(220)
        self.right_layout.addWidget(self.image_scroll_area)
        
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([600, 1000])

        self.load_places()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

    def load_places(self):
        """Fetches places from the DB and populates the custom list."""
        try:
            places = db_manager.get_all_places()
            if not places:
                self.places_list_widget.addItem("No places found in database.")
                return
                
            for place_data in places:
                list_item = QListWidgetItem(self.places_list_widget)
                custom_widget = PlaceListItem(place_data)
                
                list_item.setData(Qt.UserRole, custom_widget.place_id)
                list_item.setSizeHint(custom_widget.sizeHint())
                
                self.places_list_widget.addItem(list_item)
                self.places_list_widget.setItemWidget(list_item, custom_widget)
        except Exception as e:
            self.places_list_widget.addItem("Error loading places.")
            print(f"Error in load_places: {e}")

    def on_place_clicked(self, item):
        """Handles click events on the places list."""
        place_id = item.data(Qt.UserRole)
        
        if place_id:
            details = db_manager.get_place_details(place_id)
            
            self.detail_name_label.setText(details['name'])
            self.detail_address_label.setText(f"Address: {details['address_text']}")
            self.detail_hours_label.setText(f"Hours: {details['hours_text']}")
            self.detail_desc_text.setText(details['short_desc'])

            food_info = details.get('food_info', {})
            raw_menu_text = food_info.get('treatmenu') or food_info.get('firstmenu') or ''
            self.clear_layout(self.menu_list_layout)
            images_by_id = {img.get('image_id'): img.get('url') for img in details.get('images', [])}
            if raw_menu_text:
                raw_label = QLabel(raw_menu_text)
                raw_label.setWordWrap(True)
                self.menu_list_layout.addWidget(raw_label)
            else:
                menus = details.get('menus', [])
                if not menus:
                    self.menu_list_layout.addWidget(QLabel("No menu info"))
                for menu in menus:
                    row = QWidget()
                    row_layout = QHBoxLayout(row)
                    row_layout.setContentsMargins(0, 0, 0, 0)
                    row_layout.setSpacing(10)

                    image_label = QLabel()
                    image_label.setFixedSize(120, 90)
                    image_label.setScaledContents(True)
                    image_path = images_by_id.get(menu.get('image_id'))
                    if image_path and os.path.exists(image_path):
                        image_label.setPixmap(QPixmap(image_path))
                    else:
                        placeholder = QPixmap(120, 90)
                        placeholder.fill(QColor('lightgray'))
                        image_label.setPixmap(placeholder)

                    text_col = QVBoxLayout()
                    name = menu.get('name') or ''
                    price = menu.get('price') or ''
                    description = menu.get('description') or ''

                    name_label = QLabel(name)
                    name_font = name_label.font()
                    name_font.setPointSize(12)
                    name_font.setBold(True)
                    name_label.setFont(name_font)

                    price_label = QLabel(price)
                    desc_label = QLabel(description)
                    desc_label.setWordWrap(True)

                    text_col.addWidget(name_label)
                    if price:
                        text_col.addWidget(price_label)
                    if description:
                        text_col.addWidget(desc_label)
                    text_col.addStretch()

                    row_layout.addWidget(image_label)
                    row_layout.addLayout(text_col)
                    self.menu_list_layout.addWidget(row)
                self.menu_list_layout.addStretch()
            # Clear old images
            self.clear_layout(self.image_gallery_layout)

            # Populate new images with debugging
            print(f"\n--- Loading images for {details['name']} ---")
            menu_images = [img for img in details['images'] if img.get('kind') == 'MENU']
            images_to_show = menu_images if menu_images else details['images']
            if not images_to_show:
                self.image_gallery_layout.addWidget(QLabel("메뉴 사진 없음"))

            for img_data in images_to_show:
                image_path = img_data['url']
                print(f"Attempting to load image from: {image_path}")
                print(f"File exists? {os.path.exists(image_path)}")
                
                image_label = QLabel()
                image_label.setFixedSize(250, 200)
                image_label.setScaledContents(True)
                
                pixmap = QPixmap(image_path)
                if pixmap.isNull():
                    print("  -> FAILED to load pixmap. It is null.")
                    pixmap = QPixmap(250, 200)
                    pixmap.fill(QColor('red'))
                else:
                    print("  -> Successfully loaded pixmap.")
                
                image_label.setPixmap(pixmap)
                self.image_gallery_layout.addWidget(image_label)
            self.image_gallery_layout.addStretch()


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

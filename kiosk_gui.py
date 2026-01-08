import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QListWidget, QListWidgetItem,
                             QVBoxLayout, QHBoxLayout, QWidget, QLabel, QTextEdit, 
                             QScrollArea, QFrame, QSplitter)
from PyQt5.QtGui import QPixmap, QFont
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
        pixmap = QPixmap(place_data['cover_image_url'])
        self.thumbnail_label.setPixmap(pixmap)
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

        # --- Main Layout ---
        self.splitter = QSplitter(Qt.Horizontal)
        self.central_widget = self.splitter
        self.setCentralWidget(self.central_widget)

        # --- Left Panel (List) ---
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        
        self.list_title_label = QLabel("Attractions & Places")
        font = self.list_title_label.font()
        font.setPointSize(24)
        font.setBold(True)
        self.list_title_label.setFont(font)
        self.list_title_label.setAlignment(Qt.AlignCenter)
        self.left_layout.addWidget(self.list_title_label)
        
        self.places_list_widget = QListWidget()
        self.places_list_widget.itemClicked.connect(self.on_place_clicked)
        self.left_layout.addWidget(self.places_list_widget)
        self.splitter.addWidget(self.left_panel)

        # --- Right Panel (Details) ---
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(20, 20, 20, 20)

        self.detail_name_label = QLabel("Select a place to see details")
        font = self.detail_name_label.font()
        font.setPointSize(28)
        font.setBold(True)
        self.detail_name_label.setFont(font)
        self.right_layout.addWidget(self.detail_name_label)

        self.detail_address_label = QLabel()
        font = self.detail_address_label.font()
        font.setPointSize(12)
        self.detail_address_label.setFont(font)
        self.right_layout.addWidget(self.detail_address_label)
        
        self.detail_hours_label = QLabel()
        self.detail_hours_label.setFont(font)
        self.right_layout.addWidget(self.detail_hours_label)

        self.detail_desc_text = QTextEdit()
        self.detail_desc_text.setReadOnly(True)
        self.detail_desc_text.setFrameShape(QFrame.NoFrame)
        self.right_layout.addWidget(self.detail_desc_text)
        
        # Image Gallery
        self.image_scroll_area = QScrollArea()
        self.image_scroll_area.setWidgetResizable(True)
        self.image_gallery_widget = QWidget()
        self.image_gallery_layout = QHBoxLayout(self.image_gallery_widget)
        self.image_scroll_area.setWidget(self.image_gallery_widget)
        self.image_scroll_area.setFixedHeight(220)
        self.right_layout.addWidget(self.image_scroll_area)
        
        self.splitter.addWidget(self.right_panel)
        
        # Adjust splitter initial size
        self.splitter.setSizes([600, 1000])

        self.load_places()

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
                
                # Store the id in the item itself
                list_item.setData(Qt.UserRole, custom_widget.place_id)
                list_item.setSizeHint(custom_widget.sizeHint())
                
                self.places_list_widget.addItem(list_item)
                self.places_list_widget.setItemWidget(list_item, custom_widget)
        except Exception as e:
            self.places_list_widget.addItem("Error loading places.")
            print(f"Error: {e}")

    def on_place_clicked(self, item):
        """Handles click events on the places list."""
        place_id = item.data(Qt.UserRole)
        
        if place_id:
            details = db_manager.get_place_details(place_id)
            
            # Update detail panel
            self.detail_name_label.setText(details['name'])
            self.detail_address_label.setText(f"Address: {details['address_text']}")
            self.detail_hours_label.setText(f"Hours: {details['hours_text']}")
            self.detail_desc_text.setText(details['short_desc'])
            
            # Clear old images
            for i in reversed(range(self.image_gallery_layout.count())): 
                item = self.image_gallery_layout.itemAt(i)
                if item.widget():
                    item.widget().setParent(None)

            # Populate new images
            for img_data in details['images']:
                image_label = QLabel()
                image_label.setFixedSize(250, 200)
                image_label.setScaledContents(True)
                pixmap = QPixmap(img_data['url'])
                image_label.setPixmap(pixmap)
                self.image_gallery_layout.addWidget(image_label)
            self.image_gallery_layout.addStretch()


def main():
    app = QApplication(sys.argv)
    # Apply a simple stylesheet for better visuals
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f0f0f0;
        }
        QListWidget {
            border: none;
            background-color: #ffffff;
        }
        QListWidget::item {
            border-bottom: 1px solid #e0e0e0;
        }
        QListWidget::item:selected {
            background-color: #e6f2ff;
        }
        QScrollArea {
            border: none;
        }
    """)
    main_window = KioskMainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
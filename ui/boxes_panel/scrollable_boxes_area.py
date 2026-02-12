# scrollable_boxes_area.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QSizePolicy, QScrollArea, QSpacerItem,
                             QFrame, QLabel)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QWheelEvent
from ui.boxes_panel.memory_boxes.memory_box import MemoryBox, BOX_BORDER_COLORS, BOX_TITLES
from ui.boxes_panel.waiting_area import WaitingAreaWidget


class ScrollableBoxesArea(QScrollArea):
    """Notion tarzı scrollable kutular alanı - WHEEL EVENT DESTEĞİ EKLENDİ"""
    
    # Yeni sinyaller
    boxHovered = pyqtSignal(int, bool)  # box_id, hovered
    waitingAreaHovered = pyqtSignal(int, bool)  # box_id, hovered
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.box_rows = []
        self.waiting_areas = {}
        self.current_hovered_box = None
        
        self._setup_scroll_area()
        self._setup_content()
    
    def _setup_scroll_area(self):
        """Notion tarzı scroll area özelliklerini ayarla"""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.setStyleSheet("""
            QScrollArea {
                background-color: #f7f6f3;
                border: none;
                padding: 0;
            }
            
            QScrollBar:vertical {
                background-color: transparent;
                width: 10px;
                border-radius: 5px;
                margin: 2px;
            }
            
            QScrollBar::handle:vertical {
                background-color: #dadada;
                border-radius: 5px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #c4c4c4;
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        self.setViewportMargins(0, 0, 0, 0)
        
        self.setFocusPolicy(Qt.FocusPolicy.WheelFocus)
        self.viewport().setFocusPolicy(Qt.FocusPolicy.WheelFocus)
    
    def wheelEvent(self, event: QWheelEvent):
        """Mouse wheel ile scroll - DRAG DESTEKLİ"""
        try:
            vscroll = self.verticalScrollBar()
            
            if vscroll and vscroll.isEnabled():
                delta = event.angleDelta().y()
                
                if delta == 0:
                    event.ignore()
                    return
                
                scroll_amount = -delta
                current_value = vscroll.value()
                new_value = current_value + scroll_amount
                
                min_value = vscroll.minimum()
                max_value = vscroll.maximum()
                
                if new_value < min_value:
                    new_value = min_value
                elif new_value > max_value:
                    new_value = max_value
                
                if new_value != current_value:
                    vscroll.setValue(new_value)
                    event.accept()
                    
                    if self.parent_window and hasattr(self.parent_window, '_update_all_card_positions'):
                        self.parent_window._update_all_card_positions()
                else:
                    event.ignore()
            else:
                event.ignore()
                
        except Exception:
            event.ignore()
    
    def _setup_content(self):
        """Notion tarzı içerik widget'ını oluştur"""
        self.content_widget = QWidget()
        self.content_widget.setObjectName("contentWidget")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(24)
        self.content_layout.setContentsMargins(48, 32, 48, 32)
        
        self.content_widget.setStyleSheet("""
            QWidget#contentWidget {
                background-color: #f7f6f3;
                border: none;
            }
        """)
        
        self.setWidget(self.content_widget)
    
    def create_boxes_with_waiting_areas(self, db=None):
        """Notion tarzı kutuları ve bekleme alanlarını oluştur"""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.box_rows.clear()
        self.waiting_areas.clear()
        
        self._create_header()
        
        for box_id in range(1, 6):
            self._create_box_row(box_id, db)
            
            if box_id < 5:
                self._add_divider()
        
        self.content_layout.addStretch(1)
    
    def _create_header(self):
        """Notion tarzı minimalist başlık bölümü"""
        main_title = QLabel("Ezber Kutuları")
        main_title.setObjectName("mainTitle")
        main_title.setStyleSheet("""
            QLabel#mainTitle {
                font-size: 48px;
                font-weight: 800;
                color: #37352f;
                padding: 8px 0;
                background: transparent;
                border: none;
                margin: 0;
            }
        """)
        
        self.content_layout.addWidget(main_title)
        
        self.content_layout.addSpacing(40)
    
    def _create_box_row(self, box_id, db):
        """Leitner tarzı kutu satırı oluştur - L ŞEKLİNDE BEYAZ ALAN"""
        border_color = BOX_BORDER_COLORS[box_id - 1]
        title = BOX_TITLES[box_id - 1]
        
        container_widget = QWidget()
        container_widget.setObjectName(f"container_{box_id}")
        
        main_layout = QHBoxLayout(container_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        white_vertical_panel = QFrame()
        white_vertical_panel.setObjectName(f"whiteVertical_{box_id}")
        white_vertical_panel.setFrameShape(QFrame.Shape.NoFrame)
        
        white_vertical_panel.setStyleSheet(f"""
            QFrame#whiteVertical_{box_id} {{
                background-color: #ffffff;
                border: 2px solid {border_color};
                border-right: none;
                border-top-left-radius: 12px;
                border-bottom-left-radius: 12px;
                min-width: 350px;
                min-height: 460px;
            }}
        """)
        
        vertical_layout = QVBoxLayout(white_vertical_panel)
        vertical_layout.setContentsMargins(20, 20, 20, 20)
        vertical_layout.setSpacing(0)
        
        box_widget = MemoryBox(title, "#FFFFFF", border_color, box_id, db=db)
        box_widget.setFixedSize(300, 260)
        
        box_widget.setStyleSheet(f"""
            MemoryBox {{
                border: 3px solid {border_color};
                border-radius: 10px;
                background-color: #ffffff;
            }}
            
            MemoryBox QLabel {{
                background-color: transparent;
                border: none !important;
                padding: 0px !important;
                margin: 0px !important;
                font-weight: normal;
            }}
            
            MemoryBox QLabel[objectName="count_lbl"] {{
                background-color: transparent !important;
                color: {border_color} !important;
                font-weight: bold !important;
                font-size: 14px !important;
                border: none !important;
                padding: 0px !important;
                margin: 0px !important;
                min-width: 0px !important;
                max-width: none !important;
            }}
            
            MemoryBox QLabel[objectName="title_lbl"] {{
                background-color: transparent !important;
                color: {border_color} !important;
                font-weight: bold !important;
                font-size: 14px !important;
                border: none !important;
                padding: 0px !important;
                margin: 0px !important;
            }}
            
            MemoryBox QPushButton {{
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 6px 12px;
                color: #000000;
                font-size: 12px;
            }}
            
            MemoryBox QPushButton:hover {{
                background-color: #e0e0e0;
            }}
            
            MemoryBox QPushButton:disabled {{
                background-color: #f5f5f5;
                color: #999999;
            }}
            
            MemoryBox QPushButton#draw_btn {{
                min-width: 80px;
            }}
            
            MemoryBox QPushButton#reset_btn {{
                min-width: 100px;
            }}
        """)
        
        vertical_layout.addWidget(box_widget, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        bottom_space = QWidget()
        bottom_space.setObjectName(f"bottomSpace_{box_id}")
        bottom_space.setFixedHeight(140)
        
        bottom_space.setStyleSheet(f"""
            QWidget#bottomSpace_{box_id} {{
                background: transparent;
                border: none;
                border-right: 2px solid {border_color};
            }}
        """)
        
        vertical_layout.addWidget(bottom_space, 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        main_layout.addWidget(white_vertical_panel, 0, Qt.AlignmentFlag.AlignLeft)
        
        right_composite_widget = QWidget()
        right_composite_widget.setObjectName(f"rightComposite_{box_id}")
        
        right_vertical_layout = QVBoxLayout(right_composite_widget)
        right_vertical_layout.setContentsMargins(0, 0, 0, 0)
        right_vertical_layout.setSpacing(0)
        
        white_horizontal_panel = QFrame()
        white_horizontal_panel.setObjectName(f"whiteHorizontal_{box_id}")
        white_horizontal_panel.setFrameShape(QFrame.Shape.NoFrame)
        
        white_horizontal_panel.setStyleSheet(f"""
            QFrame#whiteHorizontal_{box_id} {{
                background-color: #ffffff;
                border: 2px solid {border_color};
                border-left: none;
                border-top-right-radius: 12px;
                border-bottom: none;
                min-width: 940px;
                min-height: 320px;
                margin-left: -1px;
            }}
        """)
        
        horizontal_layout = QHBoxLayout(white_horizontal_panel)
        horizontal_layout.setContentsMargins(20, 20, 20, 20)
        horizontal_layout.setSpacing(24)
        
        waiting_areas_list = []
        
        if box_id == 1:
            waiting_area1 = WaitingAreaWidget(box_id, "Her gün", self.parent_window, True)
        elif box_id == 5:
            waiting_area1 = WaitingAreaWidget(box_id, "On dört günde bir", self.parent_window, True)
        else:
            prev_title = BOX_TITLES[box_id - 2]
            waiting_area1 = WaitingAreaWidget(box_id-1, prev_title, self.parent_window, True)
        
        if waiting_area1:
            waiting_area1.setFixedSize(450, 260)
            waiting_area1.empty_container.setFixedHeight(240)
            waiting_area1.scroll_area.setFixedWidth(300)
            waiting_area1.transfer_button.setFixedWidth(150)
            waiting_area1.show_empty_container()
            waiting_areas_list.append(waiting_area1)
            horizontal_layout.addWidget(waiting_area1)
        
        if box_id == 1:
            next_title = BOX_TITLES[box_id]
            waiting_area2 = WaitingAreaWidget(box_id+1, next_title, self.parent_window, False)
        elif box_id == 5:
            prev_title = BOX_TITLES[box_id - 2]
            waiting_area2 = WaitingAreaWidget(box_id-1, prev_title, self.parent_window, False)
        else:
            next_title = BOX_TITLES[box_id]
            waiting_area2 = WaitingAreaWidget(box_id+1, next_title, self.parent_window, False)
        
        if waiting_area2:
            waiting_area2.setFixedSize(450, 260)
            waiting_area2.empty_container.setFixedHeight(240)
            waiting_area2.scroll_area.setFixedWidth(300)
            waiting_area2.transfer_button.setFixedWidth(150)
            waiting_area2.show_empty_container()
            waiting_areas_list.append(waiting_area2)
            horizontal_layout.addWidget(waiting_area2)
        
        right_vertical_layout.addWidget(white_horizontal_panel, 0, Qt.AlignmentFlag.AlignTop)
        
        transparent_space = QWidget()
        transparent_space.setObjectName(f"transparentSpace_{box_id}")
        transparent_space.setFixedHeight(140)
        
        transparent_space.setStyleSheet(f"""
            QWidget#transparentSpace_{box_id} {{
                background: transparent;
                border: none;
                border-left: 2px solid {border_color};
                border-top: 2px solid {border_color};
            }}
        """)
        
        right_vertical_layout.addWidget(transparent_space, 1)
        
        main_layout.addWidget(right_composite_widget, 1)
        
        corner_widget = QWidget()
        corner_widget.setObjectName(f"corner_{box_id}")
        corner_widget.setFixedSize(2, 2)
        
        corner_widget.setStyleSheet(f"""
            QWidget#corner_{box_id} {{
                background-color: {border_color};
            }}
        """)
        
        corner_layout = QHBoxLayout()
        corner_layout.setContentsMargins(0, 0, 0, 0)
        corner_layout.setSpacing(0)
        corner_layout.addStretch()
        corner_layout.addWidget(corner_widget)
        corner_layout.addStretch()
        
        right_vertical_layout.addLayout(corner_layout)
        
        row_widget = QWidget()
        row_widget.setObjectName(f"rowWidget_{box_id}")
        
        row_layout = QVBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(0)
        
        row_widget.setStyleSheet("""
            QWidget {
                background-color: #f7f6f3;
                border: none;
            }
        """)
        
        row_layout.addWidget(container_widget)
        
        self.box_rows.append({
            'widget': row_widget,
            'memory_box': box_widget,
            'waiting_areas': waiting_areas_list
        })
        
        self.waiting_areas[box_id] = waiting_areas_list
        
        self.content_layout.addWidget(row_widget)
    
    def _add_divider(self):
        """Notion tarzı ince ayraç ekle"""
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Plain)
        divider.setStyleSheet("""
            QFrame {
                border: none;
                border-top: 1px solid #ededec;
                margin: 16px 0;
            }
        """)
        divider.setFixedHeight(1)
        self.content_layout.addWidget(divider)
    
    def _on_row_hover(self, box_id, hovered):
        """Satır hover durumunu işle"""
        self.current_hovered_box = box_id if hovered else None
        self.boxHovered.emit(box_id, hovered)
    
    def get_box_widget(self, box_id):
        """Box ID'ye göre MemoryBox widget'ını getir"""
        for box_row in self.box_rows:
            if box_row['memory_box'].box_id == box_id:
                return box_row['memory_box']
        return None
    
    def get_waiting_areas(self, box_id):
        """Box ID'ye göre waiting areas listesini getir"""
        return self.waiting_areas.get(box_id, [])
    
    def update_all_box_counts(self):
        """Tüm kutuların kart sayılarını güncelle"""
        for box_row in self.box_rows:
            box_row['memory_box'].update_card_count()
    
    def clear_all_waiting_areas(self):
        """Tüm bekleme alanlarını temizle"""
        for waiting_areas in self.waiting_areas.values():
            for waiting_area in waiting_areas:
                if waiting_area:
                    waiting_area.clear_cards()
    
    def set_theme(self, theme='light'):
        """Tema değiştirme fonksiyonu (light/dark)"""
        if theme == 'dark':
            self.setStyleSheet("""
                QScrollArea {
                    background-color: #1a1a1a;
                    border: none;
                }
                
                QScrollBar:vertical {
                    background-color: transparent;
                    width: 10px;
                    border-radius: 5px;
                }
                
                QScrollBar::handle:vertical {
                    background-color: #555555;
                    border-radius: 5px;
                }
                
                QScrollBar::handle:vertical:hover {
                    background-color: #666666;
                }
            """)
            
            self.content_widget.setStyleSheet("""
                QWidget#contentWidget {
                    background-color: #1a1a1a;
                    border: none;
                }
            """)
        else:
            self._setup_scroll_area()
            self.content_widget.setStyleSheet("""
                QWidget#contentWidget {
                    background-color: #f7f6f3;
                    border: none;
                }
            """)
"""TEMEL UI YAPISI - Değişmeyecek"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QPushButton, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from ..drag_drop_manager import drop_target, DropTarget


@drop_target(DropTarget.WAITING_AREA)
class WaitingAreaBase(QWidget):
    """Temel bekleme alanı - SADECE UI YAPISI"""
    
    card_dropped = pyqtSignal(int, int)
    button_clicked = pyqtSignal()
    card_dragged_out = pyqtSignal(int)
    
    def __init__(self, box_id, target_box_title, parent=None, is_left_side=False):
        super().__init__(parent)
        self.box_id = box_id
        self.target_box_title = target_box_title
        self.is_left_side = is_left_side
        self.cards = []
        self.card_widgets = {}
        self.is_drag_over = False
        self.db = None
        
        self.setFixedHeight(260)
        self.setFixedWidth(450)
        
        self._setup_ui()
        self._setup_styles()
        
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
    
    def _setup_ui(self):
        """TEMEL UI KURULUMU"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("scroll_area")
        self.scroll_area.setFixedWidth(300)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.verticalScrollBar().setVisible(False)
        self.scroll_area.horizontalScrollBar().setVisible(False)
        self.scroll_area.setAcceptDrops(True)
        self.scroll_area.viewport().setAcceptDrops(True)
        
        # Container Widget
        self.container_widget = QWidget()
        self.container_widget.setObjectName("container_widget")
        self.container_widget.setMouseTracking(True)
        self.container_widget.setAcceptDrops(True)
        
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(20, 10, 20, 10)
        self.container_layout.setSpacing(10)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        # Boş Alan Container
        self.empty_container = QFrame()
        self.empty_container.setObjectName("empty_container")
        self.empty_container.setFixedHeight(240)
        self.empty_container.setFixedWidth(260)
        self.empty_container.setMouseTracking(True)
        
        empty_layout = QVBoxLayout(self.empty_container)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(8)
        
        self.empty_label = QLabel("Kartları buraya\nsürükleyin")
        self.empty_label.setObjectName("empty_label")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)
        
        self.status_label = QLabel("(bilmediklerim)" if self.is_left_side else "(bildiklerim)")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        empty_layout.addWidget(self.empty_label)
        empty_layout.addWidget(self.status_label)
        
        self.container_layout.addWidget(self.empty_container, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        self.scroll_area.setWidget(self.container_widget)
        main_layout.addWidget(self.scroll_area)
        
        # Transfer Butonu
        self.transfer_button = QPushButton()
        self.transfer_button.setObjectName("transfer_button")
        self.transfer_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.transfer_button.clicked.connect(self._on_button_clicked)
        self._update_button_text()
        self.transfer_button.setFixedWidth(150)
        main_layout.addWidget(self.transfer_button)
        
        # Scroll viewport drag-drop handler'ları
        self._setup_scroll_handlers()

    def show_empty_container(self):
        """Empty container'ı göster"""
        try:
            if not self.empty_container.isVisible():
                self.empty_container.show()
            
            self.empty_container.raise_()
            
            found = False
            for i in range(self.container_layout.count()):
                item = self.container_layout.itemAt(i)
                if item and item.widget() == self.empty_container:
                    found = True
                    self.container_layout.insertWidget(0, self.empty_container)
                    break
            
            if not found:
                self.container_layout.insertWidget(0, self.empty_container, 
                                                alignment=Qt.AlignmentFlag.AlignHCenter)
            
        except Exception:
            pass

    def hide_empty_container(self):
        """Empty container'ı gizle"""
        try:
            if self.empty_container.isVisible():
                self.empty_container.hide()
                    
        except Exception:
            pass
    
    def _setup_scroll_handlers(self):
        """Scroll area için drag-drop handler'ları kur"""
        def scroll_viewport_drag_enter(event):
            self.dragEnterEvent(event)
            
        def scroll_viewport_drag_move(event):
            event.acceptProposedAction()
            
        def scroll_viewport_drop(event):
            self.dropEvent(event)
            
        def scroll_viewport_drag_leave(event):
            self.dragLeaveEvent(event)
        
        self.scroll_area.viewport().dragEnterEvent = scroll_viewport_drag_enter
        self.scroll_area.viewport().dragMoveEvent = scroll_viewport_drag_move
        self.scroll_area.viewport().dropEvent = scroll_viewport_drop
        self.scroll_area.viewport().dragLeaveEvent = scroll_viewport_drag_leave
    
    def _setup_styles(self):
        """TEMEL STİLLER"""
        if self.is_left_side:
            button_color = "#FF9800"
            button_hover = "#F57C00"
            button_pressed = "#EF6C00"
            border_color = "#FF9800"
        else:
            button_color = "#4CAF50"
            button_hover = "#388E3C"
            button_pressed = "#2E7D32"
            border_color = "#4CAF50"
        
        self.setStyleSheet(f"""
            WaitingAreaBase {{
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 14px;
            }}
            
            QScrollArea#scroll_area {{
                background-color: #F9F9F9;
                border: none;
                border-top-left-radius: 14px;
                border-bottom-left-radius: 14px;
                border-right: 1px solid #E8E8E8;
            }}
            
            QScrollArea QScrollBar:vertical {{
                width: 0px;
                background: transparent;
                border: none;
            }}
            
            QScrollArea QScrollBar:horizontal {{
                height: 0px;
                background: transparent;
                border: none;
            }}
            
            QWidget#container_widget {{
                background-color: transparent;
                border: none;
            }}
            
            QFrame#empty_container {{
                background-color: transparent;
                border: none;
            }}
            
            QLabel#empty_label {{
                font-family: 'Segoe UI';
                font-size: 14px;
                font-weight: 500;
                color: #666666;
                background-color: transparent;
                padding: 8px;
                line-height: 1.4;
            }}
            
            QLabel#status_label {{
                font-family: 'Segoe UI';
                font-size: 12px;
                color: #888888;
                background-color: transparent;
                font-style: italic;
                font-weight: 400;
                padding: 3px;
            }}
            
            QPushButton#transfer_button {{
                background-color: {button_color};
                border: none;
                border-top-right-radius: 14px;
                border-bottom-right-radius: 14px;
                font-family: 'Segoe UI';
                font-size: 13px;
                font-weight: bold;
                color: #FFFFFF;
                padding: 0px 5px;
                margin: 0px;
                text-align: center;
                line-height: 1.3;
                min-height: 260px;
                min-width: 150px;
            }}
            
            QPushButton#transfer_button:hover {{
                background-color: {button_hover};
            }}
            
            QPushButton#transfer_button:pressed {{
                background-color: {button_pressed};
            }}
        """)
    
    def _update_drag_style(self, is_drag_over):
        """Drag over stilini güncelle - BASE"""
        if is_drag_over:
            border_color = "#FF9800" if self.is_left_side else "#4CAF50"
            highlight_color = "#FFF3E0" if self.is_left_side else "#E8F5E9"
            
            self.setStyleSheet(f"""
                WaitingAreaBase {{
                    background-color: #FFFFFF;
                    border: 2px solid {border_color};
                    border-radius: 14px;
                }}
                
                QScrollArea#scroll_area {{
                    background-color: {highlight_color};
                    border: none;
                    border-top-left-radius: 14px;
                    border-bottom-left-radius: 14px;
                    border-right: 1px solid {border_color};
                }}
                
                QLabel#empty_label {{
                    font-family: 'Segoe UI';
                    font-size: 14px;
                    font-weight: 600;
                    color: {border_color};
                    background-color: transparent;
                    padding: 8px;
                    line-height: 1.4;
                }}
                
                QLabel#status_label {{
                    font-family: 'Segoe UI';
                    font-size: 12px;
                    color: {border_color};
                    background-color: transparent;
                    font-style: italic;
                    font-weight: 500;
                    padding: 3px;
                }}
                
                QPushButton#transfer_button {{
                    background-color: {"#FF9800" if self.is_left_side else "#4CAF50"};
                    border: none;
                    border-top-right-radius: 14px;
                    border-bottom-right-radius: 14px;
                    font-family: 'Segoe UI';
                    font-size: 13px;
                    font-weight: bold;
                    color: #FFFFFF;
                    padding: 0px 5px;
                    margin: 0px;
                    text-align: center;
                    line-height: 1.3;
                    min-height: 260px;
                    min-width: 150px;
                }}
                
                QPushButton#transfer_button:hover {{
                    background-color: {"#F57C00" if self.is_left_side else "#388E3C"};
                }}
                
                QPushButton#transfer_button:pressed {{
                    background-color: {"#EF6C00" if self.is_left_side else "#2E7D32"};
                }}
            """)
        else:
            self._setup_styles()
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Drag olayını kabul et - BASE"""
        if event.mimeData().hasFormat("application/x-flashcard-operation"):
            event.acceptProposedAction()
            self.is_drag_over = True
            self._update_drag_style(True)
            
    def dragMoveEvent(self, event):
        """Drag hareket ederken - BASE"""
        event.acceptProposedAction()
        
    def dropEvent(self, event: QDropEvent):
        """Kart bırakıldığında - BASE"""
        self.dragLeaveEvent(event)
        from .drag_drop_manager import get_drag_drop_manager
        get_drag_drop_manager().process_drop(self, event, getattr(self, 'db', None))

    def dragLeaveEvent(self, event):
        """Drag alanından çıkıldığında - BASE"""
        self.is_drag_over = False
        self._update_drag_style(False)
        event.accept()
    
    def _update_button_text(self):
        """Buton metnini güncelle - BASE"""
        button_text = f"{self.target_box_title}\nkutusuna\ntaşı"
        self.transfer_button.setText(button_text)
        
    def _on_button_clicked(self):
        """Buton tıklandığında - BASE"""
        self.button_clicked.emit()
    
    def _update_container_height(self):
        """Container yüksekliğini güncelle - BASE"""
        card_count = len(self.cards)
        if card_count == 0:
            height = 260
        else:
            height = max(260, card_count * 130 + 20)
        
        self.container_widget.setMinimumHeight(height)
    
    def _scroll_to_bottom(self):
        """Scroll'u en alta kaydır - BASE"""
        scroll_bar = self.scroll_area.verticalScrollBar()
        if scroll_bar:
            scroll_bar.setValue(scroll_bar.maximum())
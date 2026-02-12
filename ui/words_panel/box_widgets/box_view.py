from PyQt6.QtWidgets import QFrame, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

# Import managers
from .design.style_manager import BoxStyleManager
from .state.state_manager import BoxStateManager
from .managers.animation_manager import AnimationManager
from .managers.event_handler import EventHandler
from .managers.title_manager import TitleManager


class BoxView(QFrame):
    # SADECE gerekli sinyaller
    title_changed = pyqtSignal(str)
    delete_requested = pyqtSignal(object)
    selection_changed = pyqtSignal(object, bool)

    def __init__(self, title="Yeni Kutu", db_id=None, db_connection=None, ui_index=None):
        super().__init__()
        
        self.db_id = db_id
        self.title = str(title)
        self.is_selected = False
        self.is_expanded = False
        self._force_expanded = False
        self._hover_active = True
        self.db_connection = db_connection
        self.ui_index = ui_index if ui_index is not None else 1
        self._deleted = False
        
        # UI referansları
        self.label = None
        self.editor = None
        self.card_counter = None
        self.checkbox = None
        self.enter_btn = None
        self.delete_btn = None
        self.card = None
        
        # UI'yi önce kur
        self._setup_ui()
        
        # Manager'ları UI kurulduktan sonra başlat
        self._initialize_managers()
        
        # İlk yükleme
        if self.state_manager:
            QTimer.singleShot(100, self._initial_load)
        else:
            self.update_card_counter(0, 0)

    def _initialize_managers(self):
        """Manager'ları başlat"""
        # State manager'ı başlat
        if self.db_connection:
            self.state_manager = BoxStateManager(self)
        else:
            self.state_manager = None
        
        # Diğer manager'lar
        self.animation_manager = AnimationManager(self)
        self.event_handler = EventHandler(self)
        self.title_manager = TitleManager(self)

    def _initial_load(self):
        """İlk yükleme"""
        if self._deleted or not self.state_manager:
            return
        
        try:
            self.state_manager.load_counts_with_sync()
        except Exception:
            self.update_card_counter(0, 0)

    def _setup_ui(self):
        """UI bileşenlerini kur"""
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        self.setStyleSheet("background: transparent; border: none;")

        self.setMinimumSize(
            BoxStyleManager.SIZES['base_width'],
            BoxStyleManager.SIZES['base_height']
        )

        self.setGraphicsEffect(BoxStyleManager.get_shadow_effect(self))

        # Card widget'ını oluştur
        self.card = QFrame(self)
        self.card.setObjectName("CardFrame")
        self.card.setStyleSheet(BoxStyleManager.get_card_stylesheet())

        from .design.layout_builder import build_box_design
        build_box_design(self, self.card)
        
        if self.label:
            self.label.setText(self.title)
        
        # Enter butonuna tıklama event'i bağla
        if self.enter_btn:
            self.enter_btn.clicked.connect(self._on_enter_clicked)

    def _on_enter_clicked(self):
        """Enter butonuna tıklandığında - DOĞRUDAN DETAIL WINDOW AÇ"""
        if self._deleted:
            return
        
        # Doğrudan detail window aç
        from .detail_window_opener import open_detail_window_for_box
        open_detail_window_for_box(self)

    # ==================== DELEGATE METHODS ====================
    def load_counts_with_sync(self):
        if self.state_manager:
            return self.state_manager.load_counts_with_sync()
        return 0, 0
    
    def refresh_card_counts(self):
        if self.state_manager:
            return self.state_manager.refresh_card_counts()
        self.update_card_counter(0, 0)
    
    def get_card_counts(self):
        if hasattr(self, 'card_counter') and self.card_counter:
            return self.card_counter.unknown_count, self.card_counter.known_count
        return 0, 0
    
    def update_card_counter_font_size(self, font_size: int):
        if not self._deleted and hasattr(self, 'card_counter'):
            self.card_counter.update_font_size(font_size)
    
    def update_card_counter(self, unknown_count: int, known_count: int):
        if not self._deleted and hasattr(self, 'card_counter'):
            self.card_counter.update_counts(unknown_count, known_count)

    # ==================== SELECTION METHODS ====================
    def set_selected(self, selected: bool):
        if self._deleted or not hasattr(self, 'checkbox'):
            return
            
        if self.is_selected != selected:
            self.is_selected = selected
            self.checkbox.setChecked(selected)
            
            if selected:
                self._force_expanded = True
                self._hover_active = False
                self.animation_manager.expand(immediate=True)
            else:
                self._force_expanded = False
                self._hover_active = True
                if not self.underMouse():
                    self.animation_manager.shrink(immediate=True)
                elif self.underMouse():
                    self.animation_manager.expand(immediate=True)
            
            self.selection_changed.emit(self, selected)
    
    def toggle_selection(self):
        if not self._deleted:
            self.set_selected(not self.is_selected)

    # ==================== TITLE METHODS ====================
    def enable_edit(self, event):
        self.title_manager.enable_edit(event)
    
    def finish_edit(self):
        self.title_manager.finish_edit()

    # ==================== EVENT METHODS ====================
    def resizeEvent(self, e):
        self.event_handler.handle_resize(e)
    
    def enterEvent(self, e):
        self.event_handler.handle_enter(e)
    
    def leaveEvent(self, e):
        self.event_handler.handle_leave(e)

    # ==================== UTILITY METHODS ====================
    def isDeleted(self):
        return self._deleted
    
    def deleteLater(self):
        self._deleted = True
        
        if self.state_manager:
            self.state_manager.cleanup()
        
        self.animation_manager.stop()
        
        try:
            self.setGraphicsEffect(None)
        except:
            pass
        
        super().deleteLater()
    
    def request_delete(self):
        if not self._deleted:
            try:
                # Parent widget'ı bul
                parent_widget = self
                while parent_widget.parent() and not parent_widget.isWindow():
                    parent_widget = parent_widget.parent()
                
                # Dialog başlığı ve mesajı (Türkçe karakterleri Unicode olarak yazalım)
                title = "Kutu Silme Onayı"
                message = ("Bu kutuyu silerseniz i\u00e7indeki t\u00fcm kelimeler "
                          "kal\u0131c\u0131 olarak silinecektir.\n"
                          "\u0130\u015flem geri al\u0131namaz.")
                
                # Dialog'u oluştur ve parent'ı ayarla
                msg_box = QMessageBox(parent_widget)
                msg_box.setWindowTitle(title)
                msg_box.setText(message)
                msg_box.setIcon(QMessageBox.Icon.Warning)
                
                # Dialog'un modal olmasını sağla (aynı pencere içinde)
                msg_box.setWindowModality(Qt.WindowModality.WindowModal)
                
                # Standart butonları kullan (daha güvenli)
                msg_box.setStandardButtons(
                    QMessageBox.StandardButton.Yes | 
                    QMessageBox.StandardButton.No
                )
                
                # Buton metinlerini ayarla
                msg_box.button(QMessageBox.StandardButton.Yes).setText("Evet")
                msg_box.button(QMessageBox.StandardButton.No).setText("Hay\u0131r")
                
                # Stil ayarları - daha basit ve etkili
                msg_box.setStyleSheet("""
                    QMessageBox {
                        font-family: Arial, sans-serif;
                        font-size: 12px;
                    }
                    QLabel {
                        color: black;
                    }
                    QPushButton {
                        color: black;
                        min-width: 80px;
                        min-height: 25px;
                        border: 1px solid #555;
                        border-radius: 3px;
                        padding: 5px 15px;
                    }
                    QPushButton#yesButton {
                        background-color: #f0f0f0;
                    }
                    QPushButton#noButton {
                        background-color: #f0f0f0;
                    }
                    QPushButton:hover {
                        background-color: #e0e0e0;
                    }
                """)
                
                # Butonlara ID ver
                yes_button = msg_box.button(QMessageBox.StandardButton.Yes)
                no_button = msg_box.button(QMessageBox.StandardButton.No)
                yes_button.setObjectName("yesButton")
                no_button.setObjectName("noButton")
                
                # Buton renklerini açıkça siyah yap
                yes_button.setStyleSheet("color: black;")
                no_button.setStyleSheet("color: black;")
                
                # Dialog'u göster
                result = msg_box.exec()
                
                # Eğer Evet seçildiyse silme işlemini gerçekleştir
                if result == QMessageBox.StandardButton.Yes:
                    if self.state_manager:
                        self.state_manager.request_delete()
                    self.delete_requested.emit(self)
                    
            except Exception as e:
                # Hata durumunda direk sil (eski davranış)
                print(f"Dialog hatası: {e}")
                if self.state_manager:
                    self.state_manager.request_delete()
                self.delete_requested.emit(self)
    
    def refresh(self):
        if not self._deleted and self.state_manager:
            self.state_manager.load_counts_with_sync()
            self.update()
    
    def set_db_connection(self, db_connection):
        self.db_connection = db_connection
        if not self.state_manager and db_connection:
            self.state_manager = BoxStateManager(self)
            QTimer.singleShot(100, self._initial_load)
        elif self.state_manager:
            self.state_manager.db_connection = db_connection
    
    def set_ui_index(self, index: int):
        self.ui_index = index
        if hasattr(self.state_manager, 'ui_index'):
            self.state_manager.ui_index = index
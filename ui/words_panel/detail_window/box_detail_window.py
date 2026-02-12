# ui/words_panel/detail_window/box_detail_window.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFrame, QHBoxLayout, QSizePolicy, QPushButton, QLineEdit
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QTimer, pyqtSignal, QEvent
from PyQt6.QtGui import QCursor
import sys
import os


class EditableTitle(QLineEdit):
    edit_finished = pyqtSignal(str)
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QLineEdit {
                background: transparent; 
                border: none; 
                font-size: 28px; 
                font-weight: 700; 
                color: #202020; 
                selection-background-color: #e8e8e8; 
                selection-color: #202020;
            }
            QLineEdit:focus {
                background: transparent; 
                border: none;
            }
        """)
        self.setMinimumHeight(45)
        self.setMaximumHeight(65)
        self.setPlaceholderText("Başlık girin...")
        self.returnPressed.connect(self.finish_editing)
        self.setReadOnly(True)
        self.normal_cursor = QCursor(Qt.CursorShape.ArrowCursor)
        self.edit_cursor = QCursor(Qt.CursorShape.IBeamCursor)
        self.setCursor(self.normal_cursor)
        self._last_text = text
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setReadOnly(False)
            self.setCursor(self.edit_cursor)
            self.setFocus()
            QTimer.singleShot(10, lambda: self.end(False))
            event.accept()
    
    def finish_editing(self):
        self.setReadOnly(True)
        self.setCursor(self.normal_cursor)
        self.clearFocus()
        text = self.text().strip()
        if text:
            self._last_text = text
            self.edit_finished.emit(text)
        else:
            self.setText(self._last_text)
    
    def focusOutEvent(self, event):
        if not self.isReadOnly():
            self.finish_editing()
        super().focusOutEvent(event)
    
    def setText(self, text: str):
        self._last_text = text
        super().setText(text)


class BoxDetailWindow(QWidget):
    _all_windows = {}
    window_opened = pyqtSignal(int)
    
    def __init__(self, parent=None, db=None, box_id=None, box_title="", origin_widget=None):
        super().__init__(parent)
        
        self.box_id = box_id
        self.box_title = box_title
        self.words_window = parent
        self.db = db
        self.origin_widget = origin_widget
        self.is_visible = False
        self.current_animation = None
        self.cards_loaded = False
        
        # Place holder
        self.placeholder = None
        
        # İçeriğin fade-in animasyonu için
        self.content_opacity_animation = None
        
        # Eğer db None ise, parent'tan almaya çalış
        if not self.db and parent:
            if hasattr(parent, 'db'):
                self.db = parent.db
            else:
                current_parent = parent.parent()
                while current_parent and not self.db:
                    if hasattr(current_parent, 'db') and current_parent.db:
                        self.db = current_parent.db
                        break
                    current_parent = current_parent.parent()
        
        # Content widget'ı DB'den sonra oluştur
        self.content_widget = self.load_content_widget()
        
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(300, 200)
        self.setStyleSheet("BoxDetailWindow {background-color: #ffffff; border: none;}")
        
        self.setup_ui()
        self.hide()
        
        if box_id in BoxDetailWindow._all_windows:
            old_window = BoxDetailWindow._all_windows[box_id]
            if old_window != self:
                old_window.close_window_immediate()
                old_window.deleteLater()
        
        BoxDetailWindow._all_windows[box_id] = self
        
        # Place holder oluştur
        self.create_placeholder()
    
    def create_placeholder(self):
        """Place holder oluştur"""
        try:
            from .box_detail_placeholder import BoxDetailPlaceholder
            
            self.placeholder = BoxDetailPlaceholder(self)
            
            # Fade-out tamamlandı sinyalini bağla
            self.placeholder.fade_out_completed.connect(self._on_placeholder_fade_out_completed)
            
            self.placeholder.hide()
        except ImportError:
            self.placeholder = None
        except Exception:
            self.placeholder = None
    
    def _on_placeholder_fade_out_completed(self):
        """Place holder fade-out tamamlandığında içeriği fade-in ile göster"""
        # İç container'ı göster (ama önce saydam)
        self.inner_container.show()
        self.inner_container.setWindowOpacity(0.0)
        
        # İçeriği fade-in ile göster
        self.content_opacity_animation = QPropertyAnimation(self.inner_container, b"windowOpacity")
        self.content_opacity_animation.setDuration(400)
        self.content_opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.content_opacity_animation.setStartValue(0.0)
        self.content_opacity_animation.setEndValue(1.0)
        
        def on_fade_in_finished():
            self.content_opacity_animation = None
        
        self.content_opacity_animation.finished.connect(on_fade_in_finished)
        self.content_opacity_animation.start()
    
    def setup_ui(self):
        # Ana layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Ana container
        self.main_container = QFrame()
        self.main_container.setStyleSheet("QFrame {background: #ffffff; border: 2px solid #e0e0e0; border-left: none;}")
        self.main_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        main_layout.addWidget(self.main_container)
        
        # Ana container içindeki layout
        container_layout = QVBoxLayout(self.main_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # İç container - normal içerik (başlangıçta saydam)
        self.inner_container = QWidget()
        self.inner_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.inner_container.setWindowOpacity(0.0)
        
        content_layout = QVBoxLayout(self.inner_container)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)
        
        # Üst kısım
        top_container = QWidget()
        top_layout = QHBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(15)
        
        self.title_label = EditableTitle(self.box_title)
        self.title_label.edit_finished.connect(self._on_title_changed)
        top_layout.addWidget(self.title_label, 1)
        
        self.close_button = QPushButton("✕")
        self.close_button.setFixedSize(30, 30)
        self.close_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #f8f8f8; 
                border: 1px solid #e0e0e0; 
                border-radius: 15px; 
                font-size: 12px; 
                color: #666666;
            }
            QPushButton:hover {
                background-color: #f0f0f0; 
                color: #333333; 
                border: 1px solid #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #e8e8e8;
            }
        """)
        self.close_button.clicked.connect(self.close_window)
        top_layout.addWidget(self.close_button, 0, Qt.AlignmentFlag.AlignTop)
        
        content_layout.addWidget(top_container)
        
        # Kart ekle butonu
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        self.add_card_button = QPushButton("Kart ekle")
        self.add_card_button.clicked.connect(self._on_add_card_clicked)
        self.add_card_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.add_card_button.setStyleSheet("""
            QPushButton {
                background-color: #10b981; 
                color: white; 
                border: none; 
                border-radius: 6px;
                padding: 8px 12px; 
                font-size: 13px; 
                font-weight: 700; 
                min-width: 100px; 
                max-width: 110px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:pressed {
                background-color: #047857; 
                padding: 9px 12px 7px 12px;
            }
        """)
        button_layout.addWidget(self.add_card_button, 0, Qt.AlignmentFlag.AlignLeft)
        button_layout.addStretch(1)
        content_layout.addWidget(button_container)
        
        # Ayraç
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("border-top: 1px solid #f0f0f0; margin: 5px 0px;")
        separator.setFixedHeight(1)
        content_layout.addWidget(separator)
        
        # Content widget
        content_layout.addWidget(self.content_widget, 1)
        
        # İç container'ı ana container'a ekle
        container_layout.addWidget(self.inner_container)
    
    def load_content_widget(self):
        """Content widget'ı yükle - FİKS VERSİYON"""
        print(f"\n🚨 BoxDetailContent yükleniyor...")
        
        try:
            import os
            import sys
            
            # 1. box_detail_content.py'nin tam yolunu bul
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)  # words_panel klasörü
            
            print(f"📁 Current dir: {current_dir}")
            print(f"📁 Parent dir: {parent_dir}")
            
            # 2. Python path'ine ekle
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            # 3. IMPORT ET!
            try:
                # İlk deneme: detail_window klasöründen
                from detail_window.box_detail_content import BoxDetailContent
                print("✅ Import başarılı (detail_window.box_detail_content)")
            except ImportError as e:
                print(f"❌ Import hatası 1: {e}")
                
                # İkinci deneme: doğrudan
                import importlib.util
                
                content_file = os.path.join(current_dir, "box_detail_content.py")
                print(f"📄 Content file: {content_file}")
                print(f"📄 File exists: {os.path.exists(content_file)}")
                
                if os.path.exists(content_file):
                    spec = importlib.util.spec_from_file_location(
                        "box_detail_content_module", 
                        content_file
                    )
                    module = importlib.util.module_from_spec(spec)
                    sys.modules["box_detail_content_module"] = module
                    spec.loader.exec_module(module)
                    
                    BoxDetailContent = module.BoxDetailContent
                    print("✅ Dinamik import başarılı")
                else:
                    raise ImportError(f"Dosya bulunamadı: {content_file}")
            
            # 4. Widget'ı oluştur
            content_widget = BoxDetailContent()
            print(f"✅ BoxDetailContent oluşturuldu: {content_widget}")
            
            # 5. DB ve box_id'yi ata
            if hasattr(content_widget, 'db'):
                content_widget.db = self.db
                print(f"✅ DB atandı")
            
            if hasattr(content_widget, 'box_id'):
                content_widget.box_id = self.box_id
                print(f"✅ Box ID atandı: {self.box_id}")
            
            return content_widget
            
        except Exception as e:
            print(f"❌ CRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback - en azından container'ları ayır
            from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel
            
            widget = QWidget()
            widget.setStyleSheet("background-color: #f8f9fa;")
            
            # YAN YANA CONTAINER'LAR
            layout = QHBoxLayout(widget)  # HBoxLayout - yan yana!
            layout.setSpacing(20)
            
            # Sol container - Bilmediklerim
            left_frame = QFrame()
            left_frame.setStyleSheet("""
                QFrame {
                    background-color: #f8f9fa;
                    border: 2px solid #3b82f6;
                    border-radius: 8px;
                    min-width: 300px;
                }
            """)
            left_layout = QVBoxLayout(left_frame)
            left_label = QLabel("<h2>Bilmediklerim</h2>")
            left_label.setStyleSheet("color: #3b82f6; padding: 10px;")
            left_layout.addWidget(left_label)
            
            # Sağ container - Öğrendiklerim
            right_frame = QFrame()
            right_frame.setStyleSheet("""
                QFrame {
                    background-color: #f8f9fa;
                    border: 2px solid #10b981;
                    border-radius: 8px;
                    min-width: 300px;
                }
            """)
            right_layout = QVBoxLayout(right_frame)
            right_label = QLabel("<h2>Öğrendiklerim</h2>")
            right_label.setStyleSheet("color: #10b981; padding: 10px;")
            right_layout.addWidget(right_label)
            
            layout.addWidget(left_frame, 1)
            layout.addWidget(right_frame, 1)
            
            print("⚠️ Fallback widget oluşturuldu (yan yana container'lar)")
            return widget
    
    def _on_title_changed(self, new_title):
        """Başlık değiştiğinde hem DB'yi hem de state JSON'ını güncelle"""
        old_title = self.box_title
        self.box_title = new_title
        
        if self.db:
            try:
                self.db.update_box_title(self.box_id, new_title)
            except Exception:
                pass
        
        try:
            self._update_state_json_title(new_title, old_title)
        except Exception:
            pass
        
        if self.origin_widget:
            try:
                if hasattr(self.origin_widget, 'set_title'):
                    self.origin_widget.set_title(new_title)
                elif hasattr(self.origin_widget, 'label'):
                    self.origin_widget.label.setText(new_title)
                    if hasattr(self.origin_widget, 'title_changed'):
                        self.origin_widget.title_changed.emit(new_title)
            except Exception:
                pass
    
    def _update_state_json_title(self, new_title: str, old_title: str):
        """State JSON dosyasının adını ve içeriğini güncelle"""
        try:
            # Multiple import denemesi
            try:
                from ui.words_panel.detail_window.internal.states.state_loader import BoxDetailStateLoader
            except ImportError:
                try:
                    from .internal.states.state_loader import BoxDetailStateLoader
                except ImportError:
                    return
            
            ui_index = getattr(self.origin_widget, 'ui_index', 1) if self.origin_widget else 1
            
            state_loader = BoxDetailStateLoader(self.db)
            state = state_loader.load_or_create(self.box_id, old_title, ui_index)
            state.box_title = new_title
            state.mark_dirty()
            state.save()
                
        except Exception:
            pass
    
    def _on_add_card_clicked(self):
        """Kart ekle butonu tıklandığında"""
        if hasattr(self.content_widget, 'add_new_card'):
            if not hasattr(self.content_widget, 'db') or not self.content_widget.db:
                self.content_widget.db = self.db
            
            if not hasattr(self.content_widget, 'box_id') or not self.content_widget.box_id:
                self.content_widget.box_id = self.box_id
            
            self.content_widget.add_new_card()
    
    def load_box_cards(self):
        """Kartları yükle"""
        if self.cards_loaded:
            return
        
        if not self.db:
            if not self.db and self.parent():
                parent = self.parent()
                while parent and not self.db:
                    if hasattr(parent, 'db') and parent.db:
                        self.db = parent.db
                        self.content_widget.db = self.db
                        break
                    parent = parent.parent()
            
            if not self.db:
                return
        
        if not self.box_id:
            return
        
        if hasattr(self.content_widget, 'load_cards'):
            if not hasattr(self.content_widget, 'db') or not self.content_widget.db:
                self.content_widget.db = self.db
            
            if not hasattr(self.content_widget, 'box_id') or not self.content_widget.box_id:
                self.content_widget.box_id = self.box_id
            
            self.content_widget.load_cards(self.db, self.box_id)
            self.cards_loaded = True
    
    def show_placeholder(self):
        """Place holder'ı göster"""
        if self.placeholder:
            # Place holder'ı main_container'ın üstüne ekle
            if self.placeholder.parent() != self.main_container:
                self.placeholder.setParent(self.main_container)
            
            # Tüm alanı kapla
            self.placeholder.setGeometry(0, 0, self.main_container.width(), self.main_container.height())
            self.placeholder.raise_()
            
            # İç container'ı gizle
            self.inner_container.hide()
            
            # Animasyonlu göster
            self.placeholder.show_animated(duration=300)
    
    def hide_placeholder(self):
        """Place holder'ı gizle - yumuşak fade-out"""
        if self.placeholder:
            # Fade-out başlat
            self.placeholder.hide_animated(duration=500)
        else:
            # Place holder yoksa içeriği direkt göster
            self.inner_container.show()
            self.inner_container.setWindowOpacity(1.0)
    
    @classmethod
    def get_or_create_window(cls, parent, db, box_id, box_title):
        """Window'u al veya oluştur"""
        if not db and parent:
            if hasattr(parent, 'db'):
                db = parent.db
            else:
                current_parent = parent.parent()
                while current_parent and not db:
                    if hasattr(current_parent, 'db') and current_parent.db:
                        db = current_parent.db
                        break
                    current_parent = current_parent.parent()
        
        if box_id in cls._all_windows:
            window = cls._all_windows[box_id]
            if window and hasattr(window, 'box_id'):
                if window.parent() != parent:
                    window.setParent(parent)
                    window.words_window = parent
                
                if window.box_title != box_title:
                    window.box_title = box_title
                    window.title_label.setText(box_title)
                
                if db and not window.db:
                    window.db = db
                
                if hasattr(window, 'content_widget'):
                    window.content_widget.db = db
                    window.content_widget.box_id = box_id
                
                return window
        
        return cls(parent=parent, db=db, box_id=box_id, box_title=box_title)
    
    def open_window(self):
        if self.is_visible:
            self.close_window()
            return
        
        for window_id, window in list(BoxDetailWindow._all_windows.items()):
            if window != self and window and window.is_visible:
                window.close_window_immediate()
        
        if not self.words_window:
            return
        
        if self.parent() != self.words_window:
            self.setParent(self.words_window)
            self.words_window = self.parent()
        
        self._calculate_and_set_initial_position()
        
        start_rect = QRect(-self.width(), self.target_y, self.width(), self.height())
        target_rect = QRect(0, self.target_y, self.width(), self.height())
        
        self.setGeometry(start_rect)
        self.show()
        self.raise_()
        
        # İç container'ı saydam yap
        self.inner_container.setWindowOpacity(0.0)
        
        # Place holder'ı göster
        if self.placeholder:
            QTimer.singleShot(10, self.show_placeholder)
        
        if self.current_animation:
            self.current_animation.stop()
        
        self.current_animation = QPropertyAnimation(self, b"geometry")
        self.current_animation.setDuration(400)
        self.current_animation.setEasingCurve(QEasingCurve.Type.OutQuart)
        self.current_animation.setStartValue(start_rect)
        self.current_animation.setEndValue(target_rect)
        
        def on_animation_finished():
            self.is_visible = True
            self.window_opened.emit(self.box_id)
            if self.words_window:
                self.words_window.installEventFilter(self)
            self.current_animation = None
            
            # Kartları yükle
            self.load_box_cards()
            
            # Place holder'ı gizle
            QTimer.singleShot(300, self.hide_placeholder)
        
        self.current_animation.finished.connect(on_animation_finished)
        self.current_animation.start()
    
    def _calculate_and_set_initial_position(self):
        if not self.words_window:
            return
        
        words_width = self.words_window.width()
        words_height = self.words_window.height()
        
        header_height = 80
        if hasattr(self.words_window, 'container'):
            container = self.words_window.container
            container_pos = container.mapTo(self.words_window, container.rect().topLeft())
            header_height = container_pos.y()
        
        self.window_width = words_width - 10
        self.window_height = words_height - header_height - 8
        self.target_y = header_height
        
        self.resize(self.window_width, self.window_height)
    
    def eventFilter(self, obj, event):
        if obj == self.words_window and event.type() == QEvent.Type.Resize:
            QTimer.singleShot(50, self.update_position_and_size)
        return super().eventFilter(obj, event)
    
    def close_window(self):
        if not self.is_visible:
            return
        
        if self.words_window:
            self.words_window.removeEventFilter(self)
        
        if self.current_animation:
            self.current_animation.stop()
            self.current_animation = None
        
        # Animasyonları durdur
        if self.content_opacity_animation:
            self.content_opacity_animation.stop()
            self.content_opacity_animation = None
        
        current_rect = self.geometry()
        target_rect = QRect(-self.width(), current_rect.y(), self.width(), current_rect.height())
        
        close_animation = QPropertyAnimation(self, b"geometry")
        close_animation.setDuration(400)
        close_animation.setEasingCurve(QEasingCurve.Type.InQuart)
        close_animation.setStartValue(current_rect)
        close_animation.setEndValue(target_rect)
        
        def on_close_finished():
            self.hide()
            self.is_visible = False
            self.current_animation = None
            
            if self.box_id in BoxDetailWindow._all_windows and BoxDetailWindow._all_windows[self.box_id] == self:
                del BoxDetailWindow._all_windows[self.box_id]
        
        close_animation.finished.connect(on_close_finished)
        close_animation.start()
        self.current_animation = close_animation
    
    def close_window_immediate(self):
        self.hide()
        self.is_visible = False
        
        if self.current_animation:
            self.current_animation.stop()
            self.current_animation = None
        
        if self.content_opacity_animation:
            self.content_opacity_animation.stop()
            self.content_opacity_animation = None
        
        if self.words_window:
            self.words_window.removeEventFilter(self)
        
        if self.placeholder:
            self.placeholder.hide()
        
        if self.box_id in BoxDetailWindow._all_windows and BoxDetailWindow._all_windows[self.box_id] == self:
            del BoxDetailWindow._all_windows[self.box_id]
    
    def toggle_window(self):
        if self.is_visible:
            self.close_window()
        else:
            self.open_window()
    
    @classmethod
    def hide_all_windows(cls):
        for window in list(cls._all_windows.values()):
            if window and window.is_visible:
                window.close_window_immediate()
    
    def update_position_and_size(self):
        if not self.is_visible or not self.words_window:
            return
        self._calculate_and_set_initial_position()
        self.setGeometry(QRect(0, self.target_y, self.window_width, self.window_height))
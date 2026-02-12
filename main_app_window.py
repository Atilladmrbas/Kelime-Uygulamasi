# main_app_window.py - DÜZELTİLMİŞ VERSİYON (flash_sync_manager TAMAMEN KALDIRILDI)
from PyQt6.QtWidgets import QTabWidget, QApplication, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer
from ui.boxes_panel.boxes_window import BoxesWindow
from ui.words_panel.words_window import WordsWindow
from ui.calendar_panel.calendar_window import CalendarWindow
from core.database import Database
from ui.words_panel.detail_window.box_detail_controller import get_controller
from three_buttons import ThreeButtons

class MainAppWindow(QTabWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kelime Uygulaması")
        self.setMinimumSize(1400, 800)
        
        self.db = Database()
        self._initialize_boxes()

        # ❌ FlashCardsSyncManager TAMAMEN KALDIRILDI - senkronizasyon zaten CopySyncManager üzerinden çalışıyor

        # Önce tab'leri oluştur, SONRA overlay observer
        self.boxes_tab_widget = self._create_boxes_tab()

        # Controller'ı başlat
        self.controller = get_controller(self.db)
        
        self.words_window = WordsWindow()
        self.calendar_window = CalendarWindow()

        self.words_window.db = self.db
        
        # Tab'leri ekle
        self.addTab(self.boxes_tab_widget, "Kutular")
        self.addTab(self.words_window, "Kelimeler")
        self.addTab(self.calendar_window, "Takvim")
        
        self.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background: #ffffff;
                border-radius: 4px;
                top: -1px;
            }
            QTabBar {
                background: #ffffff;
            }
            QTabBar::tab {
                background: #ffffff;
                padding: 12px 24px;
                margin-right: 2px;
                border: 1px solid #cccccc;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-family: 'Segoe UI';
                font-size: 15px;
                color: #666666;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                font-weight: bold;
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
            }
            QTabBar::tab:hover {
                background: #f8f9fa;
                color: #333333;
            }
        """)
        
        self.setMovable(False)
        self.setTabsClosable(False)
        
        self._connect_signals()
        
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
        # Tab değişimi için gecikmeli bağlantı
        QTimer.singleShot(100, lambda: self._reset_tab_colors(0))
        
        # Overlay sistemini geciktirilmiş başlat
        QTimer.singleShot(500, self._initialize_overlay_system)

    def _create_boxes_tab(self):
        """Kutular sekmesini oluştur"""
        tab_widget = QWidget()
        main_layout = QVBoxLayout(tab_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        boxes_window = BoxesWindow(db=self.db)
        self.boxes_window = boxes_window
        
        main_layout.addWidget(boxes_window, 1)
        
        # ThreeButtons widget'ını ekle
        self.three_buttons = ThreeButtons(self.db)
        self.three_buttons.delete_all_copy_cards.connect(
            lambda: self.three_buttons._execute_delete_all_copy_cards(self.boxes_window)
        )
        self.three_buttons.move_all_cards_to_selected_box.connect(
            lambda box_id: self.three_buttons._execute_move_to_selected_box(box_id, self.boxes_window)
        )
        self.three_buttons.move_all_cards_to_last_locations.connect(
            lambda: self.three_buttons._execute_move_to_last_locations(self.boxes_window)
        )
        
        main_layout.addWidget(self.three_buttons)
        
        return tab_widget

    def _initialize_boxes(self):
        """Varsayılan kutuları oluştur"""
        cursor = self.db.conn.cursor()
        default_boxes = [
            ("Her gün", 1),
            ("İki günde bir", 2),
            ("Dört günde bir", 3),
            ("Dokuz günde bir", 4),
            ("On dört günde bir", 5)
        ]
        
        for box_title, order in default_boxes:
            cursor.execute("SELECT id FROM boxes WHERE title = ?", (box_title,))
            if not cursor.fetchone():
                self.db.add_box(box_title)

    def _connect_signals(self):
        """Sinyal bağlantılarını kur"""
        self.currentChanged.connect(self._on_tab_changed)
        
        if hasattr(self.words_window, 'buttons') and hasattr(self.words_window.buttons, 'switch_to_boxes_tab'):
            self.words_window.buttons.switch_to_boxes_tab.connect(self.switch_to_boxes_tab)
        
        if hasattr(self.words_window, 'slide_to_boxes_requested'):
            self.words_window.slide_to_boxes_requested.connect(self.switch_to_boxes_tab)
        
        if hasattr(self.words_window, 'transfer_requested'):
            self.words_window.transfer_requested.connect(self._on_transfer_completed)

    def _on_tab_changed(self, index):
        """Sekme değiştiğinde detail window'ları yönet"""
        try:
            from ui.words_panel.detail_window.box_detail_window import BoxDetailWindow
            
            if index == 1:
                for window in BoxDetailWindow._all_windows.values():
                    if window and window.is_visible and window.words_window == self.words_window:
                        window.show()
                        window.raise_()
            else:
                for window in BoxDetailWindow._all_windows.values():
                    if window and window.is_visible:
                        window.hide()
                        
        except Exception:
            pass
        
        QTimer.singleShot(200, self._refresh_overlays_for_tab)

    def _refresh_overlays_for_tab(self):
        """Sekme değiştiğinde overlay'ları güncelle"""
        if hasattr(self, 'overlay_observer') and self.overlay_observer:
            self.overlay_observer._batch_update_overlays()

    def _on_transfer_completed(self, boxes):
        """Transfer tamamlandığında kutuları güncelle"""
        if hasattr(self.boxes_window, 'update_all_counts'):
            self.boxes_window.update_all_counts()
        
        QTimer.singleShot(300, self._refresh_all_overlays)

    def switch_to_boxes_tab(self):
        """Kutular sekmesine geç"""
        self.setCurrentIndex(0)
        self._update_boxes()
        
        QTimer.singleShot(100, self._refresh_all_overlays)

    def _update_boxes(self):
        """Kutuları güncelle"""
        if hasattr(self.boxes_window, 'update_all_counts'):
            self.boxes_window.update_all_counts()

    def _reset_tab_colors(self, index):
        """Tab renklerini sıfırla"""
        tab_bar = self.tabBar()
        for i in range(self.count()):
            if i == index:
                tab_bar.setTabTextColor(i, Qt.GlobalColor.darkGray)
            else:
                tab_bar.setTabTextColor(i, Qt.GlobalColor.gray)

    def showEvent(self, event):
        """Pencere gösterildiğinde"""
        super().showEvent(event)
        if hasattr(self.boxes_window, 'update_all_counts'):
            self.boxes_window.update_all_counts()
        
        QTimer.singleShot(800, self._initialize_overlay_system)

    def _initialize_overlay_system(self):
        """Overlay sistemini başlat"""
        try:
            from ui.boxes_panel.overlay_observer import get_overlay_observer
            
            self.overlay_observer = get_overlay_observer()
            self.overlay_observer.db = self.db
            
            # Mevcut kartları kaydet
            self._register_existing_cards()
            
        except ImportError:
            pass
        except Exception:
            pass

    def _register_existing_cards(self):
        """Mevcut kartları overlay sistemine kaydet"""
        if not hasattr(self, 'overlay_observer') or not self.overlay_observer:
            return
        
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if not app:
                return
            
            from ui.words_panel.button_and_cards.flashcard_view import FlashCardView
            
            for widget in app.allWidgets():
                if isinstance(widget, FlashCardView):
                    if hasattr(widget, 'is_copy_card') and not widget.is_copy_card:
                        self.overlay_observer.register_original_card(widget)
                        
                        if not hasattr(widget, 'color_overlay') or not widget.color_overlay:
                            self._init_card_overlay(widget)
            
        except ImportError:
            pass
        except Exception:
            pass

    def _init_card_overlay(self, card_widget):
        """Kart widget'ına overlay başlat"""
        try:
            from ui.words_panel.button_and_cards.color_overlay import ColorOverlayWidget
            
            card_widget.color_overlay = ColorOverlayWidget(parent_card=card_widget)
            
            if hasattr(card_widget.color_overlay, 'overlay_updated'):
                card_widget.color_overlay.overlay_updated.connect(
                    lambda: card_widget.update() if card_widget else None
                )
            
            QTimer.singleShot(300, lambda: card_widget.color_overlay.schedule_lazy_update()
                              if hasattr(card_widget, 'color_overlay') else None)
            
        except ImportError:
            pass
        except Exception:
            pass

    def _refresh_all_overlays(self):
        """Tüm overlay'ları yenile"""
        if not hasattr(self, 'overlay_observer') or not self.overlay_observer:
            return
        
        self.overlay_observer._batch_update_overlays()

    def closeEvent(self, event):
        """Uygulama kapanırken temizlik yap"""
        try:
            boxes_window = self.findChild(BoxesWindow)
            if boxes_window:
                boxes_window.restore_cards_to_original_boxes()
            
            if hasattr(self, 'boxes_window') and self.boxes_window:
                self.boxes_window.restore_cards_to_original_boxes()
                    
        except Exception:
            pass
        
        self._cleanup_overlay_system()
        
        # ❌ flash_sync_manager cleanup TAMAMEN KALDIRILDI
        
        event.accept()

    def _cleanup_overlay_system(self):
        """Overlay sistemini temizle"""
        if not hasattr(self, 'overlay_observer') or not self.overlay_observer:
            return
        
        try:
            if hasattr(self.overlay_observer, 'update_timer') and self.overlay_observer.update_timer.isActive():
                self.overlay_observer.update_timer.stop()
            
            for card_id, card_list in list(self.overlay_observer.original_cards.items()):
                for card_widget in card_list[:]:
                    try:
                        if hasattr(card_widget, 'color_overlay') and card_widget.color_overlay:
                            card_widget.color_overlay.cleanup()
                    except Exception:
                        pass
            
            if hasattr(self.overlay_observer, 'clear_cache'):
                self.overlay_observer.clear_cache()
            
        except Exception:
            pass


def create_main_app_window():
    return MainAppWindow()
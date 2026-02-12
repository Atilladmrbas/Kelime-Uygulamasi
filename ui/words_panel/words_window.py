# ui/words_panel/words_window.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
import json

from ui.words_panel.words_container.container_boxes import WordsContainer
from ui.words_panel.buttons_panel import ButtonsPanel
from core.database import Database
from ui.words_panel.button_and_cards.card_teleporter import CardTeleporter
from ui.words_panel.detail_window.box_detail_controller import init_controller


class WordsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kelimeler")
        self.setMinimumSize(800, 600)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
            }
        """)

        self.db = Database()
        self.teleporter = CardTeleporter(self)
        
        # Controller'ı başlat
        self.controller = init_controller(self.db)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(15)

        self.container = WordsContainer(self.db)
        self.container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_layout.addWidget(self.container, stretch=1)
        self.container.teleporter = self.teleporter
        self.container.box_added_callback = self.on_box_added

        self._create_bottom_panel()
        self.main_layout.addWidget(self.bottom_panel, stretch=0)

        QTimer.singleShot(100, self._initial_load)
    
    def open_box_detail(self, box):
        """Kutu için detail window aç"""
        if not self.db:
            return None
        
        from ui.words_panel.detail_window.box_detail_window import BoxDetailWindow
        
        window = BoxDetailWindow.get_or_create_window(
            parent=self,
            db=self.db,
            box_id=box.db_id,
            box_title=box.title,
            origin_widget=box
        )
        
        window.open_window()
        return window
    
    def _create_bottom_panel(self):
        """Responsive buton paneli"""
        self.bottom_panel = QWidget(self)
        self.bottom_panel.setObjectName("BottomPanel")
        
        self.bottom_panel.setMinimumHeight(80)
        self.bottom_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        self.bottom_panel.setStyleSheet("""
            QWidget#BottomPanel {
                background: transparent;
                border: none;
            }
        """)
        
        bottom_layout = QHBoxLayout(self.bottom_panel)
        bottom_layout.setContentsMargins(20, 10, 20, 10)
        bottom_layout.setSpacing(0)
        
        self.buttons = ButtonsPanel(self.bottom_panel)
        self.buttons.setParent(self.bottom_panel)
        self.buttons.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        
        bottom_layout.addWidget(self.buttons, alignment=Qt.AlignmentFlag.AlignLeft)
        bottom_layout.addStretch(1)
        
        self.buttons.copy_to_everyday_requested.connect(self.copy_cards_to_everyday_box)

    def copy_cards_to_everyday_box(self):
        """Seçili kutulardaki SADECE BİLMEDİKLERİM (bucket=0) kartları 'Her gün' kutusuna kopyala"""
        if not self.db:
            return
        
        try:
            # Seçili kutuları al
            selected_boxes = []
            if hasattr(self.container, 'boxes'):
                for box in self.container.boxes:
                    if hasattr(box, 'is_selected') and box.is_selected:
                        if hasattr(box, 'db_id'):
                            selected_boxes.append(box.db_id)
            
            if not selected_boxes:
                return
            
            # 'Her gün' kutusundaki tüm kopyaları çekilmemiş yap
            self.db.reset_drawn_status_in_box(1)
            
            processed_count = 0
            
            for box_id in selected_boxes:
                # ✅ DEĞİŞİKLİK: SADECE BİLMEDİKLERİM (bucket=0) container'ındaki orijinal kartları al
                original_cards = self._get_unknown_original_cards_from_database(box_id)
                
                for card in original_cards:
                    original_id = card['id']
                    
                    # Kopya oluştur veya mevcut kopyayı al
                    copy_id = self.db.get_available_copy(original_id, 1)
                    
                    if copy_id:
                        # Kopyayı 'Her gün' kutusuna taşı
                        self.db.update_word_box(copy_id, 1)
                        self.db.mark_card_as_drawn(copy_id, False)  # Çekilmemiş yap
                        processed_count += 1
            
            # ✅ DEĞİŞİKLİK: Başarılı mesajı KALDIRILDI (sessiz işlem)
            # Sadece kutuları güncelle
            
            # Kutuları güncelle
            self._refresh_all_memory_boxes()
            
            # Kutular sekmesine geç
            if hasattr(self.buttons, 'switch_to_boxes_tab'):
                self.buttons.switch_to_boxes_tab.emit()
            
        except Exception:
            # ✅ DEĞİŞİKLİK: Hata mesajı da KALDIRILDI (sessiz hata yönetimi)
            pass

    def _clear_all_drawn_cards_lists(self):
        """Tüm MemoryBox'ların çekilmiş kart listelerini temizle"""
        try:
            # Ana pencereyi bul
            main_window = self.window()
            
            # BoxesWindow'ı bul
            if hasattr(main_window, 'boxes_window'):
                boxes_window = main_window.boxes_window
                
                # Tüm MemoryBox widget'larını bul
                memory_boxes = self._find_all_memory_boxes(boxes_window)
                
                for memory_box in memory_boxes:
                    if hasattr(memory_box, '_drawn_card_ids'):
                        memory_box._drawn_card_ids.clear()
            
        except Exception:
            pass

    def _find_all_memory_boxes(self, widget):
        """Widget içindeki tüm MemoryBox'ları bul"""
        memory_boxes = []
        
        try:
            # Eğer widget kendisi MemoryBox ise
            if hasattr(widget, '__class__') and 'MemoryBox' in widget.__class__.__name__:
                memory_boxes.append(widget)
            
            # Çocuk widget'ları kontrol et
            for child in widget.children():
                memory_boxes.extend(self._find_all_memory_boxes(child))
                
        except Exception:
            pass
        
        return memory_boxes

    def _mark_card_as_not_drawn(self, copy_card_id):
        """Bir kopya kartın "çekilmiş" durumunu sıfırla"""
        try:
            # Ana pencereyi bul
            main_window = self.window()
            
            # BoxesWindow'ı bul
            if hasattr(main_window, 'boxes_window'):
                boxes_window = main_window.boxes_window
                
                # Tüm MemoryBox widget'larını bul
                memory_boxes = self._find_all_memory_boxes(boxes_window)
                
                for memory_box in memory_boxes:
                    if hasattr(memory_box, '_drawn_card_ids'):
                        if copy_card_id in memory_box._drawn_card_ids:
                            memory_box._drawn_card_ids.remove(copy_card_id)
            
        except Exception:
            pass

    def _refresh_all_memory_boxes(self):
        """Tüm MemoryBox'ların kart sayılarını güncelle"""
        try:
            # Ana pencereyi bul
            main_window = self.window()
            
            # BoxesWindow'ı bul
            if hasattr(main_window, 'boxes_window'):
                boxes_window = main_window.boxes_window
                
                # Tüm MemoryBox widget'larını bul
                memory_boxes = self._find_all_memory_boxes(boxes_window)
                
                for memory_box in memory_boxes:
                    if hasattr(memory_box, 'update_card_count'):
                        memory_box.update_card_count()
            
        except Exception:
            pass
    
    def _get_unknown_original_cards_from_database(self, box_id):
        """Sadece bilmediklerim'deki (bucket=0) orijinal kartları getir"""
        unknown_original_cards = []
        
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("""
                SELECT id, english, turkish, detail, box, bucket 
                FROM words 
                WHERE box = ? AND bucket = 0 AND is_copy = 0
            """, (box_id,))
            
            rows = cursor.fetchall()
            
            for row in rows:
                card_data = {
                    "id": row[0],
                    "english": row[1],
                    "turkish": row[2],
                    "detail": row[3],
                    "box_id": row[4],
                    "bucket": row[5]
                }
                unknown_original_cards.append(card_data)
            
        except Exception:
            pass
        
        return unknown_original_cards
    
    def _copy_bubble_data(self, original_id, new_id):
        """Bubble verisini kopyala"""
        try:
            from ui.words_panel.button_and_cards.bubble.bubble_persistence import load_bubble, save_bubble
            
            bubble_data = load_bubble(original_id)
            if bubble_data:
                if isinstance(bubble_data, dict):
                    html_content = bubble_data.get('html', bubble_data.get('html_content', ''))
                else:
                    html_content = str(bubble_data)
                
                from ui.words_panel.button_and_cards.bubble.note_bubble import NoteBubble
                temp_bubble = NoteBubble(parent=None, card_view=None, state=None, db=self.db)
                temp_bubble.text.setHtml(html_content)
                
                save_bubble(temp_bubble, new_id)
                
        except Exception:
            pass
    
    def _refresh_memory_boxes(self):
        """Memory box sayaçlarını güncelle"""
        try:
            main_window = self.window()
            if main_window and hasattr(main_window, 'boxes_window'):
                if hasattr(main_window.boxes_window.design, 'update_all_counts'):
                    main_window.boxes_window.design.update_all_counts()
                    
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        window_width = self.width()
        
        if window_width < 1000:
            if hasattr(self.buttons, 'btn_word'):
                self.buttons.btn_word.set_responsive_size(300, 100)
        else:
            if hasattr(self.buttons, 'btn_word'):
                self.buttons.btn_word.set_responsive_size(380, 120)
        
        if hasattr(self.container, 'rearrange'):
            QTimer.singleShot(10, self.container.rearrange)
        
        # BoxDetailWindow'ları güncelle
        QTimer.singleShot(50, self._update_detail_windows_position)
    
    def _update_detail_windows_position(self):
        """Tüm açık BoxDetailWindow'ların pozisyonunu güncelle"""
        try:
            from ui.words_panel.detail_window.box_detail_window import BoxDetailWindow
            
            for box_id, window in BoxDetailWindow._all_windows.items():
                if window and window.is_visible and window.words_window == self:
                    window.update_position_and_size()
        except ImportError:
            pass
    
    def _initial_load(self):
        self.container.load_boxes_from_db()
        
        for box in self.container.boxes:
            self._connect_box_signals(box)

    def _connect_box_signals(self, box):
        try:
            box.selection_changed.disconnect()
        except:
            pass
        
        box.selection_changed.connect(self._handle_box_selection)

    def on_box_added(self, box):
        self._connect_box_signals(box)

    def _handle_box_selection(self, box, is_selected):
        selected_boxes = [b for b in self.container.boxes if b.is_selected]
        selected_count = len(selected_boxes)
        
        self.buttons.update_opacity(selected_count)
        
        if hasattr(self.buttons, 'update_selected_boxes'):
            self.buttons.update_selected_boxes(selected_boxes)
# ui/words_panel/detail_window/card_scroll_layout.py
"""
Kart grid'i ve smooth scroll yönetimi için tek sınıf
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFrame, QGridLayout
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QScrollArea, QSizePolicy


class SmoothScrollArea(QScrollArea):
    """Yumuşak scroll özellikli QScrollArea"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Config
        self.scroll_step = 80
        self.animation_duration = 250
        self.multiplier = 2.5
    
    def wheelEvent(self, event: QWheelEvent):
        """Yumuşak wheel scroll"""
        delta = event.angleDelta().y()
        direction = 1 if delta > 0 else -1
        scroll_bar = self.verticalScrollBar()
        current_value = scroll_bar.value()
        
        target_value = current_value - (direction * self.scroll_step * self.multiplier)
        min_value = scroll_bar.minimum()
        max_value = scroll_bar.maximum()
        
        # Sınır kontrolü
        if target_value < min_value:
            target_value = min_value
        elif target_value > max_value:
            target_value = max_value
        
        # Animasyon
        self.animation = QPropertyAnimation(scroll_bar, b"value")
        self.animation.setDuration(self.animation_duration)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.setStartValue(current_value)
        self.animation.setEndValue(target_value)
        self.animation.start()
        
        event.accept()


class CardScrollLayout(QFrame):
    """
    Kartların grid layout'u ve smooth scroll'unu yöneten ana widget
    SABİT GRID LAYOUT - RENK FİLTRESİNDEN ETKİLENMEZ!
    """
    
    def __init__(self, container_type="unknown", config=None, parent=None):
        """
        Args:
            container_type: "unknown" veya "learned"
            config: Layout ayarları dictionary'si
            parent: Parent widget
        """
        super().__init__(parent)
        self.container_type = container_type
        
        # Varsayılan config - SABİT DEĞERLER!
        self.config = {
            'card_size': (260, 120),      # (width, height) - SABİT
            'columns': 3,                  # Grid kolon sayısı - SABİT!
            'row_spacing': 20,            # Satır arası boşluk - SABİT
            'col_spacing': 30,            # Kolon arası boşluk - SABİT
            'padding': (15, 25, 20, 25),  # top, right, bottom, left - SABİT
            'title_height': 70,           
            'divider_height': 2,
        }
        
        # Config'i güncelle (sadece başlangıçta)
        if config:
            self.config.update(config)
            # columns ASLA değişmez!
            self.config['columns'] = 3
        
        # Widget listesi
        self.card_widgets = []
        self.visible_cards = []  # SADECE görünen kartlar
        
        # Ana layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # UI'yı kur
        self.setup_ui()
    
    def setup_ui(self):
        """UI widget'larını oluştur"""
        # Scroll area ve grid
        self.scroll_area = SmoothScrollArea()
        self.scroll_area.setSizePolicy(
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Expanding
        )
        
        # Grid widget
        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background-color: transparent;")
        
        # Grid layout - SABIT column stretch ile!
        self.grid_layout = QGridLayout(self.grid_widget)
        self._update_grid_layout_margins()
        self.grid_layout.setHorizontalSpacing(self.config['col_spacing'])
        self.grid_layout.setVerticalSpacing(self.config['row_spacing'])
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        # Sütunları eşit genişlikte yap - ÇOK ÖNEMLİ!
        for col in range(self.config['columns']):
            self.grid_layout.setColumnStretch(col, 1)
        
        # Scroll area'ya grid'i ekle
        self.scroll_area.setWidget(self.grid_widget)
        
        # Ana layout'a ekle
        self.main_layout.addWidget(self.scroll_area, 1)
        
        # Stil
        self.setStyleSheet("""
            CardScrollLayout {
                background-color: #f8f9fa;
                border: none;
                border-radius: 8px;
            }
        """)
        self.setMinimumWidth(300)
    
    def _update_grid_layout_margins(self):
        """Grid layout margin'lerini config'den güncelle - SABİT"""
        self.grid_layout.setContentsMargins(
            self.config['padding'][3],    # left
            self.config['padding'][0],    # top  
            self.config['padding'][1],    # right
            self.config['padding'][2]     # bottom
        )
    
    def add_card(self, card_widget):
        """
        Kart widget'ını grid'e ekle
        """
        if not card_widget:
            return False
        
        # Kart boyutunu ayarla - SABİT
        card_widget.setFixedSize(*self.config['card_size'])
        card_widget.setMinimumSize(*self.config['card_size'])
        card_widget.setMaximumSize(*self.config['card_size'])
        
        # Listeye ekle
        self.card_widgets.append(card_widget)
        self.visible_cards.append(card_widget)
        
        # Grid'e ekle
        self._add_card_to_grid(card_widget)
        
        # Grid boyutunu güncelle
        self._update_grid_size()
        
        return True
    
    def _add_card_to_grid(self, card_widget):
        """Kartı grid layout'a ekle - SABİT KOLON SAYISI"""
        card_count = len(self.card_widgets)
        row = (card_count - 1) // self.config['columns']
        col = (card_count - 1) % self.config['columns']
        
        # Parent'ı güncelle
        if card_widget.parent() != self.grid_widget:
            card_widget.setParent(self.grid_widget)
        
        # Layout'a ekle - SATIR VE SÜTUN BELİRT!
        self.grid_layout.addWidget(card_widget, row, col, Qt.AlignmentFlag.AlignCenter)
        card_widget.show()
    
    def remove_card(self, card_widget):
        """
        Kart widget'ını grid'den çıkar
        """
        if card_widget not in self.card_widgets:
            return False
        
        # Listelerden çıkar
        self.card_widgets.remove(card_widget)
        if card_widget in self.visible_cards:
            self.visible_cards.remove(card_widget)
        
        # Grid'den çıkar
        self.grid_layout.removeWidget(card_widget)
        card_widget.hide()
        
        # Grid'i yeniden düzenle - SABİT KOLON SAYISIYLA!
        self._rearrange_grid()
        
        # Grid boyutunu güncelle
        self._update_grid_size()
        
        return True
    
    def _rearrange_grid(self):
        """
        Grid'deki tüm kartları yeniden düzenle - DÜZELTİLDİ!
        TÜM kartları sıfırdan yerleştirir.
        """
        # TÜM widget'ları grid'den çıkar
        widgets_to_keep = []
        
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                if widget in self.card_widgets and widget in self.visible_cards:
                    widgets_to_keep.append(widget)
                else:
                    widget.hide()
        
        # Görünen kartları SIRAYLA grid'e ekle
        for i, card in enumerate(widgets_to_keep):
            row = i // self.config['columns']
            col = i % self.config['columns']
            
            if card.parent() != self.grid_widget:
                card.setParent(self.grid_widget)
            
            self.grid_layout.addWidget(card, row, col, Qt.AlignmentFlag.AlignCenter)
            card.show()
        
        self.visible_cards = widgets_to_keep
    
    def _update_grid_size(self):
        """
        Grid widget'ının boyutunu hesapla ve ayarla
        SABİT FORMÜL - RENKTEN ETKİLENMEZ!
        """
        visible_count = len(self.visible_cards)
        
        if visible_count == 0:
            # Boş grid için - scroll area boyutunda
            self.grid_widget.setFixedSize(
                self.scroll_area.width() - 10,
                self.scroll_area.height() - 10
            )
            return
        
        # SABİT: Her zaman 3 kolon!
        rows = (visible_count + 2) // 3  # 3 kolon, yukarı yuvarla
        
        card_w, card_h = self.config['card_size']
        
        # SABİT grid boyutu hesaplama
        grid_width = 3 * card_w + 2 * self.config['col_spacing']
        grid_height = rows * card_h + (rows - 1) * self.config['row_spacing']
        
        # Padding ekle
        grid_width += self.config['padding'][1] + self.config['padding'][3]
        grid_height += self.config['padding'][0] + self.config['padding'][2]
        
        # Minimum genişlik - scroll area'dan az olmasın
        min_width = self.scroll_area.width() - 20
        if grid_width < min_width:
            grid_width = min_width
        
        # Boyutu ayarla
        self.grid_widget.setFixedSize(grid_width, grid_height)
    
    def clear_all_cards(self):
        """Tüm kartları temizle"""
        for card in self.card_widgets[:]:
            self.remove_card(card)
    
    def filter_cards(self, filter_func, immediate=True):
        """
        Kartları filtrele - DÜZELTİLDİ: Görünen kartlar YENİDEN SIRALANIR!
        
        Args:
            filter_func: Kart widget'ını alıp bool döndüren fonksiyon
            immediate: Hemen uygula (False ise QTimer ile)
        """
        def apply_filter():
            print(f"🔍 [CardScrollLayout] Filtre uygulanıyor - {self.container_type}")
            
            # 1. TÜM kartları grid'den çıkar
            all_widgets = []
            while self.grid_layout.count():
                item = self.grid_layout.takeAt(0)
                if item.widget():
                    widget = item.widget()
                    all_widgets.append(widget)
                    widget.hide()  # Önce hepsini gizle
            
            # 2. Görünmesi gereken kartları bul ve SIRALA
            self.visible_cards = []
            for card in self.card_widgets:
                if filter_func(card):
                    self.visible_cards.append(card)
                    card.show()
                else:
                    card.hide()
            
            print(f"   - Toplam kart: {len(self.card_widgets)}")
            print(f"   - Görünen kart: {len(self.visible_cards)}")
            print(f"   - Kolon sayısı: {self.config['columns']} (SABİT)")
            
            # 3. SADECE görünen kartları SIRAYLA grid'e ekle (0'dan başlayarak)
            for i, card in enumerate(self.visible_cards):
                row = i // self.config['columns']
                col = i % self.config['columns']
                
                if card.parent() != self.grid_widget:
                    card.setParent(self.grid_widget)
                
                # Grid'e ekle - SATIR/SÜTUN BELİRT!
                self.grid_layout.addWidget(card, row, col, Qt.AlignmentFlag.AlignCenter)
                card.show()
                card.raise_()
            
            # 4. Grid boyutunu güncelle
            self._update_grid_size()
            
            # 5. Scroll'u sıfırla
            self.scroll_area.verticalScrollBar().setValue(0)
            
            # 6. Layout'u güncellemeye zorla
            self.grid_widget.updateGeometry()
            self.scroll_area.updateGeometry()
            self.updateGeometry()
            
            print(f"✅ [CardScrollLayout] Filtre uygulandı - {len(self.visible_cards)} kart gösteriliyor")
        
        if immediate:
            apply_filter()
        else:
            QTimer.singleShot(10, apply_filter)
    
    def resizeEvent(self, event):
        """Boyut değiştiğinde grid'i yeniden düzenle"""
        super().resizeEvent(event)
        QTimer.singleShot(50, self._delayed_resize_update)
    
    def _delayed_resize_update(self):
        """Gecikmeli resize güncellemesi"""
        self._update_grid_size()
        self._rearrange_grid()
    
    def get_card_count(self):
        """Toplam kart sayısını döndür"""
        return len(self.card_widgets)
    
    def get_visible_card_count(self):
        """Görünen kart sayısını döndür"""
        return len(self.visible_cards)
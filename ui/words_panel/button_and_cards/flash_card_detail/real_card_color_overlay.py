# file: ui/words_panel/button_and_cards/flash_card_detail/real_card_color_overlay.py

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QColor, QBrush, QPainterPath


class ColorOverlayWidget(QWidget):
    """
    Orijinal kartların üzerinde gösterilen renk kılıfı.
    YUVARLAK KÖŞELİ - KARTLARLA AYNI!
    """
    
    overlay_updated = pyqtSignal()
    
    # Koyu memory box renkleri
    BOX_COLORS = {
        1: QColor(158, 161, 167),  # Kutu 1 - Koyu gri
        2: QColor(131, 102, 138),  # Kutu 2 - Koyu lavanta
        3: QColor(67, 124, 144),   # Kutu 3 - Koyu mavi
        4: QColor(170, 157, 46),   # Kutu 4 - Koyu sarı
        5: QColor(51, 147, 48),    # Kutu 5 - Koyu yeşil
    }
    
    def __init__(self, parent_card=None):
        super().__init__(parent_card)
        
        self.card = parent_card
        self.db = None
        self.is_visible = False
        self.is_loaded = False
        self.target_boxes = {}
        
        # Fare olaylarını geç
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # Arkaplan tamamen transparan
        self.setStyleSheet("background-color: transparent;")
        
        # Zamanlayıcı - 0 ms!
        self.lazy_timer = QTimer(self)
        self.lazy_timer.setSingleShot(True)
        self.lazy_timer.timeout.connect(self._load_and_update)
        self.lazy_timer.setInterval(0)
        
        # Başlangıçta gizle
        self.hide()
        
        print(f"🆕 ColorOverlayWidget oluşturuldu (YUVARLAK KÖŞELİ) - {self}")
    
    def set_database(self, db):
        self.db = db
    
    def schedule_lazy_update(self, force=False):
        if not self.is_loaded or force:
            self._load_and_update()
    
    def _load_and_update(self):
        if not self.card or not self.db or not self.card.card_id:
            return
        
        try:
            card_id = self.card.card_id
            
            cursor = self.db.conn.cursor()
            cursor.execute("""
                SELECT box, COUNT(*) as count 
                FROM words 
                WHERE original_card_id = ? AND is_copy = 1
                AND box BETWEEN 1 AND 5
                GROUP BY box
                ORDER BY count DESC
                LIMIT 1
            """, (card_id,))
            
            row = cursor.fetchone()
            
            self.target_boxes = {}
            
            if row:
                box_id = row[0] if row[0] is not None else 0
                count = row[1]
                self.target_boxes = {box_id: count}
                print(f"📊 Overlay: Kutu {box_id} - {count} kopya")
            
            self.is_loaded = True
            self._update_overlay_visibility()
            self.overlay_updated.emit()
            
        except Exception as e:
            print(f"❌ Overlay yükleme hatası: {e}")
            self.target_boxes = {}
            self.hide()
    
    def _update_overlay_visibility(self):
        if not self.card or not hasattr(self.card, 'bucket_id'):
            return
        
        if self.card.bucket_id == 0 and self.target_boxes:
            self.is_visible = True
            
            # Tam kart boyutunda
            self.setGeometry(0, 0, self.card.width(), self.card.height())
            self.setFixedSize(self.card.width(), self.card.height())
            
            # EN ÜSTE ÇIK
            self.show()
            self.raise_()
            self.update()
            
            box_id = list(self.target_boxes.keys())[0]
            print(f"✅ Overlay GÖSTERİLDİ! Kutu {box_id}")
        else:
            self.is_visible = False
            self.hide()
    
    def update_for_card_move(self, target_box_id):
        if not self.card or self.card.bucket_id != 0:
            return
        
        try:
            if not self.db or not self.card.card_id:
                self.schedule_lazy_update()
                return
            
            card_id = self.card.card_id
            
            cursor = self.db.conn.cursor()
            cursor.execute("""
                SELECT box, COUNT(*) as count 
                FROM words 
                WHERE original_card_id = ? AND is_copy = 1
                AND box BETWEEN 1 AND 5
                GROUP BY box
                ORDER BY count DESC
                LIMIT 1
            """, (card_id,))
            
            row = cursor.fetchone()
            
            self.target_boxes = {}
            
            if row:
                box_id = row[0] if row[0] is not None else 0
                count = row[1]
                self.target_boxes = {box_id: count}
                print(f"🔄 Overlay güncellendi: Kutu {box_id} - {count} kopya")
            
            self._update_overlay_visibility()
            
        except Exception as e:
            print(f"❌ update_for_card_move hatası: {e}")
            self.schedule_lazy_update()
    
    def parent_resized(self):
        if self.is_visible and self.card:
            self.setGeometry(0, 0, self.card.width(), self.card.height())
            self.setFixedSize(self.card.width(), self.card.height())
            self.update()
    
    def paintEvent(self, event):
        """YUVARLAK KÖŞELİ - Kartlarla aynı!"""
        if not self.is_visible or not self.target_boxes:
            return
        
        # En üstte olduğundan emin ol
        self.raise_()
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)  # YUVARLAK KÖŞELER İÇİN!
        
        # YUVARLAK KÖŞELİ PATH oluştur (14px - kartlarla aynı!)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 14, 14)
        
        # Clipping uygula - sadece yuvarlak köşeli alanı boya
        painter.setClipPath(path)
        
        # Sadece İLK kutunun rengini al
        box_id = list(self.target_boxes.keys())[0]
        base_color = self.BOX_COLORS.get(box_id, QColor(158, 161, 167))
        
        # %20 opaklık
        overlay_color = QColor(base_color.red(), base_color.green(), base_color.blue(), 51)
        
        # TAM KARTI BOYA - ama sadece yuvarlak köşeli alanı!
        painter.fillRect(0, 0, self.width(), self.height(), overlay_color)
        
        painter.end()
    
    def _hide_overlay(self):
        self.is_visible = False
        self.hide()
    
    def cleanup(self):
        self.lazy_timer.stop()
        self.hide()
        self.setParent(None)
        self.deleteLater()
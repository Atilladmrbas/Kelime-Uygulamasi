# flashcard_panel.py - GÜNCELLENMİŞ VE DÜZELTİLMİŞ
from __future__ import annotations

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QPropertyAnimation, QRect, QEasingCurve, QTimer

from ui.words_panel.button_and_cards.flashcard_view import FlashCardView  # ✅ DOĞRU IMPORT
from core.flashcard_model import FlashCardData


class FlashCardPanel(QWidget):
    """
    SADECE:
    - box IS NULL olan kartlar
    - üretim (spawn) alanı
    Container'a giren kart burada tutulmaz.
    """

    def __init__(self, db=None, parent=None):
        super().__init__(parent)

        self.db = db
        self.cards: list[FlashCardView] = []

        self.card_w = 260
        self.card_h = 120
        self.overlap = 22

        self.setMinimumHeight(self.card_h)
        self.setStyleSheet("background: transparent;")
        
        self.load_unassigned_cards()
    
    # =================================================
    # LOAD CARDS
    # =================================================
    
    def load_unassigned_cards(self):
        """Paneli yeniden yükle"""
        # Önce mevcut kartları temizle
        for card in self.cards[:]:
            try:
                card.hide()
                card.setParent(None)
                card.deleteLater()
            except Exception:
                pass
        self.cards.clear()
        
        # DB'den box_id NULL olan kartları al
        rows = self.db.get_unassigned_words()
        for row in rows:
            data = FlashCardData(
                english=row.get("english", ""),
                turkish=row.get("turkish", ""),
                detail=row.get("detail", ""),
                box=None,
                id=row.get("id"),
            )
            self._spawn_loaded_card(data)

    def _spawn_loaded_card(self, data: FlashCardData):
        parent_container = self.parent()

        card = FlashCardView(data, parent=parent_container, db=self.db)

        # Silme bağlantısı
        try:
            card.delete_requested.disconnect()
        except Exception:
            pass
        card.delete_requested.connect(self.delete_card)

        card.is_newly_created = False
        card.home_panel = self

        self.cards.append(card)
        card.show()

        self.reposition_all()

    # =================================================
    # CARD MANAGEMENT
    # =================================================
    
    def delete_card(self, card_view):
        # sadece panel kartları
        if card_view not in self.cards:
            return

        # Bubble'ı temizle
        bubble = getattr(card_view, "bubble", None)
        if bubble:
            bubble.hide()
            bubble.setParent(None)
            bubble.deleteLater()
            card_view.bubble = None

        # DB'den sil (eğer kayıtlı kartsa)
        if not getattr(card_view, "is_newly_created", False):
            card_id = getattr(card_view, "card_id", None)
            if card_id:
                try:
                    self.db.delete_word(int(card_id))
                except Exception:
                    pass

        # Kartı listeden kaldır
        self.cards.remove(card_view)
        try:
            card_view.hide()
            card_view.setParent(None)
            card_view.deleteLater()
        except Exception:
            pass

        self.reposition_all()

    def remove_card_from_panel(self, card: FlashCardView):
        if card in self.cards:
            self.cards.remove(card)
            try:
                card.hide()
                card.setParent(None)
                card.deleteLater()
            except Exception:
                pass
            self.reposition_all()

    # =================================================
    # ADD NEW CARD
    # =================================================
    
    def add_card_from_button(self, button, en, tr):
        parent_container = self.parent()

        card = FlashCardView(
            data=None,
            parent=parent_container,
            db=self.db
        )

        # Silme bağlantısı
        try:
            card.delete_requested.disconnect()
        except Exception:
            pass
        card.delete_requested.connect(self.delete_card)

        card.is_newly_created = True
        card.home_panel = self

        self.cards.append(card)

        positions = self.compute_positions()
        final_x, final_y = positions[-1] if positions else (0, 0)

        btn_rect = button.geometry()
        start_x = btn_rect.center().x() - self.card_w // 2
        start_y = btn_rect.center().y() - self.card_h // 2

        card.setGeometry(start_x, start_y, self.card_w, self.card_h)
        card.show()
        card.stackUnder(button)

        anim = QPropertyAnimation(card, b"geometry", self)
        anim.setDuration(420)
        anim.setStartValue(QRect(start_x, start_y, self.card_w, self.card_h))
        anim.setEndValue(QRect(final_x, final_y, self.card_w, self.card_h))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        anim.start()
        card._spawn_anim = anim
        anim.finished.connect(self.reposition_all)

    # =================================================
    # POSITIONING
    # =================================================
    
    def compute_positions(self):
        positions = []

        parent_container = self.parent()
        button = parent_container.btn_word
        btn_rect = button.geometry()

        panel_w = self.width()
        base_y = btn_rect.center().y() - self.card_h // 2
        base_x = panel_w - self.card_w - 10

        for i in range(len(self.cards)):
            positions.append((base_x - i * self.overlap, base_y))

        return positions

    def reposition_all(self):
        positions = self.compute_positions()

        alive = []
        for c, (x, y) in zip(self.cards, positions):
            try:
                c.move(x, y)
                alive.append(c)
            except RuntimeError:
                pass

        self.cards = alive

    def resizeEvent(self, event):
        self.reposition_all()
        return super().resizeEvent(event)
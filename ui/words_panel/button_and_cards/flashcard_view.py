from __future__ import annotations

import json
import uuid

from PyQt6.QtWidgets import (
    QFrame, QLineEdit, QPushButton,
    QWidget, QGraphicsOpacityEffect,
    QMenu, QApplication,
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpacerItem,
    QSizePolicy
)
from PyQt6.QtGui import (
    QFont, QPainter, QColor, QLinearGradient,
    QPen, QAction, QCursor
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QSize,
    QMimeData, QByteArray, QPoint, QRect
)

from ui.words_panel.button_and_cards.bubble.note_bubble import NoteBubble
from ui.words_panel.button_and_cards.bubble.bubble_opening import open_bubble, close_bubble
from ui.words_panel.button_and_cards.bubble.bubble_persistence import load_bubble, delete_bubble, save_bubble

from ui.words_panel.button_and_cards.flash_card_detail.original_card_dialogs import (
    show_original_card_delete_dialog
)

from ui.words_panel.button_and_cards.flash_card_detail.real_card_color_overlay import ColorOverlayWidget


class DynamicField(QLineEdit):
    delete_requested = pyqtSignal(object)
    text_changed_signal = pyqtSignal()
    text_committed = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.setFont(QFont("Segoe UI", 10))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.IBeamCursor)
        self.setStyleSheet("""
            QLineEdit {
                background: #ebebeb;
                border: 1px solid rgba(0,0,0,0.06);
                border-radius: 6px;
                color: #222;
                padding: 1px 2px;
                margin: 0px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(0,0,0,0.18);
                background: #efefef;
            }
        """)
        
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        self.textChanged.connect(self._on_text_changed)
        
        self._original_text = ""
        self._is_modified = False
        self._last_saved_text = ""

    def _on_text_changed(self):
        current_text = self.text()
        if current_text != self._original_text:
            self._is_modified = True
            self.text_changed_signal.emit()
        else:
            self._is_modified = False

    def _show_context_menu(self, position):
        menu = QMenu()
        
        delete_action = QAction("Delete", menu)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self))
        menu.addAction(delete_action)
        
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                color: black;
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QMenu::item {
                background-color: transparent;
                color: black;
                padding: 6px 16px;
                margin: 2px;
                border-radius: 3px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: #e3f2fd;
            }
        """)
        
        menu.exec(self.mapToGlobal(position))

    def mouseDoubleClickEvent(self, e):
        """Çift tıklama ile düzenlemeyi aç"""
        self.setReadOnly(False)
        self.selectAll()
        self.setFocus()
        super().mouseDoubleClickEvent(e)

    def returnPressed(self):
        """Enter tuşuna basıldığında"""
        if self._is_modified:
            new_text = self.text()
            self._original_text = new_text
            self._is_modified = False
            
            self.text_committed.emit(new_text)
            
            if hasattr(self.parent(), "sync_data"):
                self.parent().sync_data()
        
        self.clearFocus()
        super().returnPressed()

    def focusOutEvent(self, e):
        """Focus kaybolduğunda"""
        super().focusOutEvent(e)
        self.setReadOnly(True)
        
        if self._is_modified:
            new_text = self.text()
            self._original_text = new_text
            self._is_modified = False
            
            self.text_committed.emit(new_text)
            
            if hasattr(self.parent(), "sync_data"):
                self.parent().sync_data()

    def setText(self, text: str):
        """Metni ayarla ve orijinal metni güncelle"""
        super().setText(text)
        self._original_text = text
        self._last_saved_text = text
        self._is_modified = False

    def get_original_text(self):
        """Orijinal metni döndür"""
        return self._original_text

    def get_is_modified(self):
        """Değiştirilip değiştirilmediğini döndür"""
        return self._is_modified


class FlashCardView(QFrame):
    delete_requested = pyqtSignal(object)
    updated = pyqtSignal(object)
    card_clicked = pyqtSignal(object)
    
    MAX_FIELDS = 3

    def __init__(self, data=None, parent=None, db=None):
        super().__init__(parent)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMouseTracking(True)

        self.data = data
        self.db = db
        self.card_id = None
        self.box_id = None
        self.bucket_id = 0
        self.front = True
        self.bubble_open = False
        self.is_newly_created = False
        self.temp_id = None
        self.is_copy_card = False
        
        self.is_selected_for_teleport = False
        self.selection_manager = None
        
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        self.teleporter = None
        self._init_teleporter()

        self.W, self.H = 260, 120
        self.setFixedSize(self.W, self.H)

        self.front_fields = []
        self.back_fields = []
        
        self.plus_front = QPushButton("+", self)
        self.plus_back = QPushButton("+", self)
        for btn, is_front in ((self.plus_front, True), (self.plus_back, False)):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, f=is_front: self._add_field(f))
            self._apply_plus_style(btn)

        self.flip_btn = QPushButton("↺", self)
        self.del_btn = QPushButton("🗑", self)
        self.note_btn = QPushButton("T", self)

        for btn in (self.flip_btn, self.del_btn, self.note_btn):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
            self._apply_action_button_style(btn)

        self.flip_btn.clicked.connect(self.toggle)
        self.del_btn.clicked.connect(self.on_delete_clicked)
        self.note_btn.clicked.connect(self.toggle_bubble)

        self._create_field(True, "")
        self._create_field(False, "")

        self.bubble = NoteBubble(
            parent=self, 
            card_view=self, 
            state=None, 
            db=self.db,
            is_copy=False
        )
        self.bubble.hide()
        self.bubble.text.textChanged.connect(self.on_bubble_text_changed)

        self._relayout()
        
        self.color_overlay = None
        
        if data is not None:
            self.bind_model(data)
        else:
            self.temp_id = str(uuid.uuid4())[:8]
            self.is_newly_created = True
            if self.front_fields:
                self.front_fields[0].setText("")
                self.front_fields[0]._original_text = ""
            if self.back_fields:
                self.back_fields[0].setText("")
                self.back_fields[0]._original_text = ""

    def _init_color_overlay(self):
        """Renk kılıfını başlat - HEMEN OLUŞTUR, HEMEN GÖSTER!"""
        if hasattr(self, 'is_copy_card') and self.is_copy_card:
            return
        
        print(f"🎨 [_init_color_overlay] Overlay oluşturuluyor - Kart: {self.card_id}")
        
        # Mevcut overlay varsa temizle
        if self.color_overlay:
            try:
                self.color_overlay.cleanup()
            except:
                pass
            self.color_overlay = None
        
        # YENİ overlay oluştur
        self.color_overlay = ColorOverlayWidget(parent_card=self)
        self.color_overlay.set_database(self.db)
        self.color_overlay.overlay_updated.connect(self._on_overlay_updated)
        
        # Overlay'i KARTIN ÜZERİNE yerleştir
        self.color_overlay.setParent(self)
        self.color_overlay.setGeometry(0, 0, self.width(), self.height())
        
        # EN ÖNEMLİ: Overlay'i en üste getir ve göster
        self.color_overlay.raise_()
        self.color_overlay.show()
        
        # HEMEN veri yükleme başlasın!
        if self.card_id and self.db:
            self.color_overlay.schedule_lazy_update(force=True)
        
        print(f"✅ [_init_color_overlay] Overlay oluşturuldu ve gösterildi")
    
    def _lazy_init_overlay(self):
        """Overlay'ı geciktirilmiş başlat"""
        if self.color_overlay and self.card_id and self.db:
            if hasattr(self, 'bucket_id') and self.bucket_id == 0:
                self.color_overlay.schedule_lazy_update()
    
    def _on_overlay_updated(self):
        """Overlay güncellendiğinde"""
        self.update()
    
    def _init_teleporter(self):
        """CardTeleporter'ı bul"""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'card_teleporter') and parent.card_teleporter:
                self.teleporter = parent.card_teleporter
                return self.teleporter
            if hasattr(parent, 'teleporter') and parent.teleporter:
                self.teleporter = parent.teleporter
                return self.teleporter
            parent = parent.parent()
        
        main_window = self.window()
        if main_window:
            if hasattr(main_window, 'card_teleporter') and main_window.card_teleporter:
                self.teleporter = main_window.card_teleporter
                return self.teleporter
            if hasattr(main_window, 'teleporter') and main_window.teleporter:
                self.teleporter = main_window.teleporter
                return self.teleporter
        
        return None

    def _force_show_overlay(self):
        """Overlay'i zorla göster - HEMEN, KARTLA BERABER!"""
        try:
            if not hasattr(self, 'is_copy_card') or self.is_copy_card:
                return
            
            if not hasattr(self, 'color_overlay') or self.color_overlay is None:
                self._init_color_overlay()
            
            if self.color_overlay and self.bucket_id == 0:
                # Veritabanını kontrol et - HEMEN
                if self.db and self.card_id:
                    try:
                        cursor = self.db.conn.cursor()
                        cursor.execute("""
                            SELECT COUNT(*) FROM words 
                            WHERE original_card_id = ? AND is_copy = 1
                        """, (self.card_id,))
                        count = cursor.fetchone()[0]
                        
                        if count > 0:
                            print(f"🚨 ZORLA overlay gösteriliyor! Kopya sayısı: {count}")
                            
                            # EN ÇOK KOPYA OLAN MEMORY BOX'U BUL (1-5 ARASI)
                            cursor.execute("""
                                SELECT box, COUNT(*) as count 
                                FROM words 
                                WHERE original_card_id = ? AND is_copy = 1
                                AND box BETWEEN 1 AND 5
                                GROUP BY box
                                ORDER BY count DESC
                                LIMIT 1
                            """, (self.card_id,))
                            
                            row = cursor.fetchone()
                            
                            if row:
                                box_id = row[0] if row[0] is not None else 0
                                count = row[1]
                                
                                # Overlay'e verileri yükle
                                self.color_overlay.target_boxes = {box_id: count}
                                self.color_overlay.is_loaded = True
                                self.color_overlay.is_visible = True
                                
                                # HEMEN GÖSTER - KARTLA BERABER!
                                self.color_overlay.setGeometry(0, 0, self.width(), self.height())
                                self.color_overlay.show()
                                self.color_overlay.raise_()
                                self.color_overlay.update()
                                
                                print(f"✅ Overlay ZORLA gösterildi! Kutu {box_id} - {count} kopya")
                            
                    except Exception as e:
                        print(f"❌ _force_show_overlay hatası: {e}")
        except Exception as e:
            print(f"❌ _force_show_overlay genel hata: {e}")

    def _show_context_menu(self, position):
        if not self.teleporter:
            self._init_teleporter()
            if not self.teleporter:
                return
        
        app = QApplication.instance()
        if app and (app.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier):
            return
        
        menu = self.teleporter.create_context_menu(self, position)
        if menu:
            menu.exec(self.mapToGlobal(position))

    def _apply_selection_effect(self):
        """Kart seçildiğinde görsel efekt uygula"""
        self._selection_border_color = QColor(66, 135, 245)
        self._selection_border_width = 2
        self._is_teleport_selected = True
        self.update()

    def _remove_selection_effect(self):
        """Kart seçim kaldırıldığında efektleri temizle"""
        self._is_teleport_selected = False
        self.update()

    def _get_card_identifier(self):
        """Kart için benzersiz ID döndür"""
        if self.card_id:
            return self.card_id
        elif self.temp_id:
            return f"temp_{self.temp_id}"
        return None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setPen(QColor(0, 0, 0, 20))
        
        if hasattr(self, 'is_copy_card') and self.is_copy_card:
            grad = QLinearGradient(0, 0, self.width(), self.height())
            grad.setColorAt(0, QColor("#f5f5f5"))
            grad.setColorAt(1, QColor("#e0e0e0"))
        else:
            grad = QLinearGradient(0, 0, self.width(), self.height())
            grad.setColorAt(0, QColor("#ececec"))
            grad.setColorAt(1, QColor("#d5d5d5"))
        
        painter.setBrush(grad)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 14, 14)
        
        painter.save()
        
        if hasattr(self, 'is_copy_card') and self.is_copy_card:
            text_color = QColor(100, 100, 100)
            text = "KOPYA"
        else:
            text_color = QColor(100, 100, 100)
            text = "ORİJİNAL"
        
        painter.setPen(text_color)
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.drawText(self.width() - 50, 15, text)
        painter.restore()
        
        if hasattr(self, '_is_teleport_selected') and self._is_teleport_selected:
            painter.save()
            painter.setBrush(Qt.BrushStyle.NoBrush)
            pen = QPen(self._selection_border_color)
            pen.setWidth(self._selection_border_width)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRoundedRect(
                self.rect().adjusted(
                    self._selection_border_width,
                    self._selection_border_width,
                    -self._selection_border_width,
                    -self._selection_border_width
                ),
                14, 14
            )
            painter.restore()
        
        painter.end()
        
        # ⚠️ Overlay'i en üste getir - ama sadece varsa
        if hasattr(self, 'color_overlay') and self.color_overlay is not None:
            self.color_overlay.raise_()

    def mousePressEvent(self, event):
        self.setFocus()
        
        modifiers = event.modifiers()
        
        if event.button() == Qt.MouseButton.LeftButton and modifiers & Qt.KeyboardModifier.ControlModifier:
            if not self.teleporter:
                self._init_teleporter()
            
            if self.teleporter:
                self.teleporter.toggle_card_selection(self)
                
                card_id = self._get_card_identifier()
                if card_id and card_id in getattr(self.teleporter, 'selected_cards', set()):
                    self._apply_selection_effect()
                else:
                    self._remove_selection_effect()
                
                self._notify_parent_selection_changed()
                event.accept()
                return
        
        self.card_clicked.emit(self)
        super().mousePressEvent(event)

    def _notify_parent_selection_changed(self):
        """Seçim değiştiğinde parent widget'a bildir"""
        try:
            parent = self.parent()
            while parent:
                if hasattr(parent, 'selection_changed_externally'):
                    parent.selection_changed_externally()
                    return
                
                if hasattr(parent, 'on_card_selection_changed'):
                    parent.on_card_selection_changed(self)
                    return
                    
                parent = parent.parent()
        except Exception:
            pass

    def bind_model(self, model):
        if not model: 
            return
            
        current_front_text = self.front_fields[0].text() if self.front_fields else ""
        current_back_text = self.back_fields[0].text() if self.back_fields else ""
        
        if isinstance(model, dict):
            model_front = model.get("english", "")
            model_back = model.get("turkish", "")
        else:
            model_front = getattr(model, "english", "")
            model_back = getattr(model, "turkish", "")
        
        if self.is_newly_created and not current_front_text and not current_back_text:
            if model_front:
                current_front_text = model_front
            if model_back:
                current_back_text = model_back
        
        self.data = model
        self.is_newly_created = False
        
        if isinstance(model, dict):
            card_id = model.get("id")
            self.box_id = model.get("box_id")
            self.bucket_id = model.get("bucket", 0)
            detail_raw = model.get("detail", "{}")
            english = model.get("english", "")
            turkish = model.get("turkish", "")
            is_copy = model.get("is_copy", 0) == 1
        else:
            card_id = getattr(model, "id", None)
            self.box_id = getattr(model, "box_id", None)
            self.bucket_id = getattr(model, "bucket", 0)
            detail_raw = getattr(model, "detail", "{}")
            english = getattr(model, "english", "")
            turkish = getattr(model, "turkish", "")
            is_copy = getattr(model, "is_copy", False)
        
        self.is_copy_card = is_copy
        
        if card_id:
            try:
                self.card_id = int(card_id)
            except (ValueError, TypeError):
                self.card_id = card_id
        else:
            self.card_id = None

        for field in self.front_fields + self.back_fields:
            try:
                field.hide()
                field.deleteLater()
            except:
                pass
        
        self.front_fields.clear()
        self.back_fields.clear()

        try:
            detail = json.loads(detail_raw)
            front_fields_data = detail.get("front_fields", [])
            back_fields_data = detail.get("back_fields", [])
            
            if not front_fields_data and not english:
                front_fields_data = [current_front_text if current_front_text else ""]
            elif not front_fields_data and english:
                front_fields_data = [english]
            
            if not back_fields_data and not turkish:
                back_fields_data = [current_back_text if current_back_text else ""]
            elif not back_fields_data and turkish:
                back_fields_data = [turkish]
            
            for text in front_fields_data:
                field = self._create_field(True, str(text))
                field.text_changed_signal.connect(self._schedule_save)
            
            for text in back_fields_data:
                field = self._create_field(False, str(text))
                field.text_changed_signal.connect(self._schedule_save)
                
        except Exception:
            front_text = current_front_text if current_front_text else (english if english else "")
            back_text = current_back_text if current_back_text else (turkish if turkish else "")
            
            front_field = self._create_field(True, front_text)
            front_field.text_changed_signal.connect(self._schedule_save)
            
            back_field = self._create_field(False, back_text)
            back_field.text_changed_signal.connect(self._schedule_save)

        self._relayout()
        self.update_fields()
        
        if not self.is_copy_card:
            QTimer.singleShot(500, self._force_show_overlay)
            QTimer.singleShot(1000, self._force_show_overlay)
            QTimer.singleShot(2000, self._force_show_overlay)

        def _force_show_overlay(self):
            """Overlay'i zorla göster - ACİL DURUM"""
            if not hasattr(self, 'color_overlay') or self.color_overlay is None:
                self._init_color_overlay()
            
            if self.color_overlay and self.bucket_id == 0:
                # Veritabanını kontrol et
                if self.db and self.card_id:
                    try:
                        cursor = self.db.conn.cursor()
                        cursor.execute("""
                            SELECT COUNT(*) FROM words 
                            WHERE original_card_id = ? AND is_copy = 1
                        """, (self.card_id,))
                        count = cursor.fetchone()[0]
                        
                        if count > 0:
                            print(f"🚨 ZORLA overlay gösteriliyor! Kopya sayısı: {count}")
                            self.color_overlay.schedule_lazy_update(force=True)
                            self.color_overlay.show()
                            self.color_overlay.raise_()
                            self.color_overlay.update()
                    except Exception as e:
                        print(f"❌ _force_show_overlay hatası: {e}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        # ============= YENİ - Overlay boyutunu güncelle =============
        if hasattr(self, 'color_overlay') and self.color_overlay:
            self.color_overlay.setGeometry(0, 0, self.width(), self.height())
            if self.color_overlay.is_visible:
                self.color_overlay.parent_resized()
        # ============================================================
        
        QTimer.singleShot(50, self._relayout)

    def _schedule_save(self):
        QTimer.singleShot(1000, self.sync_data)

    def _relayout(self):
        fw, fh, gap = 180, 22, 8
        cx = (self.W - fw) // 2

        def place(fields, plus_button):
            n = len(fields)
            total_h = n * fh + (n - 1) * gap
            
            start_y = (self.H - total_h) // 2
            
            for i, f in enumerate(fields):
                f.setGeometry(cx, int(start_y + i * (fh + gap)), fw, fh)
            
            if n < self.MAX_FIELDS:
                plus_button.setVisible(True)
                plus_x = cx + (fw - 20) // 2
                plus_y = int(start_y + total_h + 4)
                plus_button.setGeometry(plus_x, plus_y, 20, 20)
            else:
                plus_button.setVisible(False)

        place(self.front_fields, self.plus_front)
        place(self.back_fields, self.plus_back)

        self.flip_btn.setGeometry(self.W - 35, self.H - 28, 30, 24)
        self.del_btn.setGeometry(5, self.H - 28, 30, 24)
        self.note_btn.setGeometry(self.W - 35, 5, 30, 24)

        self.update_fields()
        
        self.note_btn.raise_()
        self.flip_btn.raise_()
        self.del_btn.raise_()
        self.plus_front.raise_()
        self.plus_back.raise_()
        
        # ============= KRİTİK: Overlay EN ÜSTTE OLMALI! =============
        if hasattr(self, 'color_overlay') and self.color_overlay is not None:
            if not self.is_copy_card:
                # Overlay'i her şeyin ÜSTÜNE çıkar!
                self.color_overlay.raise_()
                self.color_overlay.show()
                
                # Boyutunu güncelle
                self.color_overlay.setGeometry(0, 0, self.width(), self.height())
                self.color_overlay.setFixedSize(self.width(), self.height())
                
                if self.color_overlay.is_visible:
                    self.color_overlay.parent_resized()
                    self.color_overlay.update()
        
        # 100ms sonra TEKRAR en üste çıkar (güvence)
        if hasattr(self, 'color_overlay') and self.color_overlay is not None:
            if not self.is_copy_card:
                QTimer.singleShot(100, self._ensure_overlay_on_top)
        # ============================================================

    def _ensure_overlay_on_top(self):
        """Overlay'in KESİNLİKLE en üstte olduğundan emin ol"""
        if hasattr(self, 'color_overlay') and self.color_overlay is not None:
            if not self.is_copy_card:
                self.color_overlay.raise_()
                self.color_overlay.show()
                self.color_overlay.update()

    def toggle(self):
        self.front = not self.front
        self._relayout()
        
        if self.color_overlay and self.color_overlay.is_visible:
            self.color_overlay.parent_resized()

    def update_fields(self):
        for f in self.front_fields: 
            f.setVisible(self.front)
        for f in self.back_fields: 
            f.setVisible(not self.front)
        self.plus_front.setVisible(self.front and len(self.front_fields) < self.MAX_FIELDS)
        self.plus_back.setVisible(not self.front and len(self.back_fields) < self.MAX_FIELDS)

    def sync_data(self):
        try:
            if self.is_newly_created and not self.card_id:
                success = self._save_new_card()
                if success:
                    if self.data:
                        if isinstance(self.data, dict):
                            self.data["id"] = self.card_id
                        else:
                            try:
                                self.data.id = self.card_id
                            except:
                                pass
                    self._notify_parent_card_saved()
                return
            
            if not self.db or not self.card_id:
                return
            
            front_texts = [f.text() for f in self.front_fields]
            back_texts = [f.text() for f in self.back_fields]
            
            front_texts = [text.strip() for text in front_texts if text.strip()]
            back_texts = [text.strip() for text in back_texts if text.strip()]
            
            if not front_texts:
                front_texts = [""]
            if not back_texts:
                back_texts = [""]
            
            english = front_texts[0] if front_texts else ""
            turkish = back_texts[0] if back_texts else ""
            
            detail = {
                "front_fields": front_texts,
                "back_fields": back_texts
            }
            detail_json = json.dumps(detail, ensure_ascii=False)
            
            success = False
            try:
                success = self.db.update_word(
                    int(self.card_id), 
                    english, 
                    turkish, 
                    detail_json, 
                    self.box_id, 
                    self.bucket_id
                )
            except Exception:
                try:
                    self.db.delete_word(int(self.card_id))
                    new_id = self.db.add_word(
                        english=english,
                        turkish=turkish,
                        detail=detail_json,
                        box_id=self.box_id,
                        bucket=self.bucket_id,
                        original_card_id=None,
                        is_copy=False
                    )
                    if new_id:
                        self.card_id = new_id
                        success = True
                except Exception:
                    success = False
            
            if success:
                if isinstance(self.data, dict):
                    self.data["english"] = english
                    self.data["turkish"] = turkish
                    self.data["detail"] = detail_json
                    self.data["box_id"] = self.box_id
                    self.data["bucket"] = self.bucket_id
                    self.data["is_copy"] = False
                elif self.data:
                    try:
                        self.data.english = english
                        self.data.turkish = turkish
                        self.data.detail = detail_json
                        self.data.box_id = self.box_id
                        self.data.bucket = self.bucket_id
                        self.data.is_copy = False
                    except:
                        pass
                
                self._update_parent_data()
                self._update_state_file()
                self.updated.emit(self)
                
                if not hasattr(self, 'is_copy_card') or not self.is_copy_card:
                    try:
                        if hasattr(self, 'bubble') and self.bubble:
                            from ui.words_panel.button_and_cards.bubble.bubble_persistence import save_bubble
                            save_bubble(self.bubble)
                    except Exception:
                        pass
        
        except Exception:
            pass

    def _notify_parent_card_saved(self):
        try:
            parent = self.parent()
            while parent:
                if hasattr(parent, '_on_card_saved') and callable(getattr(parent, '_on_card_saved')):
                    parent._on_card_saved(self)
                    break
                parent = parent.parent()
        except Exception:
            pass

    def _update_parent_data(self):
        try:
            parent = self.parent()
            if not parent or not hasattr(parent, '_data'):
                return
            
            for i, item in enumerate(parent._data):
                if isinstance(item, dict) and item.get('id') == self.card_id:
                    parent._data[i] = self.data.copy() if isinstance(self.data, dict) else self.data
                    break
                elif hasattr(item, 'id') and item.id == self.card_id:
                    parent._data[i] = self.data
                    break
            
        except Exception:
            pass

    def _update_state_file(self):
        try:
            if not self.card_id or not self.box_id:
                return
                
            parent = self.parent()
            detail_window = None
            
            while parent:
                if hasattr(parent, 'state') and hasattr(parent, 'box_id'):
                    detail_window = parent
                    break
                parent = parent.parent()
            
            if detail_window and hasattr(detail_window, 'state'):
                state = detail_window.state
                
                card_found = False
                for card in state.cards:
                    if card.get('id') == self.card_id:
                        card['bucket'] = self.bucket_id
                        card_found = True
                        break
                
                if not card_found:
                    state.cards.append({
                        'id': self.card_id,
                        'bucket': self.bucket_id,
                        'rect': None
                    })
                
                state.mark_dirty()
                state.save()
                
        except Exception:
            pass

    def toggle_bubble(self):
        current_id = self.card_id or self.temp_id
        
        if not current_id:
            self.temp_id = str(uuid.uuid4())[:8]
            current_id = self.temp_id
        
        bubble = self.bubble
        if not bubble:
            return
        
        bubble_is_open = getattr(bubble, "_bubble_open", False)
        
        if not bubble_is_open:
            data = load_bubble(current_id)
            html = ""
            if isinstance(data, dict):
                html = data.get("html", data.get("html_content", ""))
            else:
                html = data or ""
                
            bubble.text.setHtml(html or "<p></p>")
            
            main_win = self.window()
            if main_win and bubble.parent() != main_win:
                bubble.setParent(main_win)
            
            try:
                open_bubble(self)
            except:
                bubble.show()
                bubble.raise_()
                
        else:
            try:
                close_bubble(bubble)
            except:
                bubble.hide()

    def _final_check(self):
        if self.bubble_open and not self.bubble.isVisible():
            self.bubble.show()
            self.bubble.raise_()

    def on_bubble_text_changed(self):
        QTimer.singleShot(500, self._delayed_bubble_save)

    def _delayed_bubble_save(self):
        try:
            if not hasattr(self, 'bubble') or not self.bubble:
                return
            
            current_id = self.card_id or self.temp_id
            
            if not current_id:
                return
            
            html_content = ""
            bubble_width = 320
            bubble_height = 200
            
            if hasattr(self.bubble, 'text'):
                html_content = self.bubble.text.toHtml()
            
            if hasattr(self.bubble, 'width'):
                bubble_width = self.bubble.width()
            
            if hasattr(self.bubble, 'height'):
                bubble_height = self.bubble.height()
            
            from ui.words_panel.button_and_cards.bubble.bubble_persistence import save_bubble
            save_bubble(self.bubble)
            
            if self.card_id and hasattr(self, 'db') and self.db:
                try:
                    cursor = self.db.conn.cursor()
                    cursor.execute("SELECT is_copy FROM words WHERE id=?", (self.card_id,))
                    row = cursor.fetchone()
                    
                    if row and row[0] == 0:
                        try:
                            from ui.boxes_panel.copy_flash_card.copy_bubble.copy_bubble_sync import CopyBubbleSyncManager
                            sync_manager = CopyBubbleSyncManager.instance()
                            sync_manager.notify_original_updated(
                                original_card_id=self.card_id,
                                html_content=html_content,
                                width=bubble_width,
                                height=bubble_height
                            )
                        except ImportError:
                            pass
                except Exception:
                    pass
            
        except Exception:
            pass

    def on_delete_clicked(self):
        if not self.card_id or not self.db:
            return
        
        has_content = False
        front_texts = [f.text().strip() for f in self.front_fields]
        back_texts = [f.text().strip() for f in self.back_fields]
        
        if any(front_texts) or any(back_texts):
            has_content = True
        
        if not has_content:
            self._delete_card_directly()
            return
        
        copy_count = 0
        try:
            if self.db and self.card_id:
                cursor = self.db.conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM words WHERE original_card_id = ?", (self.card_id,))
                copy_count = cursor.fetchone()[0]
        except Exception:
            pass
        
        card_data = {
            'front_texts': front_texts,
            'back_texts': back_texts
        }
        
        if show_original_card_delete_dialog(self, card_data, copy_count):
            self._delete_card_with_copies()

    def _delete_card_with_copies(self):
        try:
            if not self.card_id or not self.db:
                return
            
            copy_cards = []
            try:
                cursor = self.db.conn.cursor()
                cursor.execute("SELECT id FROM words WHERE original_card_id = ?", (self.card_id,))
                copy_cards = [row[0] for row in cursor.fetchall()]
            except Exception:
                pass
            
            if copy_cards:
                self._cleanup_specific_card_copies(self.card_id, copy_cards)
            
            if copy_cards:
                try:
                    cursor = self.db.conn.cursor()
                    placeholders = ','.join(['?' for _ in copy_cards])
                    cursor.execute(f"DELETE FROM words WHERE id IN ({placeholders})", copy_cards)
                    self.db.conn.commit()
                except Exception:
                    self.db.conn.rollback()
            
            try:
                success = self.db.delete_word(int(self.card_id))
                if not success:
                    cursor = self.db.conn.cursor()
                    cursor.execute("DELETE FROM words WHERE id = ?", (self.card_id,))
                    self.db.conn.commit()
            except Exception:
                return
            
            try:
                from ui.words_panel.button_and_cards.bubble.bubble_persistence import delete_bubble
                delete_bubble(self.card_id)
                for copy_id in copy_cards:
                    delete_bubble(copy_id)
            except:
                pass
            
            self._remove_from_state()
            
            try:
                parent = self.parent()
                while parent:
                    if hasattr(parent, 'delete_card_from_detail'):
                        parent.delete_card_from_detail(self)
                        break
                    elif hasattr(parent, '_on_card_deleted'):
                        parent._on_card_deleted(self, "unknown")
                        break
                    parent = parent.parent()
            except Exception:
                pass
            
            self.hide()
            self.setParent(None)
            self.deleteLater()
            
        except Exception:
            pass

    def _delete_card_directly(self):
        try:
            if not self.card_id or not self.db:
                return
            
            try:
                self.db.delete_word(int(self.card_id))
            except Exception:
                pass
            
            try:
                from ui.words_panel.button_and_cards.bubble.bubble_persistence import delete_bubble
                delete_bubble(self.card_id)
            except:
                pass
            
            self._remove_from_state()
            
            try:
                parent = self.parent()
                while parent:
                    if hasattr(parent, 'delete_card_from_detail'):
                        parent.delete_card_from_detail(self)
                        break
                    elif hasattr(parent, '_on_card_deleted'):
                        parent._on_card_deleted(self, "unknown")
                        break
                    parent = parent.parent()
            except Exception:
                pass
            
            if self.box_id:
                self._update_memory_box_count(self.box_id)
            
            self.hide()
            self.setParent(None)
            self.deleteLater()
            
        except Exception:
            pass

    def _cleanup_specific_card_copies(self, original_card_id, copy_cards):
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if not app:
                return
            
            for widget in app.allWidgets():
                if hasattr(widget, '__class__') and 'WaitingAreaWidget' in widget.__class__.__name__:
                    waiting_area = widget
                    
                    if hasattr(waiting_area, 'cards'):
                        cards_to_remove = []
                        for word_id in waiting_area.cards:
                            if word_id in copy_cards:
                                cards_to_remove.append(word_id)
                        
                        for word_id in cards_to_remove:
                            try:
                                if waiting_area.db:
                                    try:
                                        waiting_area.db.delete_word(word_id)
                                    except:
                                        pass
                                
                                if hasattr(waiting_area, '_remove_card_by_id'):
                                    waiting_area._remove_card_by_id(word_id)
                                elif hasattr(waiting_area, 'remove_card'):
                                    waiting_area.remove_card(word_id)
                                
                            except Exception:
                                continue
        except Exception:
            pass

    def _immediate_memory_box_update(self, box_id):
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import QTimer
            
            app = QApplication.instance()
            if not app:
                return
            
            def update_now():
                try:
                    for widget in app.allWidgets():
                        if hasattr(widget, '__class__') and 'MemoryBox' in widget.__class__.__name__:
                            if hasattr(widget, 'box_id') and widget.box_id == box_id:
                                if hasattr(widget, 'update_card_count'):
                                    widget.update_card_count()
                                    widget.count_lbl.update()
                                    widget.btn.update()
                                    widget.update()
                                    break
                    
                    for widget in app.topLevelWidgets():
                        if hasattr(widget, 'design'):
                            if hasattr(widget.design, '_force_immediate_count_update'):
                                widget.design._force_immediate_count_update()
                                break
                            
                except Exception:
                    pass
            
            QTimer.singleShot(0, update_now)
            
        except Exception:
            pass

    def _update_memory_box_count(self, box_id):
        try:
            app = QApplication.instance()
            if not app:
                return
            
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'design') and hasattr(widget.design, 'update_all_counts'):
                    widget.design.update_all_counts()
                    return
                elif hasattr(widget, '__class__') and 'BoxesDesign' in widget.__class__.__name__:
                    if hasattr(widget, 'update_all_counts'):
                        widget.update_all_counts()
                        return
            
            for widget in app.allWidgets():
                if hasattr(widget, '__class__') and 'MemoryBox' in widget.__class__.__name__:
                    if hasattr(widget, 'box_id') and widget.box_id == box_id:
                        if hasattr(widget, 'update_card_count'):
                            widget.update_card_count()
                            break
            
        except Exception:
            pass

    def _update_all_memory_box_counts(self):
        try:
            app = QApplication.instance()
            if not app:
                return
            
            from PyQt6.QtCore import QTimer
            
            QTimer.singleShot(100, self._refresh_memory_box_counts_once)
            QTimer.singleShot(300, self._refresh_memory_box_counts_once)
            QTimer.singleShot(500, self._refresh_memory_box_counts_once)
            
        except Exception:
            pass

    def _refresh_memory_box_counts_once(self):
        try:
            app = QApplication.instance()
            if not app:
                return
            
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'design') and hasattr(widget.design, 'update_all_counts'):
                    widget.design.update_all_counts()
                    return
                elif hasattr(widget, 'update_all_counts'):
                    widget.update_all_counts()
                    return
            
            for widget in app.allWidgets():
                if hasattr(widget, '__class__') and 'BoxesDesign' in widget.__class__.__name__:
                    if hasattr(widget, 'update_all_counts'):
                        widget.update_all_counts()
                        break
            
            for widget in app.allWidgets():
                if hasattr(widget, '__class__') and 'MemoryBox' in widget.__class__.__name__:
                    if hasattr(widget, 'update_card_count'):
                        widget.update_card_count()
            
        except Exception:
            pass

    def _update_box_views_in_container(self, container):
        try:
            from PyQt6.QtCore import QTimer
            from ui.words_panel.box_widgets.box_view import BoxView
            
            def find_and_update(widget):
                if isinstance(widget, BoxView) and hasattr(widget, 'refresh_card_counts'):
                    widget.refresh_card_counts()
                
                for child in widget.children():
                    if isinstance(child, QWidget):
                        find_and_update(child)
            
            find_and_update(container)
            
        except Exception:
            pass

    def _remove_from_state(self):
        try:
            if not self.card_id:
                return
                
            parent = self.parent()
            detail_window = None
            
            while parent:
                if hasattr(parent, 'state') and hasattr(parent, 'box_id'):
                    detail_window = parent
                    break
                parent = parent.parent()
            
            if detail_window and hasattr(detail_window, 'state'):
                state = detail_window.state
                state.remove_card(self.card_id)
                state.mark_dirty()
                state.save()
                
        except Exception:
            pass

    def _save_new_card(self):
        if not self.db:
            return False
            
        try:
            front_texts = [f.text() for f in self.front_fields]
            back_texts = [f.text() for f in self.back_fields]
            
            english = front_texts[0] if front_texts else ""
            turkish = back_texts[0] if back_texts else ""
            
            if not english and not turkish:
                english = ""
                turkish = ""
            
            detail = {
                "front_fields": front_texts,
                "back_fields": back_texts
            }
            detail_json = json.dumps(detail, ensure_ascii=False)
            
            card_id = self.db.add_word(
                english=english,
                turkish=turkish,
                detail=detail_json,
                box_id=self.box_id if self.box_id else None,
                bucket=0,
                is_copy=False
            )
            
            if card_id:
                self.card_id = card_id
                self.is_newly_created = False
                self.temp_id = None
                
                if isinstance(self.data, dict):
                    self.data["id"] = card_id
                    self.data["english"] = english
                    self.data["turkish"] = turkish
                    self.data["detail"] = detail_json
                    self.data["box_id"] = self.box_id
                    self.data["bucket"] = 0
                    self.data["is_copy"] = False
                elif self.data:
                    try:
                        self.data.id = card_id
                        self.data.english = english
                        self.data.turkish = turkish
                        self.data.detail = detail_json
                        self.data.box_id = self.box_id
                        self.data.bucket = 0
                        self.data.is_copy = False
                    except:
                        pass
                
                if not self.is_copy_card:
                    self._init_color_overlay()
                    if self.bucket_id == 0:
                        self._lazy_init_overlay()
                
                return True
                
        except Exception:
            pass
                
        return False

    def _apply_plus_style(self, btn):
        btn.setStyleSheet("QPushButton { border: none; background: transparent; font-size: 18px; font-weight: bold; color: #444; }")

    def _apply_action_button_style(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.7);
                border: 1px solid rgba(0,0,0,0.1);
                border-radius: 6px;
                font-size: 13px;
                color: #333;
            }
            QPushButton:hover { background: #ffffff; border: 1px solid #3498db; }
        """)

    def _create_field(self, is_front, text=""):
        fld = DynamicField(self)
        fld.setText(text.strip() if text else "")
        fld.setReadOnly(True)
        fld.delete_requested.connect(lambda w: self._delete_field(is_front, fld))
        
        fld.text_committed.connect(lambda t: self._on_field_committed())
        
        if is_front:
            self.front_fields.append(fld)
        else:
            self.back_fields.append(fld)
        
        self._relayout()
        return fld
    
    def _on_field_committed(self):
        self.sync_data()
        self.updated.emit(self)
    
    def _delete_field(self, is_front, field):
        try:
            field_text = field.text()
            
            if is_front and field in self.front_fields:
                self.front_fields.remove(field)
            elif not is_front and field in self.back_fields:
                self.back_fields.remove(field)
            
            field.hide()
            field.deleteLater()
            
            self._relayout()
            
            if field_text.strip() or (is_front and len(self.front_fields) > 0) or (not is_front and len(self.back_fields) > 0):
                QTimer.singleShot(100, self.sync_data)
                
        except Exception:
            pass
    
    def _add_field(self, is_front):
        if is_front and len(self.front_fields) >= self.MAX_FIELDS:
            return
        if not is_front and len(self.back_fields) >= self.MAX_FIELDS:
            return
        
        field = self._create_field(is_front, "")
        
        field.setReadOnly(False)
        field.setFocus()
        field.selectAll()
        
        QTimer.singleShot(100, self.sync_data)

    def get_card_data(self):
        return {
            'id': self.card_id,
            'english': self.front_fields[0].text() if self.front_fields else '',
            'turkish': self.back_fields[0].text() if self.back_fields else '',
            'detail': json.dumps({
                'front_fields': [f.text() for f in self.front_fields],
                'back_fields': [f.text() for f in self.back_fields]
            }) if self.front_fields or self.back_fields else '{}',
            'box_id': self.box_id,
            'bucket': self.bucket_id,
            'is_copy': False
        }

    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        if hasattr(self, 'color_overlay') and self.color_overlay and hasattr(self.color_overlay, 'is_visible'):
            if self.color_overlay.is_visible:
                self.color_overlay.parent_resized()
        
        QTimer.singleShot(50, self._relayout)
    
    def on_card_moved_to_box(self, target_box_id):
        if self.color_overlay:
            self.color_overlay.schedule_lazy_update(force=True)
    
    def on_card_learned(self):
        """Kart öğrenildi container'ına taşındığında çağrılır"""
        print(f"🎓 [FlashCardView] on_card_learned çağrıldı - Kart ID: {self.card_id}")
        
        # ÖNCE: Overlay'i hemen kaldır
        if hasattr(self, 'color_overlay') and self.color_overlay is not None:
            print(f"   - Overlay bulundu, kaldırılıyor...")
            if hasattr(self.color_overlay, '_hide_overlay'):
                self.color_overlay._hide_overlay()
            elif hasattr(self.color_overlay, 'hide'):
                self.color_overlay.hide()
            
            # Overlay'i temizle
            self.color_overlay.cleanup()
            self.color_overlay = None
            print(f"   ✅ Overlay tamamen kaldırıldı")
        else:
            print(f"   - Overlay zaten yok")
        
        # Bucket'ı güncelle
        self.bucket_id = 1
        
        # Veritabanını güncelle
        if self.db and self.card_id:
            try:
                self.db.update_word_bucket(self.card_id, 1)
                print(f"   ✅ Veritabanı bucket=1 olarak güncellendi")
            except Exception as e:
                print(f"   ❌ Veritabanı güncelleme hatası: {e}")
        
        # UI'ı güncelle
        self.update()
        
        # Notify parent
        self._notify_bucket_changed()
        print(f"✅ [FlashCardView] on_card_learned tamamlandı")
    
    def _notify_bucket_changed(self):
        try:
            parent = self.parent()
            while parent:
                if hasattr(parent, '_on_card_bucket_changed'):
                    parent._on_card_bucket_changed(self)
                    break
                parent = parent.parent()
        except Exception:
            pass
    
    def cleanup(self):
        if self.color_overlay:
            self.color_overlay.cleanup()
            self.color_overlay = None
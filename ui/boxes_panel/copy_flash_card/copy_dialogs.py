from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt
import json


def show_copy_delete_dialog(parent_widget, copy_card_view):
    """Kopya kart silme dialog'u gösterir - TÜM LOGIC BURADA"""
    dialog = QDialog(parent_widget)
    dialog.setWindowTitle("Kopya Kartı Sil")
    dialog.setFixedSize(420, 240)
    dialog.setWindowModality(Qt.WindowModality.WindowModal)

    dialog.setStyleSheet("""
        QDialog {
            background-color: white;
            border: 1px solid #E0E0E0;
            border-radius: 12px;
        }
    """)

    main_layout = QVBoxLayout(dialog)
    main_layout.setContentsMargins(30, 30, 30, 25)
    main_layout.setSpacing(20)

    message_label = QLabel("Kopya kartı nasıl işlemek istiyorsunuz?")
    message_label.setStyleSheet("""
        QLabel {
            font-family: 'Segoe UI';
            font-size: 15px;
            color: #333333;
            font-weight: bold;
            background-color: transparent;
        }
    """)
    message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_layout.addWidget(message_label)

    detail_label = QLabel("<b>Gerçek kart silinmez</b>")
    detail_label.setStyleSheet("""
        QLabel {
            font-family: 'Segoe UI';
            font-size: 14px;
            color: #666666;
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 15px;
            margin: 5px;
        }
    """)
    detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    detail_label.setWordWrap(True)
    main_layout.addWidget(detail_label)

    buttons_layout = QHBoxLayout()
    buttons_layout.setSpacing(15)
    
    delete_copy_btn = QPushButton("Sadece Kopyayı Sil")
    delete_copy_btn.setMinimumHeight(40)
    delete_copy_btn.setStyleSheet("""
        QPushButton {
            background-color: #ffebee;
            border: 1px solid #ffcdd2;
            border-radius: 6px;
            font-family: 'Segoe UI';
            font-size: 13px;
            font-weight: 500;
            color: #d32f2f;
            padding: 8px 16px;
        }
        QPushButton:hover {
            background-color: #ffcdd2;
            color: #b71c1c;
        }
        QPushButton:pressed {
            background-color: #ef9a9a;
        }
    """)
    
    def on_delete_copy():
        _delete_copy_only(copy_card_view)
        dialog.accept()
    
    delete_copy_btn.clicked.connect(on_delete_copy)
    buttons_layout.addWidget(delete_copy_btn)
    
    quick_move_btn = QPushButton("Hızlı Taşı ve Sil")
    quick_move_btn.setMinimumHeight(40)
    quick_move_btn.setStyleSheet("""
        QPushButton {
            background-color: #e8f5e9;
            border: 1px solid #c8e6c9;
            border-radius: 6px;
            font-family: 'Segoe UI';
            font-size: 13px;
            font-weight: 500;
            color: #388e3c;
            padding: 8px 16px;
        }
        QPushButton:hover {
            background-color: #c8e6c9;
            color: #2e7d32;
        }
        QPushButton:pressed {
            background-color: #a5d6a7;
        }
    """)
    
    def on_quick_move():
        _quick_move_and_delete(copy_card_view)
        dialog.accept()
    
    quick_move_btn.clicked.connect(on_quick_move)
    buttons_layout.addWidget(quick_move_btn)
        
    main_layout.addLayout(buttons_layout)
    main_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
    
    dialog.exec()


def _delete_copy_only(copy_card_view):
    """Sadece kopyayı sil"""
    try:
        db = getattr(copy_card_view, 'db', None)
        card_id = getattr(copy_card_view, 'card_id', None)
        
        if db and card_id:
            db.delete_word(card_id)
        
        # ✅ SENKRONİZASYON SİSTEMİNDEN KALDIR - YENİ EKLENDİ
        try:
            from ui.words_panel.button_and_cards.copy_sync_manager import CopySyncManager
            sync_manager = CopySyncManager.instance()
            sync_manager.unregister_copy(card_id)
        except Exception:
            pass
        
        # UI'dan kaldır
        _remove_card_from_ui(copy_card_view)
        # Kutu sayacını güncelle
        _update_box_counters(db, copy_card_view)
        
    except Exception:
        pass


def _quick_move_and_delete(copy_card_view):
    """Hızlı taşı ve sil: Orijinal kartı öğrendiklerim'e taşı, kopyayı sil"""
    card_id = getattr(copy_card_view, 'card_id', None)
    
    db = getattr(copy_card_view, 'db', None)
    if not db or not card_id:
        return
    
    try:
        cursor = db.conn.cursor()
        
        # 1. Önce bu kopya kartın orijinal ID'sini bul
        cursor.execute("SELECT original_card_id FROM words WHERE id=?", (card_id,))
        original_row = cursor.fetchone()
        
        if not original_row:
            # Bu kopya kart zaten orijinal olabilir mi?
            cursor.execute("SELECT is_copy FROM words WHERE id=?", (card_id,))
            is_copy_row = cursor.fetchone()
            if is_copy_row and is_copy_row[0] == 0:
                cursor.execute("UPDATE words SET bucket=1 WHERE id=?", (card_id,))
            else:
                db.delete_word(card_id)
            
            _remove_card_from_ui(copy_card_view)
            _update_box_counters(db, copy_card_view)
            return
        
        original_id = original_row[0]
        
        # 2. Orijinal kartın bucket'ını 1 yap (öğrendiklerim)
        cursor.execute("UPDATE words SET bucket=1 WHERE id=?", (original_id,))
        
        # 3. Kopya kartı sil
        cursor.execute("DELETE FROM words WHERE id=?", (card_id,))
        
        db.conn.commit()
        
        # 4. Orijinal kartın hangi box'ta olduğunu bul
        cursor.execute("SELECT box FROM words WHERE id=?", (original_id,))
        box_row = cursor.fetchone()
        original_box_id = box_row[0] if box_row else None
        
        # 5. Orijinal kartın şu anki bucket'ını kontrol et
        cursor.execute("SELECT bucket FROM words WHERE id=?", (original_id,))
        bucket_row = cursor.fetchone()
        current_bucket = bucket_row[0] if bucket_row else 0
        
        # 6. Kendini UI'dan kaldır
        _remove_card_from_ui(copy_card_view)
        
        # 7. Orijinal kartın UI'ını güncelle (eğer açıksa)
        if original_box_id:
            _update_original_card_ui(db, original_id, original_box_id, current_bucket)
        
        # 8. Kutu sayacını güncelle
        _update_box_counters(db, copy_card_view)
        
    except Exception:
        # Hata olsa bile kopyayı silmeye çalış
        try:
            db.delete_word(card_id)
            _remove_card_from_ui(copy_card_view)
            _update_box_counters(db, copy_card_view)
        except:
            pass


def _remove_card_from_ui(copy_card_view):
    """Kartı UI'dan güvenle kaldır"""
    try:
        from PyQt6.QtCore import QTimer
        
        # Drag-drop manager'dan kaydını sil
        try:
            from ui.words_panel.drag_drop_manager.decorators import DragDropManager
            if DragDropManager.is_registered(copy_card_view):
                DragDropManager.unregister(copy_card_view)
        except:
            pass
        
        # CardTeleporter'dan çıkar
        if hasattr(copy_card_view, 'teleporter') and copy_card_view.teleporter:
            if hasattr(copy_card_view.teleporter, 'remove_card_selection'):
                card_id = getattr(copy_card_view, 'card_id', None)
                if card_id:
                    copy_card_view.teleporter.remove_card_selection(card_id)
        
        # Bubble'ı temizle
        if hasattr(copy_card_view, 'bubble'):
            try:
                bubble = copy_card_view.bubble
                if bubble:
                    bubble.hide()
                    bubble.setParent(None)
                    bubble.deleteLater()
                    copy_card_view.bubble = None
            except Exception:
                pass
        
        # Widget'ı gizle ve temizle
        if hasattr(copy_card_view, 'hide'):
            copy_card_view.hide()
        
        if hasattr(copy_card_view, 'setParent'):
            try:
                copy_card_view.setParent(None)
            except:
                pass
        
        # Silme işlemini geciktir
        QTimer.singleShot(100, copy_card_view.deleteLater)
        
    except Exception:
        pass


def _update_original_card_ui(db, original_id, box_id, current_bucket):
    """Orijinal kartın UI'ını güncelle (BoxDetailContent varsa)"""
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer
        
        app = QApplication.instance()
        if not app:
            return
        
        # Tüm açık pencerelerde arama yap
        for window in app.topLevelWidgets():
            # BoxDetailWindow mu kontrol et
            if hasattr(window, 'box_id') and window.box_id == box_id:
                # Content widget'ını kontrol et
                if hasattr(window, 'content_widget'):
                    content = window.content_widget
                    
                    # BoxDetailContent mı?
                    if hasattr(content, '_transfer_single_card'):
                        # Orijinal kartın şu anki durumunu kontrol et
                        if current_bucket == 0:  # Bilmediklerim'de
                            success = content._transfer_single_card(
                                original_id,
                                1,  # new_bucket
                                "unknown",  # from_type
                                "learned"   # to_type
                            )
                            
                            # UI'ı güncelle
                            if success:
                                if hasattr(content, 'update_grid_size'):
                                    QTimer.singleShot(100, lambda: content.update_grid_size("unknown"))
                                    QTimer.singleShot(100, lambda: content.update_grid_size("learned"))
                                
                                if hasattr(content, '_force_update_positions'):
                                    QTimer.singleShot(150, content._force_update_positions)
                        
                        elif current_bucket == 1:  # Zaten öğrendiklerim'de
                            # Sadece yeniden yükle
                            if hasattr(content, 'refresh_card_lists'):
                                QTimer.singleShot(100, content.refresh_card_lists)
                        
                        return True
        
        return False
        
    except Exception:
        return False


def _update_box_counters(db, copy_card_view):
    """Kutu sayaçlarını güncelle"""
    try:
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QApplication
        
        # 1. Önce copy_card_view'ın ait olduğu kutu varsa onu güncelle
        box_id = getattr(copy_card_view, 'box_id', None)
        if box_id:
            _refresh_specific_box_counter(db, box_id)
        
        # 2. Orijinal kartın kutusunu da güncelle (quick_move için)
        if hasattr(copy_card_view, 'card_id'):
            cursor = db.conn.cursor()
            cursor.execute("SELECT original_card_id FROM words WHERE id=?", (copy_card_view.card_id,))
            original_row = cursor.fetchone()
            if original_row:
                original_id = original_row[0]
                cursor.execute("SELECT box FROM words WHERE id=?", (original_id,))
                box_row = cursor.fetchone()
                if box_row:
                    original_box_id = box_row[0]
                    if original_box_id != box_id:  # Farklı kutu ise
                        _refresh_specific_box_counter(db, original_box_id)
        
        # 3. Tüm BoxView'ları güncelle
        app = QApplication.instance()
        if app:
            try:
                from ui.words_panel.box_widgets.box_view import BoxView
                for widget in app.topLevelWidgets():
                    box_views = widget.findChildren(BoxView)
                    for box_view in box_views:
                        if hasattr(box_view, 'refresh_card_counts'):
                            QTimer.singleShot(200, box_view.refresh_card_counts)
            except ImportError:
                pass
        
        # 4. WordsWindow'daki container'ı güncelle
        try:
            main_window = QApplication.instance().activeWindow()
            while main_window and not hasattr(main_window, 'words_window'):
                main_window = main_window.parent()
            
            if main_window and hasattr(main_window, 'words_window'):
                words_window = main_window.words_window
                if hasattr(words_window, 'container') and hasattr(words_window.container, 'refresh_all_boxes'):
                    QTimer.singleShot(300, words_window.container.refresh_all_boxes)
        except:
            pass
        
    except Exception:
        pass


def _refresh_specific_box_counter(db, box_id):
    """Belirli bir kutu sayacını güncelle"""
    try:
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication.instance()
        if not app:
            return
        
        # BoxView'ı bul ve güncelle
        try:
            from ui.words_panel.box_widgets.box_view import BoxView
            for widget in app.topLevelWidgets():
                box_views = widget.findChildren(BoxView)
                for box_view in box_views:
                    if hasattr(box_view, 'db_id') and box_view.db_id == box_id:
                        if hasattr(box_view, 'refresh_card_counts'):
                            QTimer.singleShot(100, box_view.refresh_card_counts)
                            return
        except ImportError:
            pass
        
        # BoxDetailWindow'ı bul ve güncelle
        for window in app.topLevelWidgets():
            if hasattr(window, 'box_id') and window.box_id == box_id:
                if hasattr(window, '_refresh_box_counter'):
                    QTimer.singleShot(150, window._refresh_box_counter)
                    break
        
    except Exception:
        pass
# ui/words_panel/box_widgets/managers/title_manager.py
from PyQt6.QtCore import QTimer

class TitleManager:
    """Başlık düzenleme işlemlerini yönetir"""
    
    def __init__(self, box_view):
        self.box_view = box_view
    
    def enable_edit(self, _):
        """Başlık düzenlemeyi etkinleştir"""
        if self.box_view._deleted:
            return
            
        if self.box_view.label and self.box_view.editor:
            self.box_view.editor.setText(self.box_view.label.text())
            self.box_view.label.hide()
            self.box_view.editor.show()
            self.box_view.editor.setFocus()
    
    def finish_edit(self):
        """Başlık düzenlemeyi bitir"""
        if self.box_view._deleted or not self.box_view.editor:
            return
            
        new_title = self.box_view.editor.text().strip() or "Adsız Kutu"
        
        # Değişiklik yoksa
        if new_title == self.box_view.title:
            if self.box_view.editor and self.box_view.label:
                self.box_view.editor.hide()
                self.box_view.label.show()
            return
        
        old_title = self.box_view.title
        self.box_view.title = new_title
        
        # UI güncelle
        if self.box_view.label:
            self.box_view.label.setText(new_title)
        
        if self.box_view.editor and self.box_view.label:
            self.box_view.editor.hide()
            self.box_view.label.show()
        
        # State ve veritabanını güncelle
        self.box_view.state_manager.update_title(new_title, old_title)
        
        # Sinyal gönder
        self.box_view.title_changed.emit(new_title)
        
        # Sayaçları yenile
        QTimer.singleShot(100, self.box_view.state_manager.load_counts_with_sync)
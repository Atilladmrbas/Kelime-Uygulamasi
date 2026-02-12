"""
DECORATOR'LAR - Eski ile tamamen aynı
Değişmeyecek, sadece import'lar güncellenecek
"""

from PyQt6.QtCore import Qt
from .base_manager import get_drag_drop_manager, DropTarget


def draggable_card():
    """
    Decorator: Kart sınıfını draggable yap
    """
    def decorator(cls):
        original_mouse_press = cls.mousePressEvent
        
        def new_mouse_press(self, event):
            if event.button() == Qt.MouseButton.LeftButton:
                self._drag_start_pos = event.position().toPoint()
                event.accept()
                return
            
            if original_mouse_press:
                original_mouse_press(self, event)
        
        original_mouse_move = cls.mouseMoveEvent
        
        def new_mouse_move(self, event):
            if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, '_drag_start_pos'):
                manhattan_length = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
                if manhattan_length >= 10:
                    get_drag_drop_manager().start_drag(self, event)
                    self._drag_start_pos = None
                    return
            
            if original_mouse_move:
                original_mouse_move(self, event)
        
        cls.mousePressEvent = new_mouse_press
        cls.mouseMoveEvent = new_mouse_move
        
        return cls
    
    return decorator


def drop_target(target_type: DropTarget):
    """
    Decorator: Widget'ı drop target olarak kaydet
    """
    def decorator(cls):
        original_init = cls.__init__
        
        def new_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            get_drag_drop_manager().register_drop_target(self, target_type)
            
            original_drop = self.dropEvent if hasattr(self, 'dropEvent') else None
            
            def unified_drop_event(event):
                if hasattr(self, 'is_drag_over'):
                    self.is_drag_over = False
                if hasattr(self, '_update_drag_style'):
                    self._update_drag_style(False)
                
                manager = get_drag_drop_manager()
                db = getattr(self, 'db', None)
                manager.process_drop(self, event, db)
            
            self.dropEvent = unified_drop_event
        
        cls.__init__ = new_init
        return cls
    
    return decorator
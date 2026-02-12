# ui/words_panel/box_widgets/detail_window_opener.py
import os
import sys

def open_detail_window_for_box(box_view):
    """
    Basit detail window açıcı - DEBUG VERSION
    """
    try:
        # 1. WordsWindow'u bul
        words_window = None
        current = box_view
        
        while current:
            if hasattr(current, 'container'):
                words_window = current
                break
            current = current.parent()
        
        if not words_window:
            return False
        
        # 2. Import path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        detail_window_dir = os.path.join(current_dir, "..", "detail_window")
        
        if detail_window_dir not in sys.path:
            sys.path.insert(0, detail_window_dir)
        
        # 3. Import et
        try:
            from box_detail_window import BoxDetailWindow
        except ImportError as e:
            return False
        
        # 4. Var olan pencereyi kontrol et
        existing_window = BoxDetailWindow._all_windows.get(box_view.db_id)
        if existing_window and existing_window.is_visible:
            existing_window.close_window()
            return True
        
        # 5. Yeni pencere oluştur
        detail_window = BoxDetailWindow(
            parent=words_window,
            db=None,
            box_id=box_view.db_id,
            box_title=box_view.title,
            origin_widget=box_view
        )
        
        # 6. Pencereyi aç
        detail_window.open_window()
        
        return True
        
    except Exception as e:
        return False
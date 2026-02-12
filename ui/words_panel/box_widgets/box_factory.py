# ui/words_panel/box_widgets/box_factory.py
from .box_view import BoxView

class BoxFactory:
    @staticmethod
    def create_box(title="Yeni Kutu", db_id=None, db_connection=None, **kwargs):
        """BoxView oluştur"""
        box = BoxView(
            title=title,
            db_id=db_id,
            db_connection=db_connection
        )
        
        # Ek özellikler
        for key, value in kwargs.items():
            if hasattr(box, key):
                setattr(box, key, value)
        
        return box
    
    @staticmethod
    def create_box_from_data(data_dict):
        """Dict'ten BoxView oluştur"""
        return BoxFactory.create_box(**data_dict)
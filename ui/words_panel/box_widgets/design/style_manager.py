# ui/words_panel/box_widgets/design/style_manager.py
from PyQt6.QtGui import QColor

class BoxStyleManager:
    """BoxView stillerini merkezi yönetim"""
    
    # Renkler
    COLORS = {
        # Ana renkler
        'background': '#ffffff',
        'border': '#E5E8EE',
        'title_text': '#333333',
        'counter_text': '#888888',
        'counter_inactive': 'rgba(102, 102, 102, 0.3)',
        
        # Buton renkleri
        'button_bg': '#f0f0f0',
        'button_border': '#d0d0d0',
        'button_hover_bg': '#e8e8e8',
        'button_hover_border': '#c0c0c0',
        'button_pressed_bg': '#e0e0e0',
        'button_pressed_border': '#b0b0b0',
        
        # Checkbox renkleri
        'checkbox_checked_bg': '#3b82f6',
        'checkbox_checked_border': '#2563eb',
        'checkbox_hover_bg': '#f0f0f0',
        'checkbox_hover_border': '#c8c8c8',
        'checkbox_default_bg': '#f8f9fa',
        'checkbox_default_border': '#e0e0e0',
        'checkbox_checkmark': '#ffffff',
        
        # Title box
        'title_box_border': '#D4D7DD',
        'title_box_bg': '#ffffff',
        
        # Shadow
        'shadow_color': QColor(0, 0, 0, 90)
    }
    
    # Boyutlar
    SIZES = {
        'base_width': 270,
        'base_height': 230,
        'title_box_height': 52,
        'button_size': 38,
        'icon_size': 22,
        'checkbox_size': 32,
        'border_radius': 20,
        'title_border_radius': 12,
        'button_border_radius': 10,
        'checkbox_border_radius': 6,
        'shadow_blur': 55,
        'shadow_offset': 4,
        'card_margin': 8,
        'expanded_margin': 2,
        'content_margins': (16, 14, 16, 14),
        'content_spacing': 5,
        'bottom_spacing': 12
    }
    
    # Font boyutları
    FONTS = {
        'title_size': 18,
        'counter_base_size': 28,
        'counter_min_size': 24,
        'counter_max_size': 32,
        'counter_font_weight': 'bold',
        'title_font_weight': 600
    }
    
    @classmethod
    def get_card_stylesheet(cls):
        """Ana kart stilini döndür"""
        return f"""
            QFrame#CardFrame {{
                background: {cls.COLORS['background']};
                border-radius: {cls.SIZES['border_radius']}px;
                border: 2px solid {cls.COLORS['border']};
            }}
        """
    
    @classmethod
    def get_title_box_stylesheet(cls):
        """Title box stilini döndür"""
        return f"""
            QFrame {{
                border: 2px solid {cls.COLORS['title_box_border']};
                border-radius: {cls.SIZES['title_border_radius']}px;
                background: {cls.COLORS['title_box_bg']};
            }}
            QLabel, QLineEdit {{
                font-size: {cls.FONTS['title_size']}px;
                font-weight: {cls.FONTS['title_font_weight']};
                background: transparent;
                border: none;
                color: {cls.COLORS['title_text']};
            }}
        """
    
    @classmethod
    def get_counter_stylesheet(cls, has_cards=True):
        """Sayaç stilini döndür"""
        color = cls.COLORS['counter_text'] if has_cards else cls.COLORS['counter_inactive']
        return f"""
            CardCounter {{
                background-color: transparent;
                border: none;
                color: {color};
                padding: 0px;
                margin: 0px;
            }}
        """
    
    @classmethod
    def get_button_stylesheet(cls):
        """Buton stili (hem delete hem enter için)"""
        return f"""
            QPushButton {{
                background-color: {cls.COLORS['button_bg']};
                border: 1px solid {cls.COLORS['button_border']};
                border-radius: {cls.SIZES['button_border_radius']}px;
            }}
            QPushButton:hover {{
                background-color: {cls.COLORS['button_hover_bg']};
                border: 1px solid {cls.COLORS['button_hover_border']};
            }}
            QPushButton:pressed {{
                background-color: {cls.COLORS['button_pressed_bg']};
                border: 1px solid {cls.COLORS['button_pressed_border']};
            }}
        """
    
    @classmethod
    def get_bottom_container_stylesheet(cls):
        """Alt container stilini döndür"""
        return """
            QFrame {
                background: transparent;
                border: none;
            }
        """
    
    @classmethod
    def get_checkbox_colors(cls, is_checked=False, is_hover=False):
        """Checkbox renklerini duruma göre döndür"""
        if is_checked:
            return {
                'bg': cls.COLORS['checkbox_checked_bg'],
                'border': cls.COLORS['checkbox_checked_border'],
                'checkmark': cls.COLORS['checkbox_checkmark']
            }
        elif is_hover:
            return {
                'bg': cls.COLORS['checkbox_hover_bg'],
                'border': cls.COLORS['checkbox_hover_border'],
                'checkmark': None
            }
        else:
            return {
                'bg': cls.COLORS['checkbox_default_bg'],
                'border': cls.COLORS['checkbox_default_border'],
                'checkmark': None
            }
    
    @classmethod
    def get_shadow_effect(cls, widget):
        """Gölge efekti oluştur"""
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(cls.SIZES['shadow_blur'])
        shadow.setOffset(0, cls.SIZES['shadow_offset'])
        shadow.setColor(cls.COLORS['shadow_color'])
        return shadow
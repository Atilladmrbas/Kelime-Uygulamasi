from PyQt6.QtWidgets import (
    QFrame, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout
)
from PyQt6.QtCore import Qt

# Import components
from ..components.counters import CardCounter
from ..components.selection import NotionCheckBox
from ..components.buttons import DeleteButton, EnterButton
from .style_manager import BoxStyleManager


def build_box_design(box_view, card_frame):
    """BoxView için UI layout'u oluştur"""
    # Layout oluştur
    layout = QVBoxLayout(card_frame)
    layout.setContentsMargins(*BoxStyleManager.SIZES['content_margins'])
    layout.setSpacing(BoxStyleManager.SIZES['content_spacing'])
    
    # ----- TITLE BOX -----
    title_box = create_title_box(box_view)
    layout.addWidget(title_box)
    
    # ----- CARD COUNTER -----
    layout.addStretch(1)
    box_view.card_counter = CardCounter(card_frame)
    layout.addWidget(box_view.card_counter, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addStretch(1)
    
    # ----- BOTTOM BUTTONS -----
    bottom_container = create_bottom_container(box_view)
    layout.addWidget(bottom_container)
    
    # Checkbox event bağlantısı
    box_view.checkbox.stateChanged.connect(
        lambda state: box_view.set_selected(state == Qt.CheckState.Checked.value)
    )


def create_title_box(box_view):
    """Title box widget'ını oluştur"""
    title_box = QFrame()
    title_box.setFixedHeight(BoxStyleManager.SIZES['title_box_height'])
    title_box.setStyleSheet(BoxStyleManager.get_title_box_stylesheet())
    
    # Title box layout
    tb_layout = QVBoxLayout(title_box)
    tb_layout.setContentsMargins(0, 0, 0, 0)
    
    # Label (görünen başlık)
    label = QLabel()
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.mouseDoubleClickEvent = box_view.enable_edit
    tb_layout.addWidget(label)
    
    # Editor (düzenleme için)
    editor = QLineEdit()
    editor.hide()
    editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
    editor.editingFinished.connect(box_view.finish_edit)
    tb_layout.addWidget(editor)
    
    # BoxView referansları
    box_view.label = label
    box_view.editor = editor
    
    return title_box


def create_bottom_container(box_view):
    """Alt buton container'ını oluştur"""
    container = QFrame()
    container.setFixedHeight(48)
    container.setStyleSheet(BoxStyleManager.get_bottom_container_stylesheet())
    
    # Layout
    bottom_layout = QHBoxLayout(container)
    bottom_layout.setContentsMargins(0, 0, 0, 0)
    bottom_layout.setSpacing(BoxStyleManager.SIZES['bottom_spacing'])
    
    # Delete butonu
    delete_btn = DeleteButton(size=BoxStyleManager.SIZES['button_size'])
    delete_btn.clicked.connect(box_view.request_delete)
    bottom_layout.addWidget(delete_btn)
    
    # Checkbox
    checkbox = NotionCheckBox()
    bottom_layout.addWidget(checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
    box_view.checkbox = checkbox
    box_view.is_selected = False
    
    # Enter butonu - SADECE detail_window_opener'ı çağırsın
    enter_btn = EnterButton(size=BoxStyleManager.SIZES['button_size'])
    
    # Enter butonuna tıklanınca direkt detail_window_opener'ı çağır
    enter_btn.clicked.connect(lambda: _on_enter_button_clicked(box_view))
    
    bottom_layout.addWidget(enter_btn)
    
    # BoxView referansları
    box_view.enter_btn = enter_btn
    box_view.delete_btn = delete_btn
    
    return container


def _on_enter_button_clicked(box_view):
    """Enter butonuna tıklandığında"""
    if hasattr(box_view, '_deleted') and box_view._deleted:
        return
    
    # detail_window_opener'ı import et ve çağır
    try:
        from ..detail_window_opener import open_detail_window_for_box
        open_detail_window_for_box(box_view)
    except ImportError as e:
        pass
    except Exception as e:
        pass
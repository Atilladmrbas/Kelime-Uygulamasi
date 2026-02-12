# ui/words_panel/box_widgets/components/counters.py
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class CardCounter(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.known_count = 0
        self.unknown_count = 0
        self.has_cards = False
        self.current_font_size = 28
        self.update_text()
        
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_style()
        
    def update_style(self):
        font = QFont()
        font.setPointSize(self.current_font_size)
        font.setWeight(QFont.Weight.Bold)
        self.setFont(font)
        
        if self.has_cards:
            self.setStyleSheet("""
                CardCounter {
                    background-color: transparent;
                    border: none;
                    color: #888888;
                    padding: 0px;
                    margin: 0px;
                }
            """)
        else:
            self.setStyleSheet("""
                CardCounter {
                    background-color: transparent;
                    border: none;
                    color: rgba(102, 102, 102, 0.3);
                    padding: 0px;
                    margin: 0px;
                }
            """)
    
    def update_font_size(self, size: int):
        if size != self.current_font_size:
            self.current_font_size = size
            font = QFont()
            font.setPointSize(size)
            font.setWeight(QFont.Weight.Bold)
            self.setFont(font)
            self.update_style()
        
    def update_counts(self, unknown: int, known: int):
        self.unknown_count = unknown
        self.known_count = known
        self.has_cards = (unknown + known) > 0
        self.update_text()
        self.update_style()
        
    def update_text(self):
        self.setText(f"{self.unknown_count}/{self.known_count}")
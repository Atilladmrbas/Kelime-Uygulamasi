from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton

class WordDetailDialog(QDialog):
    def __init__(self, english, turkish, detail="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{english} → {turkish}")
        self.setMinimumSize(400, 300)

        layout = QVBoxLayout()

        self.detail_edit = QTextEdit()
        self.detail_edit.setText(detail)
        layout.addWidget(self.detail_edit)

        self.save_btn = QPushButton("Kaydet")
        layout.addWidget(self.save_btn)

        self.setLayout(layout)

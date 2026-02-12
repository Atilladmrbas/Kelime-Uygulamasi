# calendar_window.py
# Calendar – FIXED SYMMETRIC GRID (NO BROKEN CELLS)
# 7 columns always, rows = needed
# Missing cells are placeholders: NO content, but borders remain (so grid stays symmetric)

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGridLayout, QSizePolicy, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, QDate

from ui.calendar_panel.day_multi_select_cell import DayMultiSelectContent


# --------------------------------------------------
# PERSISTENT DATE STORE WITH FILE SAVING
# --------------------------------------------------
class CalendarDataStore:
    def __init__(self):
        self._data = {}
        # Dosya yolunu belirle (calendar_panel klasöründe olsun)
        current_dir = Path(__file__).parent
        self._file_path = current_dir / "calendar_data.json"
        self.load_from_file()
    
    def load_from_file(self):
        """Dosyadan kayıtlı verileri yükle"""
        try:
            if self._file_path.exists():
                with open(self._file_path, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            else:
                self._data = {}
                # Boş veriyle dosya oluştur
                self.save_to_file()
        except Exception:
            self._data = {}
    
    def save_to_file(self):
        """Verileri dosyaya kaydet"""
        try:
            # Klasörün var olduğundan emin ol
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self._file_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
    
    def get_values(self, key: str) -> List[Optional[str]]:
        """Bir tarih için değerleri getir"""
        v = self._data.get(key)
        if isinstance(v, list):
            return (v + [None] * 5)[:5]
        return [None] * 5
    
    def set_values(self, key: str, values: List[Optional[str]]):
        """Bir tarih için değerleri ayarla ve dosyaya kaydet"""
        if not isinstance(values, list):
            values = [None] * 5
        
        # 5 değere tamamla
        values = (values + [None] * 5)[:5]
        self._data[key] = values
        
        # Otomatik kaydet
        self.save_to_file()
    
    def clear_month(self, year: int, month: int):
        """Bir ayın tüm verilerini temizle"""
        prefix = f"{year:04d}-{month:02d}-"
        keys_to_delete = []
        
        for k in self._data.keys():
            if k.startswith(prefix):
                keys_to_delete.append(k)
        
        for k in keys_to_delete:
            del self._data[k]
        
        if keys_to_delete:
            self.save_to_file()
    
    def clear_all(self):
        """Tüm verileri temizle"""
        self._data = {}
        self.save_to_file()
    
    def get_all_data(self) -> Dict:
        """Tüm verileri getir (debug için)"""
        return self._data.copy()
    
    def get_file_path(self) -> str:
        """Dosya yolunu döndür"""
        return str(self._file_path)


# --------------------------------------------------
# DAY CELL
# --------------------------------------------------
class DayCell(QWidget):
    CELL_HEIGHT = 210

    def __init__(self, store: CalendarDataStore):
        super().__init__()
        self.store = store
        self.date_key = None

        self.setFixedHeight(self.CELL_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.container = QWidget()
        self.container.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border: 2px solid #e5e7eb;
            }
        """)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self.day_label = QLabel("")
        layout.addWidget(self.day_label, alignment=Qt.AlignmentFlag.AlignLeft)

        self.content = DayMultiSelectContent()
        self.content.values_changed.connect(self.on_values_changed)
        layout.addWidget(self.content)

        layout.addStretch()
        root.addWidget(self.container)
    
    def on_values_changed(self, date_key: str, values: list):
        """Slot değerleri değiştiğinde çağrılır"""
        pass

    def bind_date(self, qdate: QDate, is_today: bool):
        self.date_key = qdate.toString("yyyy-MM-dd")

        self.container.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border: 1px solid #e5e7eb;
            }
        """)

        self.day_label.setText(str(qdate.day()))
        self.content.setVisible(True)

        if is_today:
            self.day_label.setStyleSheet("""
                QLabel {
                    background: #ef4444;
                    color: white;
                    font-size: 14px;
                    font-weight: 700;
                    padding: 2px 8px;
                    border-radius: 4px;
                }
            """)
        else:
            self.day_label.setStyleSheet("""
                QLabel {
                    background: transparent;
                    color: #111827;
                    font-size: 14px;
                    font-weight: 600;
                    padding: 2px 6px;
                }
            """)

        self.content.bind_store(
            self.date_key,
            self.store.get_values,
            self.store.set_values
        )

    def make_placeholder(self):
        """
        Grid bozulmasın diye VAR.
        - Gün numarası göstermez
        - Slotları göstermez
        - Tıklanabilir içerik yok
        - AMA border kalır (simetri için kritik)
        """
        self.date_key = None

        self.day_label.setText("")
        self.day_label.setStyleSheet("""
            QLabel {
                background: transparent;
                color: transparent;
                padding: 0px;
            }
        """)

        self.content.setVisible(False)

        # Border kalsın ki çizgiler devam etsin
        self.container.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border: 1px solid #e5e7eb;
            }
        """)


# --------------------------------------------------
# CALENDAR GRID (PERFECT SYMMETRY)
# --------------------------------------------------
class CalendarGrid(QWidget):
    def __init__(self, store: CalendarDataStore):
        super().__init__()
        self.store = store
        self.today = QDate.currentDate()
        
        # ARKA PLAN BEYAZ YAPILDI
        self.setStyleSheet("background-color: #ffffff;")

        self.grid = QGridLayout(self)
        self.grid.setSpacing(0)
        self.grid.setContentsMargins(0, 0, 0, 0)

        for c in range(7):
            self.grid.setColumnStretch(c, 1)

    def clear(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def render_month(self, year: int, month: int):
        self.clear()

        days = QDate(year, month, 1).daysInMonth()
        rows = (days + 6) // 7  # kaç satır lazım
        total_cells = rows * 7  # son satır dahil 7'ye tamamla

        for r in range(rows):
            self.grid.setRowMinimumHeight(r, DayCell.CELL_HEIGHT)
            self.grid.setRowStretch(r, 0)

        for i in range(total_cells):
            r = i // 7
            c = i % 7

            cell = DayCell(self.store)

            if i < days:
                qdate = QDate(year, month, i + 1)
                cell.bind_date(qdate, qdate == self.today)
            else:
                cell.make_placeholder()

            self.grid.addWidget(cell, r, c)


# --------------------------------------------------
# TOOLBAR WITH CLEAR ALL OPTION
# --------------------------------------------------
class CalendarToolbar(QWidget):
    def __init__(self, prev_cb, next_cb, clear_month_cb, clear_all_cb):
        super().__init__()
        self.setFixedHeight(56)
        
        # ARKA PLAN BEYAZ VE YAZI SİYAH YAPILDI
        self.setStyleSheet("""
            background-color: #ffffff;
            color: #000000;
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        # BAŞLIK - SİYAH YAZI
        self.title = QLabel("")
        self.title.setStyleSheet("""
            font-size: 18px;
            font-weight: 700;
            color: #000000;
        """)

        # Ay temizle butonu
        clear_month_btn = QPushButton("Bu Ayı Temizle")
        clear_month_btn.setStyleSheet("""
            QPushButton {
                background:#fee2e2;
                color:#991b1b;
                border:1px solid #fecaca;
                border-radius:6px;
                padding:4px 10px;
                font-weight:600;
                font-size:12px;
            }
            QPushButton:hover { background:#fecaca; }
        """)
        clear_month_btn.clicked.connect(clear_month_cb)

        # Tümünü temizle butonu
        clear_all_btn = QPushButton("Tümünü Temizle")
        clear_all_btn.setStyleSheet("""
            QPushButton {
                background:#dc2626;
                color:white;
                border:1px solid #dc2626;
                border-radius:6px;
                padding:4px 10px;
                font-weight:600;
                font-size:12px;
            }
            QPushButton:hover { background:#b91c1c; }
        """)
        clear_all_btn.clicked.connect(clear_all_cb)

        # Navigasyon butonları
        prev_btn = QPushButton("◀")
        next_btn = QPushButton("▶")
        prev_btn.clicked.connect(prev_cb)
        next_btn.clicked.connect(next_cb)

        # Buton stilleri
        prev_btn.setStyleSheet("""
            QPushButton {
                background:#f3f4f6;
                color: #000000;
                border:1px solid #d1d5db;
                border-radius:6px;
                padding:6px 12px;
                font-size:14px;
                font-weight:600;
            }
            QPushButton:hover { 
                background:#e5e7eb;
                color: #000000;
            }
        """)
        
        next_btn.setStyleSheet("""
            QPushButton {
                background:#f3f4f6;
                color: #000000;
                border:1px solid #d1d5db;
                border-radius:6px;
                padding:6px 12px;
                font-size:14px;
                font-weight:600;
            }
            QPushButton:hover { 
                background:#e5e7eb;
                color: #000000;
            }
        """)

        layout.addWidget(self.title)
        layout.addWidget(clear_month_btn)
        layout.addWidget(clear_all_btn)
        layout.addStretch()
        layout.addWidget(prev_btn)
        layout.addWidget(next_btn)


# --------------------------------------------------
# MAIN WINDOW WITH FILE STATUS
# --------------------------------------------------
class CalendarWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        # ARKA PLAN BEYAZ YAPILDI
        self.setStyleSheet("""
            background-color: #ffffff;
            color: #000000;
        """)

        self.store = CalendarDataStore()
        self.current = QDate.currentDate()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.toolbar = CalendarToolbar(
            self.prev_month,
            self.next_month,
            self.clear_month,
            self.clear_all
        )
        self.grid = CalendarGrid(self.store)

        root.addWidget(self.toolbar)
        root.addWidget(self.grid, 1)

        self.update_calendar()

    def update_calendar(self):
        self.toolbar.title.setText(self.current.toString("MMMM yyyy"))
        self.grid.render_month(self.current.year(), self.current.month())

    def prev_month(self):
        self.current = self.current.addMonths(-1)
        self.update_calendar()

    def next_month(self):
        self.current = self.current.addMonths(1)
        self.update_calendar()

    def clear_month(self):
        """Sadece mevcut ayı temizle"""
        reply = QMessageBox.question(
            self, 
            "Ayı Temizle", 
            f"{self.current.toString('MMMM yyyy')} ayındaki tüm işaretlemeleri temizlemek istediğinize emin misiniz?\n\nBu işlem geri alınamaz.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.store.clear_month(self.current.year(), self.current.month())
            self.update_calendar()

    def clear_all(self):
        """Tüm takvim verilerini temizle"""
        reply = QMessageBox.question(
            self, 
            "Tümünü Temizle", 
            "Tüm takvim verilerini (tüm aylardaki işaretlemeleri) temizlemek istediğinize emin misiniz?\n\nBu işlem geri alınamaz.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.store.clear_all()
            self.update_calendar()
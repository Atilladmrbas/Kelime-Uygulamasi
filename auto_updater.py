# auto_updater.py
import os
import sys
import json
import requests
import zipfile
import shutil
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox, QProgressDialog
from PyQt6.QtCore import QThread, pyqtSignal, Qt

class UpdateThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, download_url, app_path):
        super().__init__()
        self.download_url = download_url
        self.app_path = Path(app_path)
    
    def run(self):
        try:
            import tempfile
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                
                self.progress.emit(10)
                response = requests.get(self.download_url, stream=True)
                zip_path = tmp_path / "update.zip"
                
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(8192):
                        f.write(chunk)
                
                self.progress.emit(40)
                
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(tmp_path / "extracted")
                
                self.progress.emit(60)
                
                extracted_dir = next((tmp_path / "extracted").iterdir())
                py_files = list(extracted_dir.rglob("*.py"))
                
                for i, src_file in enumerate(py_files):
                    if '__pycache__' not in str(src_file):
                        rel_path = src_file.relative_to(extracted_dir)
                        dst_file = self.app_path / rel_path
                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dst_file)
                    
                    progress = 60 + int((i + 1) / len(py_files) * 30)
                    self.progress.emit(progress)
                
                version_info = {
                    "version": "v1.0.0",
                    "last_update": "2024"
                }
                with open(self.app_path / "version.json", 'w') as f:
                    json.dump(version_info, f)
                
                self.progress.emit(100)
                self.finished.emit(True, "✅ Güncelleme tamamlandı!")
                
        except Exception as hata:
            self.finished.emit(False, f"❌ Hata: {str(hata)}")


class Updater:
    def __init__(self, app_path=None):
        if app_path is None:
            if getattr(sys, 'frozen', False):
                self.app_path = Path(sys.executable).parent
            else:
                self.app_path = Path(__file__).parent
        else:
            self.app_path = Path(app_path)
    
    def check_for_updates(self, parent_widget=None):
        try:
            # SENİN GITHUB REPON!
            url = "https://api.github.com/repos/Atilladmrbas/Kelime-Uygulamasi/releases/latest"
            
            response = requests.get(url, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                latest_version = data['tag_name']
                
                current_version = "v1.0.0"
                version_file = self.app_path / "version.json"
                if version_file.exists():
                    with open(version_file, 'r') as f:
                        veri = json.load(f)
                        current_version = veri.get('version', 'v1.0.0')
                
                if latest_version != current_version:
                    return {
                        'update_available': True,
                        'latest_version': latest_version,
                        'current_version': current_version,
                        'download_url': data['zipball_url'],
                        'release_notes': data['body'][:200] + "..." if data['body'] else ""
                    }
            
            return {'update_available': False}
            
        except Exception as hata:
            print(f"Güncelleme kontrolü başarısız: {hata}")
            return {'update_available': False}
    
    def install_update(self, download_url, parent_widget=None):
        progress = QProgressDialog("Güncelleme hazırlanıyor...", "İptal", 0, 100, parent_widget)
        progress.setWindowTitle("Güncelleme")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(5)
        progress.show()
        
        self.update_thread = UpdateThread(download_url, self.app_path)
        self.update_thread.progress.connect(progress.setValue)
        
        def on_finished(basarili, mesaj):
            progress.close()
            if basarili:
                QMessageBox.information(parent_widget, "Başarılı", 
                    "✅ Güncelleme tamamlandı!\nUygulama yeniden başlatılacak.")
                os.execl(sys.executable, sys.executable, *sys.argv)
            else:
                QMessageBox.warning(parent_widget, "Hata", mesaj)
        
        self.update_thread.finished.connect(on_finished)
        self.update_thread.start()
"""
Global Duplicate Checker - Hard Odaklı, Dil Bağımsız Çift Kontrol Sistemi
Herhangi iki dil çifti için çalışır: EN-TR, RU-TR, ES-NL, vb.
"""

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication
import sqlite3
from typing import Dict, List, Optional, Tuple
import re


class GlobalDuplicateChecker(QObject):
    """
    Global dil çifti duplicate kontrol sistemi
    Hard odaklı tarama: Tam harf eşleşmesi ile çift kontrol
    """
    
    duplicate_found = pyqtSignal(dict)  # Duplicate bulunduğunda
    
    def __init__(self, db=None):
        super().__init__()
        self.db = db
        self.open_contents = {}  # content_id -> BoxDetailContent
        self.word_cache = {}  # Önbellek için {box_id: {container_type: [cards]}}
    
    def set_database(self, db):
        """Veritabanını ayarla"""
        self.db = db
    
    def register_content(self, content_id, content_obj):
        """BoxDetailContent'ı kaydet"""
        self.open_contents[content_id] = content_obj
        self._update_cache_for_content(content_obj)
    
    def unregister_content(self, content_id):
        """BoxDetailContent'ı kaldır"""
        if content_id in self.open_contents:
            del self.open_contents[content_id]
    
    def _update_cache_for_content(self, content_obj):
        """Content'ten kartları cache'e al"""
        if not hasattr(content_obj, 'box_id') or not content_obj.box_id:
            return
        
        box_id = content_obj.box_id
        if box_id not in self.word_cache:
            self.word_cache[box_id] = {"unknown": [], "learned": []}
        
        # Cache'i temizle
        self.word_cache[box_id]["unknown"] = []
        self.word_cache[box_id]["learned"] = []
        
        # Box başlığını al
        box_title = getattr(content_obj, 'box_title', f'Box {box_id}')
        if not box_title:
            box_title = f'Box {box_id}'
        
        # Kartları cache'e al
        for container_type in ["unknown", "learned"]:
            if hasattr(content_obj, 'cards_data') and container_type in content_obj.cards_data:
                for card_data in content_obj.cards_data[container_type]:
                    front = str(card_data.get('english', '')).strip()
                    back = str(card_data.get('turkish', '')).strip()
                    card_id = card_data.get('id')
                    
                    if front and back and card_id:
                        self.word_cache[box_id][container_type].append({
                            'id': card_id,
                            'front': front,
                            'back': back,
                            'container': container_type,
                            'content_id': id(content_obj),
                            'box_title': box_title  # ✅ Box başlığını ekle
                        })
    
    def check_global_pair_duplicate(self, 
                                    front_text: str, 
                                    back_text: str, 
                                    exclude_card_id: Optional[int] = None,
                                    current_box_id: Optional[int] = None,
                                    check_only_same_box: bool = False) -> Dict:
        """Global çift duplicate kontrolü - EZBER KUTULARINI FİLTRELE"""
        
        print("=" * 60)
        print(f"🔍🔍🔍 DUPLICATE_CHECKER ÇAĞRILDI:")
        print(f"   - front_text: '{front_text}'")
        print(f"   - back_text: '{back_text}'")
        print(f"   - exclude_card_id: {exclude_card_id}")
        print(f"   - current_box_id: {current_box_id}")
        print(f"   - check_only_same_box: {check_only_same_box}")
        
        front_clean = front_text.strip()
        back_clean = back_text.strip()
        
        if not front_clean or not back_clean:
            print("❌ Boş kelime, kontrol yapılmıyor")
            return {'has_duplicate': False, 'total_count': 0, 'found_locations': []}
        
        result = {
            'has_duplicate': False,
            'word_pair': (front_clean, back_clean),
            'found_locations': [],
            'total_count': 0,
            'check_only_same_box': check_only_same_box
        }
        
        print(f"📊 Clean kelimeler: '{front_clean}' → '{back_clean}'")
        
        # Box başlıkları için cache
        box_titles_cache = {}
        
        # 1. AÇIK PENCERELERDE ARA - EZBER KUTULARINI FİLTRELE
        print(f"🔍 Açık pencerelerde aranıyor ({len(self.open_contents)} pencere)...")
        
        for content_id, content in self.open_contents.items():
            # Box ID'yi integer olarak al
            content_box_id = getattr(content, 'box_id', 0)
            
            # Box başlığını al
            box_title = self._get_box_title_for_content(content, content_box_id)
            
            # ✅ EZBER KUTULARINI BAŞLIĞA GÖRE FİLTRELE
            if self._is_memory_box(box_title):
                print(f"   - Pencere {content_id} filtrelendi (Ezber Kutusu: '{box_title}')")
                continue
                
            # ✅ DÜZELTME: check_only_same_box True ise filtrele
            if check_only_same_box and current_box_id and content_box_id != current_box_id:
                print(f"   - Pencere {content_id} filtrelendi (sadece Box {current_box_id} aranıyor)")
                continue
            
            print(f"   - Pencere: {content_id}, Box ID: {content_box_id}, Başlık: '{box_title}'")
            
            # Cache'e kaydet
            box_titles_cache[content_box_id] = box_title
            
            for container_type in ["unknown", "learned"]:
                if hasattr(content, 'cards_data') and container_type in content.cards_data:
                    for card_data in content.cards_data[container_type]:
                        card_id = card_data.get('id')
                        
                        if exclude_card_id and card_id == exclude_card_id:
                            print(f"      - Kart {card_id} exclude edildi (kendisi)")
                            continue
                        
                        card_front = str(card_data.get('english', '')).strip()
                        card_back = str(card_data.get('turkish', '')).strip()
                        
                        # HARD ODARLI KONTROL: Tam çift eşleşmesi
                        if (card_front.lower() == front_clean.lower() and 
                            card_back.lower() == back_clean.lower()):
                            
                            print(f"      ⚠️ DUPLICATE BULUNDU! Kart {card_id}: '{card_front}' → '{card_back}'")
                            
                            result['has_duplicate'] = True
                            result['total_count'] += 1
                            
                            result['found_locations'].append({
                                'box_id': content_box_id,
                                'box_title': box_title,
                                'container': container_type,
                                'card_id': card_id,
                                'content_id': content_id,
                                'front': card_front,
                                'back': card_back,
                                'same_box': content_box_id == current_box_id if current_box_id else False,
                                'is_open_window': True
                            })
        
        # 2. VERİTABANINDA ARA (kapalı pencereler için) - EZBER KUTULARINI FİLTRELE
        if self.db:
            print(f"🔍 Veritabanında aranıyor...")
            try:
                cursor = self.db.conn.cursor()
                
                # SQL sorgusu - EZBER KUTULARINI FİLTRELE
                sql_query = """
                    SELECT w.id, w.box, w.bucket 
                    FROM words w
                    WHERE LOWER(TRIM(w.english)) = ? 
                    AND LOWER(TRIM(w.turkish)) = ?
                    AND w.box NOT IN (
                        SELECT id FROM boxes 
                        WHERE title LIKE '%Her Gün%' 
                        OR title LIKE '%Ezber%' 
                        OR title LIKE '%Daily%'
                        OR title LIKE '%Memory%'
                    )
                """
                params = [front_clean.lower(), back_clean.lower()]
                
                if exclude_card_id:
                    sql_query += " AND w.id != ?"
                    params.append(exclude_card_id)
                
                # ✅ EK FİLTRE: check_only_same_box True ise sadece current_box_id'yi ara
                if check_only_same_box and current_box_id:
                    sql_query += " AND w.box = ?"
                    params.append(current_box_id)
                
                print(f"   - SQL sorgusu: {sql_query}")
                print(f"   - Parametreler: {params}")
                
                cursor.execute(sql_query, params)
                rows = cursor.fetchall()
                print(f"   - SQL sorgu sonucu: {len(rows)} satır")
                
                # Her satırı işle
                for row_idx, row in enumerate(rows):
                    card_id = row[0]
                    box_id = row[1]
                    bucket = row[2]
                    
                    print(f"      - Satır {row_idx+1}: ID={card_id}, Box={box_id}, Bucket={bucket}")
                    
                    # Box başlığını belirle
                    box_title = self._get_box_title_from_db(box_id)
                    
                    # ✅ EZBER KUTUSU KONTROLÜ (yedek kontrol)
                    if self._is_memory_box(box_title):
                        print(f"         - Box {box_id} filtrelendi (Ezber Kutusu: '{box_title}')")
                        continue
                    
                    print(f"      ⚠️ VERİTABANINDA DUPLICATE BULUNDU! Kart {card_id}, Box {box_id}")
                    
                    # Cache'de varsa onu kullan (açık penceredeki isim daha güncel olabilir)
                    if box_id in box_titles_cache:
                        box_title = box_titles_cache[box_id]
                        print(f"         - Cache box_title: {box_title}")
                    else:
                        print(f"         - DB box_title: {box_title}")
                    
                    result['has_duplicate'] = True
                    result['total_count'] += 1
                    
                    container_type = "unknown" if bucket == 0 else "learned"
                    
                    result['found_locations'].append({
                        'box_id': box_id,
                        'box_title': box_title,
                        'container': container_type,
                        'card_id': card_id,
                        'content_id': None,  # Kapalı pencere
                        'front': front_clean,
                        'back': back_clean,
                        'same_box': box_id == current_box_id if current_box_id else False,
                        'is_open_window': False
                    })
                    
            except Exception as e:
                print(f"❌ Veritabanı duplicate kontrol hatası: {e}")
                import traceback
                traceback.print_exc()
        
        # DEBUG: Tüm bulunan lokasyonları göster
        if result['found_locations']:
            print(f"📋 BULUNAN DUPLICATE'LAR ({len(result['found_locations'])} adet):")
            for i, loc in enumerate(result['found_locations'], 1):
                same_box_mark = "✅" if loc.get('same_box') else "🌍"
                window_status = "🪟" if loc.get('is_open_window') else "📂"
                print(f"   {i}. {same_box_mark} {window_status} {loc.get('box_title', f'Box {loc.get("box_id")}')} - {loc['container']} - ID: {loc['card_id']}")
        
        print(f"📊 SONUÇ: has_duplicate={result['has_duplicate']}, total_count={result['total_count']}")
        print("=" * 60)
        
        return result

    def _is_memory_box(self, box_title: str) -> bool:
        """Box başlığının ezber kutusu olup olmadığını kontrol et"""
        if not box_title:
            return False
        
        memory_keywords = [
            'Her Gün', 'Ezber', 'Daily', 'Memory', 
            'Günlük', 'Gün', 'Hergün', 'HerGün'
        ]
        
        box_title_lower = box_title.lower()
        for keyword in memory_keywords:
            if keyword.lower() in box_title_lower:
                return True
        
        return False
    
    def _get_box_title_for_content(self, content, box_id):
        """Content'ten box başlığını al"""
        box_title = f"Box {box_id}"
        
        try:
            # 1. Yol: content'in kendi box_title özelliği
            if hasattr(content, 'box_title') and content.box_title:
                box_title = content.box_title
                print(f"   - Content box_title: {box_title}")
                return box_title
            
            # 2. Yol: DB'den box başlığını al
            if hasattr(self, 'db') and self.db:
                db_title = self._get_box_title_from_db(box_id)
                if db_title != f"Box {box_id}":
                    box_title = db_title
                    print(f"   - DB box_title: {box_title}")
                    return box_title
            
            # 3. Yol: parent window'dan al
            if hasattr(content, 'window') and content.window():
                window = content.window()
                
                # BoxDetailWindow kontrolü
                if hasattr(window, 'box_title') and window.box_title:
                    box_title = window.box_title
                    print(f"   - Window box_title: {box_title}")
                    return box_title
                
                # title_label kontrolü
                if hasattr(window, 'title_label') and hasattr(window.title_label, 'text'):
                    title_text = window.title_label.text()
                    if title_text and title_text.strip():
                        box_title = title_text.strip()
                        print(f"   - Window title_label: {box_title}")
                        return box_title
            
            # 4. Yol: content'in parent'larında ara
            parent = content.parent()
            while parent:
                if hasattr(parent, 'box_title') and parent.box_title:
                    box_title = parent.box_title
                    print(f"   - Parent box_title: {box_title}")
                    return box_title
                parent = parent.parent()
                
        except Exception as e:
            print(f"   - Box başlığı alınırken hata: {e}")
        
        return box_title
    
    def _get_box_title_from_db(self, box_id):
        """Veritabanından box başlığını al - get_box_info metodunu kullan"""
        if not self.db or not box_id:
            return f"Box {box_id}"
        
        try:
            # DB'nin get_box_info metodunu kullan
            if hasattr(self.db, 'get_box_info'):
                box_info = self.db.get_box_info(box_id)
                if box_info and 'title' in box_info and box_info['title']:
                    return box_info['title']
            
            # Alternatif: doğrudan SQL sorgusu
            cursor = self.db.conn.cursor()
            
            # Önce boxes tablosunu kontrol et
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='boxes'")
            if cursor.fetchone():
                cursor.execute("SELECT title FROM boxes WHERE id=?", (box_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    return row[0]
            
            # Başka bir tablo olabilir mi kontrol et
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%box%'")
            box_tables = cursor.fetchall()
            for table in box_tables:
                table_name = table[0]
                try:
                    cursor.execute(f"SELECT title FROM {table_name} WHERE id=?", (box_id,))
                    row = cursor.fetchone()
                    if row and row[0]:
                        return row[0]
                except:
                    continue
                    
        except Exception as e:
            print(f"   - DB'den box başlığı alınırken hata: {e}")
        
        return f"Box {box_id}"
    
    def check_duplicate_on_card_update(self, card_id: int, new_front: str, new_back: str) -> Dict:
        """Kart güncellendiğinde duplicate kontrolü"""
        return self.check_global_pair_duplicate(new_front, new_back, exclude_card_id=card_id)
    
    def check_duplicate_on_card_add(self, front_text: str, back_text: str, box_id: Optional[int] = None) -> Dict:
        """Yeni kart eklenirken duplicate kontrolü"""
        return self.check_global_pair_duplicate(front_text, back_text, current_box_id=box_id)
    
    def get_similar_pairs(self, front_text: str, back_text: str, threshold: float = 0.7) -> List[Dict]:
        """
        Benzer çiftleri bul (opsiyonel - ileri seviye)
        Levenshtein distance veya benzerlik algoritması ile
        """
        # Bu kısım isteğe bağlı, şimdilik basit bırakıyorum
        return []
    
    def clear_cache(self):
        """Önbelleği temizle"""
        self.word_cache.clear()
    
    def refresh_all_caches(self):
        """Tüm content'lerin cache'ini yenile"""
        for content in self.open_contents.values():
            self._update_cache_for_content(content)


# Global singleton instance
_global_duplicate_checker = None

def get_duplicate_checker(db=None):
    """Global duplicate checker instance'ını al"""
    global _global_duplicate_checker
    if _global_duplicate_checker is None:
        _global_duplicate_checker = GlobalDuplicateChecker(db)
    elif db and not _global_duplicate_checker.db:
        _global_duplicate_checker.db = db
    
    return _global_duplicate_checker

def init_duplicate_checker(db):
    """Duplicate checker'ı başlat"""
    return get_duplicate_checker(db)
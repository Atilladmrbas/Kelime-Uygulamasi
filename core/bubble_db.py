# core/bubble_db.py
import sqlite3
import os
from datetime import datetime


class BubbleDatabase:
    """Bubble içerikleri için ayrı database - CORE klasöründe"""
    
    def __init__(self, db_path=None):
        if db_path:
            self.db_path = db_path
        else:
            # CORE klasörü içinde bubbles.db oluştur
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(base_dir, "bubbles.db")
        
        self._init_db()
    
    def _init_db(self):
        """Database ve tabloları oluştur - width/height alanları eklendi"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bubbles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER UNIQUE NOT NULL,
                box_id INTEGER,
                html_content TEXT NOT NULL,
                width INTEGER DEFAULT 320,
                height INTEGER DEFAULT 200,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Eski tabloda width/height yoksa ekle (migrasyon)
        cursor.execute("PRAGMA table_info(bubbles)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'width' not in columns:
            cursor.execute("ALTER TABLE bubbles ADD COLUMN width INTEGER DEFAULT 320")
            print("✅ [BubbleDatabase] width alanı eklendi")
        
        if 'height' not in columns:
            cursor.execute("ALTER TABLE bubbles ADD COLUMN height INTEGER DEFAULT 200")
            print("✅ [BubbleDatabase] height alanı eklendi")
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bubbles_card_id 
            ON bubbles(card_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bubbles_box_id 
            ON bubbles(box_id)
        """)
        
        conn.commit()
        conn.close()
    
    def _get_connection(self):
        """Database connection oluştur"""
        return sqlite3.connect(self.db_path)
    
    def save_bubble(self, card_id, html_content, box_id=None, width=None, height=None):
        """
        Bubble kaydet/güncelle - BOYUT MUTLAKA KAYDEDİLMELİ!
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Varsayılan değerler
            if width is None:
                width = 320
            if height is None:
                height = 200
            
            # Önce var mı kontrol et
            cursor.execute("SELECT id FROM bubbles WHERE card_id = ?", (card_id,))
            exists = cursor.fetchone()
            
            now = datetime.now()
            
            if exists:
                # GÜNCELLEME - width/height DAHİL!
                cursor.execute("""
                    UPDATE bubbles 
                    SET html_content = ?, box_id = ?, width = ?, height = ?, updated_at = ?
                    WHERE card_id = ?
                """, (html_content, box_id, width, height, now, card_id))
                print(f"✅ [BubbleDB] Bubble güncellendi: {card_id}, {width}x{height}")
            else:
                # YENİ KAYIT - width/height DAHİL!
                cursor.execute("""
                    INSERT INTO bubbles (card_id, html_content, box_id, width, height, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (card_id, html_content, box_id, width, height, now))
                print(f"✅ [BubbleDB] Yeni bubble kaydedildi: {card_id}, {width}x{height}")
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"❌ [BubbleDB.save_bubble] Hata: {e}")
            conn.rollback()
            return False
            
        finally:
            conn.close()
    
    def get_bubble(self, card_id):
        """Bubble içeriğini getir - width/height dahil"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT id, card_id, box_id, html_content, width, height, created_at, updated_at " 
                "FROM bubbles WHERE card_id = ?", 
                (card_id,)
            )
            row = cursor.fetchone()
            
            if row:
                columns = ['id', 'card_id', 'box_id', 'html_content', 'width', 'height', 'created_at', 'updated_at']
                result = dict(zip(columns, row))
                
                # width/height None ise varsayılan değer ata
                if result.get('width') is None:
                    result['width'] = 320
                if result.get('height') is None:
                    result['height'] = 200
                    
                return result
            return None
            
        except Exception as e:
            print(f"❌ [BubbleDatabase.get_bubble] Hata: {e}")
            return None
            
        finally:
            conn.close()
    
    def update_box_id(self, card_id, new_box_id):
        """Kart taşınınca box_id güncelle"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE bubbles 
                SET box_id = ?, updated_at = ?
                WHERE card_id = ?
            """, (new_box_id, datetime.now(), card_id))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ [BubbleDatabase.update_box_id] Hata: {e}")
            conn.rollback()
            return False
            
        finally:
            conn.close()
    
    def update_bubble_size(self, card_id, width, height):
        """Sadece width/height güncelle (performans için)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE bubbles 
                SET width = ?, height = ?, updated_at = ?
                WHERE card_id = ?
            """, (width, height, datetime.now(), card_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            print(f"❌ [BubbleDatabase.update_bubble_size] Hata: {e}")
            conn.rollback()
            return False
            
        finally:
            conn.close()
    
    def delete_bubble(self, card_id):
        """Bubble sil"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM bubbles WHERE card_id = ?", (card_id,))
            conn.commit()
            
            if cursor.rowcount > 0:
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ [BubbleDatabase.delete_bubble] Hata: {e}")
            conn.rollback()
            return False
            
        finally:
            conn.close()
    
    def get_bubbles_by_box(self, box_id):
        """Belirli bir kutuya ait bubble'ları getir - width/height dahil"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT id, card_id, box_id, html_content, width, height, created_at, updated_at "
                "FROM bubbles WHERE box_id = ?", 
                (box_id,)
            )
            
            rows = cursor.fetchall()
            columns = ['id', 'card_id', 'box_id', 'html_content', 'width', 'height', 'created_at', 'updated_at']
            
            result = []
            for row in rows:
                item = dict(zip(columns, row))
                # width/height None ise varsayılan değer ata
                if item.get('width') is None:
                    item['width'] = 320
                if item.get('height') is None:
                    item['height'] = 200
                result.append(item)
            
            return result
            
        except Exception as e:
            print(f"❌ [BubbleDatabase.get_bubbles_by_box] Hata: {e}")
            return []
            
        finally:
            conn.close()
    
    def migrate_all_bubbles(self):
        """Tüm bubble'lara width/height ekle (default değer)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # width veya height NULL olanları güncelle
            cursor.execute("""
                UPDATE bubbles 
                SET width = 320, height = 200 
                WHERE width IS NULL OR height IS NULL
            """)
            
            conn.commit()
            print(f"✅ [BubbleDatabase] {cursor.rowcount} bubble migrate edildi")
            return cursor.rowcount
            
        except Exception as e:
            print(f"❌ [BubbleDatabase.migrate_all_bubbles] Hata: {e}")
            conn.rollback()
            return 0
            
        finally:
            conn.close()
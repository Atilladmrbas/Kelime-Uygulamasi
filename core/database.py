# database.py
import os
import sqlite3


class Database:
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(base_dir, "words.db")

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        self.create_tables()
        self._migrate_words_table()
        self._add_copy_fields()

    def create_tables(self):
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS boxes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                english TEXT NOT NULL,
                turkish TEXT NOT NULL,
                detail TEXT,
                box INTEGER,
                bucket INTEGER DEFAULT 0,
                original_card_id INTEGER DEFAULT NULL,
                is_copy BOOLEAN DEFAULT 0,
                is_drawn BOOLEAN DEFAULT 0,
                FOREIGN KEY (box) REFERENCES boxes(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drawn_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_card_id INTEGER NOT NULL,
                copy_card_id INTEGER NOT NULL,
                box_id INTEGER NOT NULL,
                drawn_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (original_card_id) REFERENCES words(id),
                FOREIGN KEY (copy_card_id) REFERENCES words(id),
                FOREIGN KEY (box_id) REFERENCES boxes(id)
            )
        """)
        
        self.conn.commit()

    def _migrate_words_table(self):
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(words)")
        columns = [row["name"] for row in cursor.fetchall()]

        if "bucket" not in columns:
            cursor.execute(
                "ALTER TABLE words ADD COLUMN bucket INTEGER DEFAULT 0"
            )
            self.conn.commit()

        if "original_card_id" not in columns:
            cursor.execute("ALTER TABLE words ADD COLUMN original_card_id INTEGER DEFAULT NULL")
        
        if "is_copy" not in columns:
            cursor.execute("ALTER TABLE words ADD COLUMN is_copy BOOLEAN DEFAULT 0")
        
        if "is_drawn" not in columns:
            cursor.execute("ALTER TABLE words ADD COLUMN is_drawn BOOLEAN DEFAULT 0")
        
        self.conn.commit()

    def _add_copy_fields(self):
        self._migrate_words_table()

    def mark_copy_as_drawn(self, original_card_id, copy_card_id, box_id):
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE drawn_cards 
                SET is_active = 0 
                WHERE original_card_id = ? AND is_active = 1
            """, (original_card_id,))
            
            cursor.execute("""
                INSERT INTO drawn_cards (original_card_id, copy_card_id, box_id, is_active)
                VALUES (?, ?, ?, 1)
            """, (original_card_id, copy_card_id, box_id))
            
            cursor.execute("UPDATE words SET is_drawn=1 WHERE id=?", (copy_card_id,))
            
            self.conn.commit()
            return True
            
        except Exception:
            self.conn.rollback()
            return False

    def mark_copy_as_available(self, original_card_id):
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                UPDATE drawn_cards 
                SET is_active = 0 
                WHERE original_card_id = ? AND is_active = 1
            """, (original_card_id,))
            self.conn.commit()
            return True
        except Exception:
            return False

    def get_available_copy(self, original_card_id, target_box_id=1):
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT id FROM words 
            WHERE original_card_id = ? AND is_copy = 1
            LIMIT 1
        """, (original_card_id,))
        
        existing_copy = cursor.fetchone()
        
        if existing_copy:
            return None
        
        original = self.get_word_by_id(original_card_id)
        if not original:
            return None
        
        english = original.get('english', '').strip()
        turkish = original.get('turkish', '').strip()
        if not english and not turkish:
            return None
        
        cursor.execute("""
            INSERT INTO words (english, turkish, detail, box, bucket, original_card_id, is_copy, is_drawn)
            VALUES (?, ?, ?, ?, ?, ?, 1, 0)
        """, (
            english,
            turkish,
            original.get('detail', '{}'),
            target_box_id,
            0,
            original_card_id,
        ))
        
        self.conn.commit()
        new_id = cursor.lastrowid
        return new_id

    def get_drawn_copy_for_original(self, original_card_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT dc.copy_card_id FROM drawn_cards dc
            WHERE dc.original_card_id = ? AND dc.is_active = 1
        """, (original_card_id,))
        
        row = cursor.fetchone()
        return row["copy_card_id"] if row else None

    def is_copy_currently_drawn(self, copy_card_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id FROM drawn_cards 
            WHERE copy_card_id = ? AND is_active = 1
        """, (copy_card_id,))
        
        row = cursor.fetchone()
        return row is not None

    def reset_drawn_status_for_copy(self, copy_card_id):
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                UPDATE drawn_cards 
                SET is_active = 0 
                WHERE copy_card_id = ? AND is_active = 1
            """, (copy_card_id,))
            
            cursor.execute("UPDATE words SET is_drawn=0 WHERE id=?", (copy_card_id,))
            
            self.conn.commit()
            return True
        except Exception:
            return False

    def mark_card_as_drawn(self, card_id, is_drawn=True):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE words SET is_drawn=? WHERE id=?",
            (1 if is_drawn else 0, card_id)
        )
        self.conn.commit()
        return True

    def is_card_drawn(self, card_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT is_drawn FROM words WHERE id=?", (card_id,))
        row = cursor.fetchone()
        return row["is_drawn"] == 1 if row else False

    def reset_drawn_status_in_box(self, box_id):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "UPDATE words SET is_drawn=0 WHERE box=? AND is_copy=1",
                (box_id,)
            )
            
            cursor.execute("""
                UPDATE drawn_cards 
                SET is_active = 0 
                WHERE box_id = ? AND is_active = 1
            """, (box_id,))
            
            self.conn.commit()
            return cursor.rowcount
        except Exception:
            return 0

    def get_undrawn_copy_cards_in_box(self, box_id):
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT * FROM words 
                WHERE box = ? 
                AND is_copy = 1 
                AND is_drawn = 0
                ORDER BY RANDOM()
                LIMIT 50
            """, (box_id,))
            
            rows = cursor.fetchall()
            result = []
            
            for row in rows:
                result.append(dict(row))
            
            return result
            
        except Exception:
            return []

    def get_boxes(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title FROM boxes ORDER BY id ASC")
        
        user_boxes = []
        system_box_titles = [
            'Her gün',
            'İki günde bir',
            'Dört günde bir',
            'Dokuz günde bir',
            'On dört günde bir'
        ]
        
        for row in cursor.fetchall():
            box_id = row["id"]
            title = row["title"]
            
            if title not in system_box_titles and not title.startswith("Kutu "):
                user_boxes.append((box_id, title))
        
        return user_boxes

    def get_next_available_box_id(self):
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("SELECT id FROM boxes ORDER BY id")
            existing_ids = [row[0] for row in cursor.fetchall()]
            
            if not existing_ids:
                return 1
            
            for i in range(1, max(existing_ids) + 2):
                if i not in existing_ids:
                    return i
                    
            return max(existing_ids) + 1
            
        except Exception:
            cursor.execute("SELECT MAX(id) FROM boxes")
            max_id = cursor.fetchone()[0]
            return (max_id or 0) + 1

    def add_box(self, title):
        cursor = self.conn.cursor()
        
        try:
            system_titles = [
                'Her gün',
                'İki günde bir',
                'Dört günde bir',
                'Dokuz günde bir',
                'On dört günde bir'
            ]
            if title in system_titles:
                return None
            
            next_id = self.get_next_available_box_id()
            
            cursor.execute(
                "INSERT INTO boxes (id, title) VALUES (?, ?)",
                (next_id, title)
            )
            self.conn.commit()
            return next_id
            
        except Exception:
            self.conn.rollback()
            return None

    def delete_box(self, box_id):
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT title FROM boxes WHERE id=?", (box_id,))
        box_info = cursor.fetchone()
        
        if box_info:
            title = box_info["title"]
            
            system_titles = [
                'Her gün',
                'İki günde bir',
                'Dört günde bir',
                'Dokuz günde bir',
                'On dört günde bir'
            ]
            
            if title in system_titles:
                return False
            
            cursor.execute("DELETE FROM words WHERE box=?", (box_id,))
            cursor.execute("DELETE FROM boxes WHERE id=?", (box_id,))
            self.conn.commit()
            return True
        else:
            return False

    def update_box_title(self, box_id, new_title):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE boxes SET title=? WHERE id=?",
            (new_title, box_id),
        )
        self.conn.commit()

    def get_box_info(self, box_id: int):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title FROM boxes WHERE id = ?", (box_id,))
        row = cursor.fetchone()
        if row:
            return {"id": row["id"], "title": row["title"]}
        return None

    def get_box_by_title(self, title: str):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title FROM boxes WHERE title = ?", (title,))
        row = cursor.fetchone()
        if row:
            return {"id": row["id"], "title": row["title"]}
        return None

    def cleanup_auto_boxes(self):
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT id, title FROM boxes WHERE title LIKE 'Kutu %'")
        auto_boxes = cursor.fetchall()
        
        deleted_count = 0
        for box in auto_boxes:
            box_id = box["id"]
            
            cursor.execute("DELETE FROM words WHERE box=?", (box_id,))
            cursor.execute("DELETE FROM boxes WHERE id=?", (box_id,))
            deleted_count += 1
        
        if deleted_count > 0:
            self.conn.commit()
        
        return deleted_count

    def add_word(self, english, turkish, detail, box_id, bucket=0, original_card_id=None, is_copy=False):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO words (english, turkish, detail, box, bucket, original_card_id, is_copy)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (english, turkish, detail, box_id, bucket, original_card_id, is_copy),
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_word(self, word_id, english, turkish, detail, box_id, bucket):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE words
            SET english=?, turkish=?, detail=?, box=?, bucket=?
            WHERE id=?
            """,
            (english, turkish, detail, box_id, bucket, word_id),
        )
        self.conn.commit()

    def update_word_bucket(self, word_id: int, bucket: int) -> bool:
        """Kartın bucket değerini güncelle"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE words SET bucket = ? WHERE id = ?",
                (bucket, word_id)
            )
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ update_word_bucket hatası: {e}")
            self.conn.rollback()
            return False

    def update_word_box(self, word_id, box_id, bucket=0):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE words SET box=?, bucket=? WHERE id=?",
            (box_id, bucket, word_id),
        )
        self.conn.commit()
        return True

    def delete_word(self, word_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM words WHERE id=?", (word_id,))
        self.conn.commit()

    def get_cards_by_box_and_bucket(self, box_id, bucket):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM words
            WHERE box=? AND bucket=?
            ORDER BY id ASC
            """,
            (box_id, bucket),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_all_words(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM words ORDER BY id ASC")
        return [dict(row) for row in cursor.fetchall()]

    def get_card_info(self, card_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM words WHERE id = ?", (card_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_card_box(self, card_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT box FROM words WHERE id=?", (card_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    def get_cards_by_box(self, box_id, only_copies=False, only_originals=False):
        cursor = self.conn.cursor()
        
        if only_copies:
            cursor.execute(
                """
                SELECT * FROM words
                WHERE box=? AND is_copy=1
                ORDER BY id ASC
                """,
                (box_id,),
            )
        elif only_originals:
            cursor.execute(
                """
                SELECT * FROM words
                WHERE box=? AND is_copy=0
                ORDER BY id ASC
                """,
                (box_id,),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM words
                WHERE box=?
                ORDER BY id ASC
                """,
                (box_id,),
            )
        return [dict(row) for row in cursor.fetchall()]

    def get_words_by_box(self, box_id):
        return self.get_cards_by_box(box_id)

    def get_word_by_id(self, word_id: int):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM words WHERE id = ?", (word_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def get_cards_count_by_box(self, box_id: int):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM words WHERE box = ?", (box_id,))
        row = cursor.fetchone()
        return row["count"] if row else 0
    
    def get_cards_count_by_bucket(self, box_id: int, bucket: int):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as count FROM words WHERE box = ? AND bucket = ?", 
            (box_id, bucket)
        )
        row = cursor.fetchone()
        return row["count"] if row else 0

    def get_daily_box_id(self):
        box_info = self.get_box_by_title("Her gün")
        if box_info:
            return box_info["id"]
        return None
    
    def create_system_box_on_demand(self, title):
        system_titles = [
            'Her gün',
            'İki günde bir',
            'Dört günde bir',
            'Dokuz günde bir',
            'On dört günde bir'
        ]
        
        if title not in system_titles:
            return None
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM boxes WHERE title = ?", (title,))
        if cursor.fetchone():
            cursor.execute("SELECT id FROM boxes WHERE title = ?", (title,))
            return cursor.fetchone()["id"]
        
        cursor.execute("INSERT INTO boxes (title) VALUES (?)", (title,))
        self.conn.commit()
        box_id = cursor.lastrowid
        return box_id

    def unassign_card_from_box(self, card_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE words SET box=NULL, bucket=0 WHERE id=?",
            (card_id,)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def add_word_copy(self, original_card_id, target_box_id=1):
        return self.get_available_copy(original_card_id, target_box_id)

    def delete_copy_cards(self, original_card_id=None, box_id=None):
        cursor = self.conn.cursor()
        
        if original_card_id:
            cursor.execute("DELETE FROM words WHERE original_card_id=? AND is_copy=1", (original_card_id,))
            cursor.execute("DELETE FROM drawn_cards WHERE original_card_id=?", (original_card_id,))
        elif box_id:
            cursor.execute("DELETE FROM words WHERE box=? AND is_copy=1", (box_id,))
            cursor.execute("DELETE FROM drawn_cards WHERE box_id=?", (box_id,))
        else:
            cursor.execute("DELETE FROM words WHERE is_copy=1")
            cursor.execute("DELETE FROM drawn_cards")
        
        self.conn.commit()
        return cursor.rowcount

    def mark_original_as_learned(self, original_card_id):
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("SELECT bucket, is_copy FROM words WHERE id=?", (original_card_id,))
            row = cursor.fetchone()
            
            if row:
                current_bucket = row[0]
                is_copy = row[1]
                
                if is_copy == 0 and current_bucket != 1:
                    cursor.execute("UPDATE words SET bucket=1 WHERE id=?", (original_card_id,))
            
            self.conn.commit()
            return True
            
        except Exception:
            self.conn.rollback()
            return False

    def get_copy_cards_by_original(self, original_card_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM words 
            WHERE original_card_id=? AND is_copy=1
            ORDER BY box ASC
        """, (original_card_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_original_card_id(self, copy_card_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT original_card_id FROM words WHERE id=?", (copy_card_id,))
        row = cursor.fetchone()
        return row["original_card_id"] if row else None

    def is_card_copy(self, card_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT is_copy FROM words WHERE id=?", (card_id,))
        row = cursor.fetchone()
        return row["is_copy"] == 1 if row else False

    def copy_cards_from_box(self, source_box_id, target_box_id=1):
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT id FROM words 
            WHERE box=? AND is_copy=0 AND bucket=0
        """, (source_box_id,))
        
        original_cards = cursor.fetchall()
        copied_count = 0
        
        for row in original_cards:
            original_id = row["id"]
            copy_id = self.get_available_copy(original_id, target_box_id)
            if copy_id:
                copied_count += 1
        
        return copied_count

    def get_copies_of_card(self, original_card_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id FROM words 
            WHERE original_card_id = ? AND is_copy = 1
        """, (original_card_id,))
        return [row["id"] for row in cursor.fetchall()]

    def get_copy_cards_of_original(self, original_card_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM words WHERE original_card_id=? AND is_copy=1", (original_card_id,))
        return [row["id"] for row in cursor.fetchall()]

    def get_copy_cards_in_box(self, box_id):
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT DISTINCT w1.* FROM words w1
                WHERE w1.box = ? 
                AND w1.is_copy = 1
                AND w1.id = (
                    SELECT MIN(w2.id) 
                    FROM words w2 
                    WHERE w2.original_card_id = w1.original_card_id 
                    AND w2.box = w1.box
                    AND w2.is_copy = 1
                )
                ORDER BY w1.original_card_id ASC
            """, (box_id,))
            
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                result.append({
                    'id': row[0],
                    'english': row[1],
                    'turkish': row[2],
                    'detail': row[3],
                    'box_id': row[4],
                    'bucket': row[5],
                    'original_card_id': row[6],
                    'is_copy': row[7] if len(row) > 7 else 0
                })
            return result
            
        except Exception:
            return []

    def get_original_cards_in_box(self, box_id):
        return self.get_cards_by_box(box_id, only_originals=True)

    def __del__(self):
        try:
            if self.conn:
                self.conn.close()
        except:
            pass
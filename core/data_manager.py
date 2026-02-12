# ---------------- CARDS BY BOX ----------------

def get_cards_by_box(self, box_id):
    """Belirli bir kutuya ait tüm kelimeleri döndürür."""
    all_words = self.load_words()
    return [w for w in all_words if w.get("box") == str(box_id)]


def add_card(self, flashcard):
    """Yeni bir kart ekler."""
    words = self.load_words()
    words.append(flashcard.to_dict())
    self.save_words(words)


def update_card(self, flashcard):
    """Mevcut bir kartı günceller."""
    words = self.load_words()
    updated = False

    for i, w in enumerate(words):
        if w.get("id") == flashcard.id:
            words[i] = flashcard.to_dict()
            updated = True
            break

    if not updated:
        words.append(flashcard.to_dict())

    self.save_words(words)


def delete_card(self, card_id):
    """Kart siler."""
    words = self.load_words()
    words = [w for w in words if w.get("id") != card_id]
    self.save_words(words)

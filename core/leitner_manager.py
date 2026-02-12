from datetime import date
import random

INTERVALS = [1, 2, 5, 10, 20]

class LeitnerManager:
    def get_due_words(self, words):
        today = str(date.today())
        due = []
        for w in words:
            level = w.get("level",1)
            last = w.get("last_review", today)
            days_passed = (date.fromisoformat(today) - date.fromisoformat(last)).days
            if days_passed >= INTERVALS[level-1]:
                due.append(w)
        return due

    def check_answer(self, word, answer, words):
        correct = answer.strip().lower() == word['turkish'].lower()
        today = str(date.today())
        for w in words:
            if w['english'] == word['english']:
                if correct:
                    w['level'] = min(w.get("level",1)+1,5)
                else:
                    w['level'] = 1
                w['last_review'] = today
                break
        return correct, words

    def select_random_word(self, words):
        if not words:
            return None
        return random.choice(words)

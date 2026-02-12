import uuid

class FlashCardData:
    def __init__(self, english, turkish, detail="", box=None, bucket=0, id=None, box_id=None):
        self.id = id or str(uuid.uuid4())
        self.english = english
        self.turkish = turkish
        self.detail = detail
        self.box = box  # String box name
        self.box_id = box_id  # Integer box ID from database
        self.bucket = bucket

    def to_dict(self):
        return {
            "id": self.id,
            "english": self.english,
            "turkish": self.turkish,
            "detail": self.detail,
            "box": self.box,
            "box_id": self.box_id,
            "bucket": self.bucket
        }
    
    def to_json(self):
        """JSON formatında döndür (drag-drop için)"""
        import json
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data):
        """Dict'ten FlashCardData oluştur"""
        return cls(
            english=data.get("english", ""),
            turkish=data.get("turkish", ""),
            detail=data.get("detail", ""),
            box=data.get("box"),
            box_id=data.get("box_id"),
            bucket=data.get("bucket", 0),
            id=data.get("id")
        )
    
    @classmethod
    def from_db_row(cls, row):
        """Database row'dan FlashCardData oluştur"""
        return cls(
            id=row.get("id"),
            english=row.get("english", ""),
            turkish=row.get("turkish", ""),
            detail=row.get("detail", ""),
            box_id=row.get("box"),
            bucket=row.get("bucket", 0)
        )
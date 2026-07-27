"""
Database models for the backend's metadata store.

Note: this database holds ONLY metadata. The actual file bytes never
touch it — they live entirely in the storage service. This separation
is one of the core things you'll be asked to justify in the viva.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class FileRecord(db.Model):
    __tablename__ = "file_records"

    id = db.Column(db.Integer, primary_key=True)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(300), nullable=False)   # name used in storage service
    owner = db.Column(db.String(120), nullable=True)
    size_bytes = db.Column(db.Integer, nullable=False)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "original_name": self.original_name,
            "owner": self.owner,
            "size_bytes": self.size_bytes,
            "upload_time": self.upload_time.isoformat(),
        }
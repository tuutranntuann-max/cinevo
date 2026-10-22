"""Subtitle tracks associated with an online movie."""
from ..extensions import db


class MovieSubtitle(db.Model):
    __tablename__ = "movie_subtitles"

    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), nullable=False, index=True)
    label = db.Column(db.String(80), nullable=False)
    language = db.Column(db.String(35), nullable=False, default="vi")
    source_type = db.Column(db.String(10), nullable=False)
    file_name = db.Column(db.String(100))
    source_url = db.Column(db.String(2048))

    movie = db.relationship("Movie", back_populates="subtitles")

    def to_dict(self):
        return {
            "id": self.id,
            "label": self.label,
            "language": self.language,
            "source_type": self.source_type,
            "format": "vtt" if self.source_type == "upload" else "url",
            "source_url": self.source_url,
        }

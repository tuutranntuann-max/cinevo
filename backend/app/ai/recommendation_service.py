"""AI: gợi ý phim. GIAI ĐOẠN KHUNG: luật đơn giản theo thể loại, chưa gọi mô hình AI thật."""
from ..models import Movie


class MovieRecommendationService:
    def recommend(self, genre: str | None = None, limit: int = 5) -> dict:
        movies = Movie.query.filter_by(status="now_showing").all()
        if genre:
            wanted = genre.strip().lower()
            matched = [m for m in movies if wanted in (m.genre or "").lower()]
            movies = matched or movies
        movies.sort(key=lambda m: m.rating or 0, reverse=True)
        # TODO (AI thật): dùng lịch sử xem của user + embedding/LLM để xếp hạng.
        return {
            "source": "mock-rule-based",
            "genre": genre,
            "message": f"Gợi ý phim thể loại {genre}." if genre else "Phim được đánh giá cao nhất hôm nay.",
            "movies": [m.to_dict() for m in movies[:limit]],
        }

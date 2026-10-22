"""Local, rule-based Cinevo assistant; no third-party AI service is used."""
import re
import unicodedata

from ..models import Booking, Membership, Movie, Showtime, ShopOrder
from ..timeutil import local_now


GENRES = {
    "action": ("hanh dong", "action", "adventure", "phieu luu"),
    "comedy": ("hai", "comedy", "funny"),
    "horror": ("kinh di", "horror", "scary", "ma"),
    "romance": ("tinh cam", "romance", "romantic"),
    "animation": ("hoat hinh", "animation", "animated"),
    "science fiction": ("vien tuong", "sci fi", "science fiction"),
    "drama": ("tam ly", "drama"),
    "family": ("gia dinh", "family", "kids", "tre em"),
}

VIETNAMESE_HINTS = {
    "ban", "toi", "minh", "phim", "ve", "dat", "thich", "goi", "y",
    "gio", "nao", "gi", "giup", "loi", "don", "giao", "dich", "kiem",
}
ENGLISH_HINTS = {
    "about", "am", "an", "and", "are", "book", "booking", "can", "check",
    "details", "do", "error", "film", "films", "find", "for", "hello",
    "hey", "how", "i", "in", "is", "like", "me", "movie", "movies", "my",
    "of", "payment", "please", "recommend", "showtime", "suggest", "tell",
    "the", "ticket", "to", "transaction", "want", "watch", "what", "with",
    "you", "your",
}
RECOMMENDATION_TERMS = (
    "recommend", "suggest", "what should i watch", "movie for me", "goi y",
    "nen xem", "phim nao", "thich", "muon xem", "tim phim",
)
TRANSACTION_TERMS = (
    "transaction", "payment status", "check my payment", "my payment",
    "check my order", "my booking", "my ticket", "order status",
    "giao dich", "thanh toan cua toi", "don hang", "ma ve", "ve cua toi",
    "kiem tra giao dich", "kiem tra thanh toan", "kiem tra don hang",
    "kiem tra ve",
)
BOOKING_TERMS = (
    "book", "booking", "ticket", "seat", "dat ve", "dat ghe", "chon ghe",
    "suat chieu", "how to buy",
)
ERROR_TERMS = (
    "error", "problem", "failed", "failure", "not working", "cannot",
    "khong duoc", "khong the", "bi loi", "gap loi", "loi thanh toan",
)
MOVIE_INFO_TERMS = (
    "about", "information", "details", "showtime", "schedule", "cast",
    "director", "gioi thieu", "chi tiet", "thong tin", "lich chieu",
    "dien vien", "dao dien", "noi dung",
)


def _normalize(value):
    text = unicodedata.normalize("NFD", value.lower().replace("đ", "d"))
    return " ".join("".join(char for char in text if unicodedata.category(char) != "Mn").split())


def _has_any(text, terms):
    return any(term in text for term in terms)


def _language(message, normalized):
    words = set(normalized.split())
    if words.intersection(VIETNAMESE_HINTS):
        return "vi"
    if words.intersection(ENGLISH_HINTS):
        return "en"
    return "vi"


def _money(amount, language):
    value = f"{amount:,.0f}"
    return f"{value} VND" if language == "en" else f"{value}đ"


class ChatbotService:
    def reply(self, message: str, history: list | None = None, user=None) -> dict:
        normalized = _normalize(message)
        language = _language(message, normalized)
        result = {"source": "cinevo-local-assistant", "language": language, "reply": ""}

        if _has_any(normalized, TRANSACTION_TERMS):
            return self._transactions(normalized, language, user, result)

        if _has_any(normalized, ERROR_TERMS):
            result["reply"] = (
                "Please check your internet connection, refresh the page, and verify the booking or payment status in your account. "
                "If it still fails, contact Cinevo support and include your booking code. I cannot confirm transfers directly with your bank."
                if language == "en" else
                "Bạn hãy kiểm tra kết nối mạng, tải lại trang và xem trạng thái vé hoặc thanh toán trong tài khoản. "
                "Nếu vẫn lỗi, hãy liên hệ hỗ trợ Cinevo và gửi mã vé. Trợ lý không thể xác nhận giao dịch trực tiếp với ngân hàng."
            )
            return result

        if _has_any(normalized, BOOKING_TERMS):
            result["reply"] = (
                "Choose a movie, cinema, showtime, and seats. Continue to checkout to confirm your booking. Sign in is required before payment."
                if language == "en" else
                "Bạn chọn phim, rạp, suất chiếu và ghế; sau đó tiếp tục đến bước xác nhận đặt vé. Hệ thống yêu cầu đăng nhập trước khi thanh toán."
            )
            result["action"] = {"label": "Browse movies", "url": "/user/movies"} if language == "en" else {
                "label": "Xem danh sách phim", "url": "/user/movies",
            }
            return result

        genre = next(
            (name for name, terms in GENRES.items() if _has_any(normalized, terms)),
            None,
        )
        if genre or _has_any(normalized, RECOMMENDATION_TERMS):
            return self._recommendations(genre, language, result)

        matching_movie = self._matching_movie(normalized)
        if matching_movie or _has_any(normalized, MOVIE_INFO_TERMS):
            return self._movie_information(matching_movie, language, result)

        if normalized in {"hi", "hello", "hey", "xin chao", "chao", "chao ban"}:
            result["reply"] = (
                "Hello! I can recommend movies, share movie and showtime information, explain bookings, or check your Cinevo transactions."
                if language == "en" else
                "Xin chào! Mình có thể gợi ý phim, cung cấp thông tin và lịch chiếu, hướng dẫn đặt vé hoặc kiểm tra giao dịch Cinevo của bạn."
            )
            return result

        result["reply"] = (
            "I can help with movie recommendations, showtimes, booking steps, and your Cinevo transaction status. What would you like to know?"
            if language == "en" else
            "Mình có thể gợi ý phim, tìm thông tin/lịch chiếu, hướng dẫn đặt vé và kiểm tra giao dịch Cinevo. Bạn muốn hỗ trợ việc nào?"
        )
        return result

    @staticmethod
    def _matching_movie(normalized):
        for movie in Movie.query.all():
            if _normalize(movie.title) in normalized:
                return movie
        return None

    def _recommendations(self, genre, language, result):
        movies = Movie.query.filter_by(status="now_showing").all()
        terms = GENRES.get(genre, ()) if genre else ()
        if terms:
            matches = [movie for movie in movies if _has_any(_normalize(movie.genre or ""), terms)]
            if matches:
                movies = matches
        movies.sort(key=lambda movie: (movie.rating or 0, movie.title), reverse=True)
        result["movies"] = self._movie_cards(movies[:3])
        if result["movies"]:
            result["reply"] = (
                "Here are some movies that may suit you. Tell me a genre or mood if you want more tailored suggestions."
                if language == "en" else
                "Đây là một số phim có thể hợp với bạn. Bạn có thể nói thêm thể loại hoặc tâm trạng để mình gợi ý sát hơn."
            )
        else:
            result["reply"] = (
                "I couldn't find any currently showing movies. Please check the movie list again later."
                if language == "en" else "Hiện chưa tìm thấy phim đang chiếu phù hợp. Bạn thử xem lại danh sách phim sau nhé."
            )
        return result

    def _movie_information(self, movie, language, result):
        if not movie:
            result["reply"] = (
                "Which movie would you like to know about? You can send its title."
                if language == "en" else "Bạn muốn xem thông tin phim nào? Hãy gửi tên phim cho mình nhé."
            )
            result["action"] = {"label": "Browse movies", "url": "/user/movies"} if language == "en" else {
                "label": "Xem danh sách phim", "url": "/user/movies",
            }
            return result

        result["movies"] = self._movie_cards([movie])
        result["reply"] = (
            f"{movie.title}: {movie.genre or 'Genre not listed'}, rated {movie.rating or 0}/10, "
            f"{movie.duration_minutes or 0} minutes, age rating {movie.age_rating or 'not listed'}. Upcoming showtimes are shown below."
            if language == "en" else
            f"{movie.title}: thể loại {movie.genre or 'chưa cập nhật'}, đánh giá {movie.rating or 0}/10, "
            f"thời lượng {movie.duration_minutes or 0} phút, độ tuổi {movie.age_rating or 'chưa cập nhật'}. Lịch chiếu sắp tới ở bên dưới."
        )
        return result

    @staticmethod
    def _movie_cards(movies):
        if not movies:
            return []
        schedule = (
            Showtime.query.filter(
                Showtime.movie_id.in_([movie.id for movie in movies]),
                Showtime.start_time >= local_now(),
            ).order_by(Showtime.start_time).all()
        )
        schedules_by_movie = {}
        for showtime in schedule:
            items = schedules_by_movie.setdefault(showtime.movie_id, [])
            if len(items) < 2:
                items.append({
                    "id": showtime.id,
                    "start_time": showtime.start_time.isoformat(),
                    "cinema": showtime.room.cinema.name,
                    "city": showtime.room.cinema.city,
                    "price": showtime.base_price,
                })
        return [{
            "id": movie.id,
            "title": movie.title,
            "genre": movie.genre or "",
            "rating": movie.rating or 0,
            "age_rating": movie.age_rating or "",
            "duration_minutes": movie.duration_minutes or 0,
            "url": f"/user/movies/{movie.id}",
            "showtimes": schedules_by_movie.get(movie.id, []),
        } for movie in movies]

    def _transactions(self, normalized, language, user, result):
        if not user:
            result["reply"] = (
                "Please sign in first so I can securely check transactions linked to your account."
                if language == "en" else
                "Bạn vui lòng đăng nhập để mình kiểm tra an toàn các giao dịch thuộc tài khoản của bạn."
            )
            result["action"] = {"label": "Sign in", "url": "/user/login"} if language == "en" else {
                "label": "Đăng nhập", "url": "/user/login",
            }
            return result

        transactions = []
        for booking in Booking.query.filter_by(user_id=user.id).order_by(Booking.created_at.desc()).limit(20):
            transactions.append({
                "kind": "ticket", "reference": booking.code, "status": booking.payment.status if booking.payment else booking.status,
                "amount": booking.total_amount, "created_at": booking.created_at.isoformat(),
                "description": booking.showtime.movie.title,
            })
        for membership in Membership.query.filter_by(user_id=user.id).order_by(Membership.created_at.desc()).limit(20):
            transactions.append({
                "kind": "membership", "reference": membership.payment_ref, "status": membership.status,
                "amount": membership.amount, "created_at": membership.created_at.isoformat(),
                "description": membership.tier,
            })
        for order in ShopOrder.query.filter_by(user_id=user.id).order_by(ShopOrder.created_at.desc()).limit(20):
            transactions.append({
                "kind": "shop", "reference": order.code, "status": order.status,
                "amount": order.total_amount, "created_at": order.created_at.isoformat(),
                "description": order.pickup_cinema,
            })
        code = next(
            (token for token in re.findall(r"[a-z0-9-]{6,40}", normalized)
             if any(transaction["reference"].lower() == token for transaction in transactions)),
            None,
        )
        if code:
            transactions = [transaction for transaction in transactions if transaction["reference"].lower() == code]
        else:
            transactions = sorted(transactions, key=lambda item: item["created_at"], reverse=True)[:5]

        if not transactions:
            result["reply"] = (
                "I couldn't find a matching transaction in your account. Check the code or contact Cinevo support."
                if language == "en" else
                "Mình chưa tìm thấy giao dịch khớp trong tài khoản của bạn. Hãy kiểm tra lại mã hoặc liên hệ hỗ trợ Cinevo."
            )
            return result

        status_labels = {
            "PENDING": ("đang chờ xác nhận", "awaiting confirmation"),
            "PAID": ("đã thanh toán", "paid"),
            "CANCELLED": ("đã hủy", "cancelled"),
            "REJECTED": ("bị từ chối", "rejected"),
            "EXPIRED": ("đã hết hạn", "expired"),
            "SCHEDULED": ("đã lên lịch", "scheduled"),
            "ACTIVE": ("đang hoạt động", "active"),
            "READY_FOR_PICKUP": ("sẵn sàng nhận", "ready for pickup"),
            "COLLECTED": ("đã nhận", "collected"),
        }
        for transaction in transactions:
            transaction["status_label"] = status_labels.get(
                transaction["status"],
                (transaction["status"], transaction["status"]),
            )[0 if language == "vi" else 1]
            transaction["amount_label"] = _money(transaction["amount"], language)

        result["transactions"] = transactions
        result["reply"] = (
            "These are the matching transactions recorded in your Cinevo account. Pending status means Cinevo has not confirmed it yet; I cannot verify bank transfers directly."
            if language == "en" else
            "Đây là giao dịch được ghi nhận trong tài khoản Cinevo của bạn. Trạng thái đang chờ nghĩa là Cinevo chưa xác nhận; trợ lý không kiểm tra trực tiếp được giao dịch ngân hàng."
        )
        return result

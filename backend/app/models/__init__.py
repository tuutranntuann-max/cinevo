"""Import toàn bộ model để SQLAlchemy nhận diện khi create_all()."""
from .role import Role, ROLE_USER, ROLE_MANAGER, ROLE_ADMIN, ROLE_EMPLOYEE
from .user import User, OtpCode, STATUS_ACTIVE, STATUS_PENDING, STATUS_LOCKED
from .movie import Movie
from .movie_review import MovieReview
from .support_chat import SupportConversation, SupportMessage, SupportAssignment
from .staff_application import StaffApplication
from .staff_password_reset import StaffPasswordResetRequest
from .movie_trailer import MovieTrailer
from .movie_film import MovieFilm
from .movie_subtitle import MovieSubtitle
from .appearance_settings import AppearanceSettings
from .movie_cancellation import MovieCancellation
from .cinema import Cinema
from .room import Room
from .seat import Seat, SEAT_STANDARD, SEAT_VIP, VIP_SURCHARGE
from .showtime import Showtime
from .food import Food
from .product import Product
from .booking import Booking, BookingSeat, BookingFood
from .payment import Payment, PAYMENT_METHODS
from .expense import Expense
from .promotion import Promotion
from .news_article import NewsArticle
from .cinema_event import CinemaEvent
from .activity_log import ActivityLog, log_activity
from .commerce import CommerceSettings, Membership, ShopOrder, ShopOrderItem
from .seat_hold import SeatHold, UserTrust
from .gmail_oauth import GmailAssistantSettings, GmailOAuthCredential, GmailOAuthState

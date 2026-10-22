"""Đăng ký tất cả blueprint. Mọi API nằm dưới tiền tố /api."""


def register_blueprints(app):
    from .auth import bp as auth_bp
    from .movies import bp as movies_bp
    from .reviews import bp as reviews_bp
    from .support_chat import bp as support_chat_bp
    from .staff_accounts import bp as staff_accounts_bp
    from .cinemas import bp as cinemas_bp
    from .showtimes import bp as showtimes_bp
    from .bookings import bp as bookings_bp
    from .promotions import bp as promotions_bp
    from .content_management import bp as content_management_bp
    from .commerce import bp as commerce_bp
    from .manager import bp as manager_bp
    from .admin import bp as admin_bp
    from .gmail_assistant import bp as gmail_assistant_bp
    from .chatbot import bp as chatbot_bp

    for bp in (
        auth_bp, movies_bp, reviews_bp, support_chat_bp, staff_accounts_bp, cinemas_bp,
        showtimes_bp, bookings_bp, promotions_bp, content_management_bp, manager_bp, admin_bp,
        commerce_bp, gmail_assistant_bp, chatbot_bp,
    ):
        app.register_blueprint(bp)

    # Module AI chỉ được đăng ký khi bật cờ FEATURE_AI (mặc định TẮT).
    if app.config.get("FEATURE_AI"):
        from .ai import bp as ai_bp
        app.register_blueprint(ai_bp)

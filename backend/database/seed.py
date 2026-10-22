"""Tạo bảng + dữ liệu demo cho CINEVO.

Chạy tay:   python database/seed.py --reset     (xóa sạch và tạo lại)
run.py tự động gọi seed_demo() khi database còn trống.
"""
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # cho phép chạy trực tiếp file này

from app import create_app                      # noqa: E402
from app.timeutil import local_now             # noqa: E402
from app.extensions import db                   # noqa: E402
from app.models import (Cinema, CommerceSettings, Food, Movie, Product, Promotion, Role, Room, Seat, Showtime, User,   # noqa: E402
                        ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_USER, SEAT_STANDARD, SEAT_VIP, STATUS_ACTIVE)

DEMO_ACCOUNTS = [
    ("Khách Demo", "user@cinevo.vn", "0900000001", "User@123", ROLE_USER),
    ("Quản lý Demo", "manager@cinevo.vn", "0900000002", "Manager@123", ROLE_MANAGER),
    ("Admin Demo", "admin@cinevo.vn", "0900000003", "Admin@123", ROLE_ADMIN),
]

MOVIES = [  # title, genre, minutes, age, rating, director, status, color, description
    ("Avatar 3: Lửa và Tro Tàn", "Hành động, Khoa học viễn tưởng", 190, "T13", 8.7, "James Cameron", "now_showing", "#0f4c5c",
     "Jake Sully và gia đình đối mặt với tộc Na'vi hung hãn mới trên Pandora."),
    ("Mưa Đỏ", "Chiến tranh, Lịch sử", 125, "T16", 8.9, "Đặng Thái Huyền", "now_showing", "#7f1d1d",
     "Hành trình của những người lính trẻ trong mùa hè năm 1972."),
    ("Tiệc Trăng Máu 2", "Hài, Tâm lý", 110, "T16", 7.8, "Nguyễn Quang Dũng", "now_showing", "#6b21a8",
     "Một bữa tiệc, bảy người bạn và những bí mật nằm trong chiếc điện thoại."),
    ("Bóng Ma Hành Lang", "Kinh dị", 98, "T18", 7.2, "Lê Văn Khoa", "now_showing", "#1f2937",
     "Cư dân tòa chung cư cũ lần lượt nghe tiếng bước chân lúc nửa đêm."),
    ("Hành Tinh Cuối Cùng", "Khoa học viễn tưởng, Phiêu lưu", 135, "P", 8.1, "Anna Rivera", "now_showing", "#92400e",
     "Một phi hành đoàn nhỏ đi tìm ngôi nhà mới cho nhân loại."),
    ("Mùa Hè Rực Rỡ", "Tình cảm, Hài", 105, "P", 7.5, "Trần Hạ My", "coming_soon", "#be123c",
     "Chuyện tình của hai người trẻ trong một mùa hè ở Đà Lạt."),
]

CINEMAS = [("Cinevo Cầu Giấy", "Hà Nội", "Tầng 5, 229 Cầu Giấy, Cầu Giấy", "02438000001"),
           ("Cinevo Nguyễn Huệ", "TP.HCM", "Tầng 3, 35 Nguyễn Huệ, Quận 1", "02838000002")]

FOODS = [("Combo A", "1 Popcorn + 1 Coca", 69000, True), ("Combo B", "2 Popcorn + 2 Coca", 99000, True),
         ("Popcorn lớn", "Bắp rang bơ size L", 49000, False), ("Coca-Cola", "Ly 22oz", 25000, False)]
SHOP_PRODUCTS = [
    ("Kính 3D tiêu chuẩn", "Kính 3D", "Kính xem phim 3D dùng nhiều lần.", 35000, 100),
    ("Kính 3D trẻ em", "Kính 3D", "Gọng nhỏ, phù hợp trẻ em.", 45000, 40),
    ("Hộp đựng kính 3D", "Phụ kiện rạp", "Hộp bảo quản kính xem phim.", 25000, 60),
    ("Khăn lau kính microfiber", "Phụ kiện rạp", "Khăn mềm dùng vệ sinh tròng kính.", 15000, 80),
]

SLOTS = [time(10, 0), time(14, 0), time(19, 0), time(21, 30)]
DAYS = 5
ROWS, COLS = "ABCDEFGH", 10
VIP_ROWS = "FG"


def is_empty() -> bool:
    return Role.query.first() is None


def seed_demo():
    roles = {n: Role(name=n, description=d) for n, d in
             [(ROLE_USER, "Khách hàng"), (ROLE_EMPLOYEE, "Nhân viên rạp"),
              (ROLE_MANAGER, "Quản lý rạp"), (ROLE_ADMIN, "Quản trị hệ thống")]}
    db.session.add_all(roles.values())

    for name, email, phone, pw, role in DEMO_ACCOUNTS:
        u = User(full_name=name, email=email, phone=phone, role=roles[role], status=STATUS_ACTIVE)
        u.set_password(pw)
        db.session.add(u)

    movies = []
    for title, genre, mins, age, rating, director, status, color, desc in MOVIES:
        m = Movie(title=title, genre=genre, duration_minutes=mins, age_rating=age, rating=rating,
                  director=director, status=status, poster_color=color, description=desc,
                  release_date=local_now().date() + timedelta(days=-14 if status == "now_showing" else 30))
        movies.append(m)
    db.session.add_all(movies)

    cinemas = [Cinema(name=n, city=c, address=a, phone=p) for n, c, a, p in CINEMAS]
    db.session.add_all(cinemas)
    db.session.flush()

    rooms = []
    for ci, cinema in enumerate(cinemas):
        for r in range(2):
            room = Room(cinema_id=cinema.id, name=f"Phòng {r + 1:02d}", room_type=["2D", "IMAX"][r],
                        total_rows=len(ROWS), total_cols=COLS)
            db.session.add(room)
            db.session.flush()
            for row in ROWS:
                for n in range(1, COLS + 1):
                    db.session.add(Seat(room_id=room.id, row_label=row, number=n,
                                        seat_type=SEAT_VIP if row in VIP_ROWS else SEAT_STANDARD))
            rooms.append((ci * 2 + r, room))

    showing = [m for m in movies if m.status == "now_showing"]
    for day in range(DAYS):
        for idx, room in rooms:
            for s, slot in enumerate(SLOTS):
                movie = showing[(idx + s + day) % len(showing)]
                db.session.add(Showtime(movie_id=movie.id, room_id=room.id, base_price=90000,
                                        start_time=datetime.combine(local_now().date() + timedelta(days=day), slot)))

    db.session.add_all([Food(name=n, description=d, price=p, is_combo=c) for n, d, p, c in FOODS])
    db.session.add_all([
        Product(name=name, category=category, description=description, price=price,
                stock_quantity=quantity, active=True)
        for name, category, description, price, quantity in SHOP_PRODUCTS
    ])
    db.session.add(CommerceSettings(
        id=1,
        values={"demo_inventory_seeded": True},
    ))
    db.session.add_all([Promotion(code="CINEVO10", description="Giảm 10% cho khách mới", discount_percent=10),
                        Promotion(code="WEEKEND15", description="Giảm 15% suất cuối tuần", discount_percent=15)])
    db.session.commit()


def seed_shop_products():
    settings = db.session.get(CommerceSettings, 1)
    values = dict(settings.values or {}) if settings else {}
    if values.get("demo_inventory_seeded"):
        return
    if Product.query.filter(Product.active.is_(True), Product.stock_quantity > 0).first():
        values["demo_inventory_seeded"] = True
        if settings:
            settings.values = values
        else:
            db.session.add(CommerceSettings(id=1, values=values))
        db.session.commit()
        return
    db.session.add_all([
        Product(name=name, category=category, description=description, price=price,
                stock_quantity=quantity, active=True)
        for name, category, description, price, quantity in SHOP_PRODUCTS
    ])
    values["demo_inventory_seeded"] = True
    if settings:
        settings.values = values
    else:
        db.session.add(CommerceSettings(id=1, values=values))
    db.session.commit()


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        if "--reset" in sys.argv:
            db.drop_all()
        db.create_all()
        if is_empty():
            seed_demo()
            print("Đã tạo database và dữ liệu demo.")
        else:
            print("Database đã có dữ liệu. Dùng --reset để tạo lại.")

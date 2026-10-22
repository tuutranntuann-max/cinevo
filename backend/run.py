"""Điểm chạy backend:  python run.py   (mặc định http://127.0.0.1:5000)

HOST/PORT/FLASK_DEBUG/APP_ENV đọc từ .env. Debug tự tắt nếu HOST không phải localhost hoặc APP_ENV=production.
"""
from app import create_app
from app.config import get_run_settings
from app.extensions import db
from app.models import MovieTrailer, Product, Role, ROLE_EMPLOYEE, StaffApplication
from app.services.staff_privacy import encrypt_staff_data, staff_data_digest
from database.seed import is_empty, seed_demo, seed_shop_products
from sqlalchemy import inspect, text

app = create_app()

with app.app_context():
    db.create_all()          # tạo bảng nếu chưa có
    user_columns = {column["name"] for column in inspect(db.engine).get_columns("users")}
    if "auth_version" not in user_columns:
        db.session.execute(text(
            "ALTER TABLE users ADD COLUMN auth_version INTEGER NOT NULL DEFAULT 0"
        ))
        db.session.commit()
    if "avatar_url" not in user_columns:
        db.session.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(300)"))
        db.session.commit()
    otp_columns = {column["name"] for column in inspect(db.engine).get_columns("otp_codes")}
    if "purpose" not in otp_columns:
        db.session.execute(text(
            "ALTER TABLE otp_codes ADD COLUMN purpose VARCHAR(20) NOT NULL DEFAULT 'REGISTER'"
        ))
        db.session.commit()
    booking_columns = {column["name"] for column in inspect(db.engine).get_columns("bookings")}
    if "discount_amount" not in booking_columns:
        db.session.execute(text(
            "ALTER TABLE bookings ADD COLUMN discount_amount INTEGER NOT NULL DEFAULT 0"
        ))
        db.session.commit()
    if "promo_code" not in booking_columns:
        db.session.execute(text("ALTER TABLE bookings ADD COLUMN promo_code VARCHAR(30)"))
        db.session.commit()
    promotion_columns = {column["name"] for column in inspect(db.engine).get_columns("promotions")}
    if "image_url" not in promotion_columns:
        db.session.execute(text("ALTER TABLE promotions ADD COLUMN image_url VARCHAR(500)"))
        db.session.commit()
    if not Role.query.filter_by(name=ROLE_EMPLOYEE).first():
        db.session.add(Role(name=ROLE_EMPLOYEE, description="Nhân viên hỗ trợ và vận hành rạp"))
        db.session.commit()
    staff_application_columns = {
        column["name"] for column in inspect(db.engine).get_columns("staff_applications")
    }
    legacy_pii_columns = {"citizen_id", "address"} & staff_application_columns
    if legacy_pii_columns:
        for name, column_type in (
            ("citizen_id_ciphertext", "VARCHAR(255)"),
            ("citizen_id_digest", "VARCHAR(64)"),
            ("address_ciphertext", "VARCHAR(600)"),
        ):
            if name not in staff_application_columns:
                db.session.execute(text(
                    f"ALTER TABLE staff_applications ADD COLUMN {name} {column_type}"
                ))
        db.session.commit()
        rows = db.session.execute(text(
            "SELECT id, citizen_id, address, citizen_id_ciphertext, "
            "citizen_id_digest, address_ciphertext FROM staff_applications"
        )).mappings().all()
        for row in rows:
            db.session.execute(
                text(
                    "UPDATE staff_applications SET citizen_id_ciphertext = :encrypted_id, "
                    "citizen_id_digest = :id_digest, address_ciphertext = :encrypted_address "
                    "WHERE id = :application_id"
                ),
                {
                    "encrypted_id": row["citizen_id_ciphertext"] or encrypt_staff_data(row["citizen_id"]),
                    "id_digest": row["citizen_id_digest"] or staff_data_digest(row["citizen_id"]),
                    "encrypted_address": row["address_ciphertext"] or encrypt_staff_data(row["address"]),
                    "application_id": row["id"],
                },
            )
        db.session.commit()
        for index in inspect(db.engine).get_indexes("staff_applications"):
            if "citizen_id" in index["column_names"]:
                index_name = index["name"].replace('"', '""')
                db.session.execute(text(f'DROP INDEX IF EXISTS "{index_name}"'))
        for column in legacy_pii_columns:
            db.session.execute(text(f"ALTER TABLE staff_applications DROP COLUMN {column}"))
        db.session.commit()

    staff_application_columns = {
        column["name"] for column in inspect(db.engine).get_columns("staff_applications")
    }
    if "privacy_accepted" not in staff_application_columns:
        db.session.execute(text(
            "ALTER TABLE staff_applications ADD COLUMN privacy_accepted BOOLEAN NOT NULL DEFAULT 0"
        ))
        db.session.commit()
    db.session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_staff_applications_citizen_id_digest "
        "ON staff_applications (citizen_id_digest)"
    ))
    db.session.commit()
    trailer_columns = {column["name"] for column in inspect(db.engine).get_columns("movie_trailers")}
    if "file_name" not in trailer_columns:
        db.session.execute(text("ALTER TABLE movie_trailers ADD COLUMN file_name VARCHAR(100)"))
        db.session.commit()
    if "audio_file_name" not in trailer_columns:
        db.session.execute(text("ALTER TABLE movie_trailers ADD COLUMN audio_file_name VARCHAR(100)"))
        db.session.commit()
    cinema_columns = {column["name"] for column in inspect(db.engine).get_columns("cinemas")}
    if "chain" not in cinema_columns:
        db.session.execute(text("ALTER TABLE cinemas ADD COLUMN chain VARCHAR(100)"))
        db.session.commit()
    film_columns = {column["name"] for column in inspect(db.engine).get_columns("movie_films")}
    if "image_extension" not in film_columns:
        db.session.execute(text("ALTER TABLE movie_films ADD COLUMN image_extension VARCHAR(10)"))
    if "image_file_name" not in film_columns:
        db.session.execute(text("ALTER TABLE movie_films ADD COLUMN image_file_name VARCHAR(100)"))
    db.session.commit()
    movie_columns = {column["name"] for column in inspect(db.engine).get_columns("movies")}
    if "theatrical_end_date" not in movie_columns:
        db.session.execute(text("ALTER TABLE movies ADD COLUMN theatrical_end_date DATE"))
        db.session.commit()
    if "title_logo_url" not in movie_columns:
        db.session.execute(text("ALTER TABLE movies ADD COLUMN title_logo_url VARCHAR(300)"))
    if "title_logo_enabled" not in movie_columns:
        db.session.execute(text("ALTER TABLE movies ADD COLUMN title_logo_enabled BOOLEAN NOT NULL DEFAULT 0"))
    if "cast_members" not in movie_columns:
        db.session.execute(text("ALTER TABLE movies ADD COLUMN cast_members VARCHAR(500)"))
    db.session.commit()
    for trailer in MovieTrailer.query.filter(MovieTrailer.file_name.is_(None)).all():
        trailer.file_name = f"movie_{trailer.movie_id}.{trailer.extension}"
    db.session.commit()
    if is_empty():           # lần chạy đầu: nạp dữ liệu demo
        seed_demo()
        print(">> Đã tạo database SQLite và dữ liệu demo.")
    elif not Product.query.filter(Product.active.is_(True), Product.stock_quantity > 0).first():
        seed_shop_products()
        print(">> Đã thêm danh mục mẫu cho Cinevo Shop.")

if __name__ == "__main__":
    host, port, debug = get_run_settings()
    app.run(host=host, port=port, debug=debug)

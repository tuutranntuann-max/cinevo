from app.extensions import db
from app.models import Cinema, CommerceSettings, Movie, Product, Role, ROLE_EMPLOYEE, User
from database.seed import SHOP_PRODUCTS, is_empty, seed_demo


def test_demo_seed_repairs_database_with_only_migration_role_and_shop_data(app, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.add(Role(name=ROLE_EMPLOYEE, description="Nhân viên hỗ trợ và vận hành rạp"))
        db.session.add_all([
            Product(name=name, category=category, description=description, price=price,
                    stock_quantity=quantity, active=True)
            for name, category, description, price, quantity in SHOP_PRODUCTS
        ])
        db.session.add(CommerceSettings(id=1, values={"demo_inventory_seeded": True}))
        db.session.commit()

        assert is_empty()
        seed_demo()

        assert Movie.query.count() == 6
        assert Cinema.query.count() == 2
        assert Role.query.count() == 4
        assert User.query.count() == 3
        assert Product.query.count() == len(SHOP_PRODUCTS)
        assert CommerceSettings.query.count() == 1

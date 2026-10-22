from datetime import date
from io import BytesIO

from openpyxl import Workbook

from app.models import Movie


def test_admin_can_import_csv_as_hidden_drafts_and_publish(client, auth, app):
    csv_data = (
        "Tên phim,Thể loại,Thời lượng (phút),Phân loại tuổi,Đạo diễn,Mô tả,Ngày khởi chiếu\n"
        "CSV Import Film,Hành động,125,T16,Đạo diễn thử,Mô tả phim,2026-11-01\n"
        " csv   import film ,Khác,90,T13,,,2026-11-02\n"
    ).encode("utf-8-sig")

    assert client.post("/api/admin/movies/import", data={
        "file": (BytesIO(csv_data), "movies.csv"),
    }).status_code == 401
    assert client.post("/api/admin/movies/import", headers=auth("manager"), data={
        "file": (BytesIO(csv_data), "movies.csv"),
    }).status_code == 403

    response = client.post("/api/admin/movies/import", headers=auth("admin"), data={
        "file": (BytesIO(csv_data), "movies.csv"),
    })
    assert response.status_code == 200
    assert response.get_json()["imported_count"] == 1
    assert response.get_json()["skipped_count"] == 1
    assert response.get_json()["skipped_titles"] == ["csv   import film"]

    public_movies = client.get("/api/movies").get_json()
    assert all(movie["title"] != "CSV Import Film" for movie in public_movies)

    with app.app_context():
        movie = Movie.query.filter_by(title="CSV Import Film").one()
        movie_id = movie.id
        assert movie.status == "draft"
        assert movie.duration_minutes == 125
        assert movie.release_date == date(2026, 11, 1)

    assert client.get("/api/movies").status_code == 200
    assert client.get(f"/api/movies/{movie_id}").status_code == 404
    manager_movies = client.get("/api/manager/movies", headers=auth("manager")).get_json()
    assert all(movie["id"] != movie_id for movie in manager_movies)

    published = client.patch(
        f"/api/admin/movies/{movie_id}/status",
        headers=auth("admin"),
        json={"status": "coming_soon"},
    )
    assert published.status_code == 200
    assert published.get_json()["status"] == "coming_soon"
    assert any(movie["id"] == movie_id for movie in client.get("/api/movies").get_json())
    assert client.get(f"/api/movies/{movie_id}").status_code == 200


def test_admin_can_import_xlsx_and_reject_invalid_file_without_partial_import(client, auth, app):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["Tên phim", "Thời lượng (phút)", "Phân loại tuổi", "Ngày khởi chiếu"])
    worksheet.append(["XLSX Import Film", 110, "P", date(2026, 12, 5)])
    xlsx = BytesIO()
    workbook.save(xlsx)
    workbook.close()

    response = client.post("/api/admin/movies/import", headers=auth("admin"), data={
        "file": (BytesIO(xlsx.getvalue()), "movies.xlsx"),
    })
    assert response.status_code == 200
    assert response.get_json()["imported_count"] == 1
    with app.app_context():
        assert Movie.query.filter_by(title="XLSX Import Film", status="draft").count() == 1
        existing_count = Movie.query.count()

    invalid_csv = (
        "Tên phim,Thời lượng (phút)\n"
        "Valid-looking row,120\n"
        "Invalid duration,nope\n"
    ).encode("utf-8")
    invalid = client.post("/api/admin/movies/import", headers=auth("admin"), data={
        "file": (BytesIO(invalid_csv), "invalid.csv"),
    })
    assert invalid.status_code == 400
    assert "Dòng 3" in invalid.get_json()["message"]
    with app.app_context():
        assert Movie.query.count() == existing_count


def test_admin_movie_import_rejects_unsupported_formats(client, auth):
    response = client.post("/api/admin/movies/import", headers=auth("admin"), data={
        "file": (BytesIO(b"not a workbook"), "movies.xls"),
    })
    assert response.status_code == 400

    corrupt_xlsx = client.post("/api/admin/movies/import", headers=auth("admin"), data={
        "file": (BytesIO(b"not an xlsx file"), "movies.xlsx"),
    })
    assert corrupt_xlsx.status_code == 400

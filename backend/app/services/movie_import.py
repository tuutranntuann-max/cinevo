"""Read and validate movie catalog files uploaded by administrators."""
import csv
from datetime import date, datetime
from io import BytesIO, StringIO
from zipfile import BadZipFile, ZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException


MAX_MOVIE_IMPORT_ROWS = 500
MAX_XLSX_UNCOMPRESSED_BYTES = 20 * 1024 * 1024
MOVIE_IMPORT_HEADERS = {
    "tên phim": "title",
    "title": "title",
    "thể loại": "genre",
    "genre": "genre",
    "thời lượng (phút)": "duration_minutes",
    "duration_minutes": "duration_minutes",
    "phân loại tuổi": "age_rating",
    "age_rating": "age_rating",
    "đạo diễn": "director",
    "director": "director",
    "mô tả": "description",
    "description": "description",
    "ngày khởi chiếu": "release_date",
    "release_date": "release_date",
}


def _rows_from_csv(content):
    text = content.decode("utf-8-sig")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = []
    for row in csv.reader(StringIO(text), dialect):
        rows.append(row)
        if len(rows) > MAX_MOVIE_IMPORT_ROWS + 1:
            raise ValueError(f"Mỗi lần chỉ nhập tối đa {MAX_MOVIE_IMPORT_ROWS} phim.")
    return rows


def _rows_from_xlsx(content):
    with ZipFile(BytesIO(content)) as archive:
        entries = archive.infolist()
        if len(entries) > 1000 or sum(entry.file_size for entry in entries) > MAX_XLSX_UNCOMPRESSED_BYTES:
            raise ValueError("Nội dung giải nén của file Excel vượt quá giới hạn cho phép.")
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    try:
        worksheet = workbook.active
        if worksheet.max_row and worksheet.max_row > MAX_MOVIE_IMPORT_ROWS + 1:
            raise ValueError(f"Mỗi lần chỉ nhập tối đa {MAX_MOVIE_IMPORT_ROWS} phim.")
        return [list(row) for row in worksheet.iter_rows(values_only=True)]
    finally:
        workbook.close()


def _cell_text(value):
    return "" if value is None else str(value).strip()


def _parse_duration(value, row_number):
    if value in (None, ""):
        return 120
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Dòng {row_number}: thời lượng phải là số phút.")
    if not number.is_integer() or not 1 <= number <= 600:
        raise ValueError(f"Dòng {row_number}: thời lượng phải là số nguyên từ 1 đến 600.")
    return int(number)


def _parse_release_date(value, row_number):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        raise ValueError(f"Dòng {row_number}: ngày khởi chiếu phải theo định dạng YYYY-MM-DD.")


def parse_movie_import(content, extension):
    """Return (header map, normalized data rows); raise ValueError on invalid input."""
    try:
        rows = _rows_from_csv(content) if extension == "csv" else _rows_from_xlsx(content)
    except (UnicodeDecodeError, csv.Error) as exc:
        raise ValueError("Không đọc được file. Hãy dùng CSV UTF-8 hoặc Excel .xlsx hợp lệ.") from exc
    except (BadZipFile, InvalidFileException, OSError, KeyError, IndexError) as exc:
        raise ValueError("Không đọc được file Excel. Hãy tải mẫu và thử lại.") from exc

    if not rows:
        raise ValueError("File không có dữ liệu.")

    headers = {}
    for index, value in enumerate(rows[0]):
        key = MOVIE_IMPORT_HEADERS.get(_cell_text(value).casefold())
        if key:
            if key in headers:
                raise ValueError(f"Cột “{key}” bị lặp trong dòng tiêu đề.")
            headers[key] = index
    if "title" not in headers:
        raise ValueError("Thiếu cột bắt buộc “Tên phim” (hoặc “title”).")

    data_rows = []
    errors = []
    nonempty_rows = 0
    for row_number, row in enumerate(rows[1:], start=2):
        if not any(_cell_text(value) for value in row):
            continue
        nonempty_rows += 1
        if nonempty_rows > MAX_MOVIE_IMPORT_ROWS:
            raise ValueError(f"Mỗi lần chỉ nhập tối đa {MAX_MOVIE_IMPORT_ROWS} phim.")
        raw_values = {
            key: row[index] if index < len(row) else None
            for key, index in headers.items()
        }
        values = {key: _cell_text(value) for key, value in raw_values.items()}
        title = values.get("title", "")
        if not title:
            errors.append(f"Dòng {row_number}: thiếu tên phim.")
            continue
        if len(title) > 200:
            errors.append(f"Dòng {row_number}: tên phim vượt quá 200 ký tự.")
            continue

        genre = values.get("genre", "")
        director = values.get("director", "")
        description = values.get("description", "")
        age_rating = values.get("age_rating", "").upper() or "T13"
        if len(genre) > 120:
            errors.append(f"Dòng {row_number}: thể loại vượt quá 120 ký tự.")
            continue
        if len(director) > 120:
            errors.append(f"Dòng {row_number}: đạo diễn vượt quá 120 ký tự.")
            continue
        if len(description) > 5000:
            errors.append(f"Dòng {row_number}: mô tả vượt quá 5000 ký tự.")
            continue
        if age_rating not in {"P", "T13", "T16", "T18"}:
            errors.append(f"Dòng {row_number}: phân loại tuổi phải là P, T13, T16 hoặc T18.")
            continue

        try:
            duration = _parse_duration(raw_values.get("duration_minutes"), row_number)
            release_date = _parse_release_date(raw_values.get("release_date"), row_number)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        data_rows.append({
            "row_number": row_number,
            "title": title,
            "genre": genre or None,
            "duration_minutes": duration,
            "age_rating": age_rating,
            "director": director or None,
            "description": description or None,
            "release_date": release_date,
        })

    if errors:
        preview = " ".join(errors[:10])
        remaining = len(errors) - 10
        if remaining:
            preview += f" Và còn {remaining} dòng có lỗi."
        raise ValueError(preview)
    if not data_rows:
        raise ValueError("File không có dòng phim hợp lệ để nhập.")
    return data_rows

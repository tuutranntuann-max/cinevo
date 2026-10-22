"""Minimal TMDb API client for searching and downloading movie posters."""
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class TmdbError(Exception):
    """A provider, network, or response error that is safe to show to admins."""


POSTER_PATH_RE = re.compile(r"^/[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp)$", re.IGNORECASE)
API_BASE = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p"
USER_AGENT = "CINEVO/1.0 (movie poster search)"
MAX_JSON_BYTES = 1024 * 1024
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def search_movie_posters(title, api_key):
    query = urlencode({
        "api_key": api_key,
        "query": title,
        "include_adult": "false",
        "language": "vi-VN",
        "page": 1,
    })
    data = _read_json(f"{API_BASE}/search/movie?{query}")
    results = data.get("results")
    if not isinstance(results, list):
        raise TmdbError("TMDb trả về danh sách phim không hợp lệ.")

    matches = []
    for item in results:
        if not isinstance(item, dict):
            continue
        poster_path = item.get("poster_path")
        if not isinstance(poster_path, str) or not POSTER_PATH_RE.fullmatch(poster_path):
            continue
        matches.append({
            "id": item.get("id"),
            "title": item.get("title") or item.get("original_title") or "",
            "original_title": item.get("original_title") or "",
            "release_date": item.get("release_date") or "",
            "overview": item.get("overview") or "",
            "poster_path": poster_path,
            "preview_url": f"{IMAGE_BASE}/w342{poster_path}",
        })
        if len(matches) == 8:
            break
    return matches


def download_poster(poster_path):
    if not isinstance(poster_path, str) or not POSTER_PATH_RE.fullmatch(poster_path):
        raise TmdbError("Đường dẫn poster TMDb không hợp lệ.")
    request = Request(
        f"{IMAGE_BASE}/w500{poster_path}",
        headers={"User-Agent": USER_AGENT, "Accept": "image/jpeg,image/png,image/webp"},
    )
    image = _read_response(request, MAX_IMAGE_BYTES)
    extension = poster_path.rsplit(".", 1)[-1].lower()
    if extension == "jpeg":
        extension = "jpg"
    if not _valid_image_signature(image, extension):
        raise TmdbError("TMDb trả về tệp không phải ảnh poster hợp lệ.")
    return image, extension


def _read_json(url):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    response = _read_response(request, MAX_JSON_BYTES)
    try:
        data = json.loads(response)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TmdbError("TMDb trả về dữ liệu không hợp lệ.") from exc
    if not isinstance(data, dict):
        raise TmdbError("TMDb trả về dữ liệu không hợp lệ.")
    return data


def _read_response(request, max_bytes):
    try:
        with urlopen(request, timeout=10) as response:
            content = response.read(max_bytes + 1)
    except HTTPError as exc:
        raise TmdbError(f"TMDb từ chối yêu cầu (HTTP {exc.code}).") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise TmdbError("Không kết nối được TMDb. Vui lòng thử lại sau.") from exc
    if len(content) > max_bytes:
        raise TmdbError("Tệp ảnh hoặc dữ liệu TMDb vượt quá giới hạn cho phép.")
    return content


def _valid_image_signature(image, extension):
    if extension in {"jpg", "jpeg"}:
        return image.startswith(b"\xff\xd8\xff")
    if extension == "png":
        return image.startswith(b"\x89PNG\r\n\x1a\n")
    return len(image) >= 12 and image.startswith(b"RIFF") and image[8:12] == b"WEBP"

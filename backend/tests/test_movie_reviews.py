def create_movie(client, auth, title="Phim đánh giá"):
    response = client.post("/api/admin/movies", headers=auth("admin"), json={
        "title": title,
        "status": "coming_soon",
        "rating": 9.8,
    })
    assert response.status_code == 201
    return response.get_json()["id"]


def test_reviews_are_public_and_average_comes_only_from_real_user_reviews(client, auth):
    movie_id = create_movie(client, auth)
    endpoint = f"/api/movies/{movie_id}/reviews"

    assert client.get(endpoint).status_code == 200
    initial = client.get(endpoint).get_json()
    assert initial["average_rating"] is None
    assert initial["review_count"] == 0
    assert initial["reviews"] == []
    assert client.post(endpoint, json={"rating": 5, "comment": "Rất hay!"}).status_code == 401

    first = client.post(endpoint, headers=auth("user"), json={
        "rating": 4,
        "comment": "Phim hấp dẫn, diễn xuất tốt.",
    })
    assert first.status_code == 201
    assert first.get_json()["created"] is True
    assert first.get_json()["review"]["user_name"] == "Khách Demo"

    second = client.post(endpoint, headers=auth("manager"), json={
        "rating": 2,
        "comment": "Nội dung chưa hợp gu.",
    })
    assert second.status_code == 201

    result = client.get(endpoint).get_json()
    assert result["review_count"] == 2
    assert result["average_rating"] == 3.0
    assert {review["rating"] for review in result["reviews"]} == {2, 4}


def test_user_can_update_and_delete_only_their_own_review(client, auth):
    movie_id = create_movie(client, auth)
    endpoint = f"/api/movies/{movie_id}/reviews"
    headers = auth("user")
    assert client.get(f"{endpoint}/mine").status_code == 401
    assert client.delete(f"{endpoint}/mine").status_code == 401
    created = client.post(endpoint, headers=headers, json={"rating": 5, "comment": "Rất tuyệt vời!"})
    review_id = created.get_json()["review"]["id"]

    own = client.get(f"{endpoint}/mine", headers=headers)
    assert own.status_code == 200
    assert own.get_json()["id"] == review_id
    assert client.get(f"{endpoint}/mine", headers=auth("manager")).get_json() is None

    updated = client.post(endpoint, headers=headers, json={"rating": 3, "comment": "Xem cũng ổn."})
    assert updated.status_code == 200
    assert updated.get_json()["created"] is False
    assert updated.get_json()["review"]["id"] == review_id
    assert client.get(endpoint).get_json()["average_rating"] == 3.0

    deleted = client.delete(f"{endpoint}/mine", headers=headers)
    assert deleted.status_code == 200
    summary = client.get(endpoint).get_json()
    assert summary["review_count"] == 0
    assert summary["average_rating"] is None


def test_reviews_reject_invalid_ratings_comments_and_unknown_movies(client, auth):
    movie_id = create_movie(client, auth)
    endpoint = f"/api/movies/{movie_id}/reviews"
    headers = auth("user")

    assert client.post(endpoint, headers=headers, json={"rating": 0, "comment": "Không hợp lệ"}).status_code == 400
    assert client.post(endpoint, headers=headers, json={"rating": 6, "comment": "Không hợp lệ"}).status_code == 400
    assert client.post(endpoint, headers=headers, json={"rating": 4, "comment": " "}).status_code == 400
    assert client.post(endpoint, headers=headers, json={"rating": 4, "comment": "x" * 1001}).status_code == 400
    assert client.get("/api/movies/99999/reviews").status_code == 404

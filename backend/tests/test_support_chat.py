def test_support_chat_requires_login_and_staff_can_read_reply_and_notify(client, auth):
    customer_endpoint = "/api/support/conversation"
    assert client.get(customer_endpoint).status_code == 401
    assert client.post(customer_endpoint, json={}).status_code == 401
    assert client.get("/api/support/staff/conversations").status_code == 401

    started = client.post(customer_endpoint, headers=auth("user"), json={})
    assert started.status_code == 201
    conversation_id = started.get_json()["id"]
    reopened = client.post(customer_endpoint, headers=auth("user"), json={})
    assert reopened.status_code == 200
    assert reopened.get_json()["id"] == conversation_id

    inbox = client.get("/api/support/staff/conversations", headers=auth("manager")).get_json()
    assert inbox["unread_count"] == 1
    assert inbox["new_conversations"] == 1
    assert inbox["conversations"][0]["customer_name"] == "Khách Demo"

    own_thread = client.get(
        f"/api/support/staff/conversations/{conversation_id}/messages",
        headers=auth("manager"),
    )
    assert own_thread.status_code == 200
    assert own_thread.get_json()["messages"] == []
    read_inbox = client.get("/api/support/staff/conversations", headers=auth("admin")).get_json()
    assert read_inbox["unread_count"] == 0

    sent = client.post(
        f"{customer_endpoint}/{conversation_id}/messages",
        headers=auth("user"),
        json={"body": "Tôi cần hỗ trợ đặt vé."},
    )
    assert sent.status_code == 201
    assert sent.get_json()["message"]["sender_role"] == "USER"
    waiting_reply = client.get(
        f"{customer_endpoint}/{conversation_id}/messages?after_id={sent.get_json()['message']['id']}",
        headers=auth("user"),
    ).get_json()["messages"]
    assert waiting_reply[0]["sender_role"] == "SYSTEM"
    assert "đang liên hệ với nhân viên" in waiting_reply[0]["body"]

    unread = client.get("/api/support/staff/conversations", headers=auth("admin")).get_json()
    assert unread["unread_count"] == 1
    assert unread["new_conversations"] == 1

    accepted = client.post(
        f"/api/support/staff/conversations/{conversation_id}/accept",
        headers=auth("manager"),
        json={},
    )
    assert accepted.status_code == 200
    assert accepted.get_json()["conversation"]["assigned_staff_name"] == "Quản lý Demo"
    conflict = client.post(
        f"/api/support/staff/conversations/{conversation_id}/accept",
        headers=auth("admin"),
        json={},
    )
    assert conflict.status_code == 409

    staff_reply = client.post(
        f"/api/support/staff/conversations/{conversation_id}/messages",
        headers=auth("manager"),
        json={"body": "Nhân viên Cinevo sẵn sàng hỗ trợ bạn."},
    )
    assert staff_reply.status_code == 201
    assert staff_reply.get_json()["message"]["sender_role"] == "MANAGER"

    latest = client.get(
        f"{customer_endpoint}/{conversation_id}/messages?after_id={sent.get_json()['message']['id']}",
        headers=auth("user"),
    ).get_json()
    assert latest["messages"][-1]["body"] == "Nhân viên Cinevo sẵn sàng hỗ trợ bạn."
    assert any("đã nhận hỗ trợ" in message["body"] for message in latest["messages"])


def test_staff_must_accept_before_replying_and_only_assignee_can_reply(client, auth):
    conversation_id = client.post(
        "/api/support/conversation", headers=auth("user"), json={}
    ).get_json()["id"]

    not_assigned = client.post(
        f"/api/support/staff/conversations/{conversation_id}/messages",
        headers=auth("manager"),
        json={"body": "Tôi trả lời trước khi nhận."},
    )
    assert not_assigned.status_code == 409

    client.post(
        f"/api/support/staff/conversations/{conversation_id}/accept",
        headers=auth("manager"),
        json={},
    )
    wrong_staff = client.post(
        f"/api/support/staff/conversations/{conversation_id}/messages",
        headers=auth("admin"),
        json={"body": "Người khác không được trả lời."},
    )
    assert wrong_staff.status_code == 409


def test_customer_cannot_access_another_users_chat_and_can_start_again_after_close(client, auth):
    conversation = client.post("/api/support/conversation", headers=auth("user"), json={}).get_json()
    conversation_id = conversation["id"]

    assert client.get(
        f"/api/support/conversation/{conversation_id}/messages",
        headers=auth("manager"),
    ).status_code == 403
    assert client.get(
        f"/api/support/staff/conversations/{conversation_id}/messages",
        headers=auth("user"),
    ).status_code == 403

    closed = client.post(
        f"/api/support/staff/conversations/{conversation_id}/close",
        headers=auth("manager"),
        json={},
    )
    assert closed.status_code == 200
    assert closed.get_json()["conversation"]["status"] == "closed"
    assert client.get("/api/support/conversation", headers=auth("user")).get_json() is None

    new_conversation = client.post("/api/support/conversation", headers=auth("user"), json={})
    assert new_conversation.status_code == 201
    assert new_conversation.get_json()["id"] != conversation_id


def test_support_chat_validates_message_and_conversation_ownership(client, auth):
    conversation_id = client.post(
        "/api/support/conversation", headers=auth("user"), json={}
    ).get_json()["id"]
    endpoint = f"/api/support/conversation/{conversation_id}/messages"

    assert client.post(endpoint, headers=auth("user"), json={"body": " "}).status_code == 400
    assert client.post(endpoint, headers=auth("user"), json={"body": "x" * 2001}).status_code == 400
    assert client.post(
        endpoint,
        headers=auth("manager"),
        json={"body": "Không được mạo danh khách hàng"},
    ).status_code == 403

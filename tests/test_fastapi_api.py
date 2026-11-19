"""Тесты FastAPI-сервиса (задачи 14, 15, 18, 20)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_service import main as api_main


@pytest.fixture
def client():
    api_main.repository.clear()
    with TestClient(api_main.app) as test_client:
        yield test_client
    api_main.repository.clear()


@pytest.fixture
def published_events(monkeypatch):
    events: list[dict] = []
    monkeypatch.setattr(api_main.publisher, "publish", events.append)
    return events


# 1. Health-check
def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api_service"}


# 2. Создание заявки + публикация события + чтение
def test_create_request_and_publish_event(client, published_events):
    response = client.post(
        "/requests",
        json={
            "equipment_id": 1,
            "description": "Не включается шпиндель",
            "priority": "critical",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["id"] == 1
    assert created["status"] == "open"
    assert created["priority"] == "critical"

    assert len(published_events) == 1
    event = published_events[0]
    assert event["event_type"] == "request.created"
    assert event["request_id"] == created["id"]
    assert event["payload"]["description"] == "Не включается шпиндель"

    detail = client.get(f"/requests/{created['id']}")
    assert detail.status_code == 200
    assert detail.json()["description"] == "Не включается шпиндель"

    listing = client.get("/requests")
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [created["id"]]


# 3. Пустое описание запрещено
@pytest.mark.parametrize("description", ["", "   ", "\n\t"])
def test_empty_description_rejected(client, published_events, description):
    response = client.post(
        "/requests",
        json={"equipment_id": 1, "description": description, "priority": "medium"},
    )

    assert response.status_code == 422
    assert published_events == []


# 4. Неизвестный priority запрещён
def test_unknown_priority_rejected(client, published_events):
    response = client.post(
        "/requests",
        json={"equipment_id": 1, "description": "Течь масла", "priority": "urgent"},
    )

    assert response.status_code == 422
    assert published_events == []


# 5. Поиск заявки и 404
def test_get_request_and_not_found(client):
    missing = client.get("/requests/999")
    assert missing.status_code == 404
    assert "не найдена" in missing.json()["detail"]


# 6. Смена статуса
def test_change_status(client, published_events):
    created = client.post(
        "/requests",
        json={"equipment_id": 2, "description": "Заменить ремень", "priority": "low"},
    ).json()

    response = client.patch(
        f"/requests/{created['id']}/status", json={"status": "in_progress"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"

    invalid = client.patch(
        f"/requests/{created['id']}/status", json={"status": "done"}
    )
    assert invalid.status_code == 422


# 7. Фильтрация списка
def test_list_filters(client, published_events):
    client.post("/requests", json={"equipment_id": 1, "description": "Первая", "priority": "low"})
    client.post("/requests", json={"equipment_id": 1, "description": "Вторая", "priority": "high"})

    by_priority = client.get("/requests", params={"priority": "high"})
    assert [item["description"] for item in by_priority.json()] == ["Вторая"]

    client.patch("/requests/1/status", json={"status": "closed"})
    closed = client.get("/requests", params={"status": "closed"})
    assert [item["id"] for item in closed.json()] == [1]

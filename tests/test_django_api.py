"""Тесты Django REST API (DRF) и журнала аудита (задачи 11, 12, 20)."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from maintenance.audit import build_audit_event
from maintenance.models import Equipment, MaintenanceRequest

pytestmark = pytest.mark.django_db


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def equipment() -> Equipment:
    return Equipment.objects.create(
        inventory_number="INV-001", name="Токарный станок", status=Equipment.Status.IN_WORK
    )


@pytest.fixture
def audit_events(monkeypatch) -> list[dict]:
    events: list[dict] = []

    def fake_log(event_type, request_id, payload, **kwargs):
        event = build_audit_event(event_type, request_id, payload)
        events.append(event)
        return event

    monkeypatch.setattr("maintenance.views.log_request_event", fake_log)
    return events


def make_request(equipment: Equipment, **overrides) -> MaintenanceRequest:
    data = {
        "equipment": equipment,
        "description": "Повышенная вибрация",
        "priority": MaintenanceRequest.Priority.HIGH,
        "status": MaintenanceRequest.Status.OPEN,
    }
    data.update(overrides)
    return MaintenanceRequest.objects.create(**data)


# 1. Создание заявки + событие аудита
def test_create_request_and_audit_event(client, equipment, audit_events):
    response = client.post(
        "/api/requests/",
        {
            "equipment": equipment.pk,
            "description": "Не включается шпиндель",
            "priority": "critical",
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["equipment"] == equipment.pk
    assert body["priority"] == "critical"
    assert body["status"] == "open"

    assert len(audit_events) == 1
    event = audit_events[0]
    assert event["event_type"] == "request.created"
    assert event["request_id"] == body["id"]
    assert event["payload"]["description"] == "Не включается шпиндель"


# 2. Пустое описание запрещено
@pytest.mark.parametrize("description", ["", "   ", "\n\t "])
def test_empty_description_rejected(client, equipment, description):
    response = client.post(
        "/api/requests/",
        {"equipment": equipment.pk, "description": description, "priority": "medium"},
        format="json",
    )

    assert response.status_code == 400
    assert "description" in response.json()


# 3. Неизвестный приоритет запрещён
def test_unknown_priority_rejected(client, equipment):
    response = client.post(
        "/api/requests/",
        {"equipment": equipment.pk, "description": "Течь масла", "priority": "urgent"},
        format="json",
    )

    assert response.status_code == 400
    assert "priority" in response.json()


# 4. Несуществующее оборудование запрещено
def test_unknown_equipment_rejected(client, equipment):
    response = client.post(
        "/api/requests/",
        {"equipment": 999999, "description": "Течь масла", "priority": "low"},
        format="json",
    )

    assert response.status_code == 400
    assert "equipment" in response.json()


# 5. Поиск и получение заявки
def test_retrieve_and_search_request(client, equipment):
    target = make_request(equipment, description="Заменить ремень привода")
    make_request(equipment, description="Почистить фильтр")

    detail = client.get(f"/api/requests/{target.pk}/")
    assert detail.status_code == 200
    assert detail.json()["description"] == "Заменить ремень привода"

    search = client.get("/api/requests/", {"search": "ремень"})
    assert search.status_code == 200
    assert search.json()["count"] == 1
    assert search.json()["results"][0]["id"] == target.pk

    missing = client.get("/api/requests/999999/")
    assert missing.status_code == 404


# 6. Смена статуса через PATCH и через action
def test_change_status(client, equipment, audit_events):
    request = make_request(equipment)

    response = client.patch(
        f"/api/requests/{request.pk}/", {"status": "in_progress"}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
    assert audit_events[-1]["event_type"] == "request.status_changed"
    assert audit_events[-1]["payload"]["status"] == "in_progress"

    action = client.patch(
        f"/api/requests/{request.pk}/status/", {"status": "closed"}, format="json"
    )
    assert action.status_code == 200
    assert action.json()["status"] == "closed"

    invalid = client.patch(
        f"/api/requests/{request.pk}/status/", {"status": "unknown"}, format="json"
    )
    assert invalid.status_code == 400


# 7. Структура документа аудита (тип, id, payload, дата)
def test_audit_event_structure():
    event = build_audit_event(
        "request.created",
        42,
        {"priority": "high", "status": "open"},
    )

    assert event["event_type"] == "request.created"
    assert event["request_id"] == 42
    assert event["payload"] == {"priority": "high", "status": "open"}
    assert event["created_at"].tzinfo is not None


# 8. Корневой путь ведёт на API, а не в 404
def test_home_redirects_to_api(client):
    response = client.get("/")

    assert response.status_code == 302
    assert response["Location"] == "/api/"


# 9. CRUD оборудования и уникальность инвентарного номера
def test_equipment_crud(client):
    created = client.post(
        "/api/equipment/",
        {"inventory_number": "INV-777", "name": "Пресс", "status": "reserve"},
        format="json",
    )
    assert created.status_code == 201

    duplicate = client.post(
        "/api/equipment/",
        {"inventory_number": "INV-777", "name": "Другой пресс", "status": "in_work"},
        format="json",
    )
    assert duplicate.status_code == 400

    listing = client.get("/api/equipment/")
    assert listing.status_code == 200
    assert listing.json()["count"] == 1

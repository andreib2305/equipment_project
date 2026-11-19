"""Тесты формирования и публикации событий (задачи 16–18, 20)."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from api_service.consumer import MaintenanceConsumer
from api_service.events import (
    REQUEST_CREATED_EVENT,
    RabbitMQPublisher,
    build_request_created_event,
)


@pytest.fixture
def request_data() -> dict:
    return {
        "id": 7,
        "equipment_id": 3,
        "description": "Повышенная вибрация",
        "priority": "high",
        "status": "open",
        "created_at": datetime(2026, 11, 19, 10, 0, tzinfo=timezone.utc),
    }


# 1. Формирование события request.created
def test_build_request_created_event(request_data):
    event = build_request_created_event(request_data)

    assert event["event_type"] == REQUEST_CREATED_EVENT == "request.created"
    assert event["request_id"] == 7
    assert event["payload"]["equipment_id"] == 3
    assert event["payload"]["created_at"] == "2026-11-19T10:00:00+00:00"
    assert "created_at" in event

    # Событие должно без ошибок сериализоваться в JSON.
    assert json.loads(json.dumps(event, ensure_ascii=False)) == event


# 2. Публикация в очередь maintenance_requests
def test_publisher_sends_json_to_queue(request_data, fake_pika):
    publisher = RabbitMQPublisher(
        "amqp://guest:guest@localhost:5672/%2F", "maintenance_requests"
    )
    event = build_request_created_event(request_data)

    publisher.publish(event)

    declarations = [item for item in fake_pika if "queue_declare" in item]
    publications = [item for item in fake_pika if "basic_publish" in item]

    assert declarations[0]["queue_declare"] == {
        "queue": "maintenance_requests",
        "durable": True,
    }
    call = publications[0]["basic_publish"]
    assert call["routing_key"] == "maintenance_requests"
    assert call["properties"].content_type == "application/json"
    assert call["properties"].delivery_mode == 2
    assert json.loads(call["body"])["event_type"] == "request.created"
    assert fake_pika[-1] == {"closed": True}


class FakeMethod:
    def __init__(self, delivery_tag: int = 1):
        self.delivery_tag = delivery_tag


class FakeChannel:
    def __init__(self):
        self.acked: list[int] = []
        self.nacked: list[tuple[int, bool]] = []

    def basic_ack(self, delivery_tag):
        self.acked.append(delivery_tag)

    def basic_nack(self, delivery_tag, requeue):
        self.nacked.append((delivery_tag, requeue))


# 3. Consumer подтверждает сообщение после обработки
def test_consumer_acknowledges_message(capsys):
    consumer = MaintenanceConsumer("amqp://guest:guest@localhost:5672/%2F")
    channel = FakeChannel()
    body = json.dumps(
        {"event_type": "request.created", "request_id": 42, "payload": {"id": 42}}
    ).encode("utf-8")

    processed = consumer.handle_message(channel, FakeMethod(), None, body)

    assert processed is True
    assert channel.acked == [1]
    assert channel.nacked == []
    assert "Заявка #42: request.created" in capsys.readouterr().out


# 4. Битое сообщение отклоняется без возврата в очередь
def test_consumer_rejects_broken_message():
    consumer = MaintenanceConsumer("amqp://guest:guest@localhost:5672/%2F")
    channel = FakeChannel()

    processed = consumer.handle_message(channel, FakeMethod(5), None, b"not-json")

    assert processed is False
    assert channel.acked == []
    assert channel.nacked == [(5, False)]

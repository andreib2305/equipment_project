"""Формирование и публикация событий в RabbitMQ (задачи 16–18)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Mapping

logger = logging.getLogger(__name__)

REQUEST_CREATED_EVENT = "request.created"


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def build_request_created_event(request: Mapping[str, Any]) -> dict[str, Any]:
    """Собирает JSON-совместимое событие request.created.

    Функция не зависит от RabbitMQ и покрыта тестом.
    """

    return {
        "event_type": REQUEST_CREATED_EVENT,
        "request_id": int(request["id"]),
        "payload": {
            "id": int(request["id"]),
            "equipment_id": int(request["equipment_id"]),
            "description": request["description"],
            "priority": request["priority"],
            "status": request["status"],
            "created_at": _iso(request["created_at"]),
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


class RabbitMQPublisher:
    """Публикует события в durable-очередь maintenance_requests."""

    def __init__(
        self,
        url: str,
        queue: str = "maintenance_requests",
        *,
        enabled: bool = True,
    ) -> None:
        self.url = url
        self.queue = queue
        self.enabled = enabled

    def publish(self, event: Mapping[str, Any]) -> None:
        if not self.enabled:
            logger.info("RabbitMQ отключён, событие не отправлено: %s", event)
            return

        # pika импортируется лениво: приложение и тесты работают без брокера,
        # пока публикация действительно не потребуется.
        import pika

        body = json.dumps(event, ensure_ascii=False).encode("utf-8")
        parameters = pika.URLParameters(self.url)
        connection = pika.BlockingConnection(parameters)
        try:
            channel = connection.channel()
            channel.queue_declare(queue=self.queue, durable=True)
            channel.basic_publish(
                exchange="",
                routing_key=self.queue,
                body=body,
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,  # persistent
                ),
            )
            logger.info(
                "Событие %s по заявке #%s отправлено в %s",
                event.get("event_type"),
                event.get("request_id"),
                self.queue,
            )
        finally:
            connection.close()

"""Журнал аудита заявок в MongoDB (коллекция audit_events).

Запись в MongoDB не должна ломать основной сценарий API: при недоступной
базе событие пишется в лог приложения, а запрос продолжает обрабатываться.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_client = None
_retry_after = 0.0
_RETRY_INTERVAL = 60.0  # секунд до повторной попытки подключения


def build_audit_event(
    event_type: str,
    request_id: int,
    payload: dict[str, Any],
    created_at: datetime | None = None,
) -> dict[str, Any]:
    """Формирует документ события аудита.

    Структура: тип события, id заявки, полезная нагрузка и дата.
    Вынесена в отдельную функцию, чтобы её можно было проверить тестом
    без запуска MongoDB.
    """

    return {
        "event_type": event_type,
        "request_id": int(request_id),
        "payload": payload,
        "created_at": created_at or datetime.now(timezone.utc),
    }


def get_collection():
    """Возвращает коллекцию audit_events или None, если MongoDB недоступна."""

    global _client, _retry_after

    if not getattr(settings, "MONGO_AUDIT_ENABLED", True):
        return None

    with _lock:
        if _client is not None:
            database = _client[settings.MONGO_DB_NAME]
            return database[settings.MONGO_AUDIT_COLLECTION]

        if time.monotonic() < _retry_after:
            return None

        try:
            from pymongo import MongoClient

            client = MongoClient(
                settings.MONGO_URI,
                serverSelectionTimeoutMS=1500,
                connectTimeoutMS=1500,
            )
            client.admin.command("ping")
        except Exception as exc:  # pragma: no cover - зависит от окружения
            logger.warning("MongoDB недоступна, аудит пишется только в лог: %s", exc)
            _retry_after = time.monotonic() + _RETRY_INTERVAL
            return None

        _client = client
        return _client[settings.MONGO_DB_NAME][settings.MONGO_AUDIT_COLLECTION]


def log_request_event(
    event_type: str,
    request_id: int,
    payload: dict[str, Any],
    *,
    collection=None,
) -> dict[str, Any]:
    """Сохраняет событие изменения заявки в audit_events."""

    event = build_audit_event(event_type, request_id, payload)

    if collection is None:
        collection = get_collection()

    if collection is None:
        logger.info("audit_event %s", event)
        return event

    try:
        collection.insert_one(event)
    except Exception as exc:  # pragma: no cover - зависит от окружения
        logger.warning("Не удалось записать событие аудита: %s", exc)

    return event

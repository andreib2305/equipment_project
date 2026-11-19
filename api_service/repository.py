"""Хранилище заявок FastAPI-сервиса.

В учебном сервисе используется потокобезопасное in-memory хранилище, чтобы
продемонстрировать контракт API без обязательного запуска Django. В целевой
архитектуре (задача 19) источником истины остаётся Django backend: этот
репозиторий заменяется HTTP-клиентом к Django REST API.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any


class InMemoryRequestRepository:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._next_id = 1

    def list(
        self,
        *,
        status: str | None = None,
        priority: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._items.values())

        if status is not None:
            items = [item for item in items if item["status"] == status]
        if priority is not None:
            items = [item for item in items if item["priority"] == priority]

        return sorted(items, key=lambda item: item["id"], reverse=True)

    def get(self, request_id: int) -> dict[str, Any] | None:
        with self._lock:
            item = self._items.get(request_id)
            return dict(item) if item is not None else None

    def create(
        self,
        *,
        equipment_id: int,
        description: str,
        priority: str,
    ) -> dict[str, Any]:
        with self._lock:
            request_id = self._next_id
            self._next_id += 1
            item = {
                "id": request_id,
                "equipment_id": equipment_id,
                "description": description,
                "priority": priority,
                "status": "open",
                "created_at": datetime.now(timezone.utc),
            }
            self._items[request_id] = item
            return dict(item)

    def update_status(self, request_id: int, status: str) -> dict[str, Any] | None:
        with self._lock:
            item = self._items.get(request_id)
            if item is None:
                return None
            item["status"] = status
            return dict(item)

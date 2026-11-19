from __future__ import annotations

import json
import sys
from typing import Any

import pytest


@pytest.fixture
def valid_payload() -> dict[str, Any]:
    return {"equipment_id": 1, "description": "Не включается шпиндель", "priority": "high"}


@pytest.fixture
def fake_pika(monkeypatch):
    """Подменяет pika, чтобы проверить публикацию без брокера."""

    published: list[dict[str, Any]] = []

    class FakeChannel:
        def queue_declare(self, **kwargs):
            published.append({"queue_declare": kwargs})

        def basic_publish(self, **kwargs):
            published.append({"basic_publish": kwargs})

    class FakeConnection:
        def __init__(self, parameters):
            self.parameters = parameters

        def channel(self):
            return FakeChannel()

        def close(self):
            published.append({"closed": True})

    class FakeProperties:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    module = type(sys)("pika")
    module.URLParameters = lambda url: url
    module.BlockingConnection = FakeConnection
    module.BasicProperties = FakeProperties
    monkeypatch.setitem(sys.modules, "pika", module)

    return published

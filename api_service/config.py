"""Конфигурация сервиса api_service (читается из переменных окружения)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    service_name: str = "api_service"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/%2F"
    rabbitmq_queue: str = "maintenance_requests"
    rabbitmq_enabled: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            service_name=os.getenv("SERVICE_NAME", "api_service"),
            rabbitmq_url=os.getenv(
                "RABBITMQ_URL", "amqp://guest:guest@localhost:5672/%2F"
            ),
            rabbitmq_queue=os.getenv("RABBITMQ_QUEUE", "maintenance_requests"),
            rabbitmq_enabled=os.getenv("RABBITMQ_ENABLED", "1") == "1",
        )

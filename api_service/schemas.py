"""Pydantic-модели FastAPI-сервиса (задачи 14–15)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class RequestStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    closed = "closed"


class RequestCreate(BaseModel):
    """Тело POST /requests.

    Пустое (в том числе состоящее из пробелов) описание запрещено.
    Неизвестный priority отклоняется enum-валидацией — 422.
    """

    model_config = ConfigDict(extra="forbid")

    equipment_id: int = Field(..., ge=1, description="ID оборудования в Django backend")
    description: str = Field(..., min_length=1, max_length=2000)
    priority: Priority = Priority.medium

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Описание заявки не может быть пустым")
        return value


class RequestStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: RequestStatus


class RequestRead(BaseModel):
    id: int
    equipment_id: int
    description: str
    priority: Priority
    status: RequestStatus
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    service: str

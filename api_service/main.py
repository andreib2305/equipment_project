"""FastAPI-сервис: API заявок и публикация событий в RabbitMQ.

Эндпоинты (задачи 14–18):
    GET  /health
    GET  /requests
    GET  /requests/{id}
    POST /requests          — создаёт заявку и публикует request.created
    PATCH /requests/{id}/status — смена статуса (используется тестами)
"""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException, Query, status

from api_service.config import Settings
from api_service.events import RabbitMQPublisher, build_request_created_event
from api_service.repository import InMemoryRequestRepository
from api_service.schemas import (
    HealthResponse,
    Priority,
    RequestCreate,
    RequestRead,
    RequestStatus,
    RequestStatusUpdate,
)

logger = logging.getLogger(__name__)
settings = Settings.from_env()

repository = InMemoryRequestRepository()
publisher = RabbitMQPublisher(
    settings.rabbitmq_url,
    settings.rabbitmq_queue,
    enabled=settings.rabbitmq_enabled,
)

app = FastAPI(
    title="Equipment Maintenance API Service",
    description=(
        "Сервис заявок на обслуживание оборудования. "
        "При создании заявки публикует событие request.created в RabbitMQ."
    ),
    version="1.0.0",
)


def get_repository() -> InMemoryRequestRepository:
    return repository


def get_publisher() -> RabbitMQPublisher:
    return publisher


def _not_found(request_id: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Заявка #{request_id} не найдена",
    )


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.service_name)


@app.get("/requests", response_model=list[RequestRead], tags=["requests"])
def list_requests(
    status_filter: RequestStatus | None = Query(default=None, alias="status"),
    priority: Priority | None = Query(default=None),
    repo: InMemoryRequestRepository = Depends(get_repository),
) -> list[dict]:
    return repo.list(
        status=status_filter.value if status_filter else None,
        priority=priority.value if priority else None,
    )


@app.get("/requests/{request_id}", response_model=RequestRead, tags=["requests"])
def get_request(
    request_id: int,
    repo: InMemoryRequestRepository = Depends(get_repository),
) -> dict:
    item = repo.get(request_id)
    if item is None:
        raise _not_found(request_id)
    return item


@app.post(
    "/requests",
    response_model=RequestRead,
    status_code=status.HTTP_201_CREATED,
    tags=["requests"],
)
def create_request(
    payload: RequestCreate,
    repo: InMemoryRequestRepository = Depends(get_repository),
    event_publisher: RabbitMQPublisher = Depends(get_publisher),
) -> dict:
    item = repo.create(
        equipment_id=payload.equipment_id,
        description=payload.description,
        priority=payload.priority.value,
    )

    event = build_request_created_event(item)
    try:
        event_publisher.publish(event)
    except Exception:  # pragma: no cover - брокер недоступен
        # Заявка уже создана; недоставленное событие логируем. В production
        # здесь уместен outbox-паттерн с повторной публикацией.
        logger.exception("Не удалось опубликовать событие %s", event["event_type"])

    return item


@app.patch(
    "/requests/{request_id}/status",
    response_model=RequestRead,
    tags=["requests"],
)
def update_request_status(
    request_id: int,
    payload: RequestStatusUpdate,
    repo: InMemoryRequestRepository = Depends(get_repository),
) -> dict:
    item = repo.update_status(request_id, payload.status.value)
    if item is None:
        raise _not_found(request_id)
    return item

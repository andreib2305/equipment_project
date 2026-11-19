"""Consumer очереди maintenance_requests (задачи 17–18).

Запуск:
    python -m api_service.consumer

Скрипт слушает очередь, печатает номер заявки и тип события и подтверждает
сообщение (basic_ack) только после успешной обработки. При ошибке сообщение
отклоняется без возврата в очередь (basic_nack), чтобы не зацикливать сбойное
сообщение.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from api_service.config import Settings

logger = logging.getLogger(__name__)

DEFAULT_QUEUE = "maintenance_requests"


class MaintenanceConsumer:
    def __init__(
        self,
        url: str,
        queue: str = DEFAULT_QUEUE,
        *,
        auto_ack: bool = False,
    ) -> None:
        self.url = url
        self.queue = queue
        self.auto_ack = auto_ack

    def process_event(self, event: dict[str, Any]) -> None:
        event_type = event.get("event_type", "unknown")
        request_id = event.get("request_id")
        if request_id is None and isinstance(event.get("payload"), dict):
            request_id = event["payload"].get("id")
        if request_id is None:
            raise ValueError("В событии отсутствует request_id")

        print(f"[consumer] Заявка #{request_id}: {event_type}", flush=True)

    def handle_message(self, channel, method, properties, body: bytes) -> bool:
        """Обрабатывает одно сообщение; True — подтверждено, False — отклонено."""

        try:
            event = json.loads(body.decode("utf-8"))
            if not isinstance(event, dict):
                raise ValueError("Сообщение должно быть JSON-объектом")
            self.process_event(event)
        except Exception:
            logger.exception("Не удалось обработать сообщение: %r", body)
            if not self.auto_ack:
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return False

        if not self.auto_ack:
            channel.basic_ack(delivery_tag=method.delivery_tag)
        return True

    def run(self) -> None:
        import pika

        connection = pika.BlockingConnection(pika.URLParameters(self.url))
        channel = connection.channel()
        channel.queue_declare(queue=self.queue, durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(
            queue=self.queue,
            on_message_callback=self.handle_message,
            auto_ack=self.auto_ack,
        )
        print(
            f"[consumer] Ожидание сообщений в очереди '{self.queue}'. "
            "Для остановки нажмите Ctrl+C.",
            flush=True,
        )
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
        finally:
            connection.close()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(asctime)s %(name)s: %(message)s",
    )
    settings = Settings.from_env()
    consumer = MaintenanceConsumer(settings.rabbitmq_url, settings.rabbitmq_queue)

    try:
        consumer.run()
    except Exception as exc:  # pragma: no cover - зависит от брокера
        logger.error("Consumer остановлен: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

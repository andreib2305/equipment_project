"""Задача 13. Синхронная и асинхронная обработка пяти заявок.

Каждая «операция» длится 2 секунды (например, обращение к внешнему сервису).
Запуск:

    python async_demo.py

Ожидаемый результат: синхронный вариант ≈ 10 секунд, асинхронный ≈ 2 секунды.
"""

from __future__ import annotations

import asyncio
import time

REQUEST_IDS = (1, 2, 3, 4, 5)
OPERATION_DELAY = 2.0


def process_request_sync(request_id: int) -> str:
    """Синхронная обработка: поток блокируется на время операции."""

    time.sleep(OPERATION_DELAY)
    return f"Заявка #{request_id} обработана"


async def process_request_async(request_id: int) -> str:
    """Асинхронная обработка: ожидание не блокирует event loop."""

    await asyncio.sleep(OPERATION_DELAY)
    return f"Заявка #{request_id} обработана"


def run_sync() -> tuple[list[str], float]:
    started = time.perf_counter()
    results = [process_request_sync(request_id) for request_id in REQUEST_IDS]
    return results, time.perf_counter() - started


async def run_async() -> tuple[list[str], float]:
    started = time.perf_counter()
    results = await asyncio.gather(
        *(process_request_async(request_id) for request_id in REQUEST_IDS)
    )
    return list(results), time.perf_counter() - started


def format_results(title: str, results: list[str], elapsed: float) -> str:
    lines = [title]
    lines.extend(f"  {result}" for result in results)
    lines.append(f"  Итого: {elapsed:.2f} с")
    return "\n".join(lines)


def main() -> None:
    sync_results, sync_elapsed = run_sync()
    async_results, async_elapsed = asyncio.run(run_async())

    print(format_results("Синхронный вариант:", sync_results, sync_elapsed))
    print()
    print(format_results("Асинхронный вариант (asyncio.gather):", async_results, async_elapsed))
    print()
    print(f"Ускорение: {sync_elapsed / async_elapsed:.1f}x")
    print(
        "Вывод: синхронный код ждёт каждую операцию последовательно, "
        "а asyncio выполняет ожидания параллельно в одном потоке."
    )


if __name__ == "__main__":
    main()

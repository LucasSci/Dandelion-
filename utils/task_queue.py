from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Any, Awaitable, Callable

TaskCallable = Callable[..., Awaitable[Any] | Any]


class TaskQueue:
    def __init__(self, name: str = "dandelion.task_queue") -> None:
        self._name = name
        self._queue: asyncio.Queue[tuple[TaskCallable, tuple[Any, ...], dict[str, Any]]] = asyncio.Queue()
        self._worker: asyncio.Task | None = None
        self._logger = logging.getLogger(name)

    async def start(self) -> None:
        if self._worker and not self._worker.done():
            return
        self._worker = asyncio.create_task(self._run(), name=self._name)

    async def stop(self) -> None:
        if not self._worker:
            return
        self._worker.cancel()
        with suppress(asyncio.CancelledError):
            await self._worker
        self._worker = None

    async def enqueue(self, func: TaskCallable, *args: Any, **kwargs: Any) -> None:
        await self._queue.put((func, args, kwargs))

    async def _run(self) -> None:
        while True:
            func, args, kwargs = await self._queue.get()
            try:
                result = func(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                self._logger.exception("Erro ao processar tarefa enfileirada.")
            finally:
                self._queue.task_done()

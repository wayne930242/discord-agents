import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Generic, TypeVar

from discord_agents.utils.logger import get_logger

logger = get_logger("channel_queue_router")

T = TypeVar("T")
Handler = Callable[[T], Awaitable[None]]


@dataclass(slots=True)
class QueueItem(Generic[T]):
    payload: T
    handler: Handler[T]


class ChannelQueueRouter:
    """Route messages into per-channel queues.

    Messages in the same channel are processed in-order by a single worker.
    Different channels are processed concurrently by different workers.
    """

    def __init__(self, max_pending_per_channel: int = 0) -> None:
        self._queues: Dict[str, asyncio.Queue[QueueItem[object]]] = {}
        self._workers: Dict[str, asyncio.Task[None]] = {}
        self._guard = asyncio.Lock()
        self._closed = False
        self._max_pending_per_channel = max_pending_per_channel

    async def enqueue(self, channel_id: str, payload: T, handler: Handler[T]) -> None:
        if self._closed:
            raise RuntimeError("ChannelQueueRouter is closed")

        queue = await self._ensure_queue(channel_id)
        try:
            queue.put_nowait(QueueItem(payload=payload, handler=handler))
        except asyncio.QueueFull as exc:
            logger.warning(f"Channel queue is full: channel={channel_id}")
            raise RuntimeError(f"Channel queue is full: {channel_id}") from exc

    async def _ensure_queue(self, channel_id: str) -> asyncio.Queue[QueueItem[object]]:
        async with self._guard:
            queue = self._queues.get(channel_id)
            if queue is None:
                queue = asyncio.Queue(maxsize=self._max_pending_per_channel)
                self._queues[channel_id] = queue
                self._workers[channel_id] = asyncio.create_task(
                    self._worker_loop(channel_id),
                    name=f"channel-worker-{channel_id}",
                )
            return queue

    async def _worker_loop(self, channel_id: str) -> None:
        queue = self._queues[channel_id]
        while True:
            item = await queue.get()
            try:
                await item.handler(item.payload)  # type: ignore[arg-type]
            except Exception as exc:
                logger.error(
                    f"Channel worker failed for channel {channel_id}: {exc}",
                    exc_info=True,
                )
            finally:
                queue.task_done()

    async def wait_channel_idle(self, channel_id: str) -> None:
        queue = self._queues.get(channel_id)
        if queue is None:
            return
        await queue.join()

    async def wait_all_idle(self) -> None:
        for queue in self._queues.values():
            await queue.join()

    def pending_counts(self) -> dict[str, int]:
        return {channel_id: queue.qsize() for channel_id, queue in self._queues.items()}

    async def close(self) -> None:
        self._closed = True
        await self.wait_all_idle()
        workers = list(self._workers.values())
        for worker in workers:
            worker.cancel()
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)
        self._workers.clear()
        self._queues.clear()

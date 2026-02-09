import asyncio
import time

import pytest

from discord_agents.scheduler.channel_queue_router import ChannelQueueRouter


@pytest.mark.asyncio
async def test_same_channel_messages_are_processed_in_order() -> None:
    router = ChannelQueueRouter()
    processed: list[str] = []

    async def handler(item: str) -> None:
        await asyncio.sleep(0.01)
        processed.append(item)

    await router.enqueue("channel-1", "a", handler)
    await router.enqueue("channel-1", "b", handler)

    await router.wait_channel_idle("channel-1")
    await router.close()

    assert processed == ["a", "b"]


@pytest.mark.asyncio
async def test_different_channels_are_processed_concurrently() -> None:
    router = ChannelQueueRouter()
    started = asyncio.Event()
    finished = asyncio.Event()
    in_flight = 0
    lock = asyncio.Lock()

    async def handler(_: str) -> None:
        nonlocal in_flight
        async with lock:
            in_flight += 1
            if in_flight >= 2:
                started.set()
        await asyncio.sleep(0.12)
        async with lock:
            in_flight -= 1
            if in_flight == 0:
                finished.set()

    t0 = time.perf_counter()
    await router.enqueue("channel-a", "x", handler)
    await router.enqueue("channel-b", "y", handler)

    await asyncio.wait_for(started.wait(), timeout=1.0)
    await asyncio.wait_for(finished.wait(), timeout=1.0)
    elapsed = time.perf_counter() - t0

    await router.close()

    assert elapsed < 0.22


@pytest.mark.asyncio
async def test_queue_full_raises_error() -> None:
    router = ChannelQueueRouter(max_pending_per_channel=1)

    started = asyncio.Event()
    unblock = asyncio.Event()

    async def handler(_: str) -> None:
        started.set()
        await unblock.wait()

    await router.enqueue("channel-1", "a", handler)
    await started.wait()
    await router.enqueue("channel-1", "b", handler)
    with pytest.raises(RuntimeError, match="Channel queue is full"):
        await router.enqueue("channel-1", "c", handler)

    unblock.set()
    await router.close()

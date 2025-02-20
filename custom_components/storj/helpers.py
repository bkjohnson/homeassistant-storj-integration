"""Helpers for the integration"""

from typing import Self
from aiofiles.threadpool.binary import AsyncBufferedReader


class ChunkAsyncStreamIterator:  # pragma: no cover
    """Async iterator for chunked streams.

    Based on the same class from homeassistant but accepts a file object
    and reads using 2048 byte increments instead.
    """

    __slots__ = ("_stream",)

    def __init__(self, filestream: AsyncBufferedReader) -> None:
        """Initialize."""
        self._stream = filestream

    def __aiter__(self) -> Self:
        """Iterate."""
        return self

    async def __anext__(self) -> bytes:
        """Yield next chunk."""
        rv = await self._stream.read(2048)
        if rv == b"":
            raise StopAsyncIteration
        return rv

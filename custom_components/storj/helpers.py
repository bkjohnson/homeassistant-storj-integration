"""Helpers for the integration"""

from typing import Self


CHUNK_SZ = 1024


def create_chunks(b: bytes, sz: int):
    return [b[i * sz : (i + 1) * sz] for i in range(int(len(b) / sz) + 1)]


class ChunkAsyncStreamIterator:
    """Async iterator for chunked streams.

    Based on the same class from homeassistant but accepts a string of bytes
    and iterates over them in chunks.
    """

    __slots__ = ("_stream", "chunks")

    def __init__(self, filestream: bytes) -> None:
        """Initialize."""
        self._stream = filestream
        self.chunks = create_chunks(filestream, CHUNK_SZ)

    def __aiter__(self) -> Self:
        """Iterate."""
        return self

    async def __anext__(self) -> bytes:
        """Yield next chunk."""
        if len(self.chunks) == 0:
            raise StopAsyncIteration

        return self.chunks.pop(0)

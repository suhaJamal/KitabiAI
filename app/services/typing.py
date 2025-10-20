"""
Shared lightweight typing aliases.

- Provides BytesLike (bytes/bytearray/memoryview) to keep service signatures clear.
- Avoids heavy deps just for typing.
"""

# tiny helper to keep typing clear without importing numpy/pandas types
from typing import Union

BytesLike = Union[bytes, bytearray, memoryview]

from contextlib import AbstractAsyncContextManager
from typing import Protocol


class ModelLease(Protocol):
    def __call__(self) -> AbstractAsyncContextManager[None]: ...

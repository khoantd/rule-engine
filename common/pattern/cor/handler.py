from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Optional


class Handler(ABC):
    """
    The Handler interface declares a method for building the chain of handlers.
    It also declares a method for executing a request.
    """

    def __init__(self, data) -> Optional[str]:
        pass

    @abstractmethod
    def set_next(self, handler: Handler) -> Handler:
        pass

    @abstractmethod
    def handle(self, request, data) -> Optional[str]:
        pass


class AbstractHandler(Handler):
    """
    The default chaining behavior can be implemented inside a base handler
    class.
    """
    _next_handler: Handler = None
    # _next_data: dict = {}
    _stage: str = ''

    def set_next(self, handler: Handler) -> Handler:
        self._next_handler = handler

        # Returning a handler from here will let us link handlers in a
        # convenient way like this:
        # monkey.set_next(squirrel).set_next(dog)
        # if isinstance(handler, None):
        #     return handler.handle(handler, data)
        return handler

    @abstractmethod
    def handle(self, process_name: str = 'default', request: Any = Optional, data: Any = Optional) -> str:
        # print("request:", request)
        # print("data:", data)
        # self._next_data = data
        if isinstance(self._next_handler, Handler):
            # self._next_data = data
            # print(self._next_handler)
            return self._next_handler.handle(process_name, request, data)
        else:
            return None

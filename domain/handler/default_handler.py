from dataclasses import dataclass
from typing import Any, Optional

from common.pattern.cor.handler import AbstractHandler


@dataclass
class DefaultHandler(AbstractHandler):
    def handle(self, process_name: str = 'default', request: Any = Optional, data: Any = Optional) -> str:
        # print("class name:", DefaultHandler.__class__)
        # print("data:", data)
        if request == self._stage:
            # request = 'NEW'
            return {
                "step": request,
                "data": data,
                "histories": []
            }
        else:
            return super().handle(process_name, request, data)

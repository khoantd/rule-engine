from dataclasses import dataclass
from typing import Any, Optional


from common.pattern.cor.handler import AbstractHandler


@dataclass
class InprogressCaseHandler(AbstractHandler):
    _stage = 'INPROGESS'

    def handle(self, process_name: str = 'default', request: Any = Optional, data: Any = Optional) -> str:
        # signal = request.signal
        # self._data = data
        # print('received:', request)
        # print('received:', data)
        if request == self._stage:
            # print(request)
            # print(data)
            # data['id'] = 1
            # data['name'] = "Hari"
            data['address'] = 'Ho Chi Minh'
            # request = 'INPROGESS'
            # print(data.keys())
            if 'histories' not in list(data.keys()):
                data['histories'] = [{"from": "",
                                     "to": request}]
            else:
                length = len(data['histories'])
                # print(length)
                id = int(data['histories'][length-1]["id"])+1
                data['histories'].append({
                    "id": id,
                    "from": data['histories'][length-1]["to"],
                    "to": request})
            return {
                "process_name": process_name,
                "step": request,
                "data": data
            }
        else:
            return super().handle(process_name, request, data)

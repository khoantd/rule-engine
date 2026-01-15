from dataclasses import dataclass
from typing import Any, Optional

from common.pattern.cor.handler import AbstractHandler
from common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class NewCaseHandler(AbstractHandler):
    _stage = 'NEW'

    def handle(self, process_name: str = 'default', request: Any = Optional, data: Any = Optional) -> str:
        logger.debug("NewCaseHandler processing request", process_name=process_name, 
                    request=request, stage=self._stage)
        if request == self._stage:
            logger.info("Processing NEW case", process_name=process_name)
            # request = 'NEW'
            data['id'] = 1
            data['name'] = 'Khoa'
            data['dob'] = '07/02/1986'
            logger.debug("Setting initial data fields", data_keys=list(data.keys()) if isinstance(data, dict) else [])
            # print(list(data.keys()))
            if 'histories' not in list(data.keys()):
                logger.debug("Creating initial history entry", process_name=process_name)
                data['histories'] = [{"id": 1,
                                      "from": "",
                                     "to": request}]
            else:
                logger.debug("Appending to existing history", process_name=process_name, 
                           history_count=len(data['histories']))
                history_length = len(data['histories'])
                last_history_entry = data['histories'][history_length-1]
                # Convert id to int with error handling
                try:
                    next_id = int(last_history_entry["id"]) + 1
                except (ValueError, TypeError, KeyError) as conversion_error:
                    logger.warning("Failed to convert history id to int, using default",
                                 error=str(conversion_error), last_id=last_history_entry.get("id"))
                    next_id = history_length + 1
                
                data['histories'].append({
                    "id": next_id,
                    "from": last_history_entry["to"],
                    "to": request})
            result = {
                "process_name": process_name,
                "step": request,
                "data": data
            }
            logger.info("NEW case handled successfully", process_name=process_name, 
                       data_keys=list(data.keys()) if isinstance(data, dict) else [])
            return result
        else:
            logger.debug("Request does not match NEW stage, delegating to next handler", 
                        process_name=process_name, request=request, stage=self._stage)
            # print(super())
            return super().handle(process_name, request, data)

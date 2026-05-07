from __future__ import annotations

import json

import websockets

from edgepulse.core.models import PerceptionEvent


class EdgePulseEventClient:
    def __init__(self, url: str) -> None:
        self.url = url

    async def send(self, event: PerceptionEvent) -> None:
        async with websockets.connect(self.url, ping_interval=20) as ws:
            await ws.send(json.dumps(event.to_dict()))

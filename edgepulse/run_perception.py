from __future__ import annotations

import asyncio
import os

import httpx

from edgepulse.perception.mediapipe_mac import MediaPipePerception


async def main() -> None:
    api_url = os.getenv("EDGEPULSE_API_URL", "http://127.0.0.1:8501")
    perception = MediaPipePerception(camera_index=int(os.getenv("EDGEPULSE_CAMERA_INDEX", "0")))
    async with httpx.AsyncClient(timeout=1.0) as client:
        for event, _frame in perception.events():
            await client.post(f"{api_url}/events", json=event.to_dict())
            await asyncio.sleep(0.08)


if __name__ == "__main__":
    asyncio.run(main())

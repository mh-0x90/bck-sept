import asyncio

import httpx


class AvailabilityClient:
    def __init__(self) -> None:
        self.timeout = 0.35
        self.retry_delays = (0.12, 0.18)

    async def is_available(self, url: str) -> bool:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(3):
                try:
                    response = await client.get(url)
                    if response.status_code < 500:
                        return True
                except httpx.HTTPError:
                    pass

                if attempt < len(self.retry_delays):
                    await asyncio.sleep(self.retry_delays[attempt])

        return False

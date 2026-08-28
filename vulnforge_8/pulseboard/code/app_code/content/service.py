from app_code.content.filters import normalise_filter, normalise_id_filter
from app_code.content.matcher import filter_by_partial_id
from app_code.content.models import RefreshResult
from app_code.content.sorting import sort_candidates
from app_code.network.client import AvailabilityClient
from app_code.storage.repository import IntegrationRepository


class IntegrationHealthService:
    def __init__(self) -> None:
        self.repository = IntegrationRepository()
        self.availability = AvailabilityClient()

    async def refresh(self, raw_filter, raw_id_filter: str) -> RefreshResult:
        rule = normalise_filter(raw_filter)
        id_filter = normalise_id_filter(raw_id_filter)

        candidates = sort_candidates(self.repository.find(rule))

        available = []
        for item in candidates:
            if await self.availability.is_available(item.health_url):
                available.append(item)

        matched = filter_by_partial_id(available, id_filter)
        return RefreshResult(
            candidates=len(candidates),
            available=len(available),
            matched=len(matched),
        )

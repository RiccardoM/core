"""Define an client to interact with IdealService Waste."""
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from aiohttp import ClientSession, ClientTimeout
from aiohttp.client_exceptions import ClientError
from aiorecollect.errors import DataError, RequestError

from .const import LOGGER

API_URL_LIST = "http://idealservice.infofactory.it/it/api/lista-comuni"
API_URL_CALENDAR = "http://idealservice.infofactory.it/it/api/comune/{0}/calendario/{1}"

DEFAULT_TIMEOUT = 10


@dataclass(frozen=True)
class PickupType:
    """Define a waste pickup type."""

    icon: str
    title: str
    description: str


@dataclass(frozen=True)
class PickupEvent:
    """Define a waste pickup event."""

    date: date
    pickup_types: List[PickupType]


class Client:
    """Define a client to interact with the IdealService APIs."""

    def __init__(
        self, place_id: int, calendar_id: int, *, session: ClientSession = None
    ) -> None:
        """Initialize."""
        self._api_url = API_URL_CALENDAR.format(place_id, calendar_id)
        self._session = session
        self.place_id = place_id
        self.calendar_id = calendar_id

    async def _async_request(self, method: str, url: str, **kwargs) -> dict:
        """Make an API request."""
        use_running_session = self._session and not self._session.closed

        session: ClientSession
        if use_running_session:
            session = self._session
        else:
            session = ClientSession(timeout=ClientTimeout(total=DEFAULT_TIMEOUT))

        try:
            async with session.request(method, url, **kwargs) as resp:
                data = await resp.json()
                resp.raise_for_status()
        except ClientError as err:
            LOGGER.debug("Data received for %s: %s", url, data)
            raise RequestError(err) from None
        finally:
            if not use_running_session:
                await session.close()

        return data

    async def _async_get_pickup_data(
        self, *, days: Optional[int] = None, offset: Optional[int] = None
    ) -> dict:
        """Get pickup data (with an optional days span and/or offset number of days)."""
        url = self._api_url
        if days and offset:
            url += f"?days={days}&offset={offset}"

        return await self._async_request("get", url)

    async def async_get_pickup_events(
        self, *, days: Optional[int] = None, offset: Optional[int] = None
    ) -> List[PickupEvent]:
        """Get all pickup events based on the given days and offset."""
        pickup_data = await self._async_get_pickup_data(days=days, offset=offset)
        pickup_types_legends = pickup_data["legenda"]

        events = []
        for month in pickup_data["calendario"]:
            for day in month["events"]:
                if not day["events"]:
                    continue

                pickup_types = []
                for pickup in day["events"]:
                    # Get the pickup legend data
                    legend_id = pickup["legenda"]
                    pickup_flag_legend = pickup_types_legends[str(legend_id)]
                    pickup_types.append(
                        PickupType(
                            pickup_flag_legend["icona"],
                            pickup_flag_legend["titolo"],
                            pickup_flag_legend["occhiello"],
                        )
                    )

                events.append(
                    PickupEvent(date.fromisoformat(day["date"]), pickup_types)
                )

        return events

    async def async_get_next_pickup_event(self) -> PickupEvent:
        """Get the very next pickup event."""
        pickup_events = await self.async_get_pickup_events()
        for event in pickup_events:
            if event.date >= date.today():
                return event
        raise DataError("No pickup events found after today")

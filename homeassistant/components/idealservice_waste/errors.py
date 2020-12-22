"""Define library exception types."""


class IdealServiceError(Exception):
    """Define a base ReCollect Waste exception."""

    pass


class PlaceError(IdealServiceError):
    """Define a exception related to the zone."""

    pass


class CalendarError(IdealServiceError):
    """Define an exception related to the calendar."""

    pass


class RequestError(IdealServiceError):
    """Define a exception related to HTTP request errors."""

    pass


class DataError(IdealServiceError):
    """Define an exception related to invalid/missing data."""

    pass

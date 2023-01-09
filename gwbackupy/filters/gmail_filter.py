from datetime import datetime, timezone
from typing import Union

import tzlocal

from gwbackupy.filters.filter_interface import FilterInterface
from gwbackupy.storage.storage_interface import LinkInterface


class GmailFilter(FilterInterface):
    def __init__(self):
        super().__init__()
        self.__date_from: Union[datetime, None] = None
        self.__date_to: Union[datetime, None] = None
        self.__is_deleted: bool = False
        self.__is_missing: bool = False

    def date_to(self, dt: datetime):
        self.__date_to = dt.astimezone(timezone.utc)

    def date_from(self, dt: datetime):
        self.__date_from = dt.astimezone(timezone.utc)

    def is_deleted(self):
        self.__is_deleted = True

    def is_missing(self):
        self.__is_missing = True

    def match(self, d: any) -> bool:
        d: dict[str, any]
        link: LinkInterface = d["link"]
        if link.is_object():
            return True

        if self.__date_to is not None:
            ts1 = self.__date_to.timestamp()
            ts2 = int(link.mutation()) / 1000.0
            if ts2 >= ts1:
                return False
        if self.__date_from is not None:
            ts1 = self.__date_from.timestamp()
            ts2 = int(link.mutation()) / 1000.0
            if ts2 < ts1:
                return False
        if not self.__is_deleted and not self.__is_missing:
            # no missing or deleted filter
            return True
        if self.__is_deleted and link.is_deleted():
            # deleted
            return True
        if self.__is_missing:
            ids_from_server: dict[str, any] = d["server-data"]
            if link.id() not in ids_from_server:
                # missing
                return True
        return False

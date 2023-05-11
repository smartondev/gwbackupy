from __future__ import annotations

from datetime import datetime, timezone
from typing import Union

from gwbackupy.filters.filter_interface import FilterInterface
from gwbackupy.storage.storage_interface import LinkInterface


class GmailFilter(FilterInterface):
    def __init__(self):
        super().__init__()
        self.__date_from: Union[datetime, None] = None
        self.__date_to: Union[datetime, None] = None
        self.__is_deleted: bool = False
        self.__is_missing: bool = False

    def with_date_to(self, dt: datetime | None):
        if dt is None:
            self.__date_to = None
            return
        self.__date_to = dt.astimezone(timezone.utc)

    def with_date_from(self, dt: datetime | None):
        if dt is None:
            self.__date_to = None
            return
        self.__date_from = dt.astimezone(timezone.utc)

    def with_match_deleted(self, match_deleted: bool = True):
        self.__is_deleted = match_deleted

    def is_match_deleted(self) -> bool:
        return self.__is_deleted

    def with_match_missing(self, match_missing: bool = True):
        self.__is_missing = match_missing

    def is_match_missing(self) -> bool:
        return self.__is_missing

    def match(self, d: any) -> bool:
        d: dict[str, any]
        """
        :param d: data dict with keys: "link", "server-data", "message-id"
        """
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
        if link.is_deleted():
            return self.is_match_deleted()
        if not self.is_match_missing():
            return True
        ids_from_server: dict[str, any] = d["server-data"]
        return self.is_match_missing() and link.id() not in ids_from_server

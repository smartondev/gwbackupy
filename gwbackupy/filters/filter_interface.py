from __future__ import annotations

from datetime import datetime
from builtins import bool

import tzlocal


class FilterInterface:
    def __init__(self):
        pass

    def with_date_from(self, dt: datetime | None):
        pass

    def with_date_to(self, dt: datetime | None):
        pass

    def with_match_deleted(self):
        pass

    def is_match_deleted(self) -> bool:
        pass

    def match(self, d: any) -> bool:
        pass

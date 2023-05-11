from datetime import datetime
from builtins import bool

import tzlocal


class FilterInterface:
    def __init__(self):
        pass

    def date_from(self, dt: datetime):
        pass

    def date_to(self, dt: datetime):
        pass

    def with_match_deleted(self):
        pass

    def is_match_deleted(self) -> bool:
        pass

    def match(self, d: any) -> bool:
        pass

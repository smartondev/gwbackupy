from __future__ import annotations


class PeopleServiceWrapperInterface:
    def get_peoples(self, email: str) -> dict[str, [dict[str, any]]]:
        pass

    def get_people(self, email: str, contact_id: str) -> [dict[str, any]]:
        pass

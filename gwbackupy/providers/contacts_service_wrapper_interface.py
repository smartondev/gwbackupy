from __future__ import annotations


class ContactsServiceWrapperInterface:
    def get_contacts(self, email: str) -> dict[str, [dict[str, any]]]:
        pass

    def get_contact(self, email: str, contact_id: str) -> [dict[str, any]]:
        pass

    def get_contact_main_photo(self, email: str, contact_id: str) -> bytes:
        pass

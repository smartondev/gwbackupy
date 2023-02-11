from __future__ import annotations

from gwbackupy.providers.contacts_service_provider import ContactsServiceProvider
from gwbackupy.providers.contacts_service_wrapper_interface import (
    ContactsServiceWrapperInterface,
)


class GapiContactsServiceWrapper(ContactsServiceWrapperInterface):
    def __init__(
        self,
        service_provider: ContactsServiceProvider,
        try_count: int = 5,
        try_sleep: int = 10,
        dry_mode: bool = False,
    ):
        self.try_count = try_count
        self.try_sleep = try_sleep
        self.service_provider = service_provider
        self.dry_mode = dry_mode

    def get_service_provider(self) -> ContactsServiceProvider:
        return self.service_provider

    def get_contacts(self, email: str) -> dict[str, [dict[str, any]]]:
        with self.service_provider.get_service(email) as service:
            response = (
                service.people()
                .connections()
                .list(
                    resourceName="people/me",
                    pageSize=1500,
                    personFields="addresses,ageRange,biographies,birthdays,braggingRights,coverPhotos,emailAddresses,"
                    "events,genders,imClients,interests,locales,memberships,metadata,names,nicknames,"
                    "occupations,organizations,phoneNumbers,photos,relations,relationshipInterests,"
                    "relationshipStatuses,residences,skills,taglines,urls,userDefined",
                )
                .execute()
            )
            print(response)
            exit(1)

    def get_contact(self, email: str, contact_id: str) -> [dict[str, any]]:
        pass

    def get_contact_main_photo(self, email: str, contact_id: str) -> bytes:
        pass

from __future__ import annotations

import logging

from gwbackupy import global_properties
from gwbackupy.providers.people_service_provider import PeopleServiceProvider
from gwbackupy.providers.people_service_wrapper_interface import (
    PeopleServiceWrapperInterface,
)


class GapiPeopleServiceWrapper(PeopleServiceWrapperInterface):
    def __init__(
        self,
        service_provider: PeopleServiceProvider,
        try_count: int = 5,
        try_sleep: int = 10,
        dry_mode: bool = False,
    ):
        self.try_count = try_count
        self.try_sleep = try_sleep
        self.service_provider = service_provider
        self.dry_mode = dry_mode

    def get_service_provider(self) -> PeopleServiceProvider:
        return self.service_provider

    def get_peoples(self, email: str) -> dict[str, [dict[str, any]]]:
        with self.service_provider.get_service(email) as service:
            next_page_token = None
            page = 1
            items: dict[str, [dict[str, any]]] = dict()
            while True:
                logging.debug(f"Loading page {page}. from server...")
                data = (
                    service.people()
                    .connections()
                    .list(
                        resourceName="people/me",
                        pageSize=2000,
                        pageToken=next_page_token,
                        personFields="addresses,ageRange,biographies,birthdays,braggingRights,coverPhotos,"
                        "events,genders,imClients,interests,locales,memberships,metadata,names,nicknames,"
                        "emailAddresses,occupations,organizations,phoneNumbers,photos,relations,relationshipInterests,"
                        "relationshipStatuses,residences,skills,taglines,urls,userDefined",
                    )
                    .execute()
                )
                print(data)
                next_page_token = data.get("nextPageToken", None)
                page_message_count = len(data.get("connections", []))
                logging.debug(
                    f"Page {page} successfully loaded (connections count: {page_message_count} / next page token: {next_page_token})"
                )
                for item in data.get("connections", []):
                    items[item.get("resourceName")] = item
                if next_page_token is None:
                    break
                page += 1
            logging.log(global_properties.log_finest, f"Items: {items}")
            return items

    def get_people(self, email: str, contact_id: str) -> [dict[str, any]]:
        pass

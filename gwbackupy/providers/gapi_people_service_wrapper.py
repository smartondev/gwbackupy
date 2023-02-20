from __future__ import annotations

import logging

import requests

from gwbackupy import global_properties
from gwbackupy.providers.people_service_provider import PeopleServiceProvider
from gwbackupy.providers.people_service_wrapper_interface import (
    PeopleServiceWrapperInterface,
    PhotoDescriptor,
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

    def get_photo(self, email: str, people_id: str, uri: str) -> PhotoDescriptor:
        logging.debug(f"{people_id} downloading photo: {uri}")
        r = requests.get(uri, stream=True)
        if r.status_code != 200:
            raise Exception(
                f"photo download failed, status code: {r.status_code} ({uri})"
            )
        for header in r.headers:
            logging.log(global_properties.log_finest, f"{header}: {r.headers[header]}")
        photo_bytes = b""
        for chunk in r.iter_content(chunk_size=1024):
            photo_bytes += chunk
        return PhotoDescriptor(
            uri=uri,
            data=photo_bytes,
            mime_type=r.headers.get("content-type", "image/unknown"),
        )

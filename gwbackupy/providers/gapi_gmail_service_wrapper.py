from __future__ import annotations

import logging

from googleapiclient.errors import HttpError

from gwbackupy.helpers import is_rate_limit_exceeded, random_string
from gwbackupy.process_helpers import sleep_kc
from gwbackupy.providers.gmail_service_provider import GmailServiceProvider
from gwbackupy.providers.gmail_service_wrapper_interface import (
    GmailServiceWrapperInterface,
)


class GapiGmailServiceWrapper(GmailServiceWrapperInterface):
    def __init__(
        self,
        service_provider: GmailServiceProvider,
        try_count: int = 5,
        try_sleep: int = 10,
        dry_mode: bool = False,
    ):
        self.try_count = try_count
        self.try_sleep = try_sleep
        self.service_provider = service_provider
        self.dry_mode = dry_mode

    def get_service_provider(self) -> GmailServiceProvider:
        return self.service_provider

    def get_labels(self, email: str) -> list[dict[str, any]]:
        with self.service_provider.get_service(email) as service:
            response = service.users().labels().list(userId="me").execute()
            return response.get("labels", [])

    def get_messages(self, email: str, q: str) -> dict[str, dict[str, any]]:
        with self.service_provider.get_service(email) as service:
            messages = {}
            count = 0
            next_page_token = None
            page = 1
            while True:
                logging.debug(f"Loading page {page}. from server...")
                data = (
                    service.users()
                    .messages()
                    .list(userId="me", pageToken=next_page_token, maxResults=10000, q=q)
                    .execute()
                )
                next_page_token = data.get("nextPageToken", None)
                page_message_count = len(data.get("messages", []))
                logging.debug(
                    f"Page {page} successfully loaded (messages count: {page_message_count} / next page token: {next_page_token})"
                )
                # print(data)
                # exit(-1)
                count = count + page_message_count
                for message in data.get("messages", []):
                    messages[message.get("id")] = message
                page += 1
                if data.get("nextPageToken") is None:
                    break
            return messages

    def get_message(
        self, email: str, message_id: str, message_format: str = "minimal"
    ) -> dict[str, any] | None:
        for i in range(self.try_count):
            try:
                with self.service_provider.get_service(email) as service:
                    result = (
                        service.users()
                        .messages()
                        .get(userId="me", id=message_id, format=message_format)
                        .execute()
                    )
                    return result
            except HttpError as e:
                if e.status_code == 404:
                    # message not found
                    return None
                if i == self.try_count - 1:
                    # last try
                    logging.exception(f"{message_id} message download failed: {e}")
                    raise e
                if is_rate_limit_exceeded(e):
                    logging.warning(
                        f"{message_id} rate limit exceeded, sleeping for {self.try_sleep} seconds"
                    )
                    sleep_kc(self.try_sleep)
                else:
                    raise e
            except TimeoutError as e:
                if i == self.try_count - 1:
                    # last try
                    logging.exception(f"{message_id} message download failed: {e}")
                    raise e

    def create_label(
        self, email: str, name: str, get_if_already_exists: bool = False
    ) -> dict[str, any]:
        if self.dry_mode:
            return {
                "name": name,
                "id": f"DRYMODE{random_string()}",
                "type": "user",
            }
        for i in range(self.try_count):
            try:
                with self.service_provider.get_service(email) as service:
                    result = (
                        service.users()
                        .labels()
                        .create(userId="me", body={"name": name})
                        .execute()
                    )
                    return result
            except HttpError as e:
                if e.status_code == 409:
                    # already exists
                    logging.debug(f"label ({name}) already exists")
                elif i == self.try_count - 1:
                    # last try
                    logging.exception(f"Label ({name}) create fail: {e}")
                    raise e
                elif is_rate_limit_exceeded(e):
                    logging.warning(
                        f"Label ({name}) create rate limit exceeded, sleeping for {self.try_sleep} seconds"
                    )
                    sleep_kc(self.try_sleep)
                else:
                    logging.warning(f"Next attempt to create label ({name})")
            except TimeoutError as e:
                if i == self.try_count - 1:
                    # last try
                    logging.exception(f"Label ({name}) create fail: {e}")
                    raise e

            if not get_if_already_exists:
                return {
                    "name": name,
                    "type": "user",
                }
            labels = self.get_labels(email)
            for label in labels:
                if label.get("name") == name:
                    return label
            raise Exception(f"Label ({name}) is already exists but cannot found it")

    def insert_message(self, email: str, data: dict[str, any]) -> dict[str, any]:
        if self.dry_mode:
            return {"id": f"DRYMODE{random_string()}"}

        for i in range(self.try_count):
            try:
                with self.service_provider.get_service(email) as service:
                    result = (
                        service.users()
                        .messages()
                        .insert(
                            userId="me",
                            internalDateSource="dateHeader",
                            body=data,
                        )
                        .execute()
                    )
                    return result
            except HttpError as e:
                if i == self.try_count - 1:
                    # last try
                    logging.exception(f"Message insert fail: {e}")
                    raise e
                elif is_rate_limit_exceeded(e):
                    logging.warning(
                        f"Message insert rate limit exceeded, sleeping for {self.try_sleep} seconds"
                    )
                    sleep_kc(self.try_sleep)
                else:
                    logging.warning(f"Next attempt to insert message")

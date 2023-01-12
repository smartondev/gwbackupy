from __future__ import annotations

import logging
import time

from googleapiclient.errors import HttpError

from gwbackupy.helpers import is_rate_limit_exceeded
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
    ):
        self.try_count = try_count
        self.try_sleep = try_sleep
        self.service_provider = service_provider

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
                    logging.exception(f"{message_id} message download failed")
                    raise e
                if is_rate_limit_exceeded(e):
                    logging.warning(
                        f"{message_id} rate limit exceeded, sleeping for {self.try_sleep} seconds"
                    )
                    time.sleep(self.try_sleep)
                else:
                    raise e

    def create_label(self, email: str, name: str) -> dict[str, any]:
        pass

    def insert_message(self, email: str, data: dict[str, any]) -> str:
        pass

from __future__ import annotations

import logging
import random
import string

from gwbackupy.providers.gmail_service_wrapper_interface import (
    GmailServiceWrapperInterface,
)
from gwbackupy.tests.test_mock_service_provider import MockServiceProvider


class MockGmailServiceWrapper(GmailServiceWrapperInterface):
    def __init__(self):
        self.__service_provider = MockServiceProvider()

    def get_service_provider(self) -> MockServiceProvider:
        return self.__service_provider

    def get_messages(self, email: str, q: str) -> list[dict[str, any]]:
        logging.debug(f"Get all messages: {q}")
        return list()

    def get_message(
        self, email: str, message_id: str, message_format: str = "minimal"
    ) -> dict[str, any] | None:
        logging.debug(f"Get a message by ID={message_id}")
        return None

    def get_labels(self, email: str) -> list[dict[str, any]]:
        logging.debug("Get lables")
        return list()

    def create_label(self, email: str, name: str) -> dict[str, any]:
        logging.debug(f"Create label: {name}")
        return dict()

    def insert_message(self, email: str, data: dict[str, any]) -> str:
        message_id = "".join(random.choice(string.ascii_lowercase) for i in range(16))
        logging.debug(f"Insert a message with ID:{message_id}")
        return message_id

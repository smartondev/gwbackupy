from __future__ import annotations

import logging
import uuid

from gwbackupy.helpers import random_string
from gwbackupy.providers.gmail_service_wrapper_interface import (
    GmailServiceWrapperInterface,
)
from gwbackupy.tests.mock_service_provider import MockServiceProvider


class MockGmailServiceWrapper(GmailServiceWrapperInterface):
    def __init__(self):
        self.__service_provider = MockServiceProvider()
        self.__messages: dict[str, dict[str, dict[str, any]]] = {}
        self.__labels: dict[str, list[dict[str, any]]] = {}
        self.throw_if_label_already_created = True

    def get_service_provider(self) -> MockServiceProvider:
        return self.__service_provider

    def get_messages(self, email: str, q: str) -> dict[str, dict[str, any]]:
        logging.debug(f"Get all messages: {q}")
        return self.__messages.get(email, {})

    def get_message(
        self, email: str, message_id: str, message_format: str = "minimal"
    ) -> dict[str, any] | None:
        logging.debug(f"Get a message by ID={message_id}")
        if email in self.__messages:
            if message_id in self.__messages[email]:
                return self.__messages[email][message_id]
        return None

    def get_labels(self, email: str) -> list[dict[str, any]]:
        logging.debug("Get labels")
        return self.__labels.get(email, [])

    def create_label(
        self, email: str, name: str, get_if_already_exists: bool = False
    ) -> dict[str, any]:
        logging.debug(f"Create label: {name}")
        labels = self.__labels.get(email, None)
        if labels is None:
            labels = []
            self.__labels[email] = labels

        for label in labels:
            if label.get("name") == name:
                if self.throw_if_label_already_created:
                    raise Exception(f"Label {name} already created")
                return label

        label = {
            "id": "Label_" + random_string(),
            "name": name,
            "type": "user",
        }
        self.__labels[email].append(label)
        return label

    def insert_message(self, email: str, data: dict[str, any]) -> dict[str, any]:
        message_id = random_string()
        logging.debug(f"Insert a message with ID:{message_id}")
        if email not in self.__messages:
            self.__messages[email] = {}
        result = {"id": message_id}
        result.update(data)
        self.__messages[email][message_id] = result
        return result

    def inject_message(self, email: str, data):
        if email not in self.__messages:
            self.__messages[email] = {}
        self.__messages[email][data.get("id")] = data

    def inject_messages_clear(self):
        self.__messages.clear()

    def inject_label(
        self,
        email: str,
        name: str,
        label_id: str = "Label_" + random_string(),
        label_type: str = "user",
    ):
        label = {
            "id": label_id,
            "name": name,
            "type": label_type,
        }
        if email not in self.__labels:
            self.__labels[email] = []
        self.__labels[email].append(label)

    def inject_labels_clear(self):
        self.__labels.clear()

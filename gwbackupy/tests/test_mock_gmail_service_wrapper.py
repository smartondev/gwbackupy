from __future__ import annotations

from gwbackupy.providers.gmail_service_wrapper_interface import (
    GmailServiceWrapperInterface,
)
from gwbackupy.providers.service_provider_interface import ServiceProviderInterface
from gwbackupy.tests.test_mock_service_provider import MockServiceProvider


class MockGmailServiceWrapper(GmailServiceWrapperInterface):
    def __init__(self):
        self.__service_provider = MockServiceProvider()

    def get_service_provider(self) -> MockServiceProvider:
        return self.__service_provider

    def get_messages(self, email: str, q: str) -> list[dict[str, any]]:
        return list()

    def get_message(
        self, email: str, message_id: str, message_format: str = "minimal"
    ) -> dict[str, any] | None:
        return None

    def get_labels(self, email: str) -> list[dict[str, any]]:
        return list()

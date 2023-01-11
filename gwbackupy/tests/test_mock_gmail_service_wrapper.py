from __future__ import annotations

from gwbackupy.providers.gmail_service_wrapper_interface import (
    GmailServiceWrapperInterface,
)


class MockGmailServiceWrapper(GmailServiceWrapperInterface):
    def get_messages(self, service, q: str) -> list[dict[str, any]]:
        return list()

    def get_message(
        self, service, message_id: str, message_format: str = "minimal"
    ) -> dict[str, any] | None:
        return None

    def get_labels(self, service) -> list[dict[str, any]]:
        return list()

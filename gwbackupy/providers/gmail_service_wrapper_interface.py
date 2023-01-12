from __future__ import annotations

from gwbackupy.providers.service_provider_interface import ServiceProviderInterface


class GmailServiceWrapperInterface:
    def get_messages(self, email: str, q: str) -> dict[str, [dict[str, any]]]:
        """Return all messages that match with query"""
        pass

    def get_message(
        self, email: str, message_id: str, message_format: str = "minimal"
    ) -> dict[str, any] | None:
        """Get one message by message ID. If not exists then return None"""
        pass

    def get_labels(self, email: str) -> list[dict[str, any]]:
        """Return all labels"""
        pass

    def get_service_provider(self) -> ServiceProviderInterface:
        pass

    def create_label(
        self, email: str, name: str, get_if_already_exists: bool = False
    ) -> dict[str, any]:
        """Create a label if not existing, and return the label data"""
        pass

    def insert_message(self, email: str, data: dict[str, any]) -> dict[str, any]:
        """Insert a message to server with specified data, and return new message ID"""
        pass

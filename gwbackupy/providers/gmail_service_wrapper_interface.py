from __future__ import annotations

from typing import Any, Callable

from gwbackupy.providers.service_provider_interface import ServiceProviderInterface


class GmailServiceWrapperInterface:
    on_rate_limit_callback: Callable[[], None] | None = None

    def get_messages(self, email: str, q: str) -> dict[str, dict[str, Any]]:
        """Return all messages that match with query"""
        ...

    def get_message(
        self, email: str, message_id: str, message_format: str = "minimal"
    ) -> dict[str, Any] | None:
        """Get one message by message ID. If not exists then return None"""
        ...

    def get_labels(self, email: str) -> list[dict[str, Any]]:
        """Return all labels"""
        ...

    def get_service_provider(self) -> ServiceProviderInterface:
        ...

    def create_label(
        self, email: str, name: str, get_if_already_exists: bool = False
    ) -> dict[str, Any]:
        """Create a label if not existing, and return the label data"""
        ...

    def insert_message(self, email: str, data: dict[str, Any]) -> dict[str, Any]:
        """Insert a message to server with specified data, and return new message ID"""
        ...

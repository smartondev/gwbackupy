from __future__ import annotations

from gwbackupy.providers.service_provider_interface import ServiceProviderInterface


class GmailServiceWrapperInterface:
    def get_messages(self, email: str, q: str) -> list[dict[str, any]]:
        pass

    def get_message(
        self, email: str, message_id: str, message_format: str = "minimal"
    ) -> dict[str, any] | None:
        pass

    def get_labels(self, email: str) -> list[dict[str, any]]:
        pass

    def get_service_provider(self) -> ServiceProviderInterface:
        pass

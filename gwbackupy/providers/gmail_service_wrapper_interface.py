from __future__ import annotations


class GmailServiceWrapperInterface:
    def get_messages(self, service, q: str) -> list[dict[str, any]]:
        pass

    def get_message(
        self, service, message_id: str, message_format: str = "minimal"
    ) -> dict[str, any] | None:
        pass

    def get_labels(self, service) -> list[dict[str, any]]:
        pass

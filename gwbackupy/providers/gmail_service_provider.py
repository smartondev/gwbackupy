from __future__ import annotations

from gwbackupy.providers.gapi_service_provider import GapiServiceProvider
from gwbackupy.storage.storage_interface import StorageInterface


class GmailServiceProvider(GapiServiceProvider):
    """Gmail service provider from gmail/v1 API with full access scope"""

    def __init__(
        self,
        credentials_file_path: str | None = None,
        service_account_file_path: str | None = None,
        service_account_email: str | None = None,
        storage: StorageInterface | None = None,
    ):
        super().__init__(
            "gmail",
            "v1",
            ["https://mail.google.com/"],
            credentials_file_path=credentials_file_path,
            storage=storage,
            service_account_file_path=service_account_file_path,
            service_account_email=service_account_email,
        )

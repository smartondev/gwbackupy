from __future__ import annotations

from gwbackupy.storage.storage_interface import StorageInterface


class ServiceProviderInterface:
    def __init__(
        self,
        service_name: str,
        version: str,
        scopes: [str],
        credentials_file_path: str | None = None,
        service_account_file_path: str | None = None,
        service_account_email: str | None = None,
        storage: StorageInterface | None = None,
    ):
        self.credentials_file_path = credentials_file_path
        self.service_account_file_path = service_account_file_path
        self.service_account_email = service_account_email
        self.storage = storage
        self.scopes = scopes
        self.service_name = service_name
        self.version = version

    def get_service(self, email: str):
        pass

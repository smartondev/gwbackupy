from __future__ import annotations

from gwbackupy.storage.storage_interface import (
    LinkInterface,
    LinkList,
)


class ServiceProviderInterface:
    def __init__(
        self,
        service_name: str,
        version: str,
        scopes: [str],
    ):
        self.scopes = scopes
        self.service_name = service_name
        self.version = version

    def get_service(self, email: str):
        pass

    def set_storage_links(self, links: LinkList[LinkInterface]):
        pass

from __future__ import annotations

from gwbackupy.storage.storage_interface import (
    LinkInterface,
    LinkList,
)


class ServiceItem:
    def __init__(self, provider: ServiceProviderInterface, email: str, service):
        self.__provider = provider
        self.__service = service
        self.__email = email

    def __enter__(self):
        if self.__service is None:
            raise ValueError(f"Service is released ({self.__email})")
        return self.__service

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.__provider.release_service(self.__email, self.__service)
        finally:
            self.__service = None


class ServiceProviderInterface:
    def release_service(self, email: str, service):
        pass

    def get_service(self, email: str) -> ServiceItem:
        pass

    def set_storage_links(self, links: LinkList[LinkInterface]):
        pass

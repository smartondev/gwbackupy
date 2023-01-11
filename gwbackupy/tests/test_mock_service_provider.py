from gwbackupy.providers.service_provider_interface import (
    ServiceProviderInterface,
    ServiceItem,
)
from gwbackupy.storage.storage_interface import LinkList, LinkInterface


class MockServiceProvider(ServiceProviderInterface):
    def release_service(self, email: str, service):
        pass

    def get_service(self, email: str) -> ServiceItem:
        service = dict()
        return ServiceItem(provider=self, email=email, service=service)

    def set_storage_links(self, links: LinkList[LinkInterface]):
        pass

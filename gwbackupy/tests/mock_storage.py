from __future__ import annotations

from typing import IO

from gwbackupy.storage.storage_interface import (
    StorageInterface,
    LinkInterface,
    Data,
    LinkList,
    LinkFilter,
)


class MockLink(LinkInterface):
    def __init__(self):
        self.__id: str | None = None
        self.__properties: dict[str, any] = {}

    def fill(self, data: dict[str, any]):
        if "id" in data:
            self.__id = data["id"]

    def mutation(self) -> str:
        return self.get_property(LinkInterface.property_mutation)

    def id(self) -> str:
        return self.__id

    def get_properties(self) -> dict[str, any]:
        return self.__properties

    def get_property(self, name: str, default: any = None) -> any:
        if name in self.__properties:
            return self.__properties[name]
        return default

    def has_property(self, name: str) -> bool:
        if self.get_properties().get(name, None) is not None:
            return True
        return False

    def set_properties(self, sets: dict[str, any], replace: bool = False) -> FileLink:
        if replace:
            self.__properties = sets
            return self
        for k, v in sets.items():
            self.__properties[k] = v
        return self

    def is_deleted(self) -> bool:
        return self.has_property(LinkInterface.property_deleted) is True

    def is_metadata(self) -> bool:
        return self.has_property(LinkInterface.property_metadata) is True

    def is_object(self) -> bool:
        return self.has_property(LinkInterface.property_object) is True

    def __repr__(self) -> str:
        return f"{self.__class__}#id:{self.id()},props:{self.__properties}"

    def __eq__(self, other):
        if not isinstance(other, MockLink):
            return False
        if self.id() != other.id():
            return False
        if self.get_properties() != other.get_properties():
            return False
        return True


class MockStorage(StorageInterface):
    def new_link(
        self,
        object_id: str,
        extension: str,
        created_timestamp: int | float | None = None,
    ) -> MockLink:
        link = MockLink()
        data = {"id": object_id}
        link.fill(data)
        return link

    def get(self, link: MockLink) -> IO[bytes]:
        pass

    def put(self, link: MockLink, data: Data) -> bool:
        return True

    def remove(self, link: MockLink, as_new_mutation: bool = True) -> bool:
        return False

    def find(self, f: LinkFilter | None = None) -> LinkList[MockLink]:
        return LinkList(list())

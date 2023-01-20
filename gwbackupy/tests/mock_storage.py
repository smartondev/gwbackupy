from __future__ import annotations

import hashlib
import io
from datetime import datetime
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
        if "mutation" in data:
            self.__properties[LinkInterface.property_mutation] = data["mutation"]

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
    def __init__(self):
        self.__objects = []

    def new_link(
        self,
        object_id: str,
        extension: str,
        created_timestamp: int | float | None = None,
    ) -> MockLink:
        link = MockLink()
        data = {"id": object_id, "mutation": MockStorage.__gen_mutation()}
        link.fill(data)
        return link

    def get(self, link: MockLink) -> IO[bytes]:
        for d in self.__objects:
            if link == d.get("link"):
                stream = io.BytesIO()
                stream.write(d.get("data"))
                stream.seek(0)
                return stream
        raise Exception("Link not found")

    def put(self, link: MockLink, data: Data) -> bool:
        self.__objects.append(
            {
                "link": link,
                "data": MockStorage.data2bytes(data),
            }
        )
        return True

    def remove(self, link: MockLink, as_new_mutation: bool = True) -> bool:
        return False

    def find(self, f: LinkFilter | None = None) -> LinkList[MockLink]:
        links = []
        for d in self.__objects:
            links.append(d.get("link"))
        return LinkList(links)

    def modify(self, link: MockLink, to_link: MockLink) -> bool:
        for d in self.__objects:
            if d.get("link") == link:
                d.put("link", to_link)
                return True
        return False

    def content_hash_add(self, link: LinkInterface) -> LinkInterface:
        pass

    def content_hash_check(self, link: LinkInterface) -> bool | None:
        pass

    def content_hash_generate(self, data: IO[bytes] | bytes | str) -> str:
        return hashlib.sha1(self.data2bytes(data)).hexdigest().lower()

    def content_hash_eq(
        self, link: LinkInterface, data: IO[bytes] | bytes | str
    ) -> bool:
        pass

    def inject_get_objects(self) -> list[dict[str, any]]:
        return self.__objects

    def inject_clear_objects(self):
        return self.__objects.clear()

    @staticmethod
    def data2bytes(data: Data) -> bytes:
        if isinstance(data, bytes):
            return data
        elif isinstance(data, str):
            return bytes(data, "utf-8")
        elif isinstance(data, io.BufferedReader):
            return data.read()
        elif callable(data):
            stream = io.BytesIO()
            data(stream)
            stream.seek(0)
            return stream.read()
        else:
            raise RuntimeError(f"Not supported data type: {type(data)}")

    @staticmethod
    def __gen_mutation():
        return str(int(datetime.utcnow().timestamp() * 1000))

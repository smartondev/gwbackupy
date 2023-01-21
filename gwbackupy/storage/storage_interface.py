from __future__ import annotations

from typing import Callable, IO, Union

Path = str
DataCall = Callable[[IO[bytes]], None]
Data = Union[str, bytes, DataCall, IO]


class LinkInterface:
    """
    This interface represents a link to an storage item.
    """

    property_deleted = "deleted"
    property_metadata = "metadata"
    property_object = "object"
    property_mutation = "mutation"
    property_content_hash = "ch"
    id_special_prefix = "--gwbackupy-"

    def id(self) -> str:
        raise NotImplementedError("LinkInterface#id")

    def is_special_id(self) -> bool:
        return self.id().startswith(LinkInterface.id_special_prefix)

    def get_properties(self) -> dict[str, any]:
        raise NotImplementedError("LinkInterface#get_properties")

    def set_properties(
        self, sets: dict[str, any], replace: bool = False
    ) -> LinkInterface:
        raise NotImplementedError("LinkInterface#set_properties")

    def get_property(self, name: str, default: any = None) -> any:
        raise NotImplementedError("LinkInterface#get_property")

    def has_property(self, name: str) -> bool:
        raise NotImplementedError("LinkInterface#has_property")

    def mutation(self) -> str:
        raise NotImplementedError("LinkInterface#mutation")

    def is_deleted(self) -> bool:
        raise NotImplementedError("LinkInterface#is_deleted")

    def is_metadata(self) -> bool:
        raise NotImplementedError("LinkInterface#is_metadata")

    def is_object(self) -> bool:
        raise NotImplementedError("LinkInterface#is_object")


LinkFilter = Callable[[LinkInterface], bool]
LinkGroupBy = Callable[[LinkInterface], list]


class LinkList(list):
    """
    List of links. The list is allows to group and filter.
    """

    def __init__(self, iterable=None):
        if iterable is None:
            iterable = []
        super().__init__(item for item in iterable)

    def __setitem__(self, index, item):
        LinkList.__item_is_link_interface(item)
        super().__setitem__(index, item)

    @staticmethod
    def __item_is_link_interface(item) -> True:
        if isinstance(item, LinkInterface):
            return True
        raise ValueError("item must be a LinkInterface")

    def insert(self, index, item):
        LinkList.__item_is_link_interface(item)
        super().insert(index, item)

    def append(self, item):
        LinkList.__item_is_link_interface(item)
        super().append(item)

    def extend(self, other):
        if isinstance(other, type(self)):
            super().extend(other)
        else:
            super().extend(item for item in other)

    def find(
        self, f: LinkFilter | None, g: LinkGroupBy | None = None
    ) -> LinkInterface | dict[str, any] | None:
        """Find in links. If there are multiple results for a key, the most recent mutation is selected."""
        result = {}
        use_group_by = g is not None
        found = 0
        for link in self:
            link: LinkInterface
            if f is not None and not f(link):
                continue
            found += 1
            if use_group_by:
                gks = g(link)
            else:
                gks = [""]
            local_result = result
            for i in range(len(gks)):
                if i == len(gks) - 1:
                    break
                gk = gks[i]
                if gk not in local_result:
                    local_result[gk] = {}
                local_result = local_result[gk]
            gk = gks[-1]
            if gk not in local_result:
                # key not exists
                local_result[gk] = link
                continue

            if local_result[gk].mutation() < link.mutation():
                # mutation is newer than previous mutation
                local_result[gk] = link
        if use_group_by:
            return result
        if found > 0:
            return result[""]
        return None


class StorageInterface:
    """
    Storage interface with base storage functionality
    """

    def new_link(
        self,
        object_id: str,
        extension: str,
        created_timestamp: int | float | None = None,
    ) -> LinkInterface:
        raise NotImplementedError("StorageInterface#new_link")

    def get(self, link: LinkInterface) -> IO[bytes]:
        raise NotImplementedError("StorageInterface#get")

    def put(self, link: LinkInterface, data: Data) -> bool:
        raise NotImplementedError("StorageInterface#put")

    def remove(self, link: LinkInterface, as_new_mutation: bool = True) -> bool:
        raise NotImplementedError("StorageInterface#remove")

    def find(self, f: LinkFilter | None = None) -> LinkList[LinkInterface]:
        raise NotImplementedError("StorageInterface#find")

    def modify(self, link: LinkInterface, to_link: LinkInterface) -> bool:
        """
        modify link to a new link
        """
        raise NotImplementedError("StorageInterface#modify")

    def content_hash_add(self, link: LinkInterface) -> LinkInterface:
        """
        Add content hash to link, and return with the new link
        """
        raise NotImplementedError("StorageInterface#content_hash_add")

    def content_hash_check(self, link: LinkInterface) -> bool | None:
        """
        Check content hash on link. If link not contain content hash then return None else return equality
        """
        raise NotImplementedError("StorageInterface#content_hash_check")

    def content_hash_eq(
        self, link: LinkInterface, data: IO[bytes] | bytes | str
    ) -> bool:
        """
        Check content hash equality. If the link is not contain content hash then return False.
        """
        raise NotImplementedError("StorageInterface#content_hash_eq")

    def content_hash_generate(self, data: IO[bytes] | bytes | str) -> str:
        """
        Generate content hash from input data
        """
        raise NotImplementedError("StorageInterface#content_hash_generate")

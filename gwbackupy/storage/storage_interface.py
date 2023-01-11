from __future__ import annotations

from typing import Callable, IO, Union

Path = str
DataCall = Callable[[IO[bytes]], None]
Data = Union[str, bytes, DataCall, IO]


class LinkInterface:
    property_deleted = "deleted"
    property_metadata = "metadata"
    property_object = "object"
    property_mutation = "mutation"
    id_special_prefix = "--gwbackupy-"

    # def __init__(self):

    def id(self) -> str:
        pass

    def is_special_id(self) -> bool:
        return self.id().startswith(LinkInterface.id_special_prefix)

    def get_properties(self) -> dict[str, any]:
        pass

    def set_properties(
        self, sets: dict[str, any], replace: bool = False
    ) -> LinkInterface:
        pass

    def get_property(self, name: str, default: any = None) -> any:
        pass

    def has_property(self, name: str) -> bool:
        pass

    def mutation(self) -> str:
        pass

    def is_deleted(self) -> bool:
        pass

    def is_metadata(self) -> bool:
        pass

    def is_object(self) -> bool:
        pass


LinkFilter = Callable[[LinkInterface], bool]
LinkGroupBy = Callable[[LinkInterface], list[Union[str, int]]]


class LinkList(list):
    def __init__(self, iterable):
        super().__init__(item for item in iterable)

    def __setitem__(self, index, item):
        super().__setitem__(index, str(item))

    def insert(self, index, item):
        super().insert(index, item)

    def append(self, item):
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
        if g is None:
            g = lambda _: [""]
        for link in self:
            link: LinkInterface
            if f is not None and not f(link):
                continue
            found += 1
            gks = g(link)
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
                local_result[gk] = link
                continue
            result_mutation = local_result[gk].mutation()
            if result_mutation is None:
                result_mutation = ""
            item_mutation = link.mutation()
            if item_mutation is None:
                item_mutation = ""

            if result_mutation < item_mutation:
                local_result[gk] = link
        if use_group_by:
            return result
        if found > 0:
            return result[""]
        return None


class StorageInterface:
    def new_link(
        self,
        object_id: str,
        extension: str,
        created_timestamp: int | float | None = None,
    ) -> LinkInterface:
        pass

    def get(self, link: LinkInterface) -> IO[bytes]:
        pass

    def put(self, link: LinkInterface, data: Data) -> bool:
        pass

    def remove(self, link: LinkInterface, as_new_mutation: bool = True) -> bool:
        pass

    def find(self, f: LinkFilter | None = None) -> LinkList[LinkInterface]:
        pass

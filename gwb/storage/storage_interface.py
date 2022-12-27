from __future__ import annotations

import datetime
from operator import itemgetter
from typing import Callable, IO

Path = str
DataCall = Callable[[IO[bytes]], None]
Data = str | bytes | DataCall | IO


class ObjectDescriptor:

    def __init__(self):
        self.object_id = None
        self.path = None
        self.mime = None
        self.mutation = None
        self.deleted = False

    def __str__(self):
        return str({'oid': self.object_id, 'path': self.path, 'mime': self.mime, 'mutation': self.mutation,
                    'deleted': self.deleted})


class ObjectList(list):
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

    def get_object_ids(self):
        result = {}
        for item in self:
            item: ObjectDescriptor
            if item.object_id in result:
                continue
            result[item.object_id] = True
        return result.keys()

    def has_object_id(self, oid: str) -> bool:
        for item in self:
            item: ObjectDescriptor
            if item.object_id == oid:
                return True
        return False

    def has_mime(self, mime: str) -> bool:
        for item in self:
            item: ObjectDescriptor
            if item.mime == mime:
                return True
        return False

    def remove_all(self, oid: str):
        removes = []
        for item in self:
            item: ObjectDescriptor
            if item.object_id != oid:
                continue
            removes.append(item)
        for item in removes:
            self.remove(item)

    def get_latest_mutations(self, oid: str) -> ObjectList[ObjectDescriptor]:
        result = {}
        for item in self:
            item: ObjectDescriptor
            if item.object_id != oid:
                continue
            if item.mime not in result:
                result[item.mime] = item
                continue
            result_mutation = result[item.mime].mutation
            if result_mutation is None:
                result_mutation = ''
            item_mutation = item.mutation
            if item_mutation is None:
                item_mutation = ''

            if result_mutation < item_mutation:
                result[item.mime] = item
        return ObjectList(result.values())

    def get_latest_mutation(self, oid: str, mime: str) -> ObjectDescriptor | None:
        for item in self.get_latest_mutations(oid):
            item: ObjectDescriptor
            if item.mime == mime:
                return item

        return None


ObjectFilter = Callable[[ObjectDescriptor], bool]


class StorageInterface:
    mime_json = 'application/json'
    mime_eml = 'application/x-eml'
    mime_eml_gz = 'application/x-eml-gz'
    mime_temp = 'application/x-temp'

    def initialize(self, path: Path):
        pass

    def getd(self, desc: ObjectDescriptor) -> IO[bytes] | None:
        return self.get(path=desc.path, oid=desc.object_id, mime=desc.mime, mutation=desc.mutation,
                        deleted=desc.deleted)

    def get(self, path: Path, oid: str, mime: str, mutation: str = None, deleted: bool = False) -> IO[bytes] | None:
        pass

    def put(self, path: Path, oid: str, mime: str, data: Data, mutation: str = None,
            deleted: bool = False) -> bool:
        pass

    def putd(self, desc: ObjectDescriptor, data: Data) -> bool:
        return self.put(path=desc.path, oid=desc.object_id, mime=desc.mime, mutation=desc.mutation,
                        deleted=desc.deleted, data=data)

    def find(self, path: Path, filter_fun: ObjectFilter | None = None) -> ObjectList[ObjectDescriptor]:
        pass

    @staticmethod
    def new_mutation() -> str:
        return datetime.datetime.utcnow().strftime("%d%m%Y%H%M%S")

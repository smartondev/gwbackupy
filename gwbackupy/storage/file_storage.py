from __future__ import annotations

import copy
import io
import logging
import os
import re
import shutil
from builtins import float
from datetime import datetime, timezone
from typing import IO

from gwbackupy.storage.storage_interface import (
    StorageInterface,
    Path,
    Data,
    LinkFilter,
    LinkInterface,
    LinkList,
)


# Directory structure v2
# /[<path>]
#    - <id>.<propname>=<propvalue>.<propname>=<propvalue>.<ext>
#    - 12345678.m=12345678.metadata=.deleted=.json
#    - 12345678.m=12345678.object=message.eml.gz
#


class FileLink(LinkInterface):
    filename_parser = re.compile(
        r"^(?P<id>[^.]+?)(?P<properties>(?:\.[a-z0-9]+=[^.]*)*)\.(?P<extension>.+)$"
    )

    def __init__(self):
        self.__id: str | None = None
        self.__path: str | None = None
        self.__properties: dict[str, any] = {}
        self.__extension: str | None = None

    def fill(self, values: dict[str, any], replace: bool = False) -> FileLink:
        if "object_id" in values:
            self.__id = values["object_id"]
        if replace:
            self.__properties = {}
        if "deleted" in values:
            self.__properties[LinkInterface.property_deleted] = True
        if "object" in values:
            self.__properties[LinkInterface.property_object] = True
        if "metadata" in values:
            self.__properties[LinkInterface.property_metadata] = True
        if "extension" in values:
            self.__extension = values["extension"]
        if "mutation" in values:
            self.__properties[LinkInterface.property_mutation] = values["mutation"]
        if "path" in values:
            self.__path = values["path"]
        for key in values:
            if key not in [
                "object_id",
                "deleted",
                "object",
                "metadata",
                "extension",
                "mutation",
                "path",
            ]:
                value = values[key]
                if isinstance(value, str):
                    if value == "":
                        value = True
                    self.__properties[key] = value
        return self

    def get_file_path(self) -> str:
        path = self.__path + "/" + self.__id
        keys = list(self.__properties.keys())
        keys.sort()
        for k in keys:
            if self.__properties[k] is None:
                continue
            path += f".{k}="
            if self.__properties[k] is not True:
                path += str(self.__properties[k])
        if self.__extension is not None:
            path += f".{self.__extension}"

        return path

    @staticmethod
    def parse_file_name(filename: str) -> dict[str, any] | None:
        m = FileLink.filename_parser.search(filename)
        if m is None:
            return None
        result: dict[str, any] = {
            "object_id": m.group("id"),
            "extension": m.group("extension"),
        }
        properties = m.group("properties")
        if properties is None or properties == "":
            return result
        for prop in properties.strip(".").split("."):
            p, v = prop.split("=", 1)
            if v == "":
                v = True
            result[p] = v
        return result

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
        return f"{self.__class__}#id:{self.id()},props:{self.__properties},path:{self.__path}"


class FileStorage(StorageInterface):
    def __init__(self, root: str):
        self.root = root

    def new_link(
        self,
        object_id: str,
        extension: str,
        created_timestamp: int | float | None = None,
    ) -> FileLink:
        link = FileLink()
        path = self.root
        if created_timestamp is not None:
            sub_paths = (
                datetime.fromtimestamp(created_timestamp, tz=timezone.utc)
                .strftime("%Y-%m-%d")
                .split("-", 1)
            )
            path += f"/{sub_paths[0]}/{sub_paths[1]}"
        link.fill(
            {
                "path": path,
                "object_id": object_id,
                "extension": extension,
                "mutation": FileStorage.__gen_mutation(),
            }
        )
        return link

    @staticmethod
    def __gen_mutation():
        return str(int(datetime.utcnow().timestamp() * 1000))

    def get(self, link: FileLink) -> IO[bytes]:
        file_path = link.get_file_path()
        return open(file_path, "rb")

    def put(self, link: FileLink, data: Data) -> bool:
        file_path = link.get_file_path()
        logging.debug(f"Put object {file_path}")
        result = self.__write(file_path=file_path, data=data)
        if result:
            logging.debug(f"{file_path} put successfully")
            return True
        logging.error(f"File put fail ({file_path})")
        return False

    def initialize(self, path: Path):
        pass

    def remove(self, link: FileLink, as_new_mutation: bool = True) -> bool:
        if not as_new_mutation:
            try:
                if os.path.exists(link.get_file_path()):
                    os.remove(link.get_file_path())
                return True
            except BaseException as e:
                logging.exception(f"Delete fail {link.get_file_path()} with error: {e}")
                return False

        dst = copy.deepcopy(link).fill(
            {
                "deleted": True,
                "mutation": self.__gen_mutation(),
            }
        )
        try:
            with self.get(link) as f:
                if not f:
                    logging.error(f"{link.get_file_path()} not found or not readable")
                    return False
                self.put(dst, f)
        except BaseException as e:
            logging.exception(
                f"Copy as new mutation is failed {link.get_file_path()} -> {dst.get_file_path()}: {e}"
            )
            return False
        return True

    def find(self, f: LinkFilter | None = None) -> LinkList[LinkInterface]:
        abspath = self.root
        skip_path = len(abspath)
        result: LinkList[LinkInterface] = LinkList([])
        for _path, _, filenames in os.walk(abspath):
            for file in filenames:
                file_path = os.path.join(_path, file)
                relpath = _path[skip_path:]
                link = FileLink()
                if len(relpath) > 0:
                    link.path = relpath
                m = FileLink.parse_file_name(file)
                if m is None:
                    continue
                m["path"] = _path
                link.fill(m)

                if "extension" not in m:
                    logging.debug(f"Unknown file without extension: {file_path}")
                    continue
                if m["extension"] == "tmp":
                    logging.debug(f"Temporary file {file_path}, remove it")
                    try:
                        os.remove(file_path)
                    except BaseException as e:
                        logging.exception(
                            f"Temporary file remove fail {file_path}: {e}"
                        )
                    continue

                if f is None or f(link):
                    result.append(link)
        return result

    @staticmethod
    def __remove(file_path: str) -> bool:
        try:
            exists = os.path.exists(file_path)
            if not exists:
                return True
        except BaseException as e:
            logging.exception(f"File exists check fail {file_path}: {e}")
            return False

        try:
            os.remove(file_path)
        except BaseException as e:
            logging.exception(f"File remove fail {file_path}: {e}")
            return False
        return True

    @staticmethod
    def __write(file_path: str, data: Data) -> bool:
        path = os.path.dirname(file_path)
        try:
            path_exists = os.path.exists(path)
            if not path_exists:
                try:
                    os.makedirs(path, exist_ok=True)
                except BaseException as e:
                    logging.exception(f"Directory create fail {path}: {e}")
                    return False
        except BaseException as e:
            logging.exception(f"Directory exists check fail {path}: {e}")
            return False

        file_path_tmp = f"{file_path}.tmp"
        try:
            try:
                with open(file_path_tmp, "wb") as f:
                    if isinstance(data, bytes):
                        f.write(data)
                    elif isinstance(data, str):
                        f.write(bytes(data, "utf-8"))
                    elif isinstance(data, io.BufferedReader):
                        f.write(data.read())
                    elif callable(data):
                        data(f)
                    else:
                        raise RuntimeError(f"Not supported data type: {type(data)}")
            except BaseException as e:
                logging.exception(f"Temporary file writing fail {file_path_tmp}: {e}")
                return False
            try:
                shutil.move(file_path_tmp, file_path)
            except BaseException as e:
                logging.exception(
                    f"File rename fail {file_path_tmp} -> {file_path}: {e}"
                )
                return False
            return True
        finally:
            FileStorage.__remove(file_path_tmp)
from __future__ import annotations

import io
import logging
import os
import re
import shutil
import traceback
from typing import IO

from gwb.storage.storage_interface import StorageInterface, Path, Data, ObjectFilter, ObjectDescriptor, ObjectList, \
    DataCall


class FileStorage(StorageInterface):
    filename_parser = re.compile(
        r'^(?P<id>[^.]+?)\.(?:(?P<mutation>\d+)\.(?:(?P<deleted>deleted)\.)?)?(?P<extension>.+)$'
    )

    def __init__(self, root: str):
        self.root = root

    def get(self, path: Path, oid: str, mime: str, mutation: str = None, deleted: bool = False) -> IO[bytes] | None:
        file_path = self.__get_path(path=path, oid=oid, mime=mime, mutation=mutation, deleted=deleted)
        if not os.path.exists(file_path):
            return None
        return open(file_path, 'rb')

    def put(self, path: Path, oid: str, mime: str, data: Data, mutation: str = None,
            deleted: bool = False) -> bool:
        file_path = self.__get_path(path=path, oid=oid, mime=mime, mutation=mutation, deleted=deleted)
        logging.debug(f'Put object {file_path}')
        result = self.__write(file_path=file_path, data=data)
        if result:
            logging.debug(f'{file_path} put successfully')
            return True
        logging.error(f'File put fail ({file_path})')
        return False

    def initialize(self, path: Path):
        pass

    def find(self, path: Path, filter_fun: ObjectFilter | None = None) -> ObjectList[ObjectDescriptor]:
        abspath = self.__get_path(path=path)
        skip_path = len(abspath) - len(path)
        result: ObjectList[ObjectDescriptor] = ObjectList([])
        for _path, _, filenames in os.walk(abspath):
            for file in filenames:
                file_path = os.path.join(_path, file)
                relpath = _path[skip_path:]
                d = ObjectDescriptor()
                if len(relpath) > 0:
                    d.path = relpath
                m = FileStorage.filename_parser.search(file)
                if m is None:
                    continue
                mime = FileStorage.__extension2mime(m.group('extension'))
                if mime is None:
                    continue
                if mime == StorageInterface.mime_temp:
                    try:
                        os.remove(file_path)
                    except BaseException as e:
                        logging.error(f'Temporary file delete fail {file_path}: {e}')
                        logging.error(traceback.format_exc())
                    continue

                d.mime = mime
                mutation = m.group('mutation')
                d.object_id = m.group('id')
                d.deleted = m.group('deleted') is not None
                if mutation is not None and len(mutation) > 0:
                    d.mutation = mutation

                if filter_fun is None or filter_fun(d):
                    result.append(d)
        return result

    def __get_path(self, path: Path, oid: str | None = None, mime: str | None = None, mutation: str | None = None,
                   deleted: bool = False) -> str:
        p = self.root
        if isinstance(path, str):
            p += path

        if oid is None:
            return p
        p += '/' + oid
        if mutation is not None:
            p += f'.{mutation}'
        if deleted:
            p += f'.deleted'
        if mime is not None:
            p += f'.{FileStorage.__mime2extension(mime)}'
        return p

    @staticmethod
    def __extension2mime(extension: str) -> str | None:
        if extension == 'json':
            return StorageInterface.mime_json
        if extension == 'eml':
            return StorageInterface.mime_eml
        if extension == 'eml.gz':
            return StorageInterface.mime_eml_gz
        return None

    @staticmethod
    def __mime2extension(mime: str) -> str | None:
        if mime == StorageInterface.mime_eml:
            return 'eml'
        if mime == StorageInterface.mime_eml_gz:
            return 'eml.gz'
        if mime == StorageInterface.mime_json:
            return 'json'
        return None

    @staticmethod
    def __remove(file_path: str) -> bool:
        try:
            exists = os.path.exists(file_path)
            if not exists:
                return True
        except BaseException as e:
            logging.error(f'File exists check fail {file_path}: {e}')
            logging.error(traceback.format_exc())
            return False

        try:
            os.remove(file_path)
        except BaseException as e:
            logging.error(f'File remove fail {file_path}: {e}')
            logging.error(traceback.format_exc())
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
                    logging.error(
                        f'Directory create fail {path}: {e}')
                    logging.error(traceback.format_exc())
                    return False
        except BaseException as e:
            logging.error(f'Directory exists check fail {path}: {e}')
            logging.error(traceback.format_exc())
            return False

        file_path_tmp = f'{file_path}.tmp'
        try:
            try:
                with open(file_path_tmp, 'wb') as f:
                    if isinstance(data, bytes):
                        f.write(data)
                    elif isinstance(data, str):
                        f.write(bytes(data, 'utf-8'))
                    elif isinstance(data, io.BufferedReader):
                        f.write(data.read())
                    elif callable(data):
                        data(f)
                    else:
                        raise RuntimeError(f'Not supported data type: {type(data)}')
            except BaseException as e:
                logging.error(f'Temporary file writing fail {file_path_tmp}: {e}')
                logging.error(traceback.format_exc())
                return False
            try:
                shutil.move(file_path_tmp, file_path)
            except BaseException as e:
                logging.error(f'File rename fail {file_path_tmp} -> {file_path}: {e}')
                logging.error(traceback.format_exc())
                return False
            return True
        finally:
            FileStorage.__remove(file_path_tmp)

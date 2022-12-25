import os
import re
from datetime import datetime


class StorageDescriptor:
    """Local files descriptor"""
    filename_parser = re.compile(
        r'^(?P<id>[^.]+?)\.(?:(?P<mutation>\d+)\.(?:(?P<deleted>deleted)\.)?)?(?P<extension>.+)$'
    )

    def __init__(self, path=None, object_id=None):
        self.path = path
        self.object_id = object_id
        self.object = None
        self.object_hash = None
        self.mutations = {}
        self.latest_mutation = None
        self.deleted = False

    def get_new_mutation_metadata_file_path(self, deleted=False):
        mutation = datetime.utcnow().strftime("%d%m%Y%H%M%S")
        file_parts = [self.object_id, mutation]
        if deleted:
            file_parts.append('deleted')
        file_parts.append('json')
        return os.path.join(self.path, '.'.join(file_parts))

    def get_latest_mutation_metadata_file_path(self):
        file_parts = [self.object_id]
        if self.latest_mutation:
            file_parts.append(self.latest_mutation)
        if self.deleted:
            file_parts.append('deleted')
        file_parts.append('json')
        return os.path.join(self.path, '.'.join(file_parts))

    def add_mutation(self, file, parameters):
        mutation = parameters.get('mutation')
        self.mutations[mutation] = file
        if mutation is not None and (self.latest_mutation is None or self.latest_mutation < mutation):
            self.latest_mutation = mutation
        if parameters.get('deleted') is not None:
            self.deleted = True

    @staticmethod
    def parse(filename):
        m = StorageDescriptor.filename_parser.search(filename)
        if m is None:
            return None
        return m.groupdict()

    @staticmethod
    def is_ext_json(filename):
        return filename.endswith('.json')

    @staticmethod
    def is_ext_eml(filename):
        return filename.endswith('.eml') or filename.endswith('.eml.gz')

    @staticmethod
    def is_ext_hash(filename):
        return filename.endswith('.hash')

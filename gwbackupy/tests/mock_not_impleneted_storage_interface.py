from gwbackupy.storage.storage_interface import StorageInterface, LinkInterface


class MockNotImplementedStorage(StorageInterface):
    def __init__(self):
        pass


class MockNotImplementedLink(LinkInterface):
    def __init__(self):
        pass

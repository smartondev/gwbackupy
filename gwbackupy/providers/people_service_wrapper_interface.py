from __future__ import annotations


class PeopleServiceWrapperInterface:
    def get_peoples(self, email: str) -> dict[str, [dict[str, any]]]:
        pass

    def get_photo(self, email: str, people_id: str, uri: str) -> PhotoDescriptor:
        pass


class PhotoDescriptor:
    def __init__(self, uri: str, data: bytes, mime_type: str):
        self.uri = uri
        self.data = data
        self.mime_type = mime_type

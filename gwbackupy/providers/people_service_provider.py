from __future__ import annotations

from gwbackupy.providers.gapi_service_provider import GapiServiceProvider
from gwbackupy.storage.storage_interface import StorageInterface


class PeopleServiceProvider(GapiServiceProvider):
    """Contacts service provider from gmail/v1 API with full access scope"""

    def __init__(self, **kwargs):
        super(PeopleServiceProvider, self).__init__(
            "people", "v1", ["https://www.googleapis.com/auth/contacts"], **kwargs
        )

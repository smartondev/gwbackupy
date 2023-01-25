from __future__ import annotations

from gwbackupy.providers.gapi_service_provider import GapiServiceProvider
from gwbackupy.storage.storage_interface import StorageInterface


class GmailServiceProvider(GapiServiceProvider):
    """Gmail service provider from gmail/v1 API with full access scope"""

    def __init__(self, **kwargs):
        super(GmailServiceProvider, self).__init__(
            "gmail", "v1", ["https://mail.google.com/"], **kwargs
        )

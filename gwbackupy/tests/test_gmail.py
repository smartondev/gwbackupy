import tempfile

from gwbackupy.gmail import Gmail
from gwbackupy.storage.file_storage import FileStorage
from gwbackupy.tests.test_mock_gmail_service_wrapper import MockGmailServiceWrapper
from gwbackupy.tests.test_mock_service_provider import MockServiceProvider


def test_empty_server_backup():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        sp = MockServiceProvider()
        sw = MockGmailServiceWrapper()
        email = "example@example.com"
        gmail = Gmail(
            email=email,
            storage=fs,
            service_provider=sp,
            service_wrapper=sw,
        )
        assert gmail.backup()

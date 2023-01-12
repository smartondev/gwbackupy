from gwbackupy.gmail import Gmail
from gwbackupy.tests.mock_storage import MockStorage
from gwbackupy.tests.test_mock_gmail_service_wrapper import MockGmailServiceWrapper


def test_empty_server_backup():
    ms = MockStorage()
    sw = MockGmailServiceWrapper()
    email = "example@example.com"
    gmail = Gmail(
        email=email,
        storage=ms,
        service_wrapper=sw,
    )
    assert gmail.backup()

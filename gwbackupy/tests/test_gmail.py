import gzip
from datetime import datetime

from gwbackupy.gmail import Gmail
from gwbackupy.helpers import random_string, encode_base64url
from gwbackupy.storage.storage_interface import LinkInterface
from gwbackupy.tests.mock_storage import MockStorage
from gwbackupy.tests.mock_gmail_service_wrapper import MockGmailServiceWrapper


def test_server_backup_empty():
    ms = MockStorage()
    sw = MockGmailServiceWrapper()
    email = "example@example.com"
    gmail = Gmail(
        email=email,
        storage=ms,
        service_wrapper=sw,
    )
    assert gmail.backup()


def test_server_backup_one_message():
    ms = MockStorage()
    sw = MockGmailServiceWrapper()
    message_id = random_string()
    message_raw = bytes(f"Message body... {message_id}", "utf-8")
    sw.inject_message(
        {
            "id": message_id,
            "raw": encode_base64url(message_raw),
            "internalDate": str(int(datetime.now().timestamp() * 1000)),
        }
    )
    email = "example@example.com"
    gmail = Gmail(
        email=email,
        storage=ms,
        service_wrapper=sw,
    )
    assert gmail.backup()
    # labels + one metadata + one message body
    assert len(ms.inject_get_objects()) == 3
    message_meta_found = False
    message_body_found = False
    for link in ms.find():
        if link.id() == message_id:
            if link.is_metadata():
                message_meta_found = True
            if link.is_object():
                message_body_found = True
                with ms.get(link) as f:
                    assert message_raw == gzip.decompress(f.read())
                assert link.has_property(LinkInterface.property_content_hash)
                assert ms.content_hash_generate(message_raw) == link.get_property(
                    LinkInterface.property_content_hash
                )
    assert message_meta_found
    assert message_body_found

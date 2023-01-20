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
                assert ms.content_hash_check(link)
    assert message_meta_found
    assert message_body_found


def test_server_continuos_backup():
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
    message_id2 = random_string()
    message_raw2 = bytes(f"Message body... {message_id2}", "utf-8")
    sw.inject_message(
        {
            "id": message_id2,
            "raw": encode_base64url(message_raw2),
            "internalDate": str(int(datetime.now().timestamp() * 1000)),
        }
    )
    assert gmail.backup()
    # labels + two messages metadata + two messages object
    assert len(ms.inject_get_objects()) == 1 + 2 + 2
    requirements = {
        message_id: {"metadata": False, "message": False, "message_raw": message_raw},
        message_id2: {"metadata": False, "message": False, "message_raw": message_raw2},
    }
    for link in ms.find():
        if link.id() not in requirements:
            assert link.is_special_id()
            continue
        if link.is_metadata():
            requirements[link.id()]["metadata"] = True
        if link.is_object():
            requirements[link.id()]["message"] = True
            with ms.get(link) as f:
                assert requirements[link.id()]["message_raw"] == gzip.decompress(
                    f.read()
                )
            assert link.has_property(LinkInterface.property_content_hash)
            assert ms.content_hash_generate(
                requirements[link.id()]["message_raw"]
            ) == link.get_property(LinkInterface.property_content_hash)
            assert ms.content_hash_check(link)

    for _id in requirements:
        assert requirements[_id]["metadata"]
        assert requirements[_id]["message"]


# TODO: add tests for content hash fix BC

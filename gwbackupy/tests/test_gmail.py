import copy
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


def test_server_continuous_backup():
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
    # check initial backup
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
    # check continuous backup
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
            assert ms.content_hash_check(link)
            link_without_content_hash = copy.deepcopy(link)
            link_without_content_hash.set_properties(
                {
                    LinkInterface.property_content_hash: None,
                }
            )
            assert ms.modify(link, link_without_content_hash)
            assert (
                link_without_content_hash.has_property(
                    LinkInterface.property_content_hash
                )
                is False
            )

    for _id in requirements:
        assert requirements[_id]["metadata"]
        assert requirements[_id]["message"]

    # check content hash missing
    for link in ms.find():
        if link.is_special_id():
            continue
        if link.is_object():
            assert link.has_property(LinkInterface.property_content_hash) is False
            assert ms.content_hash_check(link) is None

    # check content hash fix
    assert gmail.backup()
    for link in ms.find():
        if link.is_special_id():
            continue
        if link.is_object():
            assert link.has_property(LinkInterface.property_content_hash)
            assert ms.content_hash_check(link) is True

import copy
import gzip
import logging
import sys
from datetime import datetime, timedelta
import parametrize_from_file

from typing import List, Dict

from gwbackupy import global_properties
from gwbackupy.filters.gmail_filter import GmailFilter
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
    email = "example@example.com"
    sw.inject_message(
        email,
        {
            "id": message_id,
            "raw": encode_base64url(message_raw),
            "internalDate": str(int(datetime.now().timestamp() * 1000)),
        },
    )
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
        email,
        {
            "id": message_id2,
            "raw": encode_base64url(message_raw2),
            "internalDate": str(int(datetime.now().timestamp() * 1000)),
        },
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


@parametrize_from_file
def test_restore_with_label_recreate(to_email: str, clear_labels: bool):
    ms = MockStorage()
    sw = MockGmailServiceWrapper()
    message_id = random_string()
    message_raw = bytes(f"Message body... {message_id}", "utf-8")
    email = "example@example.com"
    label1 = sw.create_label(email, "label_name_123")
    label2 = sw.create_label(email, "label_name_999")
    sw.inject_message(
        email,
        {
            "id": message_id,
            "raw": encode_base64url(message_raw),
            "internalDate": str(int(datetime.now().timestamp() * 1000)),
            "labelIds": [label1["id"], label2["id"]],
            "snippet": "A short snippet",
        },
    )
    gmail = Gmail(
        email=email,
        storage=ms,
        service_wrapper=sw,
    )
    assert gmail.backup()
    if clear_labels:
        sw.inject_labels_clear()
    sw.inject_messages_clear()
    filtr = GmailFilter()
    filtr.with_match_missing()
    assert gmail.restore(filtr, add_labels=[], to_email=to_email)
    messages = sw.get_messages(to_email, q="all")
    assert len(messages) == 1
    restored_message = list(messages.values())[0]
    restored_label_ids = restored_message["labelIds"]
    reloaded_labels = sw.get_labels(to_email)
    assert len(restored_label_ids) == 2
    assert __find_label_by_label_name(reloaded_labels, label1["name"])
    assert __find_label_by_label_name(reloaded_labels, label2["name"])


def test_restore_without_label_ids_key():
    """
    Test that restore works when labelIds key is missing in message metadata
    """
    ms = MockStorage()
    sw = MockGmailServiceWrapper()
    message_id = random_string()
    message_raw = bytes(f"Message body... {message_id}", "utf-8")
    email = "example@example.com"
    to_email = "example-to@example.com"
    sw.inject_message(
        email,
        {
            "id": message_id,
            "raw": encode_base64url(message_raw),
            "internalDate": str(int(datetime.now().timestamp() * 1000)),
            "snippet": "A short snippet",
        },
    )
    gmail = Gmail(
        email=email,
        storage=ms,
        service_wrapper=sw,
    )
    assert gmail.backup()
    sw.inject_messages_clear()
    sw.inject_labels_clear()
    filtr = GmailFilter()
    filtr.with_match_missing()
    assert gmail.restore(filtr, add_labels=[], to_email=to_email)
    messages = sw.get_messages(to_email, q="all")
    assert len(messages) == 1
    restored_message = list(messages.values())[0]
    restored_label_ids = restored_message["labelIds"]
    assert len(restored_label_ids) == 0


def test_quick_sync_new_and_deleted():
    """quick_sync downloads new messages and marks deleted ones"""
    ms = MockStorage()
    sw = MockGmailServiceWrapper()
    email = "example@example.com"
    message_id1 = random_string()
    message_raw1 = bytes(f"Message body... {message_id1}", "utf-8")
    sw.inject_message(
        email,
        {
            "id": message_id1,
            "raw": encode_base64url(message_raw1),
            "internalDate": str(int(datetime.now().timestamp() * 1000)),
        },
    )
    gmail = Gmail(email=email, storage=ms, service_wrapper=sw)
    assert gmail.backup()

    # Remove message1 from server (simulates deletion), add message2
    sw.inject_messages_clear()
    message_id2 = random_string()
    message_raw2 = bytes(f"Message body... {message_id2}", "utf-8")
    sw.inject_message(
        email,
        {
            "id": message_id2,
            "raw": encode_base64url(message_raw2),
            "internalDate": str(int(datetime.now().timestamp() * 1000)),
        },
    )

    assert gmail.backup(quick_sync=True)
    # labels + message1 (meta+obj) + message2 (meta+obj) = 5
    assert len(ms.inject_get_objects()) == 1 + 2 + 2
    found_new = False
    for link in ms.find():
        if link.id() == message_id2 and link.is_object():
            found_new = True
            with ms.get(link) as f:
                assert gzip.decompress(f.read()) == message_raw2
    assert found_new


def test_quick_sync_skips_existing():
    """quick_sync does not re-download existing messages"""
    ms = MockStorage()
    sw = MockGmailServiceWrapper()
    email = "example@example.com"
    message_id = random_string()
    message_raw = bytes(f"Message body... {message_id}", "utf-8")
    sw.inject_message(
        email,
        {
            "id": message_id,
            "raw": encode_base64url(message_raw),
            "internalDate": str(int(datetime.now().timestamp() * 1000)),
        },
    )
    gmail = Gmail(email=email, storage=ms, service_wrapper=sw)
    assert gmail.backup()
    objects_after_initial = len(ms.inject_get_objects())

    # Run quick_sync - existing message should be skipped, no new objects
    assert gmail.backup(quick_sync=True)
    assert len(ms.inject_get_objects()) == objects_after_initial


def test_quick_sync_with_days_checks_labels():
    """quick_sync + quick_sync_days: checks label changes for recent messages,
    skips old ones"""
    ms = MockStorage()
    sw = MockGmailServiceWrapper()
    email = "example@example.com"

    # Old message (30 days ago)
    old_message_id = random_string()
    old_timestamp = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
    old_message_raw = bytes(f"Old message {old_message_id}", "utf-8")
    sw.inject_message(
        email,
        {
            "id": old_message_id,
            "raw": encode_base64url(old_message_raw),
            "internalDate": str(old_timestamp),
        },
    )

    # Recent message (1 day ago)
    recent_message_id = random_string()
    recent_timestamp = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
    recent_message_raw = bytes(f"Recent message {recent_message_id}", "utf-8")
    sw.inject_message(
        email,
        {
            "id": recent_message_id,
            "raw": encode_base64url(recent_message_raw),
            "internalDate": str(recent_timestamp),
        },
    )

    gmail = Gmail(email=email, storage=ms, service_wrapper=sw)
    assert gmail.backup()
    objects_after_initial = len(ms.inject_get_objects())

    # Change labels on recent message to simulate server-side label change
    sw.inject_messages_clear()
    sw.inject_message(
        email,
        {
            "id": old_message_id,
            "raw": encode_base64url(old_message_raw),
            "internalDate": str(old_timestamp),
        },
    )
    sw.inject_message(
        email,
        {
            "id": recent_message_id,
            "raw": encode_base64url(recent_message_raw),
            "internalDate": str(recent_timestamp),
            "labelIds": ["INBOX", "IMPORTANT"],
        },
    )

    # Run quick_sync with 7 days: old message skipped, recent message checked
    assert gmail.backup(quick_sync=True, quick_sync_days=7)
    # Recent message was within cutoff -> checked and label change detected -> new metadata
    # Old message was before cutoff -> skipped entirely
    assert len(ms.inject_get_objects()) > objects_after_initial
    # Verify: recent message got updated metadata, old message did not
    recent_meta_count = 0
    old_meta_count = 0
    for link in ms.find():
        if link.id() == recent_message_id and link.is_metadata():
            recent_meta_count += 1
        if link.id() == old_message_id and link.is_metadata():
            old_meta_count += 1
    assert recent_meta_count == 2  # initial + updated
    assert old_meta_count == 1  # only initial, skipped by quick_sync


def __find_label_by_label_name(
    labels: List[Dict[str, any]], name: str
) -> Dict[str, any]:
    for label in labels:
        if label["name"] == name:
            return label
    raise ValueError(f"Label with name {name} not found")


if __name__ == "__main__":
    Log_Format = "%(levelname)s %(asctime)s - %(message)s"
    logging.addLevelName(global_properties.log_finest, "FINEST")
    logging.basicConfig(
        # filename="logfile.log",
        stream=sys.stdout,
        filemode="w",
        format=Log_Format,
        level=logging.DEBUG,
    )
    test_restore_with_label_recreate("example2@example.com", True)

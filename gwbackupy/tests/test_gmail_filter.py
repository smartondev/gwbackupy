from gwbackupy.filters.gmail_filter import GmailFilter
from gwbackupy.storage.storage_interface import LinkInterface
from gwbackupy.tests.mock_storage import MockStorage


def test_match_object():
    f = GmailFilter()
    ms = MockStorage()
    link = ms.new_link("abc", "json")
    link.set_properties({LinkInterface.property_object: True})
    assert f.match(
        {
            "message-id": "abc",
            "link": link,
            "server-data": {},
        }
    )
    assert f.match(
        {
            "message-id": "abc",
            "link": link,
            "server-data": {"abc": dict()},
        }
    )


def test_match_metadata():
    f = GmailFilter()
    ms = MockStorage()
    link = ms.new_link("abc", "json")
    link.set_properties({LinkInterface.property_metadata: True})
    assert f.match(
        {
            "message-id": "abc",
            "link": link,
            "server-data": {},
        }
    )
    assert f.match(
        {
            "message-id": "abc",
            "link": link,
            "server-data": {"abc": dict()},
        }
    )


def test_match_metadata_deleted():
    f = GmailFilter()
    ms = MockStorage()
    link = ms.new_link("abc", "json")
    link.set_properties(
        {
            LinkInterface.property_metadata: True,
            LinkInterface.property_deleted: True,
        }
    )
    assert not f.match(
        {
            "message-id": "abc",
            "link": link,
            "server-data": {},
        }
    )
    f.with_match_deleted()
    assert f.match(
        {
            "message-id": "abc",
            "link": link,
            "server-data": {},
        }
    )


def test_match_metadata_missing():
    f = GmailFilter()
    ms = MockStorage()
    link = ms.new_link("abc", "json")
    link.set_properties(
        {
            LinkInterface.property_metadata: True,
        }
    )
    f.with_match_missing()
    assert f.match(
        {
            "message-id": "abc",
            "link": link,
            "server-data": {},
        }
    )
    assert not f.match(
        {
            "message-id": "abc",
            "link": link,
            "server-data": {"abc": dict()},
        }
    )


def test_with_methods():
    f = GmailFilter()
    assert not f.is_match_deleted()
    f.with_match_deleted()
    assert f.is_match_deleted()
    f.with_match_deleted(False)
    assert not f.is_match_deleted()
    assert not f.is_match_missing()
    f.with_match_missing()
    assert f.is_match_missing()
    f.with_match_missing(False)
    assert not f.is_match_missing()

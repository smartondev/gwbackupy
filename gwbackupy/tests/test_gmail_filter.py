from datetime import datetime, timezone

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


def test_with_date_to():
    f = GmailFilter()
    ms = MockStorage()
    link = ms.new_link("abc", "json")
    filter_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    if datetime.now().timestamp() < filter_date.timestamp():
        raise Exception("The test is not valid if the filter date is in the future")
    f.with_date_to(filter_date)
    assert not f.match(
        {
            "message-id": "abc",
            "link": link,
            "server-data": {},
        }
    )
    f.with_date_to(None)
    assert f.match(
        {
            "message-id": "abc",
            "link": link,
            "server-data": {},
        }
    )


def test_with_date_from():
    f = GmailFilter()
    ms = MockStorage()
    f.with_date_from(datetime(2021, 1, 1, tzinfo=timezone.utc))
    link = ms.new_link(
        "abc",
        "json",
        created_timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp(),
    )
    link.set_mutation_timestamp(datetime(2019, 1, 1, tzinfo=timezone.utc))
    assert not f.match(
        {
            "message-id": "abc",
            "link": link,
            "server-data": {},
        }
    )
    f.with_date_from(None)
    assert f.match(
        {
            "message-id": "abc",
            "link": ms.new_link("abc", "json"),
            "server-data": {},
        }
    )


def test_with_date_from_and_to():
    f = GmailFilter()
    ms = MockStorage()
    link = ms.new_link("abc", "json")
    link.set_mutation_timestamp(datetime(2020, 1, 1, tzinfo=timezone.utc))
    f.with_date_from(datetime(2021, 1, 1, tzinfo=timezone.utc))
    f.with_date_to(datetime(2022, 2, 1, tzinfo=timezone.utc))
    assert not f.match(
        {
            "message-id": "abc",
            "link": link,
            "server-data": {},
        }
    )
    link.set_mutation_timestamp(datetime(2021, 5, 5, tzinfo=timezone.utc))
    assert f.match(
        {
            "message-id": "abc",
            "link": link,
            "server-data": {},
        }
    )

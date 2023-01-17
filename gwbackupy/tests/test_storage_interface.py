from gwbackupy.storage.storage_interface import LinkInterface
from gwbackupy.tests.mock_not_impleneted_storage_interface import (
    MockNotImplementedStorage,
    MockNotImplementedLink,
)


def get_exception(f):
    try:
        f()
    except BaseException as e:
        return e
    return None


def test_not_implemented_storage():
    s = MockNotImplementedStorage()
    e = get_exception(lambda: s.get(LinkInterface()))
    assert isinstance(e, NotImplementedError)
    assert str(e) == "StorageInterface#get"
    e = get_exception(lambda: s.put(LinkInterface(), ""))
    assert isinstance(e, NotImplementedError)
    assert str(e) == "StorageInterface#put"
    e = get_exception(lambda: s.remove(LinkInterface()))
    assert isinstance(e, NotImplementedError)
    assert str(e) == "StorageInterface#remove"
    e = get_exception(lambda: s.find())
    assert isinstance(e, NotImplementedError)
    assert str(e) == "StorageInterface#find"
    e = get_exception(lambda: s.new_link("-", "-"))
    assert isinstance(e, NotImplementedError)
    assert str(e) == "StorageInterface#new_link"


def test_not_implemented_link():
    link = MockNotImplementedLink()
    e = get_exception(lambda: link.id())
    assert isinstance(e, NotImplementedError)
    assert str(e) == "LinkInterface#id"
    e = get_exception(lambda: link.get_properties())
    assert isinstance(e, NotImplementedError)
    assert str(e) == "LinkInterface#get_properties"
    e = get_exception(lambda: link.set_properties({}))
    assert isinstance(e, NotImplementedError)
    assert str(e) == "LinkInterface#set_properties"
    e = get_exception(lambda: link.set_properties({}))
    assert isinstance(e, NotImplementedError)
    assert str(e) == "LinkInterface#set_properties"
    e = get_exception(lambda: link.get_property(""))
    assert isinstance(e, NotImplementedError)
    assert str(e) == "LinkInterface#get_property"
    e = get_exception(lambda: link.has_property(""))
    assert isinstance(e, NotImplementedError)
    assert str(e) == "LinkInterface#has_property"
    e = get_exception(lambda: link.mutation())
    assert isinstance(e, NotImplementedError)
    assert str(e) == "LinkInterface#mutation"
    e = get_exception(lambda: link.is_object())
    assert isinstance(e, NotImplementedError)
    assert str(e) == "LinkInterface#is_object"
    e = get_exception(lambda: link.is_metadata())
    assert isinstance(e, NotImplementedError)
    assert str(e) == "LinkInterface#is_metadata"
    e = get_exception(lambda: link.is_object())
    assert isinstance(e, NotImplementedError)
    assert str(e) == "LinkInterface#is_object"

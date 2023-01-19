from gwbackupy.storage.storage_interface import LinkInterface, LinkList
from gwbackupy.tests.helpers import get_exception
from gwbackupy.tests.mock_not_impleneted_storage_interface import (
    MockNotImplementedStorage,
    MockNotImplementedLink,
)
from gwbackupy.tests.mock_storage import MockStorage


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
    e = get_exception(lambda: link.is_deleted())
    assert isinstance(e, NotImplementedError)
    assert str(e) == "LinkInterface#is_deleted"
    e = get_exception(lambda: link.is_metadata())
    assert isinstance(e, NotImplementedError)
    assert str(e) == "LinkInterface#is_metadata"
    e = get_exception(lambda: link.is_object())
    assert isinstance(e, NotImplementedError)
    assert str(e) == "LinkInterface#is_object"


def test_link_list():
    ll = LinkList()
    e = get_exception(lambda: ll.append("aa"))
    assert isinstance(e, ValueError)
    assert get_exception(lambda: ll.append(MockNotImplementedLink())) is None
    e = get_exception(lambda: ll.__setitem__(0, "aa"))
    assert isinstance(e, ValueError)
    assert get_exception(lambda: ll.__setitem__(0, MockNotImplementedLink())) is None
    e = get_exception(lambda: ll.insert(0, "aa"))
    assert isinstance(e, ValueError)
    assert get_exception(lambda: ll.insert(0, MockNotImplementedLink())) is None


def test_link_interface():
    ms = MockStorage()
    link = ms.new_link("apple", "-")
    assert not link.is_special_id()
    link2 = ms.new_link(LinkInterface.id_special_prefix + "apple", "-")
    assert link2.is_special_id()


def test_link_list_find():
    ll = LinkList()
    assert ll.find(f=lambda _: False) is None
    assert ll.find(f=lambda _: True) is None
    ms = MockStorage()
    link = ms.new_link("apple", "-")
    ll.append(link)
    assert ll.find(f=lambda _: False) is None
    assert ll.find(f=lambda _: True) == link
    link2 = ms.new_link("apple", "-")
    ll.append(link2)
    assert ll.find(f=lambda _: True) == link2
    link3 = ms.new_link("apple2", "-")
    ll.append(link3)
    assert ll.find(f=lambda x: x.id() == "apple2") == link3
    assert ll.find(f=lambda x: x.id() == "apple") == link2
    assert ll.find(f=lambda _: True, g=lambda x: [x.id()]) == {
        "apple": link2,
        "apple2": link3,
    }
    assert ll.find(f=lambda _: True, g=lambda x: ["x", x.id()]) == {
        "x": {
            "apple": link2,
            "apple2": link3,
        },
    }
    assert ll.find(f=lambda _: True, g=lambda x: ["x", "y", x.id()]) == {
        "x": {
            "y": {
                "apple": link2,
                "apple2": link3,
            },
        },
    }
    assert ll.find(f=lambda _: True, g=lambda x: [x.id(), "x"]) == {
        "apple": {"x": link2},
        "apple2": {"x": link3},
    }

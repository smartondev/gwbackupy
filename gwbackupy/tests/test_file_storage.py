import datetime
import os
import tempfile
import time
from os.path import exists

from gwbackupy.storage.file_storage import FileStorage, FileLink
from gwbackupy.storage.storage_interface import LinkInterface


def test_find_empty():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        assert len(fs.find()) == 0


def test_link_put_and_get():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("testid", "json", None)
        assert fs.put(link, "data")
        with fs.get(link) as f:
            assert f.read() == b"data"
        links = fs.find()
        assert len(links) == 1
        assert links[0] == link


def test_link_put_and_get_spec_characters():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("test/i\\d%", "json", None)
        assert fs.put(link, "data")
        with fs.get(link) as f:
            assert f.read() == b"data"
        links = fs.find()
        assert len(links) == 1
        assert links[0] == link


def test_link_put_not_supported_data():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("testid", "json", None)
        assert not fs.put(link, {})


def test_link_put_string():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("testid", "json", None)
        assert fs.put(link, "data")
        assert exists(link.get_file_path())
        with open(link.get_file_path(), "rb") as f:
            assert f.read() == bytes("data", "utf-8")


def test_link_put_string_spec_character():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("test/id%", "json", None)
        assert fs.put(link, "data")
        assert exists(link.get_file_path())
        with open(link.get_file_path(), "rb") as f:
            assert f.read() == bytes("data", "utf-8")
        assert not exists(os.path.join(temproot, "test"))

        link2 = fs.new_link("test\\id%", "json", None)
        assert fs.put(link2, "data")
        assert exists(link2.get_file_path())
        with open(link2.get_file_path(), "rb") as f:
            assert f.read() == bytes("data", "utf-8")
        assert not exists(os.path.join(temproot, "test"))


def test_link_put_callback():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("testid", "json", None)
        assert fs.put(link, lambda x: x.write(bytes("data", "utf-8")))
        assert exists(link.get_file_path())
        with open(link.get_file_path(), "rb") as f:
            assert f.read() == bytes("data", "utf-8")


def test_link_put_bytes():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("testid", "json", None)
        assert fs.put(link, bytes("data", "utf-8"))
        assert exists(link.get_file_path())
        with open(link.get_file_path(), "rb") as f:
            assert f.read() == bytes("data", "utf-8")


def test_link_put_io_bufferedreader():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("testid", "json", None)
        tmp = tempfile.NamedTemporaryFile(delete=False)
        try:
            tmp.write(bytes("data", "utf-8"))
            tmp.close()
            assert fs.put(link, open(tmp.name, "rb"))
            assert exists(link.get_file_path())
            with open(link.get_file_path(), "rb") as f:
                assert f.read() == bytes("data", "utf-8")
        finally:
            os.remove(tmp.name)


def test_mutations():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("testid", "json", None)
        assert fs.put(link, "data")
        time.sleep(0.002)
        link2 = fs.new_link("testid", "json", None)
        assert fs.put(link2, "data2")
        with fs.get(link) as f:
            assert f.read() == b"data"
        with fs.get(link2) as f:
            assert f.read() == b"data2"
        links = fs.find()
        assert len(links) == 2
        assert link in links
        assert link2 in links
        assert fs.remove(link2)
        links = fs.find()
        assert len(links) == 3
        assert link in links
        assert link2 in links
        deleted_found = False
        for link in links:
            link: LinkInterface
            if link.is_deleted():
                assert not deleted_found
                deleted_found = True
        assert deleted_found


def test_link_remove_permanently():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("testid", "json", None)
        assert fs.put(link, "data")
        assert fs.remove(link, as_new_mutation=False)
        assert not exists(link.get_file_path())


def test_link_remove():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("testid", "json", None)
        assert fs.put(link, "data")
        time.sleep(0.002)
        assert fs.remove(link)
        assert exists(link.get_file_path())
        links = fs.find()
        assert len(links) == 2
        link_scanned = links.find(f=lambda link: link.id() == "testid")
        assert link_scanned is not None
        assert link_scanned.is_deleted()


def test_find_not_valid_files():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        with open(os.path.join(temproot, ".gitignore"), "w") as f:
            f.write("a")
        with open(os.path.join(temproot, "invalid"), "w") as f:
            f.write("b")
        with open(os.path.join(temproot, "without-extension."), "w") as f:
            f.write("c")
        links = fs.find()
        assert len(links) == 0


def test_find_with_spec_character():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        tmp = os.path.join(temproot, "%252f%2f%5c.json")
        with open(tmp, "w") as f:
            f.write("a")
        links = fs.find()
        assert len(links) == 1
        assert exists(tmp)
        assert links[0].id() == "%2f/\\"


def test_find_with_tempfile():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)

        # tempfile remove test
        tmp = os.path.join(temproot, "any.tmp")
        with open(tmp, "w") as f:
            f.write("a")
        links = fs.find()
        assert len(links) == 0
        assert not exists(tmp)

        # tempfile remove fail test, work only in windows???
        # tmp2 = os.path.join(temproot, "any2.tmp")
        # with open(tmp2, "w") as f:
        #     f.write("a")
        #     links = fs.find()
        #     assert len(links) == 0
        # assert exists(tmp2)


def test_find_without_properties():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        with open(os.path.join(temproot, "testid.ext"), "w") as f:
            f.write("a")
        links = fs.find()
        assert len(links) == 1
        assert len(links[0].get_properties()) == 0


def test_link_set_properties():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("test", "ext")
        link.set_properties({"my": "value"})
        assert link.get_property("my") == "value"
        fs.put(link, "data")
        links = fs.find()
        assert links[0].get_property("my") == "value"


def test_eq():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("test", "ext")
        assert link != 4
        link2 = fs.new_link("test2", "ext")
        assert link != link2
        time.sleep(0.002)
        link3 = fs.new_link("test", "ext")
        assert link != link3


def test_subdirs():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("test", "ext", datetime.datetime.now().timestamp())
        assert os.path.dirname(link.get_file_path()) != temproot
        assert os.path.dirname(link.get_file_path()).startswith(temproot)


def test_remove_permanently_fail():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("test", "ext")
        fs.put(link, "data")
        # work only in windows ??
        # with open(link.get_file_path(), "w") as f:
        #     assert not fs.remove(link, as_new_mutation=False)


def test_remove_fail():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("test", "ext")
        fs.put(link, "data")
        os.remove(link.get_file_path())
        assert not fs.remove(link)


def test_link_props():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("test", "ext")
        assert not link.is_metadata()
        assert not link.is_object()
        link.set_properties({LinkInterface.property_metadata: True})
        assert link.is_metadata()
        assert not link.is_object()
        link.set_properties({LinkInterface.property_object: True})
        assert link.is_metadata()
        assert link.is_object()
        assert link.get_property(LinkInterface.property_object) is True
        assert link.get_property("not-exists") is None
        assert link.get_property("not-exists", 33) is 33

        link.set_properties({LinkInterface.property_object: True}, replace=True)
        assert not link.is_metadata()
        assert link.is_object()


def test_storage_modify():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("test", "ext")
        fs.put(link, "d1234")
        link2 = fs.new_link("test", "ext2")
        assert fs.modify(link, link2)
        with fs.get(link2) as f:
            assert f.read() == b"d1234"
        try:
            with fs.get(link) as f:
                assert False
        except FileNotFoundError:
            assert True
        links = fs.find()
        assert len(links) == 1
        assert links[0] == link2


def test_storage_modify_fail():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        # not exists
        link = fs.new_link("test", "ext")
        print(link.get_file_path())
        link2 = fs.new_link("test", "ext2")
        print(link2.get_file_path())
        assert not fs.modify(link, link2)
        links = fs.find()
        assert len(links) == 0

        # already exists
        fs.put(link, "d1")
        fs.put(link2, "d2")
        assert not fs.modify(link, link2)


def test_content_hash():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("test", "ext")
        fs.put(link, "d1234")
        assert fs.content_hash_check(link) is None
        new_link = fs.content_hash_add(link)
        assert fs.content_hash_check(new_link) is True
        chash = new_link.get_property(LinkInterface.property_content_hash)
        assert chash is not None
        with fs.get(new_link) as f:
            assert chash == fs.content_hash_generate(f)
        fs.put(new_link, "a1234")
        assert fs.content_hash_check(new_link) is False

        link3 = fs.new_link("test123", "ext2")
        link3.set_properties(
            {LinkInterface.property_content_hash: fs.content_hash_generate("a1234")}
        )
        fs.put(link3, "a1234")
        assert fs.content_hash_check(link3) is True

        link4 = fs.new_link("test4", "ext2")
        assert fs.content_hash_eq(link4, "cccc") is False


def test_content_hash_add_fail():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("test", "ext")
        fs.put(link, "d1234")
        os.remove(link.get_file_path())
        try:
            new_link = fs.content_hash_add(link)
            assert False
        except FileNotFoundError:
            assert True


def test_content_hash_check_fail():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("test", "ext")
        fs.put(link, "d1234")
        new_link = fs.content_hash_add(link)
        os.remove(new_link.get_file_path())
        try:
            fs.content_hash_check(new_link)
            assert False
        except FileNotFoundError:
            assert True


def test_generate_content_hash():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        assert fs.content_hash_generate("a1234") == "m828c88f34ecb4c1ca8d89e018c6fad1a"
        assert (
            fs.content_hash_generate(bytes("a1234", "utf-8"))
            == "m828c88f34ecb4c1ca8d89e018c6fad1a"
        )
        link = fs.new_link("test", "ext")
        fs.put(link, "a1234")
        assert (
            fs.content_hash_generate(fs.get(link))
            == "m828c88f34ecb4c1ca8d89e018c6fad1a"
        )
        try:
            fs.content_hash_generate({})
            assert False
        except RuntimeError as e:
            assert str(e).startswith("Invalid type: ")


def test_file_link_escape():
    assert FileLink.escape("a1234") == "a1234"
    assert FileLink.escape("a/a") == "a%2fa"
    assert FileLink.escape("a%/a") == "a%25%2fa"
    assert FileLink.escape("a%2f/a") == "a%252f%2fa"
    assert FileLink.escape("a\\a") == "a%5ca"
    assert FileLink.escape("a%5c%2f\\a") == "a%255c%252f%5ca"
    assert FileLink.escape("a=a") == "a%3da"
    assert FileLink.escape("a.a") == "a%2ea"


def test_file_link_unescape():
    assert FileLink.unescape("a1234") == "a1234"
    assert FileLink.unescape("a%2fa") == "a/a"
    assert FileLink.unescape("a%25%2fa") == "a%/a"
    assert FileLink.unescape("a%252f%2fa") == "a%2f/a"
    assert FileLink.unescape("a%5ca") == "a\\a"
    assert FileLink.unescape("a%255c%252f%5ca") == "a%5c%2f\\a"
    assert FileLink.unescape("a%3da") == "a=a"
    assert FileLink.unescape("a%2ea") == "a.a"

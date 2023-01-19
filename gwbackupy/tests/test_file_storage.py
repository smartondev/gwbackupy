import datetime
import io
import os
import tempfile
import time
from os.path import exists

from gwbackupy.storage.file_storage import FileStorage


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
        with open(os.path.join(temproot, "without-extension"), "w") as f:
            f.write("b")
        links = fs.find()
        assert len(links) == 0


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

        # tempfile remove fail test
        tmp2 = os.path.join(temproot, "any2.tmp")
        with open(tmp2, "w") as f:
            f.write("a")
            links = fs.find()
            assert len(links) == 0
        assert exists(tmp2)


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
        with open(link.get_file_path(), "w") as f:
            assert not fs.remove(link, as_new_mutation=False)


def test_remove_fail():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("test", "ext")
        fs.put(link, "data")
        os.remove(link.get_file_path())
        assert not fs.remove(link)

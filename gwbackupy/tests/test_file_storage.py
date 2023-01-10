import tempfile
import time

from gwbackupy.storage.file_storage import FileStorage


def test_find_empty():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        assert len(fs.find()) == 0


def test_link_create_and_get():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("testid", "json", None)
        assert fs.put(link, "data")
        with fs.get(link) as f:
            assert f.read() == b"data"
        links = fs.find()
        assert len(links) == 1
        assert links[0] == link


def test_mutations():
    with tempfile.TemporaryDirectory(prefix="myapp-") as temproot:
        fs = FileStorage(root=temproot)
        link = fs.new_link("testid", "json", None)
        assert fs.put(link, "data")
        time.sleep(1)
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

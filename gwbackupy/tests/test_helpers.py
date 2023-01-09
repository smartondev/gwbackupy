from gwbackupy.helpers import str_trim


def test_str_trim():
    assert str_trim("aa", 2, "+") == "aa"
    assert str_trim("aaa", 2, "+") == "aa+"
    assert str_trim("cccc", 2, "+") == "cc+"
    assert str_trim("abcd", 1, "+") == "a+"

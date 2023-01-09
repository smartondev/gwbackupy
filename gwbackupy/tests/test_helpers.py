from gwbackupy.helpers import str_trim, decode_base64url


def test_str_trim():
    assert str_trim("aa", 2, "+") == "aa"
    assert str_trim("aaa", 2, "+") == "aa+"
    assert str_trim("cccc", 2, "+") == "cc+"
    assert str_trim("abcd", 1, "+") == "a+"


def test_decode_base64url():
    assert decode_base64url("YQ") == b"a"
    assert decode_base64url("YjY0") == b"b64"

import io

from gwbackupy.helpers import str_trim, decode_base64url, encode_base64url, json_load


def test_str_trim():
    assert str_trim("aa", 2, "+") == "aa"
    assert str_trim("aaa", 2, "+") == "aa+"
    assert str_trim("cccc", 2, "+") == "cc+"
    assert str_trim("abcd", 1, "+") == "a+"


def test_decode_base64url():
    assert decode_base64url("YQ") == b"a"
    assert decode_base64url("YjY0") == b"b64"


def test_encode_base64url():
    assert encode_base64url(b"a") == "YQ"
    assert encode_base64url(b"b64") == "YjY0"


def test_json_load():
    assert json_load(io.BytesIO(b'{"a": 1}')) == {"a": 1}
    assert json_load(io.BytesIO(b'{"a": 1, "b":}')) is None

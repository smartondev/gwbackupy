import copy
import io
import json
from datetime import datetime, timezone

from googleapiclient.errors import HttpError

from gwbackupy.helpers import (
    str_trim,
    decode_base64url,
    encode_base64url,
    json_load,
    parse_date,
    is_rate_limit_exceeded,
)


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


def test_parse_date():
    assert parse_date("2020-01-01", timezone.utc) == datetime(
        2020, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc
    )
    assert parse_date("2022-12-28 18:03:01", timezone.utc) == datetime(
        2022, 12, 28, 18, 3, 1, 0, tzinfo=timezone.utc
    )
    d = "not a date"
    try:
        parse_date(d, timezone.utc)
    except ValueError as e:
        assert str(e) == f"Date time parsing failed: {d}"


class Resp:
    def __init__(self, status, reason):
        self.status = status
        self.reason = reason


def test_is_rate_limit_exceeded():
    assert not is_rate_limit_exceeded(Exception("error"))
    data = [
        {
            "error": {
                "message": "ignore",
                "details": [
                    {
                        "domain": "usageLimits",
                        "reason": "rateLimitExceeded",
                    }
                ],
            }
        }
    ]
    e = HttpError(Resp(403, "Forbidden"), json.dumps(data).encode("utf8"))
    assert is_rate_limit_exceeded(e)
    e = HttpError(Resp(401, "Forbidden"), json.dumps(data).encode("utf8"))
    assert not is_rate_limit_exceeded(e)
    data2 = copy.deepcopy(data)
    data2[0]["error"]["details"][0]["domain"] = "-"
    e = HttpError(Resp(403, "Forbidden"), json.dumps(data2).encode("utf8"))
    assert not is_rate_limit_exceeded(e)
    data2 = copy.deepcopy(data)
    data2[0]["error"]["details"][0]["reason"] = "-"
    e = HttpError(Resp(403, "Forbidden"), json.dumps(data2).encode("utf8"))
    assert not is_rate_limit_exceeded(e)
    data2 = copy.deepcopy(data)
    data2[0]["error"]["details"].append(dict())
    e = HttpError(Resp(403, "Forbidden"), json.dumps(data2).encode("utf8"))
    assert not is_rate_limit_exceeded(e)

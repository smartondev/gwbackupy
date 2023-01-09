from __future__ import annotations

import base64
from datetime import datetime
import json
import logging
from json import JSONDecodeError
from typing import IO

import tzlocal
from googleapiclient.errors import HttpError


def str_trim(text, length, postfix="..."):
    if len(text) > length:
        text = text[:length] + postfix
    return text


def decode_base64url(data):
    padding = 4 - (len(data) % 4)
    data = data + ("=" * padding)
    return base64.urlsafe_b64decode(data)


def encode_base64url(data):
    return base64.urlsafe_b64encode(data).decode("utf-8").replace("=", "")


def parse_date(date: str, tz: tzlocal) -> datetime:
    try:
        return datetime.strptime(date, "%Y-%m-%d %H:%M:%S").astimezone(tz)
    except ValueError:
        try:
            return datetime.strptime(
                f"{date} 00:00:00", "%Y-%m-%d %H:%M:%S"
            ).astimezone(tz)
        except ValueError:
            raise ValueError(f"Date time parsing failed: {date}")


def json_load(io: IO[bytes]) -> list[any] | dict[str, any] | None:
    try:
        return json.load(io)
    except JSONDecodeError as e:
        logging.exception(f"Invalid JSON format: {e}")
    except BaseException as e:
        logging.exception(f"JSON load error: {e}")
    return None


def is_rate_limit_exceeded(e) -> bool:
    if not isinstance(e, HttpError):
        return False
    e: HttpError
    if e.status_code != 403:
        return False
    d = e.error_details
    if not isinstance(d, list):
        return False
    if len(d) != 1:
        return False
    item = d[0]
    return (
        item.get("domain") == "usageLimits"
        and item.get("reason") == "rateLimitExceeded"
    )
from __future__ import annotations

import base64
import random
import string
from datetime import datetime
import json
import logging
from json import JSONDecodeError
from typing import IO

import tzlocal
from googleapiclient.errors import HttpError


def str_trim(text, length, postfix="..."):
    """
    Trim a string to a specified length, and add a postfix if the string is longer than the specified length.
    :param text: the string to be trimmed
    :param length: the maximum length of the string
    :param postfix: the postfix to add if the string is longer than the specified length (default is "...")
    :return: the trimmed string
    """
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
    """
    Parse a date string and return a datetime object with the corresponding timezone.
    :param date: string representing a date in the format "YYYY-MM-DD" or 'YYYY-MM-DD hh:mm:ss'
    :param tz: timezone to be set for the returned datetime object
    :return: datetime object with the corresponding timezone
    """
    tzs = datetime.now().astimezone(tz).strftime("%z")
    df = "%Y-%m-%d %H:%M:%S %z"
    try:
        return datetime.strptime(f"{date} {tzs}", df).astimezone(tz)
    except ValueError:
        try:
            return datetime.strptime(f"{date} 00:00:00 {tzs}", df).astimezone(tz)
        except ValueError:
            raise ValueError(f"Date time parsing failed: {date}")


def json_load(io: IO[bytes]) -> list[any] | dict[str, any] | None:
    try:
        return json.load(io)
    except JSONDecodeError as e:
        logging.exception(f"Invalid JSON format: {e}")
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


def random_string(length: int = 8) -> str:
    return "".join(random.choice(string.ascii_lowercase) for _ in range(length))

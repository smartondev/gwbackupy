from __future__ import annotations

import logging
import signal
import threading
import time
from concurrent.futures import Future
from datetime import datetime

is_killed_handling: bool = False
is_killed_value: bool = False
is_killed_lock = threading.RLock()


def is_killed_reset():
    global is_killed_lock
    with is_killed_lock:
        global is_killed_value
        is_killed_value = False


def is_killed() -> bool:
    """
    Check the process is has killed request or not.
    This function handling the signal.SIGINT and signal.SIGTERM signals, and injectable directly by is_killed_value.
    """
    global is_killed_lock
    with is_killed_lock:
        global is_killed_handling
        if not is_killed_handling:
            signal.signal(signal.SIGINT, is_killed_handling_func)
            signal.signal(signal.SIGTERM, is_killed_handling_func)
            is_killed_handling = True
        global is_killed_value
        return is_killed_value


def is_killed_handling_func(*args):
    global is_killed_lock
    with is_killed_lock:
        global is_killed_value
        logging.info("Handle kill signal")
        is_killed_value = True


def sleep_kc(seconds: float, sleep_step: float = 0.1) -> bool:
    """
    Sleep for seconds and return True. If is_killed() is True, then stop it immediately, and return False.
    :param seconds: number of seconds to sleep
    :param sleep_step: minimum sleep between kill signal checking (Default is 0.1s)
    """
    start = datetime.now().timestamp()
    while datetime.now().timestamp() - start < seconds:
        time.sleep(sleep_step)
        if is_killed():
            return False
    return True


def await_all_futures(futures: list[Future], sleep_step: float = 0.1) -> bool:
    """
    Wait for all futures to complete.
    If is_killed() is True, then return from this function with False, otherwise return True.
    :param futures: a list of concurrent.futures.Future objects
    :param sleep_step: time to wait between each check
    :return: True if all futures are done, False otherwise
    """
    while not is_killed():
        if not sleep_kc(1, sleep_step=sleep_step):
            return False
        has_not_done = False
        for f in futures:
            if not f.done():
                has_not_done = True
                break
        if has_not_done:
            continue
        else:
            break
    return not is_killed()

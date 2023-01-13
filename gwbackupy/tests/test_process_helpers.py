import concurrent.futures
import threading
from datetime import datetime
from time import sleep

from gwbackupy.process_helpers import (
    sleep_with_check,
    is_killed,
    is_killed_reset,
    is_killed_handling_func,
    await_all_futures,
)


def test_sleep_with_check():
    assert not is_killed()
    start = datetime.now().timestamp()
    sleep_with_check(0.3, sleep_step=0.05)
    end = datetime.now().timestamp()
    assert end - start < 1
    assert end - start >= 0.3
    assert not is_killed()


def do_kill(seconds: float = 0.3):
    sleep(seconds)
    is_killed_handling_func()


def test_sleep_with_check_with_kill():
    assert not is_killed()
    try:
        _thread = threading.Thread(target=do_kill)
        _thread.start()
        start = datetime.now().timestamp()
        sleep_with_check(10, sleep_step=0.05)
        end = datetime.now().timestamp()
        assert end - start < 0.5
        assert end - start >= 0.3
        assert is_killed()
    finally:
        is_killed_reset()


def test_is_killed_reset():
    assert not is_killed()
    try:
        is_killed_handling_func()
        assert is_killed()
    finally:
        is_killed_reset()
    assert not is_killed()


def test_await_all_futures():
    assert not is_killed()
    try:
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        futures = []
        start = datetime.now().timestamp()
        for i in range(3):
            futures.append(executor.submit(lambda x: sleep(0.1)))
        assert await_all_futures(futures, sleep_step=0.05)
        end = datetime.now().timestamp()
        assert end - start >= 0.3
        assert end - start < 3

        futures.clear()
        start = datetime.now().timestamp()
        for i in range(3):
            futures.append(executor.submit(lambda x: sleep(10)))
        _thread = threading.Thread(target=do_kill)
        _thread.start()
        assert not await_all_futures(futures)
        end = datetime.now().timestamp()
        assert end - start >= 0.3
        assert end - start < 3
        is_killed_reset()
    finally:
        is_killed_reset()

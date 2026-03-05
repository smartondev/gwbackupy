from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager


class AdaptiveBatchController:
    """Controls concurrency using AIMD (Additive Increase / Multiplicative Decrease).

    Uses a Condition + active counter to throttle concurrent API calls.
    - Additive increase: +1 on slot release if enough time passed without rate limit errors
    - Multiplicative decrease: reduce concurrency on rate limit error (minimum: initial_size)
    - Decrease cooldown: ignores rapid-fire rate limit errors within `decrease_cooldown` seconds
    """

    def __init__(
        self,
        initial_size: int,
        max_size: int | None = None,
        increase_interval: float = 30.0,
        decrease_factor: float = 0.75,
        decrease_cooldown: float = 5.0,
    ):
        if initial_size < 1:
            initial_size = 1
        self._current_size = initial_size
        self._min_size = initial_size
        self._max_size = max_size if max_size is not None else max(initial_size * 4, 50)
        self._increase_interval = increase_interval
        self._decrease_factor = decrease_factor
        self._decrease_cooldown = decrease_cooldown
        self._cond = threading.Condition(threading.RLock())
        self._active = 0
        self._last_rate_limit_time: float = 0
        self._last_decrease_time: float = 0
        self._last_increase_time: float = 0

    @property
    def current_size(self) -> int:
        with self._cond:
            return self._current_size

    @property
    def max_size(self) -> int:
        return self._max_size

    @contextmanager
    def slot(self):
        """Context manager: acquire a concurrency slot before work, release after."""
        with self._cond:
            while self._active >= self._current_size:
                self._cond.wait()
            self._active += 1
        try:
            yield
        finally:
            with self._cond:
                self._active -= 1
                self._cond.notify()
            self._try_increase()

    def on_rate_limit(self):
        """Called when a rate limit error is detected. Reduces concurrency."""
        with self._cond:
            now = time.monotonic()
            self._last_rate_limit_time = now
            if now - self._last_decrease_time < self._decrease_cooldown:
                return
            old_size = self._current_size
            new_size = max(
                self._min_size, int(self._current_size * self._decrease_factor)
            )
            if new_size < old_size:
                self._current_size = new_size
                self._last_decrease_time = now
                logging.debug(
                    f"Auto-batch: decreased concurrency from {old_size} to {new_size}"
                )

    def _try_increase(self):
        """Attempt to increase concurrency by 1 if enough time passed without rate limits."""
        with self._cond:
            now = time.monotonic()
            if now - self._last_increase_time < self._increase_interval:
                return
            if self._last_rate_limit_time > 0 and (
                now - self._last_rate_limit_time < self._increase_interval
            ):
                return
            if self._current_size >= self._max_size:
                return
            self._current_size += 1
            self._last_increase_time = now
            self._cond.notify()
            logging.debug(f"Auto-batch: increased concurrency to {self._current_size}")

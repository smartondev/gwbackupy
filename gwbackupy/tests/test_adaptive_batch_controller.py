import threading
import time

from gwbackupy.adaptive_batch_controller import AdaptiveBatchController


def test_initial_size():
    controller = AdaptiveBatchController(initial_size=5)
    assert controller.current_size == 5


def test_initial_size_minimum():
    controller = AdaptiveBatchController(initial_size=0)
    assert controller.current_size == 1


def test_max_size_default():
    controller = AdaptiveBatchController(initial_size=5)
    assert controller.max_size == max(5 * 4, 50)


def test_max_size_custom():
    controller = AdaptiveBatchController(initial_size=5, max_size=10)
    assert controller.max_size == 10


def test_on_rate_limit_decreases():
    controller = AdaptiveBatchController(initial_size=10, decrease_cooldown=0)
    controller.on_rate_limit()
    assert controller.current_size == 10  # can't go below initial_size


def test_on_rate_limit_minimum_boundary():
    controller = AdaptiveBatchController(initial_size=1, decrease_cooldown=0)
    controller.on_rate_limit()
    assert controller.current_size == 1  # can't go below initial_size


def test_on_rate_limit_after_increase():
    """Decrease works when current_size is above initial_size."""
    controller = AdaptiveBatchController(
        initial_size=5, max_size=20, decrease_cooldown=0, increase_interval=0
    )
    # Increase to 10
    for _ in range(5):
        controller._try_increase()
    assert controller.current_size == 10
    controller.on_rate_limit()
    assert controller.current_size == 7  # int(10 * 0.75)


def test_on_rate_limit_cooldown():
    """Rapid-fire rate limits only cause one decrease within cooldown period."""
    controller = AdaptiveBatchController(
        initial_size=5, max_size=40, decrease_cooldown=5.0, increase_interval=0
    )
    # Increase to 20
    for _ in range(15):
        controller._try_increase()
    assert controller.current_size == 20
    # First rate limit: 20 -> 15 (int(20 * 0.75))
    controller.on_rate_limit()
    assert controller.current_size == 15
    # Rapid subsequent calls within cooldown: no further decrease
    controller.on_rate_limit()
    assert controller.current_size == 15
    controller.on_rate_limit()
    assert controller.current_size == 15


def test_slot_context_manager():
    controller = AdaptiveBatchController(initial_size=2)
    acquired = []

    def worker():
        with controller.slot():
            acquired.append(True)
            time.sleep(0.05)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    assert len(acquired) == 4


def test_slot_respects_decreased_concurrency():
    """After a rate limit decrease, concurrency is properly limited."""
    controller = AdaptiveBatchController(
        initial_size=2, max_size=10, decrease_cooldown=0, increase_interval=0
    )
    # Increase to 4
    controller._try_increase()
    controller._try_increase()
    assert controller.current_size == 4
    controller.on_rate_limit()
    assert controller.current_size == 3  # int(4 * 0.75)
    # Verify we can acquire exactly 3 slots concurrently
    results = []

    def worker():
        with controller.slot():
            results.append(True)

    threads = [threading.Thread(target=worker) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    assert len(results) == 3


def test_try_increase():
    controller = AdaptiveBatchController(
        initial_size=3, max_size=5, increase_interval=0
    )
    # No rate limits, should increase
    controller._try_increase()
    assert controller.current_size == 4
    controller._try_increase()
    assert controller.current_size == 5
    # At max, should not increase
    controller._try_increase()
    assert controller.current_size == 5


def test_try_increase_blocked_by_recent_rate_limit():
    controller = AdaptiveBatchController(
        initial_size=5, max_size=20, increase_interval=0.01, decrease_cooldown=0
    )
    # Increase to 10 (small delays to pass increase interval)
    for _ in range(5):
        time.sleep(0.015)
        controller._try_increase()
    assert controller.current_size == 10
    controller.on_rate_limit()
    assert controller.current_size == 7  # int(10 * 0.75)
    # Try increase immediately — blocked because rate limit was within increase_interval
    controller._try_increase()
    assert controller.current_size == 7  # no increase


def test_slot_triggers_increase():
    """Slot release triggers concurrency increase when conditions are met."""
    controller = AdaptiveBatchController(
        initial_size=2, max_size=5, increase_interval=0.0
    )
    with controller.slot():
        pass
    assert controller.current_size == 3


def test_decrease_factor_custom():
    controller = AdaptiveBatchController(
        initial_size=5,
        max_size=20,
        decrease_factor=0.75,
        decrease_cooldown=0,
        increase_interval=0,
    )
    # Increase to 12
    for _ in range(7):
        controller._try_increase()
    assert controller.current_size == 12
    controller.on_rate_limit()
    assert controller.current_size == 9  # int(12 * 0.75)

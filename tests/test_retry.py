from utils.retry import calculate_delay


def test_calculate_delay_is_bounded_without_jitter():
    delay = calculate_delay(attempt=10, base_delay=2.0, max_delay=5.0, jitter=False)
    assert delay == 5.0


def test_calculate_delay_exponential_without_jitter():
    delay = calculate_delay(attempt=3, base_delay=1.5, max_delay=20.0, jitter=False)
    assert delay == 6.0

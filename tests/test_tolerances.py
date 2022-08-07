import pytest
from chaoslib.exceptions import ActivityFailed

from chaospixie.tolerances import (
    group_values,
    median_should_be_above,
    median_should_be_below,
    percentile_should_be_above,
    percentile_should_be_below,
)


def test_median_should_be_below():
    assert (
        median_should_be_below(
            "latency",
            1.0,
            value=[
                {"latency": 0.5},
                {"latency": 0.8},
                {"latency": 0.9},
            ],
        )
        is True
    )


def test_median_should_be_above():
    assert (
        median_should_be_above(
            "latency",
            1.0,
            value=[
                {"latency": 0.5},
                {"latency": 0.8},
                {"latency": 0.9},
            ],
        )
        is False
    )


def test_percentile_should_be_below():
    assert (
        percentile_should_be_below(
            "latency",
            1.0,
            99,
            value=[
                {"latency": 0.5},
                {"latency": 0.8},
                {"latency": 0.9},
            ],
        )
        is True
    )


def test_percentile_should_be_above():
    assert (
        percentile_should_be_above(
            "latency",
            1.0,
            99,
            value=[
                {"latency": 0.5},
                {"latency": 0.8},
                {"latency": 0.9},
            ],
        )
        is False
    )


def test_median_should_be_below_fails_with_empty_dataset():
    with pytest.raises(ActivityFailed):
        median_should_be_below("latency", 1.0, value=[])


def test_median_should_be_above_fails_with_empty_dataset():
    with pytest.raises(ActivityFailed):
        median_should_be_above("latency", 1.0, value=[])


def test_percentile_should_be_below_fails_with_empty_dataset():
    with pytest.raises(ActivityFailed):
        percentile_should_be_below("latency", 1.0, 99, value=[])


def test_percentile_should_be_above_fails_with_empty_dataset():
    with pytest.raises(ActivityFailed):
        percentile_should_be_above("latency", 1.0, 99, value=[])


def test_group_values_with_target():
    values = [
        {"latency": 0.5, "pod": "/consumer/1"},
        {"latency": 0.8, "pod": "/consumer/2"},
        {"something": 0.8, "pod": "/consumer/2"},
        {"latency": 0.9, "pod": "/producer/3"},
    ]
    assert group_values(values, "latency", ("pod", "/consumer.*")) == [0.5, 0.8]


def test_group_values_convert_to_seconds():
    values = [
        {"latency": 5 * 1e9, "pod": "/consumer/1"},
    ]
    assert group_values(values, "latency", None, "seconds") == [5]


def test_group_values_convert_to_milliseconds():
    values = [
        {"latency": 5 * 1e9, "pod": "/consumer/1"},
    ]
    assert group_values(values, "latency", None, "milliseconds") == [5 * 1e3]


def test_group_values_convert_to_microseconds():
    values = [
        {"latency": 5 * 1e9, "pod": "/consumer/1"},
    ]
    assert group_values(values, "latency", None, "microseconds") == [5 * 1e6]

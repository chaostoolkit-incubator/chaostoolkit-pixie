import re
from statistics import StatisticsError, median, quantiles
from typing import Any, Dict, List, Literal, Tuple

from chaoslib.exceptions import ActivityFailed
from logzero import logger

__all__ = [
    "median_should_be_below",
    "median_should_be_above",
    "percentile_should_be_below",
    "percentile_should_be_above",
]


def median_should_be_below(
    column: str,
    treshold: float,
    convert_from_nanoseconds: Literal[
        "seconds", "milliseconds", "microseconds"
    ] = None,
    target: Tuple[str, str] = None,
    value: List[Dict[str, Any]] = None,
) -> bool:
    """
    Compute the median of all the `column` in the list of results. If you need
    to limit the computation to a specific dataset within the results, you
    can provide the `target` as a tuple such as `(key, value)`. The `value` can
    be a fixed value or a regular expression to match many.

    Sometimes the column's value type is in nanoseconds, which isn't always
    easy to make sense of. You can set the
    `convert_from_nanoseconds` flag so we automatically convert
    to seconds the value. In that case, the threshold must also be in seconds.
    The `convert_from_nanoseconds` flag can be: `"seconds"`, `"milliseconds"`
    or `"microseconds"`.

    Return true if the median is below (or equal) to the threshold you
    provide.
    """
    values = group_values(value, column, target, convert_from_nanoseconds)
    logger.debug(f"Found values: {values}")

    try:
        m = median(values)
    except StatisticsError:
        logger.debug("Fziled to compute median", exc_info=True)
        raise ActivityFailed("failed to compute median")

    logger.debug(f"median of '{column}' returned: {m}")
    return m <= treshold


def median_should_be_above(
    column: str,
    treshold: float,
    target: Tuple[str, str] = None,
    convert_from_nanoseconds: Literal[
        "seconds", "milliseconds", "microseconds"
    ] = None,
    value: List[Dict[str, Any]] = None,
) -> bool:
    """
    Compute the median of all the `column` in the list of results. If you need
    to limit the computation to a specific dataset within the results, you
    can provide the `target` as a tuple such as `(key, value)`. The `value` can
    be a fixed value or a regular expression to match many.

    Sometimes the column's value type is in nanoseconds, which isn't always
    easy to make sense of. You can set the
    `convert_from_nanoseconds_to_seconds` flag so we automatically convert
    to seconds the value. In that case, the threshold mus also be in seconds.

    Return true if the median is above (or equal) to the threshold you
    provide.
    """
    values = group_values(value, column, target, convert_from_nanoseconds)
    logger.debug(f"Found values: {values}")

    try:
        m = median(values)
    except StatisticsError:
        logger.debug("Fziled to compute median", exc_info=True)
        raise ActivityFailed("failed to compute median")

    logger.debug(f"median of '{column}' returned: {m}")
    return m >= treshold


def percentile_should_be_below(
    column: str,
    treshold: float,
    percentile: int = 99,
    target: Tuple[str, str] = None,
    convert_from_nanoseconds: Literal[
        "seconds", "milliseconds", "microseconds"
    ] = None,
    value: List[Dict[str, Any]] = None,
) -> bool:
    """
    Compute the percentiles of all the `column` in the list of results. The
    default returned percentile is the 99-percentile. If you need
    to limit the computation to a specific dataset within the results, you
    can provide the `target` as a tuple such as `(key, value)`.
    The `value` can be a fixed value or a regular expression to match many.

    Sometimes the column's value type is in nanoseconds, which isn't always
    easy to make sense of. You can set the
    `convert_from_nanoseconds_to_seconds` flag so we automatically convert
    to seconds the value. In that case, the threshold mus also be in seconds.

    Return true if the percentile is below (or equal) to the threshold you
    provide.
    """
    values = group_values(value, column, target, convert_from_nanoseconds)
    logger.debug(f"Found values: {values}")

    try:
        q = quantiles(values, n=100)
        logger.debug(f"percentiles (length={len(q)}): {q}")
        q = q[percentile - 1]
    except StatisticsError:
        logger.debug("Fziled to compute percentiles", exc_info=True)
        raise ActivityFailed("failed to compute percentiles")

    logger.debug(f"p{percentile} of '{column}' returned: {q}")
    return q <= treshold


def percentile_should_be_above(
    column: str,
    treshold: float,
    percentile: int = 99,
    target: Tuple[str, str] = None,
    convert_from_nanoseconds: Literal[
        "seconds", "milliseconds", "microseconds"
    ] = None,
    value: List[Dict[str, Any]] = None,
) -> bool:
    """
    Compute the percentiles of all the `column` in the list of results. The
    default returned percentile is the 99-percentile. If you need
    to limit the computation to a specific dataset within the results, you
    can provide the `target` as a tuple such as `(key, value)`.
    The `value` can be a fixed value or a regular expression to match many.

    Sometimes the column's value type is in nanoseconds, which isn't always
    easy to make sense of. You can set the
    `convert_from_nanoseconds_to_seconds` flag so we automatically convert
    to seconds the value. In that case, the threshold mus also be in seconds.

    Return true if the percentile is above (or equal) to the threshold you
    provide.
    """
    values = group_values(value, column, target, convert_from_nanoseconds)
    logger.debug(f"Found values: {values}")

    try:
        q = quantiles(values, n=100)
        logger.debug(f"percentiles (length={len(q)}): {q}")
        q = q[percentile - 1]
    except StatisticsError:
        logger.debug("Fziled to compute percentiles", exc_info=True)
        raise ActivityFailed("failed to compute percentiles")

    logger.debug(f"p{percentile} of '{column}' returned: {q}")
    return q >= treshold


###############################################################################
# Private functions
###############################################################################
def group_values(
    results: List[Dict[str, Any]],
    column: str,
    target: Tuple[str, str] = None,
    convert_from_nanoseconds: Literal[
        "seconds", "milliseconds", "microseconds"
    ] = None,
) -> List[float]:
    values = []

    rgx = key = None
    if target:
        key = target[0]
        rgx = re.compile(target[1])

    for r in results:
        if key and (key in r) and rgx and (rgx.match(r[key]) is None):
            continue

        if column not in r:
            continue

        v = r[column]

        if convert_from_nanoseconds == "seconds":
            v = v / 1.0e9
        elif convert_from_nanoseconds == "milliseconds":
            v = v / 1.0e6
        elif convert_from_nanoseconds == "microseconds":
            v = v / 1.0e3

        values.append(v)
    return values

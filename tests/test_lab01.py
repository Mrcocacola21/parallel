import math

import pytest

from lab01.algorithms import (
    assert_equivalent,
    parallel_processing,
    process_value,
    sequential_processing,
    split_data,
)


def test_formula_and_split():
    assert math.isclose(
        process_value(10, 3),
        sum(math.sqrt(10 + i) * math.sin(10 + i) for i in (1, 2, 3)),
    )
    assert process_value(0, 1) == math.sin(1)
    assert split_data([1, 2, 3, 4, 5], 3) == [[1, 2], [3, 4], [5]]
    assert split_data([], 2) == [[], []]
    with pytest.raises(ValueError):
        split_data([1], 0)


@pytest.mark.parametrize("workers", [1, 2, 4, 8])
def test_spawn_and_order(workers):
    data = [42, 1, 3, 9, 7]
    assert_equivalent(
        sequential_processing(data, 7), parallel_processing(data, 7, workers)
    )


def test_length_mismatch():
    with pytest.raises(AssertionError):
        assert_equivalent([1.0], [])

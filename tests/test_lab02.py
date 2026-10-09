import pandas as pd
import pytest

from lab02.algorithms import (
    assert_equivalent,
    merge_results,
    parallel_processing,
    process_chunk,
)


def frame():
    return pd.DataFrame(
        {"Revenue": [1.0, 2.0, 100.0, 4.0, 8.0], "Country": ["A", "B", "A", "B", "A"]}
    )


def test_weighted_merge_unequal_and_empty():
    source = frame()
    parts = [source.iloc[:1], source.iloc[1:], source.iloc[:0]]
    actual = merge_results([process_chunk(part) for part in parts])
    assert actual.mean == 23
    assert_equivalent(process_chunk(source), actual)


@pytest.mark.parametrize("workers", [1, 2, 4, 8])
def test_pool_starmap(workers):
    source = frame()
    assert_equivalent(process_chunk(source), parallel_processing(source, workers))

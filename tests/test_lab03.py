import asyncio

import pandas as pd
import pytest

from common.utilities import split_frame
from lab03.algorithms import (
    analyze_chunk,
    assert_equivalent,
    async_processing,
    merge_analysis,
    pool_processing,
    threading_processing,
)


def frame():
    return pd.DataFrame(
        {
            "StockCode": ["A", "B", "A", "A", "C"],
            "CustomerID": ["1", "2", "1", None, "2"],
            "UnitPrice": [1.0, 2.0, 3.0, 5.0, 10.0],
            "Quantity": [2, 1, 3, 1, 1],
            "Revenue": [2.0, 2.0, 9.0, 5.0, 10.0],
        }
    )


@pytest.mark.parametrize("mode", ["threading", "pool2", "pool4", "pool8", "async"])
def test_sets_means_and_concurrency(mode):
    source = frame()
    chunks = split_frame(source, 4)
    if mode == "threading":
        parts = threading_processing(chunks)
    elif mode == "async":
        parts = asyncio.run(async_processing(chunks, io_delay=0.001))
    else:
        parts = pool_processing(chunks, int(mode[-1]))
    actual = merge_analysis(parts)
    assert_equivalent(analyze_chunk(source), actual)
    assert actual.summary()["unique_customers"] == 2
    assert actual.summary()["unique_products"] == 3
    assert actual.summary()["mean_price"] == 4.2


def broken_worker(_):
    raise RuntimeError("Контрольний виняток")


@pytest.mark.parametrize("mode", ["threading", "pool", "async"])
def test_exceptions_propagate(mode):
    with pytest.raises(RuntimeError, match="Контрольний"):
        if mode == "threading":
            threading_processing([1, 2], broken_worker)
        elif mode == "pool":
            pool_processing([1, 2], 2, broken_worker)
        else:
            asyncio.run(async_processing([1, 2], broken_worker))

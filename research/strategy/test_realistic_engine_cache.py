#!/usr/bin/env python3
"""Regression tests for shared-array caching in the realistic backtest engine."""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from research.strategy.realistic_engine_v1 import _get_engine_data


class EngineArrayCacheTests(unittest.TestCase):
    def make_inputs(self):
        idx = pd.date_range("2024-01-01", periods=30, freq="D")
        cols = ["AAA", "BBB"]
        close = pd.DataFrame(
            {c: np.linspace(10.0 + i, 15.0 + i, len(idx)) for i, c in enumerate(cols)},
            index=idx,
        )
        volume = pd.DataFrame(
            {c: np.arange(100.0, 100.0 + len(idx)) for c in cols},
            index=idx,
        )
        return close.copy(), (close + 0.1), (close - 0.1), close, volume

    def test_common_arrays_are_reused_for_same_dataframes(self):
        op, hp, lp, cp, vp = self.make_inputs()
        first = _get_engine_data(op, hp, lp, cp, vp)
        second = _get_engine_data(op, hp, lp, cp, vp)
        self.assertIs(first, second)
        expected_volume = vp.shift(1).rolling(20, min_periods=20).mean().to_numpy(dtype=float)
        np.testing.assert_allclose(first["avg_volume20"], expected_volume, equal_nan=True)

    def test_cache_invalidates_when_a_panel_object_changes(self):
        op, hp, lp, cp, vp = self.make_inputs()
        first = _get_engine_data(op, hp, lp, cp, vp)
        replacement_close = cp.copy()
        replacement_close.iloc[-1, 0] += 1.0
        second = _get_engine_data(op, hp, lp, replacement_close, vp)
        self.assertIsNot(first, second)
        self.assertEqual(second["ca"][-1, 0], replacement_close.iloc[-1, 0])


if __name__ == "__main__":
    unittest.main()

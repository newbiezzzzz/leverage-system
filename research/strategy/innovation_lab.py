#!/usr/bin/env python3
"""Mathematical / indicator / pattern discovery layer for Strategy Hunter.

# Discovery layer v1: expandable beyond the fixed strategy library.

Generates additional mechanically-defined strategy variants from primitive
market series. It deliberately does not use holdout data to choose parameters.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def _rsi(close: pd.DataFrame, n: int) -> pd.DataFrame:
    delta = close.diff()
    up = delta.clip(lower=0).rolling(n, min_periods=n).mean()
    down = (-delta.clip(upper=0)).rolling(n, min_periods=n).mean()
    rs = up / down.replace(0, np.nan)
    return 100.0 - 100.0 / (1.0 + rs)


def _atr(high: pd.DataFrame, low: pd.DataFrame, close: pd.DataFrame, n: int) -> pd.DataFrame:
    prev = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev).abs(), (low - prev).abs()],
        axis=1,
    ).groupby(level=1, axis=1).max() if isinstance(high.columns, pd.MultiIndex) else None
    if tr is None:
        tr = pd.concat(
            [high - low, (high - prev).abs(), (low - prev).abs()],
            keys=["a", "b", "c"],
            axis=1,
        ).groupby(level=1, axis=1).max()
    return tr.rolling(n, min_periods=n).mean()


def build_discovery_variants(op, hp, lp, cp, vp, universe, ind):
    variants = {}
    liquid = (
        universe
        & (ind["avg_dollar"] >= 100_000.0)
        & cp.ge(0.50)
        & cp.le(1000.0)
        & cp.notna()
    )

    def add(name, mask, score, family, params):
        variants[name] = {
            "mask": mask.fillna(False),
            "score": score,
            "family": family,
            "params": params,
        }

    ret = cp.pct_change()
    ma50 = ind["ma50"]
    ma100 = ind["ma100"]
    ma200 = ind["ma200"]
    mom20 = cp / cp.shift(20) - 1.0
    mom60 = cp / cp.shift(60) - 1.0
    vr20 = ind["volume_ratio20"]

    # RSI: mean reversion and trend-confirmed momentum.
    for n in (7, 14, 21):
        rsi = _rsi(cp, n)
        for low, high in ((20, 80), (30, 70), (40, 60)):
            add(f"math_rsi{n}_reclaim{low}", liquid & (rsi <= low) & (cp > ma100), rsi, "math_rsi_reversal", {"rsi": n, "oversold": low})
            add(f"math_rsi{n}_trend{high}", liquid & (rsi >= high) & (cp > ma200) & (mom20 > 0), rsi, "math_rsi_trend", {"rsi": n, "overbought": high})

    # Stochastic K/D and threshold transitions.
    for n in (5, 9, 14, 21):
        low_n = lp.rolling(n, min_periods=n).min()
        high_n = hp.rolling(n, min_periods=n).max()
        k = 100.0 * (cp - low_n) / (high_n - low_n).replace(0, np.nan)
        d = k.rolling(3, min_periods=3).mean()
        add(f"math_stoch{n}_oversold", liquid & (k < 25) & (k > d) & (cp > ma100), k, "math_stoch_reversal", {"lookback": n, "threshold": 25})
        add(f"math_stoch{n}_trend", liquid & (k > 75) & (k > d) & (cp > ma200), k, "math_stoch_trend", {"lookback": n, "threshold": 75})

    # Bollinger level/bandwidth math.
    for n in (10, 20, 40):
        mid = cp.rolling(n, min_periods=n).mean()
        sd = cp.rolling(n, min_periods=n).std()
        z = (cp - mid) / sd.replace(0, np.nan)
        bandwidth = (4.0 * sd / mid.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
        for zmin in (-2.0, -1.5, -1.0):
            add(f"math_bb_revert{n}_z{zmin:g}", liquid & (z <= zmin) & (cp > ma200), z, "math_bollinger_reversal", {"lookback": n, "z": zmin})
        for squeeze in (0.03, 0.05, 0.08):
            add(f"math_bb_squeeze{n}_{squeeze:g}", liquid & (bandwidth <= squeeze) & (cp > ma100) & (mom20 > 0), mom20, "math_bollinger_breakout", {"lookback": n, "max_bandwidth": squeeze})

    # ATR / true-range normalized movement.
    for n in (7, 14, 21):
        atr = (hp - lp).combine((hp - cp.shift(1)).abs(), np.maximum).combine((lp - cp.shift(1)).abs(), np.maximum).rolling(n, min_periods=n).mean()
        atr_pct = atr / cp.replace(0, np.nan)
        for lim in (0.01, 0.02, 0.04, 0.06):
            add(f"math_atr{n}_quiet{lim:g}", liquid & (atr_pct <= lim) & (cp > ma100) & (mom20 > 0), mom20, "math_atr_contraction", {"atr_window": n, "atr_pct_max": lim})
        for exp in (0.03, 0.05, 0.08):
            add(f"math_atr{n}_exp{exp:g}", liquid & (atr_pct >= exp) & (cp > ma200) & (mom20 > 0), mom20, "math_atr_expansion", {"atr_window": n, "atr_pct_min": exp})

    # MACD / exponential trend transition.
    for fast, slow in ((8, 21), (12, 26), (20, 50)):
        ema_f = cp.ewm(span=fast, adjust=False, min_periods=fast).mean()
        ema_s = cp.ewm(span=slow, adjust=False, min_periods=slow).mean()
        macd = ema_f - ema_s
        signal = macd.ewm(span=9, adjust=False, min_periods=9).mean()
        hist = macd - signal
        add(f"math_macd{fast}_{slow}_cross", liquid & (macd > signal) & (hist > 0) & (cp > ma100), hist, "math_macd", {"fast": fast, "slow": slow})
        add(f"math_macd{fast}_{slow}_zero", liquid & (macd > 0) & (hist > 0) & (cp > ma200), hist, "math_macd", {"fast": fast, "slow": slow, "zero": True})

    # ADX-like directional strength using directional movement ratios.
    for n in (7, 14, 21):
        up_move = hp.diff()
        down_move = -lp.diff()
        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
        tr = pd.concat([hp - lp, (hp - cp.shift(1)).abs(), (lp - cp.shift(1)).abs()], keys=["a", "b", "c"], axis=1).groupby(level=1, axis=1).max()
        atr = tr.rolling(n, min_periods=n).mean()
        plus_di = 100.0 * plus_dm.rolling(n, min_periods=n).mean() / atr.replace(0, np.nan)
        minus_di = 100.0 * minus_dm.rolling(n, min_periods=n).mean() / atr.replace(0, np.nan)
        dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        adx = dx.rolling(n, min_periods=n).mean()
        for threshold in (15, 20, 25, 30):
            add(f"math_adx{n}_{threshold}", liquid & (adx >= threshold) & (plus_di > minus_di) & (cp > ma100), adx, "math_adx_trend", {"window": n, "adx": threshold})

    # OBV slope and price/volume agreement.
    sign = np.sign(ret).fillna(0.0)
    obv = (vp * sign).cumsum()
    for n in (10, 20, 40):
        obv_slope = obv - obv.shift(n)
        add(f"math_obv{n}_up", liquid & (obv_slope > 0) & (cp > ma100) & (mom20 > 0), obv_slope, "math_obv", {"lookback": n})
        add(f"math_obv{n}_divergence", liquid & (obv_slope > 0) & (mom20 <= 0) & (cp > ma200), obv_slope, "math_obv_divergence", {"lookback": n})

    # Efficiency ratio: separate directional from noisy markets.
    for n in (10, 20, 40):
        direction = (cp - cp.shift(n)).abs()
        noise = ret.abs().rolling(n, min_periods=n).sum()
        er = direction / (cp * noise).replace(0, np.nan)
        for t in (0.15, 0.25, 0.40, 0.60):
            add(f"math_efficiency{n}_{t:g}", liquid & (er >= t) & (cp > ma100) & (mom20 > 0), er, "math_efficiency", {"lookback": n, "threshold": t})

    # Mathematical z-score / normalized surprise.
    for n in (10, 20, 40, 60):
        mean = ret.rolling(n, min_periods=n).mean()
        std = ret.rolling(n, min_periods=n).std()
        z = (ret - mean) / std.replace(0, np.nan)
        for zmax in (-2.5, -2.0, -1.5):
            add(f"math_return_z_reversal{n}_{abs(zmax):g}", liquid & (z <= zmax) & (cp > ma200), z, "math_return_z_reversal", {"window": n, "z": zmax})
        for zmin in (1.0, 1.5, 2.0):
            add(f"math_return_z_cont{n}_{zmin:g}", liquid & (z >= zmin) & (cp > ma100), z, "math_return_z_continuation", {"window": n, "z": zmin})

    # Cross-sectional interactions: momentum x volume x volatility.
    vol20 = ret.rolling(20, min_periods=20).std()
    vol63 = ret.rolling(63, min_periods=63).std()
    vol_rank = vol20.div(vol63.replace(0, np.nan)).rank(axis=1, pct=True)
    mom_rank = mom60.rank(axis=1, pct=True)
    vr_rank = vr20.rank(axis=1, pct=True)
    for mr in (0.60, 0.80, 0.90):
        for vrank in (0.60, 0.80):
            add(
                f"interaction_mom{int(mr*100)}_vr{int(vrank*100)}",
                liquid & (mom_rank >= mr) & (vr_rank >= vrank) & (vol_rank <= 0.80),
                mom_rank + vr_rank,
                "interaction_momentum_volume",
                {"momentum_rank": mr, "volume_rank": vrank, "max_vol_rank": 0.80},
            )

    for rz in (-1.5, -1.0, -0.5):
        ret_z = (ret - ret.rolling(20, min_periods=20).mean()) / ret.rolling(20, min_periods=20).std().replace(0, np.nan)
        add(
            f"interaction_shock_revert{rz:g}",
            liquid & (ret_z <= rz) & (cp > ma200) & (vr_rank >= 0.50),
            ret_z,
            "interaction_shock_reversal",
            {"return_z": rz, "volume_rank_min": 0.50},
        )

    # Candle geometry / price-action made numeric.
    rng = (hp - lp).replace(0, np.nan)
    close_location = (cp - lp) / rng
    body = (cp - op) / rng
    for clv in (0.60, 0.75, 0.90):
        add(
            f"priceaction_close_location_{clv:g}",
            liquid & (close_location >= clv) & (body > 0) & (cp > ma100) & (vr20 >= 1.0),
            close_location,
            "price_action_strength",
            {"close_location_min": clv, "volume_ratio_min": 1.0},
        )
    for wick in (1.5, 2.0, 3.0):
        lower_wick = (np.minimum(op, cp) - lp) / rng
        add(
            f"priceaction_lower_wick{wick:g}",
            liquid & (lower_wick >= 0.20) & (close_location >= 0.60) & (cp > ma200) & (vr20 <= 2.0),
            lower_wick,
            "price_action_reversal",
            {"lower_wick_ratio_min": 0.20, "close_location_min": 0.60, "volume_ratio_max": 2.0, "shape": wick},
        )


    # Explicitly research major indicator families mentioned by the Owner,
    # while keeping them as members of the open research universe (not a boundary).
    # Ichimoku: causal cloud/Tenkan/Kijun/Chikou-style signals.
    for conv, base, span in ((9, 26, 52), (10, 30, 60), (20, 60, 120)):
        tenkan = (hp.rolling(conv, min_periods=conv).max() + lp.rolling(conv, min_periods=conv).min()) / 2.0
        kijun = (hp.rolling(base, min_periods=base).max() + lp.rolling(base, min_periods=base).min()) / 2.0
        span_b = (hp.rolling(span, min_periods=span).max() + lp.rolling(span, min_periods=span).min()) / 2.0
        span_a = (tenkan + kijun) / 2.0
        cloud_top = pd.concat([span_a, span_b], axis=1).groupby(level=1, axis=1).max()
        cloud_bottom = pd.concat([span_a, span_b], axis=1).groupby(level=1, axis=1).min()
        chikou_confirm = cp > cp.shift(base)
        tk_cross = (tenkan > kijun) & (tenkan.shift(1) <= kijun.shift(1))
        for cloud_filter, label in (
            ((cp > cloud_top), "above_cloud"),
            ((cp > cloud_top) & chikou_confirm, "above_cloud_chikou"),
            ((cp > cloud_top) & (tenkan > kijun), "above_cloud_tk"),
        ):
            add(
                f"ichimoku_{conv}_{base}_{span}_{label}",
                liquid & cloud_filter,
                cp / cloud_top.replace(0, np.nan) - 1.0,
                "ichimoku",
                {"conversion": conv, "base": base, "span": span, "confirmation": label},
            )
        add(
            f"ichimoku_{conv}_{base}_{span}_tk_cross",
            liquid & tk_cross & (cp > cloud_top) & chikou_confirm,
            cp / kijun.replace(0, np.nan) - 1.0,
            "ichimoku",
            {"conversion": conv, "base": base, "span": span, "confirmation": "tk_cross_cloud_chikou"},
        )

    # Donchian: breakout lengths and channel-position variants.
    for n in (10, 20, 40, 55, 100):
        upper = hp.shift(1).rolling(n, min_periods=n).max()
        lower = lp.shift(1).rolling(n, min_periods=n).min()
        mid = (upper + lower) / 2.0
        width = (upper - lower) / cp.replace(0, np.nan)
        for confirm, label in (
            (cp > upper, "upper_break"),
            ((cp > upper) & (vr20 >= 1.2), "upper_break_volume"),
            ((cp > upper) & (cp > ma200), "upper_break_trend"),
            ((cp > upper) & (cp > ma200) & (vr20 >= 1.2), "upper_break_trend_volume"),
        ):
            add(
                f"donchian_{n}_{label}",
                liquid & confirm,
                cp / upper.replace(0, np.nan) - 1.0,
                "donchian_breakout",
                {"channel": n, "confirmation": label},
            )
        add(
            f"donchian_{n}_mid_reclaim",
            liquid & (cp > mid) & (cp.shift(1) <= mid.shift(1)) & (cp > ma100),
            cp / mid.replace(0, np.nan) - 1.0,
            "donchian_reclaim",
            {"channel": n, "confirmation": "mid_reclaim"},
        )

    # EMA trend family: this is the user's example, but it is tested as one
    # family among many rather than becoming the search boundary.
    for fast, slow in ((5, 20), (9, 21), (10, 30), (20, 50), (50, 200)):
        ema_f = cp.ewm(span=fast, adjust=False, min_periods=fast).mean()
        ema_s = cp.ewm(span=slow, adjust=False, min_periods=slow).mean()
        cross = (ema_f > ema_s) & (ema_f.shift(1) <= ema_s.shift(1))
        add(
            f"ema_{fast}_{slow}_cross",
            liquid & cross & (cp > ema_s),
            ema_f / ema_s.replace(0, np.nan) - 1.0,
            "ema_trend",
            {"fast": fast, "slow": slow, "entry": "fresh_cross"},
        )
        add(
            f"ema_{fast}_{slow}_trend",
            liquid & (ema_f > ema_s) & (cp > ema_s) & (mom20 > 0),
            ema_f / ema_s.replace(0, np.nan) - 1.0,
            "ema_trend",
            {"fast": fast, "slow": slow, "entry": "trend_hold"},
        )

    # RSI should be tested as both mean-reversion and momentum/trend confirmation.
    # (The earlier discovery layer already has RSI; these variants explicitly
    # include cross/reclaim semantics rather than only static thresholds.)
    for n in (7, 14, 21):
        rsi = _rsi(cp, n)
        for level in (20, 25, 30, 35, 40):
            reclaim = (rsi > level) & (rsi.shift(1) <= level)
            add(
                f"rsi_{n}_reclaim_{level}_trend",
                liquid & reclaim & (cp > ma100),
                rsi,
                "rsi_reclaim",
                {"rsi": n, "level": level, "context": "ma100"},
            )
        for level in (50, 55, 60):
            add(
                f"rsi_{n}_momentum_{level}",
                liquid & (rsi > level) & (rsi.shift(1) <= level) & (cp > ma200) & (mom20 > 0),
                rsi,
                "rsi_momentum",
                {"rsi": n, "level": level, "context": "ma200"},
            )

    # External research bridge: global intelligence hypotheses now generate
    # explicitly tagged test variants. Sources influence discovery, never proof.
    hypotheses_path = Path(__file__).resolve().parents[1] / "results" / "global_strategy_hypotheses.json"
    try:
        hypotheses = json.loads(hypotheses_path.read_text(encoding="utf-8"))
    except Exception:
        hypotheses = []
    if isinstance(hypotheses, list):
        external_themes = {str(h.get("theme")): h for h in hypotheses if isinstance(h, dict)}
        # These recipes are deliberately simple: the external source creates
        # a testable lead, while the quantitative engine determines whether it survives.
        external_bases = {
            "momentum": ("ext_momentum", liquid & (mom60 > 0) & (cp > ma100), mom60, "external_momentum"),
            "breakout": ("ext_breakout", liquid & (cp > cp.shift(1).rolling(20, min_periods=20).max()) & (cp > ma100) & (vr20 >= 1.2), mom20, "external_breakout"),
            "mean_reversion": ("ext_reversion", liquid & (ret <= -0.05) & (cp > ma200), -ret, "external_mean_reversion"),
            "volume": ("ext_volume", liquid & (vr20 >= 1.5) & (mom20 > 0) & (cp > ma100), mom20, "external_volume"),
            "volatility": ("ext_volatility", liquid & (vol20 <= 0.8 * vol63) & (mom20 > 0) & (cp > ma100), mom20, "external_volatility"),
            "moving_average": ("ext_ma", liquid & (cp > ma100) & (ma50 > ma100) & (mom20 > 0), mom20, "external_moving_average"),
            "oscillator": ("ext_oscillator", liquid & (_rsi(cp, 14) <= 30) & (cp > ma100), -_rsi(cp, 14), "external_oscillator"),
            "price_action": ("ext_price_action", liquid & (close_location >= 0.75) & (body > 0) & (cp > ma100), close_location, "external_price_action"),
            "wyckoff": ("ext_wyckoff", liquid & (cp > ma200) & (undercut <= -0.01) & (clv >= 0.70), clv, "external_wyckoff"),
        }
        # Only promote themes actually found by the external intelligence layer.
        for theme, hypothesis in external_themes.items():
            if theme not in external_bases:
                continue
            base_name, base_mask, base_score, family = external_bases[theme]
            add(
                f"{base_name}_sourced",
                base_mask,
                base_score,
                family,
                {
                    "source": "global_strategy_intelligence",
                    "hypothesis_id": hypothesis.get("hypothesis_id"),
                    "source_count": hypothesis.get("source_count", 0),
                    "hypothesis": hypothesis.get("hypothesis"),
                },
            )

    return variants

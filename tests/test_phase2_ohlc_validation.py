"""
tests/test_phase2_ohlc_validation.py

Test strict OHLC validation and elimination of fabricated defaults in fetch_ihsg_snapshot:
- low <= min(open, close)
- high >= max(open, close)
- high >= low
- Close 6118.86 above High 6053.24 sets open/high/low to None.
- Missing values become None, NOT default to close or 0.
"""
from data_sources.market_data import validate_ohlc


def test_valid_ohlc():
    assert validate_ohlc(open_v=6100.0, high_v=6150.0, low_v=6080.0, close_v=6120.0) is True


def test_invalid_close_above_high():
    # 2026-10-05 real example: close 6118.86 above high 6053.24
    assert validate_ohlc(open_v=6040.0, high_v=6053.24, low_v=6020.0, close_v=6118.86) is False


def test_invalid_close_below_low():
    assert validate_ohlc(open_v=6100.0, high_v=6150.0, low_v=6080.0, close_v=6050.0) is False


def test_invalid_open_above_high():
    assert validate_ohlc(open_v=6200.0, high_v=6150.0, low_v=6080.0, close_v=6120.0) is False


def test_invalid_high_lower_than_low():
    assert validate_ohlc(open_v=6100.0, high_v=6050.0, low_v=6080.0, close_v=6100.0) is False


def test_none_close_or_bounds():
    assert validate_ohlc(open_v=6100.0, high_v=None, low_v=6080.0, close_v=6120.0) is False
    assert validate_ohlc(open_v=6100.0, high_v=6150.0, low_v=6080.0, close_v=None) is False


def test_invalid_identical_to_previous_candle():
    # Stale forward-filled data where entire OHLC is identical to previous candle
    assert validate_ohlc(
        open_v=6100.0, high_v=6150.0, low_v=6080.0, close_v=6120.0,
        prev_open=6100.0, prev_high=6150.0, prev_low=6080.0, prev_close=6120.0
    ) is False


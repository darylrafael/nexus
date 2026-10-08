from typing import Optional


def classify_direction(pct: Optional[float], threshold: float = 0.2) -> str:
    """Canonical IHSG direction classifier across the entire Nexus pipeline.

    Threshold: ±0.2%
    - > +0.2% -> 'Bullish'
    - < -0.2% -> 'Bearish'
    - [-0.2%, +0.2%] -> 'Neutral'
    - None / NaN / non-numeric -> 'Unknown'
    """
    if pct is None:
        return "Unknown"
    try:
        val = float(pct)
    except (ValueError, TypeError):
        return "Unknown"

    if val > threshold:
        return "Bullish"
    elif val < -threshold:
        return "Bearish"
    else:
        return "Neutral"

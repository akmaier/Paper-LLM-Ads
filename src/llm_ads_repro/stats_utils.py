"""Wilson score interval for binomial proportions (95% CI)."""

from __future__ import annotations

import math
from typing import Tuple


def wilson_ci(successes: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    phat = successes / n
    denom = 1 + z**2 / n
    center = (phat + z**2 / (2 * n)) / denom
    margin = (
        z
        * math.sqrt((phat * (1 - phat) + z**2 / (4 * n)) / n)
        / denom
    )
    return max(0.0, center - margin), min(1.0, center + margin)

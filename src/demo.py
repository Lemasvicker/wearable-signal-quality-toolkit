# Wearable Signal Quality Toolkit (v0.1.0)
# Minimal demo using synthetic time-series (non-proprietary)

from __future__ import annotations
import math
import random
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class SyntheticSignal:
    t: List[float]
    x: List[float]
    fs_hz: float


def generate_synthetic_signal(
    duration_s: float = 60.0,
    fs_hz: float = 25.0,
    base_freq_hz: float = 1.2,
    noise_std: float = 0.15,
    dropout_prob: float = 0.02,
    seed: int = 7,
) -> SyntheticSignal:
    rng = random.Random(seed)
    n = int(duration_s * fs_hz)
    t, x = [], []
    for i in range(n):
        ti = i / fs_hz
        # Simple quasi-periodic waveform + noise
        xi = math.sin(2 * math.pi * base_freq_hz * ti) + rng.gauss(0.0, noise_std)
        # Random dropouts -> NaN
        if rng.random() < dropout_prob:
            xi = float("nan")
        t.append(ti)
        x.append(xi)
    return SyntheticSignal(t=t, x=x, fs_hz=fs_hz)


def missingness_fraction(x: List[float]) -> float:
    if not x:
        return 0.0
    n_miss = sum(1 for v in x if isinstance(v, float) and math.isnan(v))
    return n_miss / len(x)


def saturation_fraction(x: List[float], lo: float = -1.2, hi: float = 1.2) -> float:
    if not x:
        return 0.0
    n_sat = 0
    for v in x:
        if isinstance(v, float) and math.isnan(v):
            continue
        if v <= lo or v >= hi:
            n_sat += 1
    return n_sat / len(x)


def estimate_offset_by_grid_search(
    t_ref: List[float],
    x_ref: List[float],
    t_other: List[float],
    x_other: List[float],
    search_s: float = 2.0,
    step_s: float = 0.02,
) -> Tuple[float, float]:
    """
    Toy demo: estimate constant time offset between two streams
    by maximizing correlation on a coarse grid.
    Returns (best_offset_seconds, best_score).
    """
    # Build index for other stream
    if not t_ref or not t_other:
        return 0.0, float("-inf")

    def sample_at(tq: float) -> float:
        # nearest-neighbor
        j = min(range(len(t_other)), key=lambda k: abs(t_other[k] - tq))
        return x_other[j]

    best_off, best_score = 0.0, float("-inf")
    off = -search_s
    while off <= search_s + 1e-12:
        xs, ys = [], []
        for tr, xr in zip(t_ref, x_ref):
            if isinstance(xr, float) and math.isnan(xr):
                continue
            yo = sample_at(tr + off)
            if isinstance(yo, float) and math.isnan(yo):
                continue
            xs.append(xr)
            ys.append(yo)
        if len(xs) >= 10:
            # correlation-like score (not normalized perfectly; OK for demo)
            mx = sum(xs) / len(xs)
            my = sum(ys) / len(ys)
            num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
            denx = math.sqrt(sum((a - mx) ** 2 for a in xs))
            deny = math.sqrt(sum((b - my) ** 2 for b in ys))
            score = num / (denx * deny + 1e-12)
            if score > best_score:
                best_score = score
                best_off = off
        off += step_s

    return best_off, best_score


def main() -> None:
    ref = generate_synthetic_signal(seed=7)
    other = generate_synthetic_signal(seed=8)

    # Inject a known time offset in "other" timestamps
    true_offset_s = 0.42
    other_shifted_t = [ti + true_offset_s for ti in other.t]

    print("Wearable Signal Quality Toolkit demo (synthetic)")
    print(f"Ref missingness: {missingness_fraction(ref.x):.3f}")
    print(f"Ref saturation:  {saturation_fraction(ref.x):.3f}")
    print(f"Other missingness: {missingness_fraction(other.x):.3f}")
    print(f"Other saturation:  {saturation_fraction(other.x):.3f}")

    est_off, score = estimate_offset_by_grid_search(ref.t, ref.x, other_shifted_t, other.x)
    print(f"True offset (s): {true_offset_s:.2f}")
    print(f"Estimated offset (s): {est_off:.2f}  (score={score:.3f})")


if __name__ == "__main__":
    main()

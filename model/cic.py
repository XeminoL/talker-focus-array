import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scene"))

from params import CIC_ORDER, CIC_RATIO, CIC_WIDTH

CIC_LATENCY = CIC_ORDER
MASK = (1 << CIC_WIDTH) - 1
SIGN = 1 << (CIC_WIDTH - 1)


def wrap(value):
    value &= MASK
    return value - (1 << CIC_WIDTH) if value & SIGN else value


def bipolar(bits):
    return bits.astype(np.int64) * 2 - 1


def cic_wrapped(bits):
    integrators = [0] * CIC_ORDER
    combs = [0] * CIC_ORDER
    out = []
    for index, sample in enumerate(bipolar(bits)):
        value = int(sample)
        for stage in range(CIC_ORDER):
            integrators[stage] = wrap(integrators[stage] + value)
            value = integrators[stage]
        if index % CIC_RATIO == CIC_RATIO - 1:
            for stage in range(CIC_ORDER):
                value, combs[stage] = wrap(value - combs[stage]), value
            out.append(value)
    return np.array(out, dtype=np.int64)


def cic_fast(bits, delay=0):
    level = np.concatenate((np.zeros(delay, dtype=np.int64), bipolar(bits)))[: len(bits)]
    with np.errstate(over="ignore"):
        value = level
        for _ in range(CIC_ORDER):
            value = np.cumsum(value)
        value = value[CIC_RATIO - 1 :: CIC_RATIO]
        for _ in range(CIC_ORDER):
            value = value - np.concatenate(([0], value[:-1]))
    value = value & MASK
    return np.where(value & SIGN, value - (1 << CIC_WIDTH), value)


def cic_exact(bits, delay=0):
    level = np.concatenate((np.zeros(delay, dtype=np.int64), bipolar(bits)))[: len(bits)]
    value = level.astype(object)
    for _ in range(CIC_ORDER):
        value = np.cumsum(value)
    value = value[CIC_RATIO - 1 :: CIC_RATIO]
    for _ in range(CIC_ORDER):
        value = value - np.concatenate(([0], value[:-1]))
    return np.array(value, dtype=np.int64)


if __name__ == "__main__":
    from pdm_build import pdm_path

    scene = np.load(pdm_path(4.0))
    bits = np.unpackbits(scene["bits"][0:1], axis=1)[0, : CIC_RATIO * 4000]
    wrapped = cic_wrapped(bits)
    exact = cic_exact(bits)
    gain = CIC_RATIO**CIC_ORDER
    print("outputs", len(wrapped), "gain", gain, "log2", np.log2(gain))
    print("mismatches", int(np.sum(wrapped != exact)))
    print("peak", int(np.abs(exact).max()), "limit", SIGN - 1, f"headroom {np.log2((SIGN - 1) / np.abs(exact).max()):.2f} bits")

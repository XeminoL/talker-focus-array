import subprocess
import time
from pathlib import Path

import numpy as np

from cic import CIC_LATENCY, CIC_RATIO, cic_fast
from cic_check import to_wsl
from fir_fixed import export_coefficients, fir_fixed, reduce_cic
from pdm_build import pdm_path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "build" / "frontend"
CHANNELS = 64
FRAMES = 300
SOURCES = ("cic_bank.v", "fir_bank.v", "mic_frontend.v")


def loud_bits(distance, frames):
    packed = np.load(pdm_path(distance))["bits"]
    first = np.unpackbits(packed[0:1], axis=1)[0]
    loud = int(np.argmax(np.abs(cic_fast(first, CIC_LATENCY))))
    start = max(0, loud - frames // 2) * CIC_RATIO
    length = frames * CIC_RATIO
    return np.unpackbits(packed[:, (start // 8) : (start + length) // 8 + 1], axis=1)[:, :length]


def run_rtl(bits):
    WORK.mkdir(parents=True, exist_ok=True)
    words = [int("".join(str(b) for b in column[::-1]), 2) for column in bits.T]
    (WORK / "frontend_stimulus.hex").write_text("\n".join(f"{w:016x}" for w in words) + "\n")
    sources = " ".join(f"'{to_wsl(ROOT / 'rtl' / name)}'" for name in SOURCES)
    tb = to_wsl(ROOT / "tb" / "mic_frontend_tb.v")
    coefficients = to_wsl(ROOT / "rtl" / "fir_coefficients.hex")
    command = (
        f"cd '{to_wsl(WORK)}' && cp '{coefficients}' . && "
        f"iverilog -g2005 -Wall -Pmic_frontend_tb.TICKS={bits.shape[1]} -o sim {sources} '{tb}' && vvp -n sim"
    )
    result = subprocess.run(["wsl", "bash", "-lc", command], capture_output=True, text=True)
    text = result.stdout + result.stderr
    warnings = [line for line in text.splitlines() if "warning" in line.lower() or "error" in line.lower()]
    if result.returncode != 0:
        print(text)
        raise SystemExit(1)
    return np.loadtxt(WORK / "frontend_rtl.txt", dtype=np.int64, ndmin=2), warnings


def check(name, bits, taps):
    start = time.time()
    rows, warnings = run_rtl(bits)
    compared = mismatches = 0
    for channel in range(CHANNELS):
        reference = fir_fixed(reduce_cic(cic_fast(bits[channel], CIC_LATENCY)), taps)
        got = rows[rows[:, 0] == channel, 1]
        count = min(len(got), len(reference))
        compared += count
        mismatches += int(np.sum(got[:count] != reference[:count]))
    peak = int(np.abs(rows[:, 1]).max()) if len(rows) else 0
    print(f"{name:22} outputs {len(rows)} compared {compared} mismatches {mismatches} peak {peak} warnings {len(warnings)} {time.time() - start:.0f} s")
    for line in warnings[:5]:
        print("  ", line)


if __name__ == "__main__":
    taps = export_coefficients()
    check("2.0 m loud 64 mics", loud_bits(2.0, FRAMES), taps)
    check("all ones", np.ones((CHANNELS, 200 * CIC_RATIO), dtype=np.uint8), taps)

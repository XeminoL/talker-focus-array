import subprocess
import time
from pathlib import Path

import numpy as np

from beam_fixed import BEAM_COEF_BITS, beam_fixed, design
from cic_check import to_wsl
from fir_fixed import to_hex
from frontend import frontend_path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "build" / "beam"
FRAMES = 400


def run_rtl(audio, weights, shift):
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "beam_weights.hex").write_text("\n".join(to_hex(weights.reshape(-1), BEAM_COEF_BITS)) + "\n")
    (WORK / "beam_stimulus.hex").write_text("\n".join(to_hex(audio.T.reshape(-1), 24)) + "\n")
    rtl = to_wsl(ROOT / "rtl" / "beam_bank.v")
    tb = to_wsl(ROOT / "tb" / "beam_bank_tb.v")
    command = (
        f"cd '{to_wsl(WORK)}' && iverilog -g2005 -Wall -Pbeam_bank_tb.FRAMES={audio.shape[1]} "
        f"-Pbeam_bank_tb.SHIFT={shift} -o sim '{rtl}' '{tb}' && vvp -n sim"
    )
    result = subprocess.run(["wsl", "bash", "-lc", command], capture_output=True, text=True)
    text = result.stdout + result.stderr
    warnings = [line for line in text.splitlines() if "warning" in line.lower() or "error" in line.lower()]
    if result.returncode != 0:
        print(text)
        raise SystemExit(1)
    return np.loadtxt(WORK / "beam_rtl.txt", dtype=np.int64, ndmin=1), warnings


def check(name, audio, weights, shift):
    start = time.time()
    rtl, warnings = run_rtl(audio, weights, shift)
    reference = beam_fixed(audio, weights, shift)
    count = min(len(rtl), len(reference))
    mismatches = int(np.sum(rtl[:count] != reference[:count]))
    print(f"{name:26} outputs {count} of {len(reference)} mismatches {mismatches} peak {int(np.abs(reference).max())} warnings {len(warnings)} {time.time() - start:.0f} s")
    for line in warnings[:5]:
        print("  ", line)


if __name__ == "__main__":
    audio = np.load(frontend_path(2.0))
    loud = int(np.argmax(np.abs(audio[27])))
    start = max(0, loud - FRAMES // 2)
    window = audio[:, start : start + FRAMES]
    weights, shift = design("das-sinc", 2.0)
    check("das-sinc 2.0 m loud", window, weights, shift)
    rng = np.random.default_rng(3)
    extreme = np.where(rng.random((64, 200)) < 0.5, (1 << 23) - 1, -(1 << 23)).astype(np.int64)
    worst = np.where(rng.random(weights.shape) < 0.5, (1 << 17) - 1, -(1 << 17)).astype(np.int64)
    check("random extremes shift 20", extreme, worst, 20)

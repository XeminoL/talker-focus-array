import subprocess
import time
from pathlib import Path

import numpy as np

from beam_fixed import BEAM_COEF_BITS, beam_fixed, design
from cic import CIC_LATENCY, cic_fast
from cic_check import to_wsl
from fir_fixed import export_coefficients, fir_fixed, reduce_cic, to_hex
from frontend_check import loud_bits

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "build" / "focus"
SOURCES = ("cic_bank.v", "fir_bank.v", "mic_frontend.v", "beam_bank.v", "talker_focus.v")
FRAMES = 600


def run_rtl(bits, weights, shift):
    WORK.mkdir(parents=True, exist_ok=True)
    words = [int("".join(str(b) for b in column[::-1]), 2) for column in bits.T]
    (WORK / "focus_stimulus.hex").write_text("\n".join(f"{w:016x}" for w in words) + "\n")
    (WORK / "focus_weights.hex").write_text("\n".join(to_hex(weights.reshape(-1), BEAM_COEF_BITS)) + "\n")
    sources = " ".join(f"'{to_wsl(ROOT / 'rtl' / name)}'" for name in SOURCES)
    tb = to_wsl(ROOT / "tb" / "talker_focus_tb.v")
    coefficients = to_wsl(ROOT / "rtl" / "fir_coefficients.hex")
    command = (
        f"cd '{to_wsl(WORK)}' && cp '{coefficients}' . && "
        f"iverilog -g2005 -Wall -Ptalker_focus_tb.TICKS={bits.shape[1]} -Ptalker_focus_tb.SHIFT={shift} "
        f"-o sim {sources} '{tb}' && vvp -n sim"
    )
    result = subprocess.run(["wsl", "bash", "-lc", command], capture_output=True, text=True)
    text = result.stdout + result.stderr
    warnings = [line for line in text.splitlines() if "warning" in line.lower() or "error" in line.lower()]
    if result.returncode != 0:
        print(text)
        raise SystemExit(1)
    return np.loadtxt(WORK / "focus_rtl.txt", dtype=np.int64, ndmin=1), warnings


if __name__ == "__main__":
    start = time.time()
    taps = export_coefficients()
    bits = loud_bits(2.0, FRAMES)
    weights, shift = design("das-sinc", 2.0)
    frontend = np.array([fir_fixed(reduce_cic(cic_fast(bits[m], CIC_LATENCY)), taps) for m in range(64)])
    reference = beam_fixed(frontend, weights, shift)
    rtl, warnings = run_rtl(bits, weights, shift)
    count = min(len(rtl), len(reference))
    mismatches = int(np.sum(rtl[:count] != reference[:count]))
    print(f"pdm to audio: outputs {len(rtl)} compared {count} of {len(reference)} mismatches {mismatches} peak {int(np.abs(reference).max())} warnings {len(warnings)} {time.time() - start:.0f} s")
    for line in warnings[:5]:
        print("  ", line)

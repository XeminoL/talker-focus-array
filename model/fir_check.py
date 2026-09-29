import subprocess
from pathlib import Path

import numpy as np

from cic import CIC_LATENCY, cic_fast
from cic_check import to_wsl
from fir_fixed import DATA_MAX, DATA_MIN, FIR_DATA_BITS, export_coefficients, fir_fixed, reduce_cic, to_hex
from pdm_build import pdm_path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "build" / "fir"
SAMPLES = 3000


def run_rtl(samples):
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "fir_stimulus.hex").write_text("\n".join(to_hex(samples, FIR_DATA_BITS)) + "\n")
    rtl = to_wsl(ROOT / "rtl" / "fir_decimator.v")
    tb = to_wsl(ROOT / "tb" / "fir_decimator_tb.v")
    coefficients = to_wsl(ROOT / "rtl" / "fir_coefficients.hex")
    command = (
        f"cd '{to_wsl(WORK)}' && cp '{coefficients}' . && "
        f"iverilog -g2005 -Wall -Pfir_decimator_tb.SAMPLES={len(samples)} -o sim '{rtl}' '{tb}' && vvp -n sim"
    )
    result = subprocess.run(["wsl", "bash", "-lc", command], capture_output=True, text=True)
    text = result.stdout + result.stderr
    warnings = [line for line in text.splitlines() if "warning" in line.lower() or "error" in line.lower()]
    if result.returncode != 0:
        print(text)
        raise SystemExit(1)
    return np.loadtxt(WORK / "fir_rtl.txt", dtype=np.int64, ndmin=1), warnings


def check(name, samples, taps):
    rtl, warnings = run_rtl(samples)
    reference = fir_fixed(samples, taps)
    count = min(len(rtl), len(reference))
    mismatches = int(np.sum(rtl[:count] != reference[:count]))
    print(f"{name:22} outputs {count:5d} of {len(reference)} mismatches {mismatches} peak {int(np.abs(reference).max())} warnings {len(warnings)}")
    for line in warnings[:5]:
        print("  ", line)


if __name__ == "__main__":
    taps = export_coefficients()
    bits = np.unpackbits(np.load(pdm_path(2.0))["bits"][63:64], axis=1)[0]
    speech = reduce_cic(cic_fast(bits, CIC_LATENCY))
    loud = int(np.argmax(np.abs(speech)))
    start = max(0, loud - SAMPLES // 2) // 3 * 3
    check("2.0 m mic 63 loud", speech[start : start + SAMPLES], taps)
    check("positive full scale", np.full(600, DATA_MAX, dtype=np.int64), taps)
    check("negative full scale", np.full(600, DATA_MIN, dtype=np.int64), taps)
    rng = np.random.default_rng(1)
    check("alternating extremes", np.where(rng.random(600) < 0.5, DATA_MAX, DATA_MIN), taps)

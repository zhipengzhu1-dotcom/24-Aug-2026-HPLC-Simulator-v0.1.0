"""Turning the #134 exports into the measured run tables that go into `validation/`.

Run this to regenerate every number: the raw `.arw` files are not in the repo (1.3 GB
against a 1 GB LFS allowance), so what is committed is the single-channel trace each
run was measured on, its checksum, and the peak table. The trace is ~0.7 MB and carries
the whole measurement, so a disputed width can be re-derived from the repo alone; the
manifest lets the raw be checked against the copy it came from.

The assignments below are the driver's, signed off on 2026-09-09 against annotated
overlays, and are written here rather than recomputed: spectral matching proposes, and
on this sample set it cannot decide alone. The four-peak sample's compounds pair up
spectrally -- Unknown-1 against Unknown-2 scores 0.9990 and Unknown-3 against
Unknown-4 scores 0.9994, while pair against pair scores about 0.61 -- so a spectrum
says which pair a peak belongs to and no more. Within a pair the order is Empower's and
the scouting run's, and it is unchanged at both starts.

Peaks the driver did not name stay unnamed. Every peak found is written out, including
the ones before the void, because an injection disturbance that is silently dropped is
indistinguishable from one that was never there.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from scripts.arw import Trace, read_channel
from scripts.assign import fingerprints, similarity_matrix
from scripts.integrate import Measurement, Peak, capacity_factor, measure

# validation/method.csv: the measured void and the instrument's own dwell at 0.4 mL/min.
T0_MIN = 0.525
DWELL_MIN = 0.375 / 0.4

# Empower reports area in µAU·s and height in µAU; the recorded CSVs are in those units,
# so the new files are too and the two are comparable without a conversion in the reader.
_AREA_PER_AU_MIN = 6.0e7
_HEIGHT_PER_AU = 1.0e6

_FOUR_PEAK = ("Unknown-1", "Unknown-2", "Unknown-3", "Unknown-4")
_THREE_PEAK = ("Unknown-1", "Unknown-2", "Unknown-3")

# The #134 programme, driver-supplied. Both samples ran it; only the start differs.
_GRADIENT_ROWS = ("#", "Time", "Flow (mL/min)", "%A", "%B")


def _programme(start_b: int) -> tuple[tuple[str, ...], ...]:
    a = 100 - start_b
    return (
        ("1", "0", "0.4", str(a), str(start_b)),
        ("2", "0.5", "0.4", str(a), str(start_b)),
        ("3", "20.5", "0.4", "5", "95"),
        ("4", "23.5", "0.4", "5", "95"),
        ("5", "23.6", "0.4", str(a), str(start_b)),
        ("6", "27", "0.4", str(a), str(start_b)),
    )


@dataclass(frozen=True)
class Reference:
    """The scouting run a sample's peak identities are anchored to."""

    raw: str
    nm: float
    peak_times: tuple[float, ...]
    names: tuple[str, ...]


@dataclass(frozen=True)
class Run:
    raw: str
    nm: float
    sample: str
    start_b: int
    out_peaks: str
    out_trace: str
    reference: Reference
    # Approximate tR -> compound, as signed off. Everything else is left unnamed.
    assigned: tuple[tuple[float, str], ...]
    note: str


FOUR_PEAK_SCOUTING = Reference(
    raw="Export Data Points22956.arw",
    nm=220.0,
    peak_times=(13.219, 13.317, 13.517, 13.584),
    names=_FOUR_PEAK,
)
THREE_PEAK_SCOUTING = Reference(
    raw="25-Sep-2026 v0.1.0 Validation/Export Data Points22783_tG15.arw",
    nm=254.0,
    peak_times=(9.855, 11.592, 16.159),
    names=_THREE_PEAK,
)

RUNS: tuple[Run, ...] = (
    Run(
        raw="08-Sep-2026 Gradients/Export Data Points23045-50%_Cannabinoid.arw",
        nm=220.0,
        sample="four-peak",
        start_b=50,
        out_peaks="validation/Validation_2/4peaks_run7.csv",
        out_trace="validation/traces/4peaks_run7-219.8182nm.csv",
        reference=FOUR_PEAK_SCOUTING,
        assigned=(
            (8.309, "Unknown-1"),
            (8.544, "Unknown-2"),
            (9.018, "Unknown-3"),
            (9.184, "Unknown-4"),
        ),
        note=(
            "Raised start, 50 -> 95 %B over tG 20. s* = 0.0118, on the shallow edge of "
            "this sample's scouting bracket (0.0118-0.0315). All four peaks on the ramp, "
            "order as in the scouting run. Not pre-registered: the injections were made "
            "on 2026-09-08 before any run sheet existed (#134 checklist step 1 skipped)."
        ),
    ),
    Run(
        raw="08-Sep-2026 Gradients/Export Data Points23048_75%_Cannabinoid.arw",
        nm=220.0,
        sample="four-peak",
        start_b=75,
        out_peaks="validation/Validation_2/4peaks_run8.csv",
        out_trace="validation/traces/4peaks_run8-219.8182nm.csv",
        reference=FOUR_PEAK_SCOUTING,
        assigned=(
            (1.788, "Unknown-1"),
            (1.851, "Unknown-2"),
            (2.004, "Unknown-3"),
            (2.055, "Unknown-4"),
        ),
        note=(
            "75 -> 95 %B over tG 20. Every peak elutes at k' 0.6-1.1, essentially in the "
            "void, so the retention residual here tests the void volume rather than the "
            "retention model; peaks below k' 1 are excluded from residual statistics. "
            "s* = 0.00525, 0.33 window-widths BELOW the scouting bracket, so this run "
            "varies the start and the steepness together and isolates neither. Empower's "
            "report for this run lists a fifth peak at 25.525 min carrying 94.8 % of the "
            "area; that is the baseline step where the gradient returns to 75 %B, not a "
            "compound, and it is not integrated here. Not pre-registered."
        ),
    ),
    Run(
        raw="08-Sep-2026 Gradients/Export Data Points23051_50% Nitroso.arw",
        nm=254.0,
        sample="three-peak",
        start_b=50,
        out_peaks="validation/run8.csv",
        out_trace="validation/traces/run8-254.0824nm.csv",
        reference=THREE_PEAK_SCOUTING,
        assigned=((2.392, "Unknown-1"),),
        note=(
            "50 -> 95 %B over tG 20. s* = 0.0118, inside this sample's scouting bracket "
            "(0.0105-0.0315). Only Unknown-1 is assigned: it matches the scouting "
            "spectrum at 0.997. Unknown-2 is absent -- the fit puts it near 7.7 min and "
            "the trace is flat there. The 15.951 min peak matches Unknown-3 at only "
            "0.753 and elutes about 4 min from where the fit puts it, so it is recorded "
            "unnamed rather than guessed (PROTOCOL section 4). Everything before 1.462 "
            "min (t0 + dwell) is injection disturbance; Empower's own report counted two "
            "of those as peaks and its numbering skips 4, so a peak was deleted by hand. "
            "Not pre-registered."
        ),
    ),
    Run(
        raw="08-Sep-2026 Gradients/Export Data Points23054_75% Nitroso.arw",
        nm=254.0,
        sample="three-peak",
        start_b=75,
        out_peaks="validation/run9.csv",
        out_trace="validation/traces/run9-254.0824nm.csv",
        reference=THREE_PEAK_SCOUTING,
        assigned=(),
        note=(
            "75 -> 95 %B over tG 20. No peak is assigned: nothing elutes near the void "
            "where the fit puts Unknown-1 and Unknown-2, and no later peak matches a "
            "scouting spectrum above 0.99 at a plausible time. The run contributes no "
            "retention residual and is evidence about where retention ends on this "
            "sample, not about the LSS line. s* = 0.00525, 0.25 window-widths below the "
            "scouting bracket. Not pre-registered."
        ),
    ),
)


def _match_scores(
    raw: Path, trace: Trace, peaks: tuple[Peak, ...], root: Path, run: Run
) -> list[float]:
    """Each peak's best cosine similarity against its sample's scouting spectra."""
    reference_path = root / run.reference.raw
    reference_trace = read_channel(reference_path, run.reference.nm)
    reference_peaks = measure(reference_trace).peaks
    chosen = []
    for target in run.reference.peak_times:
        best = min(reference_peaks, key=lambda peak: abs(peak.t_r - target))
        chosen.append(best)
    reference = fingerprints(reference_path, chosen, reference_trace.times)
    queries = fingerprints(raw, peaks, trace.times)
    scores = similarity_matrix(queries, reference)
    return [float(np.max(row)) if row.size else 0.0 for row in scores]


def _name_for(peak: Peak, run: Run) -> str:
    for time, name in run.assigned:
        if abs(peak.t_r - time) < 0.02:
            return name
    return ""


def _write_trace(path: Path, trace: Trace) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time_min", f"absorbance_AU_at_{trace.channel.nm:.4f}nm"])
        for time, value in zip(trace.times, trace.signal, strict=True):
            writer.writerow([f"{time:.7f}", f"{value:.7g}"])


def _write_peaks(
    path: Path, run: Run, trace: Trace, result: Measurement, scores: list[float], revision: str
) -> None:
    rs_after = {id(pair.earlier): pair for pair in result.pairs}
    total = sum(peak.area for peak in result.peaks) or 1.0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["tG_min", 20, "", "", ""])
        writer.writerow(["sample", run.sample, "", "", ""])
        writer.writerow(
            [
                "compound",
                "tR_min",
                "area",
                "area_pct",
                "height",
                "W_half_min",
                "USP_tailing",
                "USP_resolution_to_next",
                "rs_to_next",
                "k_prime",
                "spectral_match",
                "w_half_basis",
            ]
        )
        for peak, score in zip(result.peaks, scores, strict=True):
            pair = rs_after.get(id(peak))
            writer.writerow(
                [
                    _name_for(peak, run),
                    f"{peak.t_r:.3f}",
                    f"{peak.area * _AREA_PER_AU_MIN:.0f}",
                    f"{100.0 * peak.area / total:.2f}",
                    f"{peak.height * _HEIGHT_PER_AU:.0f}",
                    f"{peak.w_half:.4f}",
                    "" if peak.tailing is None else f"{peak.tailing:.2f}",
                    ""
                    if pair is None or pair.usp_resolution is None
                    else f"{pair.usp_resolution:.2f}",
                    "" if pair is None else f"{pair.rs:.2f}",
                    f"{capacity_factor(peak.t_r, T0_MIN, DWELL_MIN):.2f}",
                    f"{score:.3f}",
                    peak.w_half_basis,
                ]
            )
        writer.writerow([])
        writer.writerow(["Gradient"])
        writer.writerow(list(_GRADIENT_ROWS))
        for row in _programme(run.start_b):
            writer.writerow(list(row))
        writer.writerow([])
        writer.writerow(["PROVENANCE"])
        for key, value in (
            ("source_file", Path(run.raw).name),
            ("source_sha256", trace.sha256),
            ("channel_nm", f"{trace.channel.nm:.4f}"),
            ("nominal_nm", f"{run.nm:.0f}"),
            ("units", "area µAU·s; height µAU; times min"),
            ("sampling_hz", f"{trace.sampling_hz:.3f}"),
            ("trace", run.out_trace),
            ("integrator", f"scripts/integrate.py at {revision}"),
            ("t0_min", f"{T0_MIN}"),
            ("dwell_min", f"{DWELL_MIN}"),
            ("noise_AU", f"{result.noise:.3e}"),
            ("rs_convention", "rs = dt / (2(sigma1 + sigma2)), sigma = W_half / sqrt(8 ln 2)"),
            ("usp_convention", "2 dt / (W1 + W2), inflection tangents extended to baseline"),
            ("measured_before_prediction", "yes"),
        ):
            writer.writerow([key, value])
        writer.writerow([])
        writer.writerow([f"NOTE: {run.note}"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=Path("validation/Waters Data/OneDrive_1_9-9-2026"),
        help="folder holding the .arw exports (not in the repo)",
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    arguments = parser.parse_args()

    revision = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=False
    ).stdout.strip()

    manifest: list[list[str]] = [["file", "sha256", "bytes", "channel_nm", "written_as"]]
    for run in RUNS:
        raw = arguments.raw_root / run.raw
        trace = read_channel(raw, run.nm)
        result = measure(trace)
        scores = _match_scores(raw, trace, result.peaks, arguments.raw_root, run)
        _write_trace(arguments.repo_root / run.out_trace, trace)
        _write_peaks(arguments.repo_root / run.out_peaks, run, trace, result, scores, revision)
        manifest.append(
            [
                Path(run.raw).name,
                trace.sha256,
                str(raw.stat().st_size),
                f"{trace.channel.nm:.4f}",
                run.out_peaks,
            ]
        )
        print(f"{run.out_peaks}: {len(result.peaks)} peaks from {Path(run.raw).name}")

    manifest_path = arguments.repo_root / "validation/traces/MANIFEST.csv"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", newline="") as handle:
        csv.writer(handle).writerows(manifest)
    print(f"{manifest_path}: {len(manifest) - 1} raw files recorded")


if __name__ == "__main__":
    main()

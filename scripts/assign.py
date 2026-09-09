"""Deciding which measured peak is which compound, by its spectrum.

Elution order is the obvious way to assign peaks across runs and it is the one that
fails where it matters. The whole reason this sample set exists is that order reverses:
the composition-freedom work turns on runs where a peak overtakes its neighbour, and a
`validation/` note already records a peak eluting in a wash rather than on the ramp. An
assignment built on order cannot see that happen; it just relabels the peaks and
reports a clean residual for the wrong compound.

A PDA export gives a spectrum at every time point, so identity can be evidence instead.
Each peak's apex spectrum, with its own baseline subtracted and normalised to unit
length, is a fingerprint that a change of gradient barely touches — the compound's
absorbance shape is a property of the compound. Peaks are then scored against the
scouting run's peaks by cosine similarity.

The score is evidence, not a verdict. On the four-peak sample it separates the compounds
into two pairs and no further — within a pair the spectra score 0.999 against each other
— so a score alone cannot name a peak. This module measures the resemblance; the driver
names the peak, and `scripts/measure_runs.py` records the names that were signed off.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from scripts.arw import read_spectra
from scripts.integrate import Peak


@dataclass(frozen=True)
class Fingerprint:
    """One peak's baseline-corrected, unit-length apex spectrum."""

    t_r: float
    spectrum: NDArray[np.float64]


def _index_at(times: NDArray[np.float64], time: float) -> int:
    return int(np.argmin(np.abs(times - time)))


def fingerprints(
    path: Path, peaks: Sequence[Peak], times: NDArray[np.float64]
) -> tuple[Fingerprint, ...]:
    """Apex spectra for ``peaks``, each less the spectrum at its own leading limit.

    The PDA baseline climbs steeply through a gradient — the mobile phase absorbs — so
    a raw apex spectrum is the compound plus wherever in the gradient it happened to
    elute. Subtracting the spectrum at the foot of the same peak removes the eluent and
    leaves the compound, which is what has to be comparable between runs.
    """
    if not peaks:
        return ()
    apices = [peak.apex_index for peak in peaks]
    feet = [_index_at(times, peak.start_time) for peak in peaks]
    wanted = np.array(apices + feet, dtype=np.int64)
    spectra = read_spectra(path, wanted)
    corrected = spectra[: len(peaks)] - spectra[len(peaks) :]
    out: list[Fingerprint] = []
    for peak, spectrum in zip(peaks, corrected, strict=True):
        norm = float(np.linalg.norm(spectrum))
        unit = spectrum / norm if norm > 0.0 else spectrum
        out.append(Fingerprint(t_r=peak.t_r, spectrum=unit))
    return tuple(out)


def similarity_matrix(
    queries: Sequence[Fingerprint], references: Sequence[Fingerprint]
) -> NDArray[np.float64]:
    """Cosine similarity of every query against every reference, on the shared axis.

    The batches carry 115, 148 and 309 channels of the same grid, so the shorter axis
    is the common one — verified identical channel for channel over its whole length.
    """
    if not queries or not references:
        return np.zeros((len(queries), len(references)), dtype=np.float64)
    width = min(min(f.spectrum.size for f in queries), min(f.spectrum.size for f in references))
    left = np.array([f.spectrum[:width] for f in queries], dtype=np.float64)
    right = np.array([f.spectrum[:width] for f in references], dtype=np.float64)
    left /= np.maximum(np.linalg.norm(left, axis=1, keepdims=True), np.finfo(np.float64).eps)
    right /= np.maximum(np.linalg.norm(right, axis=1, keepdims=True), np.finfo(np.float64).eps)
    return left @ right.T

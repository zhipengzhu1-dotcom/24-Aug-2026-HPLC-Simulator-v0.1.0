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
absorbance shape is a property of the compound. Peaks are then matched to the scouting
run's peaks by cosine similarity, one-to-one.

The similarity score travels with the assignment, and a weak match is reported rather
than resolved: this module proposes, and the driver signs off before any peak table is
written.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import linear_sum_assignment

from scripts.arw import read_spectra
from scripts.integrate import Peak

# Below this, an assignment is reported as doubtful rather than silently accepted.
# Different compounds on one column routinely score above 0.9 against each other, so
# this is a floor on absurdity, not a proof of identity — which is why the driver
# signs off and this module never decides alone.
WEAK_MATCH = 0.98


@dataclass(frozen=True)
class Fingerprint:
    """One peak's baseline-corrected, unit-length apex spectrum."""

    t_r: float
    spectrum: NDArray[np.float64]


@dataclass(frozen=True)
class Assignment:
    """One measured peak, the reference it matched, and how well."""

    peak: Peak
    name: str
    similarity: float

    @property
    def doubtful(self) -> bool:
        return self.similarity < WEAK_MATCH


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


def assign(
    peaks: Sequence[Peak],
    queries: Sequence[Fingerprint],
    references: Sequence[Fingerprint],
    names: Sequence[str],
) -> tuple[Assignment, ...]:
    """Match peaks to reference compounds one-to-one, by spectrum and not by order.

    The best total-similarity pairing is taken rather than each peak's own best match,
    so two peaks cannot both claim the same compound. Peaks beyond the reference count
    are left unnamed — a system peak or a contaminant is a real possibility on every
    one of these runs and inventing a compound for it would be worse than saying so.
    """
    if len(references) != len(names):
        raise ValueError(
            f"one name per reference is required; got {len(names)} for {len(references)}"
        )
    scores = similarity_matrix(queries, references)
    if scores.size == 0:
        return tuple(Assignment(peak=peak, name="", similarity=0.0) for peak in peaks)
    rows, columns = linear_sum_assignment(-scores)
    matched = {
        int(row): (names[int(column)], float(scores[row, column]))
        for row, column in zip(rows, columns, strict=True)
    }
    return tuple(
        Assignment(
            peak=peak,
            name=matched.get(index, ("", 0.0))[0],
            similarity=matched.get(index, ("", 0.0))[1],
        )
        for index, peak in enumerate(peaks)
    )

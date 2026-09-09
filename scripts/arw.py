"""Reading Waters Empower 3 `.arw` PDA exports.

The format carries **no metadata**: row 0 is the wavelength axis, row 1 is the literal
`Time`, and every row after that is one time point — time in minutes, then one
absorbance per wavelength. Tab-delimited, CR line endings, 20 Hz. There is no sample
name, no injection id, no date and no gradient table anywhere in the file, so a run's
identity is never read from it; it is established outside and recorded in provenance.

Files run to 269 MB, so rows are streamed rather than read whole, and a data row is
split only as far as the wanted column. The sha256 is accumulated in the same pass:
the raw file is the provenance of every number downstream, and a checksum computed in
a second read is a checksum of a file that may have moved.

Nominal wavelengths are not on the grid. The axis is 210.0668 + n x 0.6093, so "220 nm"
is really 219.8182 and "254 nm" is 254.0824. :func:`nearest_channel` returns the actual
value and it travels with the trace, so no output can imply an exactness the instrument
never offered.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

# 4 MiB: large enough that the read is not the bottleneck, small enough that the
# decoded buffer never approaches the size of the file.
_CHUNK_BYTES = 1 << 22

_WAVELENGTH_LABEL = "Wavelength"
_TIME_LABEL = "Time"


@dataclass(frozen=True)
class Channel:
    """One PDA wavelength column, named by the wavelength it actually holds."""

    index: int
    nm: float

    @property
    def label(self) -> str:
        return f"{self.nm:.4f} nm"


@dataclass(frozen=True)
class Trace:
    """One run read at one channel, with the provenance of the file it came from."""

    times: NDArray[np.float64]
    signal: NDArray[np.float64]
    channel: Channel
    source: Path
    sha256: str
    wavelengths: NDArray[np.float64]

    @property
    def sampling_hz(self) -> float:
        """Points per second, from the median step — the export is evenly spaced."""
        return 1.0 / (float(np.median(np.diff(self.times))) * 60.0)

    @property
    def run_time_min(self) -> float:
        return float(self.times[-1])


def _rows(path: Path, hasher: hashlib._Hash) -> Iterator[str]:
    """Yield non-blank CR-separated rows, hashing the bytes as they go by."""
    buffer = ""
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(_CHUNK_BYTES)
            if not chunk:
                break
            hasher.update(chunk)
            buffer += chunk.decode("ascii", errors="replace")
            *complete, buffer = buffer.split("\r")
            for row in complete:
                if row.strip():
                    yield row
    if buffer.strip():
        yield buffer


def nearest_channel(wavelengths: NDArray[np.float64], target_nm: float) -> Channel:
    """The single column closest to ``target_nm`` — never an interpolation."""
    index = int(np.argmin(np.abs(wavelengths - target_nm)))
    return Channel(index=index, nm=float(wavelengths[index]))


def _read_axis(rows: Iterator[str], path: Path) -> NDArray[np.float64]:
    header = next(rows)
    fields = header.split("\t")
    if fields[0].strip() != _WAVELENGTH_LABEL:
        raise ValueError(f"{path.name}: expected a {_WAVELENGTH_LABEL!r} row 0, got {fields[0]!r}")
    label = next(rows)
    if label.strip() != _TIME_LABEL:
        raise ValueError(f"{path.name}: expected a {_TIME_LABEL!r} row 1, got {label.strip()!r}")
    return np.array([float(field) for field in fields[1:]], dtype=np.float64)


def read_channel(path: Path, target_nm: float) -> Trace:
    """Read one run at the channel nearest ``target_nm``."""
    hasher = hashlib.sha256()
    rows = _rows(path, hasher)
    wavelengths = _read_axis(rows, path)
    channel = nearest_channel(wavelengths, target_nm)
    # split() with maxsplit=n returns n+1 parts, the last being the unsplit remainder,
    # so the wanted field at position index+1 needs one split beyond it.
    maxsplit = channel.index + 2
    times: list[float] = []
    signal: list[float] = []
    for row in rows:
        cells = row.split("\t", maxsplit)
        times.append(float(cells[0]))
        signal.append(float(cells[channel.index + 1]))
    return Trace(
        times=np.array(times, dtype=np.float64),
        signal=np.array(signal, dtype=np.float64),
        channel=channel,
        source=path,
        sha256=hasher.hexdigest(),
        wavelengths=wavelengths,
    )


def read_spectra(path: Path, row_indices: NDArray[np.int64]) -> NDArray[np.float64]:
    """Full spectra at the given data-row indices, one row per index, in that order.

    A second pass over the file. Peak apices are not known until the channel has been
    integrated, and holding the whole matrix to avoid this pass would cost gigabytes.
    """
    wanted = {int(index) for index in row_indices}
    if not wanted:
        return np.empty((0, 0), dtype=np.float64)
    hasher = hashlib.sha256()
    rows = _rows(path, hasher)
    wavelengths = _read_axis(rows, path)
    found: dict[int, NDArray[np.float64]] = {}
    for position, row in enumerate(rows):
        if position in wanted:
            cells = row.split("\t")
            found[position] = np.array(cells[1:], dtype=np.float64)
            if len(found) == len(wanted):
                break
    missing = sorted(wanted - set(found))
    if missing:
        raise ValueError(f"{path.name}: no data row at index {missing[0]}")
    if any(len(spectrum) != len(wavelengths) for spectrum in found.values()):
        raise ValueError(f"{path.name}: a data row is not as wide as the wavelength axis")
    return np.array([found[int(index)] for index in row_indices], dtype=np.float64)

# Traces — the signal each measured number was read off

One CSV per run: `time_min` and the absorbance at the single PDA channel that run was
measured at. About 0.7 MB each, 20 Hz, in AU.

These exist so that a measured width, area or resolution can be re-derived from the
repository alone. Until 2026-09-09 every number in `validation/` was typed in by hand
from Empower's on-screen report, and nothing on record could be checked.

**The raw `.arw` exports are not in the repository.** They are 3-D PDA matrices running
to 269 MB each, 1.3 GB for the set, against a 1 GB Git LFS allowance — driver's
decision, 2026-09-09. `MANIFEST.csv` records each raw file's name, sha256 and byte
count, so the copy the numbers came from can be identified and checked; the raw lives
outside the repo under `validation/Waters Data/`.

To regenerate everything from the raw:

```bash
uv run python -m scripts.measure_runs --raw-root "<folder holding the .arw files>"
```

That writes the traces, the peak tables and this manifest. `scripts/arw.py` reads the
export, `scripts/integrate.py` measures the peaks and `scripts/assign.py` proposes
identities from apex spectra; `tests/test_arw.py` is their gate.

## Channels

Neither nominal wavelength exists on the instrument's grid, so the file names carry the
channel that was actually read:

| sample | nominal | actual channel | why |
|---|---|---|---|
| four-peak (`Validation_2/`) | 220 nm | **219.8182 nm** | 220.4275 is the other neighbour, 0.43 nm away against 0.18 |
| three-peak (`validation/`) | 254 nm | **254.0824 nm** | 253.4681 is 0.53 nm away against 0.08 |

The three-peak sample cannot be read at 220 nm: an eluent envelope with W½ of 2.5–10.8
min swamps the channel. The four-peak sample's first two compounds all but vanish at
254 nm (0.8 % and 0.5 % of the cluster's area against 20.7 % and 13.1 % at 220 nm).

"""The den Uijl et al. 2021 scanning-gradient sets as fixtures (research doc §1, §2).

M. J. den Uijl et al., *J. Chromatogr. A* **1636** (2021) 461780, CC BY 4.0;
peak tables from supplementary Section S-2, conditions from article Sections
2.2–2.3. Every number below is transcribed from
`docs/research/validation-datasets.md`, which is the citable transcription —
this module is deliberately a restatement of those tables and nothing else, and
`test_reality.py` asserts that cell-for-cell rather than trusting the eye.

Two independent datasets from the same paper: Set X is "representative for
common practice", Set Y was acquired for maximum precision. They differ in
instrument, column, flow rate, buffer and — the part that matters to an engine —
in whether there is a pre-gradient hold and in how t0 was established.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from hplcsim.model import Gradient, Method, Peak, Run


@dataclass(frozen=True)
class ScanningGradientSet:
    """One published tG-series: shared conditions plus tR for every compound at every tG.

    ``retention`` maps compound -> retention times aligned with ``gradient_times``,
    so each row reads in the same order as the published table.
    """

    name: str
    method: Method
    phi0: float
    phif: float
    t_init: float
    gradient_times: tuple[float, ...]
    retention: Mapping[str, tuple[float, ...]]
    unretained: tuple[str, ...]

    @property
    def fittable(self) -> tuple[str, ...]:
        """Compounds carrying gradient information — the unretained ones are excluded."""
        return tuple(c for c in self.retention if c not in self.unretained)

    def run(self, t_gradient: float) -> Run:
        return Run(
            Gradient(phi0=self.phi0, phif=self.phif, t_gradient=t_gradient, t_init=self.t_init),
            name=f"{self.name} tG{t_gradient:g}",
        )

    def t_r(self, compound: str, t_gradient: float) -> float:
        if t_gradient not in self.gradient_times:
            raise ValueError(
                f"{self.name} has no run at tG = {t_gradient:g} min; "
                f"published gradient times are {self.gradient_times}"
            )
        return self.retention[compound][self.gradient_times.index(t_gradient)]

    def peak(self, compound: str, t_gradient_run1: float, t_gradient_run2: float) -> Peak:
        """The compound as a scouting-pair observation across two of the published runs."""
        return Peak(
            t_r_run1=self.t_r(compound, t_gradient_run1),
            t_r_run2=self.t_r(compound, t_gradient_run2),
            name=compound,
        )


# Uracil, Cytosine, Tyramine and Peptide 1 elute at or near t0 at every gradient time in
# both sets: their tR is flat across tG, so they carry no gradient information and the LSS
# fit is undefined for them (research doc §1.2). Kept in the tables as a negative fixture.
_UNRETAINED = ("Uracil", "Cytosine", "Tyramine", "Peptide 1")


# --- Set X (research doc §1.1–1.2) -------------------------------------------------
#
# Kinetex C18 50 × 2.1 mm 1.7 µm, 0.5 mL/min. t0 = 0.262 min (uracil; extra-column time
# is already folded into the published V0). Vd = 0.128 mL → tD = 0.256 min. Buffer/ACN
# 95:5 → 5:95, i.e. φ = 0.05 → 0.95, *not* 0 → 1. 0.25 min isocratic hold before the ramp.

SET_X = ScanningGradientSet(
    name="den Uijl Set X",
    method=Method(t0=0.262, t_dwell=0.256, flow=0.5),
    phi0=0.05,
    phif=0.95,
    t_init=0.25,
    gradient_times=(1.5, 3.0, 3.75, 4.5, 6.0, 7.5, 9.0, 12.0),
    retention={
        # Mean of 10 replicates, min — supplementary Tables S-3 to S-10.
        "Indigotin": (1.657, 2.379, 2.705, 3.018, 3.610, 4.169, 4.706, 5.724),
        "Purpurin": (1.646, 2.360, 2.683, 2.992, 3.577, 4.130, 4.659, 5.666),
        "Emodin": (1.764, 2.590, 2.967, 3.329, 4.019, 4.673, 5.307, 6.515),
        "Toluene": (1.714, 2.443, 2.764, 3.066, 3.627, 4.140, 4.628, 5.517),
        "Propylparaben": (1.515, 2.109, 2.374, 2.625, 3.098, 3.538, 3.954, 4.740),
        "Uracil": (0.260, 0.262, 0.262, 0.262, 0.263, 0.263, 0.261, 0.263),
        "Sudan I": (2.085, 3.181, 3.687, 4.171, 5.101, 5.986, 6.839, 8.474),
        "Rutin": (1.083, 1.357, 1.483, 1.602, 1.829, 2.039, 2.243, 2.627),
        "Martius Yellow": (1.453, 2.017, 2.272, 2.514, 2.975, 3.406, 3.817, 4.589),
        "Naphthol Yellow S": (1.083, 1.324, 1.429, 1.525, 1.700, 1.862, 2.005, 2.263),
        "Orange IV": (1.407, 1.978, 2.243, 2.498, 2.988, 3.459, 3.914, 4.787),
        "Flavazine L": (1.386, 1.927, 2.178, 2.419, 2.882, 3.326, 3.751, 4.569),
        "Picric Acid": (1.276, 1.655, 1.818, 1.965, 2.240, 2.486, 2.709, 3.102),
        "Fast Red B": (1.217, 1.621, 1.807, 1.983, 2.332, 2.666, 2.977, 3.570),
        "Tyramine": (0.366, 0.366, 0.369, 0.369, 0.367, 0.367, 0.366, 0.367),
        "Cytosine": (0.214, 0.215, 0.218, 0.217, 0.217, 0.216, 0.217, 0.218),
        "Trimethoprim": (1.027, 1.206, 1.279, 1.347, 1.472, 1.575, 1.673, 1.845),
        "Propranolol": (1.237, 1.635, 1.812, 1.982, 2.303, 2.599, 2.886, 3.420),
        "Peptide 1": (0.372, 0.371, 0.372, 0.372, 0.371, 0.372, 0.373, 0.371),
        "Peptide 2": (0.988, 1.137, 1.198, 1.252, 1.353, 1.442, 1.526, 1.673),
        # tG = 4.5 is 1.521, not the published 1.6210: Table S-6 replicate 7 reads 2.523
        # against 1.520–1.522 for the other nine — a mis-integration in the supplement,
        # and the only such cell in either set. The value here is the mean of the other
        # nine (research doc §1.2). The published mean makes a correct engine look 7% off.
        "Peptide 3": (1.040, 1.290, 1.408, 1.521, 1.735, 1.936, 2.130, 2.514),
        "Peptide 4": (1.081, 1.343, 1.460, 1.569, 1.774, 1.968, 2.155, 2.514),
        "Peptide 5": (1.122, 1.436, 1.577, 1.711, 1.965, 2.203, 2.428, 2.859),
    },
    unretained=_UNRETAINED,
)


# --- Set Y (research doc §2.1–2.2) -------------------------------------------------
#
# Zorbax SB C18 50 × 4.6 mm 5 µm, 2.5 mL/min. Vd = 0.081 mL → tD = 0.0324 min. 5 → 85% B
# against neat ACN, i.e. φ = 0.05 → 0.85 (Δφ = 0.80). No pre-gradient hold.
#
# **t0 = 0.229 min, the measured uracil time — not the paper's stated column dead time of
# 0.171 min.** The 0.058 min gap is extra-column volume (the system carried a 2D-LC
# valve). Feeding the bare column dead time leaves a systematic +0.41% bias with the same
# signature as a dropped hold (research doc §2.1); the uracil value lumps the
# extra-column time in and takes the mean signed error to +0.04%. Set X does not pose the
# question — there the stated t0 and the measured uracil time already agree.

SET_Y = ScanningGradientSet(
    name="den Uijl Set Y",
    method=Method(t0=0.229, t_dwell=0.0324, flow=2.5),
    phi0=0.05,
    phif=0.85,
    t_init=0.0,
    gradient_times=(1.0, 1.5, 3.0, 3.75, 4.5, 6.0, 7.5, 9.0, 12.0, 18.0),
    retention={
        # Mean of 10 replicates, min, at 4 decimals as published.
        "Uracil": (0.2299, 0.2299, 0.2294, 0.2289, 0.2289, 0.2292, 0.2289, 0.2290, 0.2288, 0.2286),
        "Tyramine": (
            0.3083,
            0.3182,
            0.3320,
            0.3358,
            0.3379,
            0.3418,
            0.3440,
            0.3456,
            0.3482,
            0.3498,
        ),
        "Flavazine L": (
            0.3600,
            0.4010,
            0.5005,
            0.5410,
            0.5764,
            0.6398,
            0.6924,
            0.7385,
            0.8149,
            0.9301,
        ),
        "Trimethoprim": (
            0.4937,
            0.5833,
            0.7951,
            0.8830,
            0.9627,
            1.1053,
            1.2315,
            1.3439,
            1.5424,
            1.8622,
        ),
        "Propranolol": (
            0.7137,
            0.8964,
            1.3707,
            1.5838,
            1.7862,
            2.1669,
            2.5232,
            2.8600,
            3.4915,
            4.6295,
        ),
        "Berberine": (
            0.7952,
            0.9962,
            1.5122,
            1.7424,
            1.9609,
            2.3714,
            2.7552,
            3.1193,
            3.8033,
            5.0433,
        ),
        "Propylparaben": (
            0.8573,
            1.0992,
            1.7212,
            1.9976,
            2.2592,
            2.7486,
            3.2038,
            3.6331,
            4.4333,
            5.8643,
        ),
        "Toluene": (1.0375, 1.3435, 2.1245, 2.4679, 2.7904, 3.3873, 3.9349, 4.4451, 5.3750, 6.9835),
        "Sudan I": (
            1.3316,
            1.7426,
            2.9242,
            3.4709,
            3.9969,
            5.0040,
            5.9643,
            6.8906,
            8.6662,
            11.9944,
        ),
        # Cytosine sits *below* uracil — excluded on the same grounds as the other three.
        "Cytosine": (
            0.1899,
            0.1896,
            0.1891,
            0.1890,
            0.1891,
            0.1893,
            0.1891,
            0.1890,
            0.1890,
            0.1883,
        ),
        "Naphthol Yellow S": (
            0.3595,
            0.4002,
            0.4994,
            0.5393,
            0.5754,
            0.6379,
            0.6904,
            0.7359,
            0.8126,
            0.9267,
        ),
        "Rutin": (0.4860, 0.5897, 0.8585, 0.9796, 1.0938, 1.3092, 1.5112, 1.6997, 2.0541, 2.6883),
        "Martius Yellow": (
            0.7238,
            0.9283,
            1.4611,
            1.7010,
            1.9285,
            2.3560,
            2.7556,
            3.1321,
            3.8358,
            5.0942,
        ),
        "Orange IV": (
            0.7293,
            0.9475,
            1.5410,
            1.8155,
            2.0801,
            2.5883,
            3.0737,
            3.5403,
            4.4351,
            6.1069,
        ),
        "Purpurin": (
            0.9506,
            1.2325,
            1.9722,
            2.3072,
            2.6267,
            3.2315,
            3.8006,
            4.3418,
            5.3658,
            7.2431,
        ),
        "Emodin": (1.0399, 1.3643, 2.2292, 2.6254, 3.0059, 3.7300, 4.4176, 5.0763, 6.3327, 8.6647),
        "Peptide 1": (
            0.3065,
            0.3160,
            0.3319,
            0.3356,
            0.3389,
            0.3427,
            0.3465,
            0.3474,
            0.3523,
            0.3529,
        ),
        "Peptide 2": (
            0.4500,
            0.5257,
            0.7080,
            0.7835,
            0.8532,
            0.9765,
            1.0861,
            1.1839,
            1.3608,
            1.6319,
        ),
        "Peptide 5": (
            0.5740,
            0.7142,
            1.0830,
            1.2491,
            1.4082,
            1.7074,
            1.9895,
            2.2584,
            2.7686,
            3.6808,
        ),
    },
    unretained=_UNRETAINED,
)

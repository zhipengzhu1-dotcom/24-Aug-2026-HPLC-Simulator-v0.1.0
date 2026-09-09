"""PROTOTYPE — throwaway. Three variants of a peak sign-off screen.

THE QUESTION: what does a chromatographer need on screen to accept or reject a peak
integration and name the peaks?

Today that loop is: an agent renders matplotlib PNGs by hand, sends them, the driver
judges in chat, and the answers get hardcoded into `scripts/measure_runs.py`. That
survived four runs. Issue #150 has thirteen.

Three variants, switchable from the floating bar at the bottom, deliberately disagreeing
about what the *unit* of the screen is:

    A — Contact sheet.  The unit is the PEAK. Every peak in the run as a small multiple,
                        integration shaded, accept/reject on each. Triage speed.
    B — Chromatogram.   The unit is the RUN. One large trace, click a peak to select it,
                        one detail panel with the spectrum comparison. Judgement depth.
    C — Ledger.         The unit is the DATASET. Every peak of all four runs in one dense
                        table with sparklines. Consistency across runs -- which is #150's
                        actual problem.

Run it:

    uv run --extra app streamlit run prototype/peak_signoff_prototype.py

Not the v0.3 Cockpit feature (SPEC §11 "CSV import + auto peak-matching"). This is a
throwaway asking one question. No tests, no error handling, no abstractions.

Decisions are written to a scratch file named PROTOTYPE-signoff-decisions.json, which is
meant to be deleted. Nothing here writes to `validation/`.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as st

# Streamlit puts the script's own folder on sys.path, not the repo root, so the bench
# tooling is invisible without this. pytest gets the same thing from pyproject.toml.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.arw import read_channel  # noqa: E402
from scripts.assign import fingerprints, similarity_matrix  # noqa: E402
from scripts.integrate import capacity_factor, measure  # noqa: E402

RAW_ROOT = Path(
    "/Users/maracchi/Desktop/Claude/24-Aug-2026 HPLC Simulator v0.1.0/"
    "validation/Waters Data/OneDrive_1_9-9-2026"
)
DECISIONS = Path("PROTOTYPE-signoff-decisions.json")
T0, DWELL = 0.525, 0.9375
VOID = T0 + DWELL

RUNS = {
    "four-peak · 50 %B": (
        "08-Sep-2026 Gradients/Export Data Points23045-50%_Cannabinoid.arw",
        220.0,
        "four",
    ),
    "four-peak · 75 %B": (
        "08-Sep-2026 Gradients/Export Data Points23048_75%_Cannabinoid.arw",
        220.0,
        "four",
    ),
    "three-peak · 50 %B": (
        "08-Sep-2026 Gradients/Export Data Points23051_50% Nitroso.arw",
        254.0,
        "three",
    ),
    "three-peak · 75 %B": (
        "08-Sep-2026 Gradients/Export Data Points23054_75% Nitroso.arw",
        254.0,
        "three",
    ),
}
SCOUTING = {
    "four": (
        "Export Data Points22956.arw",
        220.0,
        (13.219, 13.317, 13.517, 13.584),
        ("Unknown-1", "Unknown-2", "Unknown-3", "Unknown-4"),
    ),
    "three": (
        "25-Sep-2026 v0.1.0 Validation/Export Data Points22783_tG15.arw",
        254.0,
        (9.855, 11.592, 16.159),
        ("Unknown-1", "Unknown-2", "Unknown-3"),
    ),
}


@dataclass
class Row:
    t_r: float
    area: float
    height: float
    w_half: float
    tailing: float | None
    k_prime: float
    start: float
    end: float
    rs_to_next: float | None
    usp_rs_to_next: float | None
    area_pct: float
    best_name: str
    best_score: float
    all_scores: dict[str, float]


@st.cache_data(show_spinner="Reading the export…")
def load(label: str) -> tuple[list[float], list[float], list[dict[str, object]], float, str]:
    relative, nm, family = RUNS[label]
    trace = read_channel(RAW_ROOT / relative, nm)
    result = measure(trace)

    ref_rel, ref_nm, ref_times, ref_names = SCOUTING[family]
    ref_trace = read_channel(RAW_ROOT / ref_rel, ref_nm)
    ref_peaks = [
        min(measure(ref_trace).peaks, key=lambda p, t=t: abs(p.t_r - t)) for t in ref_times
    ]
    reference = fingerprints(RAW_ROOT / ref_rel, ref_peaks, ref_trace.times)
    queries = fingerprints(RAW_ROOT / relative, result.peaks, trace.times)
    scores = similarity_matrix(queries, reference)

    rs_next = {id(pair.earlier): pair.rs for pair in result.pairs}
    usp_next = {id(pair.earlier): pair.usp_resolution for pair in result.pairs}
    total = sum(peak.area for peak in result.peaks) or 1.0
    rows: list[dict[str, object]] = []
    for peak, score_row in zip(result.peaks, scores, strict=True):
        by_name = {name: float(v) for name, v in zip(ref_names, score_row, strict=True)}
        best = max(by_name, key=lambda n: by_name[n]) if by_name else ""
        rows.append(
            asdict(
                Row(
                    t_r=peak.t_r,
                    area=peak.area * 6e7,
                    height=peak.height * 1e6,
                    w_half=peak.w_half,
                    tailing=peak.tailing,
                    k_prime=capacity_factor(peak.t_r, T0, DWELL),
                    start=peak.start_time,
                    end=peak.end_time,
                    rs_to_next=rs_next.get(id(peak)),
                    usp_rs_to_next=usp_next.get(id(peak)),
                    area_pct=100.0 * peak.area / total,
                    best_name=best,
                    best_score=by_name.get(best, 0.0),
                    all_scores=by_name,
                )
            )
        )
    # Decimate for drawing only; every number above came off the full trace.
    step = max(1, trace.times.size // 6000)
    return (
        trace.times[::step].tolist(),
        (trace.signal[::step] * 1e3).tolist(),
        rows,
        trace.channel.nm,
        ",".join(ref_names),
    )


def window(
    times: list[float], signal: list[float], lo: float, hi: float
) -> tuple[list[float], list[float]]:
    t = np.asarray(times)
    mask = (t >= lo) & (t <= hi)
    return t[mask].tolist(), np.asarray(signal)[mask].tolist()


def trace_figure(times, signal, rows, lo, hi, height=260, selected=None, shade=True):
    x, y = window(times, signal, lo, hi)
    fig = go.Figure()
    fig.add_scatter(x=x, y=y, mode="lines", line={"width": 1.2, "color": "#1f3b73"}, name="")
    if shade:
        for index, row in enumerate(rows):
            if row["end"] < lo or row["start"] > hi:
                continue
            colour = "#b3541e" if selected in (None, index) else "#c9c2b8"
            fig.add_vrect(
                x0=row["start"], x1=row["end"], fillcolor=colour, opacity=0.16, line_width=0
            )
    if lo <= VOID <= hi:
        fig.add_vline(x=VOID, line={"color": "green", "width": 1, "dash": "dash"})
    fig.update_layout(
        height=height,
        margin={"l": 40, "r": 10, "t": 10, "b": 30},
        showlegend=False,
        xaxis_title="min",
        yaxis_title="mAU",
    )
    return fig


def decision_key(label: str, index: int) -> str:
    return f"{label}||{index}"


def read_decisions() -> dict[str, dict[str, str]]:
    if DECISIONS.exists():
        return json.loads(DECISIONS.read_text())
    return {}


def write_decisions(decisions: dict[str, dict[str, str]]) -> None:
    DECISIONS.write_text(json.dumps(decisions, indent=2, sort_keys=True))


def namer(
    label: str, index: int, row: dict[str, object], names: list[str], key_suffix: str
) -> None:
    """The one control every variant must offer: name it, or refuse to."""
    decisions = st.session_state.decisions
    key = decision_key(label, index)
    current = decisions.get(key, {}).get("name", "")
    options = ["— unassigned —", *names]
    choice = st.selectbox(
        f"tR {row['t_r']:.3f}",
        options,
        index=options.index(current) if current in options else 0,
        key=f"sel-{key}-{key_suffix}",
        label_visibility="collapsed",
    )
    decisions[key] = {
        "name": "" if choice == options[0] else choice,
        "t_r": f"{row['t_r']:.3f}",
        "spectral_match": f"{row['best_score']:.3f}",
    }


# ---------------------------------------------------------------- A: contact sheet
def variant_a(label, times, signal, rows, names) -> None:
    """The unit is the PEAK. Every peak as a small multiple; judge each on its own."""
    st.caption(
        "Every peak in the run, same size, integration limits shaded. Nothing about the "
        "run as a whole — the question each cell asks is 'is this one integrated right?'"
    )
    columns = st.columns(3)
    for index, row in enumerate(rows):
        pad = max(0.12, (row["end"] - row["start"]) * 1.4)
        with columns[index % 3]:
            st.plotly_chart(
                trace_figure(
                    times,
                    signal,
                    rows,
                    row["start"] - pad,
                    row["end"] + pad,
                    height=170,
                    selected=index,
                ),
                use_container_width=True,
                key=f"a-{label}-{index}",
            )
            void = (
                " ⚠︎ before the void"
                if row["k_prime"] < 0
                else (" · k′ < 1" if row["k_prime"] < 1 else "")
            )
            st.markdown(
                f"**{row['t_r']:.3f} min**{void}  \n"
                f"area {row['area']:,.0f} · W½ {row['w_half']:.4f} · k′ {row['k_prime']:.2f}  \n"
                f"best match **{row['best_name']}** {row['best_score']:.3f}"
            )
            namer(label, index, row, names, "a")
            st.divider()


# ---------------------------------------------------------------- B: chromatogram-first
def variant_b(label, times, signal, rows, names) -> None:
    """The unit is the RUN. One trace, one selected peak, one deep detail panel."""
    st.caption(
        "The whole run first, because where a peak sits in the gradient is most of what "
        "tells you whether it is a compound. Pick one peak; everything below is about it."
    )
    picked = st.radio(
        "peak",
        list(range(len(rows))),
        format_func=lambda i: f"{rows[i]['t_r']:.3f} min  (k′ {rows[i]['k_prime']:.2f})",
        horizontal=True,
        key=f"b-pick-{label}",
    )
    st.plotly_chart(
        trace_figure(times, signal, rows, 0.0, max(times), height=300, selected=picked),
        use_container_width=True,
        key=f"b-full-{label}",
    )
    row = rows[picked]
    left, right = st.columns([3, 2])
    with left:
        pad = max(0.15, (row["end"] - row["start"]) * 2.0)
        st.plotly_chart(
            trace_figure(
                times,
                signal,
                rows,
                row["start"] - pad,
                row["end"] + pad,
                height=260,
                selected=picked,
            ),
            use_container_width=True,
            key=f"b-zoom-{label}",
        )
    with right:
        st.metric("retention time", f"{row['t_r']:.3f} min")
        a, b = st.columns(2)
        a.metric(
            "k′",
            f"{row['k_prime']:.2f}",
            delta=None if row["k_prime"] >= 1 else "in the void",
            delta_color="inverse",
        )
        b.metric("W½", f"{row['w_half']:.4f}")
        a.metric("area", f"{row['area']:,.0f}")
        b.metric("tailing", "—" if row["tailing"] is None else f"{row['tailing']:.2f}")
        st.write("**spectral match against the scouting run**")
        for name, score in sorted(row["all_scores"].items(), key=lambda kv: -kv[1]):
            st.progress(max(0.0, min(1.0, score)), text=f"{name}  {score:.3f}")
        namer(label, picked, row, names, "b")


# ---------------------------------------------------------------- C: ledger
def variant_c(label, times, signal, rows, names) -> None:
    """The unit is the DATASET. All four runs at once; the trace shrinks to a sparkline."""
    st.caption(
        "Every peak of every run in one table, because the thing that goes wrong across "
        "thirteen runs is inconsistency between them, not a bad integration in one."
    )
    for run_label in RUNS:
        run_times, run_signal, run_rows, channel_nm, name_csv = load(run_label)
        run_names = name_csv.split(",")
        st.markdown(f"###### {run_label} · {channel_nm:.4f} nm")
        header = st.columns([2, 1.4, 1.4, 1.2, 1.2, 1.2, 2.2, 2.4])
        for column, title in zip(
            header, ["", "tR", "k′", "W½", "area", "Rs→", "best match", "call it"], strict=True
        ):
            column.caption(title)
        for index, row in enumerate(run_rows):
            cells = st.columns([2, 1.4, 1.4, 1.2, 1.2, 1.2, 2.2, 2.4])
            pad = max(0.10, (row["end"] - row["start"]) * 1.2)
            spark = trace_figure(
                run_times,
                run_signal,
                run_rows,
                row["start"] - pad,
                row["end"] + pad,
                height=54,
                selected=index,
                shade=False,
            )
            spark.update_layout(
                margin={"l": 0, "r": 0, "t": 0, "b": 0},
                xaxis={"visible": False},
                yaxis={"visible": False},
            )
            cells[0].plotly_chart(spark, use_container_width=True, key=f"c-{run_label}-{index}")
            cells[1].write(f"{row['t_r']:.3f}")
            cells[2].write(f"{row['k_prime']:.2f}" + (" ⚠︎" if row["k_prime"] < 1 else ""))
            cells[3].write(f"{row['w_half']:.4f}")
            cells[4].write(f"{row['area']:,.0f}")
            cells[5].write("—" if row["rs_to_next"] is None else f"{row['rs_to_next']:.2f}")
            cells[6].write(f"{row['best_name']} {row['best_score']:.3f}")
            with cells[7]:
                namer(run_label, index, row, run_names, "c")
        st.divider()


VARIANTS = {
    "A": ("Contact sheet — the peak is the unit", variant_a),
    "B": ("Chromatogram — the run is the unit", variant_b),
    "C": ("Ledger — the dataset is the unit", variant_c),
}


def switcher(current: str) -> None:
    keys = list(VARIANTS)
    position = keys.index(current)
    previous, following = keys[position - 1], keys[(position + 1) % len(keys)]
    st.markdown(
        f"""
        <style>
        .proto-bar {{
            position: fixed; bottom: 18px; left: 50%; transform: translateX(-50%);
            z-index: 999; background: #1f1f1f; color: #fff; border-radius: 999px;
            padding: 8px 18px; box-shadow: 0 6px 22px rgba(0,0,0,.35);
            font: 600 13px -apple-system, system-ui, sans-serif; white-space: nowrap;
        }}
        .proto-bar a {{ color: #ffd08a; text-decoration: none; padding: 0 12px; }}
        </style>
        <div class="proto-bar">
          <a href="?variant={previous}" target="_self">←</a>
          PROTOTYPE · {current} — {VARIANTS[current][0]}
          <a href="?variant={following}" target="_self">→</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="PROTOTYPE · peak sign-off", layout="wide")
    if "decisions" not in st.session_state:
        st.session_state.decisions = read_decisions()

    current = st.query_params.get("variant", "D").upper()
    if current not in VARIANTS:
        current = "D"

    st.title("Peak sign-off — PROTOTYPE")
    st.caption(
        "Throwaway. Asking one question: what do you need on screen to accept or reject "
        "an integration and name the peaks? Flip variants with the bar at the bottom."
    )

    if current == "C":
        variant_c("", [], [], [], [])
    else:
        label = st.selectbox("run", list(RUNS), key="run-pick")
        times, signal, rows, channel_nm, name_csv = load(label)
        st.caption(f"{channel_nm:.4f} nm · {len(rows)} peaks · void + dwell at {VOID:.3f} min")
        VARIANTS[current][1](label, times, signal, rows, name_csv.split(","))

    named = sum(1 for value in st.session_state.decisions.values() if value.get("name"))
    st.sidebar.metric("peaks named", named)
    st.sidebar.write(f"decisions file: `{DECISIONS}`")
    if st.sidebar.button("Write decisions", type="primary"):
        write_decisions(st.session_state.decisions)
        st.sidebar.success(f"wrote {len(st.session_state.decisions)} rows")
    st.sidebar.json(st.session_state.decisions, expanded=False)

    switcher(current)


# ------------------------------------------------- D: chromatogram over a proper table
INTEGRATION_METHOD = """
**Apex-first — the ApexTrack family, not Traditional.**

*Detection* finds apices by prominence on a smoothed trace; Traditional integration
instead detects on a slope threshold with timed events, and no slope threshold is used
here to detect anything. *Limits* are walked outward from each apex to liftoff and
touchdown — ApexTrack's shape, though ApexTrack proper takes both from the second
derivative where this uses prominence for the apex and a flank criterion for the limits
(steep, then flattened; or a valley more than 3× the noise above the lowest point the
walk reached). *Baseline and splitting* are Empower's default and common to both
algorithms: one straight baseline per cluster between its outer limits, perpendicular
drop at the interior valleys — chosen so the cross-check against the instrument's own
report is like-for-like.

Every value is measured on the **unsmoothed** trace; smoothing serves detection and
slopes only. Rs is Δt/(2(σ₁+σ₂)) with σ from W½ — the definition the engine predicts in.
USP Rs is built from real inflection tangents struck down to the baseline, and is
recorded, never asserted.
"""


def variant_d(label, times, signal, rows, names) -> None:
    """The unit is the RUN, read through a table. B's chromatogram over C's columns."""
    selected = st.session_state.get(f"d-sel-{label}", 0)
    selected = min(selected, max(0, len(rows) - 1))

    st.plotly_chart(
        trace_figure(times, signal, rows, 0.0, max(times), height=380, selected=selected),
        use_container_width=True,
        key=f"d-full-{label}",
    )

    table = [
        {
            "#": index + 1,
            "RT (min)": round(row["t_r"], 3),
            "Area": round(row["area"]),
            "% Area": round(row["area_pct"], 2),
            "Height": round(row["height"]),
            "W½ (min)": round(row["w_half"], 4),
            "Tailing": None if row["tailing"] is None else round(row["tailing"], 2),
            "Rs → next": None if row["rs_to_next"] is None else round(row["rs_to_next"], 2),
            "USP Rs → next": (
                None if row["usp_rs_to_next"] is None else round(row["usp_rs_to_next"], 2)
            ),
            "k′": round(row["k_prime"], 2),
            "Match": row["best_name"],
            "Score": round(row["best_score"], 3),
            "Name": st.session_state.decisions.get(decision_key(label, index), {}).get("name", ""),
        }
        for index, row in enumerate(rows)
    ]

    event = st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"d-table-{label}",
        column_config={
            "Area": st.column_config.NumberColumn(format="%d", help="µAU·s"),
            "Height": st.column_config.NumberColumn(format="%d", help="µAU"),
            "k′": st.column_config.NumberColumn(help="below 1 the peak is in the void"),
            "Score": st.column_config.NumberColumn(
                format="%.3f", help="cosine similarity to the scouting spectrum"
            ),
        },
    )
    picked = event.selection.rows
    if picked:
        selected = picked[0]
        st.session_state[f"d-sel-{label}"] = selected

    row = rows[selected]
    left, right = st.columns([3, 2])
    with left:
        pad = max(0.15, (row["end"] - row["start"]) * 2.0)
        st.plotly_chart(
            trace_figure(
                times,
                signal,
                rows,
                row["start"] - pad,
                row["end"] + pad,
                height=240,
                selected=selected,
            ),
            use_container_width=True,
            key=f"d-zoom-{label}",
        )
    with right:
        st.markdown(
            f"**Peak {selected + 1} — {row['t_r']:.3f} min**"
            + (
                "  ·  ⚠︎ before the void"
                if row["k_prime"] < 0
                else ("  ·  k′ < 1, in the void" if row["k_prime"] < 1 else "")
            )
        )
        st.caption(f"integrated {row['start']:.3f} → {row['end']:.3f} min")
        for name, score in sorted(row["all_scores"].items(), key=lambda kv: -kv[1]):
            st.progress(max(0.0, min(1.0, score)), text=f"{name}  {score:.3f}")
        namer(label, selected, row, names, "d")

    with st.expander("Integration method"):
        st.markdown(INTEGRATION_METHOD)


# Registered here rather than in the dict above: `variant_d` is defined after it.
VARIANTS = {
    "D": ("Chromatogram over a table — the layout the driver asked for", variant_d),
    **VARIANTS,
}

main()

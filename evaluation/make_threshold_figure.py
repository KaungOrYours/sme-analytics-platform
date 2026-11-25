"""Render the leave-one-dataset-out threshold-spread figure.

The claim this figure supports is comparative: each diagnostic's refitted
optimum is stable or unstable *relative to the anchor its own source publishes*,
and those anchors span two orders of magnitude (0.1 to 10). Plotting absolute
thresholds on one axis would therefore hide the comparison. The x axis is the
ratio fitted/anchor on a log scale, so the published anchor is 1.0 for every
rule and distance from it is directly comparable; each row is annotated with
its absolute anchor so nothing is concealed by the normalisation.

Counts are encoded by marker area because the distribution is heavily tied --
one value can hold 23 of the 25 folds -- and a stack of 23 dots would not fit a
row. Every value holding three or more folds carries its count as a direct
label, so the size channel never has to be read off a legend.

Reads evaluation/results/study3_recalibration_scores.json only; computes
nothing new. Output location is configurable so this module does not hard-code
a path to a manuscript tree that is not part of the repository.

Run from the REPO ROOT:
    backend/venv/bin/python3 -m evaluation.make_threshold_figure --out <dir>
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS = Path(__file__).resolve().parent / "results" / "study3_recalibration_scores.json"
DEFAULT_OUT_DIR = Path(__file__).resolve().parent.parent / "build" / "figures"

# Display names, and which rule the library actually ships today.
# Plain strings, not TeX: this renders through matplotlib's own text layer, so
# an escaped underscore would print the backslash.
LABELS = {
    "fold_contamination": "fold_contamination",
    "evalml_cov": "evalml_cov",
    "np": "$n/p$",
    "epv": "EPV",
    "sigma_cv": "$\\sigma_{CV}$",
    "evalml_range": "evalml_range",
}
SHIPPED = "evalml_range"

INK = "#1b2733"        # single data colour; the figure has one series
RULE = "#8a949e"       # recessive reference line and grid
SURFACE = "white"      # ring colour that separates overlapping marks


def load():
    payload = json.loads(RESULTS.read_text())
    rows = []
    for key, block in payload["rq8"].items():
        anchor = block["anchor"]["threshold"]
        fitted = [r["fitted_threshold"] for r in block["recalibrated_oos"]["per_dataset"]]
        counts = Counter(round(v, 6) for v in fitted)
        mode, n_mode = counts.most_common(1)[0]
        rows.append(
            {
                "key": key,
                "anchor": anchor,
                "counts": counts,
                "n_folds": len(fitted),
                "mode": mode,
                "n_mode": n_mode,
            }
        )
    # Most-concentrated first; this also places the shipped rule last, which is
    # the point of the figure rather than a presentational choice.
    rows.sort(key=lambda r: -r["n_mode"])
    return rows


def render(rows, out_dir):
    fig, ax = plt.subplots(figsize=(6.6, 2.95))
    ys = list(range(len(rows)))[::-1]

    for y, row in zip(ys, rows):
        if row["key"] == SHIPPED:
            ax.axhspan(y - 0.42, y + 0.42, color=RULE, alpha=0.13, zorder=0, linewidth=0)
        for value, count in sorted(row["counts"].items()):
            ratio = value / row["anchor"]
            ax.scatter(
                ratio, y,
                s=14 + 12 * count,
                facecolor=INK, edgecolor=SURFACE, linewidth=0.9,
                zorder=3 + (count == row["n_mode"]), clip_on=False,
            )
            # Only the modal pile is labelled in place. Labelling every value
            # would collide at the ties this distribution is full of, and the
            # right margin already states the modal count in words.
            if count == row["n_mode"] and count >= 10:
                ax.annotate(
                    str(count), (ratio, y),
                    color=SURFACE, fontsize=7.0, fontweight="bold",
                    ha="center", va="center", zorder=6,
                )

    ax.axvline(1.0, color=RULE, linestyle=(0, (4, 3)), linewidth=1.2, zorder=1)
    ax.annotate(
        "published anchor",
        xy=(1.06, len(rows) - 0.45), xytext=(1.06, len(rows) - 0.45),
        fontsize=8, color="#55606b", va="bottom", ha="left",
    )

    ax.set_yticks(ys)
    ax.set_yticklabels([LABELS[r["key"]] for r in rows], fontsize=9)
    for tick, row in zip(ax.get_yticklabels(), rows):
        if row["key"] == SHIPPED:
            tick.set_fontweight("bold")

    ax.set_xscale("log")
    ax.set_xlim(0.065, 3.4)
    ax.set_xticks([0.1, 0.25, 0.5, 1, 2])
    ax.set_xticklabels([r"$0.1\times$", r"$0.25\times$", r"$0.5\times$", r"$1\times$", r"$2\times$"],
                       fontsize=8.5)
    ax.set_xlabel("refitted threshold, as a multiple of the published anchor (log scale)", fontsize=9)
    ax.set_ylim(-0.8, len(rows) - 0.05)

    ax.xaxis.grid(True, color=RULE, alpha=0.28, linewidth=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", color=RULE, labelcolor="#33404c")

    # Right-margin annotation: the absolute anchor and the modal fold count, so
    # the normalised axis never has to be reversed by the reader.
    for y, row in zip(ys, rows):
        anchor = row["anchor"]
        anchor_txt = f"{anchor:g}"
        weight = "bold" if row["key"] == SHIPPED else "normal"
        ax.annotate(
            f"anchor {anchor_txt}   {row['n_mode']}/{row['n_folds']} at mode",
            xy=(1.02, y), xycoords=("axes fraction", "data"),
            fontsize=8, color="#33404c", va="center", ha="left",
            fontweight=weight, annotation_clip=False,
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        path = out_dir / f"threshold_spread.{ext}"
        fig.savefig(path, bbox_inches="tight", dpi=300)
        print(f"  Written: {path}")
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=None,
                        help="directory for the figure "
                             "(default: $FIGURE_OUT_DIR, else ./build/figures)")
    args = parser.parse_args(argv)
    out_dir = Path(args.out or os.environ.get("FIGURE_OUT_DIR") or DEFAULT_OUT_DIR)
    rows = load()
    for r in rows:
        print(f"  {r['key']:20s} anchor={r['anchor']:<6g} mode={r['mode']:<10.4f} "
              f"({r['n_mode']}/{r['n_folds']})  ratio={r['mode']/r['anchor']:.3f}")
    render(rows, out_dir)


if __name__ == "__main__":
    main()

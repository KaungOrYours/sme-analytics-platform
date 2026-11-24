"""The P1-P14 pre-registered predictions and their dispositions, as a LaTeX table.

Every disposition here was RE-DERIVED from the stored run records, not carried
over from the results documents. That mattered: five recorded dispositions were
wrong or absent, and two of those errors would have propagated into the paper had
the table been transcribed.

Where a verdict turned on a confidence interval it was adjudicated at the
DATASET-CLUSTERED level, because runs are nested in datasets. Three verdicts or
their supporting evidence move when the unit of analysis is corrected; those are
noted inline.

The dispositions are judgements, so they live here as reviewed data rather than
being parsed out of prose by a script. The figures that decide them are all
reproducible from evaluation/results/.

Imported by build_appendix_tables.py; not a standalone entry point.
"""

from __future__ import annotations

# (id, statement, decisive figure, our disposition, previously recorded, note)
PREDICTIONS = [
    (
        "P1",
        r"EPV$<$10 beats $n/p<10$ on Group C",
        r"MCC $+0.141$ vs $+0.540$; paired clustered $-0.387\,[-0.619,-0.142]$",
        "REFUTED",
        "Refuted",
        r"refutation \emph{strengthens} under clustering: neither arm alone excludes "
        r"zero, but the paired difference does",
    ),
    (
        "P2",
        r"fold\_contam.\ positive under duplicates, and beats $n/p$ and $\sigma_{\mathrm{CV}}$",
        r"fires on 54 of 54 duplicate runs; matrix degenerate; MCC $0.000$",
        "REFUTED",
        "Refuted",
        r"fails deterministically rather than statistically --- with no within-condition "
        r"variance a positive MCC is unobtainable by construction",
    ),
    (
        "P3",
        r"evalml\_range fires on close to no runs; evalml\_cov fires more but is not discriminative",
        r"fires $0.0\%$ / $6.3\%$ / $15.9\%$; evalml\_cov clustered $[-0.048,0.406]$ and $[-0.173,0.623]$",
        "PARTIAL",
        "Split",
        r"CORRECTED. The recorded refutation of the evalml\_cov clause rests on run-level "
        r"intervals; both contain zero once clustered, so that clause is not falsified",
    ),
    (
        "P4",
        r"pessimism base rate exceeds optimism under outliers, and some diagnostic is positive",
        r"$42.6\%$ vs $13.0\%$ on Group C; best MCC $+0.042$, no interval excludes zero",
        "PARTIAL",
        "Partially supported",
        r"with 9 clusters the cell can only separate an MCC of about $0.22$ from zero; "
        r"underpowered to detect, not absent",
    ),
    (
        "P5",
        r"the three CV-variance diagnostics each exceed AUROC $0.6$ in every family, while "
        r"$n/p$ and fold\_contam.\ do not",
        r"$n/p$ reaches $0.936$ / $0.870$ / $0.649$ / $0.810$ --- above $0.6$ in all four families",
        "PARTIAL",
        "Confirmed",
        r"CORRECTED. P5 is conjunctive and its clause about $n/p$ fails. The refuting "
        r"evidence was already printed in the same table as the verdict",
    ),
    (
        "P6",
        r"evalml\_range ranks among the strongest by threshold-free AUROC while firing on "
        r"under $10\%$ of runs",
        r"AUROC $0.694$, indistinguishable from the top four; fires on $15.9\%$",
        "PARTIAL",
        "Partially supported",
        r"",
    ),
    (
        "P7",
        r"recalibration materially helps evalml\_range and EPV, and helps $\sigma_{\mathrm{CV}}$ less",
        r"gains $-0.161$, $+0.005$, $-0.140$; only $\sigma_{\mathrm{CV}}$ excludes zero",
        "REFUTED",
        "Refuted",
        r"verdict unchanged but its evidence moves: the $-0.161$ collapse does not exclude "
        r"zero when paired and clustered, while $\sigma_{\mathrm{CV}}$'s $-0.140$ does",
    ),
    (
        "P8",
        r"fold\_contam.\ is not rescued by recalibration: out-of-sample MCC stays at or below zero",
        r"$+0.192$, dataset-clustered $[+0.073,+0.319]$",
        "REFUTED",
        r"``requires care''",
        r"CORRECTED. A non-disposition replaced by the verdict the pre-registered criterion "
        r"implies. The confound argument is retained as interpretation",
    ),
    (
        "P9",
        r"thresholds transfer to the 8 larger datasets with reduced but still positive MCC",
        r"$-0.037$, $0.000$ (zero firings), $+0.197$; all 9 positives in one dataset",
        "REFUTED",
        "Refuted on MCC",
        r"CORRECTED. $35.8\%$ of dataset-clustered resamples contain no positive case, so "
        r"the quantity is NOT ESTIMABLE at the correct unit; this sample could not have "
        r"confirmed P9 either",
    ),
    (
        "P10",
        r"$n/p$'s out-of-sample MCC falls well below its $+0.540$ on Group C",
        r"LODO $+0.246\,[+0.065,+0.411]$ against $+0.540$",
        "CONFIRMED",
        "Confirmed",
        r"strengthened: $+0.540$'s own clustered interval already contains $0.246$, so the "
        r"shrinkage lies inside the original figure's uncertainty",
    ),
    (
        "P11",
        r"within-dataset concordance rises with $R$ and clears $0.5$ in two families",
        r"$0.332 \to 0.301 \to 0.265$, monotonically \emph{decreasing}",
        "REFUTED",
        "Refuted",
        r"not a power failure: the estimators demonstrably differ, and the measured effect "
        r"runs the other way",
    ),
    (
        "P12",
        r"concordance stays inside the observed band and the $R{=}20$ interval does not "
        r"exclude chance from below",
        r"$0.301$ and $0.265$, interval $[0.174,0.371]$, containing the algebraic floor $0.258$",
        "CONFIRMED",
        "Confirmed",
        r"CORRECTED reasoning. There is no wording defect --- the phrase was read one way in "
        r"P11 and the opposite way here. And $0.5$ is the wrong null: the permutation floor "
        r"is $0.258$, so the clause holds on either reading",
    ),
    (
        "P13",
        r"between-dataset $\rho$ is substantially unchanged across $R$",
        r"$0.811$ / $0.790$ / $0.800$ / $0.790$; paired clustered changes all contain zero",
        "CONFIRMED",
        "Confirmed",
        r"",
    ),
    (
        "P14",
        r"decoupled concordance is at least $0.5$ and materially above the coupled figures",
        r"$0.265\,[0.178,0.358]$",
        "REFUTED",
        "Refuted",
        r"",
    ),
]

ROW_END = r" \\"


def predictions_table():
    """LaTeX lines for the P1-P14 appendix block."""
    tally = {}
    for row in PREDICTIONS:
        tally[row[3]] = tally.get(row[3], 0) + 1
    corrected = sum(1 for row in PREDICTIONS if row[5].startswith("CORRECTED"))
    changed = sum(1 for row in PREDICTIONS if row[3] != row[4].upper())

    out = [
        r"\paragraph{Pre-registered predictions and their dispositions.} All fourteen,",
        r"including the seven our own data refuted. \textbf{Every disposition below was",
        r"re-derived from the stored run records rather than carried forward}, and where a",
        r"verdict turned on an interval it was adjudicated at the dataset level.",
        rf"\textbf{{{corrected}}} previously recorded dispositions were wrong or absent and",
        rf"are marked CORRECTED; \textbf{{{changed}}} differ from what we previously reported.",
        "",
        r"\begin{center}\scriptsize",
        r"\begin{tabular}{llp{0.28\textwidth}ll}",
        r"\toprule",
        r"& Prediction & Decisive figure & Disposition & Previously" + ROW_END,
        r"\midrule",
    ]
    for pid, statement, figure, ours, recorded, note in PREDICTIONS:
        shown = r"\textbf{" + ours + "}" if ours != recorded.upper() else ours
        out.append(f"{pid} & {statement} & {figure} & {shown} & {recorded}" + ROW_END)
        if note:
            out.append(
                r"& \multicolumn{4}{p{0.78\textwidth}}{\itshape " + note + "}" + ROW_END
            )
    out += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{center}",
        "",
        r"\medskip",
        r"\noindent Tally: "
        + ", ".join(
            rf"\textbf{{{count}}} {label.lower()}"
            for label, count in sorted(tally.items(), key=lambda kv: -kv[1])
        )
        + r".",
        "",
        r"\noindent By study, \textbf{Study 2 returns no fully confirmed prediction}: four",
        r"partially supported and two refuted. We previously reported this as ``four of six",
        r"refuted or only partially supported''; the correct count is six of six, and the",
        r"sentence that followed it --- naming the two that survived --- has no referent and",
        r"is withdrawn.",
        "",
    ]
    return out

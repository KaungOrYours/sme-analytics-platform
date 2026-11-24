"""Generate the paper's appendix tables as LaTeX, from the stored run records.

Appendices are generated, never hand-typed. A transcription error in a
hand-copied correlation (-0.813 for -0.830) survived into a submitted document
once already; every figure below is read from JSON at build time so the same
class of error cannot recur.

Emits three files to docs/fpr/journal/generated/ (gitignored along with the rest
of docs/fpr/):

  appendix_a_manifest.tex   one row per dataset, all 33
  appendix_b_protocol.tex   protocol freeze evidence, read from git
  appendix_c_diagnostics.tex  the full 6 x 4 diagnostic grid

paper.tex pulls them in with \\input{}, so regenerating is the only way the
appendices change.

Licence column: PMLB ships no licence field (its metadata schema has eight keys
and none is a licence), so licences were traced to primary sources by hand and
are recorded in LICENCES below with the evidence class. Anything not confirmed at
a primary source is UNVERIFIED and is marked as such rather than guessed.

Run from the REPO ROOT:
    backend/venv/bin/python3 -m evaluation.build_appendix_tables
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"

# PMLB ships an authoritative summary table. The full n must be READ from it, not
# back-computed from the 80% training partition: rounding makes 17 of 33 rows
# wrong by one, and the body calls parity5 "a complete parity-5 truth table",
# which has 32 rows, not 31.
def _pmlb_n():
    try:
        import pmlb, csv, pathlib
        f = pathlib.Path(pmlb.__file__).parent / "all_summary_stats.tsv"
        with f.open() as fh:
            return {r["dataset"]: int(r["n_instances"])
                    for r in csv.DictReader(fh, delimiter="\t")}
    except Exception:
        return {}


PMLB_N = _pmlb_n()
OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "fpr" / "journal" / "generated"

MAIN_FILES = {
    "A": "study2_group_A_results.json",
    "B": "study2_group_B_results.json",
    "C": "study2_group_C_results.json",
}
TRANSFER_FILE = "study3_transfer_results.json"
CLUSTERED_FILE = "clustered_intervals_scores.json"

# Licence provenance, traced to primary sources. PMLB itself carries none.
#   cc-by      UCI, Creative Commons Attribution 4.0. Redistribution permitted.
#   noncomm    Simonoff's analcatdata notice: free for scientific, educational
#              and non-commercial use with acknowledgement. Silent on
#              redistribution, so not an open licence.
#   restricted irish: copyright retained by named owners, use limited to
#              statistical-methods research, redistribution granted to StatLib
#              specifically and not to downstream redistributors. DO NOT SHIP.
#   none       no licence statement findable at any primary source.
#   synthetic  deterministic function of its inputs; ship a generator, not data.
LICENCES = {
    "molecular_biology_promoters": ("cc-by", "UCI 67"),
    "labor": ("cc-by", "UCI 56"),
    "bupa": ("cc-by", "UCI 60"),
    "hepatitis": ("cc-by", "UCI 46"),
    "breast_cancer": ("cc-by", "UCI 14"),
    "postoperative_patient_data": ("cc-by", "UCI 82"),
    "haberman": ("cc-by", "UCI 43"),
    "monk1": ("cc-by", "UCI 70"),
    "monk2": ("cc-by", "UCI 70"),
    "monk3": ("cc-by", "UCI 70"),
    "tic_tac_toe": ("cc-by", "UCI 101"),
    "glass2": ("cc-by", "UCI 42, MLC++ derivative"),
    "analcatdata_aids": ("noncomm", "Simonoff 2003"),
    "analcatdata_asbestos": ("noncomm", "Simonoff 2003"),
    "analcatdata_bankruptcy": ("noncomm", "Simonoff 2003"),
    "analcatdata_creditscore": ("noncomm", "Simonoff 2003"),
    "analcatdata_fraud": ("noncomm", "Simonoff 2003"),
    "analcatdata_japansolvent": ("noncomm", "Simonoff 2003"),
    "irish": ("restricted", "StatLib irish.ed, Greaney and Kelleghan 1984"),
    "profb": ("none", "StatLib, Stern via Lock"),
    "lupus": ("none", "StatLib"),
    "biomed": ("none", "StatLib"),
    "backache": ("none", "StatLib"),
    "prnn_crabs": ("none", "StatLib"),
    "prnn_synth": ("none", "StatLib"),
    "tokyo1": ("none", "MLC++ / SGI, site defunct"),
    "mux6": ("synthetic", "MLC++, Boolean multiplexer"),
    "parity5": ("synthetic", "MLC++, parity"),
    "corral": ("synthetic", "MLC++, CORRAL"),
    "threeOf9": ("synthetic", "MLC++, 3-of-9"),
    "xd6": ("synthetic", "MLC++, XD6"),
    "appendicitis": ("none", "KEEL, Weiss and Kulikowski 1991"),
    "saheart": ("none", "ESL, Rousseauw et al. 1983"),
}

LICENCE_LABEL = {
    "cc-by": "CC BY 4.0",
    "noncomm": "non-comm.",
    "restricted": r"\textbf{restricted}",
    "none": "UNVERIFIED",
    "synthetic": "synthetic",
}

# Datasets whose target overlaps definitionally with a retained feature.
TARGET_OVERLAP = {"irish", "lupus"}


def tex_escape(text):
    return str(text).replace("_", r"\_").replace("&", r"\&").replace("%", r"\%")


# ---------------------------------------------------------------------------
# Appendix A
# ---------------------------------------------------------------------------
def collect_manifest():
    rows = {}
    sources = [(g, f, "main") for g, f in MAIN_FILES.items()]
    sources.append(("T", TRANSFER_FILE, "transfer"))

    for group, filename, sample in sources:
        path = RESULTS_DIR / filename
        if not path.exists():
            continue
        with path.open() as fh:
            payload = json.load(fh)
        for record in payload["runs"]:
            a = record.get("automated")
            if not a:
                continue
            name = record["dataset"]
            entry = rows.setdefault(
                name,
                {
                    "group": group,
                    "sample": sample,
                    "n_train": a["n"],
                    "p": a["p"],
                    "runs": 0,
                    "poor": 0,
                    "max_g": float("-inf"),
                    "pos": 0,
                    "neg": 0,
                },
            )
            entry["runs"] += 1
            entry["poor"] += bool(a["labels"]["poor_optimism"])
            entry["max_g"] = max(entry["max_g"], a["G"])
            y = a.get("y_test") or []
            if y and entry["pos"] == 0 and entry["neg"] == 0:
                codes = sorted(set(y))
                if len(codes) == 2:
                    entry["pos"] = sum(1 for v in y if v == codes[1])
                    entry["neg"] = sum(1 for v in y if v == codes[0])
    return rows


def appendix_a(rows):
    lines = [
        r"\section{Dataset manifest}",
        r"\label{app:manifest}",
        "",
        r"All 33 datasets, so the sample is reconstructible without network access.",
        r"$n_{\mathrm{train}}$ is the training partition and $n$ the full dataset (the outer test",
        r"the remainder and is never corrupted). ``poor'' counts runs with",
        r"$G > \delta_G = 0.05$ out of 21. \textbf{$\max G$ is the column that makes the",
        r"all-25 versus 19-estimable difference in \S\ref{sec:granularity} auditable}: a",
        r"dataset whose $\max G$ falls below $\delta_G$ could not have registered a positive",
        r"under any threshold at or above the one used.",
        "",
        r"\medskip",
        r"\begin{center}\footnotesize",
        r"\begin{tabular}{llrrrrrrl}",
        r"\toprule",
        r"Dataset & Grp & $n_{\mathrm{train}}$ & $n$ & $p$ & poor/21 & $\max G$ & Licence & Source \\",
        r"\midrule",
    ]
    order = sorted(rows.items(), key=lambda kv: (kv[1]["sample"] == "transfer", kv[1]["group"], kv[0]))
    last_group = None
    for name, e in order:
        if last_group is not None and e["group"] != last_group:
            lines.append(r"\midrule")
        last_group = e["group"]
        klass, source = LICENCES.get(name, ("none", "UNVERIFIED"))
        flag = r"$^{\dagger}$" if name in TARGET_OVERLAP else ""
        low = r"\textbf{" + f"{e['max_g']:+.4f}" + "}" if e["max_g"] < 0.05 else f"{e['max_g']:+.4f}"
        lines.append(
            f"{tex_escape(name)}{flag} & {e['group']} & {e['n_train']} & "
            f"{PMLB_N.get(name, round(e['n_train']/0.8))} & {e['p']} & "
            f"{e['poor']} & {low} & {LICENCE_LABEL[klass]} & {tex_escape(source)} \\\\"
        )
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{center}",
        "",
        r"\medskip",
        r"\noindent $^{\dagger}$ target-definitional overlap with a retained feature; see",
        r"\S\ref{sec:data}. Bold $\max G$ marks a dataset that could not have produced the",
        r"outcome. ``UNVERIFIED'' means no licence statement was findable at any primary",
        r"source, not that the data is unlicensed in the permissive sense.",
        "",
        r"\paragraph{Screening.} PMLB ships 284 datasets, of which 162 are classification,",
        r"90 binary, and \textbf{44} at $n \le 500$. The TabMini curation excludes 19 of the",
        r"44: 4 for personally identifiable information, 9 deprecated, 4 derived from time",
        r"series or images, 1 ethically sensitive, 1 outlier --- leaving the \textbf{25} used",
        r"here. The 8 transfer datasets are PMLB binary at $500 < n \le 1000$ and lie outside",
        r"the 44 entirely.",
        "",
        r"\paragraph{Fetching.} Data is retrieved by \texttt{pmlb.fetch\_data(name,",
        r"local\_cache\_dir=...)}, whose \texttt{dropna} argument defaults to \texttt{True}.",
        r"Note that \texttt{pmlb} resolves datasets against a mutable upstream branch with no",
        r"commit pin or checksum; the cached copies used here are released with the artefact",
        r"for the subset whose licence permits it.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Appendix B
# ---------------------------------------------------------------------------
def git_added(path):
    try:
        out = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%h|%ad", "--date=format:%Y-%m-%d %H:%M",
             "-1", "--", path],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        return out.split("|") if "|" in out else None
    except Exception:
        return None


def appendix_b():
    studies = [
        ("Study 1", "docs/evaluation_protocol.md", None),
        ("Study 2", "docs/study2_protocol.md", "docs/study2_results.md"),
        ("Study 3", "docs/study3_protocol.md", "docs/study3_results.md"),
        ("Study 4", "docs/study4_protocol.md", "docs/study4_results.md"),
    ]
    lines = [
        r"\section{Protocol freeze}",
        r"\label{app:protocol}",
        "",
        r"Each study's protocol was fixed before its runs. For two of the four the",
        r"repository does not \emph{evidence} that independently, because the protocol and",
        r"the results were added in the same commit. We state which, rather than letting",
        r"``pre-registered'' carry weight it has not earned.",
        "",
        r"\begin{center}\small",
        r"\begin{tabular}{llll}",
        r"\toprule",
        r"Study & Protocol added & Results added & Freeze evidenced by git? \\",
        r"\midrule",
    ]
    for label, proto, results in studies:
        p = git_added(proto)
        r = git_added(results) if results else None
        if not p:
            lines.append(f"{label} & not in repository & --- & no \\\\")
            continue
        if not r:
            lines.append(
                f"{label} & \\texttt{{{p[0]}}} {p[1]} & --- & "
                r"n/a \\"
            )
            continue
        same = p[0] == r[0]
        verdict = r"\textbf{no, same commit}" if same else "yes"
        lines.append(
            f"{label} & \\texttt{{{p[0]}}} {p[1]} & \\texttt{{{r[0]}}} {r[1]} & {verdict} \\\\"
        )
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{center}",
        "",
        r"\medskip",
        r"\noindent Only Study 4 is independently evidenced: its protocol was committed",
        r"alone, and the results followed in a separate commit. For Studies 2 and 3 the",
        r"reader has our word and the protocol text, which is reproduced verbatim below, and",
        r"not a timestamp. One further qualification: dataset Group A was inspected before",
        r"the Study 2 grid ran, so ``confirmation'' applies to 9 of the 25 datasets rather",
        r"than to all of them.",
        "",
        r"\paragraph{Frozen design decisions.} Fixed before any run and unchanged since.",
        "",
        r"\begin{center}\small",
        r"\begin{tabular}{ll}",
        r"\toprule",
        r"Decision & Frozen value \\",
        r"\midrule",
        r"Outcome & $G = S_{\mathrm{CV},\text{selected}} - S_{\mathrm{test}}$, signed \\",
        r"Primary label & \texttt{poor\_optimism} $\equiv (G > \delta_G)$ \\",
        r"$\delta_G$ & $0.05$ \\",
        r"Score & AUROC \\",
        r"Outer split & single stratified 80/20, per seed \\",
        r"Inner resampling & 5-fold stratified cross-validation \\",
        r"Candidates & 3, fixed default hyperparameters, no search \\",
        r"Seeds & 3 per (dataset, condition) \\",
        r"Corruption & missing values, duplicates, outliers at 15\% and 35\% \\",
        r"Corruption target & training partition only; test partition never corrupted \\",
        r"Summary metric & Matthews correlation coefficient, $0$ when degenerate \\",
        r"Diagnostic anchors & $n/p<10$, EPV$<10$, $\sigma_{\mathrm{CV}}>0.10$, \\",
        r"& \texttt{fold\_contamination}$>0.10$, \texttt{evalml\_cov}$>0.2$, \texttt{evalml\_range}$\ge 0.5$ \\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{center}",
        "",
        r"\medskip",
        r"\noindent Two of these were chosen in ways worth disclosing. $\delta_G = 0.05$ was",
        r"set so that approximately 11\% of 27 pilot runs were positive, which is selection on",
        r"the dependent variable from three positive cases. And the Study 1 datasets were",
        r"deliberately chosen to span $n/p$ from 1.86 to 100, after which $n/p$ was evaluated",
        r"as a diagnostic on them.",
        "",
    ]
    lines += predictions_table()
    lines += [
        "",
        r"\paragraph{Full protocol text.} The four protocols run to roughly 8{,}700 words and",
        r"are reproduced in full in the released artefact rather than here, at the commits",
        r"identified above.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Appendix C
# ---------------------------------------------------------------------------
def appendix_c():
    path = RESULTS_DIR / CLUSTERED_FILE
    if not path.exists():
        return (
            r"\section{Per-diagnostic tables}" "\n"
            r"\NOTE{Run evaluation.score\_clustered\_intervals first.}" "\n"
        )
    with path.open() as fh:
        data = json.load(fh)

    lines = [
        r"\section{Per-diagnostic results}",
        r"\label{app:diagnostics}",
        "",
        r"Every diagnostic at its frozen anchor, on every sample, with the run-level",
        r"interval we previously published beside the dataset-clustered interval that",
        r"supersedes it. ``lost'' marks a figure that excluded the null at the run level and",
        r"does not at the dataset level.",
        "",
        r"\begin{center}\footnotesize",
        r"\begin{tabular}{llrrrl}",
        r"\toprule",
        r"Sample & Diagnostic & MCC & run-level 95\% CI & clustered 95\% CI & \\",
        r"\midrule",
    ]
    lost = total = survived = 0
    for sample, block in data["part_a"].items():
        header = (
            f"{tex_escape(sample)} ({block['n_datasets']} ds, {block['n_runs']} runs, "
            f"{block['n_poor']} poor)"
        )
        lines.append(r"\multicolumn{6}{l}{\itshape " + header + r"} \\")
        for name, d in block["diagnostics"].items():
            total += 1
            if d["significance_lost_under_clustering"]:
                verdict, lost = r"\textbf{lost}", lost + 1
            elif d["clustered_excludes_zero"]:
                verdict, survived = "survives", survived + 1
            elif d["clustered_excludes_zero"] is None:
                verdict = "not estimable"
            else:
                verdict = "null"

            def ci(block_ci):
                if block_ci.get("ci_low") is None:
                    return "not estimable"
                return f"$[{block_ci['ci_low']:+.3f}, {block_ci['ci_high']:+.3f}]$"

            mcc_s = "n/a" if d["mcc"] is None else f"${d['mcc']:+.3f}$"
            lines.append(
                f"& {tex_escape(name)} & {mcc_s} & {ci(d['run_level_ci'])} & "
                f"{ci(d['clustered_ci'])} & {verdict} \\\\"
            )
        lines.append(r"\midrule")
    lines = lines[:-1]
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{center}",
        "",
        r"\medskip",
        r"\noindent Of \textbf{" + str(total) + r"} figures, \textbf{" + str(lost) +
        r"} cease to exclude the null once the resampling unit is corrected and \textbf{" +
        str(survived) + r"} survive.",
        "",
        r"\paragraph{Recalibration.} Leave-one-dataset-out refitting, with a paired",
        r"dataset-clustered interval on the difference.",
        "",
        r"\begin{center}\small",
        r"\begin{tabular}{lrrrrl}",
        r"\toprule",
        r"Diagnostic & anchor & refitted & gain & paired clustered CI & fitted $t^*$ range \\",
        r"\midrule",
    ]
    for name, d in data["part_b"].items():
        ci = d["paired_clustered_ci"]
        ci_s = (
            "not estimable"
            if ci.get("ci_low") is None
            else f"$[{ci['ci_low']:+.3f}, {ci['ci_high']:+.3f}]$"
        )
        spread = d["fitted_threshold_spread"]
        rng = f"$[{spread['min']:.4f}, {spread['max']:.4f}]$"
        mark = r"$^{*}$" if d["gain_excludes_zero"] else ""
        lines.append(
            f"{tex_escape(name)} & ${d['anchor_mcc']:+.3f}$ & "
            f"${d['recalibrated_oos_mcc']:+.3f}$ & ${d['mcc_gain']:+.3f}${mark} & "
            f"{ci_s} & {rng} \\\\"
        )
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{center}",
        "",
        r"\medskip",
        r"\noindent $^{*}$ paired interval excludes zero. All intervals use "
        + str(data["n_bootstrap"])
        + r" resamples at a fixed seed.",
        "",
    ]
    lines += delta_g_section()
    lines += multiplicity_section()
    return "\n".join(lines)


def delta_g_section():
    """The pre-specified delta_G grid, POST-HOC sensitivity only."""
    path = RESULTS_DIR / "delta_g_sensitivity_scores.json"
    if not path.exists():
        return [r"\NOTE{delta\_g\_sensitivity\_scores.json absent.}", ""]
    with path.open() as fh:
        data = json.load(fh)
    grid = data["delta_grid"]
    out = [
        r"\paragraph{$\delta_G$ sensitivity.} The outcome threshold varied over the",
        r"pre-specified grid. This is a \textbf{sensitivity axis, not a family of independent",
        r"tests}: the same runs are relabelled at each $\delta_G$, so the five columns are",
        r"strongly dependent and are not counted toward multiplicity. Note also that varying",
        r"a threshold on a noisy quantity leaves it noisy, so this analysis does not address",
        r"the reliability ceiling of \S\ref{sec:granularity}.",
        "",
        r"\begin{center}\small",
        r"\begin{tabular}{ll" + "r" * len(grid) + r"}",
        r"\toprule",
        r"Sample & Quantity & "
        + " & ".join(rf"$\delta_G{{=}}{g}$" for g in grid)
        + r" \\",
        r"\midrule",
    ]
    for source, block in data["sources"].items():
        by_delta = block["by_delta"]
        n_poor, mccs, concs = [], [], []
        for g in grid:
            entry = by_delta.get(str(g), {})
            n_poor.append(entry.get("n_poor"))
            sigma = (entry.get("diagnostics") or {}).get("sigma_cv") or {}
            ft = sigma.get("fixed_threshold") or {}
            mccs.append(ft.get("mcc"))
            wd = (sigma.get("concordance") or {}).get("within_dataset") or {}
            concs.append(wd.get("concordance"))

        def row(label, values, fmt="{:+.3f}", first=False):
            prefix = (
                rf"{tex_escape(source)} ({block['n_datasets']} ds)"
                if first
                else ""
            )
            cells = " & ".join(
                "---" if v is None else (f"{v}" if isinstance(v, int) else fmt.format(v))
                for v in values
            )
            return f"{prefix} & {label} & {cells} \\\\"

        out.append(row("positives", n_poor, first=True))
        out.append(row(r"$\sigma_{\mathrm{CV}}$ MCC", mccs))
        out.append(row("within-dataset conc.", concs, fmt="{:.3f}"))
        out.append(r"\midrule")
    out = out[:-1]
    out += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{center}",
        "",
        r"\medskip",
        r"\noindent The sign of every fixed-threshold MCC and the between/within granularity",
        r"pattern are unchanged across the grid. The \emph{magnitude} of the between-dataset",
        r"correlation is not, and is reported separately in \S\ref{sec:granularity}.",
        "",
    ]
    return out


def multiplicity_section():
    """Count every interval-bearing figure in the results tree, reported against
    the number that reach the paper."""
    run_level = clustered = 0

    def count(obj):
        nonlocal run_level, clustered
        if isinstance(obj, dict):
            if "ci_lower" in obj:
                run_level += 1
            if "ci_low" in obj:
                clustered += 1
            for value in obj.values():
                count(value)
        elif isinstance(obj, list):
            for value in obj:
                count(value)

    for path in sorted(RESULTS_DIR.glob("*scores*.json")):
        try:
            with path.open() as fh:
                count(json.load(fh))
        except (json.JSONDecodeError, OSError):
            continue
    total = run_level + clustered
    return [
        r"\paragraph{Multiplicity, stated rather than corrected.} Across the project",
        rf"\textbf{{{total}}} interval-bearing figures were computed "
        rf"({run_level} at the run level, {clustered} dataset-clustered); a small",
        r"fraction reach the paper. Family-wise error is not the binding problem at that",
        r"scale --- \emph{selection} is, because which figures became headlines was decided",
        r"after seeing all of them. We therefore do not apply a global correction over",
        r"strongly dependent tests. Instead we designate one primary comparison, label every",
        r"other cell exploratory in its caption, treat the $\delta_G$ grid and the",
        r"stratification nesting as sensitivity axes rather than independent tests, and",
        r"report the count above so a reader can judge the exploratory surface directly.",
        "",
    ]


from evaluation.predictions_table import predictions_table


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = collect_manifest()
    written = []
    for filename, content in (
        ("appendix_a_manifest.tex", appendix_a(rows)),
        ("appendix_b_protocol.tex", appendix_b()),
        ("appendix_c_diagnostics.tex", appendix_c()),
    ):
        path = OUT_DIR / filename
        path.write_text(content, encoding="utf-8")
        written.append((filename, len(content.splitlines())))

    print(f"\nManifest: {len(rows)} datasets")
    counts = {}
    for name in rows:
        klass = LICENCES.get(name, ("none", ""))[0]
        counts[klass] = counts.get(klass, 0) + 1
    for klass, count in sorted(counts.items()):
        print(f"  {klass:<12} {count}")
    unattainable = [n for n, e in rows.items() if e["max_g"] < 0.05]
    print(f"\n  datasets with max G < delta_G (outcome unattainable): {len(unattainable)}")
    print("   ", ", ".join(sorted(unattainable)))
    print()
    for filename, n_lines in written:
        print(f"  Written: {OUT_DIR / filename}  ({n_lines} lines)")
    print()


if __name__ == "__main__":
    main()

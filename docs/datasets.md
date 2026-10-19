# Dataset shortlist — drafted 2026-10-19, candidates only, NOT locked

Per `CLAUDE.md` Section 4: ~10 datasets from OpenML-CC18 (small scale, excluding health and
personal-finance data) plus 4-6 public SME-style business datasets from UCI. Selection criteria stated
before looking at results, per `docs/evaluation_protocol.md`.

**Status: candidate list only.** Every row below needs the student to open the actual dataset page and
fill in the "Verify" column — row/feature counts, licence text, and a final exclude/include call — before
this shortlist is locked (see the git-tag convention in `pdm_plan_outline.md` Section 3: tag the commit
where this file is frozen, as evidence the selection wasn't adjusted after seeing results). I have not
asserted exact row/feature counts or licence wording here because I can't verify them without opening
each page myself, and per `CLAUDE.md` Section 3 that's not something to guess.

## Selection criteria (fixed before picking datasets)

- Small scale: roughly under a few thousand rows (matches the "small SME tabular dataset" framing).
- Excludes health and personal-finance data (patient records, disease diagnosis, individual credit
  scoring/loan default) — per supervisor-set scope in `CLAUDE.md` Section 4.
- Public, openly licensed, no personal data — per the ethics section of `CLAUDE.md` Section 4.
- Prefer datasets with a plausible "SME business" framing (sales, inventory, customer behaviour,
  operations) over generic ML-textbook datasets, since the report's framing is SME analytics.

## OpenML-CC18 candidates (study: https://www.openml.org/search?type=study&study_type=task&id=99)

| Dataset (OpenML name) | Domain | Why it's a plausible fit | Verify before locking |
|---|---|---|---|
| `cnae-9` | Business document classification (Brazilian economic-activity codes for companies) | Directly business/SME in origin — company-activity classification | Row/feature counts, licence, confirm not personal data |
| `dresses-sales` | Retail/e-commerce sales attributes | Direct retail-sales framing, small | Row/feature counts, licence, confirm target variable makes sense for the pipeline |
| `eucalyptus` | Forestry/agribusiness seed-lot trial data | Small-business-adjacent (agribusiness), non-health | Row/feature counts, licence |
| `car` | Car evaluation (consumer product acceptability) | Consumer/product-evaluation framing, well-known small benchmark | Row/feature counts, licence |
| `tic-tac-toe` | Game-endgame board states | Not business, but a clean small categorical-only benchmark if a non-business control case is wanted | Confirm whether a non-business dataset belongs in the SME-framed shortlist at all — flag to supervisor |
| `balance-scale` | Psychological/physics scale-balance data | Small classic benchmark, non-health, non-finance | Same question as above — business framing is weak |

Datasets considered and excluded on sight (do not re-add without a reason): `credit-g`, `credit-approval`
(personal-finance — consumer credit scoring); `blood-transfusion-service-center`, `diabetes`, `breast-w`,
`wdbc`, `arrhythmia`, `cmc`, `ilpd`, `analcatdata_dmft` (health); `vote` (politically sensitive personal
data, not business).

`cnae-9` and `dresses-sales` are the strongest fits for the "SME business" framing; `car` is a reasonable
third. `tic-tac-toe` and `balance-scale` are placeholders only if more non-health/non-finance datasets
are needed to reach ~10 — their business framing is weak and should be flagged to Rama rather than
silently included.

## UCI candidates (4-6 needed; archive: https://archive.ics.uci.edu/)

| Dataset | Domain | Why it's a plausible fit | Verify before locking |
|---|---|---|---|
| Wholesale customers | B2B wholesale distributor annual spend by product category | Directly SME/B2B, small, classic UCI set | **Verified 2026-10-19 via UCI's API**: 440 instances, 7 features + 1 target (`Region`), no missing values, area tagged "Business", DOI 10.24432/C5030X, creator Margarida Cardoso (2013). Licence field was empty in the API response — UCI's site states CC BY 4.0 for current datasets, but confirm the exact wording on the repository page itself before citing a licence in the report. All-numeric except `Channel`/`Region` — **no categorical column**, so it can't exercise the `inconsistent_categories` error type in `evaluation/injectors.py`; the final shortlist needs at least one dataset that can. Already wired into `evaluation/datasets.py` as the harness's placeholder dataset. |
| Online Retail (or Online Retail II) | UK online retailer transaction log | Directly retail/e-commerce, matches Myanmar-SME retail use case | Large (500k+ rows) — needs subsampling to match "small dataset" framing; confirm licence at https://archive.ics.uci.edu/dataset/352/online+retail |
| Wine Quality | Production/quality-control data from a beverage producer | Production/QC business framing, non-health (quality score, not consumer health) | Confirm row/feature counts, licence |
| Real estate valuation | Property-valuation features from a real estate business | Business/operations framing, not personal/individual finance (property-level, not person-level) | Confirm this reading is right — re-check it isn't closer to "personal finance" before including |
| Absenteeism at work | HR/workforce absenteeism records from a courier company | Business/HR operations framing | Confirm it isn't sensitive personal (health-adjacent — absence *reasons* may include medical categories) — this one needs a careful ethics read before inclusion |
| Facebook metrics (Moro et al.) | Social-media engagement metrics for a cosmetics brand's Facebook page | Marketing/business-analytics framing | Confirm row/feature counts, licence |

"Absenteeism at work" needs the most careful ethics check — if the absence-reason categories encode
health conditions, it may actually fall under the health exclusion despite the HR framing. Flag this to
Rama rather than deciding unilaterally.

## What's still open

1. Open each dataset's actual page (OpenML or UCI), confirm licence terms, record counts, feature counts,
   and original purpose — fill the "Verify" columns above and move the confirmed facts here.
2. Decide the final ~10 OpenML-CC18 + 4-6 UCI split and which 3-4 get the full protocol (all error types
   x all size levels x all seeds) vs. a lighter single pass — per the Rama corrective action in
   `CLAUDE.md` Section 4.
3. Resolve "Absenteeism at work" and the `vote`/health-adjacent exclusions with Rama if there's any doubt.
4. Fill the four PDM-plan ethics questions (GDPR, UH ethics policy, permission to use, ethical collection)
   per dataset once the shortlist is final — template already in `pdm_plan_outline.md` Section 3.

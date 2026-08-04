# Mapping causing events to the EGRISS identification questions

Which "reason for fleeing" response options does the evidence support putting in front of
respondents in each country — and what local examples should enumerator support materials
give for each one?

Built for the EGRISS methodological paper on identification questions for refugees and IDPs,
supported by a UNHCR Data Innovation Grant.

## What it does NOT do

It does not localise the **instrument**. The response options must stay identical across
countries or IRIS comparability is gone and the data cannot be pooled. What varies by country
is the **enumerator support material** — which options to give worked examples for, and what
those examples should be. Every output keeps those two things apart, and the decision rule
refuses to recommend dropping an option from the questionnaire.

It also does not establish causation. "61% of this country's displacement is drought-attributed"
is a statement about co-occurrence in administrative statistics, not a causal claim about any
individual respondent.

## Quick start

```r
setwd("path/to/this/folder")
source("run_all.R")
```

That runs the analysis in R and then the visualisation layer in Python. Data first —
see [`docs/getting_the_data.md`](docs/getting_the_data.md). Nothing is bundled.

```bash
python3 -m pip install -r prototype-python/requirements.txt
```

If Python is missing, the R analysis still completes and prints what to install. The CSVs,
the xlsx and the ggplot figures do not depend on it.

To rebuild only the maps:

```bash
IDQ_ROOT=$(pwd) python3 prototype-python/run_all.py
```

## The eight response options

| # | Option | Evidence |
|---|---|---|
| 1 | Threat of armed conflict or war | **strong** — UCDP GED state-based, IDMC IAC/NIAC |
| 2 | Widespread violence / breakdown of public order | **good** — IDMC "other situations of violence", ACLED riots, UCDP non-state |
| 3 | Discrimination or persecution | **indirect** — UNHCR recognition rates, V-Dem, documented research |
| 4 | HR violations by authorities | **partial** — UCDP one-sided (state perpetrator), V-Dem; misses all non-lethal repression |
| 5 | Other threats of violence | **residual** — not evidenceable, always retained |
| 6 | Natural disasters | **strong** — IDMC disaster displacement by hazard subtype |
| 7 | Man-made events | **very thin in data, large in reality** — see below |
| 8 | A different threat | **residual** — not evidenceable by design |

## Two maps, one switch

The main output carries two views of the same eight options, switched at the top:

**People displaced** — circles sized by how many people are displaced, sliced by what
displaced them. Magnitude.

**Events that happened** — circles sized by how many events were *recorded*, at country
level or across 1,847 subnational areas. Frequency. Conflict incidents from UCDP GED
(126 countries, 1989+) or ACLED (68 countries) as alternatives, never summed; hazard
records from IDMC.

They disagree, and the disagreement is the finding. Mexico ranks **4th in the world by
recorded events** — 98% of them code 2, widespread violence — and **32nd by displaced
population**. Sudan is the mirror image: 20th by events, 1st by IDPs. Bangladesh is 52nd
by events and 5th by IDPs, because a cyclone is one event and moves millions. A showcard
built only on the population view would give Mexican enumerators no worked example for
the option that describes almost everything happening around them.

## Four findings the pipeline produces

**Code 7 is uncounted, not rare.** Every displacement database returns it as unevidenced
almost everywhere. Human rights investigations across the twenty largest displacement
contexts document 2.36m people — Somalia alone records 1.5m affected by forced eviction
2018–2024, more than the entire global IDMC figure for man-made events. Reporting the zero
without this context would be actively misleading.

**Persecution is dissolved into armed conflict by the classification systems.** IDMC has no
category for it: a Rohingya family displaced by military persecution is recorded as NIAC.
Across 305,363 characters of IDMC's own methodology notes, "persecution", "ethnic",
"discrimination" and "torture" appear zero times. Not rare — absent from the vocabulary.

**Codes 4 and 5 are evidenced by events and by nothing else.** No displacement database
attributes population to state one-sided violence (code 4) or non-state one-sided violence
(code 5) anywhere in the world. UCDP counts both: 23,104 and 41,292 incidents respectively,
5.5% and 9.9% of all recorded events. The population view cannot show either option; the
events view can. That is a direct argument for keeping both in the instrument, and the
clearest case for having built the second view at all.

**Two populations in one country need one showcard.** Uganda's IDPs are 88% disaster-displaced;
its 1.92m hosted refugees are 30% armed conflict. Bangladesh has 5.5m disaster IDPs and 1.18m
Rohingya refugees. A single instrument has to work for both, which is the strongest argument
for localising the *support material* rather than the questions.

## Structure

```
run_all.R                 orchestration — analysis then visuals
R/01_sources.R            ingestion; fetch_*() and read_local_*() per source
R/02_profiles.R           crosswalk + showcard decision rule
R/03_outputs.R            ggplot figures
R/04_dtm.R                IOM DTM — reported reasons, a different class of evidence
R/05_independence.R       what may and may not be combined (errors, not warns)
R/06_visuals.R            calls the Python layer
config/crosswalk.yaml     the crosswalk and every decision taken, as reviewable config
prototype-python/         the interactive maps and explorers
  build_events.py         event counts by cause, country and admin1
docs/                     data acquisition, UCDP access request, qualitative research
outputs/                  generated
```

## Outputs

| File | What |
|---|---|
| `idq_population_by_cause.html` | main map — **two views**: people displaced (six population modes) and events that happened (country / 1,847 admin1 areas, UCDP or ACLED); seven causes, country search, per-country showcard panel, evidence layer |
| `idq_crosswalk_explorer.html` | all 68 source categories and where each lands |
| `idq_subreasons.html` | 66 mechanisms beneath the eight options |
| `idq_evidence_map.html` | counted vs documented |
| `idq_all_causes_map.html` | every cause at once, plus region × cause |
| `showcard_recommendations.csv` | country × code with status, rationale and local examples — also surfaced per country in the map |
| `ucdp_conflict_register.csv` | named conflicts with parties, dates, deaths, regional spread |
| `subnational_displacement_points.csv` | 7,648 geocoded locations, mostly ADM2/ADM3 |
| `admin1_conflict_profiles.csv` | region × cause |

## Things to know before trusting a number

**Sources are never summed.** `R/05_independence.R` holds an explicit relations table and
errors rather than warns. IDMC *derives* its figures from IOM DTM in twelve countries — 100%
of Sudan, 99% of Haiti, 94% of Ethiopia — so treating them as independent corroboration is
circular. ACLED and UCDP code the same underlying events. The one legitimate sum is
IDPs + hosted refugees, which are disjoint by definition.

**Imputed is labelled.** UCDP-based attribution of IDMC's unattributed band is marked as
imputed everywhere it appears, with the method stated per country.

**Wildfire is 99.8% of code 7's total.** It was reassigned from natural to man-made on the
reading that most ignition is human. That is contestable and should be stated wherever the
figure appears.

**IDMC's disaster figures include preventive evacuations.** Flagged, not removed. A week's
evacuation is in the numbers; whether a respondent would call it fleeing a home is exactly
what cognitive testing is for.

## Citation

Cite the underlying sources: UCDP, IDMC, ACLED, UNHCR, V-Dem and IOM DTM each require it.
See `docs/getting_the_data.md`.

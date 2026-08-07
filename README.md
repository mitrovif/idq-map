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
| 3 | Discrimination or persecution | **indirect** — UNHCR recognition rates, V-Dem, documented research; DTM's answer list has no option for it |
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
level or across 2,045 subnational areas. Frequency. Conflict incidents from UCDP GED
(417,968 incidents, 126 countries, 1989+) or ACLED (1,841,683 events, 203 countries) as
alternatives, never summed; hazard records from IDMC.

They disagree, and the disagreement is the finding. Mexico ranks **4th in the world by
recorded events** — 98% of them code 2, widespread violence — and **32nd by displaced
population**. Sudan is the mirror image: 20th by events, 1st by IDPs. Bangladesh is 52nd
by events and 5th by IDPs, because a cyclone is one event and moves millions. A showcard
built only on the population view would give Mexican enumerators no worked example for
the option that describes almost everything happening around them.

## Five findings the pipeline produces

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

**Where people and sources disagree, it is about which violence option.** IOM DTM is the
only source here that asks the household rather than reading an event. Across the twenty
countries it covers, 11 agree with our attribution on the dominant cause. Of the nine that
do not, four disagree *within* the violence family — Haiti, Libya, Niger, Nigeria — which is
precisely the option 1 versus option 2 distinction the questionnaire asks respondents to
draw. In Haiti people said armed conflict and the sources said widespread violence; in Niger
it is the other way round. That is the sharpest available argument for cognitive testing on
that boundary. The rest are caseload differences, not coding disagreements, and are labelled
as such.

**DTM cannot ask about persecution either.** Its reason list runs Conflict, Insecurity,
Natural disaster, Economic reasons, Other — with "Political reasons" in one country out of
twenty, covering 100,179 people, 0.2% of the total. So options 3 and 4 are absent from what
displaced people were *asked*, not merely from what was recorded. And 24% of Libya's DTM
caseload gave economic reasons, which is not a cause of forced displacement under IRIS at
all — a difference in who is in the population, before any question about why.

**Two populations in one country need one showcard.** Uganda's IDPs are 88% disaster-displaced;
among the 1.97m refugees it hosts, disaster accounts for 29%. Bangladesh has 5.5m disaster IDPs and 1.18m
Rohingya refugees. A single instrument has to work for both, which is the strongest argument
for localising the *support material* rather than the questions.

## Localising the examples, not the question

The response options must be identical everywhere. The text after each "e.g." must not.
The question variants document permits localising examples, and the desk review found that
when examples were withheld participants "showed a general lack of familiarity" with the
underlying concepts and "may fail to identify any qualifying event". So the examples carry
real weight, and they are the one part of the instrument allowed to vary.

Version 3 currently gives **no examples at all** for armed conflict, widespread violence or
other threats of violence — the three options the event data is strongest on — and a generic
global hazard list for natural disasters that names hazards which do not occur in most
countries. `build_questions.py` drafts replacements from what was actually recorded:
Philippines gets cyclones, floods and earthquakes; Haiti gets the gangs by name.

Three constraints are enforced in code rather than left to the reader. **Identity groups are
never named** — UCDP codes communal violence as "Christians (Nigeria) – Muslims (Nigeria)",
which is correct coding and unusable in an instrument read aloud by a government enumerator;
those become "communal or intercommunal violence". **An actor is used once** — Boko Haram
appearing under both armed conflict and other threats of violence gives a respondent a reason
to hesitate rather than a prompt. **Actor names are tagged as such**, because naming groups
risks anchoring: someone displaced by a group not on the list may conclude the option does
not cover them.

**Two lengths, because the instrument asks for two.** It says "SHOW SCREEN OR READ-OUT",
and those are different jobs: a list read aloud has to stay short or respondents remember
the first and last item and lose the middle, while a showcard they read themselves can
carry everything. Both are generated, and either way the count of what was *available*
is reported — a country with eleven active conflicts showing three is a different
situation from one with three.

Where one option would otherwise repeat a sentence stem, the examples are merged. Brazil
produced "clashes between Comando Vermelho and PCC, clashes between Comando Vermelho and
GDE, clashes between Bonde dos 13, PCC and Comando Vermelho…" six times over; it now reads
"clashes between armed groups, including Comando Vermelho, PCC, GDE, Bonde dos 13 and
Sindicato do Crime".

**Rendered as a form, in the language of the country, at the level that makes sense.** The
draft appears as it would on a questionnaire page — item code, routing instruction,
checkboxes — rather than as a bulleted list, because that is what a reviewer needs to judge.
The stem and the eight options exist in all six UN official languages, and each country
opens in the one most likely to be used in a national survey there. **Those translations are
unreviewed drafts**: translating an instrument is a specialist job (TRAPD, or forward-and-back
with reconciliation), and cognitive testing on an unreviewed translation tests the
translation rather than the question.

*Flee* is rendered as **leaving under duress, not fleeing in panic** — the item defines it as
leaving "due to events that posed a threat", so the sense is compelled departure. Five of
these languages have a default verb that instead means running away in fear (*fuir*, *huir*,
الفرار, *спасаясь бегством*, 逃离), and the first draft used all five. Each invites a
respondent to picture a panicked escape and answer "no" if their own departure was
deliberate — packing over days, or leaving after a threat rather than during an attack. That
is exactly the population these questions exist to count. *Persecution* remains open: a legal
term of art that in everyday registers reads as ordinary harassment, which is a materially
different threshold. Actor names are never translated; they are proper nouns.

**298 subnational sets across 58 countries** are offered where the region says something the
national set does not. A region whose examples merely repeat the national list is not shown —
DRC's provinces all collapsed to the same category phrasing and were dropped. The identity
rule is stricter at this level, because UCDP's admin1 communal-violence dyads are ethnic
groups by name with none of the markers that catch the national ones: an actor is named
subnationally only if it is also a party to a state-based or one-sided conflict in that
country.

These are drafts for the task team, not enumerator text. The names are UCDP's, not a
respondent's.

## Structure

```
run_all.R                 orchestration — analysis then visuals
R/01_sources.R            ingestion; fetch_*() and read_local_*() per source
R/02_profiles.R           crosswalk + showcard decision rule
R/03_outputs.R            ggplot figures
R/04_dtm.R                IOM DTM — reported reasons, a different class of evidence
prototype-python/fetch_dtm.py   pull DTM with your key, on a machine with network access
R/05_independence.R       what may and may not be combined (errors, not warns)
R/06_visuals.R            calls the Python layer
config/crosswalk.yaml     the crosswalk and every decision taken, as reviewable config
prototype-python/         the interactive maps and explorers
  build_events.py         event counts by cause, country and admin1
docs/                     data acquisition, how to reproduce, access requests, qualitative research
outputs/                  generated
```

## Outputs

| File | What |
|---|---|
| `idq_population_by_cause.html` | main map — **two views**: people displaced (six population modes) and events that happened (country / 1,847 admin1 areas, UCDP or ACLED); seven causes, country search, per-country showcard panel, evidence layer |
| `idq_crosswalk_explorer.html` | all 68 source categories and where each lands |
| `idq_subreasons.html` | 66 mechanisms beneath the eight options |
| `idq_localised_questions.html` | Version 3 of the forced-to-flee item with country-specific examples after each "e.g." |
| `idq_evidence_map.html` | counted vs documented |
| `idq_all_causes_map.html` | every cause at once, plus region × cause |
| `showcard_recommendations.csv` | country × code with status, rationale and local examples — also surfaced per country in the map |
| `ucdp_conflict_register.csv` | named conflicts with parties, dates, deaths, regional spread |
| `subnational_displacement_points.csv` | 7,648 geocoded locations, mostly ADM2/ADM3 |
| `admin1_conflict_profiles.csv` | region × cause |
| `dtm_reported_vs_attributed.csv` | what people said vs what we inferred, per country, with the disagreement classified |
| `localised_question_examples.csv` | every drafted example with its source and the evidence behind it |

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

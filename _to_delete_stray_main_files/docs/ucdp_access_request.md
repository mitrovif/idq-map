# UCDP API access request

Send to UCDP (contact address on https://ucdp.uu.se/apidocs/ or via the
Department of Peace and Conflict Research, Uppsala University).

**Before sending:** the bulk downloads at https://ucdp.uu.se/downloads need no
token. Download the datasets listed below, put them in `data/raw/`, and the
pipeline runs today. The token is for reproducible automated refresh, not for
first results.

---

**Subject:** UCDP API access request — EGRISS identification questions for refugee and IDP statistics

Hello,

I am writing to request an access token for the UCDP API.

**Name:** Filip Mitrovic
**Affiliation:** Expert Group on Refugee, IDP and Statelessness Statistics (EGRISS), hosted by UNHCR
**Role:** [your title]
**Email:** fmitrovic27@gmail.com

**Project / intended use:**

EGRISS is developing the first internationally recognised set of household survey
questions for identifying refugees and IDPs — modelled on the Washington Group
Questions on Disability Statistics — for adoption by national statistical offices.
The work is supported by a UNHCR Data Innovation Grant and will be published as a
methodological paper.

One component establishes which "reason for fleeing" response options are relevant
in which countries, so that enumerator training and support materials can be
adapted to local context while the questionnaire itself remains internationally
comparable. We have built a reproducible R pipeline that maps causing events to the
questionnaire's response categories, combining UCDP with IDMC, ACLED, IOM DTM,
V-Dem and UNHCR population statistics.

We would use the following UCDP datasets, at version 26.1:

- **`ucdpprioconflict`** — conflict names, parties, start dates, incompatibility
  and intensity. We currently describe each country's conflict history from
  structured fields alone; conflict and actor names would let enumerator materials
  refer to conflicts as respondents themselves would name them.
- **`gedevents`** — georeferenced events, for subnational analysis in the largest
  displacement contexts. This is the only global geocoded source we have access to
  and is required for the admin1 layer of the work.
- **`nonstate`** — communal and militia violence, to distinguish armed conflict
  from other situations of violence, which is a distinction the questionnaire
  makes and most displacement data does not.
- **`onesided`** — the government-perpetrator flag, which is currently our only
  evidence for the "human rights violations by authorities" response option.
- **`organizedviolencecy`** — country-year organized violence, as a cleaner input
  for country-level attribution than assembling the above ourselves.

We already use UCDP One-Sided Violence v26.1 and the UCDP/PRIO ACD via the
`peacesciencer` distribution, and cite both. API access would let us refresh
reproducibly as versions update rather than re-downloading manually — important
because this pipeline is intended to be handed to national statistical offices
and re-run by them.

This is non-commercial work for official statistics and academic publication.
Outputs will be published openly with full UCDP citation, and the code shared with
participating national statistical offices.

Kind regards,
Filip Mitrovic
EGRISS Project Task Team

---

## After the token arrives

```r
usethis::edit_r_environ()   # add: UCDP_TOKEN=<token>
```

Then in `run_all.R` set `MODE <- "api"`. Version strings use **dots**: `"26.1"`,
not `"26_1"` — an underscore fails silently.

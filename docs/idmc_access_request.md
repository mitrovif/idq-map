# IDMC API access request

Send to **ch.datainfo@idmc.ch**. Per IDMC's instructions, approved requests
receive a `client_id`, which is then passed as a query parameter on every call.

**Before sending:** the GIDD disaggregated export at
https://www.internal-displacement.org/database/ needs no key. Download it with
the year range set to **all years**, put it in `data/raw/uploads/`, and the
pipeline runs today. The key is for reproducible automated refresh — it is not
what unblocks first results, and asking for it does not remove the need to state
what you will do with the data.

---

**Subject:** API access request — EGRISS identification questions for refugee and IDP statistics

Dear IDMC Data and Information team,

I would like to request an API key (`client_id`) for the IDMC APIs.

**Name:** Filip Mitrovic
**Affiliation:** Expert Group on Refugee, IDP and Statelessness Statistics (EGRISS), hosted by UNHCR
**Role:** [your title]
**Email:** fmitrovic27@gmail.com

**What we are building**

EGRISS is developing the first internationally recognised set of household survey
questions for identifying refugees and IDPs — modelled on the Washington Group
Questions on Disability Statistics — for adoption by national statistical offices.
The work is supported by a UNHCR Data Innovation Grant and will be published as a
methodological paper.

One component establishes **which "reason for fleeing" response options are
relevant in which countries**, so that enumerator training and support materials
can be adapted to local context while the questionnaire itself stays
internationally comparable. The instrument does not change by country; only the
worked examples an enumerator offers do.

**How we would use IDMC data**

GIDD is the backbone of the population side of this analysis. We use the
disaggregated export — figures by country, year, cause, hazard sub-type, violence
type and geocoded location — and map each category onto the questionnaire's
response options. Specifically:

- **Conflict figures by violence type** (IAC, NIAC, other situations of violence)
  distinguish "threat of armed conflict or war" from "widespread violence or
  breakdown of public order", which are separate response options and are
  routinely conflated in practice.
- **Disaster figures by hazard sub-type** identify which specific hazards to give
  as examples in each country — flood, drought, cyclone — rather than the generic
  category.
- **Geocoded locations** let us show where within a country displacement occurred,
  which is the level at which enumerator materials would actually be adapted.

An API key would let us refresh reproducibly rather than pinning results to a
manually downloaded file, and to pull **the full time series** rather than a
single year. That distinction matters here: the survey questions ask about
displacement over a respondent's lifetime, so a single-year extract understates
protracted caseloads and over-weights whatever happened in that year.

**What we would publish**

Aggregated derivatives only — country and admin1 level shares by cause, and
per-country recommendations for enumerator support material. No IDMC records are
redistributed. IDMC is cited on every output, and the code is open at
https://github.com/mitrovif/idq-map with an accompanying prototype at
https://mitrovif.github.io/idq-map/, so your team can see exactly how the figures
are used before granting anything.

**One observation we would value your view on**

Working through the GIDD categories, the clearest finding is that **displacement
caused by persecution or discrimination has nowhere to go in the classification**.
A family displaced by targeted persecution is recorded under the armed conflict
that surrounds it. Across IDMC's published methodology notes, the terms
"persecution", "discrimination" and "torture" do not appear. This is not a
criticism of the taxonomy — it follows from what is observable through
monitoring — but it means one of the response options we are testing is, by
construction, invisible in every displacement dataset in the world. If IDMC has
considered this, or holds unpublished material on it, we would be grateful to
hear about it, and would be glad to share our findings with your team either way.

Thank you for considering the request.

Kind regards,
Filip Mitrovic
EGRISS Secretariat, hosted by UNHCR
fmitrovic27@gmail.com

---

## After the key arrives

Add it to `.Renviron` (`usethis::edit_r_environ()`):

```
IDMC_KEY=<your client_id>
```

IDMC passes it as a **query parameter**, not a header — unusual, and the reason a
key that looks correct can still 401 if it is sent the usual way:

```
https://helix-tools-api.idmcdb.org/external-api/gidd/...?client_id=<key>
```

**A note on where this can run.** The IDMC API host is not reachable from the
Cowork cloud sandbox (all requests time out), so the key only helps in an
environment with open network access — your own machine, via
`source("run_all.R")`. In the sandbox the manual GIDD download remains the route,
and yields the same data.

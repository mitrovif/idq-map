# Getting the data

No source data is in this repository. Every file below is downloaded directly
from its publisher — a licence requirement, not an inconvenience. Put everything
in `data/raw/`. Filenames are matched by pattern, so downloads work unchanged.

| Source | Where | Key needed | What it gives |
|---|---|---|---|
| **UCDP GED** | [ucdp.uu.se/downloads](https://ucdp.uu.se/downloads/) → Georeferenced Event Dataset, CSV | no | codes 1, 2, 4, 5 · global · 1989+ · geocoded · named conflicts |
| **UCDP One-Sided Violence** | same page | no | state-perpetrator flag for code 4 |
| **IDMC GIDD — disaggregated** | [internal-displacement.org/database](https://www.internal-displacement.org/database/) → Disaggregated export. **One year per download, 2023 onwards only** — download 2023, 2024 and 2025 separately and drop all three in `data/raw/uploads/` | no | the displacement denominator: violence type, hazard sub-type, geocoded. This is what splits option 1 from 2 and 6 from 7 |
| **IDMC GIDD — aggregated** | same page → Conflict and disaster export | no | 2008–2025 by country and year, but **Conflict / Disaster only**. The long series; too coarse for the eight options |
| **ACLED aggregated** | [acleddata.com](https://acleddata.com/) → Data Export Tool, aggregated regional files, **all six regions** | no | codes 1, 2, 4, 5 · weekly × admin1 |
| **UNHCR** | R package `refugees` — ships the data offline | no | refugee and IDP stocks, origin × asylum, recognition rates |
| **V-Dem** | `vdem.RData` from the [vdemdata repo](https://github.com/vdeminstitute/vdemdata) | no | conditions behind codes 3 and 4 |
| **IOM DTM** | [dtm-apim-portal.iom.int](https://dtm-apim-portal.iom.int/) | **yes**, free | reported reasons — what displaced people say |
| **UCDP API** | [ucdp.uu.se/apidocs](https://ucdp.uu.se/apidocs/) | **yes** | reproducible refresh (bulk downloads need no key) |
| **IDMC API** | email ch.datainfo@idmc.ch | **yes** | reproducible refresh (the GIDD export needs no key) — see [`idmc_access_request.md`](idmc_access_request.md) |

## The basemap

Not displacement data, but the maps will not draw without it. Save either of
these as `data/world/countries-110m.json` — the loader sniffs the format and
accepts both:

- **Natural Earth 110m countries**, GeoJSON —
  [`martynafford/natural-earth-geojson`](https://github.com/martynafford/natural-earth-geojson/blob/master/110m/cultural/ne_110m_admin_0_countries.json)
  (public domain)
- **world-atlas**, TopoJSON — `npm pack world-atlas` or
  [unpkg.com/world-atlas/countries-110m.json](https://unpkg.com/world-atlas/countries-110m.json)
  (ISC)

Either works. Natural Earth is the safer default because it needs no build step.

## The one that matters most

The **disaggregated** IDMC export, for **every year it is offered**. The questions
ask about lifetime displacement, and a one-year file understates protracted causes
while over-weighting whatever happened that year.

IDMC serves this export one year at a time and only from 2023, so the maximum
available span is 2023–2025 — three separate downloads. The loader takes all the
files it finds and dedups by year, so just drop them all in the same folder.

For anything before 2023 the aggregated export is the only option, and it
distinguishes nothing finer than Conflict versus Disaster. That ceiling is IDMC's,
not this pipeline's, and it is worth stating in the paper: **event-level
displacement data with usable cause detail does not exist before 2023.**

## Minimum to get results

UCDP GED + IDMC GIDD + the `refugees` package. Everything else degrades
gracefully — the pipeline reports what it skipped rather than failing.

## Licensing

**ACLED restricts redistribution.** Do not commit ACLED files or any output that
reproduces ACLED rows. UCDP, IDMC and UNHCR all require citation; see each
publisher's terms. `.gitignore` excludes `data/` for this reason.

# Getting the data

No source data is in this repository. Every file below is downloaded directly
from its publisher — a licence requirement, not an inconvenience. Put everything
in `data/raw/`. Filenames are matched by pattern, so downloads work unchanged.

| Source | Where | Key needed | What it gives |
|---|---|---|---|
| **UCDP GED** | [ucdp.uu.se/downloads](https://ucdp.uu.se/downloads/) → Georeferenced Event Dataset, CSV | no | codes 1, 2, 4, 5 · global · 1989+ · geocoded · named conflicts |
| **UCDP One-Sided Violence** | same page | no | state-perpetrator flag for code 4 |
| **IDMC GIDD** | [internal-displacement.org/database](https://www.internal-displacement.org/database/) → Disaggregated export, **all years** | no | the displacement denominator, by cause and hazard, geocoded |
| **ACLED aggregated** | [acleddata.com](https://acleddata.com/) → Data Export Tool, aggregated regional files, **all six regions** | no | codes 1, 2, 4, 5 · weekly × admin1 |
| **UNHCR** | R package `refugees` — ships the data offline | no | refugee and IDP stocks, origin × asylum, recognition rates |
| **V-Dem** | `vdem.RData` from the [vdemdata repo](https://github.com/vdeminstitute/vdemdata) | no | conditions behind codes 3 and 4 |
| **IOM DTM** | [dtm-apim-portal.iom.int](https://dtm-apim-portal.iom.int/) | **yes**, free | reported reasons — what displaced people say |
| **UCDP API** | [ucdp.uu.se/apidocs](https://ucdp.uu.se/apidocs/) | **yes** | reproducible refresh (bulk downloads need no key) |

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

The **all-years IDMC GIDD export**, not a single year. The questions ask about
lifetime displacement; a one-year file understates protracted causes and
over-weights whatever happened that year. If you download one thing, that.

## Minimum to get results

UCDP GED + IDMC GIDD + the `refugees` package. Everything else degrades
gracefully — the pipeline reports what it skipped rather than failing.

## Licensing

**ACLED restricts redistribution.** Do not commit ACLED files or any output that
reproduces ACLED rows. UCDP, IDMC and UNHCR all require citation; see each
publisher's terms. `.gitignore` excludes `data/` for this reason.

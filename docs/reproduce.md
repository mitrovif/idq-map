# Reproducing this from scratch

Every figure on the site can be regenerated from public sources. Nothing is
bundled — the licences forbid it — so the work is in the downloads, not the code.
Budget an hour, most of it waiting for exports.

## How each source is actually connected

This matters more than it sounds: **only one source is reached by API.**
Everything else is a manual export or an offline package, which is why the
figures are pinned to a download date rather than live.

| Source | How it is connected | Key | Notes |
|---|---|---|---|
| **UCDP GED** | manual bulk download (CSV) | no | An API exists and a token was requested (`ucdp_access_request.md`); bulk downloads need no key, so the token is for reproducible refresh, not first results |
| **IDMC GIDD** | manual export, one year per download | no | Disaggregated data exists **only from 2023**, one year at a time. The aggregated export covers 2008–2025 but distinguishes nothing finer than Conflict vs Disaster. API request drafted in `idmc_access_request.md` — key goes in the **query string**, not a header |
| **ACLED** | manual export, six regional files | account | Data Export Tool. Their terms restrict republishing, so ACLED counts are stripped from the published build |
| **UNHCR** | R package `refugees` — ships the data offline | no | No network call at all |
| **IOM DTM** | **API — the only one** | **yes**, free | `prototype-python/fetch_dtm.py` using IOM's own `dtmapi` client. Key from [dtm-apim-portal.iom.int](https://dtm-apim-portal.iom.int/), passed as a header. Must run on a machine with normal network access |
| **V-Dem** | file from the `vdemdata` GitHub repo | no | |
| **Basemap** | Natural Earth or world-atlas | no | See `getting_the_data.md` |

## What you need installed

```bash
python3 -m pip install -r prototype-python/requirements.txt
```

That is pandas, numpy, openpyxl, pyarrow, pyreadr, pycountry. R is optional —
it runs the analysis path and the ggplot figures, but the maps and every figure
on the site come from the Python layer.

## The downloads

All of these go in `data/raw/uploads/` unless stated. Filenames do not matter;
the loaders match by pattern.

1. **UCDP GED v26.1**, CSV — [ucdp.uu.se/downloads](https://ucdp.uu.se/downloads/) →
   `data/raw/ged/`
2. **UCDP One-Sided Violence**, XLSX — same page → `data/raw/uploads/ucdp_onesided/`
3. **IDMC GIDD disaggregated** — [internal-displacement.org/database](https://www.internal-displacement.org/database/)
   → one file each for 2023, 2024, 2025
4. **IDMC conflict-and-disaster export** — same page, the long 2008–2025 series
5. **ACLED aggregated**, six regional files — [acleddata.com](https://acleddata.com/)
   → Africa, Middle East, Europe–Central Asia, Asia-Pacific, Latin America &
   Caribbean, US & Canada
6. **UNHCR** — nothing to download; the `refugees` R package carries it
7. **V-Dem** — `vdem.RData` → `data/raw/`
8. **Basemap** → `data/world/countries-110m.json`

Minimum for a result: UCDP GED + one IDMC export + the basemap. Everything else
degrades gracefully and the run reports what it skipped.

## IOM DTM, the API step

Runs on your machine, not in a sandbox — and the key never needs to leave it:

```bash
python3 -m pip install --user dtmapi pandas
DTM_KEY=<your key> python3 prototype-python/fetch_dtm.py
```

That writes `dtm_data/*.csv`. Copy them to `data/raw/dtm/`. The CSVs carry no
credential, so they are the thing to share with a colleague.

## Run it

```bash
IDQ_ROOT=$(pwd) python3 prototype-python/run_all.py
```

Fifteen steps, roughly three minutes. Each prints what it read and what it
wrote, and any step whose input is missing says so and is skipped rather than
failing the run. Outputs land in `outputs/`.

To rebuild the public copy — ACLED counts stripped, per their terms:

```bash
IDQ_PUBLIC=1 python3 prototype-python/build_population_map.py
python3 prototype-python/publish_site.py
```

`publish_site.py` **refuses** to publish a page still carrying per-country ACLED
counts. That guard has already caught one leak that visual inspection missed.

## Confirming it matches

The run prints the numbers to check against:

- UCDP GED **417,968** incidents across 126 countries
- ACLED **1,841,683** events across 203 countries
- IDMC **12,729** hazard records
- **2,045** admin1 areas in the events layer
- IOM DTM **20** countries, and `11 of 20 countries agree on the dominant cause`
- **154** countries with a drafted question, **449** examples

If your IDMC or ACLED exports are newer than mine the population figures will
move; the UCDP and DTM figures should match exactly at the same versions.

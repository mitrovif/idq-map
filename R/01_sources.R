## =============================================================================
## 01_sources.R - ingestion. Every source has TWO entry points:
##     fetch_*()      pulls live from the API   (needs network + any keys)
##     read_local_*() reads a downloaded export (works offline)
## Both return the IDENTICAL tidy shape, so swapping one for the other is a
## one-line change in run_all.R. Build against local files first, switch to
## fetch_* once credentials are in place.
##
## Tidy shape:  iso3 | country | admin1 | year | code_id | evidence_type | value | source
## =============================================================================

suppressPackageStartupMessages({
  library(dplyr); library(tidyr); library(readxl); library(readr)
  library(stringr); library(purrr); library(httr2); library(jsonlite)
})

`%||%` <- function(a, b) if (is.null(a) || length(a) == 0) b else a

## ---------------------------------------------------------------- ISO3 helper
to_iso3 <- function(x) {
  manual <- c(
    "Russia" = "RUS", "Turkey" = "TUR", "Iran" = "IRN", "Syria" = "SYR",
    "Palestine" = "PSE", "Kosovo" = "XKX", "Czech Republic" = "CZE",
    "DR Congo (Zaire)" = "COD", "Myanmar (Burma)" = "MMR",
    "Cambodia (Kampuchea)" = "KHM", "Yemen (North Yemen)" = "YEM",
    "Zimbabwe (Rhodesia)" = "ZWE", "Ivory Coast" = "CIV",
    "Serbia (Yugoslavia)" = "SRB", "Madagascar (Malagasy)" = "MDG",
    "Russia (Soviet Union)" = "RUS", "Vietnam (North Vietnam)" = "VNM",
    "Bosnia-Herzegovina" = "BIH", "Macedonia, FYR" = "MKD"
  )
  drop <- c("Antarctica", "Arctic Ocean", "Atlantic Ocean", "Indian Ocean",
            "Pacific Ocean", "Southern Ocean", "Mediterranean Sea",
            "Caribbean Sea", "Red Sea")
  out <- countrycode::countrycode(x, "country.name", "iso3c", warn = FALSE)
  hit <- x %in% names(manual)
  out[hit] <- manual[x[hit]]
  out[x %in% drop] <- NA_character_
  out
}

## ============================================================ 1. UCDP
## API AT https://ucdpapi.pcr.uu.se/api/<dataset>/<version>
##
## Requires an access token - the API returns 401 without one. Request from UCDP
## (see docs/ucdp_access_request.md), then:
##   usethis::edit_r_environ(); add  UCDP_TOKEN=<token>
##
## NOTE ON VERSION STRINGS: UCDP documents versions with DOTS - "26.1", "25.1",
## not "26_1". An underscore silently fails. Current versions as documented:
##   gedevents           5.0, 17.1-26.1, plus dated candidate releases
##   ucdpprioconflict    17.2-26.1     (conflict names, parties, start dates)
##   dyadic              17.2-26.1
##   nonstate            17.2-26.1     (communal/militia violence -> code 2)
##   onesided            17.2-26.1     (state-perpetrator flag -> code 4)
##   battledeaths        17.2-26.1
##   organizedviolencecy 26.1          (country-year, all three violence types)
##
## THE BULK DOWNLOADS AT ucdp.uu.se/downloads NEED NO TOKEN. If the token has
## not arrived, download the files and use read_local_* instead - the pipeline
## does not care which route the data came by.
UCDP_DATASETS <- c(ged = "gedevents", acd = "ucdpprioconflict",
                   dyadic = "dyadic", nonstate = "nonstate",
                   onesided = "onesided", battledeaths = "battledeaths",
                   country_year = "organizedviolencecy")

ucdp_get <- function(dataset, version, pagesize = 1000, max_pages = Inf) {
  tok <- Sys.getenv("UCDP_TOKEN")
  if (!nzchar(tok))
    stop("UCDP_TOKEN not set. The API returns 401 without one. Either request a ",
         "token from UCDP, or download the dataset from ucdp.uu.se/downloads ",
         "(no token needed) and use the read_local_* functions.")
  base <- sprintf("https://ucdpapi.pcr.uu.se/api/%s/%s", dataset, version)
  page <- 0; out <- list()
  repeat {
    req <- request(base) |>
      req_url_query(pagesize = pagesize, page = page) |>
      req_headers(Authorization = paste("Bearer", tok)) |>
      req_retry(max_tries = 4)
    r <- req |> req_perform() |> resp_body_json(simplifyVector = TRUE)
    res <- r$Result %||% r$result
    if (is.null(res) || NROW(res) == 0) break
    out[[length(out) + 1]] <- as_tibble(res)
    message(sprintf("  %s %s: page %d (%s rows so far)", dataset, version, page,
                    format(sum(vapply(out, nrow, 1L)), big.mark = ",")))
    page <- page + 1
    nxt <- r$NextPageUrl %||% r$nextPageUrl %||% ""
    if (page >= max_pages || !nzchar(nxt)) break
  }
  bind_rows(out)
}

## GED - georeferenced events, global, 1989+. The single most valuable UCDP
## dataset here: it is the only one that is both global and geocoded, so it
## drives codes 1, 2 and 4 AND the admin1 deep-dives.
fetch_ucdp_ged <- function(version = "26.1", ...) ucdp_get("gedevents", version, ...)

## ACD - conflict NAMES, parties and start dates. This is what turns
## "internationalised internal armed conflict over government, began 1982-01-18"
## into "Somalia: Government vs al-Shabaab".
fetch_ucdp_acd <- function(version = "26.1", ...) ucdp_get("ucdpprioconflict", version, ...)

## Non-state conflict - communal, militia and gang violence. Currently the
## weakest-evidenced part of code 2 outside the two ACLED regions we hold.
fetch_ucdp_nonstate <- function(version = "26.1", ...) ucdp_get("nonstate", version, ...)

## Country-year organized violence - all three violence types in one table.
## New in 26.1 and the cleanest input for country-level cause attribution.
fetch_ucdp_country_year <- function(version = "26.1", ...) ucdp_get("organizedviolencecy", version, ...)

read_local_ucdp_ged <- function(path) {
  d <- if (grepl("\\.xlsx?$", path)) read_excel(path) else
       read_csv(path, show_col_types = FALSE, guess_max = 50000)
  tidy_ucdp_ged(d)
}

## GED v26.1 columns used here (all present in both the csv and xlsx releases):
##   type_of_violence  1 state-based | 2 non-state | 3 one-sided
##   conflict_name     e.g. "Somalia: Government"
##   dyad_name         e.g. "Government of Somalia - al-Shabaab"
##   side_a / side_b   named parties
##   country, adm_1, adm_2, latitude, longitude
##   date_start, year, best (deaths, best estimate)
tidy_ucdp_ged <- function(d) {
  names(d) <- tolower(names(d))
  d |>
    mutate(
      code_id = case_when(
        type_of_violence == 1 ~ 1L,
        type_of_violence == 2 ~ 2L,
        ## one-sided: government perpetrator -> code 4, otherwise code 5
        type_of_violence == 3 & str_detect(tolower(side_a), "^government of") ~ 4L,
        type_of_violence == 3 ~ 5L,
        TRUE ~ NA_integer_),
      iso3 = to_iso3(country), year = as.integer(year)) |>
    filter(!is.na(code_id), !is.na(iso3)) |>
    group_by(iso3, country, admin1 = adm_1, year, code_id) |>
    summarise(events = n(), fatalities = sum(best, na.rm = TRUE), .groups = "drop") |>
    pivot_longer(c(events, fatalities), names_to = "evidence_type",
                 values_to = "value") |>
    mutate(source = "UCDP GED")
}

## -----------------------------------------------------------------------------
## THE UPGRADE GED UNLOCKS: named conflicts.
##
## Everywhere else in this pipeline a country's conflict history is described
## from structured fields - "internationalised internal armed conflict over
## government, began 1982-01-18". GED carries conflict_name, dyad_name, side_a
## and side_b, so the same country can be described as UCDP itself names it:
## "Somalia: Government — Government of Somalia vs al-Shabaab".
##
## That matters for enumerator materials specifically. An interviewer prompting
## with a named party gets recognition; a hazard-class or conflict-type label
## gets a blank look. This is the conflict-side equivalent of the named storms
## in the IDMC disaster register.
##
## Returns, per country: the conflicts that displaced-relevant violence belongs
## to, with named parties, fatality weight, years active, and admin1 spread.
ucdp_ged_conflict_register <- function(ged_raw, min_deaths = 25, top_n = 6) {
  names(ged_raw) <- tolower(names(ged_raw))
  g <- ged_raw |>
    mutate(iso3 = to_iso3(country), year = as.integer(year)) |>
    filter(!is.na(iso3))

  g |>
    group_by(iso3, country, conflict_name, dyad_name, side_a, side_b,
             type_of_violence) |>
    summarise(events = n(),
              deaths = sum(best, na.rm = TRUE),
              first_year = min(year), last_year = max(year),
              admin1s = n_distinct(adm_1, na.rm = TRUE),
              .groups = "drop") |>
    filter(deaths >= min_deaths) |>
    group_by(iso3) |>
    slice_max(deaths, n = top_n, with_ties = FALSE) |>
    ungroup() |>
    mutate(kind = recode(as.character(type_of_violence),
                         "1" = "armed conflict", "2" = "non-state conflict",
                         "3" = "one-sided violence"),
           label = sprintf("%s — %s (%d–%d, %s deaths)",
                           conflict_name, dyad_name, first_year, last_year,
                           format(round(deaths), big.mark = ",")))
}

## Subnational layer - the piece of the original plan that has had no data.
## GED is geocoded to adm_1, so this finally runs.
ucdp_ged_admin1 <- function(ged_raw, isos) {
  names(ged_raw) <- tolower(names(ged_raw))
  ged_raw |>
    mutate(iso3 = to_iso3(country), year = as.integer(year),
           code_id = case_when(type_of_violence == 1 ~ 1L,
                               type_of_violence == 2 ~ 2L,
                               type_of_violence == 3 &
                                 str_detect(tolower(side_a), "^government of") ~ 4L,
                               type_of_violence == 3 ~ 5L)) |>
    filter(iso3 %in% isos, !is.na(adm_1), !is.na(code_id)) |>
    group_by(iso3, admin1 = adm_1, code_id) |>
    summarise(events = n(), deaths = sum(best, na.rm = TRUE),
              conflicts = paste(sort(unique(conflict_name))[1:3][
                !is.na(sort(unique(conflict_name))[1:3])], collapse = "; "),
              .groups = "drop") |>
    group_by(iso3, admin1) |>
    mutate(share = deaths / pmax(sum(deaths), 1)) |>
    ungroup()
}

## UCDP one-sided violence - actor-year, carries is_government_actor, which GED
## only implies. Used to corroborate code 4.
read_local_ucdp_onesided <- function(path) {
  read_excel(path) |>
    mutate(code_id = if_else(is_government_actor == 1, 4L, 5L)) |>
    # 'location' may list several countries: "Burundi, DR Congo (Zaire), Rwanda"
    mutate(loc = str_split(location, ",\\s*(?![^()]*\\))")) |>
    unnest(loc) |>
    group_by(location) |> mutate(n_loc = n_distinct(loc)) |> ungroup() |>
    mutate(iso3 = to_iso3(str_trim(loc)),
           value = best_fatality_estimate / n_loc) |>
    filter(!is.na(iso3)) |>
    group_by(iso3, country = loc, year = as.integer(year), code_id) |>
    summarise(value = sum(value), .groups = "drop") |>
    mutate(admin1 = NA_character_, evidence_type = "fatalities",
           source = "UCDP one-sided")
}

## ============================================================ 2. ACLED
## The free AGGREGATED regional exports need NO key and are weekly x admin1 x
## sub_event_type. The full event API needs an account + OAuth (acledR).
## Trade-off: the aggregated export has no ACTOR column, so state vs non-state
## perpetrator cannot be split - which is why code 4 leans on UCDP one-sided.
ACLED_SUBEVENT_TO_CODE <- c(
  "Armed clash" = 1, "Air/drone strike" = 1,
  "Shelling/artillery/missile attack" = 1, "Remote explosive/landmine/IED" = 1,
  "Suicide bomb" = 1, "Grenade" = 1, "Chemical weapon" = 1,
  "Government regains territory" = 1, "Non-state actor overtakes territory" = 1,
  ## "Disrupted weapons use" deliberately absent: weapons intercepted or defused
  ## before use displace nobody. Was inflating code 1 by 30,628 events.
  "Mob violence" = 2, "Violent demonstration" = 2,
  "Protest with intervention" = 2, "Looting/property destruction" = 2,
  "Arrests" = 4, "Excessive force against protesters" = 4,
  "Attack" = 5, "Sexual violence" = 5, "Abduction/forced disappearance" = 5
)

read_local_acled_aggregated <- function(paths) {
  map_dfr(paths, read_excel) |>
    rename_with(toupper) |>
    mutate(year = as.integer(format(as.Date(WEEK), "%Y")),
           code_id = unname(ACLED_SUBEVENT_TO_CODE[SUB_EVENT_TYPE]),
           iso3 = to_iso3(COUNTRY)) |>
    filter(!is.na(code_id), !is.na(iso3)) |>
    group_by(iso3, country = COUNTRY, admin1 = ADMIN1, year, code_id) |>
    summarise(events = sum(EVENTS, na.rm = TRUE),
              fatalities = sum(FATALITIES, na.rm = TRUE), .groups = "drop") |>
    pivot_longer(c(events, fatalities), names_to = "evidence_type",
                 values_to = "value") |>
    mutate(source = "ACLED", code_id = as.integer(code_id))
}

## Full ACLED event API - dormant until credentials exist.
## Register at acleddata.com, then: Sys.setenv(ACLED_EMAIL=, ACLED_KEY=)
fetch_acled <- function(iso = NULL, from = "1997-01-01") {
  if (!nzchar(Sys.getenv("ACLED_KEY"))) {
    warning("ACLED_KEY not set - skipping ACLED API pull. ",
            "Register at acleddata.com; the free aggregated exports need no key.")
    return(NULL)
  }
  if (!requireNamespace("acledR", quietly = TRUE))
    stop("install.packages('acledR')")
  acledR::acled_access(email = Sys.getenv("ACLED_EMAIL"),
                       key = Sys.getenv("ACLED_KEY"),
                       country = iso, start_date = from) |>
    tidy_acled_events()
}

tidy_acled_events <- function(d) {
  d |>
    mutate(code_id = unname(ACLED_SUBEVENT_TO_CODE[sub_event_type]),
           iso3 = to_iso3(country), year = as.integer(year)) |>
    filter(!is.na(code_id)) |>
    group_by(iso3, country, admin1, year, code_id) |>
    summarise(events = n(), fatalities = sum(fatalities, na.rm = TRUE),
              .groups = "drop") |>
    pivot_longer(c(events, fatalities), names_to = "evidence_type",
                 values_to = "value") |>
    mutate(source = "ACLED", code_id = as.integer(code_id))
}

## ============================================================ 3. IDMC
## THE key source: it reports how many people were ACTUALLY DISPLACED, by cause,
## at event level with coordinates. 'Violence type' gives IDMC's own adjudicated
## split between armed conflict (IAC/NIAC) and other situations of violence
## (OSV) - exactly the code 1 vs code 2 distinction, from the displacement
## agency rather than inferred from event data.
##
## NOTE ON ACCESS: the IDU API requires an endpoint URL issued by IDMC on
## request (see the OCHA-DAP 'idmc' package). The GIDD web export needs nothing.
IDMC_VIOLENCE_TO_CODE <- c(
  "International armed conflict (IAC)" = 1,
  "Non-International armed conflict (NIAC)" = 1,
  "Other situations of violence (OSV)" = 2,
  ## Conflict-caused but type unrecorded. Carried as its own UNATTRIBUTED band
  ## (pseudo-code 0) rather than defaulted into code 1: it stays in every
  ## denominator, so country shares are shares of ALL displacement and no longer
  ## sum to 100% across the eight options. That is deliberate - 2m people were
  ## never classified by anyone, and pretending otherwise inflates armed conflict.
  "Unclear/Unknown" = 0
)

## Hazards IDMC files under Disaster whose trigger is human. Reassigned to
## code 7. NOTE: wildfire is ~99.8% of the resulting total, so any statement
## about code 7 is in practice a statement about wildfire - report the
## composition, never the bare figure.
HUMAN_TRIGGERED_HAZARDS <- c("Wildfire", "Dam release flood", "Sinkhole")

read_local_idmc_gidd <- function(path, sheet = "1_Disaggregated_Data") {
  raw <- read_excel(path, sheet = sheet) |>
    rename(iso3 = ISO3, country = Country, year = Year,
           cause = `Figure cause`, category = `Figure category`,
           figures = `Total figures`, hazard_type = `Hazard type`,
           hazard_sub_type = `Hazard sub type`, violence_type = `Violence type`,
           coords = `Locations coordinates`, loc_name = `Locations name`,
           loc_accuracy = `Locations accuracy`,
           disp_occurred = `Displacement occurred`,
           sources = Sources) |>
    mutate(
      code_id = case_when(
        cause == "Disaster" & hazard_sub_type %in% HUMAN_TRIGGERED_HAZARDS ~ 7L,
        cause == "Disaster" ~ 6L,
        cause == "Conflict" ~ as.integer(IDMC_VIOLENCE_TO_CODE[violence_type] %||% 1),
        cause %in% c("Other", "Development") ~ 7L,
        TRUE ~ NA_integer_),
      year = as.integer(year),
      # preventive evacuations inflate disaster figures relative to what a
      # respondent would call "having to flee a home" - keep the flag visible
      preventive_evac = str_detect(coalesce(disp_occurred, ""),
                                   "reporting preventive evacuations"),
      human_triggered = hazard_sub_type %in% HUMAN_TRIGGERED_HAZARDS) |>
    filter(!is.na(code_id))

  long <- bind_rows(
    raw |> filter(category == "Internal Displacements") |>
      group_by(iso3, country, year, code_id) |>
      summarise(value = sum(figures, na.rm = TRUE), .groups = "drop") |>
      mutate(evidence_type = "displaced"),
    raw |> filter(category == "IDPs") |>
      group_by(iso3, country, year, code_id) |>
      summarise(value = sum(figures, na.rm = TRUE), .groups = "drop") |>
      mutate(evidence_type = "idp_stock")
  ) |> mutate(admin1 = NA_character_, source = "IDMC GIDD")

  list(long = long, detail = raw)
}

fetch_idmc_idu <- function() {
  url <- Sys.getenv("IDMC_API")
  if (!nzchar(url)) {
    warning("IDMC_API not set. Request an endpoint URL from IDMC, then ",
            "usethis::edit_r_environ() and add IDMC_API=<url>")
    return(NULL)
  }
  if (!requireNamespace("idmc", quietly = TRUE)) stop("install.packages('idmc')")
  idmc::idmc_get_data()
}

## ============================================================ 4. UNHCR
## The official `refugees` package ships the full 1951-present series offline,
## so this needs no network once installed. Two uses:
##   population        - IDP stock, refugee stock, and the origin x asylum matrix
##                       that drives origin-weighting
##   asylum_decisions  - recognition rates by origin, the code 3 proxy
fetch_unhcr <- function() {
  if (!requireNamespace("refugees", quietly = TRUE))
    stop("install.packages('refugees')")
  list(population = refugees::population,
       decisions  = refugees::asylum_decisions,
       countries  = refugees::countries)
}

recognition_rate_by_origin <- function(decisions, from = 2015, min_n = 1000) {
  decisions |>
    filter(year >= from) |>
    group_by(iso3 = coo_iso) |>
    summarise(rec = sum(dec_recognized, na.rm = TRUE),
              rej = sum(dec_rejected, na.rm = TRUE), .groups = "drop") |>
    mutate(denom = rec + rej) |>
    filter(denom >= min_n) |>
    mutate(recognition_rate = rec / denom) |>
    select(iso3, recognition_rate, denom)
}

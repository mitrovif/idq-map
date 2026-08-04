## =============================================================================
## EGRISS IDQ - mapping causing events to identification-question response codes
##
## Run this file top to bottom. It works in two modes:
##
##   MODE = "local"  reads downloaded exports from data/raw/   (no network, no keys)
##   MODE = "api"    pulls live from UCDP / ACLED / IDMC / UNHCR
##
## Start in "local" to get results today, then flip to "api" once you have an
## ACLED account and an IDMC endpoint URL. The tidy shape is identical either
## way, so nothing downstream changes.
## =============================================================================

MODE <- "local"          # "local" | "api"
OUT  <- "outputs"
RAW  <- "data/raw"
dir.create(OUT, showWarnings = FALSE, recursive = TRUE)

## ---------------------------------------------------------------- packages
pkgs <- c("dplyr", "tidyr", "readxl", "readr", "stringr", "purrr", "httr2",
          "jsonlite", "countrycode", "refugees", "sf", "ggplot2", "writexl")
missing <- setdiff(pkgs, rownames(installed.packages()))
if (length(missing)) install.packages(missing)
invisible(lapply(pkgs, library, character.only = TRUE))
## optional, only for MODE = "api":
##   install.packages(c("acledR", "idmc"))
##   Sys.setenv(ACLED_EMAIL = "...", ACLED_KEY = "...")   # acleddata.com
##   Sys.setenv(IDMC_API = "...")                          # request from IDMC
##   Sys.setenv(DTM_KEY  = "...")                          # dtm-apim-portal.iom.int

source("R/01_sources.R")
source("R/02_profiles.R")
source("R/03_outputs.R")
source("R/04_dtm.R")
source("R/05_independence.R")
source("R/06_visuals.R")

## ---------------------------------------------------------------- 1. ingest
if (MODE == "local") {

  ## ACLED free aggregated regional exports - one file per region, no key.
  ## Download all six regions from acleddata.com for global coverage; with only
  ## a couple of regions the event evidence is regionally blind (which the
  ## outputs report honestly rather than hiding).
  acled <- read_local_acled_aggregated(
    list.files(RAW, pattern = "aggregated_data.*\\.xlsx$", full.names = TRUE))

  ## IDMC GIDD disaggregated export. IMPORTANT: download the ALL-YEARS version,
  ## not a single year - the questions ask about LIFETIME displacement, so a
  ## one-year file will systematically understate protracted causes.
  idmc_l <- read_local_idmc_gidd(
    list.files(RAW, pattern = "IDMC_GIDD.*\\.xlsx$", full.names = TRUE)[1])
  idmc <- idmc_l$long; idmc_detail <- idmc_l$detail

  ## UCDP. GED is strongly preferred (global, geocoded, 1989+). One-sided alone
  ## only supports codes 4 and 5.
  ## Matches GEDEvent_v26_1.csv / .xlsx, ged261.csv, etc. Unzip first if zipped.
  ged_file <- list.files(RAW, pattern = "GED|ged", full.names = TRUE)
  ged_file <- ged_file[grepl("\\.(csv|xlsx)$", ged_file)]
  ucdp <- if (length(ged_file)) {
    message("UCDP GED found: ", basename(ged_file[1]))
    ged_raw <<- if (grepl("\\.xlsx$", ged_file[1])) readxl::read_excel(ged_file[1]) else
                readr::read_csv(ged_file[1], show_col_types = FALSE, guess_max = 50000)
    tidy_ucdp_ged(ged_raw)
  } else {
    message("No UCDP GED export found - falling back to one-sided violence only. ",
            "Codes 1 and 2 will rest on ACLED and IDMC alone.")
    read_local_ucdp_onesided(
      list.files(RAW, pattern = "OneSided.*\\.xlsx$", full.names = TRUE,
                 recursive = TRUE)[1])
  }

} else {
  acled       <- fetch_acled()
  ged         <- fetch_ucdp_ged(); ucdp <- tidy_ucdp_ged(ged)
  idu         <- fetch_idmc_idu()
  idmc_l      <- tidy_idmc_idu(idu); idmc <- idmc_l$long; idmc_detail <- idmc_l$detail
}

## IOM DTM - the only source that records what DISPLACED PEOPLE SAID, rather
## than what a monitor attributed after the fact. Needs a free subscription key
## from https://dtm-apim-portal.iom.int/. Optional: everything else still runs.
dtm <- NULL
if (nzchar(Sys.getenv("DTM_KEY"))) {
  message("DTM: pulling admin1 with displacement reason ...")
  dtm <- tryCatch(tidy_dtm(fetch_dtm(level = 1)),
                  error = function(e) { message("DTM failed: ", conditionMessage(e)); NULL })
} else {
  message("DTM_KEY not set - skipping. This is the one source that could tell you ",
          "how displaced people themselves distribute across the response options.")
}

unhcr <- fetch_unhcr()            # offline, ships with the `refugees` package
recognition <- recognition_rate_by_origin(unhcr$decisions)

evidence <- bind_rows(acled, idmc, ucdp, dtm) |>
  select(iso3, country, admin1, year, code_id, evidence_type, value, source)

## Provenance check. Prints how far IDMC leans on DTM, per country - the pairs
## that must not be treated as independent corroboration.
print(utils::head(idmc_dtm_dependence(idmc_detail), 10))

message(sprintf("evidence: %s rows, %d countries",
                format(nrow(evidence), big.mark = ","),
                dplyr::n_distinct(evidence$iso3)))

## ---------------------------------------------------------------- 2. profile
profiles <- build_profiles(evidence, idmc_detail, unhcr$population, recognition)

print(table(profiles$status))
readr::write_csv(profiles, file.path(OUT, "showcard_recommendations.csv"))
writexl::write_xlsx(
  list(recommendations = profiles,
       parameters = tibble::enframe(unlist(PARAMS), "parameter", "value")),
  file.path(OUT, "country_tailoring_profiles.xlsx"))

## ---------------------------------------------------------------- 3. outputs
## Reported reason vs analyst-attributed cause. The headline table for the paper.
if (!is.null(dtm)) {
  ## the _safe variant drops countries where IDMC's figures ARE DTM's, which
  ## would otherwise make the comparison circular - Sudan, Haiti, Ethiopia,
  ## Chad, Nigeria, Afghanistan and Mozambique among them
  gaps <- compare_reported_vs_attributed_safe(evidence, idmc_detail)
  readr::write_csv(gaps, file.path(OUT, "reported_vs_attributed.csv"))
  message("largest gaps between what people report and what monitors attribute:")
  print(utils::head(gaps, 12))
}

## ---- named conflicts, and the subnational layer GED finally makes possible
if (exists("ged_raw")) {
  conflicts <- ucdp_ged_conflict_register(ged_raw)
  readr::write_csv(conflicts, file.path(OUT, "ucdp_conflict_register.csv"))
  message(sprintf("named conflicts: %d across %d countries",
                  nrow(conflicts), dplyr::n_distinct(conflicts$iso3)))
  print(conflicts |> dplyr::filter(iso3 %in% c("SOM", "UKR", "SYR")) |>
          dplyr::select(iso3, label) |> utils::head(9))

  top10 <- profiles |> distinct(iso3, idps, refugees_hosted) |>
    mutate(total = idps + refugees_hosted) |> arrange(desc(total)) |>
    head(10) |> pull(iso3)
  adm1 <- ucdp_ged_admin1(ged_raw, top10)
  readr::write_csv(adm1, file.path(OUT, "admin1_conflict_profiles.csv"))
  message(sprintf("admin1 profiles: %d regions across %d countries",
                  nrow(adm1), dplyr::n_distinct(adm1$iso3)))
}

make_figures(profiles, evidence, idmc_detail, OUT)
## ---- interactive maps and explorers (Python, called from here)
## One command does everything. If Python is absent the analysis still completes
## and this prints what to install.
make_visuals(root = getwd())

## ---------------------------------------------------------------- 4. admin1
## Subnational deep-dives for the largest displacement contexts. Requires
## geocoded sources: UCDP GED (lat/long), ACLED (admin1 + centroid), IDMC IDU.
top_contexts <- profiles |>
  distinct(iso3, idps, refugees_hosted) |>
  mutate(total = idps + refugees_hosted) |>
  arrange(desc(total)) |> head(10) |> pull(iso3)
message("admin1 deep-dives for: ", paste(top_contexts, collapse = ", "))
make_admin1_profiles(evidence, idmc_detail, top_contexts, OUT)

message("done - see ", normalizePath(OUT))
message("\nOpen outputs/idq_population_by_cause.html for the main map.")

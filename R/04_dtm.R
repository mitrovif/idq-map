## =============================================================================
## 04_dtm.R - IOM Displacement Tracking Matrix.
##
## WHY THIS SOURCE IS DIFFERENT FROM EVERY OTHER ONE IN THE PIPELINE
##
## UCDP, ACLED and IDMC all record what an ANALYST attributed a displacement to,
## after the fact, from monitoring. DTM records what DISPLACED PEOPLE AND KEY
## INFORMANTS SAID when asked why they left.
##
## That is the same epistemic class as the identification questions themselves.
## Everything else in this pipeline tells you what causes monitors can see; DTM
## is the only source that tells you what causes PEOPLE REPORT. It therefore has
## a use no other source has: it can validate the response options directly, by
## showing whether the categories people actually give line up with the eight
## the questionnaire offers, and what falls into "other".
##
## The tidy output carries evidence_type = "reported_reason" to keep this
## distinct. Never pool it with "displaced" or "events" - they answer different
## questions and a reader who sums them has been misled.
##
## ACCESS
##   1. Register at https://dtm-apim-portal.iom.int/ for a free subscription key
##   2. usethis::edit_r_environ(); add   DTM_KEY=<your key>
##   3. Set MODE <- "api" in run_all.R
##
## API v3 (current) adds Displacement Reason, Origin of Displacement and sex
## disaggregation. v2 has none of those and is only useful for longer history.
## =============================================================================

DTM_BASE <- "https://dtmapi.iom.int/v3/displacement"

dtm_key <- function() {
  k <- Sys.getenv("DTM_KEY")
  if (!nzchar(k)) stop(
    "DTM_KEY not set. Register at https://dtm-apim-portal.iom.int/ for a free ",
    "subscription key, then usethis::edit_r_environ() and add DTM_KEY=<key>.")
  k
}

dtm_get <- function(path, ...) {
  resp <- request(paste0(DTM_BASE, "/", path)) |>
    req_headers(`Ocp-Apim-Subscription-Key` = dtm_key()) |>
    req_url_query(...) |>
    req_retry(max_tries = 4, backoff = ~ 2 ^ .x) |>
    req_perform()
  body <- resp_body_json(resp, simplifyVector = TRUE)
  # the API wraps payloads inconsistently across endpoints
  d <- body$result %||% body$Result %||% body
  as_tibble(d)
}

dtm_countries  <- function() dtm_get("country-list")
dtm_operations <- function() dtm_get("operation-list")

#' Pull IDP figures with displacement reason.
#' @param level 0, 1 or 2 - admin level. 1 and 2 are what feed the subnational
#'   deep-dives; level 0 is enough for the country cause profiles.
fetch_dtm <- function(level = 1, country = NULL, operation = NULL,
                      from = NULL, to = NULL) {
  path <- paste0("admin", level)
  args <- list(CountryName = country, Operation = operation,
               FromReportingDate = from, ToReportingDate = to)
  args <- args[!vapply(args, is.null, logical(1))]
  do.call(dtm_get, c(list(path), args))
}

## -----------------------------------------------------------------------------
## Crosswalk: DTM reason -> identification-question response option.
##
## IMPORTANT: DTM's reason vocabulary is NOT globally standardised. Each country
## operation defines its own list, so the values below are the common ones seen
## across operations and MUST be checked against the first live pull. The tidy
## function prints every unmapped value it meets rather than silently dropping
## it - treat that printout as the to-do list, and send new values back here.
##
## This is also the most interesting table in the whole project: it is the only
## place where a category devised by people running displacement surveys can be
## compared with the categories the questionnaire offers.
## -----------------------------------------------------------------------------
DTM_REASON_TO_CODE <- c(
  ## --- code 1: armed conflict or war -----------------------------------
  "Conflict" = 1, "Armed conflict" = 1, "Armed Conflict" = 1,
  "Conflict/Insecurity" = 1, "Insecurity" = 1, "Military operations" = 1,
  "Hostilities" = 1, "War" = 1, "Fear of conflict" = 1,
  ## --- code 2: widespread violence / breakdown of public order ---------
  "Communal violence" = 2, "Communal tension" = 2, "Social tension" = 2,
  "Intercommunal violence" = 2, "Criminality" = 2, "Gang violence" = 2,
  "Banditry" = 2, "Civil unrest" = 2, "Generalized violence" = 2,
  ## --- code 3: discrimination or persecution ---------------------------
  ## DTM rarely codes this separately. Where an operation does, it is usually
  ## phrased as ethnic or religious tension. Expect very few.
  "Ethnic tension" = 3, "Religious persecution" = 3, "Persecution" = 3,
  "Discrimination" = 3,
  ## --- code 4: human rights violations by authorities ------------------
  "Human rights violations" = 4, "Forced recruitment" = 4,
  ## --- code 5: other threats of violence -------------------------------
  "Violence" = 5, "Threats" = 5, "Personal security" = 5,
  ## --- code 6: natural disasters ---------------------------------------
  "Natural disaster" = 6, "Natural Disaster" = 6, "Disaster" = 6,
  "Flood" = 6, "Floods" = 6, "Flooding" = 6, "Drought" = 6,
  "Earthquake" = 6, "Cyclone" = 6, "Storm" = 6, "Landslide" = 6,
  "Climate" = 6, "Climate/Environmental" = 6, "Environmental" = 6,
  "Climate shocks" = 6,
  ## --- code 7: man-made events -----------------------------------------
  "Eviction" = 7, "Forced eviction" = 7, "Development project" = 7,
  "Land dispute" = 7, "Pollution" = 7,
  ## --- code 8 / not a valid reason for forced displacement -------------
  ## Economic and service-access reasons are NOT valid causes of forced
  ## displacement under IRIS and must not be folded into codes 1-7. They are
  ## kept, flagged, and reported separately - the share of DTM respondents
  ## giving them is itself evidence about false positives in the instrument.
  "Economic" = NA, "Economic reasons" = NA, "Livelihood" = NA,
  "Lack of services" = NA, "Lack of livelihood" = NA, "Voluntary" = NA,
  "Family reunification" = NA, "Other" = NA, "Unknown" = NA
)

#' Reshape a DTM pull into the pipeline's tidy shape.
tidy_dtm <- function(d, reason_col = NULL, figure_col = NULL) {
  ## column names vary by endpoint version; find them rather than assume
  reason_col <- reason_col %||%
    grep("reason|driver|cause", names(d), ignore.case = TRUE, value = TRUE)[1]
  figure_col <- figure_col %||%
    grep("^numPresentIdpInd$|idpInd|individuals|figure",
         names(d), ignore.case = TRUE, value = TRUE)[1]
  if (is.na(reason_col) || is.na(figure_col))
    stop("Could not find reason/figure columns. Present: ",
         paste(names(d), collapse = ", "))

  raw <- d |>
    mutate(reason = as.character(.data[[reason_col]]),
           value  = as.numeric(.data[[figure_col]]),
           code_id = unname(DTM_REASON_TO_CODE[reason]))

  unmapped <- setdiff(unique(raw$reason[is.na(raw$code_id)]),
                      names(DTM_REASON_TO_CODE))
  if (length(unmapped)) {
    message("DTM reason values with no crosswalk entry - add them to ",
            "DTM_REASON_TO_CODE in R/04_dtm.R:")
    for (u in unmapped) message("   \"", u, "\"")
  }

  ## reasons deliberately mapped to NA (economic, voluntary, other) are not
  ## dropped - they are reported so the non-forced share stays visible
  invalid <- raw |>
    filter(reason %in% names(DTM_REASON_TO_CODE)[is.na(DTM_REASON_TO_CODE)]) |>
    summarise(n = sum(value, na.rm = TRUE)) |> pull(n)
  total <- sum(raw$value, na.rm = TRUE)
  if (isTRUE(total > 0))
    message(sprintf("DTM: %.1f%% of reported figures give a reason that is NOT a "
                    , 100 * invalid / total),
            "valid cause of forced displacement under IRIS (economic, voluntary, ",
            "other). Report this separately - do not fold it into codes 1-7.")

  admin1 <- grep("admin1Name|adm1", names(d), ignore.case = TRUE, value = TRUE)[1]
  iso <- grep("admin0Pcode|iso3|countryIso", names(d), ignore.case = TRUE, value = TRUE)[1]

  raw |>
    filter(!is.na(code_id)) |>
    transmute(
      iso3 = if (!is.na(iso)) toupper(.data[[iso]]) else to_iso3(admin0Name),
      country = .data[["admin0Name"]] %||% NA_character_,
      admin1 = if (!is.na(admin1)) .data[[admin1]] else NA_character_,
      year = as.integer(substr(as.character(
        .data[["reportingDate"]] %||% Sys.Date()), 1, 4)),
      code_id = as.integer(code_id),
      evidence_type = "reported_reason",
      value, source = "IOM DTM") |>
    group_by(iso3, country, admin1, year, code_id, evidence_type, source) |>
    summarise(value = sum(value, na.rm = TRUE), .groups = "drop")
}

## -----------------------------------------------------------------------------
## The analysis that justifies pulling DTM at all.
##
## Compares, per country, how DISPLACED PEOPLE distribute across the response
## options against how IDMC's monitors attribute the same displacement. Where
## the two diverge is where the questionnaire is doing work the databases cannot
## - and is the single most useful table this project can put in the paper.
## -----------------------------------------------------------------------------
compare_reported_vs_attributed <- function(evidence) {
  rep <- evidence |> filter(evidence_type == "reported_reason") |>
    group_by(iso3, code_id) |> summarise(v = sum(value), .groups = "drop") |>
    group_by(iso3) |> mutate(reported_share = v / sum(v)) |> ungroup() |>
    select(iso3, code_id, reported_share)
  att <- evidence |> filter(evidence_type == "displaced") |>
    group_by(iso3, code_id) |> summarise(v = sum(value), .groups = "drop") |>
    group_by(iso3) |> mutate(attributed_share = v / sum(v)) |> ungroup() |>
    select(iso3, code_id, attributed_share)
  full_join(rep, att, by = c("iso3", "code_id")) |>
    mutate(across(c(reported_share, attributed_share), ~ coalesce(.x, 0)),
           gap = reported_share - attributed_share) |>
    arrange(desc(abs(gap)))
}

## =============================================================================
## 05_independence.R - what may and may not be combined.
##
## The pipeline pools six sources into one `evidence` table. That table must
## NEVER be summed across sources to produce a total. Three separate reasons,
## and they fail in different ways:
##
##   1. DIFFERENT UNITS. People displaced, event counts, fatalities and index
##      scores are not commensurable. 40,000 people and 400 protests do not add.
##
##   2. OVERLAPPING POPULATIONS, SAME UNITS. This is the dangerous one, because
##      the arithmetic works and the answer is wrong. IDMC DERIVES its figures
##      from IOM DTM in several countries - 100% of Sudan, 99% of Haiti, 94% of
##      Ethiopia. Adding DTM to IDMC there counts the same displaced people twice.
##      ACLED and UCDP likewise both record the same underlying violent events.
##
##   3. DIFFERENT EPISTEMIC CLASSES. Even where units match, an analyst's
##      attribution (IDMC), a respondent's reported reason (DTM) and a measure of
##      whether the condition exists (V-Dem) answer different questions. Pooling
##      them produces a number that means nothing.
##
## The correct use of multiple sources here is CORROBORATION AND COVERAGE, never
## addition. For each country and code the question is "does any source support
## including this option", not "how many in total". The showcard rule in
## 02_profiles.R is written that way deliberately: each clause consults one
## source, and support from any clause is sufficient.
##
## The single legitimate sum in the whole project is IDPs + hosted refugees. Those
## populations are disjoint by definition - you either crossed an international
## border or you did not - so adding them is correct, and is what the combined
## map view does.
## =============================================================================

## Which sources measure the same underlying thing in the same units.
## "derived" means one source is partly BUILT FROM the other, so they are not
## independent even as corroboration.
SOURCE_RELATIONS <- tibble::tribble(
  ~a,              ~b,                ~relation,   ~note,
  "IDMC GIDD",     "IOM DTM",         "derived",   "IDMC sources 14% of its rows and 10% of its people from IOM DTM globally, and 50-100% in Sudan, Haiti, Ethiopia, Chad, Nigeria, Afghanistan and Mozambique. Never sum. Treat corroboration between them as circular in those countries.",
  "ACLED",         "UCDP GED",        "overlapping","Both code the same underlying violent events from overlapping media and report sources. Event counts and fatalities must not be summed across them. Use one as primary and the other as a coverage check.",
  "ACLED",         "UCDP one-sided",  "overlapping","As above, for violence against civilians.",
  "IDMC GIDD",     "UNHCR",           "overlapping","UNHCR also publishes IDP stocks, frequently taking IDMC's figure or a national one. Do not sum IDMC IDPs with UNHCR IDPs.",
  "IDMC GIDD",     "ACLED",           "independent","Different units - people displaced vs events. Genuinely complementary: ACLED shows the cause occurs, IDMC shows it displaced people.",
  "V-Dem",         "IDMC GIDD",       "independent","Conditions vs displacement. Complementary by construction.",
  "V-Dem",         "IOM DTM",         "independent","Conditions vs reported reason.",
  "UNHCR",         "IOM DTM",         "independent","Refugee stocks vs internal displacement reasons."
)

## evidence_type values that count PEOPLE and could therefore be wrongly summed
PEOPLE_TYPES <- c("displaced", "idp_stock", "reported_reason")

#' Refuse to sum across sources that are not independent.
#'
#' Call this before any aggregation that crosses sources. It errors rather than
#' warns: a silently double-counted total is worse than a failed script.
assert_summable <- function(evidence) {
  srcs <- unique(evidence$source)
  people <- evidence |> filter(evidence_type %in% PEOPLE_TYPES)
  if (dplyr::n_distinct(people$evidence_type) > 1)
    stop("Refusing to aggregate: evidence_type mixes ",
         paste(unique(people$evidence_type), collapse = " and "),
         ". Stocks, flows and reported reasons are different quantities.")
  bad <- SOURCE_RELATIONS |>
    filter(relation %in% c("derived", "overlapping"), a %in% srcs, b %in% srcs)
  if (nrow(bad))
    stop("Refusing to aggregate across non-independent sources:\n",
         paste0("  ", bad$a, " + ", bad$b, " (", bad$relation, ") - ", bad$note,
                collapse = "\n"))
  invisible(TRUE)
}

#' Per-country share of IDMC figures that come from IOM DTM.
#'
#' Requires the `Sources` column, kept by read_local_idmc_gidd(). Countries above
#' about 0.5 cannot be used to compare reported reasons against attributed causes
#' - the comparison is circular there, because IDMC's "attribution" IS DTM's data.
idmc_dtm_dependence <- function(idmc_detail) {
  stopifnot("sources" %in% tolower(names(idmc_detail)))
  col <- names(idmc_detail)[tolower(names(idmc_detail)) == "sources"][1]
  idmc_detail |>
    filter(category == "Internal Displacements") |>
    mutate(from_dtm = str_detect(coalesce(.data[[col]], ""),
                                 regex("DTM|\\bIOM\\b", ignore_case = TRUE))) |>
    group_by(iso3) |>
    summarise(dtm_share = sum(figures[from_dtm], na.rm = TRUE) /
                pmax(sum(figures, na.rm = TRUE), 1),
              people = sum(figures, na.rm = TRUE), .groups = "drop") |>
    arrange(desc(dtm_share))
}

#' Reported reason vs analyst-attributed cause - with the circular countries
#' excluded rather than silently included.
#'
#' This supersedes compare_reported_vs_attributed() in 04_dtm.R. Use this one.
compare_reported_vs_attributed_safe <- function(evidence, idmc_detail,
                                                max_dtm_share = 0.5) {
  dep <- idmc_dtm_dependence(idmc_detail)
  circular <- dep$iso3[dep$dtm_share > max_dtm_share]
  if (length(circular))
    message("Excluding ", length(circular), " countries where IDMC's figures are ",
            "largely DTM's own, making the comparison circular: ",
            paste(circular, collapse = ", "))

  rep <- evidence |> filter(evidence_type == "reported_reason") |>
    group_by(iso3, code_id) |> summarise(v = sum(value), .groups = "drop") |>
    group_by(iso3) |> mutate(reported_share = v / sum(v)) |> ungroup()
  att <- evidence |> filter(evidence_type == "displaced") |>
    group_by(iso3, code_id) |> summarise(v = sum(value), .groups = "drop") |>
    group_by(iso3) |> mutate(attributed_share = v / sum(v)) |> ungroup()

  full_join(select(rep, iso3, code_id, reported_share),
            select(att, iso3, code_id, attributed_share),
            by = c("iso3", "code_id")) |>
    mutate(across(c(reported_share, attributed_share), ~ coalesce(.x, 0)),
           gap = reported_share - attributed_share,
           independent = !iso3 %in% circular) |>
    left_join(select(dep, iso3, dtm_share), by = "iso3") |>
    arrange(desc(independent), desc(abs(gap)))
}

## =============================================================================
## 02_profiles.R - the crosswalk applied, and the showcard decision rule.
##
## Produces, for every country, for each of the 8 response options:
##   status         RECOMMENDED | RESIDUAL | UNEVIDENCED | LOW_SALIENCE
##   rationale      the numbers behind that status, in plain words
##   local_examples what the enumerator support screen should say HERE
##
## The two perspectives combined, and why both are needed:
##   DOMESTIC - IDPs displaced by events inside the country
##   ORIGIN   - refugees hosted, displaced by events in their ORIGIN countries
## Uganda is the canonical case: nothing about Ugandan events tells you what
## belongs on a Ugandan showcard, because almost everyone the questions must
## identify was displaced from South Sudan or DR Congo.
## =============================================================================

CODES <- c(
  "1" = "Armed conflict or war",
  "2" = "Widespread violence / breakdown of public order",
  "3" = "Discrimination or persecution",
  "4" = "Human rights violations by authorities",
  "5" = "Other threats of violence",
  "6" = "Natural disasters",
  "7" = "Man-made events (eviction, pollution)",
  "8" = "A different threat")

RESIDUAL_CODES <- c(5L, 8L)
## Not a response option. IDMC conflict displacement with no violence type
## recorded. Included in every denominator, never assigned a status.
UNATTRIBUTED <- 0L
## Codes where global data is structurally blind. Never recommend REMOVAL on the
## basis of zero counts - absence of evidence is not evidence of absence, and
## for these three the blindness is documented, not suspected.
BLIND_CODES <- c(3L, 4L, 7L)

PARAMS <- list(
  domestic_threshold = 0.05,
  origin_threshold   = 0.05,
  min_hosted_for_origin_weighting = 5000,  # below this, origin mix is noise
  min_origin_n       = 1000,
  event_min_share    = 0.02,
  event_min_count    = 10,
  recognition_min    = 0.50,
  recognition_min_n  = 1000,
  gov_fatality_min   = 100
)

build_profiles <- function(evidence, idmc_detail, population, recognition,
                           params = PARAMS, acled_from = 2018) {

  latest <- max(population$year, na.rm = TRUE)
  idmc_year <- max(idmc_detail$year, na.rm = TRUE)

  ## displacement-weighted shares - the strongest evidence, because it counts
  ## people who actually moved rather than events that might have moved them
  disp <- evidence |> filter(evidence_type == "displaced") |>
    group_by(iso3, code_id) |> summarise(value = sum(value), .groups = "drop") |>
    group_by(iso3) |> mutate(domestic_share = value / sum(value)) |> ungroup()

  ## event-occurrence evidence - does the cause happen here at all
  evt <- evidence |> filter(evidence_type == "events", year >= acled_from) |>
    group_by(iso3, code_id) |> summarise(events = sum(value), .groups = "drop") |>
    group_by(iso3) |> mutate(event_share = events / sum(events)) |> ungroup()

  ucdp4 <- evidence |>
    filter(str_detect(source, "^UCDP"), code_id == 4L) |>
    group_by(iso3) |> summarise(gov_fatalities = sum(value), .groups = "drop")

  latest_pop <- population |> filter(year == latest)
  hosted <- latest_pop |> group_by(iso3 = coa_iso) |>
    summarise(idps = sum(idps, na.rm = TRUE),
              refugee_pop = sum(refugees, na.rm = TRUE) +
                            sum(asylum_seekers, na.rm = TRUE), .groups = "drop")

  origin_mix <- latest_pop |>
    mutate(n = coalesce(refugees, 0) + coalesce(asylum_seekers, 0)) |>
    filter(n > 0, coo_iso != coa_iso) |>
    group_by(coa_iso, coo_iso, coo_name) |>
    summarise(n = sum(n), .groups = "drop") |>
    group_by(coa_iso) |> mutate(share = n / sum(n)) |> ungroup()

  flow <- "Internal Displacements"
  hazard_examples <- function(iso, top = 3) {
    idmc_detail |>
      filter(iso3 == iso, code_id == 6L, category == flow) |>
      group_by(hazard_sub_type) |>
      summarise(v = sum(figures, na.rm = TRUE), .groups = "drop") |>
      filter(v > 0) |> arrange(desc(v)) |> head(top) |>
      mutate(lab = sprintf("%s (%s displaced)", hazard_sub_type,
                           format(round(v), big.mark = ","))) |> pull(lab)
  }
  pretty_violence <- c(
    "Unclear/Unknown" = "conflict, type not specified by IDMC",
    "Non-International armed conflict (NIAC)" = "non-international armed conflict",
    "International armed conflict (IAC)" = "international armed conflict",
    "Other situations of violence (OSV)" = "other situations of violence")
  violence_examples <- function(iso, code, top = 3) {
    idmc_detail |>
      filter(iso3 == iso, code_id == code, category == flow) |>
      group_by(violence_type) |>
      summarise(v = sum(figures, na.rm = TRUE), .groups = "drop") |>
      filter(v > 0) |> arrange(desc(v)) |> head(top) |>
      mutate(lab = sprintf("%s (%s displaced)",
                           coalesce(pretty_violence[violence_type], violence_type),
                           format(round(v), big.mark = ","))) |> pull(lab)
  }

  universe <- sort(unique(c(disp$iso3, evt$iso3,
                            hosted$iso3[hosted$refugee_pop > 1000])))
  universe <- universe[!is.na(universe)]

  out <- map_dfr(universe, function(iso) {
    dsh <- disp |> filter(iso3 == iso)
    esh <- evt  |> filter(iso3 == iso)
    h   <- hosted |> filter(iso3 == iso)
    hosted_n <- if (nrow(h)) h$refugee_pop[1] else 0

    om <- if (hosted_n >= params$min_hosted_for_origin_weighting) {
      origin_mix |> filter(coa_iso == iso, share >= params$origin_threshold,
                           n >= params$min_origin_n)
    } else origin_mix[0, ]

    ## origin-weighted cause shares
    osh <- setNames(rep(0, 8), 1:8)
    for (i in seq_len(nrow(om))) {
      od <- disp |> filter(iso3 == om$coo_iso[i])
      for (j in seq_len(nrow(od)))
        osh[as.character(od$code_id[j])] <-
          osh[as.character(od$code_id[j])] + om$share[i] * od$domestic_share[j]
    }

    rr_here <- recognition |> filter(iso3 == iso)
    ow_rec <- if (nrow(om)) {
      w <- om |> left_join(recognition, by = c("coo_iso" = "iso3")) |>
        filter(!is.na(recognition_rate))
      if (nrow(w)) sum(w$share * w$recognition_rate) / sum(w$share) else NA_real_
    } else NA_real_
    gov_fat <- ucdp4 |> filter(iso3 == iso) |> pull(gov_fatalities)
    gov_fat <- if (length(gov_fat)) gov_fat[1] else 0

    unattributed_share <- {
      u <- dsh |> filter(code_id == UNATTRIBUTED) |> pull(domestic_share)
      if (length(u)) u[1] else 0
    }

    map_dfr(1:8, function(cc) {
      d_s <- dsh |> filter(code_id == cc) |> pull(domestic_share)
      d_s <- if (length(d_s)) d_s[1] else if (nrow(dsh)) 0 else NA_real_
      d_v <- dsh |> filter(code_id == cc) |> pull(value)
      d_v <- if (length(d_v)) d_v[1] else 0
      o_s <- unname(osh[as.character(cc)])
      e_s <- esh |> filter(code_id == cc) |> pull(event_share)
      e_s <- if (length(e_s)) e_s[1] else if (nrow(esh)) 0 else NA_real_
      e_n <- esh |> filter(code_id == cc) |> pull(events)
      e_n <- if (length(e_n)) e_n[1] else 0

      reasons <- character(0); supported <- FALSE
      if (cc %in% RESIDUAL_CODES) {
        status <- "RESIDUAL"
        reasons <- "Residual code - retained on every showcard by design"
      } else {
        if (!is.na(d_s) && d_s >= params$domestic_threshold) {
          supported <- TRUE
          reasons <- c(reasons, sprintf(
            "%.0f%% of internal displacement in-country (%s people, IDMC %d)",
            d_s * 100, format(round(d_v), big.mark = ","), idmc_year))
        }
        if (o_s >= params$origin_threshold) {
          supported <- TRUE
          reasons <- c(reasons, sprintf(
            "%.0f%% origin-weighted - refugees hosted here come from countries where this is a major cause",
            o_s * 100))
        }
        if (!is.na(e_s) && e_s >= params$event_min_share && e_n >= params$event_min_count) {
          supported <- TRUE
          reasons <- c(reasons, sprintf("%s ACLED events %d+ (%.0f%% of political violence here)",
                                        format(round(e_n), big.mark = ","), acled_from, e_s * 100))
        }
        if (cc == 3L) {
          if (nrow(rr_here) && rr_here$recognition_rate[1] >= params$recognition_min &&
              rr_here$denom[1] >= params$recognition_min_n) {
            supported <- TRUE
            reasons <- c(reasons, sprintf(
              "%.0f%% asylum recognition rate for people originating here (%s decisions)",
              rr_here$recognition_rate[1] * 100,
              format(rr_here$denom[1], big.mark = ",")))
          }
          if (!is.na(ow_rec) && ow_rec >= params$recognition_min) {
            supported <- TRUE
            reasons <- c(reasons, sprintf(
              "%.0f%% origin-weighted recognition rate for the refugee population hosted here",
              ow_rec * 100))
          }
        }
        if (cc == 4L && gov_fat >= params$gov_fatality_min) {
          supported <- TRUE
          reasons <- c(reasons, sprintf(
            "%s civilian deaths attributed to state forces, UCDP one-sided 1989+",
            format(round(gov_fat), big.mark = ",")))
        }
        status <- if (supported) "RECOMMENDED"
          else if (cc %in% BLIND_CODES) {
            reasons <- c(reasons, paste("No supporting evidence, but global data is",
              "structurally blind to this cause - retain and test in cognitive interviews"))
            "UNEVIDENCED"
          } else if (is.na(d_s) && is.na(e_s)) {
            reasons <- c(reasons, "No source covers this country"); "UNEVIDENCED"
          } else {
            reasons <- c(reasons, paste("Sources cover this country and show little",
              "displacement from this cause - de-emphasise in enumerator support",
              "material only, do NOT drop from the instrument"))
            "LOW_SALIENCE"
          }
      }

      ex <- character(0)
      if (cc == 6L) {
        ex <- hazard_examples(iso)
        for (i in seq_len(min(3, nrow(om))))
          ex <- c(ex, paste0("[via ", om$coo_name[i], " refugees] ",
                             hazard_examples(om$coo_iso[i], 2)))
      } else if (cc %in% c(1L, 2L)) {
        ex <- violence_examples(iso, cc)
        for (i in seq_len(min(3, nrow(om))))
          ex <- c(ex, paste0("[via ", om$coo_name[i], " refugees] ",
                             violence_examples(om$coo_iso[i], cc, 1)))
      }

      tibble(iso3 = iso, code_id = cc, code_label = CODES[as.character(cc)],
             status = status,
             domestic_share = d_s, origin_share = o_s,
             event_count = e_n, displaced = d_v,
             idps = if (nrow(h)) h$idps[1] else 0,
             refugees_hosted = hosted_n,
             unattributed_share = unattributed_share,
             rationale = paste(reasons, collapse = " | "),
             local_examples = paste(head(ex, 5), collapse = "; "))
    })
  })
  out
}

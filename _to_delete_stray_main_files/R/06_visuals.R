## =============================================================================
## 06_visuals.R - run the Python visualisation layer from R.
##
## The analysis is R; the interactive maps are Python. Rather than ask anyone to
## remember two commands, run_all.R calls this and one `source("run_all.R")` does
## everything. The Python is bundled in prototype-python/ and needs six packages
## (requirements.txt).
##
## Paths are passed through IDQ_ROOT, so the project runs from wherever it is
## unzipped - no hardcoded locations on either side.
## =============================================================================

#' Is a usable Python available, with the packages the visuals need?
python_ready <- function(python = NULL) {
  py <- python %||% Sys.getenv("IDQ_PYTHON", unset = "")
  if (!nzchar(py)) {
    for (cand in c("python3", "python")) {
      if (nzchar(Sys.which(cand))) { py <- unname(Sys.which(cand)); break }
    }
  }
  if (!nzchar(py)) return(list(ok = FALSE, python = NA_character_,
                               missing = character(0),
                               msg = "No python3 found on PATH."))
  need <- c("pandas", "numpy", "openpyxl", "pyarrow", "pyreadr", "pycountry")
  chk <- vapply(need, function(p) {
    system2(py, c("-c", shQuote(sprintf("import %s", p))),
            stdout = FALSE, stderr = FALSE) == 0L
  }, logical(1))
  missing <- need[!chk]
  list(ok = length(missing) == 0, python = py, missing = missing,
       msg = if (length(missing))
         sprintf("Missing Python packages: %s\n  %s -m pip install -r %s",
                 paste(missing, collapse = ", "), py,
                 file.path("prototype-python", "requirements.txt"))
       else "ready")
}

#' Build every interactive map and explorer.
#'
#' @param root project root; defaults to the working directory
#' @param steps optional character vector of module names to run instead of all
make_visuals <- function(root = getwd(), python = NULL, steps = NULL) {
  st <- python_ready(python)
  if (!st$ok) {
    message("Skipping the visualisation layer. ", st$msg)
    message("The analysis outputs (CSV, xlsx, ggplot figures) are unaffected.")
    return(invisible(FALSE))
  }
  script_dir <- file.path(root, "prototype-python")
  if (!dir.exists(script_dir)) {
    message("prototype-python/ not found under ", root, " - skipping visuals.")
    return(invisible(FALSE))
  }
  args <- if (is.null(steps)) "run_all.py" else
    c("-c", shQuote(sprintf(
      "import sys; [__import__(m).main() for m in %s]",
      paste0("['", paste(steps, collapse = "','"), "']"))))

  message("Building visuals with ", st$python, " ...")
  code <- system2(st$python, args, env = paste0("IDQ_ROOT=", shQuote(root)),
                  stdout = "", stderr = "")
  if (!identical(code, 0L))
    warning("The Python visualisation step exited with status ", code,
            ". Analysis outputs are still valid; see the log above.")
  invisible(identical(code, 0L))
}

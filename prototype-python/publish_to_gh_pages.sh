#!/usr/bin/env bash
# Rebuild the real (public) site and publish it to the gh-pages branch.
#
# Run from anywhere inside the repo, with IDQ_ROOT pointing at the real
# project root (the one with data/raw and data/tidy already fetched):
#
#   IDQ_ROOT=/path/to/idq_map ./prototype-python/publish_to_gh_pages.sh
#
# If IDQ_ROOT is unset, it defaults to this repo's own root - fine only if
# the real raw/tidy data lives inside the repo itself.
#
# What it does, in order:
#   1. Rebuilds every output with IDQ_PUBLIC=1 (drops ACLED counts).
#   2. Assembles the site/ folder via publish_site.py (written OUTSIDE the
#      repo, at $IDQ_ROOT/site, so nothing below touches git until step 4).
#   3. Checks out gh-pages (refuses if main has uncommitted changes).
#   4. rsyncs the new site in, preserving .git, .gitignore, .nojekyll - a
#      copy that didn't carry .gitignore is what let `rsync --delete` wipe
#      it last time, which let .DS_Store back in. This keeps them in place.
#   5. Commits, and tries to push. If the push needs a credential Terminal
#      doesn't have (GitHub dropped password auth for git), it says so
#      instead of failing silently - finish the push from GitHub Desktop.
#   6. Switches back to main, whatever happened in between (trap on exit).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROTO_DIR="$REPO_ROOT/prototype-python"
STARTING_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)"

cleanup() {
  if [ "$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)" != "$STARTING_BRANCH" ]; then
    echo "returning to $STARTING_BRANCH"
    git -C "$REPO_ROOT" checkout "$STARTING_BRANCH"
  fi
}
trap cleanup EXIT

if [ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]; then
  echo "error: you have uncommitted changes on $STARTING_BRANCH - commit or" >&2
  echo "stash them first, so switching to gh-pages doesn't carry them over." >&2
  exit 1
fi

cd "$PROTO_DIR"

echo "== 1/5  rebuilding outputs (IDQ_PUBLIC=1) =="
IDQ_PUBLIC=1 python3 run_all.py

echo
echo "== 2/5  assembling site/ =="
python3 publish_site.py

SITE_DIR="${IDQ_ROOT:-$REPO_ROOT}/site"
if [ ! -d "$SITE_DIR" ]; then
  echo "error: expected a site/ folder at $SITE_DIR - check IDQ_ROOT" >&2
  exit 1
fi

echo
echo "== 3/5  switching to gh-pages =="
cd "$REPO_ROOT"
git checkout gh-pages
git pull --ff-only

echo
echo "== 4/5  syncing the new build in (keeping .gitignore / .nojekyll) =="
rsync -a --delete \
  --exclude .git --exclude .gitignore --exclude .nojekyll \
  "$SITE_DIR/" "$REPO_ROOT/"

echo
echo "== 5/5  committing =="
# Safety net: gh-pages should only ever contain top-level html pages plus
# .gitignore/.nojekyll. If a branch switch ever leaves source code or raw
# data sitting here as untracked clutter, refuse to commit rather than risk
# publishing it. Any top-level *.html add/change/delete is allowed (pages
# come and go as PAGES in publish_site.py changes); anything with a slash
# (a subdirectory) or a non-html top-level file is not. (porcelain format
# is 2 status chars + space + path.)
UNEXPECTED="$(git status --porcelain | grep -vE '^.. ([^/]+\.html|\.gitignore|\.nojekyll)$' || true)"
if [ -n "$UNEXPECTED" ]; then
  echo "error: gh-pages has unexpected changes beyond the published pages:" >&2
  echo "$UNEXPECTED" >&2
  echo "Not committing - check what these are before proceeding." >&2
  exit 1
fi
git add -A
if git diff --cached --quiet; then
  echo "nothing changed - site is already up to date on gh-pages"
else
  git commit -m "Rebuild site: $(date -u '+%Y-%m-%d %H:%M UTC')"
  if git push; then
    echo
    echo "Pushed. GitHub Pages should redeploy within a minute or two."
  else
    echo
    echo "Push needs a credential this Terminal doesn't have (GitHub dropped"
    echo "password auth for git). The commit is made and sitting locally on"
    echo "the gh-pages branch. Open GitHub Desktop, switch to gh-pages there,"
    echo "and click Push origin to finish - then re-run this script's last"
    echo "step is done, no need to rebuild again."
  fi
fi

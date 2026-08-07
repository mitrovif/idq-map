"""
Assemble the shareable site, for GitHub Pages.

WHAT IS AND IS NOT PUBLISHED, AND WHY

Everything here is a derived output, and derived outputs inherit the licence of
what they were derived from. Three different regimes apply:

  UCDP GED    CC-BY-4.0. Derivatives may be republished with attribution.
  IDMC/UNHCR  citation required; aggregates are routinely republished.
  ACLED       Content Usage Terms prohibit anything that "creates a functional
              substitute" for their content, and state that the reading is
              ACLED's to make. Country x admin1 x cause event counts on a public
              page sit close enough to that line not to be worth testing.

So the published build drops ACLED COUNTS while keeping ACLED CATEGORY NAMES and
volumes in the crosswalk explorer - describing the shape of a taxonomy, and
citing how large it is, is ordinary methodological reporting, not redistribution.
The all-causes map carries per-country ACLED event counts throughout and has no
public build, so it is held back rather than published partially.

Nobody should have to reconstruct this reasoning later, which is why it is here
rather than in a commit message.

Build the public copies first:
    IDQ_PUBLIC=1 python3 build_population_map.py
then:
    python3 publish_site.py

and publish the result to the gh-pages branch:
    git worktree add /tmp/gh gh-pages
    rsync -a --delete --exclude .git "$IDQ_ROOT/site/" /tmp/gh/
    git -C /tmp/gh add -A && git -C /tmp/gh commit -m "site" && git -C /tmp/gh push
"""
from paths import ROOT, OUT
import json
import re
import shutil

# Written outside the repository tree on purpose. The site is published to the
# gh-pages branch, not committed to main - main already has a docs/ folder of
# markdown, and 2 MB of generated HTML per rebuild does not belong in its history.
SITE = ROOT / "site"

# source file -> (published name, title, blurb)
PAGES = [
    ("idq_population_by_cause.html", "index.html",
     "Causes of displacement, and the events behind them",
     "Two switchable world maps — how many people are displaced and by what, and "
     "how often each kind of event actually happens. Search a country for the "
     "response options the evidence supports there."),
    ("idq_crosswalk_explorer.html", "crosswalk.html",
     "The crosswalk",
     "All 68 categories the source databases use, and which of the eight response "
     "options each one was mapped to — including the ones that fit badly."),
    ("idq_subreasons.html", "mechanisms.html",
     "Mechanisms beneath the options",
     "66 distinct ways people are displaced, grouped under the eight options, with "
     "how a respondent might phrase each one and whether any database counts it."),
    ("idq_localised_questions.html", "questions.html",
     "Localised examples for the question",
     "Version 3 of the forced-to-flee item, with the text after each \u201ce.g.\u201d "
     "drafted from what was actually recorded in that country. The response options "
     "do not change; only the examples."),
    ("idq_evidence_map.html", "counted-vs-documented.html",
     "Counted versus documented",
     "Where human rights research documents displacement that no statistical "
     "agency counts — the case for options 3 and 7."),
]

# Carries per-country ACLED event counts throughout, with no public build.
HELD_BACK = {"idq_all_causes_map.html": "contains ACLED per-country event counts"}


def check_no_acled_counts(html, name):
    """A published page may name ACLED; it may not carry ACLED count objects."""
    bad = re.findall(r'"source":"ACLED"[^}]*"volume"', html)
    counts = re.findall(r'ACLED events 20\d\d\+', html)
    if counts:
        raise SystemExit(
            f"REFUSING to publish {name}: {len(counts)} per-country ACLED event "
            f"counts found. Rebuild with IDQ_PUBLIC=1 or add it to HELD_BACK.")
    return len(bad)


INDEX = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Causing events and the identification questions</title>
<style>
:root{color-scheme:light dark;--s:#fcfcfb;--p:#f9f9f7;--i:#0b0b0b;--i2:#52514e;
 --m:#898781;--g:#e1e0d9;--a:#2a78d6}
@media(prefers-color-scheme:dark){:root{--s:#1a1a19;--p:#0d0d0d;--i:#fff;
 --i2:#c3c2b7;--g:#2c2c2a;--a:#3987e5}}
*{box-sizing:border-box}
body{margin:0;background:var(--p);color:var(--i);font:16px/1.6 ui-sans-serif,
 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.w{max-width:820px;margin:0 auto;padding:54px 22px 80px}
h1{font-size:30px;line-height:1.2;margin:0 0 12px;letter-spacing:-.02em;font-weight:660}
.lede{color:var(--i2);font-size:17px;margin:0 0 8px}
.meta{color:var(--m);font-size:13.5px;margin:0 0 34px}
a.card{display:block;background:var(--s);border:1px solid var(--g);border-radius:12px;
 padding:17px 19px;margin-bottom:11px;text-decoration:none;color:inherit;transition:.12s}
a.card:hover{border-color:var(--a);transform:translateY(-1px)}
a.card b{font-size:16.5px;display:block;margin-bottom:3px;letter-spacing:-.01em}
a.card span{color:var(--i2);font-size:14px}
h2{font-size:15px;margin:38px 0 10px;text-transform:uppercase;letter-spacing:.05em;
 color:var(--m);font-weight:650}
p{color:var(--i2);font-size:14.5px}
code{background:var(--s);border:1px solid var(--g);border-radius:4px;padding:1px 5px;
 font-size:13px}
.note{background:var(--s);border:1px solid var(--g);border-radius:10px;padding:14px 17px;
 font-size:14px;color:var(--i2)}
table.src{border-collapse:collapse;width:100%;font-size:13.5px;margin:6px 0 4px}
table.src td{padding:7px 10px;border-bottom:1px solid var(--g);vertical-align:top;
 color:var(--i2)}
table.src td:first-child{width:118px;color:var(--i);white-space:nowrap}
pre{background:var(--s);border:1px solid var(--g);border-radius:8px;padding:11px 13px;
 font-size:12.5px;overflow-x:auto;color:var(--i)}
a{color:var(--a)}
</style></head><body><div class="w">
<h1>Causing events and the identification questions</h1>
<p class="lede">Which &ldquo;reason for fleeing&rdquo; response options does the evidence
support putting in front of respondents in each country, and what local examples should
enumerator support materials give for each one?</p>
<p class="meta">EGRISS methodological paper on identification questions for refugees and
IDPs &middot; supported by a UNHCR Data Innovation Grant</p>
__CARDS__
<h2>What this does not do</h2>
<p>It does not localise the <b>instrument</b>. The response options stay identical
everywhere, or IRIS comparability is gone and the data cannot be pooled. What varies by
country is the <b>enumerator support material</b> &mdash; which options get a worked
example, and what that example is. It also does not establish causation: &ldquo;61% of
this country&rsquo;s displacement is drought-attributed&rdquo; describes co-occurrence in
administrative statistics, not why any individual left.</p>
<h2>Sources</h2>
<p>UCDP, IDMC, UNHCR, IOM DTM and V-Dem. Each requires citation; see the repository.
<b>ACLED event counts are omitted from this published copy</b> &mdash; their terms
restrict republishing, and the analysis runs on UCDP alone. Anyone running the pipeline
themselves gets the ACLED layer back.</p>
<h2>How each source is connected</h2>
<p>Worth knowing before trusting a refresh date: <b>only one source is reached by API.</b>
Everything else is a manual export or an offline package, so the figures are pinned to a
download date rather than live.</p>
<table class="src"><tbody>
<tr><td><b>IOM DTM</b></td><td><b>API</b>, with a free subscription key, via IOM&rsquo;s own
 <code>dtmapi</code> client</td></tr>
<tr><td><b>UCDP GED</b></td><td>bulk CSV download &mdash; no key needed. An API token was
 requested for reproducible refresh, not for first results</td></tr>
<tr><td><b>IDMC</b></td><td>manual export. Disaggregated data exists only from 2023, one
 year per download; the long 2008&ndash;2025 series distinguishes only conflict vs disaster.
 API access requested</td></tr>
<tr><td><b>ACLED</b></td><td>manual export, six regional files. Counts stripped from this
 published copy on licence grounds</td></tr>
<tr><td><b>UNHCR</b></td><td>the <code>refugees</code> R package, which ships the data
 offline &mdash; no network call</td></tr>
<tr><td><b>V-Dem</b></td><td>file from the <code>vdemdata</code> repository</td></tr>
</tbody></table>

<h2>Code, and re-running it</h2>
<p><a href="https://github.com/mitrovif/idq-map">github.com/mitrovif/idq-map</a> &mdash;
R analysis with a Python visualisation layer. No source data is bundled; every input is
downloaded from its publisher, which is a licence requirement rather than a preference.</p>
<p>Full instructions, including which download goes where and the figures to check your run
against:
<a href="https://github.com/mitrovif/idq-map/blob/main/docs/reproduce.md">docs/reproduce.md</a>.
The short version, once the downloads are in place:</p>
<pre>python3 -m pip install -r prototype-python/requirements.txt
IDQ_ROOT=$(pwd) python3 prototype-python/run_all.py</pre>
<p>Fifteen steps, about three minutes. Each prints what it read and wrote, and a step whose
input is missing says so and is skipped rather than failing the run.</p>
<div class="note">These pages are a working prototype for the task team, not a
publication. Figures are current as of the source files listed in the repository, and the
crosswalk behind them is a documented judgement that is open to challenge.</div>
</div></body></html>
"""


def main():
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)
    (SITE / ".nojekyll").write_text("")

    cards, published = [], []
    for src, dest, title, blurb in PAGES:
        f = OUT / src
        if not f.exists():
            print(f"  missing, skipped: {src}")
            continue
        html = f.read_text()
        named = check_no_acled_counts(html, src)
        (SITE / dest).write_text(html)
        published.append((dest, f.stat().st_size))
        cards.append(f'<a class="card" href="{dest}"><b>{title}</b>'
                     f'<span>{blurb}</span></a>')
        print(f"  {dest:<28} {f.stat().st_size/1e6:>5.2f} MB"
              + (f"  ({named} ACLED category rows, names only)" if named else ""))

    (SITE / "index.html").write_text(INDEX.replace("__CARDS__", "\n".join(cards)))
    # index.html is the landing page, so the main map moves aside
    for src, dest, *_ in PAGES:
        if dest == "index.html":
            (SITE / "map.html").write_text((OUT / src).read_text())
            break
    cards[0] = cards[0].replace('href="index.html"', 'href="map.html"')
    (SITE / "index.html").write_text(INDEX.replace("__CARDS__", "\n".join(cards)))

    for src, why in HELD_BACK.items():
        print(f"  HELD BACK: {src} - {why}")
    total = sum(s for _, s in published) + (SITE / "map.html").stat().st_size
    print(f"\nsite in {SITE}  ({total/1e6:.1f} MB, {len(published)+1} pages)")


if __name__ == "__main__":
    main()

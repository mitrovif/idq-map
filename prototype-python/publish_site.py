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
import os
import re
import shutil

# Written outside the repository tree on purpose. The site is published to the
# gh-pages branch, not committed to main - main already has a docs/ folder of
# markdown, and 2 MB of generated HTML per rebuild does not belong in its history.
SITE = ROOT / "site"

# source file -> (published name, title, blurb, cta). Order is display order on
# the front page - the map and the questionnaire are the two pages the task team
# actually uses day to day, so they lead; the reference material (crosswalk,
# mechanisms, counted-vs-documented) follows. cta is the link text on the
# numbered front-page item ("Open the map ->" etc) - the EGRISS front page is a
# plain numbered list, not icon cards, so there's no icon column any more.
import egriss_theme as EG

PAGES = [
    ("idq_population_by_cause.html", "index.html",
     "Step 0 — Where and why: the evidence",
     "Who is displaced in each country, how many, and what displaced them; where "
     "international-protection claims are lodged. Open a country for its drafting "
     "brief — which populations to identify, which options need local examples, the "
     "areas and the office and document to name — and build the questionnaire from it.",
     "Start from the evidence"),
    ("idq_localised_questions.html", "questions.html",
     "Steps 1–6 — Build the questionnaire",
     "Choose the country and the populations to identify (the IRRS and IRIS categories); "
     "the forced-to-flee and international-protection questions are customised from the "
     "evidence and every blue value can be edited. Test the routing with respondent "
     "profiles, then download the questionnaire, the coordinator and interviewer "
     "instructions, the derivation rules with code, and a translation template — in "
     "six languages, with a link that reopens the exact set-up.",
     "Build a questionnaire"),
    ("idq_crosswalk_mechanisms.html", "crosswalk.html",
     "Reference — What sits under each option",
     "For each of the eight forced-to-flee options: 66 real-world mechanisms in words a "
     "respondent might use, and the 68 source-database categories they were "
     "mapped from — including the ones that fit badly.", "Open the crosswalk"),
    ("idq_evidence_map.html", "counted-vs-documented.html",
     "Reference — Counted versus documented",
     "Where human rights research documents displacement that no statistical "
     "agency counts — the case for keeping options 3 and 7 even where the data look empty.",
     "Open the comparison"),
]
# idq_protection_question.html / protection.html was retired: the registration
# item now lives inline on questions.html (build_questions.py), and its map
# layer lives on the main map (build_population_map.py's "Registration
# wording" view) — both read protection.py directly, so nothing is lost.
# build_protection.py itself stays as a data-prep module (build_rows() is
# imported by build_questions.py); it just no longer builds its own page.

# Carries per-country ACLED event counts throughout, with no public build.
HELD_BACK = {"idq_all_causes_map.html": "contains ACLED per-country event counts"}


def check_no_acled_counts(html, name):
    """A published page may name ACLED; it may not carry ACLED count objects,
    UNLESS the build has explicitly opted in via IDQ_ALLOW_ACLED_PUBLISH=1.

    That opt-in exists for internal/private circulation only - e.g. sharing a
    working build with colleagues before ACLED has endorsed being credited as
    a data source. Do not flip it on for a build that goes on the public
    gh-pages URL without ACLED's sign-off; their terms restrict republishing
    their event counts."""
    bad = re.findall(r'"source":"ACLED"[^}]*"volume"', html)
    counts = re.findall(r'ACLED events 20\d\d\+', html)
    if counts:
        if os.environ.get("IDQ_ALLOW_ACLED_PUBLISH") == "1":
            print(f"  WARNING: {name} carries {len(counts)} per-country ACLED "
                  f"event counts, published anyway (IDQ_ALLOW_ACLED_PUBLISH=1). "
                  f"Confirm ACLED republishing terms are cleared for this build.")
        else:
            raise SystemExit(
                f"REFUSING to publish {name}: {len(counts)} per-country ACLED event "
                f"counts found. Rebuild with IDQ_PUBLIC=1 for the ACLED-safe build, "
                f"or set IDQ_ALLOW_ACLED_PUBLISH=1 to publish the full data anyway.")
    return len(bad)


INDEX = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EGRISS identification questions</title>
__EGRISSFONTS__
<style>
__EGRISSCSS__
*{box-sizing:border-box}
:root{--eg-container:940px}
body{margin:0;font-size:16px;line-height:1.7}
.w{max-width:940px;margin:0 auto;padding:44px 24px 20px}

/* the key-figure row, the design system's third primitive */
.figs{display:flex;gap:46px;flex-wrap:wrap;margin:0 0 30px;padding:26px 28px;
 background:var(--egriss-navy);border-radius:var(--radius-lg)}
.figs .eg-figure{font-size:2.4rem;color:var(--egriss-teal)}
.figs .eg-figure-cap{color:rgba(255,255,255,.80);font-size:12.5px;max-width:20ch}
.figs .eg-figure{font-size:2.5rem}

.item{display:flex;gap:20px;padding:26px 0;border-top:1px solid var(--egriss-line);
 transition:background var(--dur-fast) var(--ease)}
.item:last-of-type{border-bottom:1px solid var(--egriss-line)}
.item:hover{background:var(--egriss-tint)}
.num{font-family:var(--font-mono);font-size:13px;color:var(--egriss-teal);font-weight:600;
 flex:0 0 auto;width:26px;padding-top:3px}
.item .body a{text-decoration:none;color:inherit}
.item b{font-family:var(--font-head);font-size:18px;display:block;margin-bottom:5px;
 letter-spacing:-.01em;color:var(--egriss-navy);font-weight:700}
.item:hover b{color:var(--egriss-blue)}
.item p{color:var(--egriss-muted);font-size:14.5px;line-height:1.55;margin:0 0 10px;max-width:56ch}
.item .go{font-family:var(--font-mono);font-size:11.5px;color:var(--egriss-blue);
 text-decoration:none;letter-spacing:.02em}
.item .go:hover{text-decoration:underline}

h2.sec{font-family:var(--font-head);font-size:12px;margin:52px 0 10px;text-transform:uppercase;
 letter-spacing:var(--ls-caps);color:var(--egriss-blue);font-weight:700}
.src-line{font-size:14.5px;color:var(--egriss-muted);line-height:1.7}
.src-line a{color:var(--egriss-blue);text-decoration:none;border-bottom:1px solid var(--egriss-line)}
.src-line a:hover{border-color:var(--egriss-blue)}

details{margin-top:6px}
details>summary{cursor:pointer;font-family:var(--font-body);font-size:14px;font-weight:600;
 color:var(--egriss-blue);list-style:none;padding:16px 0;border-top:1px solid var(--egriss-line)}
details>summary::-webkit-details-marker{display:none}
details>summary::before{content:"+ ";color:var(--egriss-muted);font-weight:700}
details[open]>summary::before{content:"\2212 ";color:var(--egriss-muted);font-weight:700}
details h2{font-family:var(--font-head);font-size:12px;margin:20px 0 8px;text-transform:uppercase;
 letter-spacing:.06em;color:var(--egriss-muted);font-weight:700}
details p{font-size:14px;color:var(--egriss-ink);line-height:1.65}
table.src{border-collapse:collapse;width:100%;font-size:13px;margin:6px 0 16px}
table.src td{padding:8px 0;border-bottom:1px solid var(--egriss-line);vertical-align:top;
 color:var(--egriss-ink)}
table.src td:first-child{width:110px;color:var(--egriss-navy);font-weight:600;white-space:nowrap}
pre{background:var(--egriss-navy);color:var(--egriss-tint-2);border-radius:var(--radius-md);
 padding:13px 15px;font-family:var(--font-mono);font-size:12.5px;overflow-x:auto}
.note{background:var(--egriss-tint);border:1px solid var(--egriss-line);
 border-radius:var(--radius-md);padding:13px 16px;font-size:13.5px;margin:18px 0}
code{background:var(--egriss-tint);border:1px solid var(--egriss-line);border-radius:var(--radius-xs);
 padding:1px 5px;font-family:var(--font-mono);font-size:12.5px}
</style></head><body>
__EGRISSMAST__
<div class="w">
<div class="figs">
 <div><span class="eg-figure">__NCOUNTRY__</span>
  <span class="eg-figure-cap">countries with a drafting brief</span></div>
 <div><span class="eg-figure">6</span>
  <span class="eg-figure-cap">survey languages</span></div>
 <div><span class="eg-figure">5</span>
  <span class="eg-figure-cap">files per questionnaire</span></div>
</div>
__CARDS__
<h2 class="sec">Sources</h2>
<p class="src-line">Built from six sources &mdash;
<a href="https://ucdp.uu.se/" target="_blank" rel="noopener">UCDP</a>,
<a href="https://acleddata.com/" target="_blank" rel="noopener">ACLED</a>,
<a href="https://www.internal-displacement.org/database/displacement-data" target="_blank" rel="noopener">IDMC</a>,
<a href="https://www.unhcr.org/refugee-statistics/" target="_blank" rel="noopener">UNHCR</a>,
<a href="https://dtm.iom.int/" target="_blank" rel="noopener">IOM DTM</a> and
<a href="https://v-dem.net/" target="_blank" rel="noopener">V-Dem</a>
&mdash; cross-referenced country by country. What each one contributes and how it was
pulled in is below; the response options themselves never change, only which of them
the evidence supports showing, and what local example illustrates each.</p>
<details>
<summary>About this project, the sources, and how to reproduce it</summary>
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
<p>Worth knowing before trusting a refresh date: <b>only one source has a confirmed, working
API connection</b> &mdash; IOM DTM. IDMC has since issued an API key too, not yet run live.
Everything else is a manual export or an offline package, so the figures are pinned to a
download date rather than live.</p>
<table class="src"><tbody>
<tr><td><b>IOM DTM</b></td><td><b>API</b>, with a free subscription key, via IOM&rsquo;s own
 <code>dtmapi</code> client</td></tr>
<tr><td><b>UCDP GED</b></td><td>bulk CSV download &mdash; no key needed. An API token was
 requested for reproducible refresh, not for first results</td></tr>
<tr><td><b>IDMC</b></td><td>manual export (default). Disaggregated data exists only from 2023,
 one year per download; the long 2008&ndash;2025 series distinguishes only conflict vs disaster.
 An API key has since been issued; not yet confirmed to carry the same detail as the manual
 disaggregated file</td></tr>
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
</details>
</div>
__EGRISSFOOT__
</body></html>
"""


# The brand layer goes in once, here: the template above carries the four
# placeholders and nothing downstream sees them. __NCOUNTRY__ is the real count
# of countries with a registration/protection record, not a round number.
def _n_countries():
    try:
        return len(json.load(open(ROOT / "config" / "protection_context.json",
                                  encoding="utf-8"))["countries"])
    except Exception:
        return 0


INDEX = (INDEX
         .replace("__EGRISSFONTS__", EG.FONTS)
         .replace("__EGRISSCSS__", EG.CSS)
         .replace("__EGRISSMAST__", EG.masthead(
             here="index.html",
             eyebrow="Expert Group on Refugee, IDP and Statelessness Statistics",
             title="The identification questions, built for a country",
             lede="Start from the evidence on who is displaced where and why, choose the "
                  "populations to identify, review the customised questions, and download the "
                  "questionnaire with its instructions, derivation rules and translation "
                  "template. The questions and response options never change; what varies by "
                  "country is the examples, the office and the document named &mdash; and "
                  "everything that varies is shown in blue and can be edited."))
         .replace("__EGRISSFOOT__", EG.sitefoot(
             "EGRISS methodological paper on identification questions for refugees and IDPs "
             "&middot; supported by a UNHCR Data Innovation Grant. A working prototype for the "
             "task team, not a publication &middot; "
             '<a href="https://github.com/mitrovif/idq-map">source and method</a>'))
         .replace("__NCOUNTRY__", str(_n_countries())))


def main():
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)
    (SITE / ".nojekyll").write_text("")

    cards, published = [], []
    for src, dest, title, blurb, cta in PAGES:
        f = OUT / src
        if not f.exists():
            print(f"  missing, skipped: {src}")
            continue
        html = f.read_text()
        named = check_no_acled_counts(html, src)
        (SITE / dest).write_text(html)
        published.append((dest, f.stat().st_size))
        num = f"{len(cards) + 1:02d}"
        cards.append(f'<div class="item"><div class="num">{num}</div><div class="body">'
                     f'<a href="{dest}"><b>{title}</b></a><p>{blurb}</p>'
                     f'<a class="go" href="{dest}">{cta} →</a></div></div>')
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

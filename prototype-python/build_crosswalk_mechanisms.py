"""
Crosswalk + mechanisms, one page: quick navigational merge.

WHY THIS EXISTS
Two pages used to stand alone - the crosswalk (68 raw database categories,
FORWARD-mapped to a response option) and the mechanisms (66 real-world ways
displacement happens, grouped under a response option, with how a respondent
might phrase each one). Both already organise themselves around the same
eight options; reading them separately meant mentally cross-referencing two
tables to answer one question: "what actually sits under option 4?"

WHAT THIS IS AND ISN'T
This is a NAVIGATIONAL merge, not a data merge. A mechanism's `sources` field
(e.g. "ACLED Armed clash; UCDP state-based") is free text, not a verified key
into crosswalk_categories.csv's `category` column - so this does not claim
mechanism N is fed by crosswalk row M. It puts both lists under the same
option, in the same tab switcher, so someone starts from "option 4" once and
sees both views instead of opening two pages. A real link between the two
tables would be a follow-up piece of methodological work, not a UI change.

Reads the two CSVs the existing build scripts already produce, rather than
re-deriving anything - crosswalk_categories.csv and subreason_taxonomy.csv
must exist (run build_crosswalk_explorer.py and build_subreason_explorer.py,
or run_all.py, first).
"""
from paths import OUT_S
import json
import math

import pandas as pd

OUT = OUT_S

CODES = {
    1: "Threat of armed conflict or war",
    2: "Widespread violence or breakdown of public order",
    3: "Discrimination or persecution",
    4: "Threat of human rights violations by authorities",
    5: "Other threats of violence against you",
    6: "Natural disasters",
    7: "Man-made events",
    8: "A different threat to your safety",
}


def _n(v):
    """NaN-safe: turn a pandas NaN into None so it serialises as JSON null."""
    return None if (v is None or (isinstance(v, float) and math.isnan(v))) else v


def main():
    cw = pd.read_csv(f"{OUT}/crosswalk_categories.csv")
    mech = pd.read_csv(f"{OUT}/subreason_taxonomy.csv")

    payload = {}
    for code, label in CODES.items():
        crows = cw[cw.code == code]
        mrows = mech[mech.code == code]
        payload[str(code)] = dict(
            label=label,
            mechanisms=[dict(name=r.mechanism, desc=r.description,
                              phrase=r.respondent_phrasing, sources=r.sources,
                              counted=r.counted) for r in mrows.itertuples()],
            categories=[dict(source=r.source, category=r.category,
                              volume=_n(r.volume), fit=r.fit, alt=_n(r.alt),
                              note=_n(r.note)) for r in crows.itertuples()],
        )

    n_mech = sum(len(v["mechanisms"]) for v in payload.values())
    n_cat = sum(len(v["categories"]) for v in payload.values())
    html = PAGE.replace("__DATA__", json.dumps(payload, separators=(",", ":")))
    open(f"{OUT}/idq_crosswalk_mechanisms.html", "w").write(html)
    print(f"wrote idq_crosswalk_mechanisms.html "
          f"({n_mech} mechanisms, {n_cat} source categories, 8 options)")


PAGE = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>What sits under each option</title>
<style>
:root{color-scheme:light dark;--s:#fcfcfb;--p:#f9f9f7;--i:#0b0b0b;--i2:#52514e;
 --m:#898781;--g:#e1e0d9;--a:#2a78d6;--good:#0ca30c;--warn:#c98a12;--bad:#d03b3b}
@media(prefers-color-scheme:dark){:root{--s:#1a1a19;--p:#0d0d0d;--i:#fff;
 --i2:#c3c2b7;--g:#2c2c2a;--a:#3987e5;--good:#3fbf3f;--warn:#e0a83a;--bad:#e35d5d}}
*{box-sizing:border-box}
body{margin:0;background:var(--p);color:var(--i);font:16px/1.6 ui-sans-serif,
 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.w{max-width:900px;margin:0 auto;padding:44px 22px 80px}
h1{font-size:26px;line-height:1.2;margin:0 0 8px;letter-spacing:-.02em;font-weight:660}
.lede{color:var(--i2);font-size:15.5px;margin:0 0 6px;max-width:640px}
.note{color:var(--m);font-size:13px;margin:0 0 28px;max-width:640px}
a{color:var(--a)}
/* option pills: one per response option, current one filled */
.opts{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:18px}
.opt{font:inherit;font-size:13px;padding:8px 13px;border-radius:20px;
 border:1px solid var(--g);background:var(--s);color:var(--i2);cursor:pointer;
 text-align:left;max-width:220px}
.opt b{display:block;font-size:11px;color:var(--m);font-weight:700}
.opt.on{background:var(--a);color:#fff;border-color:var(--a)}
.opt.on b{color:rgba(255,255,255,.75)}
/* view switcher: Mechanisms / Source categories, under the current option */
.views{display:flex;gap:4px;border-bottom:2px solid var(--g);margin-bottom:18px}
.view{font:inherit;font-size:13.5px;font-weight:650;padding:9px 16px;border:0;
 background:none;color:var(--m);cursor:pointer;border-bottom:2px solid transparent;
 margin-bottom:-2px}
.view.on{color:var(--a);border-bottom-color:var(--a)}
.cards{display:grid;gap:10px}
.card{background:var(--s);border:1px solid var(--g);border-radius:10px;padding:15px 18px}
.card .top{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
.card b.name{font-size:15px;letter-spacing:-.01em}
.card .desc{color:var(--i2);font-size:13.5px;margin:5px 0}
.card .phrase{font-family:ui-serif,Georgia,"Times New Roman",serif;font-size:14px;
 font-style:italic;color:var(--i);margin:8px 0 6px;padding-left:11px;
 border-left:3px solid var(--g)}
.card .foot{font-size:12px;color:var(--m);margin-top:6px}
.badge{font-size:10px;text-transform:uppercase;letter-spacing:.05em;font-weight:700;
 padding:2px 8px;border-radius:10px;white-space:nowrap;flex:0 0 auto}
.b-yes{background:color-mix(in srgb,var(--good) 18%,transparent);color:var(--good)}
.b-partial{background:color-mix(in srgb,var(--warn) 20%,transparent);color:var(--warn)}
.b-no{background:color-mix(in srgb,var(--bad) 16%,transparent);color:var(--bad)}
.b-exact{background:color-mix(in srgb,var(--good) 18%,transparent);color:var(--good)}
.b-broader,.b-narrower{background:color-mix(in srgb,var(--a) 16%,transparent);color:var(--a)}
.b-contested{background:color-mix(in srgb,var(--warn) 20%,transparent);color:var(--warn)}
.b-decided,.b-none,.b-pending{background:transparent;color:var(--m);border:1px solid var(--g)}
.src-tag{font-size:11px;color:var(--m);border:1px solid var(--g);border-radius:5px;
 padding:1px 7px;margin-right:6px}
.empty{color:var(--m);font-size:13.5px;padding:14px 2px}
</style></head><body><div class="w">
<h1>What sits under each option</h1>
<p class="lede">Two ways of answering the same question, side by side.
<b>Mechanisms</b> is the real-world way it happens, in words a respondent might use.
<b>Source categories</b> is the database label it was mapped from, and how good that
fit actually is.</p>
<p class="note">These two views are not cross-linked row-for-row &mdash; a mechanism's
source note (e.g. &ldquo;ACLED Armed clash&rdquo;) is descriptive text, not a verified
match to a specific category row below. Both are grouped under the same eight options
so they're easy to compare, not because each pair has been checked against the other.</p>
<div class="opts" id="opts"></div>
<div class="views">
 <button class="view on" data-v="mechanisms">Mechanisms</button>
 <button class="view" data-v="categories">Source categories</button>
</div>
<div class="cards" id="cards"></div>
</div>
<script>
const D=__DATA__;
let CODE="1", VIEW="mechanisms";
const optsEl=document.getElementById('opts'), cardsEl=document.getElementById('cards');

function esc(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;");}
function fmtN(n){n=+n||0;
 if(n>=1000000)return(n/1000000).toFixed(1).replace(/\.0$/,"")+"M";
 if(n>=1000)return(n/1000).toFixed(1).replace(/\.0$/,"")+"k";
 return String(n);}

function buildOpts(){
 optsEl.innerHTML=Object.keys(D).map(c=>{
  const v=D[c];
  return `<button class="opt${c===CODE?' on':''}" data-c="${c}">`+
   `<b>OPTION ${c}</b>${esc(v.label)}</button>`;}).join("");
 optsEl.querySelectorAll('.opt').forEach(b=>b.addEventListener('click',()=>{
  CODE=b.dataset.c; buildOpts(); render();}));}

function renderMechanisms(items){
 if(!items.length){cardsEl.innerHTML='<div class="empty">No mechanisms recorded for this option.</div>';return;}
 cardsEl.innerHTML=items.map(m=>{
  const cls=m.counted==="yes"?"b-yes":m.counted==="partial"?"b-partial":"b-no";
  const label=m.counted==="yes"?"counted":m.counted==="partial"?"partly counted":"not counted";
  return `<div class="card"><div class="top"><b class="name">${esc(m.name)}</b>`+
   `<span class="badge ${cls}">${label}</span></div>`+
   `<p class="desc">${esc(m.desc)}</p>`+
   (m.phrase?`<p class="phrase">&ldquo;${esc(m.phrase)}&rdquo;</p>`:``)+
   (m.sources?`<p class="foot">Sources: ${esc(m.sources)}</p>`:``)+
   `</div>`;}).join("");}

function renderCategories(items){
 if(!items.length){cardsEl.innerHTML='<div class="empty">No source categories mapped to this option.</div>';return;}
 cardsEl.innerHTML=items.map(c=>{
  const cls="b-"+(c.fit||"none");
  return `<div class="card"><div class="top">`+
   `<div><span class="src-tag">${esc(c.source)}</span>`+
   `<b class="name">${esc(c.category)}</b></div>`+
   `<span class="badge ${cls}">${esc(c.fit||"unmatched")}</span></div>`+
   (c.volume!=null?`<p class="foot">${fmtN(c.volume)} recorded</p>`:``)+
   (c.note?`<p class="desc">${esc(c.note)}</p>`:``)+
   (c.alt!=null?`<p class="foot">Arguable alternative: option ${esc(c.alt)}</p>`:``)+
   `</div>`;}).join("");}

function render(){
 const v=D[CODE]||{mechanisms:[],categories:[]};
 document.querySelectorAll('.view').forEach(b=>b.classList.toggle('on',b.dataset.v===VIEW));
 document.querySelector('.view[data-v="mechanisms"]').textContent=`Mechanisms (${v.mechanisms.length})`;
 document.querySelector('.view[data-v="categories"]').textContent=`Source categories (${v.categories.length})`;
 if(VIEW==="mechanisms")renderMechanisms(v.mechanisms);else renderCategories(v.categories);}

document.querySelectorAll('.view').forEach(b=>b.addEventListener('click',()=>{
 VIEW=b.dataset.v; render();}));

buildOpts(); render();
</script></body></html>
"""


if __name__ == "__main__":
    main()

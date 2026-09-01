"""
Country-specific names for the international protection / registration question.

Thin wrapper around protection.py: that module curates the per-country data and
does the self-check; this module is only the page. See protection.py's own
docstring for the full rationale, the one naming rule ("name where the claim is
LODGED, never who adjudicates it"), and the three caveats that make this a draft.

Self-contained like protection.py itself: reads config/protection_context.json
via protection.load(), needs nothing else from data/, so it runs on a clean
checkout with no pipeline dependency.
"""
from paths import OUT_S
import json

from protection import load, probes, REGISTRAR_LABEL

OUT = OUT_S


def build_rows():
    recs = load()
    out = {}
    for iso, r in sorted(recs.items(), key=lambda kv: kv[1]["country"]):
        p = probes(r)
        out[iso] = {
            "c": r["country"], "reg": r["registrar"], "how": r["channel"],
            "org": r["office"], "orgL": r["office_local"], "alt": r["office_alt"],
            "ow": r["office_why"],
            "da": r["doc_pending"], "daL": r["doc_pending_local"],
            "daC": r["doc_pending_colloquial"],
            "dr": r["doc_recognised"], "drL": r["doc_recognised_local"],
            "drC": r["doc_recognised_colloquial"],
            "dw": r["doc_why"], "cav": r["caveat"], "cf": r["confidence"],
            "mis": r["reword_v1"], "cols": r["colours"],
            "v1": p["office"], "v2": p["document"],
            "svd": [t for t in (r.get("survey", {}) or {}).get("unhcr_document_types", []) if t != "Other"],
        }
    return out


def build_summary(rows):
    reg = {}
    cf = {}
    for r in rows.values():
        reg[r["reg"]] = reg.get(r["reg"], 0) + 1
        cf[r["cf"]] = cf.get(r["cf"], 0) + 1
    return {
        "n": len(rows),
        "reg": reg, "cf": cf,
        "v1": sum(1 for r in rows.values() if r["v1"]),
        "v2": sum(1 for r in rows.values() if r["v2"]),
        "reword": sum(1 for r in rows.values() if r["mis"]),
    }


def main():
    rows = build_rows()
    summary = build_summary(rows)
    html = (PAGE.replace("__DATA__", json.dumps(rows, separators=(",", ":")))
                .replace("__SUMMARY__", json.dumps(summary, separators=(",", ":")))
                .replace("__REGLABEL__", json.dumps(REGISTRAR_LABEL, separators=(",", ":"))))
    open(f"{OUT}/idq_protection_question.html", "w").write(html)
    print(f"wrote idq_protection_question.html "
          f"({len(html)/1e6:.2f} MB, {len(rows)} countries, "
          f"{summary['v1']} v1-nameable, {summary['v2']} v2-nameable, "
          f"{summary['reword']} need rewording)")


PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>International protection — localised registration question</title><style>
:root{color-scheme:light dark;--s:#fcfcfb;--p:#f2f1ec;--i:#111;--i2:#4a4945;
 --m:#8a8880;--g:#d9d8d0;--a:#2a78d6;--w:#fab219;--paper:#fff;
 --good:#0ca30c;--bad:#d03b3b}
@media(prefers-color-scheme:dark){:root{--s:#1c1c1a;--p:#111110;--i:#f4f3ee;
 --i2:#c3c2b7;--g:#33332f;--a:#5aa0f0;--paper:#1c1c1a}}
*{box-sizing:border-box}
body{margin:0;background:var(--p);color:var(--i);font:15px/1.6 ui-sans-serif,
 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.w{max-width:980px;margin:0 auto;padding:38px 20px 80px}
h1{font-size:23px;margin:0 0 8px;letter-spacing:-.02em;font-weight:660}
p.lede{color:var(--i2);margin:0 0 16px;font-size:14.5px;max-width:76ch}
.summary{display:flex;gap:22px;flex-wrap:wrap;background:var(--paper);
 border:1px solid var(--g);border-radius:9px;padding:14px 18px;margin:14px 0 6px;
 font-size:13px}
.summary b{display:block;font-size:19px;font-family:ui-sans-serif,sans-serif}
.summary span{color:var(--i2)}
.bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:18px 0 6px}
select,.bar button{font:inherit;font-size:13.5px;padding:8px 12px;border-radius:8px;
 border:1px solid var(--g);background:var(--s);color:var(--i);cursor:pointer}
select{min-width:250px}
.badges{display:flex;gap:6px;flex-wrap:wrap;margin-left:auto}
.badge{font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;
 padding:4px 9px;border-radius:20px;font-weight:700;white-space:nowrap}
.b-reg{background:color-mix(in srgb,var(--a) 16%,transparent);color:var(--a)}
.b-cf-HIGH{background:color-mix(in srgb,var(--good) 16%,transparent);color:var(--good)}
.b-cf-MEDIUM{background:color-mix(in srgb,var(--w) 22%,transparent);color:#8a6100}
.b-cf-LOW{background:color-mix(in srgb,var(--bad) 14%,transparent);color:var(--bad)}
/* ---- the probe cards ---- */
.form{background:var(--paper);border:1px solid var(--g);border-radius:4px;
 padding:30px 34px 26px;margin-top:14px;
 box-shadow:0 1px 2px rgba(0,0,0,.05),0 8px 26px rgba(0,0,0,.06)}
.probe{border-bottom:1px solid var(--g);padding-bottom:18px;margin-bottom:18px}
.probe:last-of-type{border-bottom:0;margin-bottom:0;padding-bottom:0}
.ptag{font-family:ui-sans-serif,sans-serif;font-size:11px;font-weight:700;
 text-transform:uppercase;letter-spacing:.06em;color:var(--m);margin-bottom:6px}
.ptext{font-family:ui-serif,Georgia,"Times New Roman",serif;font-size:16px;
 line-height:1.55}
.pmiss{color:var(--m);font-style:italic;font-family:ui-sans-serif,sans-serif;
 font-size:13.5px}
.gloss{font-size:12.5px;color:var(--i2);margin-top:5px;font-family:ui-sans-serif,sans-serif}
.gloss i{font-style:italic}
.why{font-size:11.5px;color:var(--m);margin-top:4px;font-family:ui-sans-serif,sans-serif}
.warn{background:color-mix(in srgb,var(--w) 13%,transparent);
 border:1px solid color-mix(in srgb,var(--w) 42%,transparent);border-radius:9px;
 padding:12px 15px;margin-top:14px;font-size:13.5px;color:var(--i2)}
.cav{background:color-mix(in srgb,var(--a) 6%,transparent);
 border:1px solid color-mix(in srgb,var(--a) 20%,var(--g));border-radius:9px;
 padding:12px 15px;margin-top:12px;font-size:13px;color:var(--i2)}
h2{font-size:15px;margin:28px 0 2px;font-weight:640}
@media(max-width:700px){.form{padding:20px 18px}select{min-width:0;width:100%}
 .badges{margin-left:0;width:100%}}
</style>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--s:#fff;--p:#fff;--i:#1d2940;--i2:#5a6884;--m:#8b93a8;--g:#e3e8f0;
 --a:#3b71b9;--w:#e0a93b;--paper:#fff}
body{font-family:'IBM Plex Sans',sans-serif !important;background:#fff !important}
h1{font-family:'Figtree',sans-serif !important;color:#14234c !important;font-weight:700 !important;
 letter-spacing:-.015em !important}
h2{font-family:'Figtree',sans-serif !important;color:#14234c !important}
select,.bar button{border-color:var(--g) !important}
.form{box-shadow:0 1px 3px rgba(20,35,76,.06),0 10px 28px rgba(20,35,76,.08) !important}
.summary{box-shadow:0 1px 3px rgba(20,35,76,.06) !important}
</style></head><body><div class="w">
<h1>International protection &mdash; localised registration question</h1>
<p class="lede">The item asks whether someone ever applied for international
protection, a phrase cognitive interviews found poorly understood on its own.
This drafts a country-specific example of <b>where that claim is lodged</b>
(v1) and <b>what document it produces</b> (v2), the same way the forced-to-flee
item localises its own examples &mdash; the question wording is fixed, only the
named example varies. Drafted from public sources; review before fielding,
especially anything marked MEDIUM or LOW confidence.</p>

<div class="summary" id="summary"></div>

<div class="bar">
  <select id="pick"></select>
  <span class="badges" id="badges"></span>
</div>

<div class="form" id="form"></div>
<div class="warn" id="warn" style="display:none"></div>
<div class="cav" id="cav" style="display:none"></div>

<h2>Read this before using any of it</h2>
<div class="warn">
<b>These are drafts for review, not enumerator text.</b> The naming rule
throughout: name where the claim is <b>lodged</b>, never who adjudicates it
&mdash; eligibility panels, appeals boards and hotlines are excluded even where
they are well known, because a respondent never went near them.<br><br>
<b>V1 (the office) does not travel everywhere.</b> In many countries the claim
is lodged online, by post, at a police station, or happens automatically with no
office a respondent would visit &mdash; those are flagged below with the actual
channel, so the wording can be adapted rather than asked as written.<br><br>
<b>Confidence is HIGH/MEDIUM/LOW per country.</b> LOW rows are almost entirely
small Pacific and Caribbean states; check MEDIUM and LOW against a country
source before fielding.<br><br>
<b>Internal displacement is deliberately absent.</b> Of the major contexts
checked, only a handful have a verifiable IDP status document; most have none at
all, which is a finding about the instruments, not a gap in the search.
</div>
<p style="font-size:12.5px;color:var(--m);margin-top:24px">Source: curated from
public government, UNHCR and NGO documentation. Generated by
<code>prototype-python/build_protection.py</code>.</p>
</div><script>
const Q=__DATA__, S=__SUMMARY__, REGLABEL=__REGLABEL__;
const sel=document.getElementById('pick');
Object.entries(Q).forEach(([k,v])=>{const o=document.createElement('option');
 o.value=k;o.textContent=v.c;sel.appendChild(o);});
function esc(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;");}

document.getElementById('summary').innerHTML=
 `<div><b>${S.n}</b><span>countries covered</span></div>`+
 `<div><b>${S.v1}</b><span>can name an office (v1)</span></div>`+
 `<div><b>${S.v2}</b><span>can name a document (v2)</span></div>`+
 `<div><b>${S.reword}</b><span>where v1 needs rewording</span></div>`+
 `<div><b>${S.cf.HIGH||0} / ${S.cf.MEDIUM||0} / ${S.cf.LOW||0}</b>`+
 `<span>confidence: high / medium / low</span></div>`;

function render(){
 const v=Q[sel.value];
 document.getElementById('badges').innerHTML=
  `<span class="badge b-reg">${esc(REGLABEL[v.reg]||v.reg)} registers claims</span>`+
  `<span class="badge b-cf-${v.cf}">${v.cf} confidence</span>`;

 const glossLine=(local, colloq)=>{
  const bits=[local?`<i>${esc(local)}</i> in local language`:null,
              colloq?`commonly called &ldquo;${esc(colloq)}&rdquo;`:null].filter(Boolean);
  return bits.length?`<div class="gloss">${bits.join(" &middot; ")}</div>`:"";};

 let h=`<div class="probe"><div class="ptag">v1 &middot; the office</div>`;
 h+= v.v1 ? `<div class="ptext">${esc(v.v1)}</div>${glossLine(v.orgL,null)}`+
            (v.alt?`<div class="why">Also seen: ${esc(v.alt)}</div>`:"")+
            (v.ow?`<div class="why">${esc(v.ow)}</div>`:"")
          : `<div class="pmiss">&mdash; no office can be named for this country.</div>`;
 h+=`</div><div class="probe"><div class="ptag">v2 &middot; the document</div>`;
 const docName=v.da||v.dr, docLocal=v.da?v.daL:v.drL, docColloq=v.da?v.daC:v.drC;
 h+= v.v2 ? `<div class="ptext">${esc(v.v2)}</div>${glossLine(docLocal,docColloq)}`+
            (v.da&&v.dr&&v.dr!==v.da?`<div class="why">On recognition, this becomes: `+
              `${esc(v.dr)}${v.drC?` (&ldquo;${esc(v.drC)}&rdquo;)`:""}</div>`:"")+
            (v.dw?`<div class="why">${esc(v.dw)}</div>`:"")
          : `<div class="pmiss">&mdash; no document can be named for this country.</div>`;
 h+=`</div>`;
 document.getElementById('form').innerHTML=h;

 const warn=document.getElementById('warn');
 if(v.mis){warn.style.display="";
  warn.innerHTML=`<b>V1 wording likely needs rewording here.</b> ${esc(v.how)}`;
 }else{warn.style.display="none";}

 const cav=document.getElementById('cav'), cols=(v.cols&&v.cols.length)?v.cols.join(", "):null;
 if(v.cav){cav.style.display="";cav.innerHTML=`<b>Note.</b> ${esc(v.cav)}`;
  if(cols)cav.innerHTML+=`<br><b>Colour names in use:</b> ${esc(cols)}`;
 }else if(cols){cav.style.display="";cav.innerHTML=`<b>Colour names in use:</b> ${esc(cols)}`;
 }else{cav.style.display="none";}
}
sel.addEventListener('change',render);
const deepC=(new URLSearchParams(location.search).get('c')||"").toUpperCase();
sel.value=(deepC&&Q[deepC])?deepC:(Q["KEN"]?"KEN":Object.keys(Q)[0]);
render();
</script></body></html>"""


if __name__ == "__main__":
    main()

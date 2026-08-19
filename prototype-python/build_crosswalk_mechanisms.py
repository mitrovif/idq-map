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


# Fixed display order for the flow diagram - a categorical set needs a fixed
# order, never re-sorted by value, or hue-to-entity identity breaks on every
# reload. Six sources actually appear in the crosswalk (V-Dem, UNHCR and IOM
# DTM's contributions here aren't volume-comparable displacement counts, so
# most of their rows carry volume 0 - they still get a node, just a thin one).
SOURCE_ORDER = ["UCDP one-sided", "ACLED", "IDMC GIDD", "IOM DTM", "UNHCR", "V-Dem"]


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

    # Source -> option flow diagram: one link per (source, code) pair actually
    # present, volume summed across every category that source contributes to
    # that option. Only sources that appear in this data make it into the
    # fixed order used client-side.
    present = [s for s in SOURCE_ORDER if s in set(cw.source)]
    flow_rows = (cw[cw.code.notna() & (cw.code > 0)]
                 .groupby(["source", "code"])["volume"].sum().reset_index())
    flows = [dict(source=r.source, code=int(r.code), volume=_n(r.volume) or 0)
             for r in flow_rows.itertuples()]

    n_mech = sum(len(v["mechanisms"]) for v in payload.values())
    n_cat = sum(len(v["categories"]) for v in payload.values())
    html = (PAGE.replace("__DATA__", json.dumps(payload, separators=(",", ":")))
                .replace("__FLOWS__", json.dumps(flows, separators=(",", ":")))
                .replace("__SOURCES__", json.dumps(present, separators=(",", ":"))))
    open(f"{OUT}/idq_crosswalk_mechanisms.html", "w").write(html)
    print(f"wrote idq_crosswalk_mechanisms.html "
          f"({n_mech} mechanisms, {n_cat} source categories, "
          f"{len(flows)} source-to-option flows, 8 options)")


PAGE = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>What sits under each option</title>
<style>
:root{color-scheme:light dark;--s:#fcfcfb;--p:#f9f9f7;--i:#0b0b0b;--i2:#52514e;
 --m:#898781;--g:#e1e0d9;--a:#2a78d6;--good:#0ca30c;--warn:#c98a12;--bad:#d03b3b;
 --src1:#2a78d6;--src2:#eb6834;--src3:#1baf7a;--src4:#eda100;--src5:#e87ba4;--src6:#008300}
@media(prefers-color-scheme:dark){:root{--s:#1a1a19;--p:#0d0d0d;--i:#fff;
 --i2:#c3c2b7;--g:#2c2c2a;--a:#3987e5;--good:#3fbf3f;--warn:#e0a83a;--bad:#e35d5d;
 --src1:#3987e5;--src2:#d95926;--src3:#199e70;--src4:#c98500;--src5:#d55181;--src6:#008300}}
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
/* source -> option flow diagram */
.flow{margin-top:46px;padding-top:32px;border-top:1px solid var(--g)}
.flow h2{font-size:19px;margin:0 0 6px;letter-spacing:-.01em;font-weight:650}
.flow .lede{margin-bottom:16px}
.flow-legend{display:flex;flex-wrap:wrap;gap:9px 16px;margin-bottom:14px;font-size:12.5px;color:var(--i2)}
.flow-legend span{display:inline-flex;align-items:center;gap:6px}
.flow-legend i{width:10px;height:10px;border-radius:2px;display:inline-block;flex:0 0 auto}
.flow-toggle{font:inherit;font-size:12.5px;padding:5px 11px;border-radius:7px;
 border:1px solid var(--g);background:var(--s);color:var(--i2);cursor:pointer;margin-bottom:12px}
.flow-toggle:hover{border-color:var(--m)}
.flow-wrap{position:relative}
.flow-wrap[hidden]{display:none}
.flow-wrap svg{width:100%;height:auto;display:block}
.fribbon{cursor:pointer;transition:opacity .15s ease}
.fribbon.dim{opacity:.07!important}
.flabel{font-size:11px;fill:var(--i2);font-family:inherit}
.flabel.strong{fill:var(--i);font-weight:650}
.ftip{position:absolute;pointer-events:none;background:var(--s);border:1px solid var(--g);
 border-radius:8px;padding:7px 11px;font-size:12.5px;box-shadow:0 6px 20px rgba(0,0,0,.14);
 max-width:230px;opacity:0;transition:opacity .1s ease;z-index:5}
.ftip b{display:block;font-size:12.5px;margin-bottom:2px}
.flow-table{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:4px}
.flow-table[hidden]{display:none}
.flow-table th,.flow-table td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--g)}
.flow-table th{color:var(--m);font-weight:650;font-size:11px;text-transform:uppercase;letter-spacing:.04em}
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
<div class="flow">
 <h2>How sources flow into each option</h2>
 <p class="lede">Every row in the crosswalk, added up: which source database
 contributed how much recorded volume to each response option. IOM DTM and
 UNHCR show as thin slivers on purpose &mdash; their crosswalk rows aren't
 volume-comparable displacement counts, so this keeps them visibly present
 rather than making them vanish at zero. Hover a ribbon for the number.</p>
 <div class="flow-legend" id="flowLegend"></div>
 <button class="flow-toggle" id="flowToggle" type="button">View as table</button>
 <div class="flow-wrap" id="flowWrap">
  <svg id="flowSvg" viewBox="0 0 900 520" preserveAspectRatio="xMidYMid meet" role="img"
   aria-label="Diagram of recorded volume flowing from each source database to each response option"></svg>
  <div class="ftip" id="ftip"></div>
 </div>
 <table class="flow-table" id="flowTable" hidden></table>
</div>
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

// --- source -> option flow diagram (below the tabs, not tied to the option picker) ---
const FLOWS=__FLOWS__, SOURCES=__SOURCES__;
const SRC_VAR={"UCDP one-sided":"--src1","ACLED":"--src2","IDMC GIDD":"--src3",
 "IOM DTM":"--src4","UNHCR":"--src5","V-Dem":"--src6"};
const CODE_ORDER=Object.keys(D).map(Number).sort((a,b)=>a-b);

function buildFlow(){
 if(!FLOWS.length)return;
 const svg=document.getElementById('flowSvg'), legend=document.getElementById('flowLegend'),
  tip=document.getElementById('ftip'), wrap=document.getElementById('flowWrap'),
  table=document.getElementById('flowTable'), toggle=document.getElementById('flowToggle');
 const cs=getComputedStyle(document.documentElement);
 const colorOf=s=>(cs.getPropertyValue(SRC_VAR[s]||'').trim())||'#898781';

 legend.innerHTML=SOURCES.map(s=>
  `<span><i style="background:${colorOf(s)}"></i>${esc(s)}</span>`).join("")+
  `<span><i style="background:var(--m);opacity:.55"></i>response option</span>`;

 const EPS=1000,W=900,H=520,TOP=22,BOT=22,GAPS=11,GAPO=7,NODE_W=14,XS=118,XO=W-90-NODE_W;
 const AVAIL=H-TOP-BOT;

 const flowMap={}; FLOWS.forEach(f=>{flowMap[f.source+"|"+f.code]=f;});
 let total=0; FLOWS.forEach(f=>{f._m=Math.sqrt(f.volume+EPS); total+=f._m;});
 const kSrc=(AVAIL-GAPS*Math.max(0,SOURCES.length-1))/total;
 const kOpt=(AVAIL-GAPO*Math.max(0,CODE_ORDER.length-1))/total;
 const k=Math.min(kSrc,kOpt);

 const cursorSrc={}, cursorOpt={};
 SOURCES.forEach(s=>cursorSrc[s]=0); CODE_ORDER.forEach(c=>cursorOpt[c]=0);
 const ribbons=[];
 SOURCES.forEach(src=>{CODE_ORDER.forEach(code=>{
  const f=flowMap[src+"|"+code]; if(!f)return;
  const h=k*f._m, y1=cursorSrc[src], y2=cursorOpt[code];
  cursorSrc[src]+=h; cursorOpt[code]+=h;
  ribbons.push({src,code,y1,y2,h,volume:f.volume});
 });});

 const srcTotalH=SOURCES.reduce((a,s)=>a+cursorSrc[s],0)+GAPS*Math.max(0,SOURCES.length-1);
 const optTotalH=CODE_ORDER.reduce((a,c)=>a+cursorOpt[c],0)+GAPO*Math.max(0,CODE_ORDER.length-1);
 const srcStartY=TOP+(AVAIL-srcTotalH)/2, optStartY=TOP+(AVAIL-optTotalH)/2;

 const srcY0={}; let y=srcStartY;
 SOURCES.forEach(s=>{srcY0[s]=y; y+=cursorSrc[s]+GAPS;});
 const optY0={}; y=optStartY;
 CODE_ORDER.forEach(c=>{optY0[c]=y; y+=cursorOpt[c]+GAPO;});

 let out="";
 ribbons.forEach((r,i)=>{
  const x1=XS+NODE_W, x2=XO, xm=(x1+x2)/2;
  const y1t=srcY0[r.src]+r.y1, y1b=y1t+r.h, y2t=optY0[r.code]+r.y2, y2b=y2t+r.h;
  const d=`M${x1},${y1t}C${xm},${y1t} ${xm},${y2t} ${x2},${y2t}`+
   `L${x2},${y2b}C${xm},${y2b} ${xm},${y1b} ${x1},${y1b}Z`;
  out+=`<path class="fribbon" data-i="${i}" d="${d}" fill="${colorOf(r.src)}" `+
   `fill-opacity="0.42"><title>${esc(r.src)} → Option ${r.code}: `+
   `${fmtN(r.volume)} recorded</title></path>`;
 });
 SOURCES.forEach(s=>{
  const h=Math.max(cursorSrc[s],0.6), yy=srcY0[s];
  out+=`<rect class="fnode" x="${XS}" y="${yy}" width="${NODE_W}" height="${h}" `+
   `fill="${colorOf(s)}"></rect>`+
   `<text class="flabel strong" x="${XS-8}" y="${yy+h/2}" text-anchor="end" `+
   `dominant-baseline="middle">${esc(s)}</text>`;
 });
 CODE_ORDER.forEach(c=>{
  const h=Math.max(cursorOpt[c],0.6), yy=optY0[c];
  out+=`<rect class="fnode" x="${XO}" y="${yy}" width="${NODE_W}" height="${h}" `+
   `fill="var(--m)" fill-opacity="0.55"></rect>`+
   `<text class="flabel strong" x="${XO+NODE_W+8}" y="${yy+h/2}" `+
   `dominant-baseline="middle">Option ${c}</text>`;
 });
 svg.innerHTML=out;

 svg.querySelectorAll('.fribbon').forEach(el=>{
  const r=ribbons[+el.dataset.i];
  el.addEventListener('mousemove',ev=>{
   svg.querySelectorAll('.fribbon').forEach(o=>o.classList.toggle('dim',o!==el));
   const box=wrap.getBoundingClientRect();
   tip.style.opacity=1;
   tip.style.left=Math.max(0,Math.min(box.width-236,ev.clientX-box.left+14))+'px';
   tip.style.top=Math.max(0,ev.clientY-box.top-12)+'px';
   tip.innerHTML=`<b>${esc(r.src)} &rarr; Option ${r.code}</b>${fmtN(r.volume)} recorded`;
  });
  el.addEventListener('mouseleave',()=>{
   svg.querySelectorAll('.fribbon').forEach(o=>o.classList.remove('dim'));
   tip.style.opacity=0;
  });
 });

 const rows=ribbons.slice().sort((a,b)=>b.volume-a.volume);
 table.innerHTML='<thead><tr><th>Source</th><th>Option</th><th>Recorded</th></tr></thead><tbody>'+
  rows.map(r=>`<tr><td>${esc(r.src)}</td><td>Option ${r.code} &mdash; `+
  `${esc((D[r.code]||{}).label||"")}</td><td>${fmtN(r.volume)}</td></tr>`).join("")+
  '</tbody>';

 toggle.addEventListener('click',()=>{
  const showingTable=table.hasAttribute('hidden');
  if(showingTable){table.removeAttribute('hidden'); wrap.setAttribute('hidden','');}
  else{table.setAttribute('hidden',''); wrap.removeAttribute('hidden');}
  toggle.textContent=showingTable?'View as diagram':'View as table';
 });
}
buildFlow();
</script></body></html>
"""


if __name__ == "__main__":
    main()

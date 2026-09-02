"""
Evidence map: what the databases count vs what is documented.

The whole point is the contrast. Toggle between the two layers and codes 3, 4
and 7 go from blank to lit across twenty countries. Hover any researched country
for the documented evidence, the witness quote, the scale where a source gives
one, and the enumerator example. Click to pin so the source links are clickable.
"""
from paths import ROOT_S, RAW_S, UP_S, TIDY_S, OUT_S, TOPO_S
import json, os
import pandas as pd

OUT = OUT_S
TIDY = TIDY_S
TOPO = TOPO_S

from build_dashboard import decode_topology
from build_allcauses import centroid
from qualitative_data import Q

CODE_LABEL = {
 1: "Threat of armed conflict or war",
 2: "Widespread violence or breakdown of public order",
 3: "Discrimination or persecution",
 4: "Threat of human rights violations by authorities",
 6: "Natural disasters",
 7: "Man-made events",
}


def main():
    profiles = json.load(open(f"{OUT}/profiles.json"))
    feats = [f for f in decode_topology(json.load(open(TOPO)))
             if f["name"] != "Antarctica"]
    for f in feats:
        f["c"] = centroid(f["polys"])

    idmc = pd.read_parquet(f"{TIDY}/idmc_detail.parquet")
    idmc = idmc[idmc.category == "Internal Displacements"]
    counted = {}
    for (iso, c), v in idmc.groupby(["iso3", "code_id"])["figures"].sum().items():
        if v > 0:
            counted.setdefault(iso, {})[str(int(c))] = float(v)

    qual = {}
    for iso, codes in Q.items():
        qual[iso] = {str(c): dict(
            status=d["status"], scale=d["scale"], summary=d["summary"],
            quote=d["quote"], example=d["example"],
            sources=[dict(l=s[0], u=s[1]) for s in d["sources"]])
            for c, d in codes.items()}

    data = {}
    for f in feats:
        iso = f["iso3"]
        if not iso:
            continue
        p = profiles.get(iso)
        data[iso] = dict(name=(p or {}).get("name", f["name"]),
                         counted=counted.get(iso, {}),
                         qual=qual.get(iso))

    n_doc7 = sum(1 for iso in Q if Q[iso][7]["status"] == "documented")
    total7 = sum(Q[iso][7]["scale"] or 0 for iso in Q)

    payload = dict(data=data, geo=feats, labels=CODE_LABEL,
                   stats=dict(researched=len(Q), doc7=n_doc7, total7=total7,
                              counted7=695595))
    html = TPL.replace("__DATA__", json.dumps(payload, separators=(",", ":")))
    open(f"{OUT}/idq_evidence_map.html", "w").write(html)
    print(f"wrote evidence map ({os.path.getsize(f'{OUT}/idq_evidence_map.html')/1e6:.1f} MB); "
          f"{len(Q)} researched countries, code 7 documented in {n_doc7}, "
          f"{total7:,} people vs {695595:,} counted globally")


TPL = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>What is counted vs what is documented</title>
<style>
:root{color-scheme:light;--surface-1:#fcfcfb;--plane:#f9f9f7;--ink:#0b0b0b;--ink-2:#52514e;
 --muted:#898781;--grid:#e1e0d9;--land:#eceae4;--c1:#2a78d6;--c2:#eb6834;--c6:#1baf7a;
 --good:#0ca30c;--warning:#fab219;--serious:#ec835a;}
:root[data-theme="dark"]{color-scheme:dark;--surface-1:#1a1a19;--plane:#0d0d0d;--ink:#fff;
 --ink-2:#c3c2b7;--grid:#2c2c2a;--land:#2a2a28;--c1:#3987e5;--c2:#d95926;--c6:#199e70;}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;
 --surface-1:#1a1a19;--plane:#0d0d0d;--ink:#fff;--ink-2:#c3c2b7;--grid:#2c2c2a;
 --land:#2a2a28;--c1:#3987e5;--c2:#d95926;--c6:#199e70;}}
*{box-sizing:border-box}
body{margin:0;background:var(--plane);color:var(--ink);
 font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1340px;margin:0 auto;padding:24px 20px 60px}
h1{font-size:23px;margin:0 0 6px;letter-spacing:-.015em;font-weight:640}
.sub{color:var(--ink-2);margin:0 0 16px;max-width:86ch;font-size:14.5px}
.card{background:var(--surface-1);border:1px solid var(--grid);border-radius:12px;
 padding:14px;margin-top:10px}
.ctl{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:14px 0 0}
button{font:inherit;font-size:13.5px;padding:7px 12px;border-radius:8px;
 border:1px solid var(--grid);background:var(--surface-1);color:var(--ink);cursor:pointer}
button.on{background:var(--ink);color:var(--surface-1);border-color:var(--ink)}
svg{display:block;width:100%;height:auto}
path.cty{stroke:var(--surface-1);stroke-width:.45}
path.cty.live{cursor:pointer}
path.cty.live:hover{stroke:var(--ink);stroke-width:1.2}
path.cty.pin{stroke:var(--ink);stroke-width:1.8}
.key{display:flex;gap:18px;flex-wrap:wrap;margin-top:12px;font-size:13px;color:var(--ink-2)}
.key i{width:12px;height:12px;border-radius:3px;display:inline-block;margin-right:6px;
 vertical-align:-2px}
.stats{display:flex;gap:22px;flex-wrap:wrap;margin:4px 0 0}
.stat{background:var(--surface-1);border:1px solid var(--grid);border-radius:10px;
 padding:11px 16px;min-width:140px}
.stat .n{font-size:24px;font-weight:660;letter-spacing:-.02em;line-height:1.15}
.stat .l{font-size:12px;color:var(--ink-2);margin-top:2px}
.note{font-size:12.5px;color:var(--ink-2);margin-top:16px;max-width:92ch}

/* ---- the tooltip ---- */
#tt{position:fixed;background:var(--surface-1);color:var(--ink);border:1px solid var(--grid);
 border-radius:11px;padding:0;font-size:12.5px;opacity:0;pointer-events:none;
 transition:opacity .12s;box-shadow:0 10px 34px rgba(0,0,0,.18);z-index:20;
 width:405px;max-height:78vh;overflow:auto;line-height:1.5}
#tt.pinned{pointer-events:auto;opacity:1}
#tt .hd{padding:11px 14px 9px;border-bottom:1px solid var(--grid);position:sticky;top:0;
 background:var(--surface-1);display:flex;align-items:baseline;gap:8px}
#tt .hd b{font-size:14.5px;letter-spacing:-.01em}
#tt .hd .hint{margin-left:auto;font-size:10.5px;color:var(--muted);white-space:nowrap}
#tt .bd{padding:4px 14px 12px}
#tt .blk{padding:10px 0;border-bottom:1px solid var(--grid)}
#tt .blk:last-child{border-bottom:0}
#tt .ttl{display:flex;gap:7px;align-items:baseline;margin-bottom:5px}
#tt .cd{font-weight:640;font-size:12.5px;flex:1}
.badge{font-size:9.5px;font-weight:700;letter-spacing:.05em;padding:2px 6px;border-radius:4px;
 text-transform:uppercase;white-space:nowrap}
.b-doc{background:color-mix(in srgb,var(--good) 16%,transparent);color:var(--good)}
.b-abuse{background:color-mix(in srgb,var(--warning) 26%,transparent);color:#8a5d00}
:root[data-theme="dark"] .b-abuse{color:var(--warning)}
.b-none{background:transparent;color:var(--muted);border:1px solid var(--grid)}
#tt .scale{font-weight:660;color:var(--ink)}
#tt .sm{color:var(--ink-2);margin-top:3px}
#tt .qt{margin:7px 0 0;padding:7px 10px;border-left:2.5px solid var(--c1);
 background:var(--plane);border-radius:0 6px 6px 0;font-style:italic;color:var(--ink)}
#tt .ex{margin-top:7px;padding:7px 10px;background:var(--plane);border-radius:6px;
 border:1px solid var(--grid)}
#tt .ex b{font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);
 display:block;margin-bottom:2px;font-weight:650}
#tt .src{margin-top:6px;font-size:11.5px;color:var(--muted)}
#tt .src a{color:var(--c1);text-decoration:none}
#tt .src a:hover{text-decoration:underline}
#tt .cnt{font-size:11.5px;color:var(--ink-2);margin-top:2px}
</style></head><body><div class="wrap">

<h1>What is counted, and what is documented</h1>
<p class="sub">The same twenty countries under two evidence regimes. <b>Counted</b> is what
IDMC, ACLED and UCDP record — codes 1, 2 and 6, with numbers. <b>Documented</b> is what
human rights investigations establish for codes 3, 4 and 7 — real, often large, and absent
from every displacement database. Hover a country for the evidence; click to pin it so the
source links work.</p>

<div class="stats" id="stats"></div>

<div class="ctl">
  <span style="font-size:13.5px;color:var(--ink-2)">Show</span>
  <button class="v on" data-v="counted">What the databases count</button>
  <button class="v" data-v="3">Documented — 3. Persecution</button>
  <button class="v" data-v="4">Documented — 4. HR violations</button>
  <button class="v" data-v="7">Documented — 7. Man-made events</button>
  <button id="theme" style="margin-left:auto">Dark mode</button>
</div>

<div class="card">
  <svg id="map" viewBox="0 0 1000 500" role="img"
    aria-label="World map comparing counted displacement with documented evidence"></svg>
  <div class="key" id="key"></div>
</div>
<p class="note" id="vnote"></p>

<p class="note"><b>Figures are not comparable.</b> The documented scales come from individual
investigations with different scopes, periods and methods. They establish that a cause is
real and often large. They must never be summed with IDMC counts or with each other.</p>
</div>
<div id="tt"></div>
<script>
const D=__DATA__, L=D.labels;
const NS="http://www.w3.org/2000/svg";
const W=1000,H=500,LAT0=84,LAT1=-58;
const px=l=>(l+180)/360*W, py=l=>(LAT0-l)/(LAT0-LAT1)*H;
const fmt=n=>n>=1e6?(n/1e6).toFixed(n<1e7?2:1)+"m":n>=1e3?Math.round(n/1e3).toLocaleString()+"k":String(n);
const BADGE={documented:["b-doc","Documented"],abuse_only:["b-abuse","Abuse only"],
             none_found:["b-none","None found"]};
let VIEW="counted", pinned=null;

const S=D.stats;
document.getElementById('stats').innerHTML=[
 [S.researched,"countries researched"],
 [S.doc7+" of "+S.researched,"have documented code 7 displacement"],
 [fmt(S.total7),"people, code 7, where a source gives a figure"],
 [fmt(S.counted7),"people, code 7, in the entire global database"]
].map(([n,l])=>`<div class="stat"><div class="n">${n}</div><div class="l">${l}</div></div>`).join('');

const map=document.getElementById('map');
const paths=D.geo.map(f=>{
 let s="";
 for(const poly of f.polys)for(const ring of poly){
  let seg=[],segs=[];
  for(let i=0;i<ring.length;i++){
   if(i&&Math.abs(ring[i][0]-ring[i-1][0])>180){segs.push(seg);seg=[];}
   seg.push(ring[i]);}
  if(seg.length)segs.push(seg);
  for(const sg of segs){if(sg.length<2)continue;
   s+="M"+sg.map((p,i)=>(i?"L":"")+px(p[0]).toFixed(1)+","+py(p[1]).toFixed(1)).join("")+"Z";}}
 const p=document.createElementNS(NS,"path");
 p.setAttribute("d",s);p.setAttribute("class","cty");p.dataset.iso=f.iso3||"";
 map.appendChild(p);return p;});

const tt=document.getElementById('tt');
function place(e){
 const w=405,h=Math.min(tt.offsetHeight,innerHeight*.78);
 let x=e.clientX+16, y=e.clientY+14;
 if(x+w>innerWidth-12)x=e.clientX-w-16;
 if(y+h>innerHeight-12)y=Math.max(12,innerHeight-h-12);
 tt.style.left=x+"px";tt.style.top=y+"px";}

function body(iso){
 const d=D.data[iso]; if(!d)return null;
 let h=`<div class="hd"><b>${d.name}</b>`+
   `<span class="hint">${d.qual?"click to pin · sources below":""}</span></div><div class="bd">`;
 // what the databases count
 const c=d.counted, keys=Object.keys(c).filter(k=>k!=="0");
 if(keys.length){
  h+=`<div class="blk"><div class="ttl"><span class="cd">Counted by IDMC</span></div>`;
  keys.sort((a,b)=>c[b]-c[a]).forEach(k=>{
   h+=`<div class="cnt">${k}. ${L[k]||"other"} — <b>${fmt(c[k])}</b> people</div>`;});
  if(c["0"])h+=`<div class="cnt" style="color:var(--muted)">unattributed — ${fmt(c["0"])}</div>`;
  h+=`</div>`;
 }
 if(!d.qual){
  h+=`<div class="blk" style="color:var(--muted)">Not among the twenty countries researched
   for codes 3, 4 and 7.</div></div>`;
  return h;
 }
 [3,4,7].forEach(cc=>{
  const q=d.qual[String(cc)]; if(!q)return;
  const [cls,lab]=BADGE[q.status];
  h+=`<div class="blk"><div class="ttl"><span class="cd">${cc}. ${L[cc]}</span>`+
     `<span class="badge ${cls}">${lab}</span></div>`;
  if(q.scale)h+=`<div><span class="scale">${fmt(q.scale)}</span> people <span
     style="color:var(--muted)">(where a source gives a figure)</span></div>`;
  h+=`<div class="sm">${q.summary}</div>`;
  if(q.quote)h+=`<div class="qt">“${q.quote}”</div>`;
  if(q.example)h+=`<div class="ex"><b>Enumerator example</b>“${q.example}”</div>`;
  if(q.sources.length)h+=`<div class="src">`+
     q.sources.map(s=>`<a href="${s.u}" target="_blank" rel="noopener">${s.l}</a>`).join(" · ")+
     `</div>`;
  h+=`</div>`;});
 return h+`</div>`;
}

paths.forEach(p=>{
 const iso=p.dataset.iso; if(!D.data[iso])return;
 p.addEventListener('mousemove',e=>{
  if(pinned)return;
  const h=body(iso); if(!h)return;
  tt.innerHTML=h; tt.style.opacity=1; place(e);});
 p.addEventListener('mouseleave',()=>{if(!pinned)tt.style.opacity=0;});
 p.addEventListener('click',e=>{
  e.stopPropagation();
  if(pinned===p){unpin();return;}
  unpin(); pinned=p; p.classList.add('pin');
  tt.innerHTML=body(iso); tt.classList.add('pinned'); tt.style.opacity=1; place(e);});
});
function unpin(){if(pinned)pinned.classList.remove('pin');pinned=null;
 tt.classList.remove('pinned');tt.style.opacity=0;}
document.addEventListener('click',unpin);

const NOTES={
 counted:"Shaded where IDMC records displacement in 2025, by the cause it attributes. This is "+
  "the complete picture available from displacement statistics — and it contains nothing at "+
  "all for persecution or human rights violations.",
 "3":"Countries where human rights investigations document displacement caused specifically "+
  "by ethnic, religious, political, linguistic, clan or sexual-orientation persecution. "+
  "IDMC records every one of these as conflict displacement.",
 "4":"Countries where investigations document detention, torture, enforced disappearance or "+
  "confiscation of property by authorities producing displacement. Note that in most of "+
  "these the perpetrator in the place people fled from was a de facto authority — M23, the "+
  "RSF, the Houthis, the Arakan Army — not a recognised government.",
 "7":"The map that matters. Every one of these countries was UNEVIDENCED for code 7 in the "+
  "database analysis. Somalia alone documents more eviction-driven displacement (1.5 million, "+
  "2018–2024) than the entire global IDMC figure for man-made events."};

function render(){
 const cause={"1":"var(--c1)","2":"var(--c2)","6":"var(--c6)"};
 paths.forEach(p=>{
  const d=D.data[p.dataset.iso];
  p.classList.toggle('live',!!d);
  if(!d){p.setAttribute("fill","var(--land)");return;}
  if(VIEW==="counted"){
   const k=Object.keys(d.counted).filter(x=>x!=="0")
     .sort((a,b)=>d.counted[b]-d.counted[a])[0];
   p.setAttribute("fill",k&&cause[k]?cause[k]:"var(--land)");
  } else {
   const q=d.qual&&d.qual[VIEW];
   p.setAttribute("fill", !q?"var(--land)"
     : q.status==="documented"?"var(--good)"
     : q.status==="abuse_only"?"var(--warning)":"var(--serious)");
  }});
 document.getElementById('key').innerHTML = VIEW==="counted"
  ? [["var(--c1)","Armed conflict"],["var(--c2)","Widespread violence"],
     ["var(--c6)","Natural disasters"],["var(--land)","No IDMC displacement recorded"]]
     .map(([c,l])=>`<span><i style="background:${c}"></i>${l}</span>`).join('')
  : [["var(--good)","Documented displacement from this cause"],
     ["var(--warning)","Abuse documented, displacement not attributed"],
     ["var(--serious)","Searched, none found"],
     ["var(--land)","Not researched"]]
     .map(([c,l])=>`<span><i style="background:${c}"></i>${l}</span>`).join('');
 document.getElementById('vnote').innerHTML="<b>What you are looking at.</b> "+NOTES[VIEW];
}
document.querySelectorAll('.v').forEach(b=>b.addEventListener('click',e=>{
 e.stopPropagation();
 document.querySelectorAll('.v').forEach(x=>x.classList.remove('on'));
 b.classList.add('on');VIEW=b.dataset.v;unpin();render();}));
document.getElementById('theme').addEventListener('click',e=>{
 e.stopPropagation();
 const c=document.documentElement.getAttribute('data-theme');
 document.documentElement.setAttribute('data-theme',c==='dark'?'light':'dark');});
render();
</script></body></html>"""

if __name__ == "__main__":
    main()

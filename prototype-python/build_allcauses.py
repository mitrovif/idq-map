"""
All-causes map: every cause shown at once, nothing drawn where a cause is absent.

Three views, one page:
  1. ALL-CAUSES MAP   - one world map. Each country carries a fixed 6-slot glyph;
                        a slot is drawn only if that cause is evidenced there.
                        Slot position encodes the cause, so identity never rests
                        on colour alone (which also lets us exceed the 3-hue
                        all-pairs cap safely).
  2. SMALL MULTIPLES  - one mini map per cause, single hue, presence only. This
                        is the view that answers "what affects which region".
  3. REGION x CAUSE   - matrix of people displaced, region by cause.

Deliberate asymmetry in the encoding: codes 1, 2 and 6 have displacement-weighted
evidence (we know how many people each cause actually displaced), so they get
filled colour scaled by share. Codes 3, 4 and 7 rest on proxies or on nothing at
all, so they get an outlined marker. Drawing them identically would tell the
reader the evidence is comparable when it is not.
"""
from paths import ROOT_S, RAW_S, UP_S, TIDY_S, OUT_S, TOPO_S
import json, os
import pandas as pd
import pycountry

OUT = OUT_S
TIDY = TIDY_S
TOPO = TOPO_S

from build_dashboard import decode_topology

STRONG = [1, 2, 6]            # displacement-weighted evidence
PROXY = [3, 4, 7]             # proxy or no evidence
SLOTS = [1, 2, 6, 3, 4, 7]    # fixed left-to-right order in the glyph


def centroid(polys):
    """Area-weighted centroid of the largest ring — good enough for glyph anchors."""
    best, ba = None, -1
    for poly in polys:
        ring = poly[0]
        if len(ring) < 3:
            continue
        a = cx = cy = 0.0
        for i in range(len(ring) - 1):
            x0, y0 = ring[i]; x1, y1 = ring[i + 1]
            cr = x0 * y1 - x1 * y0
            a += cr; cx += (x0 + x1) * cr; cy += (y0 + y1) * cr
        if abs(a) < 1e-9:
            continue
        a *= 0.5
        if abs(a) > ba:
            ba, best = abs(a), (cx / (6 * a), cy / (6 * a))
    return best


def main():
    profiles = json.load(open(f"{OUT}/profiles.json"))
    regions = {r["iso_code"]: r for r in json.load(open(f"{TIDY}/regions.json"))}
    feats = [f for f in decode_topology(json.load(open(TOPO)))
             if f["name"] != "Antarctica"]
    for f in feats:
        f["c"] = centroid(f["polys"])

    idmc = pd.read_parquet(f"{TIDY}/idmc_detail.parquet")
    idmc = idmc[idmc.category == "Internal Displacements"]
    idmc["region"] = idmc.iso3.map(lambda i: (regions.get(i) or {}).get("unhcr_region"))
    mat = (idmc.dropna(subset=["region"])
           .groupby(["region", "code_id"])["figures"].sum().reset_index())
    matrix = {}
    for _, r in mat.iterrows():
        matrix.setdefault(r["region"], {})[str(int(r["code_id"]))] = float(r["figures"])

    # attach region + a compact cause vector to each profile
    for iso, v in profiles.items():
        v["region"] = (regions.get(iso) or {}).get("unhcr_region")
        v["vec"] = {}
        for c in SLOTS:
            d = v["codes"][str(c)]
            if d["status"] == "RECOMMENDED":
                v["vec"][str(c)] = round(max(d["domestic_share"] or 0,
                                             d["origin_share"] or 0), 3)

    payload = dict(profiles=profiles, geo=feats, matrix=matrix,
                   slots=SLOTS, strong=STRONG, proxy=PROXY)
    html = TPL.replace("__DATA__", json.dumps(payload, separators=(",", ":")))
    open(f"{OUT}/idq_all_causes_map.html", "w").write(html)
    print(f"wrote all-causes map ({os.path.getsize(f'{OUT}/idq_all_causes_map.html')/1e6:.1f} MB)")


TPL = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>All causes of displacement, by country and region</title>
<style>
:root{color-scheme:light;--surface-1:#fcfcfb;--plane:#f9f9f7;--ink:#0b0b0b;
 --ink-2:#52514e;--muted:#898781;--grid:#e1e0d9;
 --c1:#2a78d6;--c2:#eb6834;--c6:#1baf7a;--land:#ececE6;--nodata:#f0efec;
 --seq1:#cde2fb;--seq2:#9ec5f4;--seq3:#5598e7;--seq4:#2a78d6;--seq5:#184f95;}
:root[data-theme="dark"]{color-scheme:dark;--surface-1:#1a1a19;--plane:#0d0d0d;
 --ink:#fff;--ink-2:#c3c2b7;--grid:#2c2c2a;--c1:#3987e5;--c2:#d95926;--c6:#199e70;
 --land:#2c2c2a;--nodata:#232322;
 --seq1:#104281;--seq2:#1c5cab;--seq3:#3987e5;--seq4:#86b6ef;--seq5:#cde2fb;}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;
 --surface-1:#1a1a19;--plane:#0d0d0d;--ink:#fff;--ink-2:#c3c2b7;--grid:#2c2c2a;
 --c1:#3987e5;--c2:#d95926;--c6:#199e70;--land:#2c2c2a;--nodata:#232322;
 --seq1:#104281;--seq2:#1c5cab;--seq3:#3987e5;--seq4:#86b6ef;--seq5:#cde2fb;}}
*{box-sizing:border-box}
body{margin:0;background:var(--plane);color:var(--ink);
 font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1400px;margin:0 auto;padding:26px 20px 60px}
h1{font-size:24px;margin:0 0 6px;letter-spacing:-.015em;font-weight:640}
h2{font-size:17px;margin:30px 0 4px;letter-spacing:-.01em;font-weight:620}
.sub{color:var(--ink-2);margin:0 0 18px;max-width:82ch;font-size:14.5px}
.card{background:var(--surface-1);border:1px solid var(--grid);border-radius:12px;
 padding:16px;margin-top:10px}
svg{display:block;width:100%;height:auto}
path.land{fill:var(--land);stroke:var(--surface-1);stroke-width:.4}
path.land.on{cursor:pointer}
path.land.on:hover{stroke:var(--ink);stroke-width:1}
.key{display:flex;gap:20px;flex-wrap:wrap;margin-top:14px;font-size:13px;color:var(--ink-2);
 align-items:center}
.key .sw{display:inline-flex;align-items:center;gap:6px}
.key i{width:12px;height:12px;border-radius:2px;display:inline-block}
.key i.ol{background:transparent;border:1.6px solid var(--ink-2)}
.mini{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
@media(max-width:900px){.mini{grid-template-columns:repeat(2,1fr)}}
.mini .m{background:var(--surface-1);border:1px solid var(--grid);border-radius:10px;padding:10px}
.mini h3{font-size:13.5px;margin:0 0 2px;font-weight:620}
.mini .n{font-size:12px;color:var(--ink-2);margin:0 0 6px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:7px 9px;border-bottom:1px solid var(--grid);text-align:right}
th:first-child,td:first-child{text-align:left}
th{color:var(--ink-2);font-weight:600;font-size:11.5px;text-transform:uppercase;
 letter-spacing:.04em}
td.cell{color:var(--ink);font-variant-numeric:tabular-nums}
.note{font-size:12.5px;color:var(--ink-2);margin-top:16px;max-width:92ch}
#tt{position:fixed;pointer-events:none;background:var(--surface-1);color:var(--ink);
 border:1px solid var(--grid);border-radius:8px;padding:8px 11px;font-size:12.5px;
 opacity:0;transition:opacity .1s;box-shadow:0 4px 14px rgba(0,0,0,.14);z-index:9;max-width:290px}
button{font:inherit;font-size:13.5px;padding:6px 11px;border-radius:8px;
 border:1px solid var(--grid);background:var(--surface-1);color:var(--ink);cursor:pointer}
</style></head><body><div class="wrap">

<h1>All causes of displacement, at once</h1>
<p class="sub">Every response option that the evidence supports, shown together. A cause is
drawn only where there is evidence for it — countries with no evidence for a cause simply
carry nothing in that slot. Slot position is fixed left to right, so a cause is always in
the same place regardless of colour.</p>
<button id="theme">Toggle dark mode</button> <button id="reset">Reset zoom</button>
<p class="note" style="margin-top:14px"><b>Read the country counts with care.</b> Event evidence in this run comes from ACLED exports covering only Europe/Central Asia and the Middle East, so those regions clear the evidence bar for codes 1, 2 and 4 more often than elsewhere. Counts of <i>people displaced</i> come from IDMC and are global, so the region table at the bottom is the more trustworthy regional read.</p>

<h2>One map, all causes</h2>
<div class="card">
  <svg id="map" viewBox="0 0 1000 500" role="img"
    aria-label="World map with per-country markers for each evidenced cause of displacement"></svg>
  <div class="key" id="key"></div>
</div>
<p class="note"><b>Filled squares</b> (armed conflict, other violence, natural disasters)
are sized by how much of that country's displacement the cause accounts for — these have
displacement-weighted evidence from IDMC. <b>Outlined squares</b> (persecution, HR
violations, man-made events) mark causes supported only by a proxy, or by nothing at all;
they are drawn at fixed size because there is no defensible magnitude to scale them by.
Codes 5 and 8 are residual catch-alls, present on every showcard by design, so they are
not mapped.</p>

<h2>One map per cause — which regions each cause actually affects</h2>
<p class="sub">The same data split out. Countries are shaded only where the cause is
evidenced; everything else is left blank rather than shown as zero.</p>
<div class="mini" id="mini"></div>

<h2>People displaced by region and cause</h2>
<p class="sub">Internal displacement recorded by IDMC in 2025, by UNHCR region. Blank cells
are causes that produced no recorded displacement in that region.</p>
<div class="card"><table id="mat"></table></div>
<p class="note">Europe's armed-conflict figure looks small because this run holds IDMC
data for 2025 only, and Ukraine's largest outflows were in 2022 — the all-years GIDD export
would change this row substantially. Man-made events (code 7) is empty in every region — no agency counts
development-induced displacement, so its absence here is a gap in the data, not evidence
the cause is rare.</p>
</div><div id="tt"></div>
<script>
const D=__DATA__;
const CODES={1:"Armed conflict or war",2:"Widespread violence / public order",
3:"Discrimination or persecution",4:"HR violations by authorities",
5:"Other threats of violence",6:"Natural disasters",7:"Man-made events"};
const COL={1:"var(--c1)",2:"var(--c2)",6:"var(--c6)"};
const SLOTS=D.slots, STRONG=D.strong;
const W=1000,H=500,LAT0=84,LAT1=-58;
const px=l=>(l+180)/360*W, py=l=>(LAT0-l)/(LAT0-LAT1)*H;
function pathOf(f,w,h){const sx=w/W,sy=h/H;let s="";
 for(const poly of f.polys)for(const ring of poly){
  let seg=[],segs=[];
  for(let i=0;i<ring.length;i++){
   if(i&&Math.abs(ring[i][0]-ring[i-1][0])>180){segs.push(seg);seg=[];}
   seg.push(ring[i]);}
  if(seg.length)segs.push(seg);
  for(const sg of segs){if(sg.length<2)continue;
   s+="M"+sg.map((p,i)=>(i?"L":"")+(px(p[0])*sx).toFixed(1)+","+(py(p[1])*sy).toFixed(1)).join("")+"Z";}}
 return s;}
const NS="http://www.w3.org/2000/svg";
const tt=document.getElementById('tt');
function tipOn(el,html){el.addEventListener('mousemove',e=>{tt.innerHTML=html;
 tt.style.opacity=1;tt.style.left=Math.min(e.clientX+14,innerWidth-300)+"px";
 tt.style.top=(e.clientY+14)+"px";});
 el.addEventListener('mouseleave',()=>tt.style.opacity=0);}

/* ---------------- main all-causes map ---------------- */
const map=document.getElementById('map');
const root=document.createElementNS(NS,"g"); map.appendChild(root);
D.geo.forEach(f=>{const p=document.createElementNS(NS,"path");
 p.setAttribute("d",pathOf(f,W,H));p.setAttribute("class","land");root.appendChild(p);});
// --- zoom / pan: at world scale the European glyphs overlap into mush
let Z=1,TX=0,TY=0;
function applyT(){root.setAttribute("transform",`translate(${TX},${TY}) scale(${Z})`);
 root.querySelectorAll("g[data-glyph]").forEach(g=>{
   g.setAttribute("transform",g.dataset.base+` scale(${(1/Z).toFixed(3)})`);});}
map.addEventListener("wheel",e=>{e.preventDefault();
 const r=map.getBoundingClientRect();
 const mx=(e.clientX-r.left)/r.width*W, my=(e.clientY-r.top)/r.height*H;
 const f=e.deltaY<0?1.18:1/1.18, nz=Math.min(12,Math.max(1,Z*f));
 TX=mx-(mx-TX)*(nz/Z); TY=my-(my-TY)*(nz/Z); Z=nz;
 if(Z===1){TX=0;TY=0;} applyT();},{passive:false});
let drag=null;
map.addEventListener("mousedown",e=>{drag=[e.clientX,e.clientY,TX,TY];map.style.cursor="grabbing";});
addEventListener("mouseup",()=>{drag=null;map.style.cursor="";});
addEventListener("mousemove",e=>{if(!drag)return;
 const r=map.getBoundingClientRect();
 TX=drag[2]+(e.clientX-drag[0])/r.width*W; TY=drag[3]+(e.clientY-drag[1])/r.height*H; applyT();});
document.getElementById('reset').addEventListener('click',()=>{Z=1;TX=0;TY=0;applyT();});

const SW=4.6, GAP=1.1;                    // slot square size and spacing
D.geo.forEach(f=>{
  const pr=f.iso3&&D.profiles[f.iso3]; if(!pr||!f.c)return;
  const present=SLOTS.filter(c=>pr.vec[String(c)]!==undefined);
  if(!present.length)return;
  const cx=px(f.c[0]), cy=py(f.c[1]);
  const total=present.length*(SW+GAP)-GAP;
  const g=document.createElementNS(NS,"g");
  const base=`translate(${(cx-total/2).toFixed(1)},${(cy-SW/2).toFixed(1)})`;
  g.dataset.glyph="1"; g.dataset.base=base; g.setAttribute("transform",base);
  present.forEach((c,i)=>{
    const share=pr.vec[String(c)];
    const strong=STRONG.includes(c);
    const r=document.createElementNS(NS,"rect");
    // strong causes: size scales with share (min 45% so tiny shares stay visible)
    const s=strong?SW*(0.45+0.55*Math.min(1,share)):SW*0.78;
    r.setAttribute("x",(i*(SW+GAP)+(SW-s)/2).toFixed(2));
    r.setAttribute("y",((SW-s)/2).toFixed(2));
    r.setAttribute("width",s.toFixed(2));r.setAttribute("height",s.toFixed(2));
    r.setAttribute("rx","1");
    if(strong){r.setAttribute("fill",COL[c]);r.setAttribute("stroke","var(--surface-1)");
      r.setAttribute("stroke-width",".5");}
    else{r.setAttribute("fill","none");r.setAttribute("stroke","var(--ink-2)");
      r.setAttribute("stroke-width","1.1");}
    g.appendChild(r);});
  const hit=document.createElementNS(NS,"rect");
  hit.setAttribute("x","-3");hit.setAttribute("y","-3");
  hit.setAttribute("width",(total+6).toFixed(1));hit.setAttribute("height",(SW+6).toFixed(1));
  hit.setAttribute("fill","transparent");hit.style.cursor="pointer";
  g.appendChild(hit);
  const rows=present.map(c=>`<div>${STRONG.includes(c)
    ?`<b style="color:${COL[c]}">■</b>`:`<b style="color:var(--ink-2)">▢</b>`} ${CODES[c]}`+
    (STRONG.includes(c)&&pr.vec[String(c)]>0?` — ${Math.round(pr.vec[String(c)]*100)}%`:``)+`</div>`).join("");
  tipOn(hit,`<b>${pr.name}</b><div style="margin-top:4px">${rows}</div>`);
  root.appendChild(g);});

document.getElementById('key').innerHTML =
  SLOTS.map(c=>`<span class="sw"><i class="${STRONG.includes(c)?'':'ol'}"
   style="${STRONG.includes(c)?'background:'+COL[c]:''}"></i>${c}. ${CODES[c]}</span>`).join('')
  + `<span class="sw" style="color:var(--muted)">slot order is fixed — a cause always sits in the same position</span>`;

/* ---------------- small multiples ---------------- */
const MW=300,MH=150;
document.getElementById('mini').innerHTML = SLOTS.map(c=>{
  const isStrong=STRONG.includes(c);
  const hits=Object.values(D.profiles).filter(p=>p.vec[String(c)]!==undefined);
  let subtitle;
  if(isStrong){
    // rank by people displaced, from IDMC's global coverage - NOT by country
    // count, which just reflects which regions we happen to have event data for
    const rr={};Object.entries(D.matrix).forEach(([r,m])=>{if(m[String(c)])rr[r]=m[String(c)];});
    const top=Object.entries(rr).sort((a,b)=>b[1]-a[1]).slice(0,2)
      .map(([r,n])=>`${r} (${n>=1e6?(n/1e6).toFixed(1)+"m":Math.round(n/1e3)+"k"})`).join(", ");
    subtitle=`${hits.length} countries · most displacement in ${top||"—"}`;
  } else {
    subtitle=hits.length?`${hits.length} countries · proxy evidence only — the pattern `+
      `reflects where we can measure, not where the cause occurs`
      :`no evidence anywhere — the cause is uncounted, not absent`;
  }
  const paths=D.geo.map(f=>{
    const pr=f.iso3&&D.profiles[f.iso3];
    const on=pr&&pr.vec[String(c)]!==undefined;
    const fill=on?(isStrong?COL[c]:"var(--muted)"):"var(--nodata)";
    return `<path d="${pathOf(f,MW,MH)}" fill="${fill}" stroke="var(--surface-1)" stroke-width=".3"/>`;
  }).join('');
  return `<div class="m"><h3>${c}. ${CODES[c]}</h3>
    <p class="n">${subtitle}</p>
    <svg viewBox="0 0 ${MW} ${MH}">${paths}</svg></div>`;
}).join('');

/* ---------------- region x cause matrix ---------------- */
const M=D.matrix, regs=Object.keys(M).sort();
const codesInMat=[1,2,6,7];
let max=0;regs.forEach(r=>codesInMat.forEach(c=>{max=Math.max(max,M[r][String(c)]||0);}));
const ramp=["var(--seq1)","var(--seq2)","var(--seq3)","var(--seq4)","var(--seq5)"];
const fmt=n=>n>=1e6?(n/1e6).toFixed(1)+"m":n>=1e3?Math.round(n/1e3)+"k":String(Math.round(n));
document.getElementById('mat').innerHTML =
 `<thead><tr><th>Region</th>${codesInMat.map(c=>`<th>${c}. ${CODES[c]}</th>`).join('')}</tr></thead>
  <tbody>${regs.map(r=>`<tr><td>${r}</td>`+codesInMat.map(c=>{
    const v=M[r][String(c)]||0;
    if(!v)return `<td style="color:var(--muted)">—</td>`;
    const k=Math.min(4,Math.floor(Math.sqrt(v/max)*5));
    const dark=k>=3;
    return `<td class="cell" style="background:${ramp[k]};${dark?'color:#fff':''}">${fmt(v)}</td>`;
  }).join('')+`</tr>`).join('')}</tbody>`;

document.getElementById('theme').addEventListener('click',()=>{
 const c=document.documentElement.getAttribute('data-theme');
 document.documentElement.setAttribute('data-theme',c==='dark'?'light':'dark');});
</script></body></html>"""

if __name__ == "__main__":
    main()

"""Build the self-contained interactive dashboard."""
from paths import ROOT_S, RAW_S, UP_S, TIDY_S, OUT_S, TOPO_S
import json, os, math
import pandas as pd
import pycountry

OUT = OUT_S
TOPO = TOPO_S

# ---------------------------------------------------------------- topojson -> geojson
def decode_geojson(gj, ndigits=2):
    """Natural Earth ships plain GeoJSON, world-atlas ships TopoJSON. Both are
    legitimate sources for the basemap and neither is redistributable here, so
    whichever one the user downloaded has to work. Same output shape."""
    feats = []
    for f in gj["features"]:
        p = f.get("properties", {})
        geom = f.get("geometry") or {}
        if geom.get("type") == "Polygon":
            polys = [geom["coordinates"]]
        elif geom.get("type") == "MultiPolygon":
            polys = geom["coordinates"]
        else:
            continue
        iso3 = next((p[k] for k in ("ISO_A3", "ADM0_A3", "iso_a3", "id")
                     if isinstance(p.get(k), str) and len(p[k]) == 3
                     and p[k] != "-99"), None)
        polys = [[[(round(float(x), ndigits), round(float(y), ndigits))
                   for x, y in r] for r in poly] for poly in polys]
        feats.append(dict(iso3=iso3,
                          name=p.get("NAME") or p.get("name") or "",
                          polys=polys))
    return feats


def decode_topology(topo, obj="countries", ndigits=2):
    if topo.get("type") == "FeatureCollection":
        return decode_geojson(topo, ndigits)
    tr = topo.get("transform")
    sx, sy = (tr["scale"] if tr else (1, 1))
    tx, ty = (tr["translate"] if tr else (0, 0))

    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx; y += dy
            pts.append((x * sx + tx, y * sy + ty) if tr else (x, y))
        arcs.append(pts)

    def ring(idxs):
        out = []
        for i in idxs:
            a = arcs[~i][::-1] if i < 0 else arcs[i]
            out.extend(a[1:] if out else a)
        return out

    feats = []
    for g in topo["objects"][obj]["geometries"]:
        if g["type"] == "Polygon":
            polys = [[ring(r) for r in g["arcs"]]]
        elif g["type"] == "MultiPolygon":
            polys = [[ring(r) for r in poly] for poly in g["arcs"]]
        else:
            continue
        iso3 = None
        try:
            c = pycountry.countries.get(numeric=str(g["id"]).zfill(3))
            iso3 = c.alpha_3 if c else None
        except Exception:
            pass
        polys = [[[(round(x, ndigits), round(y, ndigits)) for x, y in r]
                  for r in poly] for poly in polys]
        feats.append(dict(iso3=iso3, name=g.get("properties", {}).get("name", ""),
                          polys=polys))
    return feats


def main():
    profiles = json.load(open(f"{OUT}/profiles.json"))
    feats = decode_topology(json.load(open(TOPO)))
    # drop Antarctica and features we cannot key
    feats = [f for f in feats if f["name"] != "Antarctica"]

    tab = pd.read_csv(f"{OUT}/showcard_recommendations.csv")

    # dominant cause per country (only codes 1, 2, 6 ever win - three
    # categorical slots, which is exactly the all-pairs cap for a choropleth)
    dom = {}
    for iso, v in profiles.items():
        best, bs = None, 0.0
        for c, d in v["codes"].items():
            s = max(d["domestic_share"] or 0, d["origin_share"] or 0)
            if s > bs:
                bs, best = s, int(c)
        dom[iso] = dict(code=best, share=round(bs, 3))

    n_countries = len(profiles)
    n_rec = int((tab.status == "RECOMMENDED").sum())
    n_code7_unev = int(((tab.code_id == 7) & (tab.status == "UNEVIDENCED")).sum())
    n_origin_driven = sum(
        1 for v in profiles.values()
        if any((v["codes"][c]["origin_share"] or 0) >= 0.05 >
               (v["codes"][c]["domestic_share"] or 0) for c in ("1", "2", "6")))

    payload = dict(profiles=profiles, geo=feats, dom=dom,
                   stats=dict(countries=n_countries, recommended=n_rec,
                              code7_unevidenced=n_code7_unev,
                              origin_driven=n_origin_driven))

    html = TEMPLATE.replace("__DATA__", json.dumps(payload, separators=(",", ":")))
    with open(f"{OUT}/idq_causing_events_dashboard.html", "w") as f:
        f.write(html)
    size = os.path.getsize(f"{OUT}/idq_causing_events_dashboard.html") / 1e6
    print(f"wrote dashboard ({size:.1f} MB), {len(feats)} map features, "
          f"{n_countries} countries")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Causing events and the EGRISS identification questions</title>
<style>
:root{color-scheme:light;
 --surface-1:#fcfcfb; --plane:#f9f9f7; --ink:#0b0b0b; --ink-2:#52514e;
 --muted:#898781; --grid:#e1e0d9;
 --c1:#2a78d6; --c2:#eb6834; --c6:#1baf7a;
 --good:#0ca30c; --warning:#fab219; --serious:#ec835a; --critical:#d03b3b;
 --nodata:#e6e5df;}
:root[data-theme="dark"]{color-scheme:dark;
 --surface-1:#1a1a19; --plane:#0d0d0d; --ink:#fff; --ink-2:#c3c2b7;
 --muted:#898781; --grid:#2c2c2a;
 --c1:#3987e5; --c2:#d95926; --c6:#199e70; --nodata:#2c2c2a;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
 color-scheme:dark; --surface-1:#1a1a19; --plane:#0d0d0d; --ink:#fff;
 --ink-2:#c3c2b7; --grid:#2c2c2a; --c1:#3987e5; --c2:#d95926; --c6:#199e70;
 --nodata:#2c2c2a;}}
*{box-sizing:border-box}
body{margin:0;background:var(--plane);color:var(--ink);
 font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1440px;margin:0 auto;padding:28px 22px 60px}
h1{font-size:25px;margin:0 0 6px;letter-spacing:-.015em;font-weight:640}
.sub{color:var(--ink-2);margin:0 0 22px;max-width:78ch;font-size:14.5px}
.stats{display:flex;gap:26px;flex-wrap:wrap;margin:0 0 22px}
.stat{background:var(--surface-1);border:1px solid var(--grid);border-radius:10px;
 padding:12px 18px;min-width:150px}
.stat .n{font-size:26px;font-weight:660;letter-spacing:-.02em;line-height:1.15}
.stat .l{font-size:12.5px;color:var(--ink-2);margin-top:2px}
.controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:0 0 14px}
select,button{font:inherit;font-size:13.5px;padding:7px 11px;border-radius:8px;
 border:1px solid var(--grid);background:var(--surface-1);color:var(--ink);cursor:pointer}
.layout{display:grid;grid-template-columns:1fr 400px;gap:18px;align-items:start}
@media(max-width:1080px){.layout{grid-template-columns:1fr}}
.card{background:var(--surface-1);border:1px solid var(--grid);border-radius:12px;padding:16px}
svg{display:block;width:100%;height:auto}
path.cty{stroke:var(--surface-1);stroke-width:.5;cursor:pointer}
path.cty:hover{stroke:var(--ink);stroke-width:1.2}
path.cty.sel{stroke:var(--ink);stroke-width:1.6}
.legend{display:flex;gap:16px;flex-wrap:wrap;margin-top:12px;font-size:13px;color:var(--ink-2)}
.legend i{width:13px;height:13px;border-radius:3px;display:inline-block;
 vertical-align:-2px;margin-right:6px}
.panel h2{font-size:17px;margin:0 0 2px;letter-spacing:-.01em}
.panel .meta{color:var(--ink-2);font-size:13px;margin-bottom:12px}
.codes{border-top:1px solid var(--grid)}
.code{border-bottom:1px solid var(--grid);padding:10px 0}
.code .top{display:flex;gap:8px;align-items:flex-start}
.badge{font-size:10.5px;letter-spacing:.055em;font-weight:680;padding:3px 7px;
 border-radius:5px;white-space:nowrap;text-transform:uppercase}
.b-REC{background:color-mix(in srgb,var(--good) 17%,transparent);color:var(--good)}
.b-UNE{background:color-mix(in srgb,var(--warning) 25%,transparent);color:#8a5d00}
:root[data-theme="dark"] .b-UNE{color:var(--warning)}
.b-LOW{background:color-mix(in srgb,var(--muted) 20%,transparent);color:var(--ink-2)}
.b-RES{background:color-mix(in srgb,var(--c1) 15%,transparent);color:var(--c1)}
.code .lbl{font-weight:590;font-size:13.5px;flex:1}
.code .why{font-size:12.5px;color:var(--ink-2);margin-top:5px}
.code .ex{font-size:12.5px;margin-top:5px;color:var(--ink)}
.code .ex b{font-weight:600;color:var(--ink-2);font-weight:550}
.origins{font-size:12.5px;color:var(--ink-2);margin:8px 0 14px;padding:9px 11px;
 background:var(--plane);border-radius:8px;border:1px solid var(--grid)}
table{border-collapse:collapse;width:100%;font-size:12.5px;margin-top:8px}
th,td{text-align:left;padding:5px 8px;border-bottom:1px solid var(--grid)}
th{color:var(--ink-2);font-weight:600;font-size:11.5px;text-transform:uppercase;
 letter-spacing:.04em}
td.s{font-weight:600}
.note{font-size:12.5px;color:var(--ink-2);margin-top:20px;max-width:90ch}
details summary{cursor:pointer;font-size:13.5px;color:var(--ink-2);margin-top:18px}
#tt{position:fixed;pointer-events:none;background:var(--surface-1);color:var(--ink);
 border:1px solid var(--grid);border-radius:8px;padding:7px 10px;font-size:12.5px;
 opacity:0;transition:opacity .1s;box-shadow:0 4px 14px rgba(0,0,0,.13);z-index:9}
</style></head><body>
<div class="wrap">
<h1>Causing events and the identification questions</h1>
<p class="sub">Which "reason for fleeing" response options the available evidence supports
putting in front of respondents in each country — and what local examples the enumerator
support screen should give. Response options follow Version 3 (long) of the EGRISS
identification questions. Prototype built on IDMC GIDD 2025, ACLED (Europe/Central Asia and
Middle East only), UCDP one-sided violence 1989–2025, and UNHCR population statistics.</p>

<div class="stats" id="stats"></div>

<div class="controls">
  <label for="view" style="font-size:13.5px;color:var(--ink-2)">Colour the map by</label>
  <select id="view">
    <option value="dom">Dominant cause of displacement</option>
    <option value="1">Status — 1. Armed conflict or war</option>
    <option value="2">Status — 2. Widespread violence / public order</option>
    <option value="3">Status — 3. Discrimination or persecution</option>
    <option value="4">Status — 4. HR violations by authorities</option>
    <option value="6">Status — 6. Natural disasters</option>
    <option value="7">Status — 7. Man-made events</option>
    <option value="cov">Data coverage</option>
  </select>
  <button id="theme">Toggle dark mode</button>
</div>

<div class="layout">
  <div class="card">
    <svg id="map" viewBox="0 0 980 480" role="img"
      aria-label="World map coloured by dominant cause of displacement"></svg>
    <div class="legend" id="legend"></div>
  </div>
  <div class="card panel" id="panel"></div>
</div>

<details>
<summary>Table view — all countries and codes (accessible alternative to the map)</summary>
<div class="card" style="margin-top:10px;max-height:520px;overflow:auto">
<table id="tbl"><thead><tr><th>Country</th><th>IDPs</th><th>Refugees hosted</th>
<th>Dominant cause</th><th>Recommended codes</th><th>Unevidenced</th></tr></thead>
<tbody></tbody></table></div>
</details>

<p class="note"><b>How to read this.</b> <b>Recommended</b> means the evidence supports
showing the option and giving local examples. <b>Unevidenced</b> means no source covers
that cause here — for codes 3, 4 and 7 this is expected, because global datasets do not
count non-lethal repression, discrimination, or development-induced eviction; those codes
are never recommended for removal on the basis of zero counts. <b>Low salience</b> means
sources do cover the country and show little displacement from that cause — grounds for
de-emphasis in <i>enumerator support material only</i>, never for dropping the option from
the instrument, which must stay internationally comparable. <b>Residual</b> codes 5 and 8
stay on every showcard by design.</p>
<p class="note"><b>Coverage caveats.</b> ACLED here covers only Europe/Central Asia (2018+)
and the Middle East (2015+); other regions show no event evidence and lean on IDMC alone.
IDMC GIDD in this build is 2025 only, so it reflects one year rather than lifetime recall.
Origin-weighting is suppressed for countries hosting fewer than 5,000 refugees.</p>
</div>
<div id="tt"></div>
<script>
const D = __DATA__;
const CODES={1:"Armed conflict or war",2:"Widespread violence / breakdown of public order",
3:"Discrimination or persecution",4:"Human rights violations by authorities",
5:"Other threats of violence",6:"Natural disasters",
7:"Man-made events (eviction, pollution)",8:"A different threat"};
const CAUSE_COLOR={1:"var(--c1)",2:"var(--c2)",6:"var(--c6)"};
const STATUS_COLOR={RECOMMENDED:"var(--good)",UNEVIDENCED:"var(--warning)",
 LOW_SALIENCE:"var(--nodata)",RESIDUAL:"var(--c1)"};
const BADGE={RECOMMENDED:"b-REC",UNEVIDENCED:"b-UNE",LOW_SALIENCE:"b-LOW",RESIDUAL:"b-RES"};
const SHORT={RECOMMENDED:"Recommended",UNEVIDENCED:"Unevidenced",
 LOW_SALIENCE:"Low salience",RESIDUAL:"Residual"};

// ---- stats
const S=D.stats;
document.getElementById('stats').innerHTML=[
 [S.countries,"countries profiled"],
 [S.recommended,"country × code options recommended"],
 [S.origin_driven,"countries where the case rests on refugees' origins, not local events"],
 [S.code7_unevidenced,"countries with no evidence at all for code 7"]
].map(([n,l])=>`<div class="stat"><div class="n">${n}</div><div class="l">${l}</div></div>`).join('');

// ---- projection (equirectangular, clipped to habitable latitudes)
const W=980,H=480,LAT0=84,LAT1=-58;
const px=l=>(l+180)/360*W, py=l=>(LAT0-l)/(LAT0-LAT1)*H;
function d(f){let s="";
 for(const poly of f.polys){for(const ring of poly){
  // split the ring wherever it crosses the antimeridian
  let seg=[],segs=[];
  for(let i=0;i<ring.length;i++){
    if(i&&Math.abs(ring[i][0]-ring[i-1][0])>180){segs.push(seg);seg=[];}
    seg.push(ring[i]);}
  if(seg.length)segs.push(seg);
  for(const sg of segs){ if(sg.length<2)continue;
    s+="M"+sg.map((p,i)=>(i?"L":"")+px(p[0]).toFixed(1)+","+py(p[1]).toFixed(1)).join("")+"Z";}
 }}return s;}

const svg=document.getElementById('map');
const paths=D.geo.map(f=>{
  const p=document.createElementNS("http://www.w3.org/2000/svg","path");
  p.setAttribute("d",d(f)); p.setAttribute("class","cty");
  p.dataset.iso=f.iso3||""; p.dataset.name=f.name;
  svg.appendChild(p); return p;});

let sel=null;
function colorFor(iso,mode){
  const pr=D.profiles[iso];
  if(mode==="dom"){const dm=D.dom[iso];
    if(!dm||!dm.code||!CAUSE_COLOR[dm.code])return "var(--nodata)";
    return CAUSE_COLOR[dm.code];}
  if(mode==="cov"){if(!pr)return "var(--nodata)";
    const c=pr.coverage,n=(c.idmc?1:0)+(c.acled?1:0)+(c.unhcr?1:0);
    return n>=3?"var(--good)":n===2?"var(--warning)":n===1?"var(--serious)":"var(--nodata)";}
  if(!pr)return "var(--nodata)";
  return STATUS_COLOR[pr.codes[mode].status]||"var(--nodata)";
}
const LEGENDS={
 dom:[["var(--c1)","Armed conflict or war"],["var(--c2)","Widespread violence / public order"],
      ["var(--c6)","Natural disasters"],["var(--nodata)","No displacement data"]],
 cov:[["var(--good)","All three sources"],["var(--warning)","Two sources"],
      ["var(--serious)","One source"],["var(--nodata)","None"]]};
function statusLegend(){return [["var(--good)","Recommended"],["var(--warning)","Unevidenced"],
 ["var(--nodata)","Low salience"],["var(--c1)","Residual"]];}

function render(){
  const mode=document.getElementById('view').value;
  paths.forEach(p=>p.setAttribute("fill",colorFor(p.dataset.iso,mode)));
  const L=LEGENDS[mode]||statusLegend();
  document.getElementById('legend').innerHTML=
    L.map(([c,l])=>`<span><i style="background:${c}"></i>${l}</span>`).join('');
}

const tt=document.getElementById('tt');
paths.forEach(p=>{
  p.addEventListener('mousemove',e=>{
    const pr=D.profiles[p.dataset.iso];
    const dm=D.dom[p.dataset.iso];
    tt.innerHTML=`<b>${pr?pr.name:p.dataset.name}</b>`+
      (pr?`<br>${dm&&dm.code?CODES[dm.code]+" — "+Math.round(dm.share*100)+"%":"no cause data"}`
        :`<br>no data`);
    tt.style.opacity=1;tt.style.left=(e.clientX+14)+"px";tt.style.top=(e.clientY+14)+"px";});
  p.addEventListener('mouseleave',()=>tt.style.opacity=0);
  p.addEventListener('click',()=>{if(D.profiles[p.dataset.iso])show(p.dataset.iso,p);});
});

function show(iso,pathEl){
  const pr=D.profiles[iso];
  if(sel)sel.classList.remove('sel');
  if(pathEl){pathEl.classList.add('sel');sel=pathEl;}
  const fmt=n=>n>=1000?Math.round(n).toLocaleString():String(Math.round(n));
  let h=`<h2>${pr.name}</h2><div class="meta">${fmt(pr.idps)} IDPs · `+
        `${fmt(pr.refugees_hosted)} refugees &amp; asylum seekers hosted<br>`+
        `sources: ${Object.entries(pr.coverage).filter(([,v])=>v).map(([k])=>k.toUpperCase()).join(", ")||"none"}</div>`;
  if(pr.origins.length)
    h+=`<div class="origins"><b>Refugee origins driving this showcard:</b> `+
       pr.origins.map(o=>`${o.name} ${Math.round(o.share*100)}%`).join(" · ")+`</div>`;
  h+=`<div class="codes">`;
  for(let c=1;c<=8;c++){
    const v=pr.codes[String(c)];
    h+=`<div class="code"><div class="top">`+
       `<span class="badge ${BADGE[v.status]}">${SHORT[v.status]}</span>`+
       `<span class="lbl">${c}. ${CODES[c]}</span></div>`;
    if(v.reasons.length)h+=`<div class="why">${v.reasons.join("<br>")}</div>`;
    if(v.examples.length)h+=`<div class="ex"><b>Local examples for enumerators:</b> `+
       v.examples.join("; ")+`</div>`;
    h+=`</div>`;}
  h+=`</div>`;
  document.getElementById('panel').innerHTML=h;
}

// ---- table view (the relief requirement for the sub-3:1 aqua slot)
const tb=document.querySelector('#tbl tbody');
tb.innerHTML=Object.values(D.profiles).sort((a,b)=>
   (b.idps+b.refugees_hosted)-(a.idps+a.refugees_hosted)).map(p=>{
  const dm=D.dom[p.iso3];
  const rec=Object.entries(p.codes).filter(([,v])=>v.status==="RECOMMENDED").map(([k])=>k);
  const une=Object.entries(p.codes).filter(([,v])=>v.status==="UNEVIDENCED").map(([k])=>k);
  return `<tr><td>${p.name}</td><td>${Math.round(p.idps).toLocaleString()}</td>`+
   `<td>${Math.round(p.refugees_hosted).toLocaleString()}</td>`+
   `<td class="s">${dm&&dm.code?CODES[dm.code]:"—"}</td>`+
   `<td>${rec.join(", ")||"—"}</td><td>${une.join(", ")||"—"}</td></tr>`;}).join('');

document.getElementById('view').addEventListener('change',render);
document.getElementById('theme').addEventListener('click',()=>{
  const cur=document.documentElement.getAttribute('data-theme');
  document.documentElement.setAttribute('data-theme',cur==='dark'?'light':'dark');});
render();
show('SOM',paths.find(p=>p.dataset.iso==='SOM'));
</script></body></html>"""

if __name__ == "__main__":
    main()

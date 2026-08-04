"""
Crosswalk explorer: every source category, its volume, and where it lands.

Built bottom-up. Rather than starting from the questionnaire and hunting for
matching data, this enumerates every category value each database actually
uses, measures how much displacement or violence sits in it, and shows which
response option it currently feeds. Categories where the match is arguable are
flagged, with the alternative reading stated.

Two directions matter and they fail differently:
  FORWARD  source category -> response option. Reveals force-fits.
  REVERSE  response option -> what feeds it. Reveals starvation.
"""
from paths import ROOT_S, RAW_S, UP_S, TIDY_S, OUT_S, TOPO_S
import json, os, glob
import pandas as pd

OUT = OUT_S
UP = UP_S

CODES = {
    0: "UNATTRIBUTED \u2014 not a response option",
    1: "Threat of armed conflict or war",
    2: "Widespread violence or breakdown of public order",
    3: "Discrimination or persecution",
    4: "Threat of human rights violations by authorities",
    5: "Other threats of violence against you",
    6: "Natural disasters",
    7: "Man-made events",
    8: "A different threat to your safety",
}

# fit: exact | broader | narrower | contested | none
# 'contested' means a defensible reading puts it elsewhere - the alternative is named.
IDMC_MAP = {
 "International armed conflict (IAC)":      (1,"exact",None,"IDMC's own adjudication of interstate armed conflict."),
 "Non-International armed conflict (NIAC)": (1,"exact",None,"Internal armed conflict. Note this is also where persecution-driven displacement lands: Rohingya displacement by military operations is coded NIAC, not persecution."),
 "Other situations of violence (OSV)":      (2,"exact",None,"Communal, criminal and gang violence below the armed-conflict threshold. Maps cleanly to 'breakdown of public order'."),
 "Unclear/Unknown":                         (0,"decided",None,"DECIDED: reported as its own unattributed band rather than defaulted into code 1. Stays in every denominator, so country shares are shares of ALL displacement and no longer sum to 100% across the eight options. 2.0m people (3.15%) that nobody classified."),
 "Typhoon/Hurricane/Cyclone":               (6,"exact",None,"Largest single disaster bucket worldwide."),
 "Flood":                                   (6,"exact",None,None),
 "Tsunami":                                 (6,"exact",None,None),
 "Earthquake":                              (6,"exact",None,None),
 "Wildfire":                                (7,"decided",6,"DECIDED: reassigned to man-made on the reading that most ignition is human. Note this single category is 99.8% of everything now in code 7 \u2014 the other two human-triggered hazards contribute 1,378 people between them. Any claim about code 7 is effectively a claim about wildfire."),
 "Drought":                                 (6,"exact",None,"Slow-onset. A respondent who left over several years may not describe it as fleeing."),
 "Storm":                                   (6,"exact",None,None),
 "Mixed disasters":                         (6,"broader",None,"Multiple hazards in one figure - cannot yield a specific local example for enumerators."),
 "Erosion":                                 (6,"exact",None,"Slow-onset, same recall problem as drought."),
 "Landslide/Wet mass movement":             (6,"exact",None,None),
 "Hailstorm":                               (6,"exact",None,None),
 "Volcanic activity":                       (6,"exact",None,None),
 "Tornado":                                 (6,"exact",None,None),
 "Dry mass movement":                       (6,"exact",None,None),
 "Winter storm/Blizzard":                   (6,"exact",None,None),
 "Cold wave":                               (6,"exact",None,None),
 "Storm surge":                             (6,"exact",None,None),
 "Dam release flood":                       (7,"decided",6,"DECIDED: reassigned. Filed by IDMC as a natural flood, but the trigger is infrastructure operation. Unambiguously man-made; only 1,223 people."),
 "Sand/dust storm":                         (6,"exact",None,None),
 "Sinkhole":                                (7,"decided",6,"DECIDED: reassigned. Often induced by mining or groundwater extraction. 155 people."),
 "Avalanche":                               (6,"exact",None,None),
 "Sea level rise":                          (6,"exact",None,"Slow-onset."),
}

ACLED_MAP = {
 "Armed clash":                        (1,"exact",None,None),
 "Air/drone strike":                   (1,"exact",None,None),
 "Shelling/artillery/missile attack":  (1,"exact",None,None),
 "Remote explosive/landmine/IED":      (1,"exact",None,None),
 "Suicide bomb":                       (1,"exact",None,None),
 "Grenade":                            (1,"exact",None,None),
 "Chemical weapon":                    (1,"exact",None,None),
 "Government regains territory":       (1,"exact",None,None),
 "Non-state actor overtakes territory":(1,"exact",None,None),
 "Disrupted weapons use":              (None,"none",None,"Weapons intercepted or defused before use. Displaces nobody. Was previously mapped to code 1, inflating its event count by 30,628 - removed."),
 "Mob violence":                       (2,"exact",None,None),
 "Violent demonstration":              (2,"exact",None,None),
 "Protest with intervention":          (2,"exact",None,None),
 "Looting/property destruction":       (2,"pending",4,"DEFERRED pending ACLED credentials. Code 4 explicitly lists 'confiscation of property'; the aggregated export has no actor column, so looting by armed groups cannot be told from confiscation by authorities. Split by state vs non-state perpetrator once the full event API is available."),
 "Arrests":                            (4,"contested",None,"Detention is named in code 4. But ACLED files arrests as a strategic development, not violence, and most arrests displace nobody."),
 "Excessive force against protesters": (4,"contested",2,"Genuinely straddles: state perpetrator points to code 4, public-order setting points to code 2."),
 "Attack":                             (5,"decided",None,"DECIDED: stays in code 5. Largest ambiguous category (33,085 events, 37,299 fatalities). Keeping it out of code 1 avoids absorbing targeted violence against civilians into the war category \u2014 the exact conflation this exercise identified as the core problem."),
 "Abduction/forced disappearance":     (5,"contested",4,"Enforced disappearance by the state is a code 4 human rights violation; abduction by an armed group is code 5."),
 "Sexual violence":                    (5,"contested",3,"Where targeted at a group it is persecution (3); by authorities it is code 4. Massively under-reported in all sources."),
 "Peaceful protest":                   (None,"none",None,"Largest ACLED category at 386,822 events, and correctly mapped to nothing - peaceful protest does not displace."),
 "Agreement":                          (None,"none",None,None),
 "Change to group/activity":           (None,"none",None,None),
 "Headquarters or base established":   (None,"none",None,None),
 "Non-violent transfer of territory":  (None,"none",None,None),
 "Other":                              (None,"none",None,"Unclassifiable residual."),
}


def main():
    d = pd.read_excel(f"{UP}/5140e1e8-IDMC_GIDD_Internal_Displacement_Disaggregated.xlsx",
                      sheet_name="1_Disaggregated_Data")
    fl = d[d["Figure category"] == "Internal Displacements"].copy()
    fl["bucket"] = fl["Hazard sub type"].fillna(fl["Violence type"]).fillna("(unspecified)")
    ig = (fl.groupby("bucket").agg(n=("ID", "size"), v=("Total figures", "sum"))
          .reset_index().sort_values("v", ascending=False))

    A = pd.concat([pd.read_excel(p) for p in
                   glob.glob(f"{UP}/*aggregated_data*.xlsx")])
    A.columns = [c.upper() for c in A.columns]
    ag = (A.groupby("SUB_EVENT_TYPE").agg(n=("EVENTS", "sum"), f=("FATALITIES", "sum"))
          .reset_index().sort_values("n", ascending=False))

    rows = []
    for r in ig.itertuples():
        m = IDMC_MAP.get(r.bucket, (None, "none", None, "unmapped"))
        rows.append(dict(source="IDMC GIDD", category=r.bucket, unit="people displaced",
                         volume=float(r.v), rows=int(r.n), code=m[0], fit=m[1],
                         alt=m[2], note=m[3]))
    for r in ag.itertuples():
        m = ACLED_MAP.get(r.SUB_EVENT_TYPE, (None, "none", None, "unmapped"))
        rows.append(dict(source="ACLED", category=r.SUB_EVENT_TYPE, unit="events",
                         volume=float(r.n), rows=int(r.f), code=m[0], fit=m[1],
                         alt=m[2], note=m[3]))
    rows.append(dict(source="UCDP one-sided", category="one-sided violence, government actor",
                     unit="fatalities", volume=947331.0, rows=492, code=4, fit="narrower",
                     alt=None, note="Only lethal state violence. Detention, torture and "
                     "property confiscation - most of what code 4 describes - are invisible."))
    rows.append(dict(source="UCDP one-sided", category="one-sided violence, non-government actor",
                     unit="fatalities", volume=315684.0, rows=916, code=5, fit="contested",
                     alt=1, note="Rebel groups killing civilians. Arguably part of armed conflict."))
    # ---- IOM DTM: reported reasons. Grouped by the code they feed, because the
    # value list is long and per-operation. Volumes are unknown until the first
    # live pull - these are seeded from values seen across operations.
    DTM = [
     (1, ["Conflict","Armed conflict","Conflict/Insecurity","Insecurity",
          "Military operations","Hostilities","War","Fear of conflict"]),
     (2, ["Communal violence","Communal tension","Social tension",
          "Intercommunal violence","Criminality","Gang violence","Banditry",
          "Civil unrest","Generalized violence"]),
     (3, ["Ethnic tension","Religious persecution","Persecution","Discrimination"]),
     (4, ["Human rights violations","Forced recruitment"]),
     (5, ["Violence","Threats","Personal security"]),
     (6, ["Natural disaster","Disaster","Flood","Floods","Flooding","Drought",
          "Earthquake","Cyclone","Storm","Landslide","Climate",
          "Climate/Environmental","Environmental","Climate shocks"]),
     (7, ["Eviction","Forced eviction","Development project","Land dispute",
          "Pollution"]),
    ]
    for code, vals in DTM:
        note = "Reported reason values seeded for this code: " + ", ".join(vals) + "."
        if code == 3:
            note += (" DTM rarely codes persecution separately - expect very few, and "
                     "expect operations to fold it into conflict.")
        if code == 7:
            note += (" The only source in the whole pipeline where eviction and "
                     "development displacement appear as a reason a person can give.")
        rows.append(dict(source="IOM DTM", category=f"reported reason \u2192 code {code}",
                         unit="reported reason", volume=0.0, rows=len(vals),
                         code=code, fit="pending", alt=None, note=note))
    rows.append(dict(source="IOM DTM",
                     category="not a valid cause of forced displacement",
                     unit="reported reason", volume=0.0, rows=7, code=None,
                     fit="none", alt=None,
                     note="Economic, Economic reasons, Livelihood, Lack of services, "
                     "Lack of livelihood, Voluntary, Family reunification, Other, "
                     "Unknown. Mapped to NOTHING by design - these are not valid causes "
                     "of forced displacement under IRIS. Kept and reported separately: "
                     "the share of respondents giving them is evidence about false "
                     "positives in the instrument."))

    # ---- V-Dem: conditions, not displacement
    VDEM = [
     (3, "v2clsocgrp", "Social group equality in respect for civil liberties"),
     (3, "v2clrelig",  "Freedom of religion"),
     (3, "v2pepwrsoc", "Power distributed by social group"),
     (4, "v2cltort",   "Freedom from torture"),
     (4, "v2clkill",   "Freedom from political killings"),
     (4, "v2xcl_prpty","Property rights index"),
    ]
    for code, var, lab in VDEM:
        rows.append(dict(source="V-Dem", category=f"{var} \u2014 {lab}",
                         unit="index (inverted)", volume=181.0, rows=36, code=code,
                         fit="narrower", alt=None,
                         note="Measures whether the CONDITION exists in a country, not "
                         "displacement caused by it - the same evidential class as an "
                         "event count. 181 countries, 1990-2025. Scale runs high = more "
                         "freedom, so it is inverted here."))

    rows.append(dict(source="UNHCR", category="asylum recognition rate by origin",
                     unit="proxy rate", volume=0.0, rows=149, code=3, fit="contested",
                     alt=None, note="The only signal for persecution anywhere in the four "
                     "sources, and it is confounded by destination-country asylum policy."))

    df = pd.DataFrame(rows)
    df.to_csv(f"{OUT}/crosswalk_categories.csv", index=False)

    # reverse view: what feeds each response option
    reverse = {}
    for c in CODES:
        feeds = df[df.code == c]
        reverse[c] = dict(
            label=CODES[c],
            n_categories=int(len(feeds)),
            sources=sorted(set(feeds.source)),
            contested=int((feeds.fit == "contested").sum()),
            people=float(feeds[(feeds.source == "IDMC GIDD")].volume.sum()),
            events=float(feeds[(feeds.source == "ACLED")].volume.sum()))

    payload = dict(rows=df.to_dict("records"), codes=CODES, reverse=reverse)
    html = TPL.replace("__DATA__", json.dumps(payload, separators=(",", ":")))
    open(f"{OUT}/idq_crosswalk_explorer.html", "w").write(html)
    print(f"wrote crosswalk explorer: {len(df)} source categories, "
          f"{int((df.fit=='contested').sum())} contested, "
          f"{int((df.code.isna()).sum())} deliberately unmapped")
    for c in CODES:
        r = reverse[c]
        print(f"  code {c}: {r['n_categories']:>2} categories from {r['sources'] or 'NOTHING'}")


TPL = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Crosswalk explorer — source categories to response options</title>
<style>
:root{color-scheme:light;--surface-1:#fcfcfb;--plane:#f9f9f7;--ink:#0b0b0b;--ink-2:#52514e;
 --muted:#898781;--grid:#e1e0d9;--bar:#9ec5f4;--bar2:#2a78d6;
 --good:#0ca30c;--warning:#fab219;--critical:#d03b3b;}
:root[data-theme="dark"]{color-scheme:dark;--surface-1:#1a1a19;--plane:#0d0d0d;--ink:#fff;
 --ink-2:#c3c2b7;--grid:#2c2c2a;--bar:#1c5cab;--bar2:#3987e5;}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;
 --surface-1:#1a1a19;--plane:#0d0d0d;--ink:#fff;--ink-2:#c3c2b7;--grid:#2c2c2a;
 --bar:#1c5cab;--bar2:#3987e5;}}
*{box-sizing:border-box}
body{margin:0;background:var(--plane);color:var(--ink);
 font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1280px;margin:0 auto;padding:26px 20px 60px}
h1{font-size:23px;margin:0 0 6px;letter-spacing:-.015em;font-weight:640}
h2{font-size:16.5px;margin:30px 0 6px;font-weight:620}
.sub{color:var(--ink-2);margin:0 0 16px;max-width:84ch;font-size:14.5px}
.card{background:var(--surface-1);border:1px solid var(--grid);border-radius:12px;
 padding:14px 16px;margin-top:10px}
.ctl{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 0;align-items:center}
button{font:inherit;font-size:13px;padding:6px 11px;border-radius:8px;border:1px solid var(--grid);
 background:var(--surface-1);color:var(--ink);cursor:pointer}
button.on{background:var(--ink);color:var(--surface-1);border-color:var(--ink)}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:7px 9px;border-bottom:1px solid var(--grid);vertical-align:top;text-align:left}
th{color:var(--ink-2);font-weight:600;font-size:11px;text-transform:uppercase;
 letter-spacing:.04em;cursor:pointer;white-space:nowrap}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.bar{height:7px;border-radius:3px;background:var(--bar);min-width:2px}
.tag{font-size:10px;font-weight:700;letter-spacing:.05em;padding:2px 6px;border-radius:4px;
 text-transform:uppercase;white-space:nowrap}
.t-exact{background:color-mix(in srgb,var(--good) 16%,transparent);color:var(--good)}
.t-contested{background:color-mix(in srgb,var(--warning) 28%,transparent);color:#8a5d00}
:root[data-theme="dark"] .t-contested{color:var(--warning)}
.t-broader,.t-narrower{background:color-mix(in srgb,var(--muted) 20%,transparent);color:var(--ink-2)}
.t-none{background:transparent;color:var(--muted);border:1px solid var(--grid)}
.t-decided{background:color-mix(in srgb,var(--good) 16%,transparent);color:var(--good)}
.t-pending{background:color-mix(in srgb,var(--critical) 15%,transparent);color:var(--critical)}
.note{font-size:12px;color:var(--ink-2);margin-top:3px;max-width:64ch;line-height:1.45}
.code{font-weight:620;white-space:nowrap}
.rev{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
@media(max-width:1000px){.rev{grid-template-columns:repeat(2,1fr)}}
.rc{background:var(--surface-1);border:1px solid var(--grid);border-radius:10px;padding:12px}
.rc.starved{border-color:var(--warning);border-width:1.5px}
.rc h3{font-size:13px;margin:0 0 4px;font-weight:620;line-height:1.35}
.rc .big{font-size:22px;font-weight:660;letter-spacing:-.02em}
.rc .l{font-size:11.5px;color:var(--ink-2)}
</style></head><body><div class="wrap">
<h1>Crosswalk explorer</h1>
<p class="sub">Every category each database actually uses, how much displacement or violence
sits in it, and which response option it feeds. Built from the source vocabularies upward
rather than from the questionnaire down, so force-fits and starved options both show.</p>

<h2>What feeds each response option</h2>
<div class="rev" id="rev"></div>

<h2>Every source category</h2>
<div class="ctl">
 <button class="f on" data-f="all">All</button>
 <button class="f" data-f="contested">Still contested</button>
 <button class="f" data-f="decided">Decisions taken</button>
 <button class="f" data-f="pending">Awaiting data</button>
 <button class="f" data-f="none">Deliberately unmapped</button>
 <button class="f" data-f="IDMC GIDD">IDMC</button>
 <button class="f" data-f="ACLED">ACLED</button>
 <button id="theme" style="margin-left:auto">Dark mode</button>
</div>
<div class="card"><table id="t"><thead><tr>
 <th data-s="source">Source</th><th data-s="category">Category</th>
 <th data-s="volume">Volume</th><th></th>
 <th data-s="code">Maps to</th><th data-s="fit">Fit</th></tr></thead><tbody></tbody></table></div>

<p class="note" style="max-width:92ch"><b>Fit.</b> <i>Exact</i> — the source category
denotes the same thing as the response option. <i>Broader / narrower</i> — it covers more or
less than the option. <i>Contested</i> — a defensible reading puts it under a different
option; the alternative is named in the note. <i>Decided</i> — a judgement call that was put to the team and settled; the note records
what was chosen and why. <i>Awaiting data</i> — cannot be resolved with the sources
currently in hand. <i>Unmapped</i> — deliberately feeds nothing.</p>
</div>
<script>
const D=__DATA__;
const fmt=n=>n>=1e6?(n/1e6).toFixed(1)+"m":n>=1e3?Math.round(n/1e3)+"k":String(Math.round(n));
let FILT="all", SORT="volume", DIR=-1;

const rev=document.getElementById('rev');
rev.innerHTML=Object.entries(D.reverse).map(([c,r])=>{
 const starved=r.n_categories===0;
 return `<div class="rc${starved?' starved':''}">
  <h3>${c}. ${r.label}</h3>
  <div class="big">${r.n_categories}</div>
  <div class="l">source categories feed this${r.contested?` · ${r.contested} contested`:''}</div>
  <div class="l" style="margin-top:6px">${starved
    ? '<b>Nothing in any database maps here.</b>'
    : (r.sources.join(", ")+(r.people?` · ${fmt(r.people)} people`:'')
       +(r.events?` · ${fmt(r.events)} events`:''))}</div></div>`;}).join('');

function render(){
 let rows=D.rows.slice();
 if(FILT==="contested")rows=rows.filter(r=>r.fit==="contested");
 else if(FILT==="none")rows=rows.filter(r=>r.code===null);
 else if(FILT==="decided")rows=rows.filter(r=>r.fit==="decided");
 else if(FILT==="pending")rows=rows.filter(r=>r.fit==="pending");
 else if(FILT!=="all")rows=rows.filter(r=>r.source===FILT);
 rows.sort((a,b)=>{const x=a[SORT],y=b[SORT];
  if(x===null)return 1; if(y===null)return -1;
  return (typeof x==="number"?x-y:String(x).localeCompare(String(y)))*DIR;});
 const mx={};rows.forEach(r=>{mx[r.unit]=Math.max(mx[r.unit]||0,r.volume);});
 document.querySelector('#t tbody').innerHTML=rows.map(r=>{
  const w=r.volume&&mx[r.unit]?Math.max(2,r.volume/mx[r.unit]*100):0;
  return `<tr><td style="color:var(--ink-2);white-space:nowrap">${r.source}</td>
   <td><b>${r.category}</b>${r.note?`<div class="note">${r.note}</div>`:''}</td>
   <td class="num">${r.volume?fmt(r.volume):'—'}<div class="l" style="font-size:10.5px;color:var(--muted)">${r.unit}</div></td>
   <td style="width:110px"><div class="bar" style="width:${w}%"></div></td>
   <td class="code">${r.code?`${r.code}. ${D.codes[r.code].slice(0,30)}`:'<span style="color:var(--muted)">—</span>'}
     ${r.alt?`<div class="note">or ${r.alt}. ${D.codes[r.alt].slice(0,30)}</div>`:''}</td>
   <td><span class="tag t-${r.fit}">${r.fit==="none"?"unmapped":r.fit}</span></td></tr>`;}).join('');
}
document.querySelectorAll('.f').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.f').forEach(x=>x.classList.remove('on'));
 b.classList.add('on');FILT=b.dataset.f;render();}));
document.querySelectorAll('th[data-s]').forEach(th=>th.addEventListener('click',()=>{
 const s=th.dataset.s; DIR=(SORT===s)?-DIR:-1; SORT=s; render();}));
document.getElementById('theme').addEventListener('click',()=>{
 const c=document.documentElement.getAttribute('data-theme');
 document.documentElement.setAttribute('data-theme',c==='dark'?'light':'dark');});
render();
</script></body></html>"""

if __name__ == "__main__":
    main()

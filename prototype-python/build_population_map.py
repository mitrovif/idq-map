"""
Population map: how many people, displaced by which cause, in each country.

Each country carries a pie sized by total displaced population and divided by
cause. Hovering names the actual events - IDMC records an event name and trigger
for every figure, so "armed conflict" becomes "Sudan: Armed clashes - Khartoum"
and "natural disaster" becomes "Typhoon Kristine".

Three populations, switchable, because they answer different questions:

  IDP STOCK    people currently displaced inside the country. What a household
               survey in that country would actually encounter.
  NEW 2025     displacements recorded during the year. Shows what is happening
               now rather than what has accumulated.
  REFUGEES     refugees and asylum seekers HOSTED, attributed to the cause mix of
               their origin countries. This is the one that matters for showcard
               design in host countries - the causing events happened elsewhere.
"""
from paths import ROOT_S, RAW_S, UP_S, TIDY_S, OUT_S, TOPO_S
import json, os, re
import pandas as pd

OUT = OUT_S
TIDY = TIDY_S
UP = UP_S
TOPO = TOPO_S

from build_dashboard import decode_topology
from build_allcauses import centroid
from qualitative_data import Q

# Order matters: it is the slice order in every pie and the legend order.
# 0 is not a response option - it is IDMC conflict displacement that nobody
# classified, carried as its own band so shares stay honest.
CAUSES = [1, 2, 6, 7, 0, 9]
LABEL = {1: "Armed conflict or war",
         2: "Widespread violence / public order",
         6: "Natural disasters",
         7: "Man-made events (incl. wildfire)",
         0: "Unattributed \u2014 conflict, type not recorded",
         9: "Cause not established \u2014 no source covers it"}


def clean_event(name, trigger, hazard, violence):
    """IDMC event names look like
       'Abyei Area: Communal violence - Abyei Area - 07/04/2025'.
       Strip the trailing location/date repetition, keep the substance."""
    s = str(name or "").strip()
    s = re.sub(r"\s*-\s*\d{2}/\d{2}/\d{4}\s*$", "", s)
    parts = [p.strip() for p in s.split(" - ") if p.strip()]
    if len(parts) > 1 and parts[-1].lower() in parts[0].lower():
        parts = parts[:-1]
    s = " - ".join(parts)
    detail = hazard if pd.notna(hazard) else (violence if pd.notna(violence) else None)
    if detail and str(detail).lower() not in s.lower():
        s = f"{s} ({detail})"
    return s[:110]


def main():
    profiles = json.load(open(f"{OUT}/profiles.json"))
    regions = {r["iso_code"]: r for r in json.load(open(f"{TIDY}/regions.json"))}
    feats = [f for f in decode_topology(json.load(open(TOPO)))
             if f["name"] != "Antarctica"]
    for f in feats:
        f["c"] = centroid(f["polys"])

    # re-read the source so we keep Event name / trigger, which the tidy
    # extract dropped
    src = pd.read_excel(
        f"{UP}/5140e1e8-IDMC_GIDD_Internal_Displacement_Disaggregated.xlsx",
        sheet_name="1_Disaggregated_Data")
    src = src.rename(columns={
        "ISO3": "iso3", "Country": "country", "Figure cause": "cause",
        "Figure category": "category", "Total figures": "figures",
        "Hazard sub type": "hazard_sub_type", "Violence type": "violence_type",
        "Event name": "event_name", "Event main trigger": "trigger"})
    vmap = {"International armed conflict (IAC)": 1,
            "Non-International armed conflict (NIAC)": 1,
            "Other situations of violence (OSV)": 2, "Unclear/Unknown": 0}
    HUMAN = {"Wildfire", "Dam release flood", "Sinkhole"}
    src["code_id"] = src.apply(
        lambda r: (7 if r["hazard_sub_type"] in HUMAN else 6)
        if r["cause"] == "Disaster"
        else (vmap.get(r["violence_type"], 1) if r["cause"] == "Conflict"
              else (7 if r["cause"] in ("Other", "Development") else None)), axis=1)
    src = src[src.code_id.notna()].copy()
    src["code_id"] = src.code_id.astype(int)

    flow = src[src.category == "Internal Displacements"]
    stock = src[src.category == "IDPs"]

    def pivot_flow(d):
        """Flows accumulate: sum across every year in the file."""
        g = d.groupby(["iso3", "code_id"])["figures"].sum()
        out = {}
        for (iso, c), v in g.items():
            if v > 0:
                out.setdefault(iso, {})[str(int(c))] = float(v)
        return out

    def pivot_stock(d):
        """Stocks are a snapshot, not a total. Take each country's latest year."""
        if d.empty:
            return {}
        latest_yr = d.groupby("iso3")["Year"].max().rename("ymax")
        d = d.join(latest_yr, on="iso3")
        d = d[d["Year"] == d["ymax"]]
        g = d.groupby(["iso3", "code_id"])["figures"].sum()
        out = {}
        for (iso, c), v in g.items():
            if v > 0:
                out.setdefault(iso, {})[str(int(c))] = float(v)
        return out

    flow_by, stock_by = pivot_flow(flow), pivot_stock(stock)
    yrs = sorted(int(y) for y in src["Year"].dropna().unique())
    period = f"{yrs[0]}\u2013{yrs[-1]}" if len(yrs) > 1 else str(yrs[0])
    print(f"  IDMC file covers {period}")

    # named events, biggest first - this is the "describe the conflict" part
    ev = (flow.assign(lab=lambda d: [clean_event(n, t, h, v) for n, t, h, v in
                                     zip(d.event_name, d.trigger,
                                         d.hazard_sub_type, d.violence_type)])
          .groupby(["iso3", "code_id", "lab"])["figures"].sum().reset_index())
    events = {}
    for (iso, c), grp in ev.groupby(["iso3", "code_id"]):
        top = grp.sort_values("figures", ascending=False).head(4)
        events.setdefault(iso, {})[str(int(c))] = [
            dict(l=r.lab, n=int(r.figures)) for r in top.itertuples() if r.figures > 0]

    # refugees hosted, attributed to the cause mix of their ORIGIN countries
    pop = pd.read_parquet(f"{TIDY}/unhcr_population.parquet")
    latest = int(pop.year.max())
    lp = pop[pop.year == latest].copy()
    lp["n"] = lp.refugees.fillna(0) + lp.asylum_seekers.fillna(0)
    lp = lp[(lp.n > 0) & (lp.coo_iso != lp.coa_iso)]
    # origin cause mix from IDMC stock, falling back to flows
    mix = {}
    for iso in set(list(stock_by) + list(flow_by)):
        d = stock_by.get(iso) or flow_by.get(iso) or {}
        tot = sum(d.values())
        if tot > 0:
            mix[iso] = {k: v / tot for k, v in d.items()}
    ref_by, ref_origins, ref_totals = {}, {}, {}
    for coa, grp in lp.groupby("coa_iso"):
        acc, org = {}, []
        ref_totals[coa] = float(grp.n.sum())
        for r in grp.itertuples():
            org.append((r.coo_name, r.coo_iso, float(r.n)))
            m = mix.get(r.coo_iso)
            if m:
                for c, s in m.items():
                    acc[c] = acc.get(c, 0) + float(r.n) * s
        # UNHCR's total is the denominator; whatever the origin cause mixes could
        # not account for becomes an explicit remainder rather than vanishing.
        attributed = sum(acc.values())
        remainder = max(0.0, ref_totals[coa] - attributed)
        if attributed >= 1 or remainder >= 1:
            d_ = {k: round(v) for k, v in acc.items() if v >= 1}
            if remainder >= 1:
                d_["9"] = round(remainder)
            ref_by[coa] = d_
        org.sort(key=lambda x: -x[2])
        org = [o for o in org if str(o[0]).strip().lower() not in
               ("unknown", "various", "stateless")] or org
        ref_origins[coa] = [dict(name=o[0], iso3=o[1], n=int(o[2])) for o in org[:5]]

    ucdp = json.load(open(f"{TIDY}/ucdp_attribution.json"))
    disasters = json.load(open(f"{TIDY}/disaster_register.json"))
    gedc = json.load(open(f"{TIDY}/ged_conflicts.json"))
    geda1 = json.load(open(f"{TIDY}/ged_admin1.json"))
    points = json.load(open(f"{TIDY}/idmc_points.json"))

    import pyreadr
    long_idmc = list(pyreadr.read_r(
        f"{RAW_S}/PopulationStatistics_idmc.rda").values())[0]
    long_idmc = long_idmc[long_idmc.total > 0]
    series, peak = {}, {}
    for iso, grp in long_idmc.groupby("coa_iso"):
        g = grp.groupby("year")["total"].sum().sort_index()
        diffs = g.diff()
        cumulative = float(g.iloc[0]) + float(diffs[diffs > 0].sum())
        series[iso] = {str(int(y)): int(v) for y, v in g.items()}
        peak[iso] = dict(n=int(round(cumulative)),
                         cumulative=int(round(cumulative)),
                         peak=int(g.max()), peak_year=int(g.idxmax()),
                         first_year=int(g.index[0]), opening=int(g.iloc[0]),
                         latest=int(g.iloc[-1]), latest_year=int(g.index[-1]))

    # coverage accounting - the headline honesty number
    ref_tot = sum(ref_totals.values())
    ref_unattr = sum(v.get("9", 0) for v in ref_by.values())
    idp_tot = sum(sum(v.values()) for v in stock_by.values())
    idp_unattr = sum(v.get("0", 0) for v in stock_by.values())
    cov = dict(
        refugee_total=ref_tot, refugee_unattributed=ref_unattr,
        idp_total=idp_tot, idp_unattributed=idp_unattr,
        attributable=(ref_tot - ref_unattr + idp_tot - idp_unattr) /
                     max(ref_tot + idp_tot, 1))
    print(f"  benchmark coverage: refugees {ref_tot:,.0f} ({ref_unattr/max(ref_tot,1):.0%} "
          f"unattributable), IDPs {idp_tot:,.0f} ({idp_unattr/max(idp_tot,1):.0%} "
          f"unattributed) \u2192 {cov['attributable']:.0%} of all displaced people "
          f"have a cause")

    data = {}
    for iso, v in profiles.items():
        data[iso] = dict(
            name=v["name"], region=(regions.get(iso) or {}).get("unhcr_region"),
            stock=stock_by.get(iso, {}), flow=flow_by.get(iso, {}),
            refugees=ref_by.get(iso, {}), events=events.get(iso, {}),
            origins=ref_origins.get(iso, []),
            series=series.get(iso, {}), peak=peak.get(iso),
            attr=ucdp["attribution"].get(iso))
    # countries with map geometry but no profile still need refugee data
    for iso, r in ref_by.items():
        if iso not in data:
            data[iso] = dict(name=iso, region=(regions.get(iso) or {}).get("unhcr_region"),
                             stock={}, flow={}, refugees=r, events={},
                             origins=ref_origins.get(iso, []),
                             series=series.get(iso, {}), peak=peak.get(iso))

    qual = {iso: {str(c): dict(status=d["status"], scale=d["scale"],
                               summary=d["summary"], quote=d["quote"],
                               example=d["example"],
                               sources=[dict(l=x[0], u=x[1]) for x in d["sources"]])
                  for c, d in codes.items()}
            for iso, codes in Q.items()}
    # origin -> asylum movements, coloured by what caused displacement in the origin
    dom_of = {}
    for iso, m in mix.items():
        if m:
            dom_of[iso] = int(max(m, key=m.get))
    flows = []
    for r in lp.itertuples():
        if r.n >= 25000 and r.coo_iso and r.coa_iso:
            flows.append(dict(o=r.coo_iso, a=r.coa_iso, n=int(r.n),
                              on=r.coo_name, an=r.coa_name,
                              code=dom_of.get(r.coo_iso)))
    flows.sort(key=lambda x: -x["n"])
    flows = flows[:160]
    print(f"  {len(flows)} refugee movements over 25,000 people")

    vdem = json.load(open(f"{TIDY}/vdem_severity.json"))
    # question_i18n's per-language form text (T/LANGS) used to be embedded here
    # for the map's own inline question-form renderer. That renderer now just
    # links out to questions.html (see build_population_map's showProfile JS),
    # which already carries this translation data itself -- no need to embed
    # it twice, so it's no longer read or passed into this page's template.
    try:
        lq = json.load(open(f"{TIDY}/localised_questions.json"))
        print(f"  localised questions: {len(lq)} countries")
    except FileNotFoundError:
        lq = {}
    # International protection / registration question. `prot` is just the
    # covered ISO3 list (kept for the country panel's summary line); `protmap`
    # is protection.py's own map_payload() - office/doc/ask per country, built
    # specifically "for the existing world map, in the shape draw() expects"
    # (see that function's docstring). This is what lets the map colour the
    # land itself by registrar, document stage or wording status, as an
    # additional view alongside population and events - not a second page.
    try:
        from protection import load as _load_protection, map_payload as _protection_map_payload, REGISTRAR_LABEL as _REG_LABEL
        prot = sorted(_load_protection().keys())
        protmap = _protection_map_payload()
        print(f"  protection question: {len(prot)} countries, map layer ready")
    except Exception as e:
        prot, protmap, _REG_LABEL = [], {}, {}
        print(f"  protection question: unavailable ({e})")
    # IOM DTM: the only evidence here that comes from displaced people rather
    # than from an analyst reading an event. Kept in its own key and never
    # merged with the attributed causes - it is a check on them, not a part.
    dtm = {}
    try:
        dd = pd.read_parquet(f"{TIDY}/dtm_reported.parquet")
        cmpf = f"{OUT}/dtm_reported_vs_attributed.csv"
        verdict = {}
        if os.path.exists(cmpf):
            cv = pd.read_csv(cmpf)
            verdict = {r.iso3: str(r.disagreement) for r in cv.itertuples()
                       if isinstance(getattr(r, "iso3", None), str)}
        for iso, g in dd.groupby("iso3"):
            rec = {"total": float(g.people.sum()), "by": {}, "econ": 0.0,
                   "composite": bool(g.composite.any()),
                   "verdict": verdict.get(iso)}
            for r in g.itertuples():
                if pd.isna(r.code_id):
                    rec["econ"] += float(r.people)
                else:
                    rec["by"][str(int(r.code_id))] = float(r.people)
            dtm[iso] = rec
        print(f"  DTM reported reasons: {len(dtm)} countries")
    except FileNotFoundError:
        print("  DTM reported reasons: not present - run build_dtm.py")
    # The showcard recommendation IS the question the paper asks - which options
    # belong in front of a respondent here, and what worked examples go with them.
    # It was being written to CSV and never shown, so the dashboard answered
    # everything except the thing someone actually opens it for.
    PUBLIC = os.environ.get("IDQ_PUBLIC") == "1"
    sc = {}
    try:
        s = pd.read_csv(f"{OUT}/showcard_recommendations.csv")
        for iso, g in s.groupby("iso3"):
            if len(str(iso)) != 3:
                continue
            rows = []
            for r in g.sort_values("code_id").itertuples():
                why = "" if pd.isna(r.rationale) else str(r.rationale)
                if PUBLIC:
                    # the rationale strings carry ACLED counts too, e.g.
                    # "4,457 ACLED events 2018+ (92% of ...)" - same licence
                    # question as the events layer, so out they go with it
                    kept = [x for x in why.split(" | ") if "ACLED" not in x]
                    if not kept and why:
                        # the recommendation stands - it was computed on the full
                        # data - but its only supporting reason was an ACLED count.
                        # Say that, rather than leaving a bare status with no
                        # justification, which reads as a bug.
                        why = ("Supported by ACLED political-violence event counts, "
                               "which are not republished here — see the repository "
                               "to reproduce with ACLED included")
                    else:
                        why = " | ".join(kept)
                rows.append(dict(c=int(r.code_id), l=str(r.code_label),
                                 s=str(r.status), w=why,
                                 e=("" if pd.isna(r.local_examples)
                                    else str(r.local_examples))))
            sc[iso] = rows
        print(f"  showcards: {len(sc)} countries")
    except FileNotFoundError:
        print("  showcards: showcard_recommendations.csv missing")
    # The events layer answers a different question from everything above it:
    # not "how many people are displaced here" but "what happens here, how often".
    # A cause can be frequent and displace few (Mexico) or rare and displace
    # millions (one cyclone), and only the first tells you whether a respondent
    # needs the option to exist at all.
    # PUBLIC BUILD. ACLED's Content Usage Terms prohibit anything that "creates a
    # functional substitute" for their dataset, and say the reading is theirs to
    # make. Country x admin1 x cause event counts on a public page is close enough
    # to that line that it is not worth testing. UCDP GED is CC-BY-4.0 and carries
    # the events view on its own, so the public build simply drops the ACLED layer.
    try:
        ev = json.load(open(f"{TIDY}/events.json"))
        if PUBLIC:
            for v in ev.values():
                v["acled"] = {}; v["acled_deaths"] = {}
                v.pop("acled_years", None)
                for a in v.get("adm", []):
                    a["a"] = {}
            print("  PUBLIC BUILD - ACLED counts omitted (licence)")
        print(f"  events layer: {len(ev)} countries, "
              f"{sum(len(v['adm']) for v in ev.values())} admin1 areas")
    except FileNotFoundError:
        ev = {}
        print("  events layer: events.json missing - run build_events.py")
    payload = dict(data=data, geo=feats, causes=CAUSES, labels=LABEL, flows=flows,
                   coverage=cov, ev=ev, sc=sc, dtm=dtm, lq=lq, prot=prot,
                   protmap=protmap, reglabel=_REG_LABEL,
                   public=PUBLIC,
                   vdem=vdem, ucdp=ucdp, dis=disasters, gedc=gedc, geda1=geda1, pts=points,
                   year=latest, period=period, multiyear=len(yrs) > 1,
                   qual=qual,
                   qlabels={"3": "Discrimination or persecution",
                            "4": "Human rights violations by authorities",
                            "7": "Man-made events"})
    html = TPL.replace("__DATA__", json.dumps(payload, separators=(",", ":")))
    name = "idq_population_by_cause.html"
    open(f"{OUT}/{name}", "w").write(html)
    print(f"wrote population map "
          f"({os.path.getsize(f'{OUT}/{name}')/1e6:.1f} MB); "
          f"{len(data)} countries, {sum(len(x) for x in events.values())} event groups")


TPL = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Displaced population by cause</title>
<style>
:root{color-scheme:light;--surface-1:#fcfcfb;--plane:#f9f9f7;--ink:#0b0b0b;
 --ink-2:#52514e;--muted:#898781;--grid:#e1e0d9;
 --c1:#2a78d6;--c2:#e0a93b;--c6:#1baf7a;--unattr:#c9c7bf;--unknown:#e6e4dc;
 --land:#eceae4;
 /* codes-3/4 "documented evidence" indicator circles used to hardcode var(--c2),
    which silently recoloured them every time code 2's colour changed. Decoupled
    onto its own token. Validated (validate_palette.js, --pairs all) against
    --c1/--c2/--c6 and against --unattr, the only colour it is ever shown beside. */
 --evidence:#4a3aa7;
 /* Registration-wording view (protection.py's map_payload) — categorical trio
    reused from --c1/--c2/--c6 (already validated for CVD separation on this
    page), NONE/no-data treated as status/absence colours, not a 4th and 5th
    categorical peer. Doc-stage is a single-hue sequential ramp; ask/wording
    status uses the same good/warning/critical logic as everywhere else. */
 --reg-gov:#2a78d6;--reg-unhcr:#1baf7a;--reg-both:#e0a93b;--reg-none:#c9c7bf;
 --doc0:#e7e5dd;--doc1:#8fb3dd;--doc2:#1f4a80;
 --ask-ok:#0ca30c;--ask-reword:#e0a93b;--ask-no:#d03b3b;--pr-nodata:#e6e4dc;}
:root[data-theme="dark"]{color-scheme:dark;--surface-1:#1a1a19;--plane:#0d0d0d;
 --ink:#fff;--ink-2:#c3c2b7;--grid:#2c2c2a;--c1:#3987e5;--c2:#c98500;--c6:#199e70;
 --unattr:#5a5954;--land:#2a2a28;--evidence:#8b6fe0;
 --reg-gov:#3987e5;--reg-unhcr:#199e70;--reg-both:#c98500;--reg-none:#5a5954;
 --doc0:#2c2c2a;--doc1:#3d689e;--doc2:#8fbcf5;
 --ask-ok:#2fbf2f;--ask-reword:#e0a93b;--ask-no:#e05a5a;--pr-nodata:#3a3a37;}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;
 --surface-1:#1a1a19;--plane:#0d0d0d;--ink:#fff;--ink-2:#c3c2b7;--grid:#2c2c2a;
 --c1:#3987e5;--c2:#c98500;--c6:#199e70;--unattr:#5a5954;--unknown:#3a3a37;--evidence:#8b6fe0;
 --land:#2a2a28;
 --reg-gov:#3987e5;--reg-unhcr:#199e70;--reg-both:#c98500;--reg-none:#5a5954;
 --doc0:#2c2c2a;--doc1:#3d689e;--doc2:#8fbcf5;
 --ask-ok:#2fbf2f;--ask-reword:#e0a93b;--ask-no:#e05a5a;--pr-nodata:#3a3a37;}}
*{box-sizing:border-box}
body{margin:0;background:var(--plane);color:var(--ink);
 font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1400px;margin:0 auto;padding:26px 20px 60px}
h1{font-size:24px;margin:0 0 6px;letter-spacing:-.015em;font-weight:640}
h2{font-size:17px;margin:28px 0 4px;font-weight:620;letter-spacing:-.01em}
.sub{color:var(--ink-2);margin:0 0 16px;max-width:84ch;font-size:14.5px}
.card{background:var(--surface-1);border:1px solid var(--grid);border-radius:12px;
 padding:16px;margin-top:10px}
.ctl{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:14px 0 0}
.ctl[hidden]{display:none}
button,select{font:inherit;font-size:13.5px;padding:7px 12px;border-radius:8px;
 border:1px solid var(--grid);background:var(--surface-1);color:var(--ink);cursor:pointer}
button.on{background:var(--ink);color:var(--surface-1);border-color:var(--ink)}
button em{font-style:normal;display:block;font-size:10.5px;letter-spacing:.02em;
 color:var(--muted);font-weight:500;margin-top:1px}
button.on em{color:var(--surface-1);opacity:.72}
#intbanner{background:color-mix(in srgb,#fab219 13%,transparent);
 border:1px solid color-mix(in srgb,#fab219 42%,transparent);border-radius:9px;
 padding:9px 13px;margin:0 0 14px;gap:11px;flex-wrap:nowrap;align-items:flex-start}
#intbanner[hidden]{display:none}
.intbadge{font-size:9.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;
 padding:3px 7px;border-radius:4px;white-space:nowrap;margin-top:1px;
 background:color-mix(in srgb,#fab219 30%,transparent);color:#8a5d00}
:root[data-theme="dark"] .intbadge{color:#fab219}
.intmsg{font-size:12.5px;color:var(--ink-2);line-height:1.5}
@media(max-width:760px){#intbanner{flex-wrap:wrap}}
.viewsw{margin-bottom:2px;padding-bottom:12px;border-bottom:1px solid var(--grid)}
/* Marks "Registration wording" as a different item from the population/events
   pair before anyone clicks it, rather than reading as a third peer. */
.viewsep{width:1px;align-self:stretch;background:var(--grid);margin:2px 2px}
.viewsw button{font-size:14px;padding:8px 15px;font-weight:560}
.findwrap{position:relative;margin-left:auto}
#find{font:inherit;font-size:13.5px;padding:8px 13px;border-radius:8px;
 border:1px solid var(--grid);background:var(--surface-1);color:var(--ink);width:250px}
#find:focus{outline:2px solid var(--c1);outline-offset:-1px}
#findlist{position:absolute;z-index:12;top:calc(100% + 4px);right:0;width:290px;
 background:var(--surface-1);border:1px solid var(--grid);border-radius:9px;
 box-shadow:0 10px 30px rgba(0,0,0,.18);max-height:320px;overflow:auto;padding:4px}
#findlist div{padding:7px 10px;border-radius:6px;cursor:pointer;font-size:13.5px}
#findlist div:hover,#findlist div.sel{background:var(--plane)}
#findlist div span{color:var(--muted);font-size:11.5px;float:right}
@media(max-width:760px){.findwrap{margin-left:0;width:100%}#find{width:100%}
 #findlist{width:100%;left:0}}
.rec{display:grid;grid-template-columns:auto 1fr;gap:7px 12px;align-items:start}
.rec .st{font-size:9.5px;font-weight:700;letter-spacing:.05em;padding:3px 7px;
 border-radius:4px;text-transform:uppercase;white-space:nowrap;margin-top:2px}
.st-rec{background:color-mix(in srgb,#0ca30c 16%,transparent);color:#0ca30c}
.st-res{background:transparent;color:var(--muted);border:1px solid var(--grid)}
.st-un{background:color-mix(in srgb,#fab219 26%,transparent);color:#8a5d00}
:root[data-theme="dark"] .st-un{color:#fab219}
.st-low{background:transparent;color:var(--muted);border:1px dashed var(--grid)}
.rec .rl{font-weight:620;font-size:13px}
.rec .rw{font-size:12.5px;color:var(--ink-2)}
.rec .re{font-size:12.5px;margin-top:3px;padding:5px 9px;background:var(--plane);
 border-radius:6px;border:1px solid var(--grid)}
.gl{border-bottom:1.5px dotted var(--muted);cursor:help;position:relative}
.gl:hover,.gl:focus{border-bottom-color:var(--c1);outline:none}
.gl::after{content:attr(data-def);position:absolute;left:0;top:calc(100% + 7px);
 width:270px;background:var(--surface-1);color:var(--ink);border:1px solid var(--grid);
 border-radius:9px;padding:9px 11px;font-size:12.5px;line-height:1.45;font-weight:400;
 font-style:normal;box-shadow:0 8px 24px rgba(0,0,0,.17);opacity:0;visibility:hidden;
 transition:opacity .12s;z-index:14;pointer-events:none;text-transform:none;
 letter-spacing:normal}
.gl:hover::after,.gl:focus::after,.gl.open::after{opacity:1;visibility:visible}
/* A term near the right edge would push its definition off screen, so flip it
   to right-aligned. Set from JS because the term's position is only known
   after layout, and the text reflows. */
.gl.flip::after{left:auto;right:0}
/* On a phone there is no position that fits a 270px card next to a mid-line
   word, so stop trying: dock it to the bottom of the screen instead. */
@media(max-width:760px){
 .gl::after{position:fixed;left:12px;right:12px;bottom:14px;top:auto;width:auto;
  box-shadow:0 -6px 30px rgba(0,0,0,.22);font-size:14px;padding:13px 15px}
 .gl.flip::after{left:12px;right:12px}
}
.tblwrap{max-height:520px;overflow:hidden;padding:0}
.tblscroll{max-width:100%;max-height:520px;overflow:auto;-webkit-overflow-scrolling:touch}
.tblscroll table{min-width:640px}
.tblscroll th:first-child,.tblscroll td:first-child{position:sticky;left:0;
 background:var(--surface-1);z-index:1}
@media(max-width:760px){
 .wrap{padding-left:14px;padding-right:14px}
 h1{font-size:21px}
 .ctl{gap:6px}
 button,select{font-size:12.5px;padding:7px 10px}
 .viewsw button{font-size:13px;padding:8px 12px}
 .pgrid{grid-template-columns:1fr}
 .rec{grid-template-columns:1fr;gap:2px 0}
 .rec .st{justify-self:start;margin-bottom:2px}
}
.gdl{margin:8px 0 0;font-size:13px}
.gdl dt{font-weight:640;margin-top:9px}
.gdl dd{margin:2px 0 0;color:var(--ink-2);max-width:88ch}
/* The drafted question form itself renders only on questions.html now -- this
   panel used to build the whole form inline too (see the old .qform rules,
   removed here), which duplicated that page's exact fields and, being the
   older of the two copies, did it without the provenance table or translation
   caveats questions.html carries. This panel links out to it instead. */
a.viewform{font:inherit;font-size:13px;padding:8px 13px;border-radius:8px;
 border:1px solid var(--c1);background:var(--c1);color:#fff;text-decoration:none;
 display:inline-block;font-weight:600;margin-top:8px}
a.viewform:hover{opacity:.88}
.warn{margin-top:8px;padding:8px 11px;border-radius:7px;font-size:12.5px;
 background:color-mix(in srgb,#fab219 14%,transparent);
 border:1px solid color-mix(in srgb,#fab219 38%,transparent)}
.grp{font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);
 font-weight:640;min-width:172px}
@media(max-width:760px){.grp{min-width:0;width:100%}}
button.help{border-style:dashed;color:var(--ink-2)}
.viewctl{display:flex;gap:7px;align-items:center;margin-top:9px;opacity:.7}
.viewctl span{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);
 font-weight:640;margin-right:4px}
.viewctl button{font-size:12.5px;padding:5px 10px;color:var(--ink-2)}
.help-panel h3{font-size:14px;margin:14px 0 5px;font-weight:640}
.help-panel h3:first-child{margin-top:2px}
.ht{border-collapse:collapse;width:100%;font-size:12.5px;margin:4px 0 2px}
.ht th,.ht td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--grid);
 vertical-align:top}
.ht th{color:var(--muted);font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;
 font-weight:650}
.ht td.flip{color:var(--c2);font-weight:560}
.hn{font-size:12.5px;color:var(--ink-2);max-width:94ch;margin:5px 0 0;line-height:1.55}
.profile{margin-top:12px}
.profile h2{font-size:19px;margin:0;font-weight:660;letter-spacing:-.015em}
.profile .ph{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;
 border-bottom:1px solid var(--grid);padding-bottom:10px;margin-bottom:4px}
.profile .ph .tot{color:var(--ink-2);font-size:13.5px}
.profile .close{margin-left:auto;font-size:12.5px;padding:4px 10px}
.psec{padding:12px 0;border-bottom:1px solid var(--grid)}
.psec:last-child{border-bottom:0}
.psec h3{font-size:13px;margin:0 0 7px;font-weight:650;text-transform:uppercase;
 letter-spacing:.045em;color:var(--muted)}
.pt{border-collapse:collapse;width:100%;font-size:12.5px}
.pt th,.pt td{padding:5px 8px;border-bottom:1px solid var(--grid);text-align:left;
 vertical-align:top}
.pt td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.pt th{font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);
 font-weight:650}
.dot{width:9px;height:9px;border-radius:2px;display:inline-block;margin-right:5px;
 vertical-align:-1px}
.pgrid{display:grid;grid-template-columns:1fr 1fr;gap:22px}
@media(max-width:900px){.pgrid{grid-template-columns:1fr}}
path.flow{fill:none;stroke-linecap:round;opacity:.72;cursor:pointer;
 stroke-dasharray:5 7;animation:march 1.5s linear infinite}
path.flow:hover{opacity:1;stroke-width:4}
@keyframes march{to{stroke-dashoffset:-24}}
@media(prefers-reduced-motion:reduce){path.flow{animation:none;stroke-dasharray:none}}
.grp{font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);
 font-weight:640;min-width:170px}
@media(max-width:760px){.grp{min-width:0;width:100%}}
button.help{border-style:dashed;color:var(--ink-2)}
.viewctl{display:flex;gap:7px;align-items:center;margin-top:9px;opacity:.72}
.viewctl span{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);
 font-weight:640;margin-right:4px}
.viewctl button{font-size:12.5px;padding:5px 10px;color:var(--ink-2)}
.help-panel h3{font-size:14px;margin:14px 0 5px;font-weight:640;letter-spacing:-.005em}
.help-panel h3:first-child{margin-top:2px}
.ht{border-collapse:collapse;width:100%;font-size:12.5px;margin:4px 0 2px}
.ht th,.ht td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--grid);
 vertical-align:top}
.ht th{color:var(--muted);font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;
 font-weight:650}
.ht td.flip{color:var(--c2);font-weight:560}
.hn{font-size:12.5px;color:var(--ink-2);max-width:94ch;margin:5px 0 0;line-height:1.55}
.profile{margin-top:12px}
.profile h2{font-size:19px;margin:0;font-weight:660;letter-spacing:-.015em}
.profile .ph{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;
 border-bottom:1px solid var(--grid);padding-bottom:10px;margin-bottom:4px}
.profile .ph .tot{color:var(--ink-2);font-size:13.5px}
.profile .close{margin-left:auto;font-size:12.5px;padding:4px 10px}
.psec{padding:12px 0;border-bottom:1px solid var(--grid)}
.psec:last-child{border-bottom:0}
.psec h3{font-size:13px;margin:0 0 7px;font-weight:650;text-transform:uppercase;
 letter-spacing:.045em;color:var(--muted)}
.pt{border-collapse:collapse;width:100%;font-size:12.5px}
.pt th,.pt td{padding:5px 8px;border-bottom:1px solid var(--grid);text-align:left;
 vertical-align:top}
.pt td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.pt th{font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);
 font-weight:650}
.dot{width:9px;height:9px;border-radius:2px;display:inline-block;margin-right:5px;
 vertical-align:-1px}
.pgrid{display:grid;grid-template-columns:1fr 1fr;gap:22px}
@media(max-width:900px){.pgrid{grid-template-columns:1fr}}
svg{display:block;width:100%;height:auto}
path.land{fill:var(--land);stroke:var(--surface-1);stroke-width:.4}
.key{display:flex;gap:18px;flex-wrap:wrap;margin-top:14px;font-size:13px;color:var(--ink-2);
 align-items:center}
.key i{width:12px;height:12px;border-radius:3px;display:inline-block;margin-right:6px;
 vertical-align:-2px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:6px 9px;border-bottom:1px solid var(--grid);text-align:right}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}
th{color:var(--ink-2);font-weight:600;font-size:11.5px;text-transform:uppercase;
 letter-spacing:.04em}
td{font-variant-numeric:tabular-nums}
.note{font-size:12.5px;color:var(--ink-2);margin-top:16px;max-width:92ch}
#tt{position:fixed;pointer-events:none;background:var(--surface-1);color:var(--ink);
 border:1px solid var(--grid);border-radius:10px;padding:10px 12px;font-size:12.5px;
 opacity:0;transition:opacity .1s;box-shadow:0 8px 26px rgba(0,0,0,.17);z-index:9;
 max-width:330px;line-height:1.45}
#tt.wide{max-width:none;width:400px;max-height:76vh;overflow:auto;padding:0}
#tt.pinned{pointer-events:auto}
#tt .ev{color:var(--ink-2);font-size:11.5px;margin-top:2px}
#tt hr{border:0;border-top:1px solid var(--grid);margin:7px 0}
#tt .hd{padding:11px 13px 9px;border-bottom:1px solid var(--grid);position:sticky;top:0;
 background:var(--surface-1);display:flex;align-items:baseline;gap:8px}
#tt .hd b{font-size:14px;letter-spacing:-.01em}
#tt .hd .hint{margin-left:auto;font-size:10.5px;color:var(--muted);white-space:nowrap}
#tt .bd{padding:2px 13px 11px}
#tt .blk{padding:9px 0;border-bottom:1px solid var(--grid)}
#tt .blk:last-child{border-bottom:0}
#tt .ttl{display:flex;gap:7px;align-items:baseline;margin-bottom:4px}
#tt .cd{font-weight:640;font-size:12.5px;flex:1}
#tt .badge,.profile .badge{font-size:9.5px;font-weight:700;letter-spacing:.05em;padding:2px 6px;
 border-radius:4px;text-transform:uppercase;white-space:nowrap}
#tt .b-doc,.profile .b-doc{background:color-mix(in srgb,#0ca30c 16%,transparent);color:#0ca30c}
#tt .b-abuse,.profile .b-abuse{background:color-mix(in srgb,#fab219 26%,transparent);color:#8a5d00}
:root[data-theme="dark"] #tt .b-abuse,.profile .b-abuse{color:#fab219}
#tt .b-none,.profile .b-none{background:transparent;color:var(--muted);border:1px solid var(--grid)}
#tt .scale{font-weight:660}
#tt .qt{margin:6px 0 0;padding:6px 9px;border-left:2.5px solid var(--c1);
 background:var(--plane);border-radius:0 6px 6px 0;font-style:italic}
#tt .ex,.profile .ex{margin-top:6px;padding:6px 9px;background:var(--plane);border-radius:6px;
 border:1px solid var(--grid)}
#tt .ex b,.profile .ex b{font-size:10px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);
 display:block;margin-bottom:2px;font-weight:650}
#tt .src,.profile .src{margin-top:5px;font-size:11.5px;color:var(--muted)}
#tt .src a,.profile .src a{color:var(--c1);text-decoration:none}
#tt .src a:hover,.profile .src a:hover{text-decoration:underline}
circle.ring{fill:none;stroke:var(--ink-2);stroke-width:1.3;stroke-dasharray:2.5 2.5}
</style>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
/* ---------------------------------------------------- EGRISS visual identity
   Additive on top of the rules above rather than rewritten in place, so this
   page's own colour logic (COL/SWATCH/ECOL/ESWATCH, --evidence) stays the
   single source of truth and this block only ever touches chrome: type,
   surfaces, and the four button families. */
:root{--egriss-navy:#14234c;--egriss-blue:#3b71b9;--egriss-teal:#4cc3c9;
 --egriss-tint:#eef3fa;--egriss-tint-2:#dde8f5;--egriss-line:#d9e2ef;}
body{background:#f7fafd}
.wrap{font-family:'IBM Plex Sans',system-ui,sans-serif}
h1{font-family:'Figtree',system-ui,sans-serif;color:var(--egriss-navy);font-weight:700}
.card{background:#fff;border-color:var(--egriss-line)}
#map{background:var(--egriss-tint);border-radius:14px}
path.land{fill:var(--egriss-tint-2) !important;stroke:#fff !important;stroke-width:.7 !important}
circle.ring{stroke:#5a6884 !important}
#find{border-color:var(--egriss-line)}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]) body{background:var(--plane)}
 :root:not([data-theme="light"]) h1{color:#fff}
 :root:not([data-theme="light"]) .card{background:var(--surface-1);border-color:var(--grid)}
 :root:not([data-theme="light"]) #map{background:var(--plane)}
 :root:not([data-theme="light"]) path.land{fill:var(--land) !important;stroke:var(--surface-1) !important}}
:root[data-theme="dark"] body{background:var(--plane)}
:root[data-theme="dark"] h1{color:#fff}
:root[data-theme="dark"] .card{background:var(--surface-1);border-color:var(--grid)}
:root[data-theme="dark"] #map{background:var(--plane)}
:root[data-theme="dark"] path.land{fill:var(--land) !important;stroke:var(--surface-1) !important}

/* Registration-wording choropleth. #map gives these enough specificity to beat
   the theme-wide path.land !important rules above in every theme state. */
#map path.land.pr-reg-GOVERNMENT{fill:var(--reg-gov) !important}
#map path.land.pr-reg-UNHCR{fill:var(--reg-unhcr) !important}
#map path.land.pr-reg-BOTH{fill:var(--reg-both) !important}
#map path.land.pr-reg-NONE{fill:var(--reg-none) !important}
#map path.land.pr-doc-0{fill:var(--doc0) !important}
#map path.land.pr-doc-1{fill:var(--doc1) !important}
#map path.land.pr-doc-2{fill:var(--doc2) !important}
#map path.land.pr-ask-ok{fill:var(--ask-ok) !important}
#map path.land.pr-ask-reword{fill:var(--ask-reword) !important}
#map path.land.pr-ask-no{fill:var(--ask-no) !important}
#map path.land.pr-nodata{fill:var(--pr-nodata) !important}
#map.pr-mode path.land{cursor:pointer}
.ctl .players{border-radius:20px}
.ctl .players.on{background:var(--egriss-navy) !important;
 border-color:var(--egriss-navy) !important;color:#fff !important}
.ctl .players:not(.on):hover{background:var(--egriss-tint-2);color:var(--egriss-navy)}

/* 1. PRIMARY -- the People displaced / Events switch. Everything else on the
   panel depends on this choice, so it gets the heaviest weight: solid navy
   pill, filled track. */
.viewsw button.view{border-radius:999px;font-weight:600}
.viewsw button.view.on{background:var(--egriss-navy) !important;
 border-color:var(--egriss-navy) !important;color:#fff !important}
.viewsw button.view:not(.on):hover{background:var(--egriss-tint-2);color:var(--egriss-navy)}

/* 2. SECONDARY -- mode / level / source. Refines the primary view, so it reads
   lighter: outlined track, teal tint (not a solid fill) marks the active
   choice. Disabled options (the ACLED layer in the public build) stay visibly
   inert rather than looking like just another unselected button. */
#popctl button.mode,#evctl button.lvl,#evctl button.esrc{
 background:#fff;border-color:var(--egriss-line)}
#popctl button.mode.on,#evctl button.lvl.on,#evctl button.esrc.on{
 background:color-mix(in srgb,var(--egriss-teal) 18%,transparent) !important;
 border-color:var(--egriss-teal) !important;color:var(--egriss-navy) !important;
 font-weight:600}
#popctl button.mode:not(.on):hover,#evctl button.lvl:not(.on):hover,
#evctl button.esrc:not(.on):hover{background:var(--egriss-tint)}
#evctl button.esrc[disabled]{opacity:.45;cursor:not-allowed}

/* 3. FILTER CHIPS -- which cause. A different interaction (choosing a
   category, not switching a mode), so it gets a different shape: rounded
   outline chips. Teal fill marks an active single cause; navy fill is
   reserved for "All causes" as the reset action. */
button.cz{border-radius:999px;background:#fff;border-color:var(--egriss-line)}
button.cz.on{background:var(--egriss-teal) !important;
 border-color:var(--egriss-teal) !important;color:var(--egriss-navy) !important;
 font-weight:600}
button.cz[data-c="all"].on{background:var(--egriss-navy) !important;
 border-color:var(--egriss-navy) !important;color:#fff !important}
button.cz:not(.on):hover{border-color:var(--egriss-blue);color:var(--egriss-blue)}

/* 4. GHOST / META links -- "how to read this" and similar. Not data controls,
   so they shouldn't compete visually with the three families above: no box,
   a hairline top rule, teal underline on hover only. */
.viewctl button,button.help{background:none;border:0;border-radius:0;
 padding:2px 0 2px 10px;border-left:1px solid var(--grid)}
.viewctl button:first-child,button.help:first-child{border-left:0;padding-left:0}
.viewctl button:hover,button.help:hover{color:var(--egriss-navy)}
</style></head><body><div class="wrap">

<h1 id="title">Displaced population by cause</h1>
<p class="sub" id="lede">One circle per country, sized by how many people are displaced and divided by
what displaced them. Hover a country to see the numbers and the actual events IDMC
recorded — the named storm, the named conflict. Scroll to zoom, drag to pan.</p>

<div class="ctl" id="intbanner" hidden>
  <span class="intbadge">Pending ACLED endorsement</span>
  <span class="intmsg">This build includes ACLED event counts ahead of ACLED's formal
  endorsement to be credited as a data source. Treat the ACLED layer as
  <b>provisional</b> until that is confirmed — the rest of the page is unaffected.</span>
</div>

<div class="ctl viewsw">
  <span class="grp">What the map shows</span>
  <button class="view on" data-v="pop">People displaced</button>
  <button class="view" data-v="events">Events that happened</button>
  <span class="viewsep" aria-hidden="true"></span>
  <button class="view" data-v="prot">Registration wording<em>a different question</em></button>
  <span class="findwrap">
    <input id="find" type="search" autocomplete="off" spellcheck="false"
           placeholder="Find a country &mdash; e.g. Chad" aria-label="Find a country">
    <div id="findlist" hidden></div>
  </span>
</div>

<div class="ctl" id="evctl" hidden>
  <span class="grp">Level and source</span>
  <button class="lvl on" data-l="country">Countries</button>
  <button class="lvl" data-l="adm1">Subnational areas</button>
  <span style="width:14px"></span>
  <button class="esrc on" data-s="ucdp">Deadly incidents <em>worldwide</em></button>
  <button class="esrc" data-s="acled">All violent events <em id="acledn">&mdash;</em></button>
</div>

<div class="ctl" id="protctl" hidden>
  <span class="grp">Colour by</span>
  <button class="players on" data-pl="reg">Who registers claims</button>
  <button class="players" data-pl="doc">Document stages nameable</button>
  <button class="players" data-pl="ask">Does the office wording work?</button>
</div>

<div class="ctl" id="popctl">
  <span class="grp">Which displaced population</span>
  <button class="mode on" data-m="both">Everyone displaced now <em>snapshot</em></button>
  <button class="mode" data-m="stock">IDPs only <em>snapshot</em></button>
  <button class="mode" data-m="refugees">Refugees only <em>snapshot</em></button>
  <button class="mode" data-m="flow" id="flowbtn">Displacements recorded <em>running total &mdash; repeats counted</em></button>
  <button class="mode" data-m="period">Worst year on record <em>conflict only, 1990&ndash;2025</em></button>
  <button class="mode" data-m="flows">Movements between countries <em>arrows</em></button>
  <button class="mode" data-m="sub">Where within countries <em>towns and districts</em></button>
</div>
<div class="ctl" id="causectl">
  <span class="grp">Which cause</span>
  <button class="cz on" data-c="all">All causes</button>
  <button class="cz" data-c="1">1. Armed conflict</button>
  <button class="cz" data-c="2">2. Widespread violence</button>
  <button class="cz poponly" data-c="3">3. Persecution</button>
  <button class="cz" data-c="4">4. HR violations</button>
  <button class="cz evonly" data-c="5" hidden>5. Other threats of violence</button>
  <button class="cz" data-c="6">6. Natural disasters</button>
  <button class="cz" data-c="7">7. Man-made events</button>
</div>
<div class="ctl" id="basicctl">
  <button class="help" id="helpbtn">How to read this</button>
  <button class="help" id="srcbtn">Where these numbers come from</button>
  <button class="help" id="glossbtn">Plain English</button>
  <button class="help" id="advbtn">More options</button>
</div>
<div class="ctl" id="layerctl" hidden>
  <span class="grp">More options</span>
  <button id="evid">Documented evidence for codes 3, 4 and 7</button>
  <button id="attr">Attribute unknowns via UCDP</button>
</div>

<div class="card help-panel" id="glosspanel" hidden></div>

<div class="card help-panel" id="srcpanel" hidden>
 <h3>Where these numbers come from</h3>
 <p class="hn">Nobody measures "why did you leave home" directly at scale. Every figure
 here is assembled from organisations that count something adjacent, and the join between
 what they count and the eight response options is the thing this project had to build.
 That join is a judgement, not a fact, and it is written down in
 <code>config/crosswalk.yaml</code> so you can disagree with it.</p>
 <table class="ht"><thead><tr><th>Who</th><th>What they actually count</th>
  <th>Which options that can speak to</th></tr></thead><tbody>
 <tr><td><b>IDMC</b><div class="ev">Internal Displacement Monitoring Centre</div></td>
  <td><b>People.</b> How many were displaced inside their own country, and what the
      agency recorded as the trigger — a named storm, a named armed conflict.</td>
  <td>1, 2, 6, 7 — the entire population half of this dashboard</td></tr>
 <tr><td><b>UNHCR</b></td>
  <td><b>People.</b> Refugees and asylum seekers, by country of origin and country of
      asylum, plus how often each nationality's claims are recognised.</td>
  <td>everything shown for refugees; recognition rates stand in for 3</td></tr>
 <tr><td><b>UCDP</b><div class="ev">Uppsala Conflict Data Program</div></td>
  <td><b>Incidents.</b> One record per event in which at least one person was killed in
      organised violence, placed on a map, from 1989, worldwide. No deaths, no record.</td>
  <td>1, 2, 4, 5 — the events half</td></tr>
 <tr><td><b>ACLED</b></td>
  <td><b>Incidents.</b> Political violence and protest, whether or not anyone died — so
      several times more events than UCDP for the same conflicts. 68 countries.</td>
  <td>same options as UCDP, as an <b>alternative</b> reading, never added to it</td></tr>
 <tr><td><b>IOM DTM</b></td>
  <td><b>What displaced people say.</b> The only source here where the reason comes from
      the person rather than from an analyst.</td>
  <td>a reality check on all of the above</td></tr>
 <tr><td><b>V-Dem</b></td>
  <td><b>Conditions, not displacement.</b> Expert ratings of torture, political killing,
      religious freedom, discrimination by social group.</td>
  <td>3 and 4 — proof the cause exists here, not proof it moved anyone</td></tr>
 </tbody></table>
 <p class="hn"><b>The three things most likely to trip you up.</b>
 <b>One:</b> people and incidents are different units and are never added together —
 the two views exist precisely so they stay apart.
 <b>Two:</b> sources are not summed. IDMC derives its figures from IOM DTM in twelve
 countries, so treating them as independent agreement is circular; UCDP and ACLED code
 the same events. The only legitimate sum on this page is IDPs plus hosted refugees.
 <b>Three:</b> none of this is causation. "61% drought-attributed" describes
 co-occurrence in administrative statistics, not why any individual left.</p>
 <p class="hn"><b>What is missing, and it matters.</b> No database anywhere has a category
 for persecution or for state repression short of killing. A Rohingya family displaced by
 military persecution is recorded by IDMC as armed conflict. Across IDMC's own methodology
 notes, the words "persecution", "ethnic", "discrimination" and "torture" appear zero
 times. Options 3 and 7 look empty in the data because nobody counts them, not because
 they are rare — which is an argument for keeping them on the questionnaire, not for
 dropping them.</p>
</div>

<div class="card help-panel" id="help" hidden>
 <h3>The five views, and how they differ</h3>
 <table class="ht"><thead><tr><th>View</th><th>What it counts</th>
  <th>Where it is drawn</th><th>Period</th></tr></thead><tbody>
 <tr><td><b>People currently displaced (IDPs)</b></td>
  <td>A <b>stock</b> &mdash; people still displaced right now. A snapshot, so nobody is
      counted twice.</td><td>Country where the displacement happened</td><td>end-2025</td></tr>
 <tr><td><b>Total displacements recorded</b></td>
  <td>A <b>flow</b> &mdash; movements recorded during the period. Somebody displaced three
      times counts three times.</td><td>Country where the displacement happened</td>
  <td id="hp1">&mdash;</td></tr>
 <tr><td><b>Worst year on record</b></td>
  <td>Each country's <b>peak</b> displaced population in any single year, with the whole
      trajectory in the tooltip. Conflict only &mdash; no disaster split exists for this series.</td>
  <td>Country where the displacement happened</td><td>1990&ndash;2025</td></tr>
 <tr><td><b>Refugees hosted, by cause in origin</b></td>
  <td>People who <b>crossed an international border</b>, attributed to the cause mix of the
      country they came from.</td>
  <td class="flip">Country <b>hosting</b> them &mdash; not where events happened</td>
  <td>latest year</td></tr>
 <tr><td><b>Refugee movements between countries</b></td>
  <td>The same refugees, drawn as <b>movements</b> rather than totals. Each arrow runs from
      origin to host country, coloured by what caused the displacement.</td>
  <td class="flip">An arrow <b>from</b> origin <b>to</b> host</td><td>latest year</td></tr>
 </tbody></table>
 <p class="hn"><b>Watch the third column.</b> Three views put the circle where displacement was
 caused. The last two are about where displaced people went. Germany shows 2.8m not because
 anything happened in Germany, but because it hosts that many people displaced elsewhere. That
 is the view that matters for designing a showcard in a host country, precisely because the
 causing events happened somewhere else.</p>

 <h3>IDPs and refugees</h3>
 <p class="hn">An <b>IDP</b> was displaced inside their own country and never crossed an
 international border &mdash; still their own government's responsibility. A <b>refugee</b>
 crossed a border and is under international protection. The same event produces both; the only
 difference is whether the person crossed a line on a map. The first three views are about
 IDPs. The last two are about refugees. This distinction is the reason the identification
 questions ask about border crossing and time away at all &mdash; the reason for fleeing can
 be identical.</p>

 <h3>Why codes 3, 4 and 7 get their own layer</h3>
 <p class="hn">The response options in the identification question are numbered 1 to 8. Three
 of them &mdash; <b>3. discrimination or persecution</b>, <b>4. human rights violations by
 authorities</b>, <b>7. man-made events</b> &mdash; are counted by no displacement database
 anywhere. IDMC has no category for persecution: a Rohingya family displaced by military
 persecution is recorded as armed conflict. The layer adds documented evidence from human
 rights investigations for those three, across the twenty largest displacement contexts.
 Ringed countries have it &mdash; hover for the evidence, click to pin the sources.</p>
</div>

<div class="card">
  <div id="anchor" style="font-size:11.5px;color:var(--muted);margin:0 0 8px"></div>
  <div id="anchor" style="font-size:11.5px;color:var(--muted);margin:0 0 8px"></div>
  <svg id="map" viewBox="0 0 1000 500" role="img"
    aria-label="World map with per-country pie charts of displaced population by cause"></svg>
  <div class="key" id="key"></div>
</div>
<div class="card profile" id="profile" hidden></div>
<div class="viewctl">
  <span>Display</span>
  <button id="shape">Single bubbles</button>
  <button id="reset">Reset zoom</button>
  <button id="theme">Dark mode</button>
</div>
<p class="note" id="modenote"></p>

<h2>The twenty largest displaced populations</h2>
<div class="card tblwrap"><div class="tblscroll"><table id="tbl"></table></div></div>

<p class="note" id="caveats"><b>Caveats.</b> IDMC figures here cover 2025 only, so the stock reflects
people displaced and still displaced at end-2025, and long-settled protracted caseloads from
earlier decades are understated. The refugee view attributes each hosted refugee to the cause
mix of their origin country as a whole — it is a population-weighted estimate, not a count of
individually-attributed people, and it assumes refugees leave for the same reasons that
displace people internally in their country. Man-made events (code 7) is absent everywhere
because no agency counts development-induced displacement.</p>
</div><div id="tt"></div>
<script>
const D=__DATA__, C=D.causes, L=D.labels;
// Registration-wording view — protection.py's map_payload(), a different
// question item from the population/events data above. See PROT_LAYERS and
// drawProtection() further down for how it colours the map.
const MP=D.protmap||{}, REGLABEL=D.reglabel||{};
const COL={1:"var(--c1)",2:"var(--c2)",6:"var(--c6)",
           7:"url(#hatch)",            // no 4th hue clears CVD separation in both
           0:"var(--unattr)",           // modes, so texture and neutral instead
           9:"var(--unknown)"};
const SWATCH={1:"var(--c1)",2:"var(--c2)",6:"var(--c6)",
              7:"repeating-linear-gradient(45deg,var(--ink-2) 0 1.6px,transparent 1.6px 4px)",
              0:"var(--unattr)",9:"var(--unknown)"};
const W=1000,H=500,LAT0=84,LAT1=-58;
const px=l=>(l+180)/360*W, py=l=>(LAT0-l)/(LAT0-LAT1)*H;
const NS="http://www.w3.org/2000/svg";
const fmt=n=>n>=1e6?(n/1e6).toFixed(n<1e7?2:1)+"m":n>=1e3?Math.round(n/1e3)+"k":String(Math.round(n));
let MODE="both", SHAPE="pie", CAUSE="all", EVID=false, ATTR=false, PIN=null,
    Z=1,TX=0,TY=0, notes={};
// The events layer. VIEW is the top-level switch; the two views share the map,
// the zoom and the cause filter, and share nothing else.
let VIEW="pop", ELEVEL="country", ESRC="ucdp", PLAYER="reg";
const EC=[1,2,4,5,6,7];               // codes any event source actually carries
// Only three hues clear colour-vision deficiency against each other in both
// light and dark, and codes 1/2/6 already hold them. 4 and 5 get texture and
// neutral rather than a fourth and fifth hue that would separate for nobody.
// Solid, not a pattern: an SVG pattern is defined in user space, so at the radii
// a 3%-share cause produces at admin1 level it renders as one stray dot or as
// nothing at all. Dark and light neutral separate by lightness, which survives
// both dark mode and every form of colour-vision deficiency.
const ECOL=Object.assign({},COL,{4:"var(--ink-2)",5:"var(--unattr)"});
const ESWATCH=Object.assign({},SWATCH,{4:"var(--ink-2)",5:"var(--unattr)"});
const ELAB={1:"Armed conflict or war",2:"Widespread violence / public order",
  4:"HR violations by authorities (state one-sided)",
  5:"Other threats of violence (non-state one-sided)",
  6:"Natural disasters",7:"Man-made events (incl. wildfire)"};
const ESRCNAME={ucdp:"UCDP GED",acled:"ACLED"};
// Coverage counts were hardcoded and went stale the moment more ACLED regions
// were added. Derive them, so the label cannot disagree with the data again.
const NCOV=src=>Object.values(D.ev).filter(v=>Object.keys(v[src]||{}).length).length;
const NUCDP=NCOV("ucdp"), NACLED=NCOV("acled");
/* PLAIN ENGLISH. Every one of these is a term a displacement specialist uses
   without noticing and a non-specialist reads straight past while quietly losing
   the thread. Definitions are written for someone with no background, and are
   attached to the first occurrence of the term in any explanatory text on the
   page - including text that is regenerated whenever the view changes. */
const GLOSS=[
 ["IDPs","People displaced inside their own country who never crossed an international "+
  "border. Still their own government's responsibility in law."],
 ["IDP","See IDPs — someone displaced inside their own country."],
 ["internally displaced","Displaced inside your own country, without crossing a border."],
 ["refugees","People who crossed an international border to escape, and are under "+
  "international protection as a result. The only difference from an IDP is the border."],
 ["refugee","Someone who crossed an international border to escape and is under "+
  "international protection."],
 ["asylum seekers","People who have applied for refugee status and are waiting for a "+
  "decision. Counted here alongside refugees."],
 ["snapshot","A count of who is displaced right now. Nobody is counted twice, but it "+
  "misses everyone who was displaced earlier and has since gone home."],
 ["running total","Every displacement recorded over a period, added up. Someone "+
  "displaced three times counts three times — so it is bigger than the number of people."],
 ["stock","A count at one moment in time, rather than a total over a period."],
 ["unattributed","Displacement that a source recorded without saying what caused it. "+
  "Not an unknown number of people — a known number with an unknown reason."],
 ["origin-weighted","Refugees living in a country are described using the causes of "+
  "displacement in the country they came from, since that is where the events happened."],
 ["one-sided violence","Organised armed force used against civilians who are not "+
  "fighting back — by a government, or by an armed group."],
 ["response options","The list of answers a respondent chooses from. Here, the eight "+
  "reasons for having to leave home."],
 ["showcard","The card an enumerator shows a respondent listing the answer options, "+
  "with worked examples to help them recognise their own situation."],
 ["enumerator","The person who actually asks the questions in a survey."],
 ["subnational","Below the level of a whole country — a province, state or district."],
 ["admin1","The first level below a country: a province, state or region."],
 ["recognition rate","The share of asylum claims from a given nationality that are "+
  "accepted. Used here as indirect evidence that persecution is occurring."],
 ["preventive evacuation","People moved out of harm's way before a disaster hits. "+
  "Counted as displacement, though it may last only days."],
 ["incidents","Individual recorded events — one clash, one attack. Not people."],
 ["cognitive testing","Interviewing people about how they understand a question, to "+
  "find out whether it means to them what it means to you."],
];
const GKEY=GLOSS.map(g=>g[0]);
const GDEF=Object.fromEntries(GLOSS);
// longest first, so "asylum seekers" is not eaten by "seekers", etc.
const GRX=new RegExp("\\b("+GKEY.slice().sort((a,b)=>b.length-a.length)
  .map(t=>t.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")).join("|")+")\\b","i");

function glossify(root){
 if(!root)return;
 const used=new Set();
 const walk=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode(n){
   // never touch controls, links, code, or anything already annotated
   const p=n.parentElement;
   if(!p||p.closest('button,a,input,select,code,.gl,svg,table.pt,.rec'))
     return NodeFilter.FILTER_REJECT;
   return n.nodeValue.trim().length>2?NodeFilter.FILTER_ACCEPT:NodeFilter.FILTER_REJECT;}});
 const todo=[];
 while(walk.nextNode())todo.push(walk.currentNode);
 todo.forEach(n=>{
  let m=GRX.exec(n.nodeValue);
  if(!m)return;
  const key=GKEY.find(k=>k.toLowerCase()===m[1].toLowerCase());
  if(!key||used.has(key.toLowerCase()))return;
  used.add(key.toLowerCase());
  const after=n.splitText(m.index);
  after.nodeValue=after.nodeValue.slice(m[1].length);
  const sp=document.createElement('span');
  sp.className='gl'; sp.tabIndex=0; sp.textContent=m[1];
  sp.dataset.def=GDEF[key];
  n.parentNode.insertBefore(sp,after);});}

function glossPanel(){
 return `<h3>Plain English</h3><p class="hn">Every term on this page that assumes you `+
  `already work with displacement data. Dotted words anywhere on the page explain `+
  `themselves — hover them, or tap on a phone.</p>`+
  `<dl class="gdl">`+GLOSS.filter((g,i)=>GLOSS.findIndex(x=>x[1]===g[1])===i)
   .map(([t,d])=>`<dt>${t}</dt><dd>${d}</dd>`).join("")+`</dl>`;}

// In the public build the ACLED layer is absent for licence reasons, so say that
// rather than leaving a button that silently empties the map.
// Two builds of this page exist and look identical. The one that carries ACLED
// counts says so, on screen, at the top - a misdirected upload is otherwise a
// very easy mistake to make with a 2.3 MB file whose only difference is licensing.
if(!D.public){document.getElementById('intbanner').hidden=false;}
if(D.public){
 const ab=document.querySelector('.esrc[data-s="acled"]');
 if(ab){ab.disabled=true;ab.style.opacity=".45";ab.style.cursor="not-allowed";
  ab.title="ACLED's terms restrict republishing their data, so this layer is not "+
   "in the shared build. It is available when you run the pipeline yourself.";
  ab.innerHTML='All violent events <em>not in shared build</em>';}}
// Codes 3 and 4 have no per-country displacement count anywhere. Selecting them
// switches the map to an evidence encoding rather than faking a magnitude.
const NO_COUNT = ["3","4"];
const QB={documented:["b-doc","Documented"],abuse_only:["b-abuse","Abuse only"],
          none_found:["b-none","None found"]};
// GED codes one-sided violence to 4 and 5, which are not countable causes and so
// are absent from LABEL. The profile still has to name them.
const ALLL=Object.assign({}, {3:"Discrimination or persecution",
  4:"HR violations by authorities", 5:"Other threats of violence",
  8:"A different threat"});
const lab=c=>L[c]||ALLL[c]||"—";
const colr=c=>((c===4||c===7)?'var(--ink-2)':(c===0||c===5||c===9)?'var(--unattr)':
  (COL[c]||'var(--unattr)'));

const map=document.getElementById('map');
map.insertAdjacentHTML("afterbegin",
 `<defs><pattern id="hatch" width="4" height="4" patternUnits="userSpaceOnUse"
   patternTransform="rotate(45)">
   <rect width="4" height="4" fill="var(--surface-1)"/>
   <line x1="0" y1="0" x2="0" y2="4" stroke="var(--ink-2)" stroke-width="1.7"/>
  </pattern>
  <pattern id="dots" width="3.5" height="3.5" patternUnits="userSpaceOnUse">
   <rect width="3.5" height="3.5" fill="var(--surface-1)"/>
   <circle cx="1.2" cy="1.2" r="1" fill="var(--ink-2)"/>
  </pattern></defs>`);
const root=document.createElementNS(NS,"g"); map.appendChild(root);
const LANDS=[];
D.geo.forEach(f=>{const p=document.createElementNS(NS,"path");
 let s="";for(const poly of f.polys)for(const ring of poly){
  let seg=[],segs=[];
  for(let i=0;i<ring.length;i++){
   if(i&&Math.abs(ring[i][0]-ring[i-1][0])>180){segs.push(seg);seg=[];}
   seg.push(ring[i]);}
  if(seg.length)segs.push(seg);
  for(const sg of segs){if(sg.length<2)continue;
   s+="M"+sg.map((p,i)=>(i?"L":"")+px(p[0]).toFixed(1)+","+py(p[1]).toFixed(1)).join("")+"Z";}}
 p.setAttribute("d",s);p.setAttribute("class","land");p.dataset.iso=f.iso3||"";
 root.appendChild(p);LANDS.push(p);});
const layer=document.createElementNS(NS,"g"); root.appendChild(layer);

const tt=document.getElementById('tt');
function place(e,wide){
 const w=wide?400:330, h=Math.min(tt.offsetHeight||240, innerHeight*0.76);
 let x=e.clientX+15, y=e.clientY+15;
 if(x+w>innerWidth-12) x=Math.max(12,e.clientX-w-15);
 if(y+h>innerHeight-12) y=Math.max(12,innerHeight-h-12);
 tt.style.left=x+"px"; tt.style.top=y+"px";}
function unpin(){ if(PIN){PIN=null;} tt.classList.remove('pinned'); tt.style.opacity=0; }
function tip(el,html,iso){
 el.addEventListener('mousemove',e=>{
  if(PIN)return;
  const wide=EVID&&D.qual[iso];
  tt.className=wide?'wide':''; tt.innerHTML=html(); tt.style.opacity=1; place(e,wide);});
 el.addEventListener('mouseleave',()=>{if(!PIN)tt.style.opacity=0;});
 el.addEventListener('click',e=>{
  if(!iso||!D.data[iso])return;
  e.stopPropagation(); unpin(); tt.style.opacity=0; showProfile(iso);});}
document.addEventListener('click',()=>{if(PIN)unpin();});

function vals(d){
 if(MODE==="flows"||MODE==="sub")return[[],0];
 if(MODE==="both"){
   const acc={};let t=0;
   [["stock",1],["refugees",1]].forEach(([k])=>{
     const v=d[k]||{};
     C.forEach(c=>{const n=v[String(c)]||0;if(n>0){acc[c]=(acc[c]||0)+n;t+=n;}});});
   return[C.filter(c=>acc[c]).map(c=>[c,acc[c]]),t];}
 if(MODE==="period"){                      // long IDMC conflict series, 1990+
   if(!d.peak||!d.peak.n)return[[],0];
   return[[[1,d.peak.n]],d.peak.n];}
 let v=d[MODE]||{};
 if(ATTR&&MODE==="stock"&&d.attr&&v["0"]){
   // reallocate IDMC's "conflict, type not recorded" using UCDP. Imputed, and
   // labelled as such everywhere it appears.
   v=Object.assign({},v);
   const u=v["0"], tot=(d.attr.to_code1+d.attr.to_code2)||1;
   v["1"]=(v["1"]||0)+u*d.attr.to_code1/tot;
   v["2"]=(v["2"]||0)+u*d.attr.to_code2/tot;
   delete v["0"];}
 const o=[];let t=0;
 const want = CAUSE==="all" ? C : C.filter(c=>String(c)===CAUSE);
 want.forEach(c=>{const n=v[String(c)]||0;if(n>0){o.push([c,n]);t+=n;}});return[o,t];}

function valsAll(d){
 const keep=CAUSE; CAUSE="all";
 const r=vals(d); CAUSE=keep; return r;}

function spark(series,w,h){                 // trajectory of a country's IDP stock
 const ys=Object.keys(series).map(Number).sort((a,b)=>a-b);
 if(ys.length<2)return"";
 const vs=ys.map(y=>series[String(y)]);
 const mx=Math.max(...vs), y0=ys[0], y1=ys[ys.length-1];
 const pts=ys.map((y,i)=>`${((y-y0)/(y1-y0)*w).toFixed(1)},${(h-vs[i]/mx*h).toFixed(1)}`);
 return `<svg width="${w}" height="${h}" style="display:block;margin:6px 0 2px">
  <polyline points="${pts.join(" ")}" fill="none" stroke="var(--c1)" stroke-width="1.6"/>
  </svg><div class="ev">${y0} → ${y1}</div>`;}

const CENT={};
D.geo.forEach(f=>{if(f.iso3&&f.c)CENT[f.iso3]=f.c;});



function drawSub(){
 // IDMC geocodes every figure it records - 7,648 distinct locations, mostly at
 // ADM2/ADM3, finer than the admin1 layer. This is displaced PEOPLE at the place
 // they were displaced from, not conflict deaths.
 const pts = CAUSE==="all" ? D.pts : D.pts.filter(p=>String(p.c)===CAUSE);
 if(!pts.length){document.getElementById('key').innerHTML=
   `<span style="color:var(--muted)">no geocoded displacement for this cause</span>`;return;}
 const mx=Math.max(...D.pts.map(p=>p.n));   // fixed scale across causes
 pts.slice().sort((a,b)=>b.n-a.n).forEach(p=>{
  const g=document.createElementNS(NS,"g");
  g.dataset.base=`translate(${px(p.x).toFixed(1)},${py(p.y).toFixed(1)})`;
  g.setAttribute("transform",g.dataset.base);
  const r=0.7+11*Math.sqrt(p.n/mx);
  const c=document.createElementNS(NS,"circle");
  c.setAttribute("r",r.toFixed(2));
  c.setAttribute("fill",p.c===7?"url(#hatch)":(p.c===0?"var(--unattr)":COL[p.c]));
  c.setAttribute("fill-opacity",".7");
  c.setAttribute("stroke","var(--surface-1)");c.setAttribute("stroke-width",".4");
  g.appendChild(c);
  const hit=document.createElementNS(NS,"circle");
  hit.setAttribute("r",Math.max(r,4).toFixed(2));hit.setAttribute("fill","transparent");
  hit.style.cursor="pointer";g.appendChild(hit);
  const cn=(D.data[p.i]||{}).name||p.i;
  tip(hit,()=>`<b>${p.l}</b><div class="ev">${cn}</div><hr>`+
    `<div><b style="color:${p.c===7||p.c===0?'var(--ink-2)':COL[p.c]}">■</b> `+
    `${lab(p.c)} — <b>${fmt(p.n)}</b> displaced</div>`+
    (p.h?`<div class="ev">${p.h}</div>`:``)+
    `<div class="ev" style="margin-top:4px">located at ${p.a} precision</div>`, p.i);
  layer.appendChild(g);});
 applyT();
 document.getElementById('key').innerHTML =
  C.filter(c=>c!==9).map(c=>`<span><i style="background:${SWATCH[c]};${c===7
    ?'border:1px solid var(--grid)':''}"></i>${L[c]}</span>`).join('')+
  `<span style="color:var(--muted)">one point per recorded location \u2014 area \u221d people displaced</span>`;
 document.getElementById('anchor').innerHTML =
  `<b>Each point is a place people were displaced FROM</b>, not a country. `+
  `${pts.length.toLocaleString()} locations, mostly district or town level. Zoom in.`;
 document.getElementById('modenote').innerHTML="<b>What you are looking at.</b> "+
  `IDMC geocodes every figure it records, so displacement can be placed at the district `+
  `or town it happened in rather than smeared across a country. 7,648 locations across `+
  `146 countries \u2014 62% at ADM3 (town/village), 30% at ADM2 (district). This is the `+
  `level at which enumerator materials would actually be adapted: Mogadishu's evictions `+
  `and Somalia's pastoral drought are different places, different causes and different `+
  `prompts, inside one country.`;
 document.getElementById('tbl').innerHTML="";
}

/* ------------------------------------------------------------------ EVENTS */
/* Counts of things that happened, not people they moved. Three units live in
   here and only two of them are ever added together:
     UCDP GED  one geocoded incident with at least one battle-related death
     ACLED     one political-violence event, deaths or not - structurally many
               more, and coding the SAME conflicts, so it replaces GED, never
               joins it
     IDMC      one displacement figure record for a hazard - not an incident at
               all, but a disjoint phenomenon, so conflict + hazard is a
               legitimate (if mixed-unit) total. Every tooltip says so.        */

function evCounts(d,all){
 // conflict from whichever source is selected; hazards always from IDMC
 const cf=d[ESRC]||{}, hz=d.idmc||{}, o={};
 EC.forEach(c=>{const n=(cf[String(c)]||0)+(hz[String(c)]||0); if(n>0)o[c]=n;});
 if(all||CAUSE==="all")return o;
 return o[CAUSE]?{[CAUSE]:o[CAUSE]}:{};}

function evAdmCounts(a,all){
 // IDMC hazard records were folded into the GED-keyed object at build time, so
 // codes 6 and 7 always come from there. Under ACLED, conflict codes come ONLY
 // from a.a - falling back to GED where ACLED has no coverage would relabel one
 // source's counts as the other's, which is exactly the error the independence
 // table exists to prevent. An area ACLED never covered draws hazards or nothing.
 let base;
 if(ESRC==="acled"){
  base={6:a.u["6"]||0,7:a.u["7"]||0};
  [1,2,4,5].forEach(c=>{if(a.a[String(c)])base[c]=a.a[String(c)];});
 }else base=a.u;
 const o={};
 EC.forEach(c=>{const n=base[String(c)]||0; if(n>0)o[c]=n;});
 if(all||CAUSE==="all")return o;
 return o[CAUSE]?{[CAUSE]:o[CAUSE]}:{};}

const esum=o=>EC.reduce((a,c)=>a+(o[c]||0),0);

function evSlices(g,o,r){
 const tot=esum(o), present=EC.filter(c=>o[c]);
 if(tot<=0)return;
 if(present.length===1){                  // a full circle has no arc to draw
  const c=document.createElementNS(NS,"path");
  c.setAttribute("d",`M0,${-r}A${r},${r} 0 1 1 0,${r}A${r},${r} 0 1 1 0,${-r}Z`);
  c.setAttribute("fill",ECOL[present[0]]);
  c.setAttribute("fill-rule","evenodd");
  c.setAttribute("stroke","var(--surface-1)");c.setAttribute("stroke-width",".5");
  g.appendChild(c);return;}
 let a0=-Math.PI/2;
 present.forEach(c=>{
  const a1=a0+2*Math.PI*o[c]/tot;
  const x0=r*Math.cos(a0),y0=r*Math.sin(a0),x1=r*Math.cos(a1),y1=r*Math.sin(a1);
  const p=document.createElementNS(NS,"path");
  p.setAttribute("d",`M0,0L${x0.toFixed(2)},${y0.toFixed(2)}`+
   `A${r},${r} 0 ${a1-a0>Math.PI?1:0} 1 ${x1.toFixed(2)},${y1.toFixed(2)}Z`);
  p.setAttribute("fill",ECOL[c]);
  p.setAttribute("stroke","var(--surface-1)");p.setAttribute("stroke-width",".5");
  g.appendChild(p);a0=a1;});}

function evRows(o,deaths,affected){
 const tot=esum(o);
 return EC.filter(c=>o[c]).map(c=>{
  const extra=(c===6||c===7)
    ? ((affected&&affected[String(c)])?` · ${fmt(affected[String(c)])} people affected`:``)
    : ((deaths&&deaths[String(c)])?` · ${fmt(deaths[String(c)])} deaths`:``);
  return `<div><b style="color:${(c===4||c===7)?'var(--ink-2)':
    (c===5?'var(--unattr)':COL[c])}">■</b> ${ELAB[c]} — <b>${o[c].toLocaleString()}</b> `+
   `${(c===6||c===7)?"records":"events"} `+
   `<span style="color:var(--muted)">(${(100*o[c]/tot).toFixed(0)}%)</span>`+
   `<span class="ev">${extra}</span></div>`;}).join('');}

function evNamed(d){
 const want=CAUSE==="all"?EC:[Number(CAUSE)];
 let h="";
 want.forEach(c=>{
  const list=(d.named||{})[String(c)]; if(!list||!list.length)return;
  h+=`<div class="blk"><div class="ttl"><span class="cd">${ELAB[c]}</span></div>`+
   list.map(e=>`<div style="margin-top:3px"><b>${e.t}</b>`+
    // non-state conflicts carry the dyad as their name, so don't print it twice
    (e.d&&e.d!==e.t?`<div class="ev">${e.d}</div>`:``)+
    `<div class="ev">${e.n.toLocaleString()} ${e.u} · ${fmt(e.k)} `+
    `${e.u==="records"?"people affected":"deaths"} · ${e.y}</div></div>`).join('')+
   `</div>`;});
 return h;}

function drawEvents(){
 const CENTF={}; D.geo.forEach(f=>{if(f.iso3&&f.c)CENTF[f.iso3]=f.c;});
 const items=[];
 if(ELEVEL==="country"){
  Object.entries(D.ev).forEach(([iso,d])=>{
   const c=CENTF[iso]; if(!c)return;
   items.push({iso,d,x:c[0],y:c[1],
     o:evCounts(d,false),all:evCounts(d,true),
     deaths:ESRC==="acled"?d.acled_deaths:d.deaths,affected:d.affected,
     label:d.name,adm:null});});
 }else{
  Object.entries(D.ev).forEach(([iso,d])=>{
   (d.adm||[]).forEach(a=>{
    items.push({iso,d,x:a.x,y:a.y,o:evAdmCounts(a,false),all:evAdmCounts(a,true),
      deaths:a.d,affected:null,label:a.n,adm:a});});});}

 const max=Math.max(1,...items.map(i=>esum(i.all)));
 // fixed scale from the all-causes total, so picking one cause SHRINKS a circle
 // rather than recolouring it - the whole point of the per-cause view. The floor
 // under a single cause exists only so "a few" stays distinguishable from "none";
 // it is deliberately small enough that the shrinkage is still the message.
 const R=t=>(CAUSE==="all"?1.8:0.9)+(ELEVEL==="country"?13:9)*Math.sqrt(t/max);
 const gtot=items.reduce((a,i)=>a+esum(i.all),0);
 const ctot=items.reduce((a,i)=>a+esum(i.o),0);

 items.sort((a,b)=>esum(b.o)-esum(a.o));   // small on top, so they stay clickable
 items.forEach(it=>{
  const tot=esum(it.o); if(tot<=0)return;
  const r=R(tot);
  const g=document.createElementNS(NS,"g");
  g.dataset.base=`translate(${px(it.x).toFixed(1)},${py(it.y).toFixed(1)})`;
  g.setAttribute("transform",g.dataset.base);
  g.setAttribute("opacity",ELEVEL==="adm1"?".82":"1");
  evSlices(g,it.o,r);
  const hit=document.createElementNS(NS,"circle");
  hit.setAttribute("r",Math.max(r,4.5).toFixed(2));hit.setAttribute("fill","transparent");
  hit.style.cursor="pointer";g.appendChild(hit);

  tip(hit,()=>{
   const srcn=ESRCNAME[ESRC];
   let h=`<div class="hd"><b>${it.label}</b>`+
     (it.adm?`<span class="hint">${it.d.name}</span>`
            :`<span class="hint">click for full profile</span>`)+`</div><div class="bd">`;
   h+=`<div class="blk"><div class="ttl"><span class="cd">`+
      `${tot.toLocaleString()} recorded events</span></div>`+
      evRows(it.o,it.deaths,it.affected)+`</div>`;
   if(it.adm&&it.adm.cf)
     h+=`<div class="blk"><div class="ev"><b>Conflicts recorded here</b><br>`+
        `${it.adm.cf}</div></div>`;
   if(it.adm&&it.adm.k)
     h+=`<div class="blk"><div class="ev"><b>${fmt(it.adm.k)}</b> people displaced by `+
        `hazards recorded at this location</div></div>`;
   if(!it.adm)h+=evNamed(it.d);
   h+=`<div class="blk"><div class="ev">Conflict counts from <b>${srcn}</b>`+
      (it.d[ESRC+"_years"]?` (${it.d[ESRC+"_years"][0]}–${it.d[ESRC+"_years"][1]})`:``)+
      `; hazard counts are IDMC displacement records`+
      (it.d.idmc_years?` (${it.d.idmc_years[0]}–${it.d.idmc_years[1]})`:``)+
      `. Different units — an incident and a displacement record are not the `+
      `same thing, and the total mixes them.</div></div>`;
   return h+`</div>`;}, it.adm?null:it.iso);
  layer.appendChild(g);});

 applyT();
 document.getElementById('key').innerHTML =
  EC.map(c=>`<span><i style="background:${ESWATCH[c]};${c===4||c===7
    ?'border:1px solid var(--grid)':''}"></i>${ELAB[c]}</span>`).join('')+
  `<span style="color:var(--muted)">circle area ∝ number of recorded events</span>`;
 document.getElementById('anchor').innerHTML = (CAUSE!=="all")
  ? `<b>${ELAB[Number(CAUSE)]} is ${(100*ctot/gtot).toFixed(1)}% of all recorded events`+
    `${ESRC==="acled"?" in ACLED's 68 countries":""}.</b> Circles stay on the All-causes `+
    `scale, so these are genuinely this small — a cause can matter enormously to the people `+
    `it displaces and still be rare in an event count.`
  : ELEVEL==="country"
  ? `<b>Circle size is how OFTEN something happens, not how many people it moved.</b> `+
    `Compare with the population view — the two disagree sharply, and the disagreement `+
    `is the point.`
  : `<b>${items.length.toLocaleString()} subnational areas.</b> Conflict is concentrated in `+
    `a handful of provinces inside most affected countries; a national showcard hides that. `+
    `Zoom in.`;
 document.getElementById('modenote').innerHTML="<b>What you are looking at.</b> "+
  `Recorded events, not displaced people. Conflict incidents come from `+
  `<b>${ESRCNAME[ESRC]}</b>; hazard records from IDMC. `+
  (ESRC==="acled"
   ? `ACLED counts every political-violence event whether or not anyone died, so its totals `+
     `are several times UCDP's for the same conflicts — it covers ${NACLED} countries against `+
     `UCDP's ${NUCDP}. It is an <b>alternative</b> to UCDP GED, never an addition — the two `+
     `code the same underlying events.`
   : `UCDP GED counts geocoded incidents with at least one battle-related death, 1989 `+
     `onwards, globally. Events with no fatalities are invisible to it, which understates `+
     `code 2 in particular.`)+
  ` <b>Two response options appear here that the population view cannot show at all:</b> `+
  `code 4 (state one-sided violence) and code 5 (non-state one-sided violence). No `+
  `displacement database attributes population to either, but the events do exist and are `+
  `counted — which is a direct argument for keeping both options in the instrument.`;

 const rank=items.slice(0,20);
 document.getElementById('tbl').innerHTML=
  `<thead><tr><th>${ELEVEL==="country"?"Country":"Area"}</th>`+
  `<th>${ELEVEL==="country"?"Largest named event":"Country"}</th><th>Events</th>`+
  EC.map(c=>`<th>${c}</th>`).join('')+`</tr></thead><tbody>`+
  rank.map(it=>{
   const top=EC.filter(c=>it.o[c]).sort((a,b)=>it.o[b]-it.o[a])[0];
   const nm=it.adm?it.d.name
     :(((it.d.named||{})[String(top)]||[])[0]||{}).t||"—";
   return `<tr><td>${it.label}</td><td style="color:var(--ink-2)">${nm}</td>`+
    `<td><b>${esum(it.o).toLocaleString()}</b></td>`+
    EC.map(c=>`<td>${it.o[c]?it.o[c].toLocaleString()
      :'<span style="color:var(--muted)">—</span>'}</td>`).join('')+`</tr>`;})
   .join('')+`</tbody>`;}

function drawFlows(){
 const mx=Math.max(...D.flows.map(f=>f.n));
 // biggest last so they sit on top
 D.flows.slice().sort((a,b)=>a.n-b.n).forEach(fl=>{
  const o=CENT[fl.o], a=CENT[fl.a]; if(!o||!a)return;
  const x0=px(o[0]),y0=py(o[1]),x1=px(a[0]),y1=py(a[1]);
  // bow the arc perpendicular to the chord so overlapping pairs stay legible
  const mx0=(x0+x1)/2, my0=(y0+y1)/2, dx=x1-x0, dy=y1-y0;
  const len=Math.hypot(dx,dy)||1, bow=Math.min(len*0.22,60);
  const cx=mx0-dy/len*bow, cy=my0+dx/len*bow;
  const p=document.createElementNS(NS,"path");
  p.setAttribute("d",`M${x0.toFixed(1)},${y0.toFixed(1)} Q${cx.toFixed(1)},${cy.toFixed(1)} ${x1.toFixed(1)},${y1.toFixed(1)}`);
  p.setAttribute("class","flow");
  p.setAttribute("stroke",fl.code?COL[fl.code]:"var(--unattr)");
  // scale harder than sqrt so the largest movements dominate visually
  const w=fl.n/mx;
  p.setAttribute("stroke-width",(0.5+5.2*Math.pow(w,0.62)).toFixed(2));
  p.setAttribute("opacity",(0.35+0.5*Math.pow(w,0.4)).toFixed(2));
  layer.appendChild(p);
  tip(p,()=>`<b>${fl.on} \u2192 ${fl.an}</b><hr>`+
    `<div><b>${fmt(fl.n)}</b> refugees and asylum seekers</div>`+
    (fl.code?`<div class="ev">Displacement in ${fl.on} is mostly `+
      `${L[fl.code].toLowerCase()}</div>`:``), null);
  // arrowhead at the destination
  const t=0.94, hx=(1-t)*(1-t)*x0+2*(1-t)*t*cx+t*t*x1, hy=(1-t)*(1-t)*y0+2*(1-t)*t*cy+t*t*y1;
  const ang=Math.atan2(y1-hy,x1-hx)*180/Math.PI;
  const h=document.createElementNS(NS,"path");
  h.setAttribute("d","M0,0 L-4.5,-2.2 L-4.5,2.2 Z");
  h.setAttribute("transform",`translate(${x1.toFixed(1)},${y1.toFixed(1)}) rotate(${ang.toFixed(1)})`);
  h.setAttribute("fill",fl.code?COL[fl.code]:"var(--unattr)");
  h.setAttribute("opacity",".8");
  layer.appendChild(h);});
}

const BAND={severe:["b-doc","Severe"],substantial:["b-abuse","Substantial"],
            moderate:["b-none","Moderate"],limited:["b-none","Limited"]};
function disasterBlock(iso){
 const v=D.dis[iso]; if(!v)return "";
 let h=`<div class="blk"><div class="ttl"><span class="cd">Disaster record (IDMC)</span></div>`+
  `<div class="ev" style="font-size:12px"><b>${v.n_events}</b> named events, `+
  `<b>${fmt(v.total)}</b> people displaced`+
  (v.hazards.length?` · mostly ${v.hazards.slice(0,2).map(x=>x.h.toLowerCase()).join(" and ")}`:``)+
  `</div>`;
 if(v.top.length){
  h+=`<div class="ev" style="font-size:12px;margin-top:5px"><b>Largest events:</b></div>`;
  v.top.forEach(t=>{h+=`<div class="ev" style="font-size:12px">· <b>${t.name}</b>`+
   `${t.start?` — ${t.start}`:''} — ${fmt(t.people)} displaced</div>`;});
  h+=`<div class="ev" style="font-size:11.5px;margin-top:4px;color:var(--muted)">`+
   `A respondent will name the storm, not the hazard class. These are the usable `+
   `enumerator prompts.</div>`;}
 return h+`</div>`;}

function ucdpBlock(iso){
 const n=D.ucdp.narrative[iso], g0=D.gedc[iso];
 if(!n&&g0&&g0.length){
  let hh=`<div class="blk"><div class="ttl"><span class="cd">Named conflicts (UCDP GED)</span></div>`;
  g0.slice(0,4).forEach(c=>{hh+=`<div class="ev" style="font-size:12px">· <b>${c.dyad}</b> — `+
   `${c.first}\u2013${c.last}, ${fmt(c.deaths)} deaths across ${c.adm1s} region`+
   `${c.adm1s===1?'':'s'}</div>`;});
  return hh+`</div>`;}
 if(!n)return "";
 let h=`<div class="blk"><div class="ttl"><span class="cd">Armed conflict record (UCDP)</span></div>`+
  `<div class="ev" style="font-size:12px"><b>${n.active_years}</b> years with an active `+
  `state-based armed conflict since 1989 (${n.spans.join(", ")}) · `+
  `<b>${n.war_intensity_years}</b> at war intensity`+
  (n.still_active?` · <b style="color:var(--c2)">still active</b>`:` · none recorded since ${n.latest_year}`)+
  `</div>`;
 const g=D.gedc[iso];
 if(g&&g.length){
  h+=`<div class="ev" style="font-size:12px;margin-top:5px"><b>Named conflicts (UCDP GED):</b></div>`;
  g.slice(0,4).forEach(c=>{h+=`<div class="ev" style="font-size:12px">· <b>${c.dyad}</b> — `+
   `${c.first}\u2013${c.last}, ${fmt(c.deaths)} deaths across ${c.adm1s} region`+
   `${c.adm1s===1?'':'s'}</div>`;});
 } else if(n.active_now&&n.active_now.length){
  h+=`<div class="ev" style="font-size:12px;margin-top:5px"><b>Running most recently:</b></div>`;
  n.active_now.forEach(a=>{h+=`<div class="ev" style="font-size:12px">· ${a.type} over `+
   `${a.over==="both"?"government and territory":a.over}, began <b>${a.began}</b>`+
   `${a.war?' — war intensity':''}</div>`;});}
 const at=D.ucdp.attribution[iso];
 if(at&&at.unattributed>0)h+=`<div class="ev" style="font-size:12px;margin-top:5px">`+
  `${fmt(at.unattributed)} people IDMC could not classify. UCDP method: <b>${at.method}</b> `+
  `→ ${fmt(at.to_code1)} armed conflict, ${fmt(at.to_code2)} widespread violence. `+
  `<i>Imputed, not recorded.</i></div>`;
 return h+`</div>`;}

function vdemBlock(iso){
 const v=D.vdem[iso]; if(!v)return "";
 let h=`<div class="blk"><div class="ttl"><span class="cd">Conditions today (V-Dem)</span></div>`+
  `<div class="ev" style="font-size:12px">Measures whether the cause EXISTS here, not how `+
  `many it displaced \u2014 the same class of evidence as an event count.</div>`;
 [["3","Discrimination or persecution"],["4","HR violations by authorities"]].forEach(([k,lab])=>{
  const x=v[k]; if(!x||x.latest===null)return;
  const [cls,txt]=BAND[x.latest_band]||BAND.limited;
  h+=`<div style="margin-top:6px"><span class="badge ${cls}">${txt}</span> `+
     `<b>${k}. ${lab}</b></div>`+
     `<div class="ev" style="font-size:12px">worst since 1990: `+
     `<b>${(BAND[x.worst_band]||BAND.limited)[1].toLowerCase()}</b> in ${x.worst_year} · `+
     `driven by ${x.drivers.join(" and ")}</div>`;});
 if(v.excluded_pct)h+=`<div class="ev" style="font-size:12px;margin-top:4px">`+
   `<b>${v.excluded_pct}%</b> of the population excluded from civil liberties by social group</div>`;
 return h+`</div>`;}

function drawEvidenceCause(cc){
 // no country-level count exists for these codes; show what evidence there is
 const band={severe:14,substantial:10,moderate:6,limited:3};
 D.geo.forEach(f=>{
  const iso=f.iso3, d=D.data[iso]; if(!iso||!f.c)return;
  const q=(D.qual[iso]||{})[cc], v=(D.vdem[iso]||{})[cc];
  if(!q&&!v)return;
  const documented = q && q.status==="documented";
  const r = documented ? 11 : (v&&v.latest_band ? band[v.latest_band]||3 : 3);
  const g=document.createElementNS(NS,"g");
  g.dataset.base=`translate(${px(f.c[0]).toFixed(1)},${py(f.c[1]).toFixed(1)})`;
  g.setAttribute("transform",g.dataset.base);
  const c=document.createElementNS(NS,"circle");
  c.setAttribute("r",r);
  c.setAttribute("fill", documented?"var(--evidence)":"var(--unattr)");
  c.setAttribute("fill-opacity", documented?".85":".6");
  c.setAttribute("stroke","var(--surface-1)");c.setAttribute("stroke-width","1");
  if(!documented){c.setAttribute("stroke","var(--ink-2)");
    c.setAttribute("stroke-dasharray","2 2");c.setAttribute("fill-opacity",".35");}
  g.appendChild(c);
  const hit=document.createElementNS(NS,"circle");
  hit.setAttribute("r",Math.max(r,6));hit.setAttribute("fill","transparent");
  hit.style.cursor="pointer";g.appendChild(hit);
  tip(hit,()=>{
   let h=`<div class="hd"><b>${(d||{}).name||iso}</b><span class="hint">${
     q?"click to pin · sources":"conditions only"}</span></div><div class="bd">`;
   if(q){const [cls,lab]=QB[q.status];
    h+=`<div class="blk"><div class="ttl"><span class="cd">${cc}. ${D.qlabels[cc]}</span>`+
      `<span class="badge ${cls}">${lab}</span></div>`+
      (q.scale?`<div><span class="scale">${fmt(q.scale)}</span> people</div>`:``)+
      `<div class="ev" style="font-size:12.5px">${q.summary}</div>`+
      (q.quote?`<div class="qt">\u201C${q.quote}\u201D</div>`:``)+
      (q.example?`<div class="ex"><b>Enumerator example</b>\u201C${q.example}\u201D</div>`:``)+
      (q.sources.length?`<div class="src">`+q.sources.map(x=>
        `<a href="${x.u}" target="_blank" rel="noopener">${x.l}</a>`).join(" · ")+`</div>`:``)+
      `</div>`;}
   return h+vdemBlock(iso)+`</div>`;}, iso);
  layer.appendChild(g);});
 applyT();
 document.getElementById('key').innerHTML =
  `<span><i style="background:var(--evidence)"></i>Documented displacement from this cause</span>`+
  `<span><i style="background:var(--unattr);border:1.3px dashed var(--ink-2)"></i>`+
  `V-Dem conditions only — size = severity</span>`+
  `<span style="color:var(--muted)">no displacement count exists for this code anywhere</span>`;
 document.getElementById('anchor').innerHTML =
  `<b style="color:var(--evidence)">No database counts people displaced by this cause.</b> `+
  `Filled circles are the twenty countries with documented research; dashed circles are `+
  `V-Dem's reading of whether the condition exists, sized by severity.`;
 document.getElementById('modenote').innerHTML="<b>What you are looking at.</b> "+
  `Code ${cc} has no per-country displacement figure in IDMC, UNHCR, ACLED or UCDP \u2014 `+
  `no agency counts it. Rather than invent a magnitude, this view shows the evidence that `+
  `does exist: documented displacement from human rights investigations, and V-Dem's `+
  `measure of whether the condition is present. That asymmetry is the finding.`;
 document.getElementById('tbl').innerHTML="";
}

function showProfile(iso){
 const d=D.data[iso]; if(!d)return;
 const el=document.getElementById('profile');
 const g=D.gedc[iso]||[], a1=D.geda1[iso]||[], dis=D.dis[iso], q=D.qual[iso];
 const idp=d.stock||{}, ref=d.refugees||{};
 const sum=o=>C.reduce((x,c)=>x+((o||{})[String(c)]||0),0);
 const bar=(o,lbl)=>{const t=sum(o); if(t<=0)return"";
  return `<div style="margin-bottom:8px"><b style="font-size:12.5px">${lbl} — ${fmt(t)}</b>`+
   `<div style="display:flex;height:9px;border-radius:3px;overflow:hidden;margin-top:4px;gap:1px">`+
   C.filter(c=>o[String(c)]>0).map(c=>`<div title="${L[c]}" style="width:${
     (o[String(c)]/t*100).toFixed(1)}%;background:${
     c===7?'var(--ink-2)':(c===0||c===9)?'var(--unattr)':COL[c]}"></div>`).join("")+`</div>`+
   `<div style="font-size:11.5px;color:var(--ink-2);margin-top:4px">`+
   C.filter(c=>o[String(c)]>0).sort((x,y)=>o[String(y)]-o[String(x)]).map(c=>
    `<span style="margin-right:12px"><i class="dot" style="background:${
     c===7?'var(--ink-2)':(c===0||c===9)?'var(--unattr)':COL[c]}"></i>${L[c]} ${fmt(o[String(c)])}</span>`
   ).join("")+`</div></div>`;};

 let h=`<div class="ph"><h2>${d.name}</h2>`+
  `<span class="tot">${fmt(sum(idp)+sum(ref))} displaced · `+
  `${fmt(sum(idp))} IDPs · ${fmt(sum(ref))} refugees hosted</span>`+
  `<button class="close" id="pclose">Close</button></div>`;

 // The recommendation goes FIRST. Everything below it is the working that
 // supports it, and a reader who stops after this section has the answer.
 const rec=D.sc[iso];
 if(rec){
  const ST={RECOMMENDED:["st-rec","Give examples"],
            RESIDUAL:["st-res","Always keep"],
            UNEVIDENCED:["st-un","Keep — no data"],
            LOW_SALIENCE:["st-low","Low salience"]};
  // A summary, not the form itself -- the drafted question, with per-country
  // examples, read-aloud/showcard length, language and subnational level, all
  // now lives ONLY on questions.html (see the note by .viewform above). This
  // panel just tells you what's there and links straight to this country.
  const q=D.lq&&D.lq[iso];
  if(q){
   h+=`<div class="psec"><h3>Drafted wording for this country</h3>`+
    `<div class="ev">${q.n_localised} of 7 options carry country-specific `+
    `examples, ${q.n_available} in total`+
    ((q.adm1&&q.adm1.length)
      ? ` \u2014 <b>${q.adm1.length} subnational set${q.adm1.length===1?"":"s"}</b> `+
        `differ from the national one` : ``)+
    ((D.prot||[]).includes(iso)
      ? ` \u2014 that page also carries the registration wording (where an `+
        `international protection claim is lodged, and what document it produces).`
      : ``)+
    `.</div>`+
    `<a class="viewform" href="questions.html?c=${iso}" target="_blank" `+
    `rel="noopener">View the full drafted question for ${d.name} \u2192</a></div>`;}
  h+=`<div class="psec"><h3>What to put on the showcard here</h3>`+
    `<div style="font-size:12.5px;color:var(--ink-2);margin:-2px 0 9px">`+
    `All eight options stay on the questionnaire everywhere — that is what makes the `+
    `data comparable. What changes by country is which ones the enumerator gives a `+
    `worked example for.</div><div class="rec">`+
   rec.map(r=>{const [cls,txt]=ST[r.s]||["st-res",r.s];
    return `<span class="st ${cls}">${txt}</span><div>`+
     `<div class="rl">${r.c}. ${r.l}</div>`+
     (r.w?`<div class="rw">${r.w.replace(/\|/g,"·")}</div>`:``)+
     (r.e?`<div class="re"><b style="font-size:10px;text-transform:uppercase;`+
          `letter-spacing:.04em;color:var(--muted)">Local examples</b><br>`+
          `${r.e.replace(/;/g,"<br>")}</div>`:``)+
     `</div>`;}).join("")+`</div></div>`;}

 h+=`<div class="psec">${bar(idp,"IDPs displaced inside this country")}${
   bar(ref,"Refugees and asylum seekers hosted here")}`;
 // the unattributed share, stated plainly - a country whose split is mostly
 // unknown should not read the same as one that is fully attributed
 const it=sum(idp), unk=(idp["0"]||0)+(idp["9"]||0);
 if(it>0&&unk/it>0.25)
  h+=`<div class="warn"><b>${(100*unk/it).toFixed(0)}% of this country's IDPs have no `+
     `recorded cause.</b> The split above is based on the remaining `+
     `${fmt(it-unk)}. Treat the shares as indicative, not as measurements.</div>`;
 // the same country in the events view, so the two answers sit side by side
 const e=D.ev[iso];
 if(e){
  const cf=e.ucdp||{}, hz=e.idmc||{}, eo={};
  [1,2,4,5,6,7].forEach(c=>{const n=(cf[String(c)]||0)+(hz[String(c)]||0);
    if(n>0)eo[c]=n;});
  const et=Object.values(eo).reduce((a,b)=>a+b,0);
  if(et>0){
   h+=`<div style="margin-top:12px"><b style="font-size:12.5px">Events recorded here `+
    `— ${et.toLocaleString()}</b>`+
    `<div style="display:flex;height:9px;border-radius:3px;overflow:hidden;margin-top:4px;gap:1px">`+
    Object.keys(eo).map(c=>`<div title="${ELAB[c]}" style="width:${(eo[c]/et*100).toFixed(1)}%;`+
      `background:${(c==="4"||c==="7")?'var(--ink-2)':c==="5"?'var(--unattr)':COL[c]}"></div>`).join("")+
    `</div><div style="font-size:11.5px;color:var(--ink-2);margin-top:4px">`+
    Object.keys(eo).sort((a,b)=>eo[b]-eo[a]).map(c=>
     `<span style="margin-right:12px"><i class="dot" style="background:${
      (c==="4"||c==="7")?'var(--ink-2)':c==="5"?'var(--unattr)':COL[c]}"></i>`+
     `${ELAB[c]} ${eo[c].toLocaleString()}</span>`).join("")+
    `</div><div style="font-size:11.5px;color:var(--muted);margin-top:5px">`+
    `How often things happened, not how many people moved. Codes 4 and 5 appear here `+
    `and in no displacement count anywhere.</div></div>`;}}

 // IOM DTM — what people said, not what a monitor inferred. Deliberately the
 // last bar and visually separated: it is a CHECK on the two above it, measured
 // on a different population, and must never be read as a third estimate of the
 // same thing.
 const dt=D.dtm&&D.dtm[iso];
 if(dt&&dt.total>0){
  const V={boundary:["var(--c2)","People and sources disagree about WHICH violence option — "+
     "the distinction the questions ask respondents to draw"],
    caseload:["var(--muted)","Different caseloads rather than different labels: DTM tracks "+
     "protracted conflict displacement, the IDMC file here covers recent flows"],
    unreported:["var(--muted)","One side has no cause recorded at all"],
    agree:["var(--c6)","People's own answers agree with what we attributed"]};
  const vv=V[dt.verdict]||null;
  const keys=Object.keys(dt.by).filter(c=>dt.by[c]>0);
  const t2=keys.reduce((a,c)=>a+dt.by[c],0)+dt.econ;
  h+=`<div style="margin-top:14px;padding-top:12px;border-top:2px solid var(--grid)">`+
   `<b style="font-size:12.5px">What displaced people themselves said — ${fmt(t2)}</b>`+
   `<div style="display:flex;height:9px;border-radius:3px;overflow:hidden;margin-top:4px;gap:1px">`+
   keys.map(c=>`<div title="${lab(+c)}" style="width:${(dt.by[c]/t2*100).toFixed(1)}%;`+
     `background:${colr(+c)}"></div>`).join("")+
   (dt.econ?`<div title="Economic reasons" style="width:${(dt.econ/t2*100).toFixed(1)}%;`+
     `background:repeating-linear-gradient(45deg,var(--muted) 0 2px,transparent 2px 5px)"></div>`:``)+
   `</div><div style="font-size:11.5px;color:var(--ink-2);margin-top:4px">`+
   keys.sort((a,b)=>dt.by[b]-dt.by[a]).map(c=>
     `<span style="margin-right:12px"><i class="dot" style="background:${colr(+c)}"></i>`+
     `${lab(+c)} ${fmt(dt.by[c])}</span>`).join("")+
   (dt.econ?`<span style="margin-right:12px"><i class="dot" style="background:var(--muted)`+
     `;opacity:.5"></i>economic reasons ${fmt(dt.econ)}</span>`:``)+
   `</div>`+
   (vv?`<div class="ev" style="margin-top:6px;color:${vv[0]}">${vv[1]}</div>`:``)+
   (dt.econ?`<div class="warn" style="margin-top:7px"><b>${(100*dt.econ/t2).toFixed(0)}% `+
     `gave economic reasons.</b> Not a cause of forced displacement under IRIS, but DTM `+
     `counts these people as IDPs — a difference in who is in the population, before any `+
     `question about why.</div>`:``)+
   (dt.composite?`<div class="ev" style="margin-top:5px">Some answers named more than one `+
     `reason at once; each named cause is credited with the whole figure, so shares can `+
     `exceed 100%.</div>`:``)+
   `<div class="ev" style="margin-top:5px;color:var(--muted)">IOM DTM, latest round. The `+
   `only source here where the reason comes from the household rather than an analyst.`+
   `</div></div>`;}
 h+=`</div>`;

 h+=`<div class="pgrid"><div>`;
 if(g.length){
  h+=`<div class="psec"><h3>Named conflicts — UCDP GED</h3><table class="pt">`+
   `<thead><tr><th>Conflict</th><th>Parties</th><th class="n">Years</th>`+
   `<th class="n">Deaths</th><th class="n">Regions</th></tr></thead><tbody>`+
   g.map(c=>`<tr><td><b>${c.conflict}</b></td><td>${c.dyad}</td>`+
    `<td class="n">${c.first}–${c.last}</td><td class="n">${fmt(c.deaths)}</td>`+
    `<td class="n">${c.adm1s}</td></tr>`).join("")+`</tbody></table></div>`;}
 if(dis&&dis.top.length){
  h+=`<div class="psec"><h3>Named disaster events — IDMC</h3>`+
   `<div style="font-size:12.5px;color:var(--ink-2);margin-bottom:6px">`+
   `${dis.n_events} events, ${fmt(dis.total)} displaced</div><table class="pt">`+
   `<thead><tr><th>Event</th><th class="n">Date</th><th class="n">Displaced</th></tr></thead><tbody>`+
   dis.top.map(t=>`<tr><td><b>${t.name}</b></td><td class="n">${t.start||"—"}</td>`+
    `<td class="n">${fmt(t.people)}</td></tr>`).join("")+`</tbody></table></div>`;}
 h+=`</div><div>`;
 if(a1.length){
  h+=`<div class="psec"><h3>Where within the country — GED admin1</h3><table class="pt">`+
   `<thead><tr><th>Region</th><th>Dominant cause</th><th class="n">Deaths</th>`+
   `<th class="n">Events</th></tr></thead><tbody>`+
   a1.map(r=>`<tr><td><b>${r.a}</b><div style="font-size:11px;color:var(--muted)">${r.k}</div></td>`+
    `<td><i class="dot" style="background:${colr(r.c)}"></i>${lab(r.c)}</td>`+
    `<td class="n">${fmt(r.d)}</td><td class="n">${fmt(r.e)}</td></tr>`).join("")+
   `</tbody></table><div style="font-size:11.5px;color:var(--muted);margin-top:6px">`+
   `Conflict deaths, not displacement. Shows where within the country the violence `+
   `happened — the basis for adapting enumerator materials below national level.</div></div>`;}
 if(q){
  h+=`<div class="psec"><h3>Documented evidence — codes 3, 4, 7</h3>`;
  [3,4,7].forEach(cc=>{const e=q[String(cc)]; if(!e)return;
   const [cls,lab]=QB[e.status];
   h+=`<div style="margin-bottom:9px"><span class="badge ${cls}">${lab}</span> `+
    `<b style="font-size:12.5px">${cc}. ${D.qlabels[cc]}</b>`+
    (e.scale?` <b>${fmt(e.scale)}</b>`:``)+
    `<div style="font-size:12.5px;color:var(--ink-2);margin-top:3px">${e.summary}</div>`+
    (e.example?`<div class="ex" style="margin-top:5px"><b>Enumerator example</b>\u201C${e.example}\u201D</div>`:``)+
    (e.sources.length?`<div class="src">`+e.sources.map(x=>
      `<a href="${x.u}" target="_blank" rel="noopener">${x.l}</a>`).join(" · ")+`</div>`:``)+
    `</div>`;});
  h+=`</div>`;}
 h+=`</div></div>`;
 el.innerHTML=h; el.hidden=false;
 document.getElementById('pclose').addEventListener('click',ev=>{
   ev.stopPropagation(); el.hidden=true;});
 el.scrollIntoView({behavior:"smooth",block:"nearest"});
}

function sizeKey(max,unit){
 // Three reference circles at round numbers, drawn with the live radius function,
 // so magnitude is readable off the map instead of only rank.
 if(!max||!isFinite(max))return"";
 const nice=[1e3,5e3,1e4,5e4,1e5,5e5,1e6,5e6,1e7,5e7];
 const picks=nice.filter(v=>v<=max*0.95).slice(-3);
 if(!picks.length)return"";
 const R=t=>(CAUSE==="all"?2.2:0.6)+13*Math.sqrt(t/max);
 const w=Math.ceil(R(picks[picks.length-1])*2)+4;
 return `<span style="display:inline-flex;align-items:flex-end;gap:9px;color:var(--muted)">`+
  picks.map(v=>`<span style="display:inline-flex;flex-direction:column;align-items:center;gap:2px">`+
   `<svg width="${w}" height="${Math.ceil(R(v)*2)+2}" style="display:block;overflow:visible">`+
   `<circle cx="${w/2}" cy="${R(v)+1}" r="${R(v).toFixed(2)}" fill="none" `+
   `stroke="var(--ink-2)" stroke-width="1"/></svg>`+
   `<span style="font-size:10.5px">${fmt(v)}</span></span>`).join("")+
  `<span style="font-size:12px">${unit||"people"} — circle area ∝ the number</span></span>`;}

// One entry per "Colour by" button (see #protctl). Each supplies the CSS
// class for a given country's land path, the tooltip line, and the legend —
// the three layers protection.py's map_payload() docstring promises: who
// registers claims (categorical), how many document stages are nameable
// (ordinal), and whether the office wording actually works there (status).
const PROT_LAYERS={
 reg:{legend:[["pr-reg-GOVERNMENT","Government"],["pr-reg-UNHCR","UNHCR"],
              ["pr-reg-BOTH","Both"],["pr-reg-NONE","Nobody registers claims"]],
      cls:iso=>MP.office[iso]?('pr-reg-'+MP.office[iso]):null,
      tip:iso=>`${REGLABEL[MP.office[iso]]||MP.office[iso]} registers claims`+
        (MP.orgnames[iso]?` — ${MP.orgnames[iso]}`:"")},
 doc:{legend:[["pr-doc-0","No document nameable"],["pr-doc-1","One stage nameable"],
              ["pr-doc-2","Both stages nameable"]],
      cls:iso=>(MP.doc[iso]!=null?('pr-doc-'+MP.doc[iso]):null),
      tip:iso=>{const n=MP.doc[iso], docs=(MP.docnames[iso]||[]).filter(Boolean);
       return n==="0"?"No document can be named":
        n==="1"?`One document stage nameable${docs.length?': '+docs[0]:""}`:
        `Both stages nameable${docs.length?': '+docs.join(" → "):""}`;}},
 ask:{legend:[["pr-ask-ok","Works as written"],["pr-ask-reword","Needs rewording"],
              ["pr-ask-no","Can't be asked this way"]],
      cls:iso=>(MP.ask[iso]?('pr-ask-'+MP.ask[iso]):null),
      tip:iso=>({ok:"The office wording works as written.",
                 reword:"The office wording needs adapting for this country.",
                 no:"No office can be named here — v1 can't be asked as written."}
                [MP.ask[iso]]||"")}};

function drawProtection(){
 const cfg=PROT_LAYERS[PLAYER]||PROT_LAYERS.reg;
 LANDS.forEach(p=>{
  const iso=p.dataset.iso, cls=(iso&&cfg.cls(iso))||'pr-nodata';
  if(p.dataset.pr&&p.dataset.pr!==cls)p.classList.remove(p.dataset.pr);
  p.classList.add(cls); p.dataset.pr=cls;});
 document.getElementById('key').innerHTML=cfg.legend
  .map(([cls,label])=>`<span><i style="background:var(${
    {'pr-reg-GOVERNMENT':'--reg-gov','pr-reg-UNHCR':'--reg-unhcr','pr-reg-BOTH':'--reg-both',
     'pr-reg-NONE':'--reg-none','pr-doc-0':'--doc0','pr-doc-1':'--doc1','pr-doc-2':'--doc2',
     'pr-ask-ok':'--ask-ok','pr-ask-reword':'--ask-reword','pr-ask-no':'--ask-no'}[cls]
    })"></i>${label}</span>`).join('')+
  `<span><i style="background:var(--pr-nodata)"></i>No drafted example yet</span>`;
 document.getElementById('anchor').innerHTML=
  `<b>A different question item</b> — where a protection claim is lodged and `+
  `what document it produces, not why anyone was displaced.`;
 document.getElementById('modenote').innerHTML="<b>What you are looking at.</b> "+
  `Drafted from public sources for 151 countries — see `+
  `<a href="questions.html" target="_blank" rel="noopener">questions.html</a> for the full `+
  `wording, country by country, or click a country here to jump straight to it.`;
 document.getElementById('tbl').innerHTML="";
}

document.querySelectorAll('.players').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.players').forEach(x=>x.classList.remove('on'));
 b.classList.add('on');PLAYER=b.dataset.pl;unpin();draw();}));

function draw(){
 layer.innerHTML="";
 if(VIEW==="prot"){drawProtection();return;}
 // leaving the registration view — strip its colour classes off the land
 // layer so the base population/events tint comes back.
 LANDS.forEach(p=>{if(p.dataset.pr){p.classList.remove(p.dataset.pr);delete p.dataset.pr;}});
 if(VIEW==="events"){drawEvents();return;}
 if(MODE==="sub"){drawSub();return;}
 if(CAUSE!=="all"&&NO_COUNT.includes(CAUSE)&&MODE!=="flows"){drawEvidenceCause(CAUSE);return;}
 if(MODE==="flows"){
  drawFlows(); applyT();
  document.getElementById('key').innerHTML =
   C.filter(c=>c!==0).map(c=>`<span><i style="background:${SWATCH[c]};${c===7
     ?'border:1px solid var(--grid)':''}"></i>${L[c]}</span>`).join('')+
   `<span style="color:var(--muted)">arrow width \u221d number of people · `+
   `colour = dominant cause in the origin country</span>`;
  document.getElementById('anchor').innerHTML =
   `<b style="color:var(--c2)">Arrows run FROM where people fled TO where they are hosted.</b>`;
  document.getElementById('modenote').innerHTML="<b>What you are looking at.</b> "+notes.flows;
  const rank=D.flows.slice(0,20);
  document.getElementById('tbl').innerHTML=
   `<thead><tr><th>From</th><th>To</th><th>People</th><th>Dominant cause in origin</th></tr></thead>`+
   `<tbody>`+rank.map(f=>`<tr><td>${f.on}</td><td>${f.an}</td>`+
    `<td><b>${fmt(f.n)}</b></td><td style="color:var(--ink-2)">${f.code?L[f.code]:"\u2014"}</td></tr>`)
    .join('')+`</tbody>`;
  return;}
 // scale from the all-causes total, never from the selected cause's own maximum
 let max=0;
 D.geo.forEach(f=>{const d=f.iso3&&D.data[f.iso3];if(d)max=Math.max(max,valsAll(d)[1]);});
 if(!max)max=1;
 // area-proportional: radius scales with the square root of the population
 // no additive floor when a single cause is selected: a country with almost
 // nothing from that cause SHOULD render as almost nothing
 const R=t=>(CAUSE==="all"?2.2:0.6)+13*Math.sqrt(t/max);

 D.geo.forEach(f=>{
  const d=f.iso3&&D.data[f.iso3]; if(!d||!f.c)return;
  const [parts,total]=vals(d);
  if(total<=0){
   if(!(EVID&&D.qual[f.iso3]))return;
   // researched but nothing counted in this view - show the ring alone, which is
   // itself the finding: documented displacement that no database carries
   const g0=document.createElementNS(NS,"g");
   g0.dataset.base=`translate(${px(f.c[0]).toFixed(1)},${py(f.c[1]).toFixed(1)})`;
   g0.setAttribute("transform",g0.dataset.base);
   const ring=document.createElementNS(NS,"circle");
   ring.setAttribute("class","ring"); ring.setAttribute("r","5");
   g0.appendChild(ring);
   const h0=document.createElementNS(NS,"circle");
   h0.setAttribute("r","8"); h0.setAttribute("fill","transparent");
   h0.style.cursor="pointer"; g0.appendChild(h0);
   const iso0=f.iso3;
   tip(h0,()=>{
    const q=D.qual[iso0]; let h=`<div class="hd"><b>${d.name}</b>`+
      `<span class="hint">click for full profile</span></div><div class="bd">`+
      `<div class="blk" style="color:var(--muted)">Nothing counted in this view.</div>`;
    [3,4,7].forEach(cc=>{
     const e=q[String(cc)]; if(!e)return;
     const [cls,lab]=QB[e.status];
     h+=`<div class="blk"><div class="ttl"><span class="cd">${cc}. ${D.qlabels[cc]}</span>`+
        `<span class="badge ${cls}">${lab}</span></div>`;
     if(e.scale)h+=`<div><span class="scale">${fmt(e.scale)}</span> people</div>`;
     h+=`<div class="ev" style="font-size:12.5px">${e.summary}</div>`;
     if(e.quote)h+=`<div class="qt">\u201C${e.quote}\u201D</div>`;
     if(e.example)h+=`<div class="ex"><b>Enumerator example</b>\u201C${e.example}\u201D</div>`;
     if(e.sources.length)h+=`<div class="src">`+e.sources.map(s=>
        `<a href="${s.u}" target="_blank" rel="noopener">${s.l}</a>`).join(" · ")+`</div>`;
     h+=`</div>`;});
    return h+`</div>`;}, iso0);
   layer.appendChild(g0);
   return;}
  const cx=px(f.c[0]), cy=py(f.c[1]), r=R(total);
  const g=document.createElementNS(NS,"g");
  g.dataset.base=`translate(${cx.toFixed(1)},${cy.toFixed(1)})`;
  g.setAttribute("transform",g.dataset.base);

  if(MODE==="both"){
   // area-true nesting: inner disc area is proportional to the IDP count, the
   // annulus to the hosted refugee count, so the two populations are comparable
   // by eye and the whole circle is the total displaced population present.
   let idp=d.stock||{}, ref=d.refugees||{};
   if(CAUSE!=="all"){   // the ring renderer must honour the cause filter too
     const pick=o=>{const r={}; if(o[CAUSE])r[CAUSE]=o[CAUSE]; return r;};
     idp=pick(idp); ref=pick(ref);}
   const idpT=C.reduce((a,c)=>a+(idp[String(c)]||0),0);
   const rIn=r*Math.sqrt(Math.max(0,Math.min(1,idpT/total)));
   const arcs=(obj,r0,r1)=>{
     const tot=C.reduce((a,c)=>a+(obj[String(c)]||0),0); if(tot<=0||r1<=r0)return;
     const present=C.filter(c=>(obj[String(c)]||0)>0);
     if(present.length===1){
      // A single slice is a full circle, and an SVG arc cannot draw one - its
      // start and end points coincide and the path collapses to nothing. Draw
      // a disc (or a ring, via even-odd fill) instead.
      const c=present[0];
      const p=document.createElementNS(NS,"path");
      const circ=(rr)=>`M0,${(-rr).toFixed(2)} A${rr.toFixed(2)},${rr.toFixed(2)} 0 1 1 0,${rr.toFixed(2)} `+
                       `A${rr.toFixed(2)},${rr.toFixed(2)} 0 1 1 0,${(-rr).toFixed(2)} Z`;
      p.setAttribute("d", r0<=0.01 ? circ(r1) : circ(r1)+circ(r0));
      p.setAttribute("fill-rule","evenodd");
      p.setAttribute("fill",COL[c]);p.setAttribute("fill-opacity",".88");
      p.setAttribute("stroke","var(--surface-1)");p.setAttribute("stroke-width","0.6");
      g.appendChild(p); return;}
     let a0=-Math.PI/2;
     C.forEach(c=>{const n=obj[String(c)]||0; if(n<=0)return;
      const a1=a0+2*Math.PI*(n/tot);
      const big=(a1-a0)>Math.PI?1:0;
      const p=document.createElementNS(NS,"path");
      if(r0<=0.01){
       p.setAttribute("d",`M0,0 L${(r1*Math.cos(a0)).toFixed(2)},${(r1*Math.sin(a0)).toFixed(2)} `+
        `A${r1.toFixed(2)},${r1.toFixed(2)} 0 ${big} 1 ${(r1*Math.cos(a1)).toFixed(2)},${(r1*Math.sin(a1)).toFixed(2)} Z`);
      } else {
       p.setAttribute("d",
        `M${(r0*Math.cos(a0)).toFixed(2)},${(r0*Math.sin(a0)).toFixed(2)} `+
        `L${(r1*Math.cos(a0)).toFixed(2)},${(r1*Math.sin(a0)).toFixed(2)} `+
        `A${r1.toFixed(2)},${r1.toFixed(2)} 0 ${big} 1 ${(r1*Math.cos(a1)).toFixed(2)},${(r1*Math.sin(a1)).toFixed(2)} `+
        `L${(r0*Math.cos(a1)).toFixed(2)},${(r0*Math.sin(a1)).toFixed(2)} `+
        `A${r0.toFixed(2)},${r0.toFixed(2)} 0 ${big} 0 ${(r0*Math.cos(a0)).toFixed(2)},${(r0*Math.sin(a0)).toFixed(2)} Z`);}
      p.setAttribute("fill",COL[c]);p.setAttribute("fill-opacity",".88");
      p.setAttribute("stroke","var(--surface-1)");p.setAttribute("stroke-width","0.6");
      g.appendChild(p); a0=a1;});};
   arcs(idp,0,rIn);
   arcs(ref,rIn+0.5,r);
   if(rIn>0.5&&rIn<r-0.5){
    const sep=document.createElementNS(NS,"circle");
    sep.setAttribute("r",rIn.toFixed(2));sep.setAttribute("fill","none");
    sep.setAttribute("stroke","var(--surface-1)");sep.setAttribute("stroke-width","1.1");
    g.appendChild(sep);}
  } else if(SHAPE==="bubble"||parts.length===1){
   const dom=parts.slice().sort((a,b)=>b[1]-a[1])[0][0];
   const c=document.createElementNS(NS,"circle");
   c.setAttribute("r",r.toFixed(2));c.setAttribute("fill",COL[dom]);
   c.setAttribute("fill-opacity",".82");
   c.setAttribute("stroke","var(--surface-1)");c.setAttribute("stroke-width","1");
   g.appendChild(c);
  } else {
   let a0=-Math.PI/2;
   parts.forEach(([c,n])=>{
    const a1=a0+2*Math.PI*(n/total);
    const x0=r*Math.cos(a0),y0=r*Math.sin(a0),x1=r*Math.cos(a1),y1=r*Math.sin(a1);
    const big=(a1-a0)>Math.PI?1:0;
    const p=document.createElementNS(NS,"path");
    p.setAttribute("d",`M0,0 L${x0.toFixed(2)},${y0.toFixed(2)} `+
      `A${r.toFixed(2)},${r.toFixed(2)} 0 ${big} 1 ${x1.toFixed(2)},${y1.toFixed(2)} Z`);
    p.setAttribute("fill",COL[c]);p.setAttribute("fill-opacity",".88");
    p.setAttribute("stroke","var(--surface-1)");p.setAttribute("stroke-width","0.7");
    g.appendChild(p); a0=a1;});
  }
  if(EVID&&D.qual[f.iso3]){
   const ring=document.createElementNS(NS,"circle");
   ring.setAttribute("class","ring");
   ring.setAttribute("r",(Math.max(r,3.4)+3.4).toFixed(2));
   g.appendChild(ring);}
  const hit=document.createElementNS(NS,"circle");
  hit.setAttribute("r",Math.max(r,5).toFixed(2));hit.setAttribute("fill","transparent");
  hit.style.cursor="pointer";g.appendChild(hit);

  let rows;
  if(MODE==="both"){
   let idp=d.stock||{}, ref=d.refugees||{};
   if(CAUSE!=="all"){   // the ring renderer must honour the cause filter too
     const pick=o=>{const r={}; if(o[CAUSE])r[CAUSE]=o[CAUSE]; return r;};
     idp=pick(idp); ref=pick(ref);}
   const sum=o=>C.reduce((a,c)=>a+(o[String(c)]||0),0);
   const line=(o,lbl)=>{const t=sum(o); if(t<=0)return"";
     return `<div style="margin-top:5px"><b>${lbl} — ${fmt(t)}</b></div>`+
      C.filter(c=>o[String(c)]>0).sort((a,b)=>o[String(b)]-o[String(a)])
       .map(c=>`<div class="ev" style="font-size:12px"><b style="color:${
         c===7||c===0||c===9?'var(--ink-2)':COL[c]}">${c===7?'▨':(c===0||c===9)?'▩':'■'}</b> ${L[c]} — `+
         `${fmt(o[String(c)])} (${Math.round(o[String(c)]/t*100)}%)</div>`).join("");};
   rows=line(idp,"IDPs displaced inside this country")+
        line(ref,"Refugees and asylum seekers hosted here");
   if(d.origins.length)rows+=`<hr><div class="ev"><b>Refugee origins:</b> `+
     d.origins.map(o=>`${o.name} ${fmt(o.n)}`).join(" · ")+`</div>`;
   rows+=`<div class="ev" style="margin-top:5px">Inner disc = IDPs, outer ring = refugees; `+
     `areas are proportional so the two are comparable by eye.</div>`;
  } else rows=parts.slice().sort((a,b)=>b[1]-a[1]).map(([c,n])=>{
    let s=`<div><b style="color:${c===7||c===0||c===9?'var(--ink-2)':COL[c]}">`+
          `${c===7?'▨':(c===0||c===9)?'▩':'■'}</b> ${L[c]} — <b>${fmt(n)}</b> `+
          `(${Math.round(n/total*100)}%)</div>`;
    const evs=(d.events[String(c)]||[]).slice(0,3);
    if(evs.length&&MODE!=="refugees")
      s+=`<div class="ev">`+evs.map(e=>`· ${e.l} — ${fmt(e.n)}`).join("<br>")+`</div>`;
    return s;}).join("");
  if(MODE==="period"&&d.peak){
    rows=`<div><b style="color:${COL[1]}">■</b> <b>${fmt(d.peak.cumulative)}</b> people `+
      `displaced by conflict across ${d.peak.first_year}\u2013${d.peak.latest_year}</div>`+
      `<div class="ev">Peaked at ${fmt(d.peak.peak)} in ${d.peak.peak_year} · `+
      `${fmt(d.peak.latest)} still displaced in ${d.peak.latest_year}</div>`+
      spark(d.series,220,34)+
      `<div class="ev">Estimated as the ${d.peak.first_year} stock plus every subsequent `+
      `year-on-year increase, so nobody still displaced from the previous year is counted `+
      `twice. It undercounts people who returned and fled again within a single year. `+
      `Conflict only \u2014 no disaster series exists for this period.</div>`;}
  if(MODE==="refugees"&&d.origins.length)
    rows+=`<hr><div class="ev"><b>Origins:</b> `+
      d.origins.map(o=>`${o.name} ${fmt(o.n)}`).join(" · ")+`</div>`;
  const iso=f.iso3;
  tip(hit,()=>{
   const q=EVID?D.qual[iso]:null;
   if(!q) return `<b>${d.name}</b> — ${fmt(total)} people`+
     (MODE==="period"?` in total`:``)+`<hr>${rows}`;
   let h=`<div class="hd"><b>${d.name}</b><span class="hint">click for full profile</span></div>`+
     `<div class="bd"><div class="blk"><div class="ttl"><span class="cd">Counted \u2014 `+
     `${fmt(total)} people</span></div>${rows}</div>`+
     ucdpBlock(iso)+disasterBlock(iso);
   [3,4,7].forEach(cc=>{
    const e=q[String(cc)]; if(!e)return;
    const [cls,lab]=QB[e.status];
    h+=`<div class="blk"><div class="ttl"><span class="cd">${cc}. ${D.qlabels[cc]}</span>`+
       `<span class="badge ${cls}">${lab}</span></div>`;
    if(e.scale)h+=`<div><span class="scale">${fmt(e.scale)}</span> people `+
       `<span style="color:var(--muted)">(where a source gives a figure)</span></div>`;
    h+=`<div class="ev" style="font-size:12.5px">${e.summary}</div>`;
    if(e.quote)h+=`<div class="qt">\u201C${e.quote}\u201D</div>`;
    if(e.example)h+=`<div class="ex"><b>Enumerator example</b>\u201C${e.example}\u201D</div>`;
    if(e.sources.length)h+=`<div class="src">`+e.sources.map(s=>
       `<a href="${s.u}" target="_blank" rel="noopener">${s.l}</a>`).join(" · ")+`</div>`;
    h+=`</div>`;});
   return h+vdemBlock(iso)+`</div>`;}, iso);
  layer.appendChild(g);});
 applyT();
 document.getElementById('key').innerHTML =
  C.map(c=>`<span><i style="background:${SWATCH[c]};${c===7
    ?'border:1px solid var(--grid)':''}"></i>${L[c]}</span>`).join('')+
  sizeKey(max)+
  (EVID?`<span><i style="background:transparent;border:1.3px dashed var(--ink-2)"></i>`+
        `documented evidence for codes 3, 4 or 7 — hover for it</span>`:``);
 notes={period:"IDMC's conflict-displacement stock for every year from 1990, shipped "+
   "with UNHCR's <code>refugees</code> package. Circles are sized by each country's PEAK "+
   "displaced population over the period, and the tooltip traces the whole trajectory. "+
   "<b>Conflict only</b> — this series carries no disaster split. To get the whole "+
   "period broken down by cause, the all-years IDMC GIDD export is needed; the file "+
   "currently loaded covers "+D.period+" only.",
  both:"IDPs and hosted refugees together — everyone displaced who is physically "+
   "present in that country now, which is who a household survey there would sample. "+
   "The inner disc is people displaced inside the country; the outer ring is refugees it "+
   "hosts, displaced somewhere else. It is a <b>snapshot</b>, so nobody is counted twice.",
  sub:"IDMC geocodes every figure it records, so displacement can be placed at the "+
   "district or town it happened in rather than smeared across a country.",
  stock:"People still displaced inside their own country at the end of 2025 — "+
   "the population a household survey there would actually encounter. A <b>snapshot</b> "+
   "of who is displaced now, not a count of everyone ever displaced.",
  flow:"Displacements recorded across "+D.period+", summed. A person displaced twice is "+
   "counted twice, "+
   "and short pre-emptive evacuations are included, which inflates the disaster share "+
   "relative to what a respondent would call having to flee a home.",
  refugees:"Refugees and asylum seekers hosted, each attributed to the cause mix of their "+
   "origin country. This is the view that matters for designing a showcard in a host "+
   "country, because the causing events happened somewhere else. <b>Treat the disaster "+
   "slice with suspicion:</b> it assumes people cross a border for the same reasons that "+
   "displace people internally, and crossing a border to seek protection is far more "+
   "strongly selected on conflict and persecution than internal movement is. The conflict "+
   "share here is more likely understated than overstated."};
 document.getElementById('anchor').innerHTML = MODE==="both"
   ? `<b>Circles sit on the country where a survey would be fielded.</b> Inner disc = IDPs `+
     `displaced there; outer ring = refugees hosted there, displaced elsewhere.`
   : MODE==="refugees"
   ? `<b style="color:var(--c2)">Circles sit on the country HOSTING these people</b> — `+
     `not where the displacement was caused.`
   : `Circles sit on the country where the displacement happened.`;
 if(CAUSE!=="all"){
   document.getElementById('key').innerHTML =
    `<span><i style="background:${SWATCH[CAUSE]||'var(--unattr)'}"></i>${L[CAUSE]}</span>`+
    `<span style="color:var(--muted)">circle area \u221d people displaced by this cause `+
    `\u2014 same scale as every other cause, so sizes are comparable</span>`;
 }
 document.getElementById('modenote').innerHTML="<b>What you are looking at.</b> "+
  (CAUSE!=="all"?`Showing <b>${L[CAUSE]}</b> only. Circles are on the SAME scale as the `+
   `all-causes view, so they shrink to the share this one cause accounts for \u2014 `+
   `switch between causes and compare how much the map empties out. `:``)+notes[MODE]+
  (ATTR?` <b>Unknowns attributed.</b> IDMC's "conflict, type not recorded" band has been `+
    `reallocated to armed conflict or widespread violence using each country's own observed `+
    `ratio where it has one, and UCDP's record of whether a state-based conflict was running `+
    `where it does not. All 6.45m of the unattributed IDP stock resolves this way. These `+
    `figures are <b>imputed, not recorded</b> — the tooltip states the method per country.`:``)+
  (EVID?` <b>Evidence layer on.</b> Every country now carries a V-Dem reading of whether `+
    `persecution and state repression exist there \u2014 hover the land, not just the circle. `+
    `Ringed countries additionally carry documented displacement from `+
    `persecution, state abuse or man-made events \u2014 none of which any displacement `+
    `database counts. Somalia alone documents 1.5m people affected by forced eviction `+
    `(2018\u20132024), against 696k for man-made events in the entire global dataset.`:``);

 const rank=Object.entries(D.data).map(([iso,d])=>{const[p,t]=vals(d);return{iso,d,p,t};})
   .filter(x=>x.t>0).sort((a,b)=>b.t-a.t).slice(0,20);
 document.getElementById('tbl').innerHTML=
  `<thead><tr><th>Country</th><th>${MODE==="both"?"Split":"Largest recorded event"}</th>`+
  `<th>Total</th>`+
  C.map(c=>`<th title="${L[c]}">${c===0?"Cause not recorded"
    :c===9?"No source covers":L[c].split(" ")[0]}</th>`).join('')+`</tr></thead><tbody>`+
  rank.map(x=>{
   const top=x.p.slice().sort((a,b)=>b[1]-a[1])[0][0];
   const ev=(x.d.events[String(top)]||[])[0];
   if(MODE==="both"){
    const sum=o=>C.reduce((a,c)=>a+((o||{})[String(c)]||0),0);
    return `<tr><td>${x.d.name}</td><td style="color:var(--ink-2)">`+
     `${fmt(sum(x.d.stock))} IDPs · ${fmt(sum(x.d.refugees))} refugees</td>`+
     `<td><b>${fmt(x.t)}</b></td>`+
     C.map(c=>{const n=((x.d.stock||{})[String(c)]||0)+((x.d.refugees||{})[String(c)]||0);
       return `<td>${n?fmt(n):'<span style="color:var(--muted)">—</span>'}</td>`;}).join('')+
     `</tr>`;}
   const desc = MODE==="period" ? (x.d.peak?`peaked ${fmt(x.d.peak.peak)} in ${x.d.peak.peak_year}`:"—")
     : MODE==="refugees" ? (x.d.origins[0]?"from "+x.d.origins[0].name:"—")
     : (ev?ev.l:"—");
   return `<tr><td>${x.d.name}</td><td style="color:var(--ink-2)">${desc}</td>`+
    `<td><b>${fmt(x.t)}</b></td>`+
    C.map(c=>{const n=MODE==="period"?(c===1&&x.d.peak?x.d.peak.n:0)
        :((x.d[MODE]||{})[String(c)]||0);
      return `<td>${n?fmt(n):'<span style="color:var(--muted)">—</span>'}</td>`;}).join('')+
    `</tr>`;}).join('')+`</tbody>`;
}

function applyT(){root.setAttribute("transform",`translate(${TX},${TY}) scale(${Z})`);
 layer.querySelectorAll("g").forEach(g=>{
  if(g.dataset.base)g.setAttribute("transform",g.dataset.base+` scale(${(1/Z).toFixed(3)})`);});}
map.addEventListener("wheel",e=>{e.preventDefault();
 const r=map.getBoundingClientRect();
 const mx=(e.clientX-r.left)/r.width*W,my=(e.clientY-r.top)/r.height*H;
 const f=e.deltaY<0?1.18:1/1.18,nz=Math.min(12,Math.max(1,Z*f));
 TX=mx-(mx-TX)*(nz/Z);TY=my-(my-TY)*(nz/Z);Z=nz;
 if(Z===1){TX=0;TY=0;}applyT();},{passive:false});
let drag=null;
map.addEventListener("mousedown",e=>{drag=[e.clientX,e.clientY,TX,TY];});
addEventListener("mouseup",()=>drag=null);
addEventListener("mousemove",e=>{if(!drag)return;const r=map.getBoundingClientRect();
 TX=drag[2]+(e.clientX-drag[0])/r.width*W;TY=drag[3]+(e.clientY-drag[1])/r.height*H;applyT();});

document.querySelectorAll('.cz').forEach(b=>b.addEventListener('click',e=>{
 e.stopPropagation();
 document.querySelectorAll('.cz').forEach(x=>x.classList.remove('on'));
 b.classList.add('on');CAUSE=b.dataset.c;unpin();draw();}));
document.querySelectorAll('.mode').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.mode').forEach(x=>x.classList.remove('on'));
 b.classList.add('on');MODE=b.dataset.m;draw();}));

function setCause(c){
 document.querySelectorAll('.cz').forEach(x=>x.classList.toggle('on',x.dataset.c===c));
 CAUSE=c;}
function applyView(){
 const ev=VIEW==="events", pr=VIEW==="prot";
 document.getElementById('popctl').hidden=ev||pr;
 document.getElementById('evctl').hidden=!ev;
 document.getElementById('protctl').hidden=!pr;
 document.getElementById('map').classList.toggle('pr-mode',pr);
 document.getElementById('layerctl').hidden=ev||pr;
 document.getElementById('causectl').hidden=pr;
 // code 3 has no event source anywhere; code 5 has no population attribution
 // anywhere. Each view offers only the causes it can actually answer for. The
 // registration view has no causes at all — it is a different question item.
 if(!pr){
  document.querySelectorAll('.cz.poponly').forEach(b=>b.hidden=ev);
  document.querySelectorAll('.cz.evonly').forEach(b=>b.hidden=!ev);
  if(document.querySelector('.cz.on')&&document.querySelector('.cz.on').hidden)
    setCause("all");
 }
 document.getElementById('title').textContent = pr
   ? "Registration wording by country"
   : ev ? "Events by cause" : "Displaced population by cause";
 document.getElementById('lede').innerHTML = pr
   ? `Each country coloured by the drafted registration item — a separate part of the `+
     `instrument asking whether someone ever applied for international protection. See `+
     `<a href="questions.html" target="_blank" rel="noopener">questions.html</a> for the `+
     `full drafted wording, country by country. Scroll to zoom, drag to pan.`
   : ev
   ? `One circle per ${ELEVEL==="country"?"country":"subnational area"}, sized by how many `+
     `events were recorded there and divided by what kind. This is frequency, not `+
     `magnitude — hover to see the named conflicts and hazards behind it. `+
     `Scroll to zoom, drag to pan.`
   : `One circle per country, sized by how many people are displaced and divided by `+
     `what displaced them. Hover a country to see the numbers and the actual events IDMC `+
     `recorded — the named storm, the named conflict. Scroll to zoom, drag to pan.`;
 unpin();draw();}
/* Find a country. Hunting for Uganda on a world map is not a reasonable ask of
   someone who came here with a specific country in mind. */
const FIND=Object.entries(D.data).map(([iso,d])=>({iso,n:d.name,
  k:(d.name||"").toLowerCase()}))
  .concat(Object.entries(D.ev).filter(([iso])=>!D.data[iso])
    .map(([iso,d])=>({iso,n:d.name,k:(d.name||"").toLowerCase()})))
  .sort((a,b)=>a.n.localeCompare(b.n));
const fin=document.getElementById('find'), flist=document.getElementById('findlist');
let fsel=-1, fhits=[];
function frender(){
 if(!fhits.length){flist.hidden=true;return;}
 flist.innerHTML=fhits.map((h,i)=>`<div class="${i===fsel?'sel':''}" data-i="${i}">`+
   `${h.n}<span>${D.sc[h.iso]?"showcard":""}</span></div>`).join("");
 flist.hidden=false;}
function fgo(i){
 const h=fhits[i]; if(!h)return;
 fin.value=""; fhits=[]; flist.hidden=true; fin.blur();
 showProfile(h.iso);}
fin.addEventListener('input',()=>{
 const q=fin.value.trim().toLowerCase();
 fhits = q.length<1 ? [] : FIND.filter(f=>f.k.includes(q)).slice(0,12);
 fsel = fhits.length?0:-1; frender();});
fin.addEventListener('keydown',e=>{
 if(e.key==="ArrowDown"){fsel=Math.min(fsel+1,fhits.length-1);frender();e.preventDefault();}
 else if(e.key==="ArrowUp"){fsel=Math.max(fsel-1,0);frender();e.preventDefault();}
 else if(e.key==="Enter"){fgo(fsel);e.preventDefault();}
 else if(e.key==="Escape"){fhits=[];flist.hidden=true;fin.blur();}});
flist.addEventListener('mousedown',e=>{
 const d=e.target.closest('[data-i]'); if(d){e.preventDefault();fgo(+d.dataset.i);}});
fin.addEventListener('blur',()=>setTimeout(()=>{flist.hidden=true;},120));

document.querySelectorAll('.view').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.view').forEach(x=>x.classList.remove('on'));
 b.classList.add('on');VIEW=b.dataset.v;applyView();}));
document.querySelectorAll('.lvl').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.lvl').forEach(x=>x.classList.remove('on'));
 b.classList.add('on');ELEVEL=b.dataset.l;applyView();}));
document.querySelectorAll('.esrc').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.esrc').forEach(x=>x.classList.remove('on'));
 b.classList.add('on');ESRC=b.dataset.s;unpin();draw();}));
LANDS.forEach(p=>{
 const iso=p.dataset.iso; if(!iso)return;
 p.addEventListener('mousemove',e=>{
  if(VIEW==="prot"){
   const cfg=PROT_LAYERS[PLAYER]||PROT_LAYERS.reg, nm=(D.data[iso]||{}).name||MP.names[iso]||iso;
   tt.className='';
   tt.innerHTML = MP.office[iso]!=null
    ? `<div class="hd"><b>${nm}</b></div><div class="bd">${cfg.tip(iso)}</div>`
    : `<div class="hd"><b>${nm}</b></div><div class="bd" style="color:var(--muted)">`+
      `No drafted registration example for this country yet.</div>`;
   tt.style.opacity=1; place(e,false); return;}
  if(PIN||!EVID||!D.vdem[iso])return;
  const nm=(D.data[iso]||{}).name||D.vdem[iso].name;
  tt.className='wide';
  tt.innerHTML=`<div class="hd"><b>${nm}</b><span class="hint">conditions only</span></div>`+
    `<div class="bd">${ucdpBlock(iso)}${disasterBlock(iso)}${vdemBlock(iso)}`+
    (D.qual[iso]?``:`<div class="blk" style="color:var(--muted)">Not among the twenty `+
      `countries with documented displacement research.</div>`)+`</div>`;
  tt.style.opacity=1; place(e,true);});
 p.addEventListener('mouseleave',()=>{if(!PIN)tt.style.opacity=0;});
 p.addEventListener('click',e=>{
  if(VIEW!=="prot"||!MP.office[iso])return;
  e.stopPropagation(); window.open(`questions.html?c=${iso}`,'_blank','noopener');});});

document.getElementById('attr').addEventListener('click',e=>{
 e.stopPropagation(); ATTR=!ATTR; unpin();
 e.target.textContent=ATTR?"Attribute unknowns via UCDP  \u2713":"Attribute unknowns via UCDP";
 e.target.classList.toggle('on',ATTR); draw();});
function panelToggle(btnId,panelId,openTxt,shutTxt){
 document.getElementById(btnId).addEventListener('click',e=>{
  e.stopPropagation(); const h=document.getElementById(panelId);
  h.hidden=!h.hidden; e.target.classList.toggle('on',!h.hidden);
  e.target.textContent=h.hidden?openTxt:shutTxt;
  if(!h.hidden)h.scrollIntoView({behavior:"smooth",block:"nearest"});});}
panelToggle('helpbtn','help',"How to read this","Hide");
panelToggle('srcbtn','srcpanel',"Where these numbers come from","Hide");
document.getElementById('glosspanel').innerHTML=glossPanel();
{const e=document.getElementById('acledn');
 if(e)e.innerHTML=NACLED?`${NACLED} countries`:"not in shared build";}
panelToggle('glossbtn','glosspanel',"Plain English","Hide");
document.getElementById('advbtn').addEventListener('click',e=>{
 e.stopPropagation(); const h=document.getElementById('layerctl');
 h.hidden=!h.hidden; e.target.classList.toggle('on',!h.hidden);
 e.target.textContent=h.hidden?"More options":"Fewer options";});
document.getElementById('evid').addEventListener('click',e=>{
 e.stopPropagation(); EVID=!EVID; unpin();
 e.target.textContent=EVID?"Documented evidence for codes 3, 4 and 7  \u2713"
                          :"Documented evidence for codes 3, 4 and 7";
 e.target.classList.toggle('on',EVID); draw();});
document.getElementById('shape').addEventListener('click',e=>{
 e.stopPropagation(); SHAPE=SHAPE==="pie"?"bubble":"pie";
 e.target.textContent=SHAPE==="pie"?"Single bubbles":"Pie charts";draw();});
document.getElementById('reset').addEventListener('click',()=>{Z=1;TX=0;TY=0;applyT();});
document.getElementById('theme').addEventListener('click',()=>{
 const c=document.documentElement.getAttribute('data-theme');
 document.documentElement.setAttribute('data-theme',c==='dark'?'light':'dark');});
/* Run the annotator after every render, because most of the explanatory text on
   this page is rebuilt each time the view changes. Static-only annotation would
   cover the intro and nothing a user actually reads while exploring. */
function glossAll(){
 ["lede","modenote","anchor","profile","help","srcpanel","caveats"]
   .forEach(id=>glossify(document.getElementById(id)));}
const rawDraw=draw;
draw=function(){rawDraw.apply(this,arguments);glossAll();};
const rawProfile=showProfile;
showProfile=function(){rawProfile.apply(this,arguments);
 glossify(document.getElementById('profile'));};
/* Keep the definition on screen: flip it right-aligned when the term sits close
   enough to the right edge that a left-aligned card would overflow. */
function placeDef(g){
 if(window.innerWidth<=760){g.classList.remove('flip');return;}
 const r=g.getBoundingClientRect();
 g.classList.toggle('flip', r.left+280 > document.documentElement.clientWidth);}
document.addEventListener('mouseover',e=>{
 const g=e.target.closest&&e.target.closest('.gl'); if(g)placeDef(g);});
document.addEventListener('focusin',e=>{
 const g=e.target.closest&&e.target.closest('.gl'); if(g)placeDef(g);});

/* Tap-to-open on touch, where there is no hover. */
document.addEventListener('click',e=>{
 const g=e.target.closest('.gl');
 document.querySelectorAll('.gl.open').forEach(x=>{if(x!==g)x.classList.remove('open');});
 if(g){e.stopPropagation();placeDef(g);g.classList.toggle('open');}},true);

draw();
</script></body></html>"""

if __name__ == "__main__":
    main()

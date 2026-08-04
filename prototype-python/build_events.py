"""
The events table: what happened, where, at country and admin1 level.

The population map answers "how many people are displaced here, and by what".
This answers a different question - "what actually happens in this place, how
often" - and it is the question an enumerator briefing needs. A cause can be
frequent and displace few people (Mexico's criminal violence), or rare and
displace millions (one cyclone). Sizing by population hides the first kind
entirely, and those are exactly the cases where a respondent still needs the
response option to exist.

THREE UNITS, NEVER SUMMED BLINDLY
  UCDP GED    one geocoded incident with at least one battle-related death
  ACLED       one geocoded political-violence event, including events with no
              deaths - so ACLED counts are structurally larger and are NOT
              additive with GED. They code the same underlying conflicts.
              Offered as an alternative conflict source, never alongside.
  IDMC        one displacement figure record for a hazard event. Not an
              "event" in the incident sense at all - it is an observation of
              displacement. Combined with conflict counts only because they
              describe disjoint phenomena, and always labelled.

The circle totals conflict incidents + disaster records. That is a defensible
sum across disjoint phenomena but a mixed unit, which the tooltip states every
time. Switching the conflict source swaps GED for ACLED rather than adding it.
"""
from paths import TIDY_S
import json
import re
import unicodedata
from collections import defaultdict

import pandas as pd

TIDY = TIDY_S

# Hazards reassigned to code 7 (man-made) - see crosswalk.yaml decision log.
HUMAN_TRIGGERED = {"Wildfire", "Dam release flood", "Sinkhole"}

MIN_ADM1_EVENTS = 3       # below this an admin1 point is noise, not a pattern
MAX_ADM1_PER_COUNTRY = 60  # keeps the payload sane; countries rarely exceed it
MAX_NAMED = 6


# ACLED and UCDP name the same province differently: UCDP appends the
# administrative type ("Adamawa State", "Badakhshan province"), ACLED does not
# ("Adamawa"). Joining on the raw string matched 4 of 3,022 pairs - 0.1% - so
# the ACLED subnational layer was silently near-empty rather than wrong-looking.
ADMIN_TYPES = {
    "province", "region", "state", "department", "district", "governorate",
    "county", "oblast", "rayon", "prefecture", "municipality", "division",
    "zone", "community", "territory", "district", "city", "area", "council",
    "emirate", "canton", "parish", "commune", "voivodeship", "okrug", "krai",
    "republic", "autonomous", "metropolitan", "capital", "federal",
}


def norm_admin1(name):
    """Comparable form of an admin1 name across sources."""
    if not isinstance(name, str):
        return None
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    words = [w for w in s.split() if w]
    # strip administrative-type words from either end, repeatedly
    changed = True
    while changed and len(words) > 1:
        changed = False
        if words[-1] in ADMIN_TYPES:
            words.pop(); changed = True
        if len(words) > 1 and words[0] in ADMIN_TYPES:
            words.pop(0); changed = True
    return " ".join(words) or None


def _num(x):
    return int(round(float(x)))


def conflict_by_source(ev, source):
    """Country and admin1 event counts and deaths for one conflict source."""
    e = ev[(ev.source == source) & (ev.evidence_type == "events")]
    f = ev[(ev.source == source) & (ev.evidence_type == "fatalities")]
    cty = (e.groupby(["iso3", "code_id"]).value.sum().rename("events")
           .to_frame().join(
               f.groupby(["iso3", "code_id"]).value.sum().rename("deaths"))
           .fillna(0).reset_index())
    adm = (e.groupby(["iso3", "admin1", "code_id"]).value.sum().rename("events")
           .to_frame().join(
               f.groupby(["iso3", "admin1", "code_id"]).value.sum().rename("deaths"))
           .fillna(0).reset_index())
    yrs = e.groupby("iso3").year.agg(["min", "max"])
    return cty, adm, yrs


def disaster_records(idmc):
    """IDMC hazard records - counts of figure records, and people affected.

    Only 'Internal Displacements' (the flow series). IDP stock rows describe
    the same people at a point in time and would double-count as events.
    """
    d = idmc[(idmc.category == "Internal Displacements")
             & idmc.hazard_type.notna()].copy()
    sub = d.hazard_sub_type.fillna(d.hazard_type)
    d["code_id"] = [7 if s in HUMAN_TRIGGERED else 6 for s in sub]
    d["hz"] = sub
    d["adm1"] = (d.loc_name.fillna("").str.split(",").str[0].str.strip()
                 .replace("", pd.NA))
    ll = d.coords.fillna("").str.split(",", n=1, expand=True)
    d["lat"] = pd.to_numeric(ll[0], errors="coerce")
    d["lon"] = pd.to_numeric(ll[1] if ll.shape[1] > 1 else None, errors="coerce")
    return d


def main():
    ev = pd.read_parquet(f"{TIDY}/evidence_long.parquet")
    ged = pd.read_parquet(f"{TIDY}/ged_evidence.parquet")
    ev = pd.concat([ev, ged], ignore_index=True)
    idmc = pd.read_parquet(f"{TIDY}/idmc_detail.parquet")
    reg = {r["iso_code"]: r for r in json.load(open(f"{TIDY}/regions.json"))}
    conflicts = json.load(open(f"{TIDY}/ged_conflicts.json"))
    disasters = json.load(open(f"{TIDY}/disaster_register.json"))
    ga = pd.read_parquet(f"{TIDY}/ged_admin1.parquet")   # carries lat/lon

    ucdp_c, ucdp_a, ucdp_y = conflict_by_source(ev, "UCDP GED")
    acled_c, acled_a, acled_y = conflict_by_source(ev, "ACLED")
    dis = disaster_records(idmc)

    # admin1 coordinates: GED gives them directly; IDMC rows carry their own
    coords = {(r.iso3, r.adm_1): (float(r.lat), float(r.lon))
              for r in ga.itertuples() if pd.notna(r.lat)}

    out, isos = {}, set()
    for df in (ucdp_c, acled_c):
        isos |= set(df.iso3)
    isos |= set(dis.iso3)

    for iso in sorted(isos):
        if len(iso) != 3:
            continue
        r = reg.get(iso, {})
        rec = {
            "name": r.get("name", iso),
            "region": r.get("unhcr_region", "Unassigned"),
            "sub": r.get("unsd_subregion", ""),
            "ucdp": {}, "acled": {}, "idmc": {},
            "deaths": {}, "acled_deaths": {}, "affected": {},
            "named": {}, "adm": [],
        }

        for df, key, dk in ((ucdp_c, "ucdp", "deaths"),
                            (acled_c, "acled", "acled_deaths")):
            g = df[df.iso3 == iso]
            for t in g.itertuples():
                if t.events <= 0:
                    continue
                rec[key][str(int(t.code_id))] = _num(t.events)
                rec[dk][str(int(t.code_id))] = _num(t.deaths)

        dd = dis[dis.iso3 == iso]
        for code, g in dd.groupby("code_id"):
            rec["idmc"][str(int(code))] = int(len(g))
            rec["affected"][str(int(code))] = _num(g.figures.sum())

        for k, y in (("ucdp", ucdp_y), ("acled", acled_y)):
            if iso in y.index:
                rec[f"{k}_years"] = [int(y.loc[iso, "min"]), int(y.loc[iso, "max"])]
        if len(dd):
            rec["idmc_years"] = [int(dd.year.min()), int(dd.year.max())]

        # ---- named examples, per cause -------------------------------------
        named = defaultdict(list)
        for c in conflicts.get(iso, [])[:14]:
            named[str(c["code"])].append({
                "t": c["conflict"], "d": c["dyad"], "n": c["events"],
                "k": c["deaths"], "y": f"{c['first']}–{c['last']}",
                "u": "incidents"})
        for hz in disasters.get(iso, {}).get("hazards", []):
            code = "7" if hz["h"] in HUMAN_TRIGGERED else "6"
            g = dd[dd.hz == hz["h"]]
            if not len(g):
                continue
            named[code].append({
                "t": hz["h"], "d": "", "n": int(len(g)), "k": _num(hz["n"]),
                "y": (f"{int(g.year.min())}–{int(g.year.max())}"
                      if g.year.min() != g.year.max() else str(int(g.year.min()))),
                "u": "records"})
        for k, v in named.items():
            rec["named"][k] = sorted(v, key=lambda x: -x["n"])[:MAX_NAMED]

        # ---- admin1 ---------------------------------------------------------
        # Keyed on the NORMALISED name so the three sources land in the same
        # bucket; "label" keeps the most human of the raw spellings for display.
        adm = defaultdict(lambda: {"u": {}, "a": {}, "d": {}, "k": 0.0,
                                   "lat": None, "lon": None, "cf": "",
                                   "label": None})

        def bucket(raw):
            key = norm_admin1(raw)
            if not key:
                return None
            a = adm[key]
            # prefer the longer spelling: "Adamawa State" reads better than "Adamawa"
            if a["label"] is None or len(str(raw)) > len(a["label"]):
                a["label"] = str(raw)
            return a

        for t in ucdp_a[ucdp_a.iso3 == iso].itertuples():
            if t.events <= 0:
                continue
            a = bucket(t.admin1)
            if a is None:
                continue
            a["u"][str(int(t.code_id))] = _num(t.events)
            a["d"][str(int(t.code_id))] = _num(t.deaths)
        for t in acled_a[acled_a.iso3 == iso].itertuples():
            if t.events <= 0:
                continue
            a = bucket(t.admin1)
            if a is not None:
                a["a"][str(int(t.code_id))] = _num(t.events)
        for name, g in dd.groupby("adm1"):
            a = bucket(name)
            if a is None:
                continue
            for code, gg in g.groupby("code_id"):
                a["u"][str(int(code))] = a["u"].get(str(int(code)), 0) + len(gg)
                a["k"] += float(gg.figures.sum())
            ll = g[["lat", "lon"]].dropna()
            if len(ll) and a["lat"] is None:
                a["lat"], a["lon"] = float(ll.lat.iloc[0]), float(ll.lon.iloc[0])

        ncoords = {(i, norm_admin1(n)): xy for (i, n), xy in coords.items()}
        for key, a in adm.items():
            if a["lat"] is None:
                xy = ncoords.get((iso, key))
                if xy:
                    a["lat"], a["lon"] = xy
        # conflicts named per admin1, for the drill-down tooltip
        for t in ga[ga.iso3 == iso].itertuples():
            k = norm_admin1(t.adm_1)
            if k in adm and t.conflicts and not adm[k]["cf"]:
                adm[k]["cf"] = t.conflicts

        rows = []
        for name, a in adm.items():
            tot_u = sum(a["u"].values())
            tot_a = sum(a["a"].values())
            if a["lat"] is None or max(tot_u, tot_a) < MIN_ADM1_EVENTS:
                continue
            rows.append({"n": a["label"] or name,
                         "y": round(a["lat"], 3), "x": round(a["lon"], 3),
                         "u": a["u"], "a": a["a"], "d": a["d"],
                         "k": _num(a["k"]), "cf": a["cf"][:220]})
        rows.sort(key=lambda z: -sum(z["u"].values()))
        rec["adm"] = rows[:MAX_ADM1_PER_COUNTRY]

        if any((rec["ucdp"], rec["acled"], rec["idmc"])):
            out[iso] = rec

    json.dump(out, open(f"{TIDY}/events.json", "w"), separators=(",", ":"))

    n_adm = sum(len(v["adm"]) for v in out.values())
    tu = sum(sum(v["ucdp"].values()) for v in out.values())
    ta = sum(sum(v["acled"].values()) for v in out.values())
    ti = sum(sum(v["idmc"].values()) for v in out.values())
    print(f"wrote {len(out)} countries, {n_adm} admin1 areas")
    print(f"  UCDP GED   {tu:>9,} incidents   "
          f"({sum(1 for v in out.values() if v['ucdp'])} countries)")
    print(f"  ACLED      {ta:>9,} events      "
          f"({sum(1 for v in out.values() if v['acled'])} countries, "
          f"alternative to GED - never added)")
    print(f"  IDMC       {ti:>9,} hazard records "
          f"({sum(1 for v in out.values() if v['idmc'])} countries)")
    top = sorted(out.items(), key=lambda kv: -(sum(kv[1]['ucdp'].values())
                                               + sum(kv[1]['idmc'].values())))[:8]
    print("\nmost recorded events (GED incidents + IDMC hazard records):")
    for iso, v in top:
        print(f"   {v['name'][:26]:<27} {sum(v['ucdp'].values()):>7,} conflict  "
              f"{sum(v['idmc'].values()):>5,} hazard   {len(v['adm']):>3} areas")


if __name__ == "__main__":
    main()

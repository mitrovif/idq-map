"""
Attribute IDMC's unattributed conflict displacement using UCDP.

IDMC records 2.0m people (3.2% of flows) and 9.4% of conflict IDP STOCK as
"Unclear/Unknown" - it knows conflict caused the displacement but not what kind.
Somalia's entire 3.35m stock sits here, as do Bosnia's, Georgia's, Kenya's and
much of DR Congo's.

UCDP can settle most of it, because it records whether a state-based armed
conflict was actually running in that country that year, over what, and at what
intensity. A country with a continuously active state-based conflict is code 1;
a country with none is displacement from violence below the armed-conflict
threshold, which is code 2.

THREE TIERS, most defensible first:
  1. WITHIN-COUNTRY. If the country has attributed conflict displacement of its
     own, apply that observed IAC/NIAC vs OSV ratio to its unattributed portion.
     Same country, same period, same data producer - the safest inference.
  2. UCDP. Otherwise ask whether a state-based armed conflict was active there
     that year. Active -> code 1. None -> code 2.
  3. LEAVE IT. If neither applies, it stays unattributed. Better an honest gap
     than a fabricated attribution.

Every imputed figure is FLAGGED. The outputs report measured and imputed
separately and never merge them silently - an imputed cause is a weaker claim
than a recorded one and the reader has to be able to see which is which.
"""
from paths import ROOT_S, RAW_S, UP_S, TIDY_S, OUT_S, TOPO_S
import json
import pandas as pd
import pyreadr

RAW = RAW_S
TIDY = TIDY_S

# Gleditsch-Ward -> ISO3, for every code appearing in UCDP ACD since 1989.
GW = {
 2:"USA", 41:"HTI", 52:"TTO", 70:"MEX", 90:"GTM", 92:"SLV", 93:"NIC", 95:"PAN",
 100:"COL", 101:"VEN", 130:"ECU", 135:"PER", 150:"PRY", 200:"GBR", 230:"ESP",
 343:"MKD", 344:"HRV", 345:"SRB", 346:"BIH", 359:"MDA", 360:"ROU", 365:"RUS",
 369:"UKR", 372:"GEO", 373:"AZE", 404:"GNB", 432:"MLI", 433:"SEN", 434:"BEN",
 435:"MRT", 436:"NER", 437:"CIV", 438:"GIN", 439:"BFA", 450:"LBR", 451:"SLE",
 461:"TGO", 471:"CMR", 475:"NGA", 482:"CAF", 483:"TCD", 484:"COG", 490:"COD",
 500:"UGA", 501:"KEN", 510:"TZA", 516:"BDI", 517:"RWA", 520:"SOM", 522:"DJI",
 530:"ETH", 531:"ERI", 540:"AGO", 541:"MOZ", 560:"ZAF", 570:"LSO", 581:"COM",
 600:"MAR", 615:"DZA", 616:"TUN", 620:"LBY", 625:"SDN", 626:"SSD", 630:"IRN",
 640:"TUR", 645:"IRQ", 651:"EGY", 652:"SYR", 660:"LBN", 663:"JOR", 666:"ISR",
 678:"YEM", 690:"KWT", 700:"AFG", 702:"TJK", 703:"KGZ", 704:"UZB", 710:"CHN",
 750:"IND", 770:"PAK", 771:"BGD", 775:"MMR", 780:"LKA", 790:"NPL", 800:"THA",
 811:"KHM", 812:"LAO", 820:"MYS", 840:"PHL", 850:"IDN", 900:"AUS", 910:"PNG",
}

TYPE_LABEL = {
 "interstate": "interstate war",
 "intrastate": "internal armed conflict",
 "II": "internationalised internal armed conflict",
 "extrasystemic": "colonial or extra-state conflict",
}


def conflict_profile():
    """Country-year: was a state-based armed conflict active, and what was it?"""
    d = list(pyreadr.read_r(f"{RAW}/svmiller_ucdp_acd.rda").values())[0]
    d = d[d.year >= 1989].copy()
    rows = []
    for side in ("gwno_a", "gwno_b"):
        t = d[d[side].notna()].copy()
        t["iso3"] = t[side].astype(int).map(GW)
        rows.append(t[t.iso3.notna()])
    d = pd.concat(rows, ignore_index=True)
    d["year"] = d.year.astype(int)
    d["war"] = d.intensity_level == 2

    prof = (d.groupby(["iso3", "year"])
            .agg(n_conflicts=("conflict_id", "nunique"),
                 any_war=("war", "any"),
                 types=("type_of_conflict", lambda s: sorted(set(s))),
                 incompat=("incompatibility", lambda s: sorted(set(s))),
                 earliest=("start_date", "min"))
            .reset_index())
    return d, prof


def active_conflicts(d, iso3):
    """Every distinct conflict running in the country's most recent recorded year."""
    t = d[d.iso3 == iso3]
    if t.empty:
        return []
    yr = int(t.year.max())
    cur = t[t.year == yr].drop_duplicates("conflict_id")
    return [dict(began=str(r.start_date),
                 type=TYPE_LABEL.get(r.type_of_conflict, r.type_of_conflict),
                 over=r.incompatibility,
                 war=bool(r.intensity_level == 2)) for r in cur.itertuples()]


def narrative(iso3, prof_country):
    """A plain description of a country's conflict history, from structured fields."""
    if prof_country.empty:
        return None
    yrs = sorted(prof_country.year.unique())
    # The earliest record on file can be a long-dead conflict - Syria's is 1966,
    # which would badly misdescribe the war that began in 2011. Report the start
    # of the conflict actually running most recently, and keep the earliest
    # separately and labelled.
    earliest = min(prof_country.earliest)
    latest_yr = max(yrs)
    spans, run = [], [yrs[0]]
    for y in yrs[1:]:
        if y == run[-1] + 1:
            run.append(y)
        else:
            spans.append((run[0], run[-1])); run = [y]
    spans.append((run[0], run[-1]))
    types = sorted({t for ts in prof_country.types for t in ts})
    war_years = sorted(prof_country[prof_country.any_war].year)
    return dict(
        earliest_on_record=str(earliest),
        active_years=len(yrs),
        spans=[f"{a}–{b}" if a != b else str(a) for a, b in spans],
        types=[TYPE_LABEL.get(t, t) for t in types],
        incompatibility=sorted({i for ii in prof_country.incompat for i in ii}),
        war_intensity_years=len(war_years),
        latest_year=max(yrs),
        still_active=max(yrs) >= 2023)


def main():
    d, prof = conflict_profile()
    detail = pd.read_parquet(f"{TIDY}/idmc_detail.parquet")

    out, narr = {}, {}
    for iso in sorted(set(prof.iso3)):
        n = narrative(iso, prof[prof.iso3 == iso])
        if n:
            n["active_now"] = active_conflicts(d, iso)
            narr[iso] = n

    # ---- the attribution itself, on IDP stock (where the gap is largest)
    st = detail[detail.category == "IDPs"]
    by = st.groupby(["iso3", "code_id"])["figures"].sum().unstack(fill_value=0)
    for c in (0, 1, 2, 6, 7):
        if c not in by.columns:
            by[c] = 0.0

    recs = []
    for iso, r in by.iterrows():
        unk = float(r[0])
        if unk <= 0:
            continue
        known1, known2 = float(r[1]), float(r[2])
        tier, to1, to2 = None, 0.0, 0.0
        if known1 + known2 > 0:                       # tier 1: within-country ratio
            tier = "within-country ratio"
            to1 = unk * known1 / (known1 + known2)
            to2 = unk - to1
        else:
            p = prof[(prof.iso3 == iso) & (prof.year >= 2015)]
            if len(p):                                # tier 2: UCDP active conflict
                tier = "UCDP: state-based conflict active"
                to1 = unk
            elif iso in narr:
                tier = "UCDP: no recent state-based conflict"
                to2 = unk
            else:
                tier = None                            # tier 3: leave it
        recs.append(dict(iso3=iso, unattributed=unk, to_code1=to1, to_code2=to2,
                         method=tier or "left unattributed",
                         resolved=tier is not None))
    res = pd.DataFrame(recs).sort_values("unattributed", ascending=False)
    res.to_csv(f"{OUT_S}/attribution_of_unknown.csv", index=False)

    tot = res.unattributed.sum()
    got = res[res.resolved].unattributed.sum()
    print(f"unattributed conflict IDP stock: {tot:,.0f}")
    print(f"  attributable via the three tiers: {got:,.0f} ({got/tot:.0%})")
    print(f"  left honestly unattributed:       {tot-got:,.0f}")
    print("\nby method:")
    print(res.groupby("method")["unattributed"].agg(["size", "sum"]).to_string())
    print("\nlargest cases:")
    print(res.head(8).round(0).to_string(index=False))

    json.dump(dict(narrative=narr,
                   attribution={r.iso3: dict(unattributed=r.unattributed,
                                             to_code1=r.to_code1, to_code2=r.to_code2,
                                             method=r.method)
                                for r in res.itertuples()}),
              open(f"{TIDY}/ucdp_attribution.json", "w"), default=str)
    print(f"\nconflict narratives for {len(narr)} countries")
    for k in ("UKR", "SOM", "SYR"):
        if k in narr:
            n = narr[k]
            print(f"  {k}: {n['active_years']} active years ({', '.join(n['spans'])}), "
                  f"{n['war_intensity_years']} at war intensity")
            for a in n["active_now"]:
                print(f"       · {a['type']} over {a['over']}, began {a['began']}"
                      f"{' — war intensity' if a['war'] else ''}")


if __name__ == "__main__":
    main()

"""UCDP GED v26.1 - global, geocoded, 1989+. Named conflicts and the admin1 layer."""
from paths import ROOT_S, RAW_S, UP_S, TIDY_S, OUT_S, TOPO_S
import json
import pandas as pd
from harmonize import to_iso3

SRC = f"{RAW_S}/ged/GEDEvent_v26_1.csv"
TIDY = TIDY_S
COLS = ["year","type_of_violence","conflict_name","dyad_name","side_a","side_b",
        "adm_1","latitude","longitude","country","best","date_start","region"]

def code_of(tv, side_a):
    if tv == 1: return 1
    if tv == 2: return 2
    # one-sided: government perpetrator -> code 4, otherwise code 5
    return 4 if str(side_a).lower().startswith("government of") else 5

def main():
    d = pd.read_csv(SRC, usecols=COLS, low_memory=False)
    print(f"GED: {len(d):,} events, {d.year.min()}-{d.year.max()}, {d.country.nunique()} countries")
    d["code_id"] = [code_of(t, s) for t, s in zip(d.type_of_violence, d.side_a)]
    iso = {c: to_iso3(c) for c in d.country.unique()}
    d["iso3"] = d.country.map(iso)
    d = d[d.iso3.notna()]
    print(f"  mapped to ISO3: {len(d):,} events, {d.iso3.nunique()} countries")

    # ---- tidy evidence, global
    ev = (d.groupby(["iso3","country","adm_1","year","code_id"], dropna=False)
          .agg(events=("best","size"), fatalities=("best","sum")).reset_index())
    long = []
    for et in ("events","fatalities"):
        t = ev[["iso3","country","adm_1","year","code_id",et]].copy()
        t.columns = ["iso3","country","admin1","year","code_id","value"]
        t["evidence_type"] = et; t["source"] = "UCDP GED"
        long.append(t)
    out = pd.concat(long, ignore_index=True)
    out.to_parquet(f"{TIDY}/ged_evidence.parquet", index=False)
    print(f"  tidy evidence rows: {len(out):,}")

    # ---- named conflict register: the upgrade GED unlocks
    reg = {}
    cn = (d[d.best.notna()].groupby(["iso3","conflict_name","dyad_name","side_a","side_b","code_id"])
          .agg(events=("best","size"), deaths=("best","sum"),
               first=("year","min"), last=("year","max"),
               adm1s=("adm_1","nunique")).reset_index())
    cn = cn[cn.deaths >= 25]
    for iso, g in cn.groupby("iso3"):
        g = g.sort_values("deaths", ascending=False).head(6)
        reg[iso] = [dict(conflict=str(r.conflict_name), dyad=str(r.dyad_name),
                         a=str(r.side_a), b=str(r.side_b), code=int(r.code_id),
                         deaths=int(r.deaths), events=int(r.events),
                         first=int(r.first), last=int(r.last), adm1s=int(r.adm1s))
                    for r in g.itertuples()]
    json.dump(reg, open(f"{TIDY}/ged_conflicts.json","w"))
    from paths import OUT_S
    pd.DataFrame([dict(iso3=k, **c) for k, v in reg.items() for c in v]).to_csv(
        f"{OUT_S}/ucdp_conflict_register.csv", index=False)
    print(f"  named conflicts: {sum(len(v) for v in reg.values()):,} across {len(reg)} countries")

    # ---- admin1 layer
    a1 = (d[d.adm_1.notna()].groupby(["iso3","adm_1","code_id"])
          .agg(events=("best","size"), deaths=("best","sum"),
               lat=("latitude","mean"), lon=("longitude","mean"),
               conflicts=("conflict_name", lambda s: "; ".join(sorted(set(s))[:3])))
          .reset_index())
    a1["share"] = a1.groupby(["iso3","adm_1"])["deaths"].transform(lambda x: x/max(x.sum(),1))
    a1.to_parquet(f"{TIDY}/ged_admin1.parquet", index=False)
    a1.to_csv(f"{OUT_S}/admin1_conflict_profiles.csv", index=False)

    # per-country rollup consumed by the map: top regions with dominant cause
    roll = {}
    for iso, g in a1.groupby("iso3"):
        tot = g.groupby("adm_1")["deaths"].sum().sort_values(ascending=False)
        rows = []
        for adm in tot.head(12).index:
            sub = g[g.adm_1 == adm]
            rows.append(dict(a=str(adm), d=int(sub.deaths.sum()),
                             e=int(sub.events.sum()),
                             c=int(sub.loc[sub.deaths.idxmax(), "code_id"]),
                             k=str(sub.loc[sub.deaths.idxmax(), "conflicts"])[:90]))
        if rows:
            roll[iso] = rows
    json.dump(roll, open(f"{TIDY}/ged_admin1.json", "w"))
    print(f"  admin1 rollup: {len(roll)} countries, "
          f"{sum(len(v) for v in roll.values())} regions")
    print(f"  admin1 regions: {a1.groupby(['iso3','adm_1']).ngroups:,} across {a1.iso3.nunique()} countries")

    for k in ("SOM","UKR","SYR","COL"):
        if k in reg:
            print(f"\n{k}:")
            for c in reg[k][:3]:
                print(f"   {c['conflict']} — {c['dyad']} ({c['first']}-{c['last']}, "
                      f"{c['deaths']:,} deaths, {c['adm1s']} regions)")

if __name__ == "__main__":
    main()

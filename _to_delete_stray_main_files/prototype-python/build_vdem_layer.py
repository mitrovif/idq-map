"""
V-Dem severity layer for codes 3 and 4.

The crosswalk's weakest point is that no displacement database has a category for
persecution or for state repression short of killing. V-Dem does not fix that -
it measures the CONDITIONS, not displacement caused by them - but that is the
same evidential class as ACLED event counts for codes 1 and 2: proof the cause
exists here, not proof it moved anyone. It takes codes 3 and 4 from one confounded
proxy across 20 researched countries to a defensible measure across 180.

Two windows, because the question asks about lifetime experience:
  latest   conditions now
  worst    the worst year since 1990 - which is what a 55-year-old respondent
           may be recalling, and is often far worse than today
"""
from paths import ROOT_S, RAW_S, UP_S, TIDY_S, OUT_S, TOPO_S
import json
import numpy as np
import pandas as pd

TIDY = TIDY_S

# V-Dem scales run high = MORE freedom, so every indicator is inverted below.
CODE4 = {  # human rights violations by authorities
    "v2cltort":   "freedom from torture",
    "v2clkill":   "freedom from political killings",
    "v2xcl_prpty": "property rights",
}
CODE3 = {  # discrimination or persecution
    "v2clsocgrp": "social group equality in civil liberties",
    "v2clrelig":  "freedom of religion",
    "v2pepwrsoc": "power distributed by social group",
}


def z(s):
    """Standardise, then invert so HIGH means MORE repression."""
    return -(s - s.mean()) / (s.std() or 1)


def main():
    d = pd.read_parquet(f"{TIDY}/vdem.parquet")
    d = d[(d.year >= 1990) & d.country_text_id.notna()].copy()

    for col in list(CODE3) + list(CODE4):
        d[f"z_{col}"] = z(d[col])
    d["sev3"] = d[[f"z_{c}" for c in CODE3]].mean(axis=1)
    d["sev4"] = d[[f"z_{c}" for c in CODE4]].mean(axis=1)

    latest_year = int(d.year.max())
    out = {}
    for iso, g in d.groupby("country_text_id"):
        g = g.sort_values("year")
        cur = g[g.year == latest_year]
        rec = dict(name=str(g.country_name.iloc[-1]))
        for k, sev in (("3", "sev3"), ("4", "sev4")):
            worst_i = g[sev].idxmax()
            rec[k] = dict(
                latest=None if cur.empty else round(float(cur[sev].iloc[0]), 3),
                worst=round(float(g.loc[worst_i, sev]), 3),
                worst_year=int(g.loc[worst_i, "year"]),
                drivers=[])
            src = CODE3 if k == "3" else CODE4
            row = g.loc[worst_i]
            # name the two indicators furthest below the global mean in that year
            ranked = sorted(src, key=lambda c: row[f"z_{c}"], reverse=True)[:2]
            rec[k]["drivers"] = [src[c] for c in ranked]
        # excluded-population share, where V-Dem codes it
        pct = g[g.year == latest_year]["v2clsnlpct"]
        rec["excluded_pct"] = (None if pct.empty or pd.isna(pct.iloc[0])
                               else round(float(pct.iloc[0]), 1))
        out[iso] = rec

    # severity bands from the distribution of the latest year, so labels mean
    # "relative to the rest of the world now" rather than an arbitrary cut
    for k in ("3", "4"):
        vals = np.array([v[k]["latest"] for v in out.values()
                         if v[k]["latest"] is not None])
        q = np.quantile(vals, [0.5, 0.75, 0.9])
        for v in out.values():
            for w in ("latest", "worst"):
                x = v[k][w]
                v[k][w + "_band"] = (None if x is None else
                                     "severe" if x >= q[2] else
                                     "substantial" if x >= q[1] else
                                     "moderate" if x >= q[0] else "limited")
        print(f"  code {k} thresholds (z): moderate>={q[0]:.2f} "
              f"substantial>={q[1]:.2f} severe>={q[2]:.2f}")

    json.dump(out, open(f"{TIDY}/vdem_severity.json", "w"))
    sev4 = sorted(out.items(), key=lambda kv: -(kv[1]["4"]["latest"] or -9))[:8]
    print(f"\nwrote {len(out)} countries, latest year {latest_year}")
    print("worst code 4 (state HR violations) now:")
    for iso, v in sev4:
        print(f"   {v['name'][:28]:<29} z={v['4']['latest']:+.2f} "
              f"({v['4']['latest_band']})  driven by {', '.join(v['4']['drivers'])}")


if __name__ == "__main__":
    main()

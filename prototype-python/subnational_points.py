"""
Subnational displacement points.

IDMC geocodes every figure it records, so displacement can be placed at the
district or town it happened in rather than smeared across a country. This
turns those coordinates into one point per location per cause.
"""
from paths import TIDY_S
import json
import re
import pandas as pd


def main():
    d = pd.read_parquet(f"{TIDY_S}/idmc_detail.parquet")
    fl = d[d.category == "Internal Displacements"].copy()

    def first(c):
        """A row may carry several coordinates; take the first."""
        if not isinstance(c, str):
            return (None, None)
        m = re.match(r"\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)", c.split(";")[0])
        return (float(m.group(1)), float(m.group(2))) if m else (None, None)

    fl[["lat", "lon"]] = pd.DataFrame(fl.coords.map(first).tolist(), index=fl.index)
    fl = fl[fl.lat.notna() & fl.lon.notna()]
    fl = fl[fl.lat.between(-90, 90) & fl.lon.between(-180, 180)]
    fl["loc"] = fl.loc_name.fillna("").str.split(",").str[0].str.strip().str[:44]
    fl["acc"] = (fl.loc_accuracy.fillna("").str.split(";").str[0]
                 .str.extract(r"\((ADM\d|AM0|Point)\)")[0].fillna("?"))

    g = (fl.groupby(["iso3", "loc", "code_id", fl.lat.round(3), fl.lon.round(3),
                     "acc"], as_index=False)
         .agg(n=("figures", "sum"),
              haz=("hazard_sub_type",
                   lambda s: s.dropna().mode().iloc[0] if s.notna().any() else None)))
    g.columns = ["iso3", "loc", "code_id", "lat", "lon", "acc", "n", "haz"]
    g = g[g.n > 0].sort_values("n", ascending=False)

    pts = [dict(i=r.iso3, l=r.loc, c=int(r.code_id), y=round(r.lat, 3),
                x=round(r.lon, 3), n=int(r.n), a=r.acc,
                h=(None if pd.isna(r.haz) else str(r.haz)[:28]))
           for r in g.itertuples()]
    json.dump(pts, open(f"{TIDY_S}/idmc_points.json", "w"), separators=(",", ":"))

    from paths import OUT_S
    (pd.DataFrame(pts).rename(columns={"i": "iso3", "l": "location", "c": "code_id",
                                       "y": "lat", "x": "lon", "n": "people",
                                       "a": "accuracy", "h": "hazard"})
     .to_csv(f"{OUT_S}/subnational_displacement_points.csv", index=False))
    print(f"{len(pts):,} subnational points, {sum(p['n'] for p in pts):,} people, "
          f"{g.iso3.nunique()} countries")
    print(g.acc.value_counts().to_string())


if __name__ == "__main__":
    main()

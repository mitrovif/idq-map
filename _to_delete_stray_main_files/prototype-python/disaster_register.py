"""
Named disaster event register - the natural-disaster parallel to the UCDP
conflict record.

IDMC names and dates every disaster event it counts: 7,572 distinct events in
2025 alone, from Typhoon Fung-wong to Pakistan's monsoon floods. Same treatment
as the conflict record: what happened, when, what kind, how many it displaced.

Why this matters more here than for conflict: a respondent will not say "a
weather-related hydrological hazard". They will say the name of the storm. For
enumerator support material, the named event IS the usable prompt.
"""
from paths import ROOT_S, RAW_S, UP_S, TIDY_S, OUT_S, TOPO_S
import json, re
import pandas as pd

UP = UP_S
TIDY = TIDY_S


def clean_name(s):
    """IDMC event names carry the country list and date; strip to the event itself.
    'Philippines, Taiwan: Typhoon Fung-wong (locally Uwan) - PHL (16 Regions)... - 07/11/2025'
      -> 'Typhoon Fung-wong (locally Uwan)'"""
    s = str(s or "").strip()
    s = re.sub(r"\s*-\s*\d{2}/\d{2}/\d{4}\s*$", "", s)
    if ": " in s:
        s = s.split(": ", 1)[1]
    s = s.split(" - ")[0].strip()
    return s[:90] or "unnamed event"


def main():
    d = pd.read_excel(f"{UP}/5140e1e8-IDMC_GIDD_Internal_Displacement_Disaggregated.xlsx",
                      sheet_name="1_Disaggregated_Data")
    ds = d[(d["Figure cause"] == "Disaster") &
           (d["Figure category"] == "Internal Displacements")].copy()
    ds["name"] = ds["Event name"].map(clean_name)
    ds["start"] = pd.to_datetime(ds["Event start date"], errors="coerce")

    ev = (ds.groupby(["ISO3", "Event ID", "name", "Hazard sub type"], dropna=False)
          .agg(people=("Total figures", "sum"), start=("start", "min"))
          .reset_index())

    reg = {}
    for iso, g in ev.groupby("ISO3"):
        g = g[g.people > 0].sort_values("people", ascending=False)
        if g.empty:
            continue
        hz = (ev[ev.ISO3 == iso].groupby("Hazard sub type")["people"].sum()
              .sort_values(ascending=False))
        reg[iso] = dict(
            n_events=int(g["Event ID"].nunique()),
            total=int(g.people.sum()),
            hazards=[dict(h=str(k), n=int(v)) for k, v in hz.head(4).items() if v > 0],
            top=[dict(name=r.name, hazard=str(r._4),
                      people=int(r.people),
                      start=(None if pd.isna(r.start) else str(r.start.date())))
                 for r in g.head(4).itertuples()])

    json.dump(reg, open(f"{TIDY}/disaster_register.json", "w"))
    tot_ev = sum(v["n_events"] for v in reg.values())
    print(f"disaster register: {len(reg)} countries, {tot_ev:,} named events")
    for k in ("PHL", "SOM", "PAK", "BGD"):
        if k in reg:
            v = reg[k]
            print(f"\n{k}: {v['n_events']} events, {v['total']:,} displaced")
            for t in v["top"][:3]:
                print(f"   · {t['name']} ({t['hazard']}, {t['start']}) — {t['people']:,}")


if __name__ == "__main__":
    main()

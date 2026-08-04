"""
EGRISS IDQ causing-event map - harmonisation layer (prototype).

Reads the four source families and emits ONE tidy long table:

    iso3 | country | admin1 | year | code_id | evidence_type | value | source

evidence_type is one of:
    displaced   - people actually displaced (IDMC). The strongest evidence.
    events      - count of causing events (ACLED). Shows the cause OCCURS.
    fatalities  - deaths (ACLED, UCDP). Intensity proxy.
    rate        - derived rate (UNHCR recognition rate). Indirect proxy.

Keeping evidence_type explicit matters: 40,000 people displaced by flood and
400 protest events are not commensurable, and the showcard rule must never
silently add them together.

The R port (R/) mirrors these functions one-for-one.
"""
from paths import ROOT_S, RAW_S, UP_S, TIDY_S, OUT_S, TOPO_S
import os, re, json
import pandas as pd
import numpy as np
import pycountry

RAW = (RAW_S)
UP = os.path.join(RAW, "uploads")

# ---------------------------------------------------------------- code labels
CODES = {
    1: "Armed conflict or war",
    2: "Widespread violence / breakdown of public order",
    3: "Discrimination or persecution",
    4: "Human rights violations by authorities",
    5: "Other threats of violence",
    6: "Natural disasters",
    7: "Man-made events (eviction, pollution)",
    8: "A different threat",
}
RESIDUAL_CODES = {5, 8}
BLIND_CODES = {3, 4, 7}     # never recommend removal on zero counts

# ------------------------------------------------------------------ iso3 help
_MANUAL_ISO = {
    "Russia": "RUS", "Turkey": "TUR", "Iran": "IRN", "Syria": "SYR",
    "Palestine": "PSE", "Kosovo": "XKX", "Czech Republic": "CZE",
    "Moldova": "MDA", "North Macedonia": "MKD", "Vatican City": "VAT",
    "Bailiwick of Guernsey": "GGY", "Bailiwick of Jersey": "JEY",
    "Akrotiri and Dhekelia": None, "Isle of Man": "IMN",
    "Bosnia and Herzegovina": "BIH", "United Kingdom": "GBR",
    "Democratic Republic of Congo": "COD", "DR Congo (Zaire)": "COD",
    "Myanmar (Burma)": "MMR", "Cambodia (Kampuchea)": "KHM",
    "Yemen (North Yemen)": "YEM", "Zimbabwe (Rhodesia)": "ZWE",
    "Ivory Coast": "CIV", "Serbia (Yugoslavia)": "SRB",
    "Madagascar (Malagasy)": "MDG", "Bosnia-Herzegovina": "BIH",
    "Macedonia, FYR": "MKD", "Laos": "LAO", "Tanzania": "TZA",
    "Vietnam (North Vietnam)": "VNM", "Russia (Soviet Union)": "RUS",
    "United States of America": "USA", "Kingdom of eSwatini (Swaziland)": "SWZ",
}
# non-country ACLED rows to drop
_DROP = {"Antarctica", "Arctic Ocean", "Atlantic Ocean", "Indian Ocean",
         "Pacific Ocean", "Southern Ocean", "Mediterranean Sea",
         "Caribbean Sea", "South China Sea", "Red Sea", "Persian Gulf"}


def to_iso3(name):
    """Best-effort country name -> ISO3. Returns None if unresolvable."""
    if not isinstance(name, str) or not name.strip():
        return None
    n = name.strip()
    if n in _DROP:
        return None
    if n in _MANUAL_ISO:
        return _MANUAL_ISO[n]
    try:
        return pycountry.countries.lookup(n).alpha_3
    except LookupError:
        pass
    # strip parenthetical alternates: "Myanmar (Burma)" -> "Myanmar"
    base = re.sub(r"\s*\(.*?\)", "", n).strip()
    if base != n:
        try:
            return pycountry.countries.lookup(base).alpha_3
        except LookupError:
            pass
    try:
        m = pycountry.countries.search_fuzzy(n)
        return m[0].alpha_3
    except Exception:
        return None


# ============================================================ 1. ACLED
# ACLED's free "aggregated data" export needs NO API key. It is weekly x
# admin1 x event_type x sub_event_type with event counts, fatalities and a
# population-exposure estimate. It has no ACTOR column, which is the one
# thing that limits it here: we cannot split state from non-state perpetrator,
# so code 4 leans on UCDP one-sided instead.
ACLED_SUBEVENT_TO_CODE = {
    # --- code 1: armed conflict / war ------------------------------------
    "Armed clash": 1,
    "Air/drone strike": 1,
    "Shelling/artillery/missile attack": 1,
    "Remote explosive/landmine/IED": 1,
    "Suicide bomb": 1,
    "Grenade": 1,
    "Chemical weapon": 1,
    "Government regains territory": 1,
    "Non-state actor overtakes territory": 1,
    "Disrupted weapons use": 1,
    # --- code 2: widespread violence / breakdown of public order ---------
    "Mob violence": 2,
    "Violent demonstration": 2,
    "Protest with intervention": 2,
    "Looting/property destruction": 2,
    # --- code 4: HR violations by authorities ----------------------------
    # ACLED codes 'Arrests' as state forces detaining individuals, and
    # 'Excessive force against protesters' as state violence in a public-order
    # setting. Both sit closer to "authorities" than to "public disorder",
    # though the second genuinely straddles codes 2 and 4. Assigned to 4;
    # sensitivity of this choice is reported in the outputs.
    "Arrests": 4,
    "Excessive force against protesters": 4,
    # --- code 5: other threats of violence against you -------------------
    "Attack": 5,
    "Sexual violence": 5,
    "Abduction/forced disappearance": 5,
    # --- deliberately unmapped (not causing events for displacement) -----
    "Peaceful protest": None,
    "Agreement": None,
    "Change to group/activity": None,
    "Headquarters or base established": None,
    "Non-violent transfer of territory": None,
    "Other": None,
}


def load_acled(paths):
    frames = []
    for p in paths:
        d = pd.read_excel(p)
        d.columns = [c.strip().upper() for c in d.columns]
        frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    d["year"] = pd.to_datetime(d["WEEK"]).dt.year
    d["code_id"] = d["SUB_EVENT_TYPE"].map(ACLED_SUBEVENT_TO_CODE)
    unmapped = set(d.loc[d["code_id"].isna() &
                         ~d["SUB_EVENT_TYPE"].isin(
                             [k for k, v in ACLED_SUBEVENT_TO_CODE.items() if v is None]),
                         "SUB_EVENT_TYPE"].unique())
    if unmapped:
        print(f"  [warn] ACLED sub_event_types with no crosswalk entry: {unmapped}")
    d = d[d["code_id"].notna()].copy()
    d["code_id"] = d["code_id"].astype(int)
    d["iso3"] = d["COUNTRY"].map(to_iso3)
    d = d[d["iso3"].notna()]

    ev = (d.groupby(["iso3", "COUNTRY", "ADMIN1", "year", "code_id"], as_index=False)
            .agg(events=("EVENTS", "sum"), fatalities=("FATALITIES", "sum")))
    long = []
    for et, col in [("events", "events"), ("fatalities", "fatalities")]:
        t = ev[["iso3", "COUNTRY", "ADMIN1", "year", "code_id", col]].copy()
        t.columns = ["iso3", "country", "admin1", "year", "code_id", "value"]
        t["evidence_type"] = et
        t["source"] = "ACLED"
        long.append(t)
    return pd.concat(long, ignore_index=True)


# ============================================================ 2. IDMC GIDD
# The single most valuable source here: it reports how many people were
# ACTUALLY DISPLACED, attributed to a cause, at event level with coordinates.
# 'Violence type' gives an IDMC-adjudicated split between armed conflict
# (IAC/NIAC) and other situations of violence (OSV) - which is exactly the
# code 1 vs code 2 distinction, from the displacement agency itself rather
# than inferred from event data.
IDMC_VIOLENCE_TO_CODE = {
    "International armed conflict (IAC)": 1,
    "Non-International armed conflict (NIAC)": 1,
    "Other situations of violence (OSV)": 2,
    # DECISION: conflict-caused but type unspecified is reported as its own
    # UNATTRIBUTED band (pseudo-code 0) rather than defaulted into code 1.
    # It stays in the denominator, so country shares are shares of ALL
    # displacement and no longer sum to 100% across the eight options - which
    # is the point: 2m people were never classified by anyone.
    "Unclear/Unknown": 0,
}

# DECISION: hazards whose trigger is human, which IDMC nonetheless files under
# Disaster, are reassigned to code 7 (man-made events). Dam operation and
# extraction-induced subsidence are unambiguous; wildfire is included on the
# reading that most ignition is human. Wildfire dominates the resulting total,
# so outputs report the composition rather than a bare figure.
HUMAN_TRIGGERED_HAZARDS = {"Wildfire", "Dam release flood", "Sinkhole"}


def load_idmc(path):
    d = pd.read_excel(path, sheet_name="1_Disaggregated_Data")
    d = d.rename(columns={
        "ISO3": "iso3", "Country": "country", "Year": "year",
        "Figure cause": "cause", "Figure category": "category",
        "Total figures": "figures", "Hazard type": "hazard_type",
        "Hazard sub type": "hazard_sub_type", "Violence type": "violence_type",
        "Locations coordinates": "coords", "Locations name": "loc_name",
        "Locations accuracy": "loc_accuracy",
        "Displacement occurred": "disp_occurred", "Sources": "sources",
    })

    def code_of(r):
        if r["cause"] == "Disaster":
            if r.get("hazard_sub_type") in HUMAN_TRIGGERED_HAZARDS:
                return 7
            return 6
        if r["cause"] == "Conflict":
            return IDMC_VIOLENCE_TO_CODE.get(r["violence_type"], 1)
        if r["cause"] in ("Other", "Development"):
            return 7
        return None

    d["code_id"] = d.apply(code_of, axis=1)
    d = d[d["code_id"].notna()].copy()
    d["code_id"] = d["code_id"].astype(int)
    d["unclear_attribution"] = (d["violence_type"] == "Unclear/Unknown")
    d["human_triggered"] = d["hazard_sub_type"].isin(HUMAN_TRIGGERED_HAZARDS)
    # preventive evacuations flagged: these inflate disaster figures relative
    # to what a survey respondent would call "having to flee a home"
    d["preventive_evac"] = d["disp_occurred"].fillna("").str.contains(
        "reporting preventive evacuations")

    keep = ["iso3", "country", "year", "code_id", "figures", "category", "sources",
            "hazard_type", "hazard_sub_type", "violence_type", "coords",
            "loc_name", "loc_accuracy", "unclear_attribution", "preventive_evac"]
    detail = d[keep].copy()

    agg = (d[d["category"] == "Internal Displacements"]
           .groupby(["iso3", "country", "year", "code_id"], as_index=False)
           .agg(value=("figures", "sum")))
    agg["admin1"] = None
    agg["evidence_type"] = "displaced"
    agg["source"] = "IDMC GIDD"
    stock = (d[d["category"] == "IDPs"]
             .groupby(["iso3", "country", "year", "code_id"], as_index=False)
             .agg(value=("figures", "sum")))
    stock["admin1"] = None
    stock["evidence_type"] = "idp_stock"
    stock["source"] = "IDMC GIDD"
    long = pd.concat([agg, stock], ignore_index=True)
    return long[["iso3", "country", "admin1", "year", "code_id",
                 "evidence_type", "value", "source"]], detail


# ============================================================ 3. UCDP one-sided
def load_ucdp_onesided(path):
    d = pd.read_excel(path)
    rows = []
    for _, r in d.iterrows():
        # 'location' can list several countries: "Burundi, DR Congo (Zaire), Rwanda"
        locs = [x.strip() for x in str(r["location"]).split(",")]
        # rejoin fragments that are themselves parenthetical, e.g. "DR Congo (Zaire)"
        merged, buf = [], ""
        for part in locs:
            buf = (buf + ", " + part).strip(", ") if buf else part
            if buf.count("(") == buf.count(")"):
                merged.append(buf); buf = ""
        if buf:
            merged.append(buf)
        code = 4 if r["is_government_actor"] == 1 else 5
        share = 1.0 / max(len(merged), 1)   # split fatalities evenly, flagged
        for loc in merged:
            iso = to_iso3(loc)
            if iso:
                rows.append((iso, loc, None, int(r["year"]), code,
                             "fatalities",
                             float(r["best_fatality_estimate"]) * share,
                             "UCDP one-sided v26.1"))
    out = pd.DataFrame(rows, columns=["iso3", "country", "admin1", "year",
                                      "code_id", "evidence_type", "value", "source"])
    return (out.groupby(["iso3", "country", "admin1", "year", "code_id",
                         "evidence_type", "source"], as_index=False, dropna=False)
               .agg(value=("value", "sum")))


# ============================================================ 4. UNHCR
def load_unhcr_population(path):
    import pyreadr
    pop = list(pyreadr.read_r(path).values())[0]
    pop["year"] = pop["year"].astype(int)
    return pop


def load_unhcr_decisions(path):
    import pyreadr
    d = list(pyreadr.read_r(path).values())[0]
    d["year"] = d["year"].astype(int)
    return d


def recognition_rate_by_origin(dec, years=(2015, 2030)):
    """Code 3 proxy. Share of substantive asylum decisions that recognise
    refugee status, by country of ORIGIN. High recognition = the international
    protection system judges people from there to face persecution."""
    d = dec[(dec["year"] >= years[0]) & (dec["year"] <= years[1])]
    g = (d.groupby(["coo_iso"], as_index=False)
           .agg(rec=("dec_recognized", "sum"), rej=("dec_rejected", "sum")))
    g["denom"] = g["rec"] + g["rej"]
    g = g[g["denom"] >= 500]        # suppress noise from tiny caseloads
    g["recognition_rate"] = g["rec"] / g["denom"]
    return g.rename(columns={"coo_iso": "iso3"})[
        ["iso3", "recognition_rate", "denom"]]


def main():
    import glob
    print("ACLED ...")
    acled = load_acled(sorted(glob.glob(os.path.join(UP, "*aggregated_data*.xlsx"))))
    print(f"  {len(acled):,} rows, {acled.iso3.nunique()} countries")

    print("IDMC ...")
    # IDMC's export filenames carry a per-download hash prefix, so pinning one
    # name means the next person's download - or an all-years re-export, which is
    # the single highest-value input still missing - silently does not load.
    # Take the newest GIDD disaggregated file present, whatever it is called.
    gidd = sorted(glob.glob(os.path.join(UP, "*GIDD*Disaggregated*.xlsx")))
    if not gidd:
        raise FileNotFoundError(
            f"No IDMC GIDD disaggregated export in {UP}. Download the "
            f"'Disaggregated data' export, ALL YEARS, from "
            f"https://www.internal-displacement.org/database/ and drop it there.")
    if len(gidd) > 1:
        print(f"  {len(gidd)} GIDD exports present, using the newest: "
              f"{os.path.basename(gidd[-1])}")
    idmc, idmc_detail = load_idmc(gidd[-1])
    print(f"  {len(idmc):,} rows, {idmc.iso3.nunique()} countries")

    print("UCDP one-sided ...")
    ucdp = load_ucdp_onesided(os.path.join(UP, "ucdp_onesided/OneSided_v26_1.xlsx"))
    print(f"  {len(ucdp):,} rows, {ucdp.iso3.nunique()} countries")

    print("UNHCR ...")
    pop = load_unhcr_population(os.path.join(RAW, "PopulationStatistics_population.rda"))
    dec = load_unhcr_decisions(os.path.join(RAW, "PopulationStatistics_asylum_decisions.rda"))
    rr = recognition_rate_by_origin(dec)
    print(f"  population {len(pop):,} rows; recognition rates for {len(rr)} origins")

    evidence = pd.concat([acled, idmc, ucdp], ignore_index=True)
    os.makedirs((TIDY_S), exist_ok=True)
    T = (TIDY_S)
    evidence.to_parquet(f"{T}/evidence_long.parquet", index=False)
    idmc_detail.to_parquet(f"{T}/idmc_detail.parquet", index=False)
    pop.to_parquet(f"{T}/unhcr_population.parquet", index=False)
    rr.to_parquet(f"{T}/unhcr_recognition.parquet", index=False)
    print(f"\nwrote evidence_long: {len(evidence):,} rows -> {T}")
    print(evidence.groupby(["source", "evidence_type"]).size().to_string())


if __name__ == "__main__":
    main()

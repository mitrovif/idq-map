"""
Country cause-profiles and showcard recommendations.

For every country this answers: which of the 8 response options does the
evidence support putting in front of respondents here, and what LOCAL EXAMPLES
should the enumerator support screen give for each one?

Two distinct perspectives are combined, because a household survey in country X
enumerates two different displaced populations whose causing events happened in
different places:

  DOMESTIC  - IDPs displaced by events inside X. Evidence: IDMC + ACLED + UCDP for X.
  ORIGIN    - refugees hosted by X, displaced by events in their origin countries.
              Evidence: the same, but for X's main origin countries, weighted by
              how much of X's refugee population each origin supplies.

Uganda is the canonical case: nothing about Ugandan events tells you what
belongs on a Ugandan showcard, because ~95% of the people the questions must
identify were displaced from South Sudan and DR Congo.
"""
from paths import ROOT_S, RAW_S, UP_S, TIDY_S, OUT_S, TOPO_S
import os, json
import pandas as pd
import numpy as np

T = TIDY_S
OUT = OUT_S
os.makedirs(OUT, exist_ok=True)

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
RESIDUAL = {5, 8}
UNATTRIBUTED = 0   # IDMC conflict displacement with no violence type recorded.
                   # Counted in every denominator, never assigned to an option.
BLIND = {3, 4, 7}          # data known to be blind: never recommend removal

DOMESTIC_THRESHOLD = 0.05
ORIGIN_THRESHOLD = 0.05
MIN_HOSTED_FOR_ORIGIN_WEIGHTING = 5000   # refugees+asylum seekers hosted
MIN_ORIGIN_N = 1000                      # people from a given origin
EVENT_MIN_SHARE = 0.02
EVENT_MIN_COUNT = 10
RECOGNITION_MIN = 0.50
RECOGNITION_MIN_N = 1000
GOV_FATALITY_MIN = 100

ev = pd.read_parquet(f"{T}/evidence_long.parquet")
idmc_detail = pd.read_parquet(f"{T}/idmc_detail.parquet")
pop = pd.read_parquet(f"{T}/unhcr_population.parquet")
rr = pd.read_parquet(f"{T}/unhcr_recognition.parquet")
IDMC_YEAR = int(idmc_detail["year"].max())

LATEST = int(pop["year"].max())
ACLED_FROM = 2018
ACLED_FROM = 2018   # common window across the two regional exports

# ---------------------------------------------------------------- 1. domestic
# displacement-weighted shares from IDMC (people actually displaced, by cause)
disp = (ev[(ev.evidence_type == "displaced")]
        .groupby(["iso3", "code_id"], as_index=False)["value"].sum())
disp_tot = disp.groupby("iso3", as_index=False)["value"].sum().rename(
    columns={"value": "total"})
disp = disp.merge(disp_tot, on="iso3")
disp["domestic_share"] = disp["value"] / disp["total"].replace(0, np.nan)

# event-occurrence evidence from ACLED (does the cause happen here at all)
evt = (ev[(ev.evidence_type == "events") & (ev.year >= ACLED_FROM)]
       .groupby(["iso3", "code_id"], as_index=False)["value"].sum()
       .rename(columns={"value": "events"}))
evt_tot = evt.groupby("iso3", as_index=False)["events"].sum().rename(
    columns={"events": "events_total"})
evt = evt.merge(evt_tot, on="iso3")
evt["event_share"] = evt["events"] / evt["events_total"].replace(0, np.nan)

# state-perpetrator lethal repression from UCDP one-sided (code 4)
ucdp4 = (ev[(ev.source.str.startswith("UCDP")) & (ev.code_id == 4)]
         .groupby("iso3", as_index=False)["value"].sum()
         .rename(columns={"value": "ucdp_gov_fatalities"}))

# ------------------------------------------------------- 2. UNHCR stocks/flows
latest_pop = pop[pop.year == LATEST]
hosted = (latest_pop.groupby("coa_iso", as_index=False)
          .agg(refugees=("refugees", "sum"),
               asylum_seekers=("asylum_seekers", "sum"),
               idps=("idps", "sum"))
          .rename(columns={"coa_iso": "iso3"}))
hosted["refugee_pop"] = hosted["refugees"] + hosted["asylum_seekers"]

origin_mix = latest_pop.copy()
origin_mix["n"] = origin_mix["refugees"] + origin_mix["asylum_seekers"]
origin_mix = origin_mix[(origin_mix.n > 0) & (origin_mix.coo_iso != origin_mix.coa_iso)]
origin_mix = origin_mix.groupby(["coa_iso", "coo_iso", "coo_name"],
                                as_index=False)["n"].sum()
tot_by_coa = origin_mix.groupby("coa_iso", as_index=False)["n"].sum().rename(
    columns={"n": "n_total"})
origin_mix = origin_mix.merge(tot_by_coa, on="coa_iso")
origin_mix["share"] = origin_mix["n"] / origin_mix["n_total"]

# ------------------------------------------- 3. local examples for the showcard
FLOW = "Internal Displacements"

def hazard_examples(iso3, top=3):
    d = idmc_detail[(idmc_detail.iso3 == iso3) & (idmc_detail.code_id == 6)
                    & (idmc_detail.category == FLOW)]
    if d.empty:
        return []
    g = d.groupby("hazard_sub_type")["figures"].sum().sort_values(ascending=False)
    return [f"{k} ({int(v):,} displaced)" for k, v in g.head(top).items() if v > 0]

def violence_examples(iso3, code, top=3):
    d = idmc_detail[(idmc_detail.iso3 == iso3) & (idmc_detail.code_id == code)
                    & (idmc_detail.category == FLOW)]
    if d.empty:
        return []
    g = d.groupby("violence_type")["figures"].sum().sort_values(ascending=False)
    pretty = {"Unclear/Unknown": "conflict, type not specified by IDMC",
              "Non-International armed conflict (NIAC)": "non-international armed conflict",
              "International armed conflict (IAC)": "international armed conflict",
              "Other situations of violence (OSV)": "other situations of violence"}
    return [f"{pretty.get(k, k)} ({int(v):,} displaced)"
            for k, v in g.head(top).items() if v > 0]

acled_sub = None   # populated lazily for event-type examples

def build_profile(iso3):
    """Return dict: code_id -> {status, domestic_share, origin_share, evidence, examples}"""
    dsh = disp[disp.iso3 == iso3].set_index("code_id")["domestic_share"].to_dict()
    dval = disp[disp.iso3 == iso3].set_index("code_id")["value"].to_dict()
    esh = evt[evt.iso3 == iso3].set_index("code_id")["event_share"].to_dict()
    ecnt = evt[evt.iso3 == iso3].set_index("code_id")["events"].to_dict()
    has_idmc = iso3 in set(disp.iso3)
    has_acled = iso3 in set(evt.iso3)

    # origin-weighted shares
    _h = hosted[hosted.iso3 == iso3]
    _hosted_n = float(_h.refugee_pop.iloc[0]) if len(_h) else 0.0
    if _hosted_n >= MIN_HOSTED_FOR_ORIGIN_WEIGHTING:
        om = origin_mix[(origin_mix.coa_iso == iso3) &
                        (origin_mix.share >= ORIGIN_THRESHOLD) &
                        (origin_mix.n >= MIN_ORIGIN_N)]
    else:
        om = origin_mix.iloc[0:0]
    osh = {c: 0.0 for c in list(CODES) + [UNATTRIBUTED]}
    for _, r in om.iterrows():
        od = disp[disp.iso3 == r.coo_iso].set_index("code_id")["domestic_share"].to_dict()
        for c, v in od.items():
            if pd.notna(v):
                osh[c] += r.share * v

    # code 3 proxy
    r3 = rr[rr.iso3 == iso3]
    rec_rate = float(r3.recognition_rate.iloc[0]) if len(r3) else np.nan
    rec_n = int(r3.denom.iloc[0]) if len(r3) else 0
    # origin-weighted recognition rate: are the people hosted here from
    # origins whose claims are widely recognised as persecution?
    ow_rec, ow_w = 0.0, 0.0
    for _, r in om.iterrows():
        rr_o = rr[rr.iso3 == r.coo_iso]
        if len(rr_o):
            ow_rec += r.share * float(rr_o.recognition_rate.iloc[0]); ow_w += r.share
    ow_rec = ow_rec / ow_w if ow_w > 0 else np.nan

    g4 = ucdp4[ucdp4.iso3 == iso3]
    gov_fat = float(g4.ucdp_gov_fatalities.iloc[0]) if len(g4) else 0.0

    unattributed = dsh.get(UNATTRIBUTED, 0.0) or 0.0
    out = {"unattributed": dict(share=round(float(unattributed), 4),
                                people=int(dval.get(UNATTRIBUTED, 0)))}
    for c in CODES:
        d_s = dsh.get(c, 0.0 if has_idmc else np.nan)
        o_s = osh.get(c, 0.0)
        e_s = esh.get(c, 0.0 if has_acled else np.nan)
        e_n = ecnt.get(c, 0)
        reasons, examples = [], []

        if c in RESIDUAL:
            status = "RESIDUAL"
            reasons.append("Residual code - retained on every show card by design")
        else:
            supported = False
            if pd.notna(d_s) and d_s >= DOMESTIC_THRESHOLD:
                supported = True
                reasons.append(f"{d_s:.0%} of internal displacement in-country "
                               f"({int(dval.get(c,0)):,} people, IDMC {IDMC_YEAR})")
            if o_s >= ORIGIN_THRESHOLD:
                supported = True
                reasons.append(f"{o_s:.0%} origin-weighted - refugees hosted here "
                               f"come from countries where this is a major cause")
            if pd.notna(e_s) and e_s >= EVENT_MIN_SHARE and e_n >= EVENT_MIN_COUNT:
                supported = True
                reasons.append(f"{int(e_n):,} ACLED events {ACLED_FROM}+ "
                               f"({e_s:.0%} of political-violence events here)")
            if c == 3:
                if pd.notna(rec_rate) and rec_rate >= RECOGNITION_MIN and rec_n >= RECOGNITION_MIN_N:
                    supported = True
                    reasons.append(f"{rec_rate:.0%} asylum recognition rate for people "
                                   f"originating here ({rec_n:,} decisions) - the "
                                   f"protection system judges these claims well-founded")
                if pd.notna(ow_rec) and ow_rec >= RECOGNITION_MIN:
                    supported = True
                    reasons.append(f"{ow_rec:.0%} origin-weighted recognition rate for "
                                   f"the refugee population hosted here")
            if c == 4 and gov_fat >= GOV_FATALITY_MIN:
                supported = True
                reasons.append(f"{int(gov_fat):,} civilian deaths attributed to state "
                               f"forces, UCDP one-sided 1989-2025")

            if supported:
                status = "RECOMMENDED"
            elif (not has_idmc and not has_acled) or c in BLIND:
                status = "UNEVIDENCED"
                if c in BLIND:
                    reasons.append("No supporting evidence found, but global data is "
                                   "structurally blind to this cause - retain and test "
                                   "in cognitive interviews")
                else:
                    reasons.append("No source covers this country")
            else:
                status = "LOW_SALIENCE"
                reasons.append("Sources cover this country and show little or no "
                               "displacement from this cause - candidate for "
                               "de-emphasis in enumerator support material only")

        if c == 6:
            examples = hazard_examples(iso3)
            for _, r in om.head(3).iterrows():
                ex = hazard_examples(r.coo_iso, top=2)
                if ex:
                    examples += [f"[via {r.coo_name} refugees] {e}" for e in ex]
        elif c in (1, 2):
            examples = violence_examples(iso3, c)
            for _, r in om.head(3).iterrows():
                ex = violence_examples(r.coo_iso, c, top=1)
                if ex:
                    examples += [f"[via {r.coo_name} refugees] {e}" for e in ex]

        out[c] = dict(status=status,
                      domestic_share=None if pd.isna(d_s) else round(float(d_s), 4),
                      origin_share=round(float(o_s), 4),
                      event_share=None if pd.isna(e_s) else round(float(e_s), 4),
                      event_count=int(e_n),
                      displaced=int(dval.get(c, 0)),
                      reasons=reasons, examples=examples[:5])
    return out, om, dict(recognition_rate=rec_rate, recognition_n=rec_n,
                         ow_recognition=ow_rec, gov_fatalities=gov_fat)


def main():
    # ------------------------------------------------------------------- 4. run all
    universe = sorted(set(disp.iso3) | set(evt.iso3) |
                      set(hosted[hosted.refugee_pop > 1000].iso3.dropna()))
    print(f"building profiles for {len(universe)} countries ...")

    import pycountry
    def cname(iso):
        try:
            return pycountry.countries.get(alpha_3=iso).name
        except Exception:
            return iso

    records, payload = [], {}
    for iso in universe:
        prof, om, extra = build_profile(iso)
        h = hosted[hosted.iso3 == iso]
        idp = float(h.idps.iloc[0]) if len(h) else 0.0
        ref = float(h.refugee_pop.iloc[0]) if len(h) else 0.0
        payload[iso] = dict(
            iso3=iso, name=cname(iso), idps=idp, refugees_hosted=ref,
            codes={str(k): v for k, v in prof.items() if k != "unattributed"},
            unattributed=prof["unattributed"],
            origins=[dict(iso3=r.coo_iso, name=r.coo_name, share=round(r.share, 4),
                          n=int(r.n)) for _, r in om.head(6).iterrows()],
            extra={k: (None if (isinstance(v, float) and pd.isna(v)) else v)
                   for k, v in extra.items()},
            coverage=dict(idmc=iso in set(disp.iso3), acled=iso in set(evt.iso3),
                          unhcr=len(h) > 0))
        for c, v in prof.items():
            if c == "unattributed":
                continue
            records.append(dict(iso3=iso, country=cname(iso), code_id=c,
                                code_label=CODES[c], status=v["status"],
                                domestic_share=v["domestic_share"],
                                origin_share=v["origin_share"],
                                event_count=v["event_count"],
                                displaced=v["displaced"],
                                idps_total=idp, refugees_hosted=ref,
                                rationale=" | ".join(v["reasons"]),
                                local_examples="; ".join(v["examples"])))

    tab = pd.DataFrame(records)
    tab.to_csv(f"{OUT}/showcard_recommendations.csv", index=False)
    with open(f"{OUT}/profiles.json", "w") as f:
        json.dump(payload, f)

    print(tab.status.value_counts().to_string())
    print(f"\nwrote {len(tab):,} country-code rows -> {OUT}")


if __name__ == "__main__":
    main()

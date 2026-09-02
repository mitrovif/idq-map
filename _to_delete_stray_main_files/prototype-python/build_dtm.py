"""
IOM DTM: what displaced people say, as opposed to what a monitor could observe.

This is a DIFFERENT CLASS OF EVIDENCE from everything else in this project and is
never mixed with it. UCDP sees deaths. IDMC sees movement. ACLED sees incidents.
All three are an analyst's reading of an event. DTM asks the household. It is the
only external check on whether the crosswalk matches how people actually describe
why they left - which is the question cognitive testing is about to put directly.

TWO THINGS THE RAW FIELD DOES THAT HAVE TO BE HANDLED
  composites   "Conflict; Insecurity; Natural disaster" is one string covering
               three causes. Splitting on ";" is not optional - Libya reports up
               to five at once, and treating the whole string as one unmatched
               category would throw the country away.
  case         "Natural disaster" and "Natural Disaster" both appear, from the
               same field, sometimes in the same country.

WHAT THE VOCABULARY DOES NOT CONTAIN, WHICH IS THE FINDING
DTM's reason list has no option for persecution, for discrimination, or for
human rights violations by authorities. The nearest is "Political reasons",
which appears in one country. So options 3 and 4 are not merely uncounted in the
administrative record - they are absent from the answer list people were offered
in the field. That is a much stronger claim than "the data is thin", and it is
an argument for the EGRISS questions rather than against them.

Run fetch_dtm.py on a machine with network access first; see that file for why.
"""
from paths import RAW, TIDY_S, OUT_S
import glob
import json
import os
import re

import pandas as pd

TIDY = TIDY_S
OUT = OUT_S
DTM_DIR = RAW / "dtm"

# DTM reason -> identification-question response option.
# The vocabulary is NOT globally standardised; these are the values actually
# observed across the twenty countries pulled, normalised to lower case.
REASON_TO_CODE = {
    # ---- 1: armed conflict or war -------------------------------------
    "conflict": 1,
    "conflict/violence": 1,
    "armed conflict": 1,
    "war": 1,
    "military operations": 1,
    # ---- 2: widespread violence / breakdown of public order -----------
    # DTM offers "Insecurity" as a SEPARATE option from "Conflict", and
    # respondents pick between them. That distinction is close to the one the
    # questionnaire draws between options 1 and 2, and is the best evidence we
    # have that respondents can in fact tell them apart.
    "insecurity": 2,
    "social tension": 2,
    "communal violence": 2,
    "criminality": 2,
    "gang violence": 2,
    # ---- 3 / 4: persecution, and violations by authorities ------------
    # "Political reasons" is the closest DTM comes to either. It is coded to 3
    # rather than 4 because it describes why the person was targeted, not who
    # did it - but this is a judgement, it is thin, and it is flagged as such
    # wherever it appears.
    "political reasons": 3,
    # ---- 6: natural disasters -----------------------------------------
    "natural disaster": 6,
    "disaster": 6,
    "flood": 6, "drought": 6, "cyclone": 6, "earthquake": 6,
    # ---- 8 / not a valid cause ----------------------------------------
    # Economic reasons and livelihood are NOT causes of forced displacement
    # under IRIS. Mapped to None deliberately, not dropped silently: DTM counts
    # these people as IDPs, and the gap between DTM's population and the
    # questionnaire's is itself worth reporting.
    "economic reasons": None,
    "economic": None,
    "livelihood": None,
    "other reason": 8,
    "no reason for displacement reported": 0,
}

UNMAPPED = "__unmapped__"

# DTM ships two spellings of the same country - "Democratic Republic of the
# Congo" and "Democratic Republic of The Congo" - which silently became two
# countries, each with its own "latest round", so the caseload was split and
# the snapshot date differed between halves. Everything is resolved to ISO3
# before any grouping happens.
ALIAS = {
    "democratic republic of the congo": "COD",
    "congo dr": "COD", "dr congo": "COD",
    "central african republic": "CAF",
    "south sudan": "SSD",
    "burkina faso": "BFA",
    "united republic of tanzania": "TZA",
    "syrian arab republic": "SYR",
    "state of palestine": "PSE",
    "cote d ivoire": "CIV", "ivory coast": "CIV",
}


def to_iso3(name, lookup):
    if not isinstance(name, str):
        return None
    k = re.sub(r"[^a-z ]+", " ", name.lower()).strip()
    k = re.sub(r"\s+", " ", k)
    if k in ALIAS:
        return ALIAS[k]
    if k in lookup:
        return lookup[k]
    # last resort: unique substring match against the reference list
    hits = [v for n, v in lookup.items() if k and (k in n or n in k)]
    return hits[0] if len(set(hits)) == 1 else None


def split_reasons(s):
    """'Conflict; Insecurity; Natural disaster' -> three reasons.

    Semicolon only. "Conflict/violence" is a single DTM category and splitting
    it on the slash invents a reason called "violence" carrying 3.6m people.
    """
    if not isinstance(s, str) or not s.strip():
        return []
    return [p.strip().lower() for p in s.split(";") if p.strip()] or []


def load():
    files = sorted(glob.glob(str(DTM_DIR / "idp_admin0_*.csv")))
    if not files:
        raise FileNotFoundError(
            f"No DTM files in {DTM_DIR}. Run prototype-python/fetch_dtm.py on a "
            f"machine with network access, then copy dtm_data/*.csv there.")
    frames = []
    for f in files:
        d = pd.read_csv(f)
        if "displacementReason" not in d.columns:
            continue
        d["_file"] = os.path.basename(f)
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def main():
    d = load()
    d["reportingDate"] = pd.to_datetime(d.reportingDate, errors="coerce")
    d["year"] = d.reportingDate.dt.year

    ref = {re.sub(r"\s+", " ", re.sub(r"[^a-z ]+", " ", r["name"].lower())).strip():
           r["iso_code"] for r in json.load(open(f"{TIDY}/regions.json"))}
    d["iso3"] = [to_iso3(n, ref) for n in d.admin0Name]
    lost = d[d.iso3.isna()].admin0Name.unique()
    if len(lost):
        print(f"  could not resolve to ISO3, dropped: {list(lost)}")
    d = d[d.iso3.notna()].copy()

    # One reading per country: the latest reporting date. DTM rounds are
    # cumulative snapshots of the same caseload, so summing rounds would count
    # the same people once per round - in Sudan's case 1,262 times.
    d = d.merge(d.groupby("iso3").reportingDate.max().rename("_max"), on="iso3")
    cur = d[d.reportingDate == d._max].copy()

    rows, unmapped = [], {}
    for r in cur.itertuples():
        people = float(getattr(r, "numPresentIdpInd", 0) or 0)
        parts = split_reasons(r.displacementReason)
        if not parts:
            continue
        # A composite reason gives no basis for splitting the people between
        # its parts, so each named cause is credited with the whole figure and
        # the row is flagged. Shares therefore sum above 100% where composites
        # are common, which is stated wherever they are shown.
        for p in parts:
            code = REASON_TO_CODE.get(p, UNMAPPED)
            if code is UNMAPPED:
                unmapped[p] = unmapped.get(p, 0) + people
                continue
            rows.append(dict(iso3=r.iso3, country=r.admin0Name, reason=p, code_id=code,
                             people=people, composite=len(parts) > 1,
                             date=r.reportingDate, round=getattr(r, "roundNumber", None)))

    t = pd.DataFrame(rows)
    if unmapped:
        print("  UNMAPPED reason values (add to REASON_TO_CODE if real):")
        for k, v in sorted(unmapped.items(), key=lambda kv: -kv[1]):
            print(f"    {k!r:<46} {v:>12,.0f} people")

    t["country"] = t.groupby("iso3").country.transform("first")  # one spelling
    agg = (t.groupby(["iso3", "country", "code_id"], dropna=False)
             .agg(people=("people", "sum"),
                  composite=("composite", "any")).reset_index())
    tot = agg.groupby("iso3").people.sum().rename("country_total")
    agg = agg.merge(tot, on="iso3")
    agg["share"] = agg.people / agg.country_total

    agg.to_parquet(f"{TIDY}/dtm_reported.parquet", index=False)
    t.to_parquet(f"{TIDY}/dtm_reported_detail.parquet", index=False)

    LAB = {0: "unreported", 1: "armed conflict", 2: "widespread violence",
           3: "persecution / political", 4: "HR violations", 5: "other violence",
           6: "natural disaster", 7: "man-made", 8: "other reason",
           9: "no source covers it"}
    print(f"\nwrote {len(agg)} country x code rows for {agg.iso3.nunique()} countries")
    print(f"  {t.people.sum():,.0f} people-reasons, "
          f"{t[t.composite].people.sum():,.0f} of them from composite answers")
    print("\nWhat displaced people themselves report, latest round per country:")
    glob_share = agg.groupby("code_id").people.sum()
    for c, v in glob_share.sort_values(ascending=False).items():
        pct = 100 * v / glob_share.sum()
        print(f"   {LAB.get(int(c), c):<26} {v:>12,.0f}  ({pct:4.1f}%)")
    # ---- the reality check ------------------------------------------------
    # The only external test of the crosswalk: put what people said beside what
    # we inferred, for the same country. Written out so it can be read as a
    # table rather than reconstructed from the map.
    prof = f"{OUT}/profiles.json"
    cmp_rows = []
    if os.path.exists(prof):
        P = json.load(open(prof))
        for iso, g in agg.groupby("iso3"):
            p_ = P.get(iso)
            if not p_:
                continue
            att = {int(k): float(v.get("displaced") or 0)
                   for k, v in (p_.get("codes") or {}).items()}
            unatt = float((p_.get("unattributed") or {}).get("people") or 0)
            if unatt > 0:
                att[0] = att.get(0, 0) + unatt
            tot_a = sum(att.values())
            if tot_a < 1000:
                continue
            rep = {int(r.code_id): r.share for r in g.itertuples()
                   if pd.notna(r.code_id)}
            a = {k: v / tot_a for k, v in att.items() if v > 0}
            top_r = max(rep, key=rep.get) if rep else None
            top_a = max(a, key=a.get) if a else None
            cmp_rows.append(dict(
                iso3=iso, country=g.country.iloc[0],
                reported_top=top_r, reported_share=rep.get(top_r),
                attributed_top=top_a, attributed_share=a.get(top_a),
                agree=(top_r == top_a),
                dtm_people=float(g.people.sum()), attributed_people=float(tot_a),
                economic_share=float(g[g.code_id.isna()].people.sum() / max(g.people.sum(), 1)),
            ))
        cmp = pd.DataFrame(cmp_rows)
        if cmp.empty:
            print("\n  reported vs attributed: no overlap between DTM's countries "
                  "and the attributed profiles — nothing to compare")
            cmp = pd.DataFrame(columns=["iso3", "country", "agree"])
        cmp.to_csv(f"{OUT}/dtm_reported_vs_attributed.csv", index=False)
        # Not every disagreement means the crosswalk is wrong, and conflating
        # the two kinds would put a false claim in the paper.
        #   BOUNDARY  both sides picked a violence option, but a different one.
        #             This IS a crosswalk finding: it is the 1-vs-2 distinction
        #             the questionnaire asks respondents to draw, and it is
        #             exactly what cognitive testing has to probe.
        #   CASELOAD  one side says violence, the other disaster. Usually not a
        #             coding disagreement at all - DTM tracks a protracted
        #             conflict caseload while the IDMC file loaded here covers
        #             2025 flows, which are disaster-weighted. Different people,
        #             not different labels.
        VIOL = {1, 2, 3, 4, 5}
        def kind(r):
            a, b = r["reported_top"], r["attributed_top"]
            if a == b:
                return "agree"
            if a in VIOL and b in VIOL:
                return "boundary"
            if a == 0 or b == 0:
                return "unreported"
            return "caseload"
        cmp["disagreement"] = [kind(r) for _, r in cmp.iterrows()]
        cmp.to_csv(f"{OUT}/dtm_reported_vs_attributed.csv", index=False)

        n_ok = int((cmp.disagreement == "agree").sum())
        print(f"\n  reported vs attributed: {n_ok} of {len(cmp)} countries agree "
              f"on the dominant cause")
        for k, title in (("boundary",
                          "WHICH VIOLENCE OPTION — a crosswalk finding, and the "
                          "distinction the questions ask respondents to draw"),
                         ("caseload",
                          "violence vs disaster — usually different caseloads, "
                          "not different labels: DTM tracks protracted conflict "
                          "displacement, the IDMC file here covers 2025 flows"),
                         ("unreported",
                          "one side has no cause recorded at all")):
            sub = cmp[cmp.disagreement == k]
            if not len(sub):
                continue
            print(f"\n  {title}")
            for r in sub.itertuples():
                print(f"    {r.country[:24]:<25} people said "
                      f"{LAB.get(r.reported_top, r.reported_top)} "
                      f"({100*r.reported_share:.0f}%), we attributed "
                      f"{LAB.get(r.attributed_top, r.attributed_top)} "
                      f"({100*r.attributed_share:.0f}%)")

    miss = [x for x in (3, 4, 5, 7) if x not in set(agg.code_id)]
    print(f"\n  Response options with NO DTM evidence anywhere: {miss}")
    print("  DTM's answer list has no option for discrimination, persecution or")
    print("  human rights violations by authorities. Options 3 and 4 are absent")
    print("  from what people were ASKED, not just from what was recorded.")


if __name__ == "__main__":
    main()

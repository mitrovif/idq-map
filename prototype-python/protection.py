"""
Country-specific names for the international protection question.

WHY THIS IS THE SAME KIND OF WORK AS build_questions.py, AND WHERE IT DIFFERS
The forced-to-flee item localises its EXAMPLES while the response options stay
fixed. The international protection item has the same shape and the same
permission: the desk review records that the original wording "does not provide
any examples of what is meant by the phrase 'apply for international
protection'", that cognitive interviews found the phrase poorly understood, and
that pilots have already introduced localised probes of exactly the form
"did you go to an office like (host country local example) to register".

So this module drafts that local example for each country, in two versions the
instrument can carry:

    v1  the OFFICE   "...did you go to an office like <name> to register?"
    v2  the DOCUMENT "...did you apply for a document like <name>?"

It does double duty for the legal-document item, whose response categories the
desk review says "should be customized to each survey context" - doc_pending and
doc_recognised are that customisation.

THE ONE RULE THE CURATION FOLLOWS
Name where the claim is LODGED, never who adjudicates it. This is not pedantry.
An automated first pass ranked by keyword and put Kenya's Refugee Status
Eligibility Panel ahead of DRS, and Egypt's Passports and Immigration
Administration ahead of UNHCR - bodies a respondent never went near. Eligibility
panels, appeals boards, tribunals, hotlines and partner NGOs that do not
themselves register are excluded throughout.

THREE THINGS THAT MAKE THIS A DRAFT AND NOT A DELIVERABLE
  1. The sources describe the procedure as it stands TODAY; the question asks
     about a respondent's lifetime. Kenya's RAS->DRS rename, Lebanon's suspension
     since 2015, Turkiye's end of UNHCR mandate RSD in 2018 and Pakistan's frozen
     registration are recorded in `caveat` where a page printed them, but this is
     not a systematic historical record.
  2. v1 does not travel. In 110 of 151 countries the claim is lodged online, by
     e-mail, by post, at a police station, or happens automatically - see
     `reword_v1` and `channel`. Peru grants complementary protection
     automatically and Denmark's appeal to the Refugee Appeals Board is
     automatic: there, no "did you do something" question works at all.
  3. Confidence is HIGH for 55 countries, MEDIUM for 59, LOW for 37. The LOW rows
     are almost entirely small Pacific and Caribbean states. Check MEDIUM and LOW
     against a country source before fielding.

WHAT IS DELIBERATELY ABSENT
Internal displacement. Of 29 major contexts checked, only Ukraine, Colombia,
Georgia, Bosnia and Azerbaijan have a verifiable IDP status document; all 16
African and Asian contexts have none. Where a card exists it is an assistance
token (Philippines DAFAC, Pakistan Watan Card, Mali carte de ration) or an
ordinary civil document. Somalia's own policy states it "does not provide for a
general registration of IDPs". That is a finding about the instruments, not a
gap in the search, and v2 has no valid fill for those countries.

Colour names are kept separate from formal titles because they are usually the
better prompt - Egypt's yellow and blue cards, Spain's Tarjeta Roja, Greece's
pink card. Kenya's "pink slip" is a birth notification and Myanmar's Pink, Blue
and Green cards are citizenship documents; both would false-positive the general
population and neither is carried.

Self-contained: reads one committed JSON and needs none of data/, so it runs on
a clean checkout. `python3 protection.py` prints a summary and self-checks.
"""
from paths import ROOT
import json

DATA = ROOT / "config" / "protection_context.json"

# Version 1 and 2 of the probe. The stem never varies - only the name inside it,
# exactly as with the forced-to-flee examples.
PROBE_OFFICE = "For example, did you go to an office like {name} to register?"
PROBE_DOC = "For example, did you apply for a document like {name}?"

REGISTRAR_LABEL = {"GOVERNMENT": "Government", "UNHCR": "UNHCR",
                   "BOTH": "Both", "NONE": "Nobody"}


def load():
    """The curated record for every country, keyed by ISO3."""
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)["countries"]


def probes(rec):
    """The two drafted probes for one country, or None where the name is missing.

    Returning None rather than a probe with an empty slot is the point: a
    country with no nameable registrar cannot carry v1, and saying so is more
    useful to the task team than a sentence with a hole in it.
    """
    office = PROBE_OFFICE.format(name=rec["office"]) if rec["office"] else None
    doc_name = rec["doc_pending"] or rec["doc_recognised"]
    doc = PROBE_DOC.format(name=doc_name) if doc_name else None
    return {"office": office, "document": doc}


def question_payload():
    """Per-country payload for the questions page."""
    out = {}
    for iso, r in load().items():
        p = probes(r)
        out[iso] = {
            "c": r["country"], "reg": r["registrar"], "how": r["channel"],
            "org": r["office"], "orgL": r["office_local"], "alt": r["office_alt"],
            "ow": r["office_why"],
            "da": r["doc_pending"], "daL": r["doc_pending_local"],
            "daC": r["doc_pending_colloquial"],
            "dr": r["doc_recognised"], "drL": r["doc_recognised_local"],
            "drC": r["doc_recognised_colloquial"],
            "dw": r["doc_why"], "cav": r["caveat"], "cf": r["confidence"],
            "mis": r["reword_v1"], "cols": r["colours"],
            "v1": p["office"], "v2": p["document"],
        }
    return out


def map_payload():
    """Three layers for the existing world map, in the shape draw() expects.

    `office`   who takes the application  - categorical
    `doc`      what is issued, by stage   - ordinal, 2 / 1 / 0
    `ask`      whether v1 survives here   - status
    """
    recs, office, doc, ask, colours = load(), {}, {}, {}, {}
    for iso, r in recs.items():
        office[iso] = r["registrar"]
        n = bool(r["doc_pending"]) + bool(r["doc_recognised"])
        doc[iso] = str(n)
        ask[iso] = ("no" if (r["registrar"] == "NONE" or not r["office"])
                    else "reword" if r["reword_v1"] else "ok")
        if r["colours"]:
            colours[iso] = r["colours"]
    return {"office": office, "doc": doc, "ask": ask, "colours": colours,
            "names": {iso: r["country"] for iso, r in recs.items()},
            "docnames": {iso: [r["doc_pending_colloquial"] or r["doc_pending"],
                               r["doc_recognised_colloquial"] or r["doc_recognised"]]
                         for iso, r in recs.items()},
            "orgnames": {iso: r["office"] for iso, r in recs.items()}}


def _selfcheck():
    recs = load()
    assert len(recs) == 151, f"expected 151 countries, got {len(recs)}"
    for iso, r in recs.items():
        assert len(iso) == 3, f"bad ISO3 {iso!r}"
        assert r["registrar"] in REGISTRAR_LABEL, f"{iso}: bad registrar"
        assert r["confidence"] in ("HIGH", "MEDIUM", "LOW"), f"{iso}: bad confidence"
    m = map_payload()
    assert set(m["office"]) == set(recs), "map payload lost countries"
    return recs, m


if __name__ == "__main__":
    recs, m = _selfcheck()
    reg = {}
    for r in recs.values():
        reg[r["registrar"]] = reg.get(r["registrar"], 0) + 1
    cf = {}
    for r in recs.values():
        cf[r["confidence"]] = cf.get(r["confidence"], 0) + 1
    named_v1 = sum(1 for r in recs.values() if r["office"])
    named_v2 = sum(1 for r in recs.values() if r["doc_pending"] or r["doc_recognised"])
    both = sum(1 for r in recs.values() if r["doc_pending"] and r["doc_recognised"])
    print(f"{len(recs)} countries")
    print(f"  registrar   {reg}")
    print(f"  confidence  {cf}")
    print(f"  v1 nameable {named_v1}   v2 nameable {named_v2}   both stages {both}")
    print(f"  reword v1   {sum(1 for r in recs.values() if r['reword_v1'])}")
    print(f"  colour-named documents  {len(m['colours'])}")
    print()
    for iso in ("KEN", "EGY", "PER"):
        p = probes(recs[iso])
        print(f"{recs[iso]['country']}  [{recs[iso]['confidence']}]")
        print(f"   v1  {p['office'] or '— no organization can be named'}")
        print(f"   v2  {p['document'] or '— no document can be named'}")
        if recs[iso]["reword_v1"]:
            print(f"   !!  reword v1: {recs[iso]['channel'][:88]}")
    print("\nself-check passed")

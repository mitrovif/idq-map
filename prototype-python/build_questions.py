"""
Country-specific examples for the "forced to flee" question.

WHY THIS IS LEGITIMATE, AND WHERE ITS LIMIT IS
The response options must be identical in every country or IRIS comparability is
gone. The EXAMPLES after "e.g." are a different matter: the question variants
document states "LOCALISATION OF EXAMPLES PERMITTED" for the follow-up item, and
the desk review supplement finds that when examples were withheld, participants
"showed a general lack of familiarity with concepts such as discrimination and
property rights", concluding that "if enumerators do not read out the examples,
respondents may fail to identify any qualifying event".

So the examples are load-bearing, and they are the one part of the instrument
that is allowed to vary. This module drafts them from what actually happened in
each country.

WHAT VERSION 3 CURRENTLY OFFERS, AND WHERE THE GAPS ARE
  1 armed conflict or war ................ NO examples at all
  2 widespread violence / public order ... NO examples at all
  3 discrimination or persecution ........ generic, and no event source exists
  4 HR violations by authorities ......... generic (detention, torture)
  5 other threats of violence ............ NO examples at all
  6 natural disasters .................... generic global list of five hazards
  7 man-made events ...................... generic (eviction, pollution)
Three options carry no examples, and those three are exactly the ones the event
data is strongest on. Option 6's generic list names hazards that do not occur in
most countries, while omitting the one that does.

THREE THINGS THAT MAKE THIS A DRAFT AND NOT A DELIVERABLE
  1. The names are UCDP's, not a respondent's. "JAS" is how UCDP writes what a
     Nigerian respondent would call Boko Haram. Every example needs local review
     before it goes near an enumerator.
  2. Naming specific actors risks ANCHORING. A respondent displaced by a group we
     did not name may conclude the option does not cover them - the opposite of
     what examples are for. Preferring category phrasing over actor names, where
     the data allows, is a live design choice and is flagged per example.
  3. Examples reflect what was RECORDED. Options 3 and 7 stay generic because no
     event source carries them, which is a finding about the data rather than
     about those countries.
"""
from paths import TIDY_S, OUT_S
from question_i18n import (LANGS, T, lang_for, translate_example)
from module_i18n import M as MODULE_T
import datetime
import json
import os
import re

ACLED_MIN_EVENTS = 100   # per code, recent years, before ACLED contributes an example
ACLED_MIN_KIND = 25      # per kind of event, before it is named
# ACLED sub-event type -> the category phrase an enumerator would read. Kinds
# not listed (Disrupted weapons use, Peaceful protest ...) are not examples.
ACLED_PHRASE = {
    "Armed clash": "armed clashes",
    "Air/drone strike": "air or drone strikes",
    "Shelling/artillery/missile attack": "shelling",
    "Remote explosive/landmine/IED": "landmines or explosive devices",
    "Suicide bomb": "suicide bombings",
    "Grenade": "grenade attacks",
    "Chemical weapon": "chemical weapon attacks",
    "Government regains territory": "fighting over territory",
    "Non-state actor overtakes territory": "fighting over territory",
    "Mob violence": "mob violence",
    "Violent demonstration": "violent demonstrations",
    "Protest with intervention": "protests broken up by force",
    "Looting/property destruction": "looting or destruction of property",
    "Arrests": "arrests",
    "Excessive force against protesters": "use of force by the authorities against protesters",
    "Attack": "attacks on civilians",
    "Sexual violence": "sexual violence",
    "Abduction/forced disappearance": "abductions or forced disappearances",
}

import pandas as pd

try:
    from build_protection import build_rows as _build_reg_rows
    from protection import REGISTRAR_LABEL
    from document_specimens import load as _load_specimens
except Exception:
    _build_reg_rows = None
    REGISTRAR_LABEL = {}
    _load_specimens = None

TIDY = TIDY_S
OUT = OUT_S

# The instrument says "SHOW SCREEN OR READ-OUT", and those are different jobs.
# A list read aloud has to stay short: past three or four items respondents
# remember the first and the last and lose the middle. A showcard the respondent
# reads at their own pace can carry everything the country actually has. So two
# sets are produced per country, and how many were AVAILABLE is reported either
# way - a country with eleven active conflicts and three shown is a different
# situation from one with three.
READ_OUT_MAX = 3
SHOWCARD_MAX = 8
RECENT_YEARS = 15   # an example nobody remembers is not an example

# Version 3 (Long) of the forced-to-flee item, verbatim.
OPTIONS = [
    (1, "Threat of armed conflict or war", None),
    (2, "Widespread violence or breakdown of public order", None),
    (3, "Discrimination or persecution",
     "due to your ethnic group, nationality, religion, political beliefs, "
     "sexual orientation or other group membership"),
    (4, "Threat of human rights violations by authorities",
     "detention, torture, confiscation of property"),
    (5, "Other threats of violence against you", None),
    (6, "Natural disasters",
     "floods, droughts, landslides, earthquakes, hurricanes"),
    (7, "Man-made events",
     "eviction for infrastructure projects, pollution events"),
    (8, "A different threat to you or your family's safety [SPECIFY]", None),
]

STEM = ("The next questions are about whether you have ever had to flee a home. "
        "By this we mean leaving a home, or land, due to events that posed a "
        "threat to you or your family's safety.\n\n"
        "In your lifetime, have you ever left a home due to…")

# UCDP writes parties as acronyms or formal names. These are the ones where the
# gap between UCDP's label and what a respondent would say is largest and best
# established. Deliberately short: guessing at local usage is exactly the job
# that has to be done by people in the country.
KNOWN_AS = {
    "JAS": "Boko Haram",
    "IS": "Islamic State",
    "ISGS": "Islamic State in the Greater Sahara",
    "JNIM": "JNIM",
    "AQIM": "al-Qaeda in the Islamic Maghreb",
    "Al-Shabaab": "al-Shabaab",
    "FARC": "the FARC",
    "ELN": "the ELN",
    "AUC": "the AUC",
    "PKK": "the PKK",
    "Taleban": "the Taliban",
    "UIFSA": "the Northern Alliance",
    "SPLM/A-IO": "the SPLM-IO",
    "RSF": "the Rapid Support Forces",
}


# UCDP codes communal violence with the identity of the groups involved:
# "Christians (Nigeria) - Muslims (Nigeria)". That is correct as conflict coding
# and completely unusable as questionnaire text. Naming religious or ethnic
# groups as parties to violence, in an instrument a government enumerator reads
# aloud, is inflammatory and could put both respondent and enumerator at risk.
# These fall back to a neutral category phrase instead.
IDENTITY_MARKERS = ("christian", "muslim", "hindu", "buddhist", "sunni", "shia",
                    "jewish", "sikh", "arabs", "kurds", "tribe", "clan")


def identity_party(name):
    n = str(name or "").lower()
    if re.search(r"\(.+\)\s*$", n):      # "Muslims (Nigeria)" - the coding tell
        return True
    return any(m in n for m in IDENTITY_MARKERS)


# IDMC hazard labels that mean nothing said aloud to a respondent.
HAZARD_SKIP = {"mixed disasters", "other"}
HAZARD_SAY = {
    "flood": "floods",
    "storm": "storms",
    "wildfire": "wildfires",
    "landslide/wet mass movement": "landslides",
    "typhoon/hurricane/cyclone": "cyclones",
    "earthquake": "earthquakes",
    "tornado": "tornadoes",
    "drought": "drought",
    "hailstorm": "hailstorms",
    "dry mass movement": "landslides",
    "erosion": "erosion",
    "tsunami": "tsunami",
    "storm surge": "storm surges",
    "volcanic activity": "volcanic eruptions",
    "sea level rise": "rising sea levels",
    "sinkhole": "sinkholes",
    "dam release flood": "dam releases",
    "winter storm/blizzard": "blizzards",
    "sand/dust storm": "sandstorms",
    "avalanche": "avalanches",
    "cold wave": "extreme cold",
}


def say_hazard(h):
    k = str(h).strip().lower()
    if k in HAZARD_SKIP:
        return None
    return HAZARD_SAY.get(k, k)


def party(name):
    n = str(name or "").strip()
    n = re.sub(r"^Government of\s+", "", n)
    return KNOWN_AS.get(n, n)


def is_gov(name):
    return str(name or "").startswith("Government of")


def phrase(c, latest_year):
    """One example phrase from one UCDP conflict record, or None."""
    if c.get("last", 0) < latest_year - RECENT_YEARS:
        return None
    a, b, code = c.get("a"), c.get("b"), c.get("code")
    if code == 1:
        # state-based: side B is the armed group
        other = party(b if is_gov(a) else a)
        return (f"the fighting involving {other}", "actor")
    if code == 2:
        if str(b).strip().lower() == "civilians":
            if identity_party(a):
                return ("attacks on civilians by armed groups", "category")
            return (f"attacks on civilians by {party(a)}", "actor")
        if identity_party(a) or identity_party(b):
            return ("communal or intercommunal violence", "category")
        return (f"clashes between {party(a)} and {party(b)}", "actor")
    if code == 4:
        return ("action by government forces against civilians", "category")
    if code == 5:
        return (f"attacks on civilians by {party(a)}", "actor")
    return None


# Repeating the same sentence stem is not a list of examples, it is noise.
# Brazil produced "clashes between Comando Vermelho and PCC, clashes between
# Comando Vermelho and GDE, clashes between Bonde dos 13, PCC and Comando
# Vermelho, ..." - six times the same construction, and no respondent parses
# that read aloud. Same-stem examples are merged into one phrase naming the
# distinct actors once each.
STEMS = [
    ("the fighting involving ", "the fighting involving {}"),
    ("clashes between ", "clashes between armed groups, including {}"),
    ("attacks on civilians by ", "attacks on civilians by {}"),
]


def merge_same_stem(items, max_actors=5):
    """Collapse examples sharing a sentence stem into one phrase."""
    out, used = [], set()
    for stem, template in STEMS:
        group = [i for i in items if i["kind"] == "actor"
                 and i["text"].startswith(stem)]
        if len(group) < 2:
            continue
        actors = []
        for g in group:
            for a in re.split(r",\s*|\s+and\s+", g["text"][len(stem):]):
                a = a.strip()
                if a and a.lower() not in {x.lower() for x in actors}:
                    actors.append(a)
        actors = actors[:max_actors]
        joined = (", ".join(actors[:-1]) + " and " + actors[-1]
                  if len(actors) > 1 else actors[0])
        out.append(dict(text=template.format(joined), kind="actor-merged",
                        src=group[0]["src"], n=sum(g.get("n") or 0 for g in group),
                        detail=f"merged from {len(group)} conflicts: "
                               + "; ".join(g["detail"] for g in group[:4])
                               + ("; …" if len(group) > 4 else ""),
                        merged=len(group)))
        used.update(id(g) for g in group)
    out.extend(i for i in items if id(i) not in used)
    return out


# At admin1 the identity problem is worse, not better. UCDP's communal-violence
# dyads there read "Afisare, Anaguta, Birom - Fulani, Hausa" - ethnic groups by
# name, with none of the "(Country)" marker that catches the national ones. So
# the rule at subnational level is inverted: an actor is only named if it is
# ALSO a party to a state-based or one-sided conflict in that country, or is in
# KNOWN_AS. Everything else falls back to a category phrase.
def organised_actors(country_conflicts):
    out = set()
    for c in country_conflicts:
        if c.get("code") in (1, 4, 5):
            for x in (c.get("a"), c.get("b")):
                n = re.sub(r"^Government of\s+", "", str(x or "")).strip()
                if n and n.lower() != "civilians":
                    out.add(n.lower())
    return (out | {k.lower() for k in KNOWN_AS}
                | {v.lower() for v in KNOWN_AS.values()}
                | {v.lower().removeprefix("the ") for v in KNOWN_AS.values()})


MIN_ADM1_EVENTS = 40      # below this an admin1 example is an anecdote
MAX_ADM1 = 8


def main():
    conflicts = json.load(open(f"{TIDY}/ged_conflicts.json"))
    disasters = json.load(open(f"{TIDY}/disaster_register.json"))
    regions = {r["iso_code"]: r["name"]
               for r in json.load(open(f"{TIDY}/regions.json"))}
    try:
        dtm = pd.read_parquet(f"{TIDY}/dtm_reported.parquet")
    except FileNotFoundError:
        dtm = pd.DataFrame(columns=["iso3", "code_id", "people"])
    # profile_countries.py's payload - idps_total, refugees_hosted and, per host
    # country, its top origin countries with how many each sends. That last part
    # is what makes population-specific previews possible: a refugee from Nigeria
    # and one from South Sudan, both interviewed in Mali, carry different
    # displacement histories, and Mali's own examples fit neither. See the
    # "hosted populations" block below.
    try:
        profiles = json.load(open(f"{OUT}/profiles.json"))
    except FileNotFoundError:
        profiles = {}

    latest_year = max((c["last"] for v in conflicts.values() for c in v),
                      default=2025)
    # ACLED's sub-event kinds per country and code (harmonize.py). Turned into
    # ONE category-phrased example per code - "mob violence, looting or
    # destruction of property" - after UCDP's named conflicts, so codes 2, 4 and
    # 5, where UCDP is thin, still get something a respondent would recognise.
    # Public build: kinds and years only, never counts (ACLED terms).
    try:
        acled_sub = json.load(open(f"{TIDY}/acled_subevents.json"))
    except FileNotFoundError:
        acled_sub = {}
    PUBLIC = os.environ.get("IDQ_PUBLIC") == "1"

    out, rows = {}, []
    isos = set(conflicts) | set(disasters) | set(acled_sub)
    for iso in sorted(isos):
        ex = {}
        used_actors = set()

        def actor_key(text):
            return re.sub(r"^(the fighting involving|attacks on civilians by|"
                          r"clashes between)\s+", "", text).strip().lower()

        # ---- conflict-derived options ------------------------------------
        for code in (1, 2, 4, 5):
            seen, picked = set(), []      # picked holds ALL available
            # most recent first, then largest
            for c in sorted(conflicts.get(iso, []),
                            key=lambda c: (-c.get("last", 0), -c.get("events", 0))):
                if c.get("code") != code:
                    continue
                p = phrase(c, latest_year)
                if not p or p[0] in seen:
                    continue
                if p[1] == "actor":
                    k = actor_key(p[0])
                    if k in used_actors:
                        continue
                    used_actors.add(k)
                seen.add(p[0])
                picked.append(dict(text=p[0], kind=p[1], src="UCDP GED",
                                   detail=f"{c['conflict']} ({c['first']}–{c['last']}, "
                                          f"{c['events']:,} recorded incidents)",
                                   n=int(c.get("events") or 0)))
                if len(picked) >= SHOWCARD_MAX:
                    break
            # ACLED: one category-phrased example from the kinds of event it
            # records here, recent years only, ranked after UCDP's named ones.
            # Thresholds keep this to places where the kind of event is part
            # of life, not a one-off: at least ACLED_MIN_EVENTS for the code in
            # recent years, and at least ACLED_MIN_KIND for any kind named.
            kinds = [k for k in acled_sub.get(iso, {}).get(str(code), [])
                     if k["last"] >= latest_year - 5 and ACLED_PHRASE.get(k["sub"])
                     and k["events"] >= ACLED_MIN_KIND]
            phrases, seen_ph = [], set()
            for k in kinds:
                ph = ACLED_PHRASE[k["sub"]]
                if ph not in seen_ph:
                    seen_ph.add(ph); phrases.append(ph)
                if len(phrases) >= 2:
                    break
            if phrases and sum(k["events"] for k in kinds) >= ACLED_MIN_EVENTS:
                n_ev = sum(k["events"] for k in kinds)
                y0 = min(k["first"] for k in kinds); y1 = max(k["last"] for k in kinds)
                detail = (f"{len(kinds)} kind{'s' if len(kinds) > 1 else ''} of event recorded "
                          f"by ACLED, {max(y0, 2020)}–{y1}"
                          + ("" if PUBLIC else f" ({n_ev:,} events)"))
                picked.append(dict(text=", ".join(phrases), kind="category", src="ACLED",
                                   detail=detail, n=None if PUBLIC else int(n_ev)))
            if picked:
                ex[code] = picked
        # ---- hazards ------------------------------------------------------
        dz = disasters.get(iso, {})
        haz = [h for h in dz.get("hazards", []) if h.get("n", 0) > 0]
        HUMAN = {"Wildfire", "Dam release flood", "Sinkhole"}
        nat = [h for h in haz if h["h"] not in HUMAN][:SHOWCARD_MAX]
        man = [h for h in haz if h["h"] in HUMAN][:SHOWCARD_MAX]
        def haz_ex(items):
            o = []
            for h in items:
                t = say_hazard(h["h"])
                if t and t not in [x["text"] for x in o]:
                    o.append(dict(text=t, kind="category", src="IDMC",
                                  detail=f"{h['n']:,} people displaced",
                                  n=int(h["n"])))
            return o[:SHOWCARD_MAX]
        nat_ex, man_ex = haz_ex(nat), haz_ex(man)
        if nat_ex:
            ex[6] = nat_ex
        if man_ex:
            ex[7] = man_ex

        if not ex:
            continue

        ex_raw = {k: list(v) for k, v in ex.items()}
        ex = {k: merge_same_stem(v) for k, v in ex.items()}

        # ---- render both lengths -----------------------------------------
        # read_out  : concise, for an enumerator reading aloud
        # showcard  : everything available, for a card the respondent reads
        prov, avail = [], {}

        def render(limit):
            lines = []
            for code, label, generic in OPTIONS:
                picked = ex.get(code)
                if picked:
                    use = picked[:limit]
                    txt = ", ".join(p["text"] for p in use)
                    more = len(picked) - len(use)
                    lines.append(f"- {label} e.g. {txt}"
                                 + (f" (+{more} more recorded)" if more else ""))
                elif generic:
                    lines.append(f"- {label} e.g. {generic}")
                else:
                    lines.append(f"- {label}")
            lines.append("- None of the above [EXCLUSIVE CODE]")
            return STEM + "\n\n" + "\n".join(lines)

        for code, label, generic in OPTIONS:
            picked = ex.get(code)
            avail[code] = len(picked) if picked else 0
            if picked:
                for i, p in enumerate(picked):
                    prov.append(dict(iso3=iso, code_id=code, example=p["text"],
                                     kind=p["kind"], source=p["src"],
                                     evidence=p["detail"], localised=True,
                                     in_read_out=i < READ_OUT_MAX,
                                     rank=i + 1, incidents=p.get("n"),
                                     merged_from=p.get("merged")))
            elif generic:
                prov.append(dict(iso3=iso, code_id=code, example=generic,
                                 kind="generic", source="questionnaire default",
                                 evidence="no country evidence in any source",
                                 localised=False, in_read_out=True, rank=1,
                                 incidents=None))
            else:
                prov.append(dict(iso3=iso, code_id=code, example="",
                                 kind="none", source="", localised=False,
                                 evidence="no examples in the instrument and "
                                          "none derivable from data",
                                 in_read_out=True, rank=1, incidents=None))

        # structured form, so the page can render checkboxes and translate
        lang = lang_for(iso)
        form, untranslated = [], 0
        for code, label, generic in OPTIONS:
            picked = ex.get(code)
            items, items_t = [], []
            if picked:
                for e in picked:
                    items.append(e["text"])
                    tt, ok = translate_example(e["text"], lang)
                    items_t.append(tt)
                    untranslated += 0 if ok else 1
            elif generic:
                items = [generic]
                items_t = [T[lang]["generic"].get(code, generic)]
            form.append(dict(code=code, n=len(items),
                             eg=items, eg_t=items_t))

        d = dtm[dtm.iso3 == iso] if len(dtm) else dtm
        out[iso] = dict(
            name=regions.get(iso, iso),
            question=render(READ_OUT_MAX),           # kept for compatibility
            read_out=render(READ_OUT_MAX),
            showcard=render(SHOWCARD_MAX),
            localised=sorted(ex),
            n_localised=len(ex),
            available={str(k): v for k, v in avail.items() if v},
            n_available=sum(avail.values()),
            n_beyond_read_out=sum(max(0, v - READ_OUT_MAX) for v in avail.values()),
            has_reported=bool(len(d)),
            form=form,
            untranslated=untranslated,
            _ex=ex,
        )
        rows.extend(prov)

    # ---- admin1 variants, where they say something different ------------
    try:
        ga = pd.read_parquet(f"{TIDY}/ged_admin1.parquet")
    except FileNotFoundError:
        ga = pd.DataFrame()
    n_adm = 0
    if len(ga):
        for iso, g in ga.groupby("iso3"):
            if iso not in out:
                continue
            allowed = organised_actors(conflicts.get(iso, []))
            nat_actors = {e["text"].lower()
                          for v in out[iso].get("_ex", {}).values() for e in v}
            regions_out = []
            tot = g.groupby("adm_1").events.sum().sort_values(ascending=False)
            for adm in tot.index[:MAX_ADM1 * 3]:
                sub = g[g.adm_1 == adm]
                if sub.events.sum() < MIN_ADM1_EVENTS:
                    continue
                aex = {}
                for r in sub.itertuples():
                    code = int(r.code_id)
                    if code not in (1, 2, 4, 5):
                        continue
                    names = [n.strip() for n in str(r.conflicts or "").split(";")
                             if n.strip()]
                    picked = []
                    for nm in names:
                        if " - " in nm:
                            parts = [p.strip() for p in nm.split(" - ")]
                            actor = parts[-1]
                            if actor.lower() == "civilians":
                                actor = parts[0]
                        elif ": " in nm:
                            actor = nm.split(": ", 1)[1].strip()
                        else:
                            actor = nm.strip()
                        actor = re.sub(r"^Government of\s+", "", actor).strip()
                        safe = (actor.lower() in allowed
                                and not identity_party(actor))
                        if code == 4:
                            txt, kind = ("action by government forces against "
                                         "civilians", "category")
                        elif not safe:
                            txt, kind = ({1: ("fighting between armed forces",
                                              "category"),
                                          2: ("communal or intercommunal violence",
                                              "category")}
                                         .get(code, ("attacks on civilians by "
                                                     "armed groups", "category")))
                        elif code == 1:
                            txt, kind = f"the fighting involving {party(actor)}", "actor"
                        elif code == 2:
                            txt, kind = f"clashes between armed groups, including {party(actor)}", "actor"
                        else:
                            txt, kind = f"attacks on civilians by {party(actor)}", "actor"
                        if txt not in [x["text"] for x in picked]:
                            picked.append(dict(text=txt, kind=kind, src="UCDP GED",
                                               detail=f"{nm} in {adm}",
                                               n=int(r.events)))
                    if picked:
                        aex[code] = merge_same_stem(picked)[:SHOWCARD_MAX]
                if not aex:
                    continue
                # only worth showing if it says something the national set does not
                new_txt = {e["text"].lower() for v in aex.values() for e in v}
                named = {e["text"].lower() for v in aex.values() for e in v
                         if e["kind"] in ("actor", "actor-merged")}
                if not named or named <= nat_actors:
                    continue
                regions_out.append(dict(
                    name=str(adm), codes=sorted(aex),
                    ex={str(k): [dict(text=e["text"], kind=e["kind"]) for e in v]
                        for k, v in aex.items()},
                    events=int(sub.events.sum()),
                    differs=sorted(new_txt - nat_actors)[:6]))
                if len(regions_out) >= MAX_ADM1:
                    break
            if regions_out:
                out[iso]["adm1"] = regions_out
                n_adm += len(regions_out)
    for v in out.values():
        v.pop("_ex", None)
    print(f"  admin1 variants that differ from the national set: {n_adm} "
          f"across {sum(1 for v in out.values() if v.get('adm1'))} countries")

    # ---- hosted populations, by origin -------------------------------------
    # The form is read to more than one population in a given country. The
    # national/IDP population's own examples are already `out[iso]`. Each hosted
    # refugee population gets a preview built from ITS OWN origin country's
    # examples (also already computed, in `out[origin_iso3]`) - not the host
    # country's. A Nigerian refugee interviewed in Mali is not well served by
    # Mali's own examples, and vice versa.
    MAX_ORIGINS = 5        # named individually; the rest collapse into "other"
    MIN_OTHER_N = 100      # below this, a long tail isn't worth a line
    n_pop_previews = 0
    for iso, v in out.items():
        p = profiles.get(iso, {})
        idps = int(p.get("idps", 0) or 0)
        pops = [dict(kind="national", iso3=iso, name=v["name"], n=idps,
                     has_data=True)]
        origins = sorted(p.get("origins", []) or [], key=lambda o: -o.get("n", 0))
        shown = origins[:MAX_ORIGINS]
        for o in shown:
            has = o.get("iso3") in out
            pops.append(dict(kind="refugee", iso3=o.get("iso3"),
                             name=o.get("name", o.get("iso3", "?")),
                             n=int(o.get("n", 0) or 0), has_data=has))
            n_pop_previews += 1 if has else 0
        rest = origins[MAX_ORIGINS:]
        rest_n = sum(int(o.get("n", 0) or 0) for o in rest)
        if rest_n >= MIN_OTHER_N:
            pops.append(dict(kind="other", iso3=None,
                             name=f"{len(rest)} other origin countries",
                             n=rest_n, has_data=False))
        if len(pops) > 1 or idps:
            out[iso]["populations"] = pops
    # ---- customisation of the rest of the module, from the databases --------
    # Everything after FrcFl has a slot the instrument lets vary, and the data
    # already in the pipeline can fill most of them:
    #   FleeLoc   "Other country [SPECIFY]"  -> the origins actually hosted here
    #   FleeCross "another country"          -> where this country's own nationals
    #                                           are registered as refugees (UNHCR)
    #   IDPLoc / IDPPost "province"          -> the subnational areas with most
    #                                           displacement events here
    #   FrcOth                               -> reasons IOM DTM recorded among
    #                                           displaced people here that fall
    #                                           outside FrcFl's codes
    # Legal's document names come from protection.py on the page side.
    try:
        upop = pd.read_parquet(f"{TIDY}/unhcr_population.parquet")
        upop = upop[upop.year == upop.year.max()]
        upop["n"] = upop["refugees"].fillna(0) + upop["asylum_seekers"].fillna(0)
        dest = (upop.groupby(["coo_iso", "coa_name"])["n"].sum().reset_index()
                    .sort_values("n", ascending=False))
    except Exception:
        dest = pd.DataFrame(columns=["coo_iso", "coa_name", "n"])
    try:
        dtm_det = pd.read_parquet(f"{TIDY}/dtm_reported_detail.parquet")
        dtm_tot = pd.read_parquet(f"{TIDY}/dtm_reported.parquet")[["iso3", "country_total"]].drop_duplicates("iso3")
    except Exception:
        dtm_det = pd.DataFrame(columns=["iso3", "reason", "code_id", "people"]); dtm_tot = pd.DataFrame(columns=["iso3", "country_total"])

    def clean_country(n):
        n = re.sub(r"\s*\(.*?\)\s*$", "", str(n))
        return {"Serbia and Kosovo: S/RES/1244": "Serbia", "Iran (Islamic Rep. of)": "Iran",
                "Dem. Rep. of the Congo": "DR Congo", "United Rep. of Tanzania": "Tanzania",
                "Syrian Arab Rep.": "Syria", "Venezuela (Bolivarian Republic of)": "Venezuela",
                "Bolivia (Plurinational State of)": "Bolivia", "Türkiye": "Türkiye",
                "United States of America": "United States", "Russian Federation": "Russia",
                "Rep. of Moldova": "Moldova", "Rep. of Korea": "Republic of Korea"}.get(n, n)

    n_cust = 0
    for iso, v in out.items():
        cust = {}
        origins = [clean_country(o["name"]) for o in (v.get("populations") or []) if o.get("kind") == "refugee"][:3]
        if origins:
            cust["origins"] = origins
        d = dest[(dest.coo_iso == iso) & (dest.n >= 500)].head(3)
        if len(d):
            cust["dest"] = [clean_country(x) for x in d.coa_name]
        adm = sorted(v.get("adm1") or [], key=lambda r: -r.get("events", 0))[:3]
        if adm:
            cust["adm"] = [r["name"] for r in adm]
        dd = dtm_det[(dtm_det.iso3 == iso) & (dtm_det.code_id.isna() | (dtm_det.code_id == 8))]
        tot = dtm_tot.loc[dtm_tot.iso3 == iso, "country_total"]
        if len(dd) and len(tot) and float(tot.iloc[0]) > 0:
            g = dd.groupby("reason")["people"].sum().sort_values(ascending=False)
            g = g[g.index != "no reason for displacement reported"]
            cust["dtm"] = [[r, round(100 * float(n) / float(tot.iloc[0]), 1)] for r, n in g.head(4).items() if n > 0]
        if cust:
            v["cust"] = cust; n_cust += 1
    print(f"  module customisation from the databases: {n_cust} countries "
          f"(origins hosted, destinations abroad, subnational names, DTM reasons)")

    print(f"  hosted-population previews: {n_pop_previews} refugee-origin "
          f"populations with their own examples, offered across "
          f"{sum(1 for v in out.values() if v.get('populations'))} host-country pages "
          f"({'profiles.json found' if profiles else 'profiles.json NOT FOUND - run profile_countries.py first for this feature'})")

    # ---- language ---------------------------------------------------------
    for iso, v in out.items():
        v["lang"] = lang_for(iso)

    json.dump(out, open(f"{TIDY}/localised_questions.json", "w"))
    pd.DataFrame(rows).to_csv(f"{OUT}/localised_question_examples.csv", index=False)

    n_loc = pd.DataFrame(rows).query("localised").iso3.nunique() if rows else 0
    print(f"drafted the question for {len(out)} countries; "
          f"{n_loc} have at least one localised example")
    by = pd.DataFrame(rows)
    print("\noptions localised, by response option:")
    for code, label, _ in OPTIONS:
        s = by[(by.code_id == code) & (by.localised)]
        print(f"   {code}. {label[:44]:<45} {s.iso3.nunique():>3} countries")
    # The international protection / registration item - a separate part of
    # the instrument from the forced-to-flee item above, drafted the same way
    # (protection.py / build_protection.py). Shown inline per country on this
    # page rather than as its own page, so there's one place to look up a
    # country's full localised wording instead of two.
    reg = _build_reg_rows() if _build_reg_rows else {}
    spec = _load_specimens() if _load_specimens else {}
    # Vintage stamp for the page footer and every download: when this build
    # ran, the last year of recorded events, the UNHCR population year, and
    # whether the (internal) Registration Baseline Survey overlay was present.
    try:
        unhcr_year = int(pd.read_parquet(f"{TIDY}/unhcr_population.parquet").year.max())
    except Exception:
        unhcr_year = None
    try:
        from protection import SURVEY as _SURVEY
        survey_present = _SURVEY.exists()
    except Exception:
        survey_present = False
    meta = {"built": datetime.date.today().isoformat(), "events_to": int(latest_year),
            "unhcr_year": unhcr_year, "survey": survey_present}
    # Per-country digest written by build_population_map.py (counts, cause
    # shares, origins, areas, registrar) - the map's evidence, quoted by the
    # checks list and the instructions. Absent until the map has been built.
    try:
        mapfacts = json.load(open(f"{OUT}/mapfacts.json"))
    except FileNotFoundError:
        mapfacts = {}
    write_page(out, rows, reg, spec, meta, mapfacts)
    print("\nExample — Nigeria:")
    if "NGA" in out:
        print("   " + out["NGA"]["question"].replace("\n", "\n   "))


PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Build the questionnaire — steps 1 to 6</title><style>
:root{color-scheme:light dark;--s:#fcfcfb;--p:#f2f1ec;--i:#111;--i2:#4a4945;
 --m:#8a8880;--g:#d9d8d0;--a:#2a78d6;--w:#fab219;--paper:#fff}
@media(prefers-color-scheme:dark){:root{--s:#1c1c1a;--p:#111110;--i:#f4f3ee;
 --i2:#c3c2b7;--g:#33332f;--a:#5aa0f0;--paper:#1c1c1a}}
*{box-sizing:border-box}
body{margin:0;background:var(--p);color:var(--i);font:15px/1.6 ui-sans-serif,
 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.w{max-width:980px;margin:0 auto;padding:38px 20px 80px}
h1{font-size:23px;margin:0 0 8px;letter-spacing:-.02em;font-weight:660}
p.lede{color:var(--i2);margin:0 0 16px;font-size:14.5px;max-width:76ch}
.bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:14px 0 6px}
select,.bar button{font:inherit;font-size:13.5px;padding:8px 12px;border-radius:8px;
 border:1px solid var(--g);background:var(--s);color:var(--i);cursor:pointer}
select{min-width:250px}
.bar button.on{background:var(--i);color:var(--p);border-color:var(--i)}
.bar button:disabled{opacity:.4;cursor:default}
.verhint{font-size:12px;color:var(--m);margin:-2px 0 6px;max-width:640px}
.bar span.lbl{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;
 color:var(--m);font-weight:680;margin-left:6px}
.bar span.grp{font-size:11px;text-transform:uppercase;letter-spacing:.05em;
 color:var(--m);font-weight:680;min-width:172px}
@media(max-width:700px){.bar span.grp{min-width:0;width:100%}}
.bar+.bar{margin-top:2px}
/* ---- country picker: a searchable list with a coloured localisation badge and a
   specimen tag per row (a native <select> can't colour its options) ---- */
.cpick{position:relative;min-width:320px;flex:1 1 320px;max-width:520px}
.cpick-btn{font:inherit;font-size:13.5px;width:100%;text-align:left;padding:8px 12px;border-radius:8px;
 border:1px solid var(--g);background:var(--s);color:var(--i);cursor:pointer;display:flex;align-items:center;gap:8px}
.cpick-btn .loc,.cpick-btn .spec{margin-left:auto}
.cpick-btn .loc+.spec{margin-left:0}
.cpick-caret{color:var(--m);margin-left:6px}
.cpick-menu{position:absolute;z-index:30;top:calc(100% + 4px);left:0;width:min(560px,92vw);
 background:var(--s);border:1px solid var(--g);border-radius:10px;box-shadow:0 12px 32px rgba(20,35,76,.16);padding:8px}
.cpick-menu[hidden]{display:none}
#cpickSearch{font:inherit;font-size:13.5px;width:100%;padding:8px 11px;border-radius:7px;border:1px solid var(--g);
 background:var(--s);color:var(--i);box-sizing:border-box}
#cpickSearch:focus{outline:2px solid var(--a);outline-offset:-1px}
.cpick-key{display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:11px;color:var(--m);padding:7px 2px 4px}
.cpick-list{max-height:340px;overflow:auto;margin-top:2px}
.cpick-row{display:flex;align-items:center;gap:8px;padding:7px 9px;border-radius:7px;cursor:pointer;font-size:13.5px}
.cpick-row:hover,.cpick-row.sel{background:color-mix(in srgb,var(--a) 8%,transparent)}
.cpick-row.on{font-weight:600}
.cpick-name{flex:1 1 auto}
.loc{font-size:10.5px;font-weight:700;letter-spacing:.03em;padding:2px 7px;border-radius:20px;white-space:nowrap}
.loc-hi{background:color-mix(in srgb,#0ca30c 16%,transparent);color:#0a7d0a}
.loc-mid{background:color-mix(in srgb,var(--w) 26%,transparent);color:#8a6100}
.loc-lo{background:transparent;color:var(--m);border:1px solid var(--g)}
.spec{font-size:10.5px;font-weight:700;letter-spacing:.03em;padding:2px 7px;border-radius:4px;white-space:nowrap;
 background:color-mix(in srgb,var(--a) 14%,transparent);color:var(--a)}
.spec.spec-links{background:transparent;border:1px dashed color-mix(in srgb,var(--a) 40%,var(--g))}
/* ---- the form itself ---- */
.form{background:var(--paper);border:1px solid var(--g);border-radius:4px;
 padding:34px 38px 30px;margin-top:14px;
 box-shadow:0 1px 2px rgba(0,0,0,.05),0 8px 26px rgba(0,0,0,.06);
 font-family:ui-serif,Georgia,"Times New Roman",serif;font-size:15.5px;line-height:1.62}
.form[dir="rtl"]{direction:rtl;text-align:right;
 font-family:ui-serif,"Times New Roman",serif}
/* when a population is picked, the SAME card flips to show that population's
   own examples in place of the host country's - tinted so it's obviously not
   the default view, with a banner explaining what's being substituted */
.form.custom{border-color:color-mix(in srgb,var(--a) 35%,var(--g));
 background:color-mix(in srgb,var(--a) 4%,var(--paper))}
.custombanner{font-family:ui-sans-serif,-apple-system,sans-serif;font-size:11.5px;
 font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:var(--a);
 background:color-mix(in srgb,var(--a) 10%,transparent);
 border:1px solid color-mix(in srgb,var(--a) 30%,var(--g));border-radius:5px;
 padding:7px 11px;margin:-6px 0 16px}
.fhead{display:flex;align-items:baseline;gap:12px;border-bottom:2px solid var(--i);
 padding-bottom:7px;margin-bottom:15px;font-family:ui-sans-serif,-apple-system,sans-serif}
.fitem{font-weight:700;font-size:13px;letter-spacing:.06em}
.fask{font-size:12px;color:var(--i2);font-style:italic}
.fcountry{margin-inline-start:auto;font-size:12px;color:var(--m);
 text-transform:uppercase;letter-spacing:.06em;font-weight:650}
.stem{margin:0 0 9px}
.lead{margin:14px 0 4px;font-weight:600}
.instr{font-family:ui-sans-serif,-apple-system,sans-serif;font-size:11px;
 letter-spacing:.05em;color:var(--i2);border:1px solid var(--g);
 padding:5px 9px;border-radius:3px;display:inline-block;margin-bottom:12px}
ol.opts{list-style:none;margin:0;padding:0}
ol.opts li{display:flex;gap:11px;align-items:flex-start;padding:6.5px 0;
 border-bottom:1px dotted var(--g)}
ol.opts li:last-child{border-bottom:0}
.box{flex:0 0 auto;width:14px;height:14px;border:1.5px solid var(--i);
 margin-top:5px;border-radius:2px}
.num{flex:0 0 auto;width:20px;color:var(--m);font-size:12.5px;margin-top:3px;
 font-family:ui-sans-serif,sans-serif}
.otext{flex:1}
.eg{color:var(--a)}
.eg .lab{font-style:italic;color:var(--i2)}
.gen{color:var(--m);font-style:italic}
.more{font-size:11.5px;color:var(--m);font-family:ui-sans-serif,sans-serif}
.excl{font-size:11px;color:var(--m);font-family:ui-sans-serif,sans-serif}
.warn{background:color-mix(in srgb,var(--w) 13%,transparent);
 border:1px solid color-mix(in srgb,var(--w) 42%,transparent);border-radius:9px;
 padding:12px 15px;margin-top:14px;font-size:13.5px;color:var(--i2)}
table{border-collapse:collapse;width:100%;font-size:13px;margin-top:12px}
th,td{padding:6px 9px;border-bottom:1px solid var(--g);text-align:left;vertical-align:top}
th{color:var(--m);font-size:10.5px;text-transform:uppercase;letter-spacing:.04em}
h2{font-size:15px;margin:28px 0 2px;font-weight:640}
.k{font-size:9.5px;text-transform:uppercase;letter-spacing:.05em;padding:2px 6px;
 border-radius:4px;font-weight:700;white-space:nowrap}
.k-actor,.k-actor-merged{background:color-mix(in srgb,var(--a) 16%,transparent);color:var(--a)}
.k-category{background:color-mix(in srgb,#0ca30c 16%,transparent);color:#0ca30c}
.k-generic{background:transparent;color:var(--m);border:1px solid var(--g)}
.k-none{background:transparent;color:var(--m);border:1px dashed var(--g)}
.ro{font-size:10px;color:var(--m)}
/* ---- registration (international protection) card — mirrors build_protection.py's
   own probe-card styling, so the two items read as one family of pages ---- */
.regcard{margin-top:26px;padding-top:4px}
.regcard .sub{color:var(--i2);margin:0 0 12px;font-size:13.5px;max-width:76ch}
.regform{background:var(--paper);border:1px solid var(--g);border-radius:4px;
 padding:24px 28px 22px;font-family:ui-sans-serif,-apple-system,sans-serif}
.badges{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 12px}
.badge{font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;
 padding:4px 9px;border-radius:20px;font-weight:700;white-space:nowrap}
.b-reg{background:color-mix(in srgb,var(--a) 16%,transparent);color:var(--a)}
.b-cf-HIGH{background:color-mix(in srgb,#0ca30c 16%,transparent);color:#0ca30c}
.b-cf-MEDIUM{background:color-mix(in srgb,var(--w) 22%,transparent);color:#8a6100}
.b-cf-LOW{background:color-mix(in srgb,#d03b3b 14%,transparent);color:#d03b3b}
.probe{border-bottom:1px dotted var(--g);padding-bottom:14px;margin-bottom:14px;
 font-family:ui-sans-serif,-apple-system,sans-serif}
.probe:last-of-type{border-bottom:0;margin-bottom:0;padding-bottom:0}
.ptag{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;
 color:var(--m);margin-bottom:6px}
.ptext{font-family:ui-serif,Georgia,"Times New Roman",serif;font-size:15.5px;line-height:1.55}
.pmiss{color:var(--m);font-style:italic;font-size:13.5px}
.regcard>.pmiss{font-family:ui-sans-serif,-apple-system,sans-serif}
.gloss{font-size:12.5px;color:var(--i2);margin-top:5px}
.gloss i{font-style:italic}
.why{font-size:11.5px;color:var(--m);margin-top:4px}
.cav{background:color-mix(in srgb,var(--a) 6%,transparent);
 border:1px solid color-mix(in srgb,var(--a) 20%,var(--g));border-radius:9px;
 padding:12px 15px;margin-top:12px;font-size:13px;color:var(--i2)}
/* ---- module questions (Apply / IntApply / Outcome) ------------------------
   The registration/international-protection item, shown as it would actually
   appear in the instrument: stem, response options and skip logic, per the
   revised module — not just an abstract "probe" sentence. Only Apply carries
   a country-specific localisation example; IntApply and Outcome are fixed. */
.modq{border-top:1px dotted var(--g);padding-top:14px;margin-top:14px;
 font-family:ui-sans-serif,-apple-system,sans-serif}
.modq:first-child{border-top:0;padding-top:0;margin-top:0}
.modq-name{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
 color:var(--a);margin-bottom:3px}
.modq-skip{font-size:11.5px;font-style:italic;color:var(--m);margin-bottom:6px}
.modq-stem{font-family:ui-serif,Georgia,"Times New Roman",serif;font-size:15.5px;
 line-height:1.5;font-weight:600;margin-bottom:4px}
.modq-example{font-family:ui-serif,Georgia,"Times New Roman",serif;font-size:14.5px;
 line-height:1.5;color:var(--i2);margin:6px 0 2px}
.modq-example{font-style:italic}
.modq-example .eg{font-style:normal;font-weight:600;color:var(--a)}
.modq-form{font-family:ui-serif,Georgia,"Times New Roman",serif;font-size:15.5px;line-height:1.62;margin-top:6px}
.modq-form[dir="rtl"]{direction:rtl;text-align:right}
.modq-form .fhead{margin-top:2px}
.specimens-chain{margin-top:6px}
.modq-custom{font-family:ui-serif,Georgia,"Times New Roman",serif;font-style:italic;font-size:13.5px;
 color:var(--i2);margin:5px 0 2px}
.modq-custom-inline{font-family:ui-serif,Georgia,"Times New Roman",serif;font-style:italic;font-size:12.5px;color:var(--i2)}
.modq-vtag{font-family:ui-sans-serif,-apple-system,sans-serif;font-style:normal;font-size:10px;
 font-weight:700;color:var(--a);border:1px solid color-mix(in srgb,var(--a) 40%,var(--g));
 border-radius:3px;padding:0 4px;margin-inline-end:4px;vertical-align:middle}
.regform[dir="rtl"],.form[dir="rtl"] .aprobe{direction:rtl;text-align:right}
.regform[dir="rtl"] .modq-arrow{margin-left:0;margin-right:auto}
.modq-opts{margin:10px 0 0;padding:0}
.modq-opt{display:flex;align-items:baseline;gap:8px;padding:3px 0;font-size:13.5px}
.modq-opt .box{flex:0 0 auto;width:12px;height:12px;border:1.5px solid var(--i);
 border-radius:2px;margin-top:2px}
.modq-arrow{margin-left:auto;font-size:11px;color:var(--m);white-space:nowrap}
.modq-note{font-size:12.5px;color:var(--i2);margin:6px 0 0;max-width:72ch}
.modq-list{margin:6px 0 0;padding-left:18px;font-size:12.5px;color:var(--i2)}
.modq-list li{margin-bottom:3px}
.modq-softcheck{color:var(--m);font-style:italic}
.modq-cats{margin-top:8px}
.modq-cathead{font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;
 color:var(--m);font-weight:680;margin:8px 0 2px}
.modq-catopt{font-size:13.5px;margin:2px 0 2px 4px}
.modpicker{background:color-mix(in srgb,var(--a) 5%,transparent);
 border:1px solid color-mix(in srgb,var(--a) 22%,var(--g));border-radius:8px;
 padding:12px 15px 14px;margin:0 0 16px}
.modpicker .sectitle{font-family:ui-sans-serif,-apple-system,sans-serif;font-size:11px;
 text-transform:uppercase;letter-spacing:.06em;color:var(--m);font-weight:680;margin:0 0 8px}
.modpresets{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin:0 0 12px;
 font-family:ui-sans-serif,-apple-system,sans-serif}
.preset{font:inherit;font-size:12.5px;padding:6px 11px;border-radius:20px;border:1px solid var(--g);
 background:var(--s);color:var(--i2);cursor:pointer}
.preset.on{background:var(--i);color:var(--p);border-color:var(--i)}
.modsummary{font-size:12px;color:var(--i2);margin-left:auto}
.modgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px}
.modcard{background:var(--s);border:1px solid var(--g);border-radius:8px;padding:10px 12px 8px;
 font-family:ui-sans-serif,-apple-system,sans-serif}
.modcard.off{background:transparent;border-style:dashed}
.modtoggle{display:flex;align-items:center;gap:7px;font-size:12.5px;font-weight:700;color:var(--i);
 cursor:pointer;margin-bottom:8px;padding-bottom:6px;border-bottom:1px dotted var(--g)}
.modcoretext{font-size:11.5px;color:var(--i2);margin:0 0 8px;line-height:1.45}
.modoff{font-size:12px;color:var(--m);margin:0}
.modlabel{flex:1 1 auto}
.modfw{display:flex;gap:18px;flex-wrap:wrap;margin-bottom:8px;
 font-family:ui-sans-serif,-apple-system,sans-serif;font-size:13.5px}
.modfw label{display:flex;align-items:center;gap:6px;cursor:pointer;font-weight:600}
.modgrouptitle{font-family:ui-sans-serif,-apple-system,sans-serif;font-size:11px;
 text-transform:uppercase;letter-spacing:.05em;color:var(--a);font-weight:680;
 margin:10px 0 4px}
.moditem{display:flex;align-items:baseline;gap:7px;cursor:pointer;
 font-family:ui-sans-serif,-apple-system,sans-serif;font-size:12.5px;margin:0;padding:4px 0;
 border-bottom:1px dotted color-mix(in srgb,var(--g) 60%,transparent)}
.moditem:last-child{border-bottom:0}
.moditem input{margin-top:2px}
.modwhy{font-size:11.5px;color:var(--m);flex-basis:100%;margin-left:22px}
.modadds{font-size:10px;color:var(--a);font-weight:700;letter-spacing:.02em;white-space:nowrap}
.modgrp{font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:var(--m);font-weight:700;margin:8px 0 2px}
.modgrp:first-of-type{margin-top:2px}
.moditem.modcore,.moditem.modna{cursor:default}
.moditem.modna .modlabel{color:var(--m)}
.modtag{font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;padding:1px 5px;border-radius:3px;
 background:color-mix(in srgb,var(--a) 14%,transparent);color:var(--a);white-space:nowrap;align-self:center}
.modtag.na{background:transparent;border:1px dashed var(--g);color:var(--m);text-transform:none;letter-spacing:0;font-size:10px}
.modcore,.modresult{font-family:ui-sans-serif,-apple-system,sans-serif;font-size:12.5px;color:var(--i2);margin:0 0 8px;max-width:76ch}
.modresult{margin:10px 0 0;padding-top:8px;border-top:1px dotted var(--g)}
.modquick{margin:0 0 4px}
.modhint{font-size:12px;color:var(--m);margin:10px 0 0;max-width:72ch}
/* ---- Apply card: two localisation versions on the FrcFl form styling ---- */
.applysec{margin-top:18px}
.applysec[hidden]{display:none}
.aver{margin:16px 0 0;padding-top:12px;border-top:1px dotted var(--g)}
.avertag{font-family:ui-sans-serif,-apple-system,sans-serif;font-size:10.5px;font-weight:700;
 text-transform:uppercase;letter-spacing:.06em;color:var(--m);display:block;margin-bottom:5px}
.avertag b{color:var(--a)}
.aprobe{margin:0 0 5px;font-style:italic}
.aprobe .eg{font-style:normal;font-weight:600}
.form .gloss,.form .why{font-family:ui-sans-serif,-apple-system,sans-serif}
.form .specimens{margin-top:6px}
.form .spec-head{margin-top:12px}
.ainstr{font-family:ui-sans-serif,-apple-system,sans-serif;font-size:12.5px;line-height:1.5;
 color:var(--i2);border-top:1px dotted var(--g);margin-top:16px;padding-top:12px}
.ainstr b{color:var(--i)}
.form ol.opts.aopts{margin-top:14px}
/* ---- download toolbar ------------------------------------------------- */
.dlbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:16px 0 4px;
 font-family:ui-sans-serif,-apple-system,sans-serif}
.dlbar button{font:inherit;font-size:13px;padding:8px 14px;border-radius:8px;
 border:1px solid var(--a);background:var(--a);color:#fff;cursor:pointer;font-weight:600}
.dlbar button:disabled{opacity:.5;cursor:default}
.dlbar button.secondary{background:var(--s);color:var(--a)}
.dlsep{width:1px;align-self:stretch;background:var(--g);margin:2px 4px}
.dlstatus{font-size:12.5px;color:var(--m);max-width:60ch}
.regcard .dlbar{margin:0 0 14px}
.dlstatus.err{color:#d03b3b}
ol.opts.grid li{align-items:center}
.validpick{background:#f7f9fc;border:1px solid var(--g);border-radius:8px;padding:9px 12px;margin:9px 0 0;
 font-family:ui-sans-serif,-apple-system,sans-serif;font-size:12.5px;line-height:1.45}
.validpick b{color:var(--i)}
.validpick .vp-note{color:var(--m)}
.validpick code{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:11.5px}
.vp-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:2px 14px;margin-top:6px}
.vp{display:flex;gap:7px;align-items:baseline;cursor:pointer;color:var(--i2)}
.vp input:checked+span{color:var(--i);font-weight:600}
.ynbox{display:inline-flex;align-items:center;gap:4px;margin-right:8px;white-space:nowrap}
.ynbox i{font-style:normal;font-size:11px;color:var(--m);margin-right:6px}
.ynbox .box{margin:0}
.dlbar{flex-direction:column;align-items:stretch;gap:6px}
.dlgrp{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.dllab{font-size:12.5px;color:var(--i2);min-width:230px;font-weight:600}
.dltools{border-top:1px dotted var(--g);padding-top:8px;margin-top:2px}
.dltools button{background:var(--s);color:var(--a)}
.dlissue{font-size:12.5px;color:var(--a);margin-left:6px}
.dlbar .dlstatus{margin-top:4px}
/* ---- hand edits: any blue customisation can be clicked and changed ------ */
[data-slot]{cursor:text;padding-bottom:1px}
[data-slot]:hover{background:#eef3fa;border-bottom:1px dashed var(--a)}
.eg.edited,.egl.edited .eg,.edited{color:#7a3fb5}
.egl.edited{border-bottom-color:rgba(122,63,181,.5)}
.edithint{font-family:ui-sans-serif,-apple-system,sans-serif;font-size:12.5px;color:var(--i2);
 background:#f4f7fc;border:1px solid #c9d6ea;border-radius:8px;padding:8px 12px;margin:0 0 12px;line-height:1.5}
.edithint b{color:var(--i)}
.edithint .swatch{display:inline-block;width:10px;height:10px;border-radius:2px;vertical-align:middle;margin-right:3px}
.editpop{position:absolute;z-index:60;background:#fff;border:1px solid var(--g);border-radius:10px;
 box-shadow:0 12px 32px rgba(20,35,76,.18);padding:12px 14px;width:min(440px,calc(100vw - 32px));
 font-family:ui-sans-serif,-apple-system,sans-serif;font-size:13px}
.editpop .eplab{font-weight:600;color:var(--i);margin-bottom:6px}
.editpop textarea{width:100%;box-sizing:border-box;font:inherit;font-size:13.5px;min-height:70px;
 border:1px solid var(--g);border-radius:6px;padding:7px 9px;resize:vertical}
.editpop .ephint{font-size:11.5px;color:var(--m);margin:4px 0 8px}
.editpop .epbtns{display:flex;gap:8px;flex-wrap:wrap}
.editpop button{font:inherit;font-size:12.5px;padding:6px 12px;border-radius:7px;border:1px solid var(--a);
 background:var(--a);color:#fff;cursor:pointer;font-weight:600}
.editpop button.secondary{background:#fff;color:var(--a)}
.editpop button.plain{background:#fff;color:var(--i2);border-color:var(--g)}
/* ---- walkthrough: a hypothetical respondent's path through the module ---- */
.walk{background:#fbfcfe;border:1px solid var(--g);border-radius:10px;padding:12px 14px;margin:0 0 14px;
 font-family:ui-sans-serif,-apple-system,sans-serif;font-size:13px}
.walk .sectitle{margin:0 0 6px}
.walk .wkpre{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}
.walk .wkpre button{font:inherit;font-size:12px;padding:5px 10px;border-radius:16px;border:1px solid var(--g);
 background:#fff;color:var(--i);cursor:pointer}
.walk .wkpre button.on{background:#14234c;border-color:#14234c;color:#fff}
.walk .wkgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:6px 14px}
.walk label{display:flex;flex-direction:column;gap:2px;font-size:12px;color:var(--i2)}
.walk label.off{opacity:.4}
.walk select{font:inherit;font-size:12.5px;padding:4px 6px;border:1px solid var(--g);border-radius:6px;background:#fff}
.walk .wkres{margin-top:10px;padding:9px 12px;border-radius:8px;background:#eef3fa;color:var(--i);font-size:13.5px}
.walk .wkres b{color:#14234c}
.walk .wkres .wkcode{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:12px;color:var(--i2)}
.walk .wkpath{font-size:12px;color:var(--i2);margin-top:4px}
.walk .wkhint{font-size:11.5px;color:var(--m);margin:6px 0 0}
.regform.walking .modq{opacity:.32}
.regform.walking .modq.wk-asked{opacity:1;box-shadow:inset 3px 0 0 #14234c;padding-left:10px}
.regform.walking .modq.wk-asked .modq-name::after{content:" · asked";color:#14234c;font-weight:500;text-transform:none;letter-spacing:0}
/* ---- checks-before-fielding panel --------------------------------------- */
.chk ul{margin:6px 0 0;padding-left:18px}
.chk li{margin-bottom:5px}
.chk .lvl{font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;padding:1px 6px;border-radius:4px;margin-right:6px}
.chk .lvl-must{background:#fbe3e3;color:#a02a2a}.chk .lvl-check{background:#fbf1dc;color:#8a5a0a}.chk .lvl-note{background:#e8eef7;color:#31558f}
.pagefoot{font-size:12.5px;color:var(--m);margin-top:24px;line-height:1.6}
/* ---- page structure: numbered steps, settings card, section labels ------- */
.steps{list-style:none;display:flex;flex-wrap:wrap;gap:6px;margin:0 0 18px;padding:0;
 font-family:ui-sans-serif,-apple-system,sans-serif;font-size:12.5px}
.steps a{display:inline-block;padding:5px 11px 5px 7px;border:1px solid var(--g);border-radius:20px;color:var(--i);text-decoration:none;background:#fff}
.steps a:hover{border-color:var(--a);color:var(--a)}
.steps b,.grp b,h2.step b{display:inline-block;width:18px;height:18px;line-height:18px;border-radius:50%;background:#14234c;color:#fff;
 text-align:center;font-size:11px;font-weight:700;margin-right:6px;letter-spacing:0}
.setup{background:#f7f9fc;border:1px solid var(--g);border-radius:12px;padding:6px 16px 14px;margin:0 0 6px}
.setup .bar{margin:12px 0 4px}
.setup .bar-cont{margin-top:0}
.setup .bar span.grp{min-width:190px;color:var(--i);font-size:12px;letter-spacing:.03em;text-transform:none;font-weight:600}
.setup .modpicker{background:transparent;border:0;padding:0;margin:0;border-radius:0}
.setup .modpicker .bar{margin-bottom:0}
.modsummaryrow{margin:4px 0 4px 190px;font-size:12.5px;color:var(--i2);display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.setup .modsummary{margin-left:0}
.setup #moditems{margin:8px 0 6px}
.help.small{font-size:12px;padding:5px 10px;margin:4px 0 0}
.advanced{margin-top:8px;padding:6px 12px 10px;border-left:3px solid var(--g)}
.advhint{font-size:12px;color:var(--m);max-width:56ch;line-height:1.4}
.advanced .popsection{margin-top:10px;padding-top:12px;border-top:1px dotted var(--g)}
h2.step{font-size:17px;margin:34px 0 8px}
.cardlab{font-family:ui-sans-serif,-apple-system,sans-serif;font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;
 color:var(--i2);font-weight:700;margin:22px 0 6px}
.applysec .cardlab{margin-top:22px}
.regcard .cardlab{margin-top:26px}
.info{background:#f4f7fc;border:1px solid #d5dfee;border-radius:8px;padding:10px 14px;font-size:13px;line-height:1.55;color:var(--i2);margin-top:12px;
 font-family:ui-sans-serif,-apple-system,sans-serif}
.info b{color:var(--i)}
.modq-title{font-weight:500;text-transform:none;letter-spacing:0;color:var(--i2)}
.keylab{font-size:11px;color:var(--m);margin-right:2px}
.filegrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px;align-items:stretch}
.dlbar{flex-wrap:nowrap}
.filetile{background:#fff;border:1px solid var(--g);border-radius:10px;padding:12px 14px;display:flex;flex-direction:column;gap:6px}
.filename{font-weight:700;color:var(--i);font-size:13.5px}
.filedesc{font-size:12px;color:var(--i2);line-height:1.45;flex:1 0 auto}
.filebtns{display:flex;gap:6px}
.dltools{margin-top:6px}
/* hover-only edit affordance, so the card doesn't read as a page of links */
[data-slot]{border-bottom:1px dashed transparent}
[data-slot]:hover::after{content:" \270E";font-size:.8em;color:var(--m)}
.pop::before{content:"";display:inline-block;width:9px;height:9px;border-radius:50%;border:1.5px solid var(--m);margin-right:7px;vertical-align:-1px}
.pop.on::before{border-color:#fff;background:#fff;box-shadow:inset 0 0 0 2px var(--a)}
/* sticky download bar, shown while "Your files" is off screen */
.sticky{position:fixed;left:0;right:0;bottom:0;z-index:50;background:rgba(20,35,76,.96);color:#fff;display:flex;gap:8px;align-items:center;
 padding:8px 20px;font-family:ui-sans-serif,-apple-system,sans-serif;font-size:12.5px;flex-wrap:wrap;box-shadow:0 -6px 20px rgba(20,35,76,.25)}
.sticky .stickyc{margin-right:auto;opacity:.85}
.sticky button{font:inherit;font-size:12.5px;padding:6px 11px;border-radius:7px;border:1px solid rgba(255,255,255,.35);background:transparent;color:#fff;cursor:pointer}
.sticky button:hover{background:rgba(255,255,255,.12)}
.sticky a{color:#fff;opacity:.85;margin-left:6px}
.sticky[hidden]{display:none}
p.sub{color:var(--i2);margin:0 0 12px;font-size:13.5px;max-width:76ch}
.walk .sub{max-width:none}
body.has-sticky .w{padding-bottom:110px}
.pagefoot a{color:var(--a)}
/* ---- document specimens ("what it looks like") ----------------------------
   A pilot feature: images are hotlinked to their original publisher (gov.uk,
   an NGO), never re-hosted, so a broken link degrades to a placeholder rather
   than taking the section down - see the onerror handler in renderSpecimens().
   Most countries have no entry yet; that shows as an honest one-line note
   rather than an empty gap, matching .pmiss elsewhere on this page. */
.spec-head{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;
 color:var(--m);margin:16px 0 8px;font-family:ui-sans-serif,-apple-system,sans-serif}
.spec-grid{display:flex;flex-wrap:wrap;gap:18px;margin:0}
.spec-item{margin:0;flex:1 1 380px;max-width:520px;font-family:ui-sans-serif,-apple-system,sans-serif}
.spec-item img{width:100%;height:auto;max-height:340px;object-fit:contain;
 border:1px solid var(--g);border-radius:6px;background:var(--s);display:block}
.spec-item.broken img{display:none}
.spec-item.broken figure,.spec-item.broken{position:relative}
.spec-item.broken::before{content:"Image unavailable";display:block;padding:60px 10px;
 text-align:center;border:1px dashed var(--g);border-radius:6px;color:var(--m);font-size:12px}
.spec-item figcaption{font-size:11.5px;color:var(--i2);margin-top:6px;line-height:1.4}
.spec-item figcaption a{color:var(--a)}
.spec-note{font-size:13px;color:var(--i2);margin-top:8px;max-width:70ch}
.spec-links{font-size:12.5px;margin-top:6px}
.spec-links a{color:var(--a);margin-right:14px}
/* collapsed-by-default notes, so a long explanation doesn't sit fully open in
   the reading path — same "tuck it behind a button" pattern as map.html's
   help panels and crosswalk.html's "in plain words" toggle. */
button.help{font:inherit;font-size:12.5px;padding:6px 11px;border-radius:8px;
 border:1px dashed var(--g);background:var(--s);color:var(--i2);cursor:pointer;
 margin:2px 0 4px}
button.help.on{border-style:solid}
/* ---- population picker (single choice) + customised preview -------------
   A section of its own, set off from the Length/Language controls above by a
   rule and its own title, so it doesn't read as just another toolbar row. */
.popsection{margin-top:22px;padding-top:18px;border-top:2px solid var(--g)}
.popsection .sectitle{font-family:ui-sans-serif,-apple-system,sans-serif;font-size:11px;
 font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--m);margin:0 0 9px}
.pop{font:inherit;font-size:13px;padding:7px 11px;border-radius:20px;
 border:1px solid var(--g);background:var(--s);color:var(--i2);cursor:pointer}
.pop.on{background:var(--a);color:#fff;border-color:var(--a)}
.pop.nodata{border-style:dashed}
.pophint{font-size:12px;color:var(--m);margin:9px 0 0;max-width:640px}
@media print{body{background:#fff}.bar,select,h1,p.lede,h2,table,.warn,.dlbar,.modpicker,.verhint,.steps,.setup,.sticky,.walk,.edithint,.cardlab,.help,.info,.chk{display:none}
 .form{box-shadow:none;border:0;padding:0}}
@media(max-width:700px){.form{padding:22px 18px}select{min-width:0;width:100%}}
</style>
<script src="https://cdn.jsdelivr.net/npm/html-docx-js@0.3.1/dist/html-docx.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dompurify@3.2.4/dist/purify.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/jspdf@2.5.2/dist/jspdf.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--s:#fff;--p:#fff;--i:#1d2940;--i2:#5a6884;--m:#8b93a8;--g:#e3e8f0;
 --a:#3b71b9;--w:#e0a93b;--paper:#fff}
body{font-family:'IBM Plex Sans',sans-serif !important;background:#fff !important}
h1{font-family:'Figtree',sans-serif !important;color:#14234c !important;font-weight:700 !important;
 letter-spacing:-.015em !important}
h2{font-family:'Figtree',sans-serif !important;color:#14234c !important}
.bar button.on{background:#14234c !important;border-color:#14234c !important}
.pop.on{background:#3b71b9 !important;border-color:#3b71b9 !important}
select,.bar button{border-color:var(--g) !important}
.form{box-shadow:0 1px 3px rgba(20,35,76,.06),0 10px 28px rgba(20,35,76,.08) !important}
.regform{box-shadow:0 1px 3px rgba(20,35,76,.06),0 10px 28px rgba(20,35,76,.08) !important}
</style></head><body><div class="w">
<h1>Build the questionnaire &mdash; steps 1 to 6</h1>
<p class="lede">Build the EGRISS identification questions for one country: the questions and
response options never change; the parts the instrument lets vary &mdash; the examples after each
&ldquo;e.g.&rdquo;, the office and document named when asking about international protection
&mdash; are drafted from what was recorded in that country and shown in <span class="eg">blue</span>.
Choose the country and the populations you need to identify, check and edit the blue text, and
download the questionnaire with its instructions, derivation rules and translation template.</p>
<ol class="steps">
 <li><a id="step0" href="map.html" title="The map: who is displaced here, what displaced them, where claims are lodged"><b>0</b> Where and why</a></li>
 <li><a href="#s1"><b>1</b> Country</a></li>
 <li><a href="#s2"><b>2</b> Who to identify</a></li>
 <li><a href="#s3"><b>3</b> Forced-to-flee question</a></li>
 <li><a href="#s4"><b>4</b> Review and edit</a></li>
 <li><a href="#s5"><b>5</b> Try a respondent</a></li>
 <li><a href="#files"><b>6</b> Your files</a></li>
</ol>

<div class="setup">
<div class="bar" id="s1">
  <span class="grp"><b>1</b> Country</span>
  <select id="pick" hidden></select>
  <div class="cpick" id="cpick">
    <button type="button" class="cpick-btn" id="cpickBtn" aria-haspopup="listbox" aria-expanded="false">
      <span id="cpickLabel">Choose a country</span><span class="cpick-caret">&#9662;</span></button>
    <div class="cpick-menu" id="cpickMenu" hidden>
      <input type="search" id="cpickSearch" placeholder="Type a country&hellip;" autocomplete="off" spellcheck="false">
      <div class="cpick-key"><span class="keylab">Options with local examples:</span><span class="loc loc-hi">5&ndash;7 of 7</span><span class="loc loc-mid">3&ndash;4</span>
        <span class="loc loc-lo">0&ndash;2</span><span class="spec">&#9646; document image</span><span class="spec spec-links">&#9646; document: links only</span></div>
      <div class="cpick-list" id="cpickList" role="listbox"></div>
    </div>
  </div>
</div>

<div class="modpicker" id="modpicker">
 <div class="bar" id="s2">
  <span class="grp"><b>2</b> Who to identify</span>
  <span class="modpresets" id="modpresets">
   <button class="preset" data-p="core">Core items only (shortest)</button>
   <button class="preset" data-p="refugee">Refugees</button>
   <button class="preset" data-p="idp">IDPs</button>
   <button class="preset on" data-p="both">Refugees and IDPs (full)</button>
  </span>
 </div>
 <p class="modsummaryrow"><span class="modsummary" id="modsummary"></span>
  <button type="button" class="help small" id="subsBtn">Choose categories</button></p>
 <div id="moditems" hidden></div>
</div>

<div class="bar" id="s3">
  <span class="grp"><b>3</b> Forced-to-flee question</span>
  <span class="lbl">Version</span>
  <button class="ver on" data-v="3">Long</button>
  <button class="ver" data-v="2">Mid-length</button>
  <button class="ver" data-v="1">Shortest</button>
  <span class="lbl">Examples</span>
  <button class="len on" data-l="read_out">Read aloud (3 examples)</button>
  <button class="len" data-l="showcard">Show card (all examples)</button>
</div>
<div class="bar bar-cont">
  <span class="grp"></span>
  <span class="lbl">How asked</span>
  <button class="adm on" data-a="multi">Choose all that apply</button>
  <button class="adm" data-a="grid">Read out one by one</button>
  <span class="lbl">Language</span>
  <span id="langs"></span>
</div>
<p class="verhint" id="verhint" style="display:none">Shortest and Mid-length are the
other two official variants from the question-testing document — each merges some of
the Long version's options into broader categories, and Mid-length uses an alternate
definition of "forced to flee". Only drafted in English so far; pick English to use them.</p>
<p class="verhint">Version, example length and language apply to the forced-to-flee question;
the rest of the module follows the language and the populations chosen in step 2.</p>

<button type="button" class="help small" id="advBtn">More options: subnational example set, other populations&rsquo; examples</button>
<div class="advanced" id="advanced" hidden>
 <div class="bar">
  <span class="lbl">Subnational example set</span>
  <select id="lvl"></select>
  <span class="advhint">Where a region&rsquo;s recorded events differ from the national picture, its
  own examples replace the national ones in the forced-to-flee question.</span>
 </div>
 <div class="popsection" id="popsection" style="display:none">
  <p class="sectitle">Preview with another population&rsquo;s examples</p>
  <span id="pops"></span>
  <p class="pophint">A refugee from another country is not well served by this country&rsquo;s own
  examples. Pick a population hosted here to see the forced-to-flee question with the examples
  recorded for <i>their</i> country of origin instead.</p>
 </div>
</div>
</div>

<h2 class="step" id="s4"><b>4</b> Review and edit</h2>
<p class="edithint"><span class="swatch" style="background:#3b71b9"></span><b>Anything in blue can be edited: click it.</b>
It was drafted for this country from the databases &mdash; an office renamed, a document everyone
calls something else, an example that does not fit. <span class="swatch" style="background:#7a3fb5"></span><b>Purple</b>
marks your edits: kept in this browser, carried into every file you download and into the link you copy.</p>

<p class="cardlab">Forced-to-flee question &mdash; with this country&rsquo;s examples</p>
<div class="form" id="form"></div>
<div class="info" id="warn"></div>
<button class="help small" id="provbtn">Where these examples come from</button>
<div id="provwrap" hidden>
<p class="sub" style="margin:8px 0 4px">Each example and the record it was drafted from. The map (step 0) shows the same evidence as populations and events: <a id="maplink" href="map.html" target="_blank" rel="noopener">see this country on the map &#8599;</a></p>
<table id="prov"><thead><tr><th>Option</th><th>Example</th><th>Type</th>
<th>Source</th><th>Evidence</th></tr></thead><tbody></tbody></table>
</div>
<div class="editpop" id="editpop" hidden>
 <div class="eplab" id="epLab"></div>
 <textarea id="epText" spellcheck="false"></textarea>
 <div class="ephint" id="epHint"></div>
 <div class="epbtns"><button id="epSave">Save</button><button class="secondary" id="epReset">Use database value</button><button class="plain" id="epCancel">Cancel</button></div>
</div>

<!-- The Apply item as its own localisable card, same shape as the forced-to-flee
     form above: fixed stem, and only the blue example varies by country. Two
     localisation versions are shown - A names the office (the paper's version),
     B names the document (proposed after the paper), with the document's
     specimen as a show card. Hidden when only IDPs are being identified,
     since Apply serves refugee identification. -->
<div class="applysec" id="applysec">
<p class="cardlab">International protection question &mdash; the office and document named here, two versions</p>
<div class="form" id="applyform"></div>
<div class="warn" id="regwarn" style="display:none"></div>
<div class="cav" id="regcav" style="display:none"></div>
</div>

<div class="regcard" id="regcard">
<p class="cardlab">Full questionnaire &mdash; every item, exactly as it downloads</p>
<p class="sub">The two questions above, followed by the rest of the module for the populations
chosen in step 2. Items always asked: forced to flee, country of the home fled, moved to another
country, applied for protection, outcome. Everything else appears because a sub-category you
selected needs it.</p>
<span class="badges" id="regbadges"></span>
<div class="regform" id="regform"></div>
<p class="pmiss" id="regmiss" style="display:none">No office or document is on record for this
country yet. Draft Version A (the office) and Version B (the document) with whoever registers
claims there, then report them so the record is updated.</p>
</div>

<h2 class="step" id="s5"><b>5</b> Try a respondent</h2>
<div class="walk" id="walk">
 <p class="sub">Pick a respondent profile, or set the answers yourself. The questions that would be
 asked are marked in the questionnaire above and the resulting category follows the rules in the
 derivation sheet, for the populations chosen in step 2. Use it for interviewer training and to
 check a programmed form.</p>
 <div class="wkpre" id="wkpre"></div>
 <div class="wkgrid" id="wkgrid"></div>
 <div class="wkres" id="wkres"></div>
</div>

<h2 class="step" id="files"><b>6</b> Your files</h2>
<p class="sub">All five are for the country, populations, version and language chosen above, and
carry your edits.</p>
<div class="dlbar">
  <div class="filegrid">
   <div class="filetile"><div class="filename">Questionnaire</div><div class="filedesc">The two customised questions, the full module, and a table of every customisation.</div>
    <div class="filebtns"><button id="docxBtn">Word</button><button id="pdfBtn" class="secondary">PDF</button></div></div>
   <div class="filetile"><div class="filename">Instructions</div><div class="filedesc">For the coordinator: placement, checks before fielding, pretest protocol. For interviewers: question by question.</div>
    <div class="filebtns"><button id="insDocxBtn">Word</button><button id="insPdfBtn" class="secondary">PDF</button></div></div>
   <div class="filetile"><div class="filename">Derivation sheet</div><div class="filedesc">How answers become categories: the rules, with Stata, R and Python code.</div>
    <div class="filebtns"><button id="derDocxBtn">Word</button><button id="derPdfBtn" class="secondary">PDF</button></div></div>
   <div class="filetile"><div class="filename">Translation template</div><div class="filedesc">Every text with the six UN-language drafts, a column for the survey language, and terminology notes.</div>
    <div class="filebtns"><button id="xlsBtn">Excel</button></div></div>
   <div class="filetile"><div class="filename">KoBo / ODK form</div><div class="filedesc">The module as an XLSForm: skip logic, the valid-reason calculations, the localised lists, six languages. Upload it to KoBo, ODK or SurveyCTO.</div>
    <div class="filebtns"><button id="xlsfBtn">XLSForm</button></div></div>
  </div>
  <div class="dlgrp dltools">
   <button id="chkBtn">Checks before fielding</button>
   <button id="linkBtn">Copy link to this set-up</button>
   <button id="resetBtn" hidden>Reset your edits</button>
   <a id="issueLink" class="dlissue" href="#" target="_blank" rel="noopener">Report a correction</a></div>
  <span class="dlstatus" id="dlStatus"></span>
</div>
<div class="warn chk" id="chkpanel" hidden></div>

<h2 class="step">Sources and caveats</h2>
<p class="sub">These are drafts for review, not enumerator text: the examples come from event
databases, the office and document names from UNHCR help pages and its registration survey, and
the translations are unreviewed.</p>
<button class="help" id="notesbtn">Show the caveats</button>
<div class="warn" id="notespanel" hidden>
<b>The office is where the claim is lodged, never who decides it.</b> Eligibility
panels, appeals boards and hotlines are excluded even where they are well known,
because a respondent never went near them.<br><br>
<b>The office doesn&rsquo;t travel everywhere.</b> In many countries the claim is
lodged online, by post, at a police station, or happens automatically with no
office a respondent would visit &mdash; those are flagged in the card with the actual
channel, so the wording can be adapted rather than asked as written.<br><br>
<b>Source confidence is high, medium or low per country.</b> Check medium and low
against a country source before fielding; the checks list in step 6 says which.<br><br>__SURVEYNOTE__
<b>No IDP document is named.</b> Of the major contexts checked, only a handful have a
verifiable IDP status document; most have none at all, which is a finding about the
instruments, not a gap in the search.<br><br>
<b>The translations are unreviewed.</b> Translating an instrument is a specialist
job &mdash; TRAPD, or forward-and-back translation with reconciliation &mdash;
because a question has to be <i>understood</i> the same way, not merely mean the
same thing. Cognitive testing on an unreviewed translation tests the translation,
not the question.<br><br>
<b>&ldquo;Flee&rdquo; is rendered as leaving under duress, not fleeing in
panic.</b> The item defines it as leaving &ldquo;due to events that posed a
threat&rdquo;, so the sense is compelled departure. Five of these languages have
a default verb that instead means running away in fear &mdash; <i>fuir</i>,
<i>huir</i>, <span dir="rtl">الفرار</span>, <i>спасаясь бегством</i>,
<i>逃离</i> &mdash; and each of those invites a respondent to picture a panicked
escape and answer &ldquo;no&rdquo; if their own departure was deliberate: packing
over days, or leaving after a threat rather than during an attack. That is exactly
the population these questions exist to count. All five now use a duress
construction.<br><br>
<b>Still open:</b> <b>persecution</b>, a legal term of art in the refugee
definition that in everyday registers reads as ordinary harassment &mdash; a
materially different threshold, and not something an automatic process can
settle.<br><br>
<b>The names are UCDP&rsquo;s, not a respondent&rsquo;s.</b> UCDP writes
&ldquo;JAS&rdquo; where a Nigerian respondent says Boko Haram. Actor names are
never translated &mdash; they are proper nouns.<br><br>
<b>Identity groups are never named.</b> UCDP codes communal violence as, for
example, &ldquo;Christians (Nigeria) &ndash; Muslims (Nigeria)&rdquo;, and at
subnational level as named ethnic groups. Correct as conflict coding, unusable in
an instrument a government enumerator reads aloud. Those become &ldquo;communal or
intercommunal violence&rdquo;.<br><br>
<b>Naming actors risks anchoring.</b> Someone displaced by a group not named may
conclude the option does not cover them. Category phrasing is preferred where the
data allows, and every example is tagged with which it is.<br><br>
<b>Subnational sets appear only where they say something different.</b> A region
whose examples merely repeat the national list is not shown.
</div>
<div class="sticky" id="sticky" hidden>
 <span class="stickyc" id="stickyC"></span>
 <button data-for="docxBtn">Questionnaire</button>
 <button data-for="insDocxBtn">Instructions</button>
 <button data-for="derDocxBtn">Derivation sheet</button>
 <button data-for="xlsBtn">Translation template</button>
 <button data-for="xlsfBtn">XLSForm</button>
 <a href="#files">All formats &darr;</a>
</div>
<p class="pagefoot" id="pagefoot"></p>
</div><script>
const Q=__DATA__, P=__PROV__, T=__T__, LANGS=__LANGS__, REG=__REG__, REGLABEL=__REGLABEL__, SPEC=__SPEC__, M=__M__, META=__META__, MF=__MF__;
const CODES=[1,2,3,4,5,6,7,8];
const LBL={1:"1. Armed conflict",2:"2. Widespread violence",3:"3. Persecution",
 4:"4. HR violations",5:"5. Other violence",6:"6. Natural disasters",
 7:"7. Man-made events",8:"8. A different threat"};
let LEN="read_out", LANG=null, ADM=-1, POP=null, VER=3;   // POP: index into v.populations, or null (= national/default)
// VER: which of the three official FrcFl variants from "Question Variants for
// Cognitive interviewing.docx" is shown — 3 (Long, today's 9-line version, the
// only one with per-language translations) is the default; 1 (Shortest) and 2
// (Mid-length, alternate definition) merge several Long options into broader
// categories and are drafted in English only, so picking a non-English language
// forces VER back to 3 (see buildLangs()).

// ---- hand edits ------------------------------------------------------------
// Every blue customisation is a "slot" the coordinator can overwrite: the
// office and document names, the example lists, the FrcFl examples per
// option. Edits live in this browser (localStorage), are applied on top of
// the database values at render time (effReg / effCust / edited example
// lists), and are encoded in the page URL so a set-up can be shared.
const SLOTS={
 org:{label:"Office named in Apply, Version A",hint:"The office where a claim is lodged, as a respondent would know it. One name."},
 da:{label:"Asylum-applicant document (Apply Version B, Legal)",hint:"What the document issued while a claim is pending is called here. One name."},
 dr:{label:"Refugee document (Legal)",hint:"What the document issued on recognition is called here. One name."},
 origins:{label:"FleeLoc — 'other country' examples",hint:"Separate with commas.",list:true},
 dest:{label:"FleeCross — destination examples",hint:"Separate with commas.",list:true},
 adm:{label:"IDPLoc / IDPPost — subnational examples",hint:"Separate with commas.",list:true},
 dtm:{label:"FrcOth — reasons heard in this country",hint:"Separate with commas.",list:true},
};
SLOTS.frcothvalid={label:"FrcOth \u2014 reasons that count as a valid cause of forced displacement here",hint:"Set with the tick boxes on the FrcOth item; recorded in every download.",list:true};
for(let c=1;c<=8;c++) SLOTS["eg"+c]={label:"Forced to flee — examples for option "+c,hint:"Separate with commas. Read aloud shows the first three; the show card shows all.",list:true};
[1,2].forEach(vv=>[0,1,2,3,4,5].forEach(i=>SLOTS[`b${vv}_${i}`]={label:`${VERSION_DEFS_LABEL(vv)} version — examples for option ${i+1}`,hint:"Separate with commas.",list:true}));
function VERSION_DEFS_LABEL(v){ return v===1?"Shortest":"Mid-length"; }
let EDITS={}; try{ EDITS=JSON.parse(localStorage.getItem('idq_edits')||'{}')||{}; }catch(e){ EDITS={}; }
function edSave(){ try{ localStorage.setItem('idq_edits',JSON.stringify(EDITS)); }catch(e){} }
function edGet(iso,slot){ const e=EDITS[iso]; return (e&&Object.prototype.hasOwnProperty.call(e,slot))?e[slot]:undefined; }
function edSet(iso,slot,val){
 EDITS[iso]=EDITS[iso]||{};
 if(val==null||val==="") delete EDITS[iso][slot]; else EDITS[iso][slot]=val;
 if(!Object.keys(EDITS[iso]).length) delete EDITS[iso];
 edSave(); }
function edClear(iso){ delete EDITS[iso]; edSave(); }
function edCount(iso){ return Object.keys(EDITS[iso]||{}).length; }
const edList=s=>String(s).split(/\s*[,;]\s*|\\n+/).map(x=>x.trim()).filter(Boolean);
const isEdited=slot=>edGet(sel.value,slot)!==undefined;
// Which of FrcOth's eleven back-coding reasons count as a valid cause of
// forced displacement in this country. The default is the set fielded in the
// FDS (conscription, fear of violent crime, political insecurity or civil
// unrest, family violence) - a starting point to confirm, not a rule. Indices
// are positions in M[LANG].frcoth.list, which is the paper's own order.
const FRCOTH_DEFAULT=[0,2,3,6];
function frcothValid(iso){
 const v=edGet(iso||sel.value,"frcothvalid");
 if(v===undefined) return FRCOTH_DEFAULT.slice();
 return String(v).split(",").map(x=>parseInt(x,10)).filter(x=>!isNaN(x));
}
function frcothNames(iso){
 const list=(M.en.frcoth.list||[]);
 return frcothValid(iso).map(i=>list[i]?String(list[i][0]).replace(/<[^>]+>/g,""):"").filter(Boolean);
}
// Edited example list for an FrcFl option (or a Shortest/Mid-length bucket),
// or null when the database list stands.
function edEg(slot){ const v=edGet(sel.value,slot); return v===undefined?null:edList(v); }
// The registration record with the coordinator's edits laid over it. An
// edited name replaces the local-language and everyday variants too - what
// they typed is what gets read out.
function effReg(iso){
 const r=REG[iso]; if(!r) return r;
 const e=EDITS[iso]; if(!e) return r;
 const o=Object.assign({},r);
 if(e.org!=null){ o.org=e.org; o.orgL=null; o.alt=[]; }
 if(e.da!=null){ o.da=e.da; o.daL=null; o.daC=null; }
 if(e.dr!=null){ o.dr=e.dr; o.drL=null; o.drC=null; }
 return o; }
function effCust(iso){
 const q=Q[iso]||{}, c=Object.assign({},q.cust||{}), e=EDITS[iso]||{};
 ["origins","dest","adm"].forEach(k=>{ if(e[k]!=null) c[k]=edList(e[k]); });
 if(e.dtm!=null) c.dtm=edList(e.dtm).map(x=>[x,null]);
 return c; }
function editedRows(iso){
 return Object.entries(EDITS[iso]||{}).map(([k,v])=>({slot:k,label:(SLOTS[k]||{label:k}).label,value:v})); }

// ---- the page state in the URL, so a set-up can be shared -----------------
function stateToHash(){
 const iso=sel.value;
 const p=new URLSearchParams();
 p.set("c",iso); p.set("v",String(VER)); p.set("len",LEN); p.set("lang",LANG||"en"); p.set("adminmode",ADMIN);
 if(ADM>=0) p.set("adm",String(ADM));
 if(POP!=null) p.set("pop",String(POP));
 p.set("fw",[FW.idp?"idp":null,FW.refugee?"refugee":null].filter(Boolean).join(",")||"none");
 p.set("sub",SUBCATS.filter(c=>SUB[c.key]).map(c=>c.key).join(",")||"none");
 if(EDITS[iso]) p.set("e",JSON.stringify(EDITS[iso]));
 return "#"+p.toString(); }
function syncHash(){ try{ history.replaceState(null,"",location.pathname+location.search+stateToHash()); }catch(e){} }
// Reads the hash; returns true when it named a country. Applied in two steps
// around pickCountry() (which resets LANG/ADM/POP), see the bottom of the file.
function hashState(){
 const h=location.hash.replace(/^#/,""); if(!h) return null;
 try{ return new URLSearchParams(h); }catch(e){ return null; } }
function applyHashAfterPick(p){
 if(!p) return;
 const v=Q[sel.value];
 if(p.get("lang")&&LANGS[p.get("lang")]) LANG=p.get("lang");
 if(p.get("v")&&[1,2,3].includes(+p.get("v"))) VER=+p.get("v");
 if(p.get("len")&&["read_out","showcard"].includes(p.get("len"))) LEN=p.get("len");
 if(p.get("adminmode")&&["multi","grid"].includes(p.get("adminmode"))) ADMIN=p.get("adminmode");
 if(p.get("adm")!=null&&v.adm1&&v.adm1[+p.get("adm")]) ADM=+p.get("adm");
 if(p.get("pop")!=null&&(v.populations||[])[+p.get("pop")]) POP=+p.get("pop");
 if(p.get("fw")){ const f=p.get("fw").split(","); FW.idp=f.includes("idp"); FW.refugee=f.includes("refugee"); if(!FW.idp&&!FW.refugee){FW.idp=true;FW.refugee=true;} }
 if(p.get("sub")){ const s=p.get("sub").split(","); SUBCATS.forEach(c=>SUB[c.key]=s.includes(c.key)); }
 // From the map's drafting brief: a preset name and a population to preview
 if(p.get("preset")){ const pr=p.get("preset");
  if(pr==="core"){ FW.idp=true; FW.refugee=true; setAllSubs(false); }
  else if(pr==="refugee"){ FW.idp=false; FW.refugee=true; setAllSubs(true); }
  else if(pr==="idp"){ FW.idp=true; FW.refugee=false; setAllSubs(true); }
  else { FW.idp=true; FW.refugee=true; setAllSubs(true); } }
 if(p.get("popn")){ const i=(v.populations||[]).findIndex(x=>x.name===p.get("popn")&&x.kind!=="national"); if(i>=0){ POP=i; ADM=-1; } }
 if(p.get("e")){ try{ const e=JSON.parse(p.get("e")); if(e&&typeof e==="object"){ EDITS[sel.value]=Object.assign({},EDITS[sel.value]||{},e); edSave(); } }catch(err){} }
 document.querySelectorAll('.len').forEach(b=>b.classList.toggle('on',b.dataset.l===LEN));
 document.querySelectorAll('.adm').forEach(b=>b.classList.toggle('on',b.dataset.a===ADMIN));
 lvl.value=String(ADM);
}
const VERSION_DEFS={
 1:{label:"Shortest",
  stem2:"By this we mean leaving a home, or land, due to events that posed a "+
        "threat to you or your family's safety.",
  buckets:[
   {label:"Threat of <b>armed conflict</b> or <b>widespread violence</b>", codes:[1,2]},
   {label:"Threat of <b>persecution</b> or <b>human rights violation</b>", codes:[3,4]},
   {label:"<b>Natural</b> or <b>man-made disaster</b>", codes:[6,7]},
   {label:"A <b>different threat</b> to your safety", codes:[8], specify:true},
  ]},
 2:{label:"Mid-length",
  stem2:"By this we mean being unable to continue to live in an area due to "+
        "risks to you or your family.",
  buckets:[
   {label:"Threat of <b>armed conflict</b> or <b>widespread violence</b>", codes:[1,2]},
   {label:"Threat of <b>persecution</b>", codes:[3],
    generic:"due to your background, religion or political beliefs"},
   {label:"Threat of <b>human rights violation</b>", codes:[4], generic:"detention, torture"},
   {label:"<b>Natural disasters</b>", codes:[6],
    generic:"floods, droughts, landslides, earthquakes, hurricanes"},
   {label:"<b>Man-made events</b>", codes:[7],
    generic:"eviction for infrastructure projects, pollution events"},
   {label:"A <b>different threat</b> to your safety", codes:[8], specify:true},
  ]},
};
const sel=document.getElementById('pick'), lvl=document.getElementById('lvl');
function fmtN(n){
 n=+n||0;
 if(n>=1000000)return (n/1000000).toFixed(1).replace(/\.0$/,"")+"M";
 if(n>=1000)return (n/1000).toFixed(1).replace(/\.0$/,"")+"k";
 return String(n);}
const COUNTRY_ROWS=Object.entries(Q).sort((a,b)=>a[1].name.localeCompare(b[1].name)).map(([k,v])=>{
 const sp=SPEC[k], nImg=(sp&&sp.images)?sp.images.length:0, nLinks=(sp&&sp.links)?sp.links.length:0;
 const o=document.createElement('option'); o.value=k; o.textContent=v.name; sel.appendChild(o);
 return {iso:k,name:v.name,n:v.n_localised,nImg,nLinks};});
function locBadge(n){ return `<span class="loc ${n>=5?"loc-hi":n>=3?"loc-mid":"loc-lo"}" title="${n} of the 7 forced-to-flee options have country-specific examples">${n}/7 with local examples</span>`; }
function specBadge(r){
 if(r.nImg) return `<span class="spec" title="An image of the protection document is on file">&#9646; ${r.nImg===1?"document image":r.nImg+" document images"}</span>`;
 if(r.nLinks) return `<span class="spec spec-links" title="Links to where the document is shown, no image on file">&#9646; document: links only</span>`;
 return ""; }
function cpickRender(q){
 q=(q||"").trim().toLowerCase();
 const rows=COUNTRY_ROWS.filter(r=>!q||r.name.toLowerCase().includes(q)||r.iso.toLowerCase()===q);
 document.getElementById('cpickList').innerHTML=rows.map((r,i)=>
  `<div class="cpick-row${r.iso===sel.value?" on":""}${i===0&&q?" sel":""}" data-iso="${r.iso}" role="option">`+
  `<span class="cpick-name">${esc(r.name)}</span>${locBadge(r.n)}${specBadge(r)}</div>`).join("")||
  `<div class="cpick-row" style="color:var(--m)">No country matches</div>`;
 document.querySelectorAll('.cpick-row[data-iso]').forEach(el=>el.addEventListener('click',()=>cpickChoose(el.dataset.iso)));}
function cpickLabel(){
 const r=COUNTRY_ROWS.find(x=>x.iso===sel.value); if(!r) return;
 document.getElementById('cpickLabel').innerHTML=`${esc(r.name)} ${locBadge(r.n)}${specBadge(r)}`;}
function cpickOpen(open){
 const m=document.getElementById('cpickMenu'), b=document.getElementById('cpickBtn');
 m.hidden=!open; b.setAttribute('aria-expanded',open?"true":"false");
 if(open){const i=document.getElementById('cpickSearch'); i.value=""; cpickRender(""); i.focus();
  const on=m.querySelector('.cpick-row.on'); if(on) on.scrollIntoView({block:"center"});}}
function cpickChoose(iso){ sel.value=iso; cpickOpen(false); cpickLabel(); pickCountry(); }
document.getElementById('cpickBtn').addEventListener('click',e=>{e.stopPropagation(); cpickOpen(document.getElementById('cpickMenu').hidden);});
document.getElementById('cpickSearch').addEventListener('input',e=>cpickRender(e.target.value));
document.getElementById('cpickSearch').addEventListener('keydown',e=>{
 if(e.key==="Escape"){cpickOpen(false);}
 if(e.key==="Enter"){const first=document.querySelector('.cpick-row.sel[data-iso],.cpick-row[data-iso]'); if(first) cpickChoose(first.dataset.iso);}});
document.addEventListener('click',e=>{ if(!document.getElementById('cpick').contains(e.target)) cpickOpen(false); });
function esc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;");}

function buildLangs(){
 document.getElementById('langs').innerHTML=Object.entries(LANGS)
  .map(([k,v])=>`<button class="lang${k===LANG?' on':''}" data-k="${k}">${v[0]}</button>`)
  .join(" ");
 document.querySelectorAll('.lang').forEach(b=>b.addEventListener('click',()=>{
  LANG=b.dataset.k; syncVerButtons(); buildLangs(); render(); renderReg(sel.value);}));
 syncVerButtons();}

// Shortest/Mid-length (VER 1/2) are English-only drafts (see VER's comment) —
// disabled rather than hidden when another language is picked, so it's obvious
// they exist without silently mixing an English question structure into a
// non-English preview. Also the single place that enforces "VER can only be
// 1 or 2 when LANG is English" — called from every path that changes either
// (pickCountry, the language buttons, and the version buttons themselves) so
// render() never has to re-check the invariant itself.
function syncVerButtons(){
 const enOnly=LANG!=="en";
 if(enOnly)VER=3;
 document.querySelectorAll('.ver').forEach(b=>{
  const isEn3=b.dataset.v==="3";
  b.disabled=enOnly&&!isEn3;
  b.classList.toggle('on',+b.dataset.v===VER);});
 document.getElementById('verhint').style.display=enOnly?"":"none";}
document.querySelectorAll('.ver').forEach(b=>b.addEventListener('click',()=>{
 if(b.disabled)return;
 VER=+b.dataset.v; syncVerButtons(); render();}));

function buildLevels(v){
 lvl.innerHTML=`<option value="-1">National examples</option>`+
  (v.adm1||[]).map((r,i)=>`<option value="${i}">${esc(r.name)} — ${r.events.toLocaleString()} events</option>`).join("");
 lvl.disabled=!(v.adm1&&v.adm1.length);
 if(ADM>=(v.adm1||[]).length)ADM=-1;
 lvl.value=String(ADM);}

// Builds the "<ol class=opts>" list for any population's own form/localised data —
// shared by the main form (region-aware) and the per-population preview blocks
// below (national form, no region — see the design note on why previews don't
// cross with the selected admin1 level).
// How the forced-to-flee options are administered. "multi" is the paper's
// choose-all-that-apply list; "grid" reads each option out and codes Yes/No
// for each - what the FDS fields, and the only workable form with respondents
// who cannot read a show card or who are interviewed by telephone.
let ADMIN="multi";
const optBox=()=>{ if(ADMIN!=="grid") return `<span class="box"></span>`;
 const u=MT().ui;
 return `<span class="ynbox"><span class="box"></span><i>${esc(u.yes)}</i>`+
        `<span class="box"></span><i>${esc(u.no)}</i></span>`; };
function optsListHTML(data, lang, t, lim, region){
 let h=`<ol class="opts${ADMIN==="grid"?" grid":""}">`;
 CODES.forEach(c=>{
  // a hand edit wins; otherwise region examples override the national ones
  // for the codes they cover
  let items=null, generic=false;
  const ed=edEg("eg"+c);
  if(ed){
   items=ed;
  }else if(region&&region.ex[String(c)]){
   items=region.ex[String(c)].map(e=>e.text);
  }else{
   const row=(data.form||[]).find(x=>x.code===c);
   if(row&&row.n){items=(lang==="en"?row.eg:row.eg_t);
     generic=!(data.localised||[]).includes(c);}
  }
  let eg="";
  if(items&&items.length){
   const use=items.slice(0,lim), more=items.length-use.length;
   eg=` <span class="eg ${generic?'gen':''}${ed?' edited':''}" data-slot="eg${c}"><span class="lab">${esc(t.eg)}</span> `+
      `${esc(use.join(", "))}</span>`+
      (more?` <span class="more">${esc(t.more.replace("{n}",more))}</span>`:``);}
  else eg=` <span class="eg gen egadd" data-slot="eg${c}" title="No examples recorded for this option — click to add your own"><span class="lab">${esc(t.eg)}</span> add your own</span>`;
  h+=`<li>${optBox()}<span class="num">${c}</span>`+
     `<span class="otext">${t.opts[c]}${c===8?" "+esc(t.specify):""}${eg}</span></li>`;});
 h+=`<li>${optBox()}<span class="num">99</span>`+
    `<span class="otext">${esc(t.none)}${ADMIN==="grid"?"":` <span class="excl">${esc(t.excl)}</span>`}`+
    `</span></li></ol>`;
 return h;}

// Looks up one Long-form code's examples the same way optsListHTML does (region
// override, else the country/population's own form data) — shared so Shortest/
// Mid-length can pool several codes' real examples into one merged bucket rather
// than duplicating the lookup.
function codeItems(data, region, code){
 if(region&&region.ex[String(code)])
  return {items:region.ex[String(code)].map(e=>e.text), real:true};
 const row=(data.form||[]).find(x=>x.code===code);
 if(row&&row.n)
  return {items:row.eg, real:(data.localised||[]).includes(code)};
 return {items:[], real:false};
}

// Shortest/Mid-length variants (VER 1/2) — English only (see VER's comment).
// Each bucket merges one or more Long-form codes; real examples from every
// merged code are pooled, falling back to the bucket's own generic text (from
// the question-testing document) only when none of them have real evidence.
function versionOptsHTML(data, lim, region){
 const def=VERSION_DEFS[VER];
 let h=`<ol class="opts${ADMIN==="grid"?" grid":""}">`, nReal=0, nBeyond=0;
 def.buckets.forEach((b,i)=>{
  let items=[];
  const slot=`b${VER}_${i}`, ed=edEg(slot);
  if(ed) items=ed;
  else b.codes.forEach(code=>{
   const r=codeItems(data, region, code);
   if(r.real) items=items.concat(r.items);
  });
  let eg="", generic=false;
  if(items.length){
   nReal++;
   const use=items.slice(0,lim), more=items.length-use.length;
   nBeyond+=Math.max(0,more);
   eg=` <span class="eg${ed?' edited':''}" data-slot="${slot}"><span class="lab">e.g.</span> ${esc(use.join(", "))}</span>`+
      (more?` <span class="more">+${more} more recorded</span>`:``);
  } else if(b.generic){
   generic=true;
   eg=` <span class="eg gen" data-slot="${slot}"><span class="lab">e.g.</span> ${esc(b.generic)}</span>`;
  } else eg=` <span class="eg gen egadd" data-slot="${slot}" title="No examples recorded for this option — click to add your own"><span class="lab">e.g.</span> add your own</span>`;
  h+=`<li>${optBox()}<span class="num">${i+1}</span>`+
     `<span class="otext">${b.label}${b.specify?" [SPECIFY]":""}${eg}</span></li>`;});
 h+=`<li>${optBox()}<span class="num">99</span>`+
    `<span class="otext">None of the above${ADMIN==="grid"?"":` <span class="excl">[EXCLUSIVE CODE]</span>`}`+
    `</span></li></ol>`;
 return {html:h, nBuckets:def.buckets.length, nReal, nBeyond};}

// Population radio buttons — national/IDP + each major refugee-origin population
// hosted here, as computed in build_questions.py's "hosted populations" block.
// Single choice: picking a population FLIPS the main form itself (see render())
// to show that population's own examples — no separate card. Picking "National"
// (or re-clicking the active button) flips back, since the main form's default
// state already IS the national/IDP view.
function buildPops(v){
 const sect=document.getElementById('popsection'), wrap=document.getElementById('pops');
 const pops=v.populations||[];
 if(!pops.length){sect.style.display="none";wrap.innerHTML="";return;}
 sect.style.display="";
 wrap.innerHTML=pops.map((p,i)=>{
  const label=p.kind==="national"?`${esc(p.name)}&rsquo;s own (national) examples`:
              p.kind==="refugee"?`Refugees from ${esc(p.name)}`:esc(p.name);
  return `<button class="pop${POP===i?' on':''}${p.has_data?'':' nodata'}" `+
   `data-i="${i}" data-kind="${p.kind}" `+
   `title="${p.has_data?'':'no country-specific examples available for this population — '}${fmtN(p.n)} people">`+
   `${label}${p.kind!=="national"&&p.n?` <span style="opacity:.7">(${fmtN(p.n)})</span>`:""}</button>`;}).join(" ");
 wrap.querySelectorAll('.pop').forEach(b=>b.addEventListener('click',()=>{
  const i=+b.dataset.i;
  POP=(b.dataset.kind==="national"||POP===i)?null:i;
  if(POP!=null){ADM=-1;lvl.value="-1";}   // a region of the HOST doesn't apply to another population's own form
  buildPops(v); render();}));}

// Which data the forced-to-flee form is drawn from right now. POP picks which
// population's own data flips into the SAME form/warn/provenance area — the
// host's own view (region-aware) when POP is null, or that population's own
// origin-country data (Q[pop.iso3]) when it's set. No source means the generic
// wording only, rendered honestly rather than falling back to the host's
// examples. Shared by render() and the editor's "database value" lookup.
function formData(){
 const iso=sel.value, v=Q[iso];
 const pop=(POP!=null)?(v.populations||[])[POP]:null;
 const usingPop=!!(pop&&pop.kind!=="national");
 const dataIso=usingPop&&pop.has_data&&pop.iso3&&Q[pop.iso3]?pop.iso3:null;
 const data=usingPop?(dataIso?Q[dataIso]:{form:[],localised:[]}):v;
 const region=(!usingPop&&ADM>=0)?(v.adm1||[])[ADM]:null;
 return {v,pop,usingPop,dataIso,data,region};
}
// The database examples for one FrcFl code as the form would show them now
// (region override, else the population/country row, in the page language).
function baseItems(c){
 const {data,region}=formData();
 if(region&&region.ex[String(c)]) return region.ex[String(c)].map(e=>e.text);
 const row=(data.form||[]).find(x=>x.code===c);
 if(row&&row.n) return (LANG==="en"?row.eg:row.eg_t)||[];
 return [];
}

function render(){
 const iso=sel.value, v=Q[iso], t=T[LANG]||T.en, dir=(LANGS[LANG]||["","ltr"])[1];
 const lim=LEN==="read_out"?3:8;
 const {pop,usingPop,dataIso,data,region}=formData();
 lvl.disabled=usingPop||!(v.adm1&&v.adm1.length);

 const f=document.getElementById('form');
 f.setAttribute('dir',dir);
 f.classList.toggle('custom',usingPop);
 const banner=!usingPop?``:dataIso
  ?`<div class="custombanner">Customised preview &mdash; showing ${esc(pop.name)}&rsquo;s `+
   `own examples in place of ${esc(v.name)}&rsquo;s</div>`
  :`<div class="custombanner">No country-specific examples are available for `+
   `${esc(pop.name)} yet &mdash; showing the questionnaire&rsquo;s generic wording only.</div>`;
 const stem2=VER===3?t.stem2:VERSION_DEFS[VER].stem2;
 let h=banner+`<div class="fhead"><span class="fitem">${t.item}</span>`+
   `<span class="fask">${esc(t.ask)}</span>`+
   `<span class="fcountry">${esc(v.name)}${region?" · "+esc(region.name):""}`+
   `${usingPop?" · "+esc(pop.name):""}</span></div>`+
   `<p class="stem">${t.stem1}</p><p class="stem">${stem2}</p>`+
   `<p class="lead">${esc(t.lead)}</p>`+
   `<div class="instr">${esc(ADMIN==="grid"?MT().ui.instr_grid:t.instr)}</div>`;
 const verResult=VER===3?null:versionOptsHTML(data, lim, region);
 h+=VER===3?optsListHTML(data, LANG, t, lim, region):verResult.html;
 f.innerHTML=h;
 syncChainFrcFl();

 const provIso=usingPop?dataIso:iso;
 const rows=P.filter(r=>r.iso3===provIso);
 const miss=rows.filter(r=>r.kind==="generic"||r.kind==="none").length;
 document.getElementById('warn').innerHTML=(usingPop&&!dataIso)?
  `<b>No source data exists yet for ${esc(pop.name)} in this pipeline.</b> `+
  `All options show the questionnaire's generic wording, the same as any `+
  `country this project hasn't reached.`:
  VER===3?(
  `<b>${data.n_localised} of 7 options carry country-specific examples, `+
  `${data.n_available} in total.</b> ${miss} still use the questionnaire's generic `+
  `wording or none at all. `+
  (data.n_beyond_read_out?`<b>${data.n_beyond_read_out} more examples are recorded</b> `+
    `than belong in a read-aloud list — the show card includes them. `:``)+
  (!usingPop?((v.adm1&&v.adm1.length)?`<b>${v.adm1.length} subnational example sets</b> differ from the `+
    `national one — under &ldquo;More options&rdquo; in step 3. `:`No subnational set differs enough from `+
    `the national one to be worth showing. `):``)+
  (LANG!=="en"?`<b>The ${LANGS[LANG][0]} text is an unreviewed draft translation.</b>`:``)
  ):(
  `<b>${verResult.nReal} of ${verResult.nBuckets} options carry country-specific `+
  `examples</b> once the Long version's options are merged into ${VERSION_DEFS[VER].label}'s `+
  `broader categories. ${verResult.nBuckets-verResult.nReal} use generic wording or none at all. `+
  (verResult.nBeyond?`<b>${verResult.nBeyond} more examples are recorded</b> than belong in a `+
    `read-aloud list — the show card includes them. `:``)+
  `<b>${VERSION_DEFS[VER].label} is drafted in English only</b> — the official variant from `+
  `the question-testing document, not yet translated.`
  );
 document.querySelector('#prov tbody').innerHTML=rows.map(r=>
  `<tr><td>${LBL[r.code_id]||r.code_id}</td><td>${esc(r.example||"—")}</td>`+
  `<td><span class="k k-${r.kind}">${r.kind}</span></td><td>${r.source||"—"}</td>`+
  `<td style="color:var(--i2)">${esc(r.evidence||"")}`+
  (r.in_read_out===false?`<div class="ro">show card only</div>`:``)+`</td></tr>`).join("");
 syncHash();}

// Registration (international protection) card — a different question item
// from the flee-question form above, so it doesn't move with LEN/LANG/POP/ADM;
// only the selected country matters. Same probe-card structure as
// build_protection.py's own per-country render(), inlined here instead of on
// a separate page. See protection.py for what v1/v2/registrar/confidence mean.
// The optional items in the combined refugee/IDP module, from "Review of
// Existing Measures_JD (1).docx"'s "Short and long form versions of module"
// table — each one's `why` is that table's own rationale for keeping it.
// FrcFl, FleeLoc, FleeCross, Apply and Outcome are core (Table X: "Yes") and
// always render; everything here is optional (Table X: "No") and gated by its
// own checkbox, grouped under whichever framework(s) it unlocks a sub-category
// for. None of these carry country-specific localisation the way Apply does —
// the wording is fixed, so they render identically for every country.
// The optional items, named as the paper names them, with Table X's rationale.
const OPT_ITEMS={
 frcoth:{name:"FrcOth", label:"Other reasons for fleeing",
  why:"More detailed reasons for fleeing, more room to localise examples and valid codes, and a check against false positives."},
 idploc:{name:"IDPLoc", label:"Location of IDP displacement",
  why:"Sub-categorises IDPs into location of displacement and location of return."},
 idppost:{name:"IDPPost", label:"IDP first location post fleeing",
  why:"Sub-categorises IDPs into location of displacement or location of other settlement."},
 locliv:{name:"LocLiv / CitLoc", label:"Whether had always lived in, or was a citizen of, the country of displacement",
  why:"Must be captured in some way to classify IDP stocks; need not be asked here if citizenship is captured elsewhere in the survey."},
 mnths12:{name:"12Mnths", label:"Whether stayed abroad for at least 12 months",
  why:"Sub-categorises IDPs into a returning-migrant category."},
 intapply:{name:"IntApply", label:"Whether intended to apply for international protection",
  why:"Needed for the refugee sub-category ‘prospective asylum seeker’."},
 legal:{name:"Legal", label:"Main document allowing the respondent to stay",
  why:"Distinguishes temporary, complementary and permanent protection; identifies naturalised former refugees and people with protected status but no displacement history."},
};
const CORE_ITEMS="FrcFl, FleeLoc, FleeCross, Apply, Outcome";
// The population categories of the two statistical frameworks, as laid out
// in the 2023 methodological paper (IRRS: persons in need of international
// protection / with a refugee background / returned from abroad after seeking
// international protection; IRIS: the IDP stock and its three location
// sub-categories, the IDP-related populations, and those who have overcome
// key displacement-related vulnerabilities), each mapped to what the revised
// module can do about it (Classification Table of the question-testing
// document):
//   items  - optional items beyond the core that the category needs; a
//            category with none is identified by the core items alone
//   core   - identified by the core questionnaire; shown, no checkbox
//   na     - not identifiable from these questions: "roster" (household
//            relationship/parent variables), "extra" (additional questions
//            still to be developed), "composite" (the end-of-displacement
//            composite measure)
// Ticking a category is what switches its items on; the items themselves are
// never picked directly, so the questionnaire always follows from a
// population someone actually wants to identify.
const SUBCATS=[
 // ---- IRRS a. Persons in need of international protection ----
 {key:"prospective", fw:"refugee", grp:"a. Persons in need of international protection", label:"Prospective asylum seekers",
  cond:"Fled a home in another country; Apply = No and IntApply = Yes", items:["intapply"]},
 {key:"asylum", fw:"refugee", grp:"a. Persons in need of international protection", label:"Asylum seekers", core:true,
  cond:"Fled a home in another country; Apply = Yes and Outcome = still being decided", items:[]},
 {key:"refugee", fw:"refugee", grp:"a. Persons in need of international protection", label:"Refugees", core:true,
  cond:"Fled a home in another country; Apply = Yes and Outcome = granted", items:[]},
 {key:"complementary", fw:"refugee", grp:"a. Persons in need of international protection", label:"Admitted for complementary and subsidiary forms of protection",
  cond:"Fled a home in another country; Legal = complementary and subsidiary protection", items:["legal"]},
 {key:"temporary", fw:"refugee", grp:"a. Persons in need of international protection", label:"Admitted for temporary protection",
  cond:"Fled a home in another country; Legal = temporary protection", items:["legal"]},
 {key:"reflike", fw:"refugee", grp:"a. Persons in need of international protection", label:"Others in refugee-like situations",
  cond:"Fled a home in another country; Apply = No, IntApply = No, Legal = a visa or a regional free-movement agreement", items:["intapply","legal"]},
 // ---- IRRS b. Persons with a refugee background ----
 {key:"naturalised", fw:"refugee", grp:"b. Persons with a refugee background", label:"Naturalised former refugees",
  cond:"Apply = Yes, Outcome = granted, Legal = permanent residence or citizenship", items:["legal"]},
 {key:"refchild", fw:"refugee", grp:"b. Persons with a refugee background", label:"Children born of refugee parents", na:"roster",
  cond:"From the household roster: child of a person identified as a refugee, naturalised former refugee or repatriating refugee", items:[]},
 {key:"reunified", fw:"refugee", grp:"b. Persons with a refugee background", label:"Reunified refugee family members from abroad", na:"extra",
  cond:"Additional questions still to be developed (paper, p. 20)", items:[]},
 {key:"refbackground", fw:"refugee", grp:"b. Persons with a refugee background", label:"Others with a refugee background",
  cond:"The module's approximation: no history of forced displacement but Legal = a protected-status document (Classification Table); spouses and other family members of refugees come from the roster", items:["legal"]},
 // ---- IRRS c. Persons returned from abroad after seeking international protection ----
 {key:"repref", fw:"refugee", grp:"c. Returned from abroad after seeking international protection", label:"Repatriating refugees", core:true,
  cond:"Fled a home in this country, moved to another country, Apply = Yes and Outcome = granted", items:[]},
 {key:"repas", fw:"refugee", grp:"c. Returned from abroad after seeking international protection", label:"Repatriating asylum seekers", core:true,
  cond:"Fled a home in this country, moved to another country, Apply = Yes and Outcome = pending, denied or withdrawn", items:[]},
 {key:"retprot", fw:"refugee", grp:"c. Returned from abroad after seeking international protection", label:"Returning from international protection abroad / others returning from seeking it",
  cond:"Fled a home in this country, moved to another country for 12 months or more, Apply = No; the module cannot separate these two categories from each other or from returning migrants (paper, p. 17)", items:["mnths12"]},
 // ---- IRIS 1. Total stock of IDPs ----
 {key:"idpdisp", fw:"idp", grp:"1. Total stock of IDPs", label:"IDPs in locations of displacement",
  cond:"Fled a home in this country and did not establish residence or seek protection abroad; current location = the first location moved to (IDPPost)", items:["idppost"]},
 {key:"idpret", fw:"idp", grp:"1. Total stock of IDPs", label:"IDPs in locations of return",
  cond:"… current location = the location fled from (IDPLoc)", items:["idploc"]},
 {key:"idpother", fw:"idp", grp:"1. Total stock of IDPs", label:"IDPs in other settlement locations",
  cond:"… current location is neither IDPLoc nor IDPPost", items:["idploc","idppost"]},
 {key:"idpcit", fw:"idp", grp:"1. Total stock of IDPs", label:"IDP condition: usually resident (or a citizen) where the causing event occurred",
  cond:"LocLiv = Yes or CitLoc = Yes; skip these two items if citizenship or residence at the time of displacement is captured elsewhere in the survey", items:["locliv"]},
 {key:"retmig", fw:"idp", grp:"1. Total stock of IDPs", label:"IDP exclusion: established residence abroad (12 months or more)",
  cond:"FleeCross = Yes, 12Mnths = 12 months or more, Apply = No — a returning migrant, not an IDP (IRIS para. 15–17)", items:["mnths12"]},
 {key:"idpchild", fw:"idp", grp:"IDP-related populations", label:"Children of at least one IDP parent, born after displacement", na:"roster",
  cond:"From the household roster's parent-identification variables; only parents alive and in the same household can be linked", items:[]},
 {key:"idpfamily", fw:"idp", grp:"IDP-related populations", label:"Other non-displaced family members of IDPs", na:"roster",
  cond:"From the household roster's relationship variables (outside the core IRIS framework)", items:[]},
 {key:"overcome", fw:"idp", grp:"2. Overcome key displacement-related vulnerabilities", label:"Locally integrated / returned and reintegrated / settled elsewhere and integrated", na:"composite",
  cond:"Requires EGRISS's composite measure of displacement-related vulnerabilities, not these questions (paper, paras 26–28)", items:[]},
 // ---- shared ----
 {key:"frcoth", fw:"shared", grp:"", label:"Other or locally-defined reasons for fleeing",
  cond:"FrcOth coded to a locally valid reason; also screens out false positives", items:["frcoth"]},
];
const SELECTABLE=SUBCATS.filter(c=>!c.core&&!c.na);
const NA_LABEL={roster:"from the roster",extra:"not yet askable",composite:"composite measure only"};
const NA_LONG={roster:"from the household roster",extra:"needs additional questions still to be developed",composite:"needs the composite measure of displacement-related vulnerabilities"};
let SUB={}; SUBCATS.forEach(c=>SUB[c.key]=true);
let FW={idp:true, refugee:true};

function subActive(c){
 if(c.na) return false;
 if(c.fw==="idp"&&!FW.idp) return false;
 if(c.fw==="refugee"&&!FW.refugee) return false;
 if(c.core) return true;
 return !!SUB[c.key];
}
function itemActive(key){
 return SUBCATS.some(c=>subActive(c)&&c.items.includes(key));
}
function activeItemNames(){
 return Object.keys(OPT_ITEMS).filter(itemActive).map(k=>OPT_ITEMS[k].name);
}
function setAllSubs(on){ SELECTABLE.forEach(c=>SUB[c.key]=on); }
// Presets: one click sets both the frameworks and the sub-categories.
function applyPreset(p){
 if(p==="core"){ FW.idp=true; FW.refugee=true; setAllSubs(false); }
 else if(p==="refugee"){ FW.idp=false; FW.refugee=true; setAllSubs(true); }
 else if(p==="idp"){ FW.idp=true; FW.refugee=false; setAllSubs(true); }
 else { FW.idp=true; FW.refugee=true; setAllSubs(true); }
 buildModPicker(); renderReg(sel.value);
}
function currentPreset(){
 const all=SELECTABLE.every(c=>SUB[c.key]), none=SELECTABLE.every(c=>!SUB[c.key]);
 if(FW.idp&&FW.refugee&&none) return "core";
 if(FW.idp&&FW.refugee&&all) return "both";
 if(FW.refugee&&!FW.idp&&all) return "refugee";
 if(FW.idp&&!FW.refugee&&all) return "idp";
 return null;
}
// What the core items alone identify: the framework categories marked core.
function coreIdentifies(){ return SUBCATS.filter(c=>c.core).map(c=>c.label); }

function buildModPicker(){
 const cur=currentPreset();
 document.querySelectorAll('.preset').forEach(b=>b.classList.toggle('on',b.dataset.p===cur));
 if(cur===null){ const mi=document.getElementById('moditems'), sb=document.getElementById('subsBtn'); if(mi&&mi.hidden){ mi.hidden=false; if(sb){ sb.classList.add('on'); sb.textContent="Hide categories"; } } }
 const names=activeItemNames();
 document.getElementById('modsummary').innerHTML=
  `<b>${5+names.length} items</b>: core${names.length?" + "+names.join(", "):" only"}`;
 const line=c=>{
  const adds=c.items.length?`<span class="modadds">+${c.items.map(k=>OPT_ITEMS[k].name).join(" +")}</span>`:"";
  if(c.core) return `<div class="moditem modcore" title="${esc(c.cond)}"><span class="modtag">core</span><span class="modlabel">${c.label}</span></div>`;
  if(c.na) return `<div class="moditem modna" title="${esc(c.cond)}"><span class="modtag na">${NA_LABEL[c.na]}</span><span class="modlabel">${c.label}</span></div>`;
  return `<label class="moditem" title="${esc(c.cond)}"><input type="checkbox" class="moditem-cb" data-k="${c.key}" ${SUB[c.key]?"checked":""}>`+
   `<span class="modlabel">${c.label}</span>${adds}</label>`;};
 const card=(key,title,on,cats,coreText)=>{
  const toggle=key?`<label class="modtoggle"><input type="checkbox" class="fw-cb" data-fw="${key}" ${on?"checked":""}> ${title}</label>`
                   :`<span class="modtoggle">${title}</span>`;
  let body="";
  if(key&&!on) body=`<p class="modoff">Not being identified. Tick to include these categories.</p>`;
  else{
   body=coreText||"";
   let lastGrp=null;
   (cats||[]).forEach(c=>{ if(c.grp&&c.grp!==lastGrp){ body+=`<div class="modgrp">${c.grp}</div>`; lastGrp=c.grp; } body+=line(c); });
  }
  return `<div class="modcard${key&&!on?" off":""}">${toggle}${body}</div>`;};
 const shared=SUBCATS.filter(c=>c.fw==="shared");
 let h=`<div class="modgrid">`+
  card(null,"Core &mdash; always asked",true,shared,
   `<p class="modcoretext">${CORE_ITEMS}.<br>Enough on their own for: any history of forced displacement; whether it began inside or outside the survey country; ${coreIdentifies().join("; ").toLowerCase()}.</p>`)+
  card("refugee","IRRS &mdash; refugees and related populations",FW.refugee,SUBCATS.filter(c=>c.fw==="refugee"))+
  card("idp","IRIS &mdash; IDPs and related populations",FW.idp,SUBCATS.filter(c=>c.fw==="idp"))+
  `</div><p class="modhint">The categories are the statistical frameworks&rsquo; own (IRRS a&ndash;c, IRIS 1&ndash;2), as in the methodological paper. <b>core</b> = identified by the core items alone; a ticked category adds the item it needs (+Item); greyed categories cannot be identified from these questions &mdash; they come from the household roster, from questions still to be developed, or from the composite measure. Hover a line for the condition. The questionnaire in step 4 and the files in step 6 follow this.</p>`;
 document.getElementById('moditems').innerHTML=h;
 document.querySelectorAll('.moditem-cb').forEach(cb=>cb.addEventListener('change',()=>{
  SUB[cb.dataset.k]=cb.checked; buildModPicker(); renderReg(sel.value);}));
 document.querySelectorAll('.fw-cb').forEach(cb=>cb.addEventListener('change',()=>{
  FW[cb.dataset.fw]=cb.checked; buildModPicker(); renderReg(sel.value);}));
}
document.querySelectorAll('.preset').forEach(b=>b.addEventListener('click',()=>applyPreset(b.dataset.p)));

// ---- the module, generated from module_i18n.py's M[LANG] --------------------
// Every stem, skip condition, option and note below comes from M, so the Apply
// card and the full questionnaire follow the Language buttons exactly as the
// forced-to-flee form does. Item codes stay as they are in every language.
const MT=()=>M[LANG]||M.en;
const RTL=()=>((LANGS[LANG]||["","ltr"])[1])==="rtl";
const ITEM_TITLES={FrcFl:"Forced to flee",FrcOth:"Other reasons for fleeing",FleeLoc:"Country of the home fled",IDPLoc:"Place lived before fleeing",
 LocLiv:"Always lived there",CitLoc:"Citizen when fled",FleeCross:"Moved to another country",IDPPost:"First place moved to","12Mnths":"Time abroad",
 Apply:"Applied for international protection",IntApply:"Intended to apply",Outcome:"Outcome of the application",Legal:"Main document held"};
const modqName=name=>`<div class="modq-name">${name}${ITEM_TITLES[name]?` <span class="modq-title">&middot; ${ITEM_TITLES[name]}</span>`:""}</div>`;
function modq(name,skip,stem,body){
 return `<div class="modq" data-item="${name}">${modqName(name)}`+
  (skip?`<div class="modq-skip">${skip}</div>`:"")+
  `<div class="modq-stem">${stem}</div>${body||""}</div>`;}
function optRows(opts,arrows){
 return `<div class="modq-opts">`+opts.map((o,i)=>
  `<div class="modq-opt"><span class="box"></span>${i+1}. ${o}`+
  (arrows&&arrows[i]?`<span class="modq-arrow">${arrows[i]}</span>`:"")+`</div>`).join("")+`</div>`;}
function yesno(t,arrows){ return optRows([t.ui.yes,t.ui.no],arrows); }

// ctx: what the databases know about the selected country, used to fill the
// slots the instrument lets vary - always in blue, like the forced-to-flee
// examples, so a reader sees at a glance what was customised.
//   c        country name (fills {country} in the stems)
//   cust     origins hosted (UNHCR) / destinations abroad (UNHCR) / subnational
//            areas with most events (UCDP, IDMC) / DTM reasons outside the codes
//   v        protection record: document names for Legal, UNHCR-issued types
// Which framework version is being built: "idp" (IRIS only), "ref" (IRRS
// only) or "both". The paper's Classification Table drives what each version
// keeps: in the IDP-only version FleeCross/12Mnths/Apply survive only as the
// IRIS exclusion conditions (established residence abroad, sought protection
// abroad) and Outcome/IntApply/Legal are dropped; in the refugee-only version
// a purely internal displacement ends the module.
function fwMode(){ return FW.idp&&!FW.refugee?"idp":FW.refugee&&!FW.idp?"ref":"both"; }
// Apply is reached either by having fled a home in another country, or by
// having crossed a border after fleeing one here (FDS routing). The IDP-only
// version keeps the paper's narrower condition, where Apply is an exclusion.
const applySkip=(t,u)=>fwMode()==="idp"?t.apply.skip:u.skip_apply;

function chainCtx(iso){
 const q=Q[iso]||{}, v=effReg(iso)||null;
 return {c:q.name||(v&&v.c)||iso, cust:effCust(iso), v};
}
// A blue customisation; with a slot name it becomes clickable-to-edit and
// turns purple once edited (see the hand-edits block near the top).
const EG=(s,slot)=>`<span class="eg${slot&&isEdited(slot)?" edited":""}"${slot?` data-slot="${slot}"`:""}>${esc(s)}</span>`;
const EGL=(list,slot)=>`<span class="egl${slot&&isEdited(slot)?" edited":""}"${slot?` data-slot="${slot}"`:""}>${list.map(x=>EG(x)).join(", ")}</span>`;
const fillC=(str,ctx)=>str.split("{country}").join(EG(ctx.c));
const custLine=(tpl,list,slot)=>`<div class="modq-custom">${tpl.replace("{list}",EGL(list,slot))}</div>`;

// On-screen only (class screenonly, stripped from every download): which of
// the back-coding reasons this country treats as a valid cause of forced
// displacement. It writes frcoth_valid in the derivation sheet and the
// XLSForm, and is listed in the customisation table.
function frcothPicker(){
 const list=MT().frcoth.list||[], on=frcothValid(sel.value);
 return `<div class="validpick screenonly"><b>Which of these count as a valid cause of forced displacement in `+
  `${esc((Q[sel.value]||{}).name||sel.value)}?</b> <span class="vp-note">A country decision \u2014 it sets `+
  `<code>frcoth_valid</code> in the derivation sheet and the form, and is recorded in every download.</span>`+
  `<div class="vp-grid">`+list.map(([txt],i)=>
   `<label class="vp"><input type="checkbox" class="vp-cb" data-i="${i}" ${on.includes(i)?"checked":""}>`+
   `<span>${txt}</span></label>`).join("")+`</div></div>`;
}
function itemHTML(key,ctx){
 const t=MT(), u=t.ui, goto=x=>u.goto.replace("{x}",x), cu=ctx.cust||{};
 switch(key){
  case "frcoth": return modq("FrcOth",t.frcoth.skip,t.frcoth.stem,
   `<div class="modq-note">${t.frcoth.note}</div><ul class="modq-list">`+
   t.frcoth.list.map(([txt,soft])=>`<li>${txt}${soft?` <span class="modq-softcheck">${soft}</span>`:""}</li>`).join("")+
   `</ul>`+frcothPicker()+(cu.dtm&&cu.dtm.length?`<div class="modq-custom">${u.cust_dtm.replace("{c}",EG(ctx.c))
     .replace("{list}",EGL(cu.dtm.map(([r,pc])=>pc!=null?`${r} (${pc}%)`:r),"dtm"))}</div>`:""));
  case "fleeloc": return modq("FleeLoc",t.fleeloc.skip,t.fleeloc.stem,
   optRows([t.fleeloc.opts[0]+" &mdash; "+EG(ctx.c), t.fleeloc.opts[1]],
           [null, fwMode()==="idp"?u.oos_idp:null])+
   (cu.origins&&cu.origins.length?custLine(u.cust_other,cu.origins,"origins"):""));
  case "idploc": return modq("IDPLoc",t.idploc.skip,t.idploc.stem,`<div class="modq-note">${u.open}</div>`+
   (cu.adm&&cu.adm.length?custLine(u.cust_adm,cu.adm,"adm"):""));
  // CitLoc is asked of everyone who fled, not only when LocLiv = No: citizenship
  // where the causing event happened is the IRIS condition itself, and asking it
  // of all is what the FDS does in the field.
  case "locliv": return modq("LocLiv",t.locliv.skip,fillC(t.locliv.stem,ctx),yesno(t))+
                        modq("CitLoc",t.locliv.skip,fillC(t.citloc.stem,ctx),yesno(t));
  // FleeCross is asked only of people who fled a home in the survey country.
  // Someone who fled abroad reaches Apply through FleeLoc instead: asking them
  // about a border crossing produced 2-51% wrong answers among refugee-card
  // holders in the three FDS pilots, and the fielded FDS form skips it.
  case "fleecross": {
   const m=fwMode();
   const skip=u.skip_fleeloc1;
   const note=m==="idp"?`<div class="modq-note">${u.note_fleecross_idp}</div>`
             :`<div class="modq-note">${u.note_fleecross_out}${m==="ref"?" "+fillC(u.note_fleecross_ref,ctx):""}</div>`;
   return modq("FleeCross",skip,t.fleecross.stem,
    (cu.dest&&cu.dest.length?custLine(u.cust_to,cu.dest,"dest"):"")+yesno(t)+note);
  }
  case "idppost": return modq("IDPPost",t.idppost.skip,t.idppost.stem,`<div class="modq-note">${t.idppost.note}</div>`+
   (cu.adm&&cu.adm.length?custLine(u.cust_adm,cu.adm,"adm"):""));
  case "mnths12": return modq("12Mnths",t.mnths12.skip,t.mnths12.stem,
   optRows(t.mnths12.opts,[null, fwMode()==="idp"?u.notidp_m12:null]));
  case "intapply": return modq("IntApply",t.intapply.skip,t.intapply.stem,yesno(t));
  case "outcome": return modq("Outcome",t.outcome.skip,t.outcome.stem,optRows(t.outcome.opts));
  case "legal": {
   const v=ctx.v||{};
   // Protected-status options carry the country's own document names: option 0
   // (asylum applicant document) = the pending document, option 1 (refugee) =
   // the recognised one. Category index 4 is "Protected status" in every language.
   const egFor=(i,j)=>{
    if(i!==4) return "";
    const n=j===0?v.da:j===1?v.dr:null, slot=j===0?"da":"dr";
    return n?` <span class="modq-custom-inline">${u.eg} ${EG(n,slot)}</span>`:"";};
   let cats=t.legal.cats.map(([head,opts],i)=>`<div class="modq-cathead">${head}</div>`+
     opts.map((o,j)=>`<div class="modq-catopt">${fillC(o,ctx)}${egFor(i,j)}</div>`).join("")).join("");
   if(v.svd&&v.svd.length) cats+=`<div class="modq-custom">${u.cust_docs.replace("{c}",EG(ctx.c))
     .replace("{list}",EG("UNHCR: "+v.svd.map(x=>x.toLowerCase()).join(", ")))}</div>`;
   return modq("Legal",t.legal.skip,fillC(t.legal.stem,ctx),`<div class="modq-note">${t.legal.note}</div><div class="modq-cats">${cats}</div>`);
  }
 }
 return "";
}

// Assembles the fixed-wording part of the chain (everything before Apply) in
// item order, honouring the sub-category picker.
function buildFrontChain(ctx){
 let h=chainFrcFlHTML();
 if(itemActive("frcoth")) h+=itemHTML("frcoth",ctx);
 h+=itemHTML("fleeloc",ctx);
 if(itemActive("idploc")) h+=itemHTML("idploc",ctx);
 if(itemActive("locliv")) h+=itemHTML("locliv",ctx);
 h+=itemHTML("fleecross",ctx);
 if(itemActive("idppost")) h+=itemHTML("idppost",ctx);
 if(itemActive("mnths12")) h+=itemHTML("mnths12",ctx);
 return h;
}

// The localised names for Apply, in the language being shown: when the page
// language is the country's own survey language, the local-language name
// (as printed on the source pages) is the one read out and the formal name
// becomes the gloss; otherwise the formal name leads.
function applyNames(iso,v){
 const local=LANG!=="en"&&Q[iso]&&Q[iso].lang===LANG;
 const office=local&&v.orgL?v.orgL:v.org, officeGloss=local&&v.orgL?v.org:v.orgL;
 const da=v.da||v.dr, daL=v.da?v.daL:v.drL, daC=v.da?v.daC:v.drC;
 const doc=local&&daL?daL:da, docGloss=local&&daL?da:daL;
 return {office,officeGloss,doc,docGloss,docColloq:daC};
}
const probeHTML=(tpl,name,slot)=>tpl.replace("{name}",EG(name,slot));
const docSlot=v=>v&&v.da?"da":"dr";

// The Apply item on its own card, styled exactly like the forced-to-flee form:
// the stem never changes, only the blue example does. Two versions of that
// example are drafted side by side - A names the OFFICE (the wording in the
// paper), B names the DOCUMENT (proposed after the paper was written), with
// the document's specimen shown as a show card under B when one is sourced.
// The card follows the IRRS/refugee framework checkbox: Apply serves refugee
// identification, so it is hidden when only IDPs are being identified.
function renderApply(iso,v){
 const sec=document.getElementById('applysec'), f=document.getElementById('applyform');
 const t=MT(), u=t.ui, goto=x=>u.goto.replace("{x}",x);
 const hostName=(Q[iso]&&Q[iso].name)||(v&&v.c)||iso;
 sec.hidden=!FW.refugee;
 f.setAttribute('dir',RTL()?"rtl":"ltr");
 const head=`<div class="fhead"><span class="fitem">Apply</span>`+
  `<span class="fask">{${fwMode()==="idp"?t.apply.skip:u.skip_apply}}</span>`+
  `<span class="fcountry">${esc(hostName)}</span></div>`+
  `<p class="stem"><b>${t.apply.stem}</b></p>`;
 const opts=`<ol class="opts aopts">`+
  `<li><span class="box"></span><span class="num">1</span><span class="otext">${u.yes} `+
  `<span class="more">${goto("Outcome")}</span></span></li>`+
  `<li><span class="box"></span><span class="num">2</span><span class="otext">${u.no} `+
  `<span class="more">${itemActive("intapply")?goto("IntApply"):""}</span></span></li></ol>`;
 if(!v){ f.innerHTML=head+`<p class="pmiss">${u.no_example}</p>`+opts; return; }
 if(v.reg==="NONE"){ f.innerHTML=head+`<p class="pmiss">${u.none_proc}</p>`+opts; return; }
 const n=applyNames(iso,v);
 const localMode=LANG!=="en"&&Q[iso]&&Q[iso].lang===LANG;
 const gloss=(local,colloq)=>{
  const bits=[local?(localMode?u.formal:u.in_local).replace("{n}",esc(local)):null,
              colloq?u.called.replace("{n}",esc(colloq)):null].filter(Boolean);
  return bits.length?`<div class="gloss">${bits.join(" &middot; ")}</div>`:"";};
 let a=`<div class="aver"><span class="avertag">${u.verA}</span>`;
 if(n.office){
  a+=`<p class="aprobe">${probeHTML(t.apply.probe_office,n.office,"org")}</p>`+gloss(n.officeGloss,null);
  if(v.alt&&v.alt.length) a+=`<div class="why">${u.also_seen.replace("{n}",esc(v.alt.join("; ")))}</div>`;
  if(v.ow) a+=`<div class="why">${esc(v.ow)}</div>`;
 }else a+=`<p class="pmiss">${u.noA}${v.how?` ${esc(v.how)}`:``}</p>`;
 a+=`</div>`;
 let b=`<div class="aver"><span class="avertag">${u.verB}</span>`;
 if(n.doc){
  b+=`<p class="aprobe">${probeHTML(t.apply.probe_doc,n.doc,docSlot(v))}</p>`+gloss(n.docGloss,n.docColloq);
  if(v.da&&v.dr&&v.dr!==v.da) b+=`<div class="why">${u.on_recog.replace("{n}",esc(v.dr)+(v.drC?` (&ldquo;${esc(v.drC)}&rdquo;)`:""))}</div>`;
  if(v.dw) b+=`<div class="why">${esc(v.dw)}</div>`;
  b+=`<div class="specimens" id="regspecimens">${renderSpecimenHTML(iso,v)}</div>`;
 }else b+=`<p class="pmiss">${u.noB}${v.dw?` ${esc(v.dw)}`:``}</p>`;
 b+=`</div>`;
 const instr=`<div class="ainstr">${u.instr}${v.mis?` ${u.instr_misfire}`:``}</div>`;
 f.innerHTML=head+`<p class="lead">${u.loc_two}</p>`+a+b+opts+instr;
}

// The full questionnaire opens with FrcFl itself - the same customised form
// as the card at the top, copied in so the module is complete on its own and
// in the download. render() calls this after every re-render of the card, so
// version, length, language, level and population changes flow through.
function syncChainFrcFl(){
 const el=document.getElementById('chainFrcFl'), src=document.getElementById('form');
 if(!el||!src) return;
 el.innerHTML=modqName("FrcFl")+`<div class="modq-form" dir="${src.getAttribute('dir')||'ltr'}">${src.innerHTML}</div>`;
}
function chainFrcFlHTML(){
 const src=document.getElementById('form');
 return `<div class="modq modq-frcfl" id="chainFrcFl" data-item="FrcFl">`+modqName("FrcFl")+
  `<div class="modq-form" dir="${src.getAttribute('dir')||'ltr'}">${src.innerHTML}</div></div>`;
}

// Everything that must follow a re-render of the module: the walkthrough
// marks, the download-bar state (reset button, issue link), the URL.
function renderReg(iso){ renderRegInner(iso); afterRender(); }
function afterRender(){
 try{ walkRender(); }catch(e){}
 try{ chkRender(); }catch(e){}
 const rb=document.getElementById('resetBtn'); if(rb){ const n=edCount(sel.value); rb.hidden=!n; if(!rb.dataset.arm) rb.textContent=`Reset your ${n} edit${n===1?"":"s"}`; }
 const il=document.getElementById('issueLink'); if(il) il.href=issueURL();
 ["step0","maplink"].forEach(id=>{ const a=document.getElementById(id); if(a) a.href=`map.html?c=${sel.value}`; });
 document.querySelectorAll('.vp-cb').forEach(cb=>cb.addEventListener('change',()=>{
  const on=[...document.querySelectorAll('.vp-cb')].filter(x=>x.checked).map(x=>+x.dataset.i);
  edSet(sel.value,"frcothvalid",on.join(","));
  const rb=document.getElementById('resetBtn'); if(rb){ delete rb.dataset.arm; }
  renderReg(sel.value); }));
 const sc=document.getElementById('stickyC'); if(sc) sc.textContent=`${(Q[sel.value]||{}).name||sel.value} \u00b7 ${5+activeItemNames().length} items`;
 syncHash();
}
function renderRegInner(iso){
 const v=effReg(iso), t=MT(), u=t.ui, goto=x=>u.goto.replace("{x}",x);
 const badges=document.getElementById('regbadges'), form=document.getElementById('regform'),
       warn=document.getElementById('regwarn'), cav=document.getElementById('regcav'),
       miss=document.getElementById('regmiss');
 renderApply(iso,v);
 form.setAttribute('dir',RTL()?"rtl":"ltr");
 miss.style.display="none";form.style.display="";
 const ctx=chainCtx(iso), mode=fwMode();
 const legalHTML=itemActive("legal")?itemHTML("legal",ctx):"";
 // IDP-only version: Outcome serves no IDP classification (the Classification
 // Table uses only Apply = No as the exclusion), so it is dropped with
 // IntApply and Legal, and Apply becomes a screening item.
 const tail=()=>(itemActive("intapply")?itemHTML("intapply",ctx):"")+
   (mode==="idp"?"":itemHTML("outcome",ctx))+legalHTML;
 const applyOpts=mode==="idp"
  ? yesno(t,[u.notidp_apply,null])+`<div class="modq-note">${u.note_apply_idp}</div>`
  : yesno(t,[goto("Outcome"),itemActive("intapply")?goto("IntApply"):null]);
 if(!v){
  badges.innerHTML="";
  form.innerHTML=buildFrontChain(ctx)+modq("Apply",applySkip(t,u),t.apply.stem,
   `<div class="pmiss">${u.no_example}</div>`+applyOpts)+tail();
  warn.style.display="none";cav.style.display="none";
  return;
 }
 badges.innerHTML=
  `<span class="badge b-reg">Claims registered by ${esc(v.reg==="BOTH"?"Government and UNHCR":(REGLABEL[v.reg]||v.reg))}</span>`+
  `<span class="badge b-cf-${v.cf}" title="How well the sources support the office and document names">Source confidence: ${esc(String(v.cf).toLowerCase())}</span>`;
 if(v.reg==="NONE"){
  form.innerHTML=buildFrontChain(ctx)+modq("Apply",applySkip(t,u),t.apply.stem,
   `<div class="pmiss">${u.none_proc}</div>`)+legalHTML;
  warn.style.display="none";cav.style.display="none";
  return;
 }
 // In the full questionnaire the Apply item carries the SAME two customised
 // examples as the card above - the selected customisation travels with the
 // questionnaire - set in the example style (italic, name in blue).
 const n=applyNames(iso,v);
 let ex="";
 if(n.office) ex+=`<div class="modq-example"><span class="modq-vtag">A</span> ${probeHTML(t.apply.probe_office,n.office,"org")}</div>`;
 if(n.doc) ex+=`<div class="modq-example"><span class="modq-vtag">B</span> ${probeHTML(t.apply.probe_doc,n.doc,docSlot(v))}</div>`+
   `<div class="specimens specimens-chain">${renderSpecimenHTML(iso,v)}</div>`;
 if(!ex) ex=`<div class="pmiss">${u.no_example_short}</div>`+
   (v.ow?`<div class="why">${esc(v.ow)}</div>`:"")+(v.dw?`<div class="why">${esc(v.dw)}</div>`:"");
 let h=buildFrontChain(ctx)+modq("Apply",applySkip(t,u),t.apply.stem,ex+applyOpts)+tail();
 form.innerHTML=h;
 if(v.mis){warn.style.display="";
  warn.innerHTML=`<b>The office wording does not work well here</b> &mdash; claims are actually lodged like this: ${esc(v.how)}. Use Version B (the document).`;
 }else{warn.style.display="none";}
 const cols=(v.cols&&v.cols.length)?v.cols.join(", "):null;
 if(v.cav){cav.style.display="";cav.innerHTML=`<b>Note.</b> ${esc(v.cav)}`;
  if(cols)cav.innerHTML+=`<br><b>Colour names in use:</b> ${esc(cols)}`;
 }else if(cols){cav.style.display="";cav.innerHTML=`<b>Colour names in use:</b> ${esc(cols)}`;
 }else{cav.style.display="none";}
}

// "What it looks like" - a picture of the actual document, for interviewer
// training / respondent show cards. Pilot coverage only (see
// document_specimens.py). Sourcing runs on two tracks: UNHCR-issued documents
// are being supplied directly by EGRISS's own UNHCR contacts rather than
// hunted for on the open web, so a country whose document comes from UNHCR
// gets a different, non-urgent note than a government-issued document that's
// a genuine open research gap - see the `reg` check below.
function renderSpecimenHTML(iso,v){
 const s=SPEC[iso];
 const hasContent = s&&((s.images&&s.images.length)||s.note||(s.links&&s.links.length));
 if(!hasContent&&!v.v2) return ""; // no document nameable at all - the probe
  // above already says so; a bare "What it looks like" header with nothing
  // under it would just repeat that with extra steps.
 let h='<div class="spec-head">What it looks like</div>';
 if(s&&s.images&&s.images.length){
  h+='<div class="spec-grid">'+s.images.map(im=>
   `<figure class="spec-item"><img src="${esc(im.img)}" alt="${esc(im.label)}" loading="lazy" `+
   `onerror="this.closest('.spec-item').classList.add('broken')">`+
   `<figcaption>${esc(im.label)}<br><a href="${esc(im.source)}" target="_blank" `+
   `rel="noopener">${esc(im.source_name)}</a> &middot; ${esc(im.license)}</figcaption></figure>`
  ).join('')+'</div>';
 }
 if(s&&s.note){h+=`<p class="spec-note">${esc(s.note)}</p>`;}
 if(s&&s.links&&s.links.length){
  h+='<p class="spec-links">'+s.links.map(l=>
   `<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)}</a>`).join('')+'</p>';
 }
 if(!hasContent){
  h+= v.reg==="UNHCR"
   ? '<p class="spec-note">This document is issued directly by UNHCR &mdash; '+
     'a specimen is being sourced through EGRISS’s own UNHCR contacts rather '+
     'than public search.</p>'
   : '<p class="pmiss">No public specimen image found for this document yet.</p>';
 }
 return h;
}

function pickCountry(){
 const v=Q[sel.value]; LANG=v.lang||"en"; ADM=-1; POP=null;
 buildLangs(); buildLevels(v); buildPops(v); render();
 renderReg(sel.value);}
sel.addEventListener('change',pickCountry);
lvl.addEventListener('change',()=>{ADM=+lvl.value;render();});
document.querySelectorAll('.len').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.len').forEach(x=>x.classList.remove('on'));
 b.classList.add('on');LEN=b.dataset.l;render();}));
document.querySelectorAll('.adm').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.adm').forEach(x=>x.classList.remove('on'));
 b.classList.add('on');ADMIN=b.dataset.a;render();renderReg(sel.value);}));
// Same collapsed-panel pattern as map.html's "How to read this" etc.
function panelToggle(btnId,panelId,openTxt,shutTxt){
 document.getElementById(btnId).addEventListener('click',e=>{
  e.stopPropagation(); const h=document.getElementById(panelId);
  h.hidden=!h.hidden; e.target.classList.toggle('on',!h.hidden);
  e.target.textContent=h.hidden?openTxt:shutTxt;
  if(!h.hidden)h.scrollIntoView({behavior:"smooth",block:"nearest"});});}
panelToggle('notesbtn','notespanel',"Show the caveats","Hide the caveats");
panelToggle('provbtn','provwrap',"Where these examples come from","Hide the sources");
panelToggle('advBtn','advanced',"More options: subnational example set, other populations\u2019 examples","Fewer options");
panelToggle('subsBtn','moditems',"Choose categories","Hide categories");
// The sticky download bar: visible while "Your files" is off screen.
(function(){
 const st=document.getElementById('sticky'), files=document.getElementById('files');
 if(!st||!files||!('IntersectionObserver' in window)) return;
 st.querySelectorAll('button[data-for]').forEach(b=>b.addEventListener('click',()=>document.getElementById(b.dataset.for).click()));
 const io=new IntersectionObserver(es=>{ const vis=es.some(e=>e.isIntersecting); st.hidden=vis; document.body.classList.toggle('has-sticky',!vis); },{rootMargin:"0px 0px -40% 0px"});
 io.observe(files);
})();
/* ---------------------------------------------------------------------
   Downloadable questionnaire + interviewer instructions — DOCX / PDF,
   built in the browser from the two forms currently on screen (the
   forced-to-flee question as selected by Level/Length/Language/
   Population, and the international-protection module below it). No
   server involved. This is a real public page, not a Claude Artifact,
   so the file is handed to the browser via a Blob + object URL and a
   temporary <a download> click, rather than the Artifact `downloads`
   capability (which only exists inside the Artifact viewer sandbox).
   Specimen images are cited as a name + source link, never embedded —
   they're hotlinked from outside sites with no CORS/base64 access from
   here, and html-docx-js only supports inlined base64 images anyway.
   --------------------------------------------------------------------- */

function stripImgs(html){
 const tmp=document.createElement('div'); tmp.innerHTML=html;
 tmp.querySelectorAll('.egadd,.screenonly').forEach(el=>el.remove());
 tmp.querySelectorAll('img').forEach(im=>{ if(!/^data:/.test(im.getAttribute('src')||'')) im.remove(); });
 tmp.querySelectorAll('.spec-item').forEach(el=>el.classList.remove('broken'));
 return tmp.innerHTML;
}

const EXPORT_CSS=`
body{font-family:Calibri,Arial,sans-serif;color:#1d2940;font-size:11pt;line-height:1.5;margin:36pt}
h1{font-family:Georgia,serif;color:#14234c;font-size:20pt;margin:0 0 4pt}
h2{font-family:Georgia,serif;color:#14234c;font-size:13pt;margin:20pt 0 8pt;border-bottom:1pt solid #dde1e8;padding-bottom:3pt}
p.lede{color:#5a6884;font-size:10pt;margin:0 0 14pt}
.fhead{border-bottom:1.5pt solid #1d2940;padding-bottom:6pt;margin-bottom:12pt;font-size:9.5pt;color:#5a6884}
.fitem{font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#1d2940}
.fask{font-style:italic}
.fcountry{float:right;text-transform:uppercase;letter-spacing:.05em;font-weight:700}
.stem{margin:0 0 8pt}
.lead{margin:12pt 0 3pt;font-weight:700}
.instr{font-size:8.5pt;color:#5a6884;border:1pt solid #dde1e8;padding:3pt 7pt;display:inline-block;margin-bottom:10pt}
ol.opts{list-style:none;margin:0;padding:0}
ol.opts li{padding:4pt 0;border-bottom:0.5pt dotted #dde1e8}
.box{display:inline-block;width:9pt;height:9pt;border:1pt solid #1d2940;margin-right:8pt}
.ynbox{white-space:nowrap;margin-right:6pt}
.ynbox i{font-style:normal;font-size:8pt;color:#8b93a8;margin-right:6pt}
.num{color:#8b93a8;margin-right:6pt}
.eg{color:#3b71b9}
.eg .lab{font-style:italic;color:#5a6884}
.eg.edited,.egl.edited .eg,.edited{color:#7a3fb5}
.gen{color:#8b93a8;font-style:italic}
.more,.excl{font-size:8.5pt;color:#8b93a8}
.warn{background:#fbf1dc;border:1pt solid #e0a93b;padding:8pt 10pt;margin-top:10pt;font-size:9.5pt}
.badges{margin:0 0 10pt}
.badge{font-size:8pt;text-transform:uppercase;letter-spacing:.04em;padding:2pt 6pt;border:1pt solid #dde1e8;margin-right:6pt}
.modq{border-top:0.5pt dotted #dde1e8;padding-top:10pt;margin-top:10pt}
.modq:first-child{border-top:0;padding-top:0;margin-top:0}
.modq-name{font-size:8.5pt;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#3b71b9}
.modq-skip{font-size:9pt;font-style:italic;color:#8b93a8;margin-bottom:5pt}
.modq-stem{font-family:Georgia,serif;font-size:11.5pt;margin:4pt 0}
.modq-example{font-family:Georgia,serif;font-style:italic;font-size:10.5pt;color:#1d2940;margin:2pt 0 6pt}
.modq-example .eg{font-style:normal;font-weight:700;color:#3b71b9}
.modq-custom{font-family:Georgia,serif;font-style:italic;font-size:10pt;color:#5a6884;margin:3pt 0 2pt}
.modq-custom-inline{font-family:Georgia,serif;font-style:italic;font-size:9.5pt;color:#5a6884}
.modq-custom .eg,.modq-custom-inline .eg,.modq-catopt .eg,.modq-opt .eg,.modq-stem .eg{color:#3b71b9;font-style:normal;font-weight:700}
.modq-vtag{font-family:Calibri,Arial,sans-serif;font-style:normal;font-size:8pt;font-weight:700;color:#3b71b9;border:0.5pt solid #b9c9e4;padding:0 3pt;margin-right:3pt}
.modq-opts{margin:7pt 0 0}
.modq-opt{padding:2pt 0;font-size:10pt}
.modq-opt .box{width:8pt;height:8pt}
.modq-arrow{float:right;font-size:8.5pt;color:#8b93a8}
.gloss{font-size:9pt;color:#5a6884;margin-top:3pt}
.why{font-size:8.5pt;color:#8b93a8;margin-top:3pt}
.pmiss{color:#8b93a8;font-style:italic}
.cav{background:#eef3fa;padding:8pt 10pt;margin-top:10pt;font-size:9.5pt}
.spec-head{font-size:8.5pt;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#5a6884;margin-top:10pt}
.spec-item{margin:4pt 0}
.spec-item img{max-width:360pt;max-height:260pt;border:0.5pt solid #dde1e8}
.modq-form{font-family:Georgia,serif;font-size:11pt}
.spec-item figcaption{font-size:9pt;color:#5a6884}
.spec-note{font-size:9.5pt;color:#5a6884}
.spec-links a{font-size:9pt;color:#3b71b9;margin-right:10pt}
.gen-note{color:#8b93a8;font-size:8.5pt}
.modq-note{font-size:9pt;color:#5a6884;margin:5pt 0 0}
.modq-list{margin:5pt 0 0;padding-left:14pt;font-size:9pt;color:#5a6884}
.modq-list li{margin-bottom:2pt}
.modq-softcheck{color:#8b93a8;font-style:italic}
.modq-cats{margin-top:6pt}
.modq-cathead{font-size:8pt;text-transform:uppercase;letter-spacing:.04em;color:#8b93a8;font-weight:700;margin:6pt 0 1pt}
.modq-catopt{font-size:10pt;margin:1pt 0 1pt 3pt}
.aver{margin:12pt 0 0;padding-top:8pt;border-top:0.5pt dotted #dde1e8}
.avertag{display:block;font-size:8.5pt;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#8b93a8;margin-bottom:3pt}
.avertag b{color:#3b71b9}
.aprobe{font-family:Georgia,serif;font-style:italic;margin:0 0 3pt}
.aprobe .eg{font-style:normal;font-weight:700}
.ainstr{font-size:9.5pt;color:#5a6884;border-top:0.5pt dotted #dde1e8;margin-top:12pt;padding-top:8pt}
.aopts{margin-top:10pt}
table.cust{border-collapse:collapse;width:100%;font-size:9.5pt;margin:0 0 6pt}
table.cust th{text-align:left;vertical-align:top;width:120pt;padding:4pt 8pt 4pt 0;color:#5a6884;font-weight:700;border-bottom:0.5pt solid #dde1e8}
table.cust td{vertical-align:top;padding:4pt 0;border-bottom:0.5pt solid #dde1e8}
table.cust ul{margin:2pt 0 0;padding-left:14pt}
table.cust small{color:#8b93a8}
`;

function buildExportHTML(iso){
 const v=Q[iso];
 const langName=(LANGS[LANG]&&LANGS[LANG][0])||LANG;
 const lenName=LEN==="showcard"?"Showcard":"Read aloud";
 const formHTML=stripImgs(document.getElementById('form').innerHTML);
 const warnHTML=document.getElementById('warn').innerHTML;
 const regBadgesHTML=document.getElementById('regbadges').innerHTML;
 const regFormHTML=stripImgs(document.getElementById('regform').innerHTML);
 const regWarnEl=document.getElementById('regwarn');
 const regWarnHTML=(regWarnEl&&regWarnEl.style.display!=="none")?regWarnEl.innerHTML:"";
 const regCavEl=document.getElementById('regcav');
 const regCavHTML=(regCavEl&&regCavEl.style.display!=="none")?regCavEl.innerHTML:"";
 const applySec=document.getElementById('applysec');
 const applyHTML=applySec.hidden?"":stripImgs(document.getElementById('applyform').innerHTML);

 let h=`<!DOCTYPE html><html><head><meta charset="utf-8">`+
  `<title>${esc(v.name)} — questionnaire</title><style>${EXPORT_CSS}</style></head><body>`;
 h+=`<h1>${esc(v.name)}</h1>`+
  `<p class="lede">Identification questions, ${esc(langName)}, ${esc(lenName)} length. `+
  `The questions and response options never change &mdash; only the examples and the office `+
  `and document names, customised for this country. The forced-to-flee question comes first, `+
  `then the Apply item with its two localisation versions, then the full module.</p>`;
 h+=customisationHTML(iso);
 h+=`<h2>Forced to flee</h2><div class="fform">${formHTML}</div>`;
 if(warnHTML) h+=`<div class="warn">${warnHTML}</div>`;
 if(applyHTML){
  h+=`<h2>Apply &mdash; international protection, localised</h2><div class="fform">${applyHTML}</div>`;
  if(regWarnHTML) h+=`<div class="warn">${regWarnHTML}</div>`;
  if(regCavHTML) h+=`<div class="cav">${regCavHTML}</div>`;
 }
 h+=`<h2>International protection &amp; displacement module</h2><div class="badges">${regBadgesHTML}</div>`+
  `<div class="regform">${regFormHTML}</div>`;
 if(!applyHTML){
  if(regWarnHTML) h+=`<div class="warn">${regWarnHTML}</div>`;
  if(regCavHTML) h+=`<div class="cav">${regCavHTML}</div>`;
 }
 h+=stampHTML();
 h+=`</body></html>`;
 return h;
}

// "How this questionnaire was customised" - every choice made on the page,
// in one place at the top of the download, so whoever receives the file can
// see what was localised, which version of each item they hold, and which
// populations the item set can identify. This is the instructions half of
// "questionnaire & instructions".
function customisationHTML(iso){
 const v=Q[iso], r=effReg(iso);
 const langName=(LANGS[LANG]&&LANGS[LANG][0])||LANG;
 const region=(ADM>=0&&v.adm1)?v.adm1[ADM]:null;
 const pop=(POP!=null)?(v.populations||[])[POP]:null;
 const fw=[FW.idp?"IDPs (IRIS)":null,FW.refugee?"refugees (IRRS)":null].filter(Boolean);
 const subs=SUBCATS.filter(subActive);
 const items=Object.keys(OPT_ITEMS).filter(itemActive);
 const row=(k,val)=>`<tr><th>${k}</th><td>${val}</td></tr>`;
 let h=`<h2>How this questionnaire was customised</h2><table class="cust">`;
 h+=row("Country",esc(v.name)+(region?` &middot; ${esc(region.name)} (subnational example set)`:``));
 if(pop) h+=row("Population previewed",esc(pop.name)+` &mdash; the forced-to-flee examples shown are `+
   `${pop.kind==="national"?"the host country's own":"this population's own, in place of the host country's"}`);
 h+=row("Forced to flee, version",`${esc(VERSION_DEFS[VER]?VERSION_DEFS[VER].label:"Long")} `+
   (VER===3?`&mdash; the full item, 8 response codes plus none`:`&mdash; official variant from the question-testing document, drafted in English only`));
 h+=row("Length",LEN==="showcard"?"Show card &mdash; all recorded examples":"Read aloud &mdash; up to three examples per option");
 h+=row("How the options are asked",ADMIN==="grid"?"Read out one by one &mdash; each option coded Yes or No, plus &lsquo;none of the above&rsquo;. Works with respondents who cannot read a show card, and by telephone."
   :"Choose all that apply &mdash; one question, several options may be ticked, &lsquo;none of the above&rsquo; exclusive.");
 h+=row("Language",esc(langName)+(LANG!=="en"?" (unreviewed draft translation)":""));
 h+=row("Frameworks",fw.length?fw.join(" and "):"none selected");
 h+=row("Core items, always asked",CORE_ITEMS+`. These alone identify: any history of forced displacement; whether it began inside or outside the survey country; ${coreIdentifies().join("; ").toLowerCase()}.`);
 if(FW.idp&&!FW.refugee) h+=row("IDP-only version (IRIS)","FleeCross, 12Mnths and Apply are kept only as IRIS's exclusion conditions (established residence abroad; sought protection abroad); Outcome, IntApply and Legal are dropped; a home fled in another country is out of scope.");
 if(FW.refugee&&!FW.idp) h+=row("Refugee-only version (IRRS)","The IDP location items are dropped; a respondent who fled within the survey country and never crossed a border is out of scope and the module can end at FleeCross.");
 const notId=SUBCATS.filter(c=>c.na&&((c.fw==="refugee"&&FW.refugee)||(c.fw==="idp"&&FW.idp)));
 h+=row("Framework categories identified",subs.length?`<ul>`+subs.map(c=>`<li>${c.label} <small>(${c.fw==="idp"?"IRIS":c.fw==="refugee"?"IRRS":""} ${esc(c.grp)}; ${esc(c.cond)}${c.items.length?`; adds ${c.items.map(k=>OPT_ITEMS[k].name).join(" + ")}`:"; core items"})</small></li>`).join("")+`</ul>`:"none &mdash; core questionnaire only (short version)");
 if(notId.length) h+=row("Not identifiable from these questions",`<ul>`+notId.map(c=>`<li>${c.label} <small>(${NA_LONG[c.na]}: ${esc(c.cond)})</small></li>`).join("")+`</ul>`);
 h+=row("Items added beyond the core",items.length?`<ul>`+items.map(k=>`<li><b>${OPT_ITEMS[k].name}</b> &mdash; ${OPT_ITEMS[k].label}. <small>${OPT_ITEMS[k].why}</small></li>`).join("")+`</ul>`:"none");
 const cu=effCust(iso);
 if(cu.origins) h+=row("FleeLoc &mdash; other-country examples",`${cu.origins.join(", ")} <small>(largest refugee populations hosted in ${esc(v.name)}, UNHCR)</small>`);
 if(cu.dest) h+=row("FleeCross &mdash; destination examples",`${cu.dest.join(", ")} <small>(where nationals of ${esc(v.name)} are registered as refugees or asylum seekers, UNHCR)</small>`);
 if(cu.adm) h+=row("IDPLoc / IDPPost &mdash; subnational examples",`${cu.adm.join(", ")} <small>(areas with the most recorded displacement events, UCDP and IDMC)</small>`);
 if(itemActive("frcoth")) h+=row("FrcOth &mdash; reasons that count as valid here",
   (frcothNames(iso).join("; ")||"none selected")+` <small>(sets <code>frcoth_valid</code>; the default is the set fielded in the FDS &mdash; confirm against ${esc(v.name)}'s own rules)</small>`);
 if(cu.dtm) h+=row("FrcOth &mdash; reasons from IOM DTM",cu.dtm.map(([x,pc])=>pc!=null?`${esc(x)} (${pc}%)`:esc(x)).join(", ")+` <small>(share of displaced people interviewed who gave a reason outside the FrcFl codes)</small>`);
 if(r&&(r.da||r.dr||(r.svd&&r.svd.length))) h+=row("Legal &mdash; document names",
   [r.da?`asylum applicant document: <b>${esc(r.da)}</b>`:null, r.dr?`refugee: <b>${esc(r.dr)}</b>`:null,
    (r.svd&&r.svd.length)?`UNHCR issues: ${r.svd.map(x=>x.toLowerCase()).join(", ")}`:null].filter(Boolean).join(" &middot; ")+
   `; passport and citizenship lines name ${esc(v.name)}`);
 if(r&&r.reg!=="NONE"&&FW.refugee){
  h+=row("Apply localisation",`Version A (office): ${r.org?"<b>"+esc(r.org)+"</b>":"cannot be worded here"} &middot; `+
    `Version B (document): ${(r.da||r.dr)?"<b>"+esc(r.da||r.dr)+"</b>":"cannot be worded here"}`+
    (r.mis?` &middot; the office wording does not work well in this country; Version B is preferred`:``)+
    ` &middot; source confidence ${esc(r.cf)}`);
 }else if(r&&r.reg==="NONE"){
  h+=row("Apply localisation","No registration or protection procedure exists in this country; the Apply sequence does not apply.");
 }
 const ed=editedRows(iso);
 h+=row("Your edits",ed.length?`<ul>`+ed.map(e=>`<li><b>${esc(e.label)}</b>: <span class="edited">${esc(e.value)}</span></li>`).join("")+`</ul>`+
   `<small>These replace the database values above wherever they appear; shown in purple in the questionnaire.</small>`
   :"none &mdash; every customisation is the database value");
 h+=row("Link to this set-up",`<small>${esc(shareURL())}</small>`);
 h+=`</table>`;
 return h;
}

// The generation stamp every download ends with, and the page footer: when
// the customisation was generated, how old the sources are, and where to
// send a correction.
function shareURL(){ return location.origin+location.pathname+location.search+stateToHash(); }
function issueURL(){
 const v=Q[sel.value]||{name:sel.value};
 const title=`Correction: ${v.name} (${sel.value})`;
 const body=`Country: ${v.name} (${sel.value})\nItem / example that is wrong:\n\nWhat it should say:\n\nSource (a page, a document, or "confirmed by the registrar on <date>"):\n\nSet-up link: ${shareURL()}\n`;
 return `https://github.com/mitrovif/idq-map/issues/new?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`;
}
function vintageText(){
 const m=META||{};
 const bits=[];
 if(m.events_to) bits.push(`recorded events (UCDP GED, IDMC, ACLED kinds) through ${m.events_to}`);
 if(m.unhcr_year) bits.push(`UNHCR population statistics for ${m.unhcr_year}`);
 bits.push("IOM DTM reported reasons, help.unhcr.org and RIMAP pages for offices and documents");
 if(m.survey) bits.push("UNHCR's Registration Baseline Survey (2024/25)");
 return bits.join("; ");
}
function stampHTML(){
 const m=META||{};
 return `<p><small class="gen-note">Generated ${new Date().toISOString().slice(0,10)} from the EGRISS identification-questions `+
  `dataset built ${esc(m.built||"")}. Sources: ${vintageText()}. Translations are unreviewed drafts. `+
  `Corrections: ${esc(issueURL())}</small></p>`;
}
function renderFooter(){
 const m=META||{};
 document.getElementById('pagefoot').innerHTML=
  `Dataset built ${esc(m.built||"")}. Sources: ${vintageText()}. `+
  `Found an office renamed, a document called something else, an example that is wrong? `+
  `<a id="issueLink2" href="${issueURL()}" target="_blank" rel="noopener">Report a correction</a> `+
  `(pre-filled with the country and a link to this set-up). Generated by `+
  `<code>prototype-python/build_questions.py</code>. Ctrl/Cmd-P prints the form alone.`;
}

// ---------------------------------------------------------------------
// Interviewer instructions - a second, richer document beside the
// questionnaire, modelled on the question-by-question format of the MICS6
// Instructions for Interviewers and the DHS-8 Interviewer's Manual:
// each item gets its purpose, how to ask it, definitions, probing rules,
// recording rules and common errors, and then a country box built from the
// same databases that customise the questionnaire (event provenance, the
// office and document record, DTM reasons, the survey overlay's history).
// English only for now - interviewer manuals are normally translated as a
// separate, reviewed exercise.
const INSTR={
 frcfl:{name:"FrcFl", title:"Forced to flee",
  purpose:"The module's screening question: it establishes whether the respondent has EVER had to flee a home, and from which causes. Every later question depends on it, so an error here travels through the whole module.",
  how:"Read the two introductory sentences first, slowly - they define what &ldquo;flee a home&rdquo; means. Then read the lead-in and each response option WITH its example. The examples are part of the question: cognitive testing found that when they were withheld, respondents failed to recognise events that qualify. Read up to three examples per option at an even pace.",
  defs:["<b>Flee a home</b> means leaving a home, or land, because of events that threatened the respondent's or their family's safety. It does NOT require panic or a sudden escape: packing over several days, or leaving after a threat rather than during an attack, still counts.",
        "<b>A home</b> includes land the respondent lived on.",
        "<b>In your lifetime</b> - the question is about the whole life, not recent years. If the respondent answers only about the current crisis, remind them: &ldquo;at any time in your life&rdquo;."],
  probe:"If the respondent hesitates over whether their situation &ldquo;counts&rdquo;, re-read the option and its examples and let THEM decide - never decide for them. If they describe leaving for work or family reasons with no threat, do not code an option; &ldquo;None of the above&rdquo; exists for exactly that answer, and the follow-up question (FrcOth) will catch reasons the list misses.",
  record:"Tick EVERY option the respondent confirms - multiple answers are expected. &ldquo;None of the above&rdquo; is an exclusive code: if it is ticked, nothing else may be.",
  errors:["Skipping the examples to save time - the single most damaging shortcut in testing.",
          "Treating the question as being about the most recent move only.",
          "Coding economic hardship as a threat. Hardship without a safety threat belongs at FrcOth, where it is recorded and then classified as valid or not under this country's rules."]},
 frcoth:{name:"FrcOth", title:"Other reasons for fleeing",
  purpose:"Catches valid reasons the main list misses, and screens OUT answers that do not qualify - it is the module's main protection against false positives.",
  how:"Read the question and then STOP. Do not read the list below it - it is a back-coding list for you and the office, not response options.",
  defs:["An answer is recorded here whenever the respondent chose &ldquo;a different threat&rdquo; at FrcFl."],
  probe:"Neutral probes only: &ldquo;Can you tell me a little more about that?&rdquo; Do not suggest any of the listed reasons.",
  record:"Write the answer VERBATIM, in the respondent's own words. Coding against the list happens afterwards. Two soft checks while you write: risk of conscription or forced recruitment belongs at FrcFl under armed conflict or widespread violence - re-ask FrcFl if that is what you heard; mass evictions for infrastructure projects belong at FrcFl under man-made events, while a one-off eviction by a landlord stays here.",
  errors:["Reading the back-coding list aloud.","Summarising instead of recording verbatim."]},
 fleeloc:{name:"FleeLoc", title:"Location of displacement",
  purpose:"Separates displacement that began inside the survey country from displacement that began abroad - the fork between the IDP track and the refugee track.",
  how:"Read as written. If the respondent fled more than once, the question is about the FIRST home they had to flee.",
  defs:[],
  probe:"If the respondent starts describing several displacements, bring them back to the first one: &ldquo;the first home you ever had to flee&rdquo;.",
  record:"One answer only. For &ldquo;Other country&rdquo;, write the country's name.",
  errors:["Recording the most recent displacement instead of the first."]},
 idploc:{name:"IDPLoc", title:"Location before displacement",
  purpose:"Lets IDPs be sub-categorised by comparing where they lived before displacement with where they live now (location of return vs elsewhere).",
  how:"Open question. Record as much geographic detail as the respondent can give.",
  defs:[],
  probe:"If they give only a village or town, ask for the district and province too.",
  record:"Write village or town, then county/district, then province - all that are known.",
  errors:["Accepting a single place-name when more detail was available."]},
 locliv:{name:"LocLiv / CitLoc", title:"Always lived there / citizenship",
  purpose:"IRIS's condition for counting someone as an IDP: a person displaced inside a country they were only passing through, and whose citizenship lies elsewhere, is not an IDP of that country. If citizenship at the time of displacement is captured elsewhere in your survey, these two questions may be dropped.",
  how:"Read as written. &ldquo;Always lived&rdquo; ignores short or temporary absences - holidays, seasonal work, study.",
  defs:["<b>Always lived</b>: their usual residence was there; short absences do not break it."],
  probe:"If the respondent lists periods abroad, ask whether those were temporary stays or moves.",
  record:"Yes/No each. CitLoc is asked only when LocLiv = No.",
  errors:["Treating a season of work abroad as breaking &ldquo;always lived&rdquo;."]},
 fleecross:{name:"FleeCross", title:"Moved to another country",
  purpose:"Routing and classification: it separates those who stayed inside the country (IDP track) from those who crossed a border (refugee track), and in the IDP-only version it is the exclusion condition for people who established residence abroad.",
  how:"Read as written, including &ldquo;even if this was only temporary&rdquo; - those words do real work.",
  defs:["Any move to another country counts, however short, including a stay in a border town or a camp just across the border."],
  probe:"Respondents often omit short crossings. If the story mentioned a border area, ask: &ldquo;including any short stay in another country?&rdquo;",
  record:"Yes/No.",
  errors:["Letting a respondent answer No because the stay abroad was brief - brief stays are exactly what the 12Mnths question then sorts out."]},
 idppost:{name:"IDPPost", title:"First place moved to",
  purpose:"With IDPLoc, sub-categorises IDPs into location of displacement vs other settlement.",
  how:"The FIRST place they moved to, not where they live now. Stopovers - places passed through in transit, days rather than weeks - do not count.",
  defs:[],
  probe:"&ldquo;Where did you first stay for some time?&rdquo;",
  record:"Village or town, county/district, province.",
  errors:["Recording the current address.","Recording a transit stop."]},
 mnths12:{name:"12Mnths", title:"Time abroad",
  purpose:"Applies the usual-residence rule: 12 months or more abroad establishes a new country of residence. In the IDP-only version, 12 months or more means the respondent is a returning migrant, not an IDP.",
  how:"Read as written; prompt with the two bands.",
  defs:["Count the total continuous stay after fleeing, not separate trips added together."],
  probe:"If unsure, anchor on events: &ldquo;did you spend a full year there - a planting season and a harvest, two winters?&rdquo;",
  record:"One band.",
  errors:["Adding up several short stays into one figure."]},
 apply:{name:"Apply", title:"Applied for international protection",
  purpose:"The central refugee-track question. IRRS defines an asylum seeker by having LODGED a claim, so this question is about a formal application - not about receiving help.",
  how:"Read the question as written, then ONE of the two localisation versions - A names the office where a claim is lodged, B names the document the claim produces. Version B is often recalled better; where a specimen image is provided, show it while asking.",
  defs:["<b>International protection</b> covers refugee status, asylum, and this country's equivalents. Cognitive interviews found the bare phrase poorly understood - the example carries the question.",
        "<b>Applied</b> means the respondent (or their household for them) lodged a claim - registering for assistance is NOT applying."],
  probe:"If the respondent says they &ldquo;registered&rdquo;, establish what for: registration for aid or a ration card is not an application for protection. Ask what office it was and what document they received - the country box below tells you what the right answers look like here.",
  record:"Yes/No. Yes routes to Outcome; No routes to IntApply where that question is included.",
  errors:["Counting registration for assistance as an application - the main false-positive risk, especially where UNHCR registers people in parallel to the government procedure.",
          "Respondents who applied YEARS ago under a different office or organisation answering No because the named office did not exist then - the country box lists the older names to listen for."]},
 intapply:{name:"IntApply", title:"Intended to apply",
  purpose:"Identifies prospective asylum seekers - people who have not lodged a claim but plan to.",
  how:"Read as written.",defs:["Intention is enough; no step needs to have been taken."],
  probe:"None beyond a neutral repeat.",record:"Yes/No.",errors:[]},
 outcome:{name:"Outcome", title:"Outcome of the application",
  purpose:"Separates recognised refugees, pending asylum seekers, and failed or withdrawn applications.",
  how:"Read all four options before accepting an answer.",
  defs:["<b>Still being decided</b> includes appeals.","<b>Withdrew</b> is the respondent's own decision to stop - different from denied."],
  probe:"If the respondent holds a renewable card but never heard a decision, that is usually &ldquo;still being decided&rdquo; - probe for whether a decision was ever communicated.",
  record:"One answer.",errors:["Coding an expired or unrenewed document as &ldquo;denied&rdquo;."]},
 legal:{name:"Legal", title:"Main document held",
  purpose:"Distinguishes types of protection (temporary, complementary, permanent), identifies naturalised former refugees, and quality-assures the answers above.",
  how:"Read the question, then work through the category headers; read the options under a header only when the header fits. One MAIN document - the one that allows them to stay.",
  defs:["If the respondent holds several documents, the main one is the one that gives the right to stay - not a ration card or appointment slip."],
  probe:"Ask to see the document if the respondent is willing - never insist. The country box lists what the documents are called here, including everyday names.",
  record:"One answer.",errors:["Recording an assistance or enrolment token as the main stay document when a status document exists."]},
};

// The country box for one item: everything the databases know that an
// interviewer in this country should have in hand.
function instrCountryBox(key,iso,v,r,mode){
 const bits=[];
 const cu=effCust(iso);
 if(key==="frcfl"){
  const rows=P.filter(x=>x.iso3===iso&&x.localised);
  if(rows.length){
   bits.push(`<b>Where the examples come from.</b> The examples in this questionnaire were drafted from recorded events, so you can answer &ldquo;why that example?&rdquo;:`);
   bits.push(`<ul>`+rows.slice(0,10).map(x=>`<li><i>${esc(x.example)}</i> &mdash; ${esc(x.source)}${x.evidence?`; ${esc(x.evidence)}`:""}</li>`).join("")+`</ul>`);
  }
 }
 if(key==="frcoth"&&cu.dtm&&cu.dtm.length){
  bits.push(`<b>What people here actually answer.</b> Among displaced people IOM DTM interviewed in this country, reasons given outside the FrcFl codes: `+
   cu.dtm.map(([x,pc])=>pc!=null?`${esc(x)} (${pc}%)`:esc(x)).join(", ")+`. Expect these; record them verbatim.`);
 }
 if(key==="fleeloc"&&cu.origins&&cu.origins.length){
  bits.push(`<b>Likely &ldquo;other country&rdquo; answers here:</b> ${cu.origins.map(esc).join(", ")} &mdash; the largest displaced populations hosted in this country (UNHCR).`);
 }
 if((key==="idploc"||key==="idppost")&&cu.adm&&cu.adm.length){
  bits.push(`<b>Areas you will hear most often:</b> ${cu.adm.map(esc).join(", ")} &mdash; the areas with the most recorded displacement events (UCDP, IDMC).`);
 }
 if(key==="fleecross"&&cu.dest&&cu.dest.length){
  bits.push(`<b>Likely destinations named here:</b> ${cu.dest.map(esc).join(", ")} &mdash; where this country's nationals are registered as refugees or asylum seekers (UNHCR).`);
 }
 if(key==="apply"&&r){
  if(r.reg==="NONE"){ bits.push(`No registration or protection procedure exists in this country; this sequence is not asked.`); }
  else{
   const who={GOVERNMENT:"the Government",UNHCR:"UNHCR",BOTH:"both the Government and UNHCR"}[r.reg]||r.reg;
   bits.push(`<b>Who registers claims here:</b> ${who} (source confidence ${esc(r.cf)}).`);
   if(r.org) bits.push(`<b>The office (Version A):</b> ${esc(r.org)}${r.orgL?` &mdash; <i>${esc(r.orgL)}</i> in the local language`:""}${r.alt&&r.alt.length?`; also heard as: ${esc(r.alt.join("; "))}`:""}.${r.ow?` ${esc(r.ow)}.`:""}`);
   const dn=r.da||r.dr;
   if(dn) bits.push(`<b>The document (Version B):</b> ${esc(dn)}${(r.da?r.daC:r.drC)?` &mdash; people call it &ldquo;${esc(r.da?r.daC:r.drC)}&rdquo;`:""}${r.da&&r.dr&&r.dr!==r.da?`; on recognition it becomes ${esc(r.dr)}${r.drC?` (&ldquo;${esc(r.drC)}&rdquo;)`:""}`:""}.${r.dw?` ${esc(r.dw)}.`:""}`);
   if(r.cols&&r.cols.length) bits.push(`<b>Colour names in use:</b> ${esc(r.cols.join(", "))} &mdash; respondents often know the document by its colour; accept these answers.`);
   if(r.mis) bits.push(`<b>The office wording does not work well here.</b> Claims are actually lodged like this: ${esc(r.how)}. Use Version B (the document).`);
   if(r.cav) bits.push(`<b>Background and history to listen for.</b> ${esc(r.cav)}`);
   const sp=SPEC[iso];
   if(sp&&sp.images&&sp.images.length) bits.push(`<b>Show card:</b> a specimen of the document is included in the questionnaire download &mdash; show it while asking.`);
  }
 }
 if(key==="legal"&&r&&r.reg!=="NONE"){
  const l=[];
  if(r.da) l.push(`asylum applicant document = <b>${esc(r.da)}</b>`);
  if(r.dr) l.push(`refugee = <b>${esc(r.dr)}</b>`);
  if(r.svd&&r.svd.length) l.push(`UNHCR itself issues: ${r.svd.map(x=>x.toLowerCase()).join(", ")}`);
  if(l.length) bits.push(`<b>What the protected-status options are called here:</b> ${l.join("; ")}.`);
  if(r.cols&&r.cols.length) bits.push(`<b>Everyday colour names:</b> ${esc(r.cols.join(", "))}.`);
 }
 if(key==="fleecross"&&mode==="idp") bits.push(`<b>In the IDP-only version</b> this question exists to exclude people who established residence abroad; it is asked only when the home fled was in the survey country.`);
 if(key==="apply"&&mode==="idp") bits.push(`<b>In the IDP-only version</b> this is a screening question: Yes means the respondent is a repatriated refugee or asylum seeker, not an IDP, and the module ends.`);
 return bits.length?`<div class="ibox"><div class="ibox-h">In ${esc((Q[iso]&&Q[iso].name)||iso)}</div>${bits.map(b=>`<p>${b}</p>`).join("")}</div>`:"";
}

function instrSection(key,iso,v,r,mode){
 const d=INSTR[key]; if(!d) return "";
 let h=`<h2>${d.name} &mdash; ${d.title}</h2>`;
 h+=`<p><b>Purpose.</b> ${d.purpose}</p>`;
 h+=`<p><b>How to ask.</b> ${d.how}</p>`;
 if(d.defs.length) h+=`<p><b>Definitions.</b></p><ul>`+d.defs.map(x=>`<li>${x}</li>`).join("")+`</ul>`;
 if(d.probe) h+=`<p><b>Probing.</b> ${d.probe}</p>`;
 if(d.record) h+=`<p><b>Recording.</b> ${d.record}</p>`;
 if(d.errors.length) h+=`<p><b>Common errors.</b></p><ul>`+d.errors.map(x=>`<li>${x}</li>`).join("")+`</ul>`;
 h+=instrCountryBox(key,iso,v,r,mode);
 return h;
}

function buildInstructionsHTML(iso){
 const v=Q[iso], r=effReg(iso), mode=fwMode();
 const langName=(LANGS[LANG]&&LANGS[LANG][0])||LANG;
 let h=`<!DOCTYPE html><html><head><meta charset="utf-8">`+
  `<title>${esc(v.name)} &mdash; instructions</title><style>${EXPORT_CSS}${INSTR_CSS}${DERIV_CSS}</style></head><body>`;
 h+=`<h1>${esc(v.name)} &mdash; instructions</h1>`+
  `<p class="lede">Part A is for the survey coordinator: where the questions go and who answers, the checks to make before `+
  `fielding, and a pretest protocol. Part B is the question-by-question interviewer instructions: for each question, `+
  `its purpose, how to ask it, definitions, probing, recording, and common errors &mdash; followed by a box of `+
  `what is specific to ${esc(v.name)}, drawn from the same sources that customised the questionnaire. `+
  `<b>Draft for review; instructions are in English</b> &mdash; an interviewer manual is normally translated as `+
  `its own reviewed exercise. Questionnaire settings when this file was generated: ${esc(VERSION_DEFS[VER]?VERSION_DEFS[VER].label:"Long")} version, `+
  `${LEN==="showcard"?"show card":"read-aloud"} length, ${esc(langName)}, `+
  `${mode==="idp"?"IDP-only (IRIS)":mode==="ref"?"refugee-only (IRRS)":"combined refugee and IDP"} questionnaire.</p>`;
 h+=coordinatorHTML(iso);
 h+=`<h2>Part B &mdash; for interviewers</h2>`;
 h+=`<h3>General rules</h3><ul>`+
  `<li><b>Read every question exactly as written.</b> The parts in blue (or purple, where the coordinator changed them) are also read as written &mdash; they are not yours to improvise; they were drafted for this country and are listed with their sources below.</li>`+
  `<li><b>Anything in CAPITAL LETTERS or brackets is never read aloud</b> &mdash; it is an instruction to you.</li>`+
  `<li><b>The italic line above each question is its skip rule</b>: it says who gets the question. Follow the arrows after response options.</li>`+
  `<li><b>Never suggest an answer.</b> Probe neutrally: repeat the question, or ask &ldquo;can you tell me more?&rdquo;.</li>`+
  `<li><b>Read the examples.</b> They are part of the question: testing found respondents fail to recognise qualifying events without them.</li>`+
  `<li><b>Record immediately</b>, and verbatim where the question is open.</li></ul>`;
 const items=["frcfl"];
 if(itemActive("frcoth")) items.push("frcoth");
 items.push("fleeloc");
 if(itemActive("idploc")) items.push("idploc");
 if(itemActive("locliv")) items.push("locliv");
 items.push("fleecross");
 if(itemActive("idppost")) items.push("idppost");
 if(itemActive("mnths12")) items.push("mnths12");
 if(FW.refugee||mode==="idp") items.push("apply");
 if(itemActive("intapply")) items.push("intapply");
 if(mode!=="idp"&&FW.refugee) items.push("outcome");
 if(itemActive("legal")) items.push("legal");
 items.forEach(k=>{h+=instrSection(k,iso,v,r,mode);});
 h+=stampHTML();
 h+=`</body></html>`;
 return h;
}
const INSTR_CSS=`
ul.chk li{margin-bottom:4pt}
.ibox{background:#f4f7fc;border:1pt solid #c9d6ea;border-radius:6pt;padding:8pt 11pt;margin:8pt 0 14pt}
.ibox-h{font-size:8.5pt;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#3b71b9;margin-bottom:4pt}
.ibox p{margin:0 0 6pt;font-size:10pt}
.ibox ul{margin:2pt 0 6pt;padding-left:14pt;font-size:9.5pt}
h2{page-break-inside:avoid}
`;

// =====================================================================
// For the survey coordinator: the classification rules as a small engine
// (shared by the derivation sheet and the walkthrough), the walkthrough
// panel, the checks-before-fielding list, the coordinator part of the
// instructions, and the translation template.
// =====================================================================

// ---- variables the module produces, as named in the derivation sheet ----
// Every code here is the position of the option in the module (Legal's 18
// options numbered down the list, its category headers kept as groups).
const VARS=[
 ["frcfl_1 … frcfl_7","FrcFl","0/1 for each of options 1–7 (armed conflict, widespread violence, persecution, human-rights violations, other violence, natural disasters, man-made events); several may be 1"],
 ["frcfl_8","FrcFl","1 if ‘a different threat’ was ticked"],
 ["frcfl_none","FrcFl","1 if ‘none of the above’ (exclusive)"],
 ["frcoth_valid","FrcOth","1 if the ‘different threat’ was coded to a reason this country treats as a valid cause of forced displacement; 0 otherwise. Set on the page: {frcoth}"],
 ["fd_hist","derived","1 if any of frcfl_1…frcfl_7 = 1 or frcoth_valid = 1 — a history of forced displacement"],
 ["fleeloc","FleeLoc","1 survey country · 2 other country (fleeloc_oth holds the name)"],
 ["locliv","LocLiv","1 yes · 2 no"],
 ["citloc","CitLoc","1 yes · 2 no (asked of everyone who fled)"],
 ["fleecross","FleeCross","1 yes · 2 no"],
 ["mnths12","12Mnths","1 less than 12 months · 2 twelve months or more"],
 ["apply","Apply","1 yes · 2 no"],
 ["intapply","IntApply","1 yes · 2 no (asked only when apply = 2)"],
 ["outcome","Outcome","1 granted · 2 denied · 3 still being decided · 4 withdrawn"],
 ["legal","Legal","1 no documents · 2–7 visas (tourist, student, work, humanitarian, family, other) · 8 regional free-movement agreement · 9 permanent resident · 10 passport · 11 other citizenship document · 12 asylum applicant document · 13 refugee · 14 recognised stateless person · 15 complementary/subsidiary protection · 16 temporary protection · 17 enrolment document · 18 other"],
 ["loc_now_idppost","derived","1 if the current dwelling's location is the location recorded at IDPPost (compare at the lowest administrative level both are coded to)"],
 ["loc_now_idploc","derived","1 if the current dwelling's location is the location recorded at IDPLoc"],
];
const LEGAL_PERM=[9,10,11], LEGAL_PROT=[12,13,14,15,16];

// A condition is an AND of clauses; a clause is an OR of atoms
// [variable, op, value(s)] with op eq / in / nin.
const eq=(v,x)=>[v,"eq",x], inl=(v,xs)=>[v,"in",xs], nin=(v,xs)=>[v,"nin",xs];
function evalAtom(a,ans){ const v=ans[a[0]]; if(v==null) return false;
 if(a[1]==="eq") return v===a[2]; if(a[1]==="in") return a[2].includes(v); return !a[2].includes(v); }
const evalCond=(cond,ans)=>cond.every(cl=>cl.some(a=>evalAtom(a,ans)));

// The rules for the questionnaire as configured: which optional items are in
// it decides how fine the categories can be. Order matters - the first rule
// that fits wins, which is also how the generated code is written.
function ruleSet(){
 const A=itemActive, mode=fwMode();
 const has={intapply:A("intapply"),legal:A("legal"),locliv:A("locliv"),m12:A("mnths12"),
            idploc:A("idploc"),idppost:A("idppost"),outcome:mode!=="idp",frcoth:A("frcoth")};
 const R=[]; const add=(code,label,group,cond,note,fwref)=>R.push({code,label,group,cond,note,fwref});
 const FD=[[eq("fd_hist",1)]];
 // --- no history of forced displacement ---
 if(has.legal) add(31,"Others with a refugee background — protected-status document without a forced-displacement history","none",[[eq("fd_hist",0)],[inl("legal",LEGAL_PROT)]],
   "IRRS b.4 as the module approximates it: children of refugees born here without full citizenship, people who claimed protection while away from home, status granted in error - the questions cannot separate these.","IRRS b.4");
 add(30,"No history of forced displacement","none",[[eq("fd_hist",0)]],null,"—");
 if(mode!=="idp"){
  // --- first displaced outside the survey country: IRRS a and b ---
  const OUT=FD.concat([[eq("fleeloc",2)]]);
  if(has.legal){
   add(12,"Admitted for complementary and subsidiary forms of protection","ref",OUT.concat([[eq("legal",15)]]),
     "Read from the document held, whether or not an application was made (some are granted on a group basis).","IRRS a.3.ii");
   add(13,"Admitted for temporary protection","ref",OUT.concat([[eq("legal",16)]]),
     "Read from the document held, whether or not an application was made.","IRRS a.3.iii");
   add(11,"Refugees","ref",OUT.concat([[eq("apply",1)],[eq("outcome",1)],[nin("legal",LEGAL_PERM)]]),
     "Refugee status granted and no permanent residence or citizenship since.","IRRS a.3.i");
   add(17,"Naturalised former refugees","ref",OUT.concat([[eq("apply",1)],[eq("outcome",1)],[inl("legal",LEGAL_PERM)]]),null,"IRRS b.1");
  }else add(11,"Refugees — including those since naturalised and those under complementary or temporary protection","ref",OUT.concat([[eq("apply",1)],[eq("outcome",1)]]),
     "Legal is not in this questionnaire, so IRRS a.3.i–iii and b.1 cannot be separated.","IRRS a.3, b.1");
  add(14,"Asylum seekers","ref",OUT.concat([[eq("apply",1)],[eq("outcome",3)]]),null,"IRRS a.2");
  add(18,"Failed or withdrawn asylum application","ref",OUT.concat([[eq("apply",1)],[inl("outcome",[2,4])]]),
    "Not an IRRS category; kept separately (Classification Table). May hold another legal basis for staying - see Legal - or none.","—");
  if(has.intapply){
   add(15,"Prospective asylum seekers","ref",OUT.concat([[eq("apply",2)],[eq("intapply",1)]]),null,"IRRS a.1");
   if(has.legal) add(16,"Others in refugee-like situations","ref",OUT.concat([[eq("apply",2)],[eq("intapply",2)],[inl("legal",[2,3,4,5,6,7,8])]]),
     "Fled and never applied, admitted on a visa or under a regional free-movement agreement (paper, p. 19).","IRRS a.4");
   add(19,"Displaced abroad, no application for protection and no intention to apply","ref",OUT.concat([[eq("apply",2)],[eq("intapply",2)]]),
     has.legal?"Another legal basis for being here (citizenship, permanent residence), undocumented, or an enrolment document - not an IRRS category.":"Legal is not in this questionnaire, so ‘others in refugee-like situations’ (IRRS a.4) cannot be separated from this group.","—");
  }else{
   if(has.legal) add(16,"Others in refugee-like situations — prospective asylum seekers included","ref",OUT.concat([[eq("apply",2)],[inl("legal",[2,3,4,5,6,7,8])]]),
     "IntApply is not in this questionnaire, so prospective asylum seekers (IRRS a.1) cannot be separated.","IRRS a.4 (+a.1)");
   add(19,"Displaced abroad, no application for protection","ref",OUT.concat([[eq("apply",2)]]),
     "IntApply is not in this questionnaire, so prospective asylum seekers (IRRS a.1) cannot be separated from those with no intention to apply.","—");
  }
 }
 if(mode!=="ref"){
  // --- first displaced inside the survey country: IRIS 1 and IRRS c ---
  let IN=FD.concat([[eq("fleeloc",1)]]);
  if(has.locliv){
   add(28,"Displaced inside the survey country while neither usually resident nor a citizen of it (not an IDP)","idp",IN.concat([[eq("locliv",2)],[eq("citloc",2)]]),
     "For example a refugee later displaced within the host country; classify through the refugee track or Legal (IRIS para. 5, condition 2).","—");
   IN=IN.concat([[eq("locliv",1),eq("citloc",1)]]);
  }
  // sought protection abroad -> IRRS c, not an IDP
  if(has.outcome){
   add(25,"Repatriating refugees","idp",IN.concat([[eq("fleecross",1)],[eq("apply",1)],[eq("outcome",1)]]),null,"IRRS c.1");
   add(24,"Repatriating asylum seekers","idp",IN.concat([[eq("fleecross",1)],[eq("apply",1)],[inl("outcome",[2,3,4])]]),null,"IRRS c.2");
  }else add(24,"Sought international protection abroad — not an IDP (repatriating refugee or asylum seeker)","idp",IN.concat([[eq("fleecross",1)],[eq("apply",1)]]),
     "In the IDP-only questionnaire Outcome is not asked, so IRRS c.1 and c.2 cannot be separated.","IRRS c.1–2");
  if(has.m12) add(26,"Returned after 12 months or more abroad without applying — returning from international protection abroad, others returning, or a returning migrant","idp",IN.concat([[eq("fleecross",1)],[eq("mnths12",2)],[eq("apply",2)]]),
    "Established residence abroad, so not an IDP (IRIS paras 15–17); the module cannot tell IRRS c.3 and c.4 from a returning migrant (paper, p. 17).","IRRS c.3–4 / not IDP");
  // IDPs: never left, or left for under 12 months without applying
  const IDP=has.m12?IN.concat([[eq("fleecross",2),eq("mnths12",1)],[eq("fleecross",2),eq("apply",2)]])
                   :IN.concat([[eq("fleecross",2)]]);
  if(has.idppost) add(21,"IDPs in locations of displacement","idp",IDP.concat([[eq("loc_now_idppost",1)]]),null,"IRIS 1");
  if(has.idploc) add(22,"IDPs in locations of return","idp",IDP.concat([[eq("loc_now_idploc",1)]]),null,"IRIS 1");
  if(has.idploc&&has.idppost) add(23,"IDPs in other settlement locations","idp",IDP.concat([[eq("loc_now_idppost",0)],[eq("loc_now_idploc",0)]]),null,"IRIS 1");
  add(20,(has.idploc||has.idppost)?"IDPs — location sub-category undetermined":"IDPs (total stock)","idp",IDP,
    (has.idploc||has.idppost)?"Location could not be compared (a location missing or not coded)":"IDPLoc and IDPPost are not in this questionnaire, so the three IRIS location sub-categories cannot be formed.","IRIS 1");
  if(!has.m12) add(27,"Moved abroad and returned without applying — IDP or returning migrant, undetermined","idp",IN.concat([[eq("fleecross",1)],[eq("apply",2)]]),
    "12Mnths is not in this questionnaire, so returning migrants (12 months or more abroad) cannot be separated from IDPs who were abroad briefly.","IRIS 1 / IRRS c.3–4");
  if(!has.locliv) R.filter(r=>r.group==="idp"&&r.code<28).forEach(r=>r.note=(r.note?r.note+" ":"")+"LocLiv/CitLoc are not in this questionnaire: the IDP condition (usually resident, or a citizen, where the causing event occurred) must come from elsewhere in the survey.");
 }
 if(mode==="ref") add(29,"Internal displacement only - out of scope for the refugee questionnaire","idp",FD.concat([[eq("fleeloc",1)],[eq("fleecross",2)]]),null,"—");
 if(mode==="idp") add(29,"Displaced from a home in another country - out of scope for the IDP questionnaire","ref",FD.concat([[eq("fleeloc",2)]]),null,"—");
 add(90,"Not classifiable (missing or inconsistent answers)","none",[],null,"—");
 return R;
}
function classify(ans){ const R=ruleSet(); for(const r of R){ if(r.code===90) continue; if(evalCond(r.cond,ans)) return r; } return R[R.length-1]; }

// ---- rendering a condition in three languages ----
const REND={
 stata:{atom:a=>a[1]==="eq"?`${a[0]}==${a[2]}`:a[1]==="in"?`inlist(${a[0]},${a[2].join(",")})`:`!inlist(${a[0]},${a[2].join(",")})`,or:" | ",and:" & "},
 r:{atom:a=>a[1]==="eq"?`${a[0]} == ${a[2]}`:a[1]==="in"?`${a[0]} %in% c(${a[2].join(", ")})`:`!(${a[0]} %in% c(${a[2].join(", ")}))`,or:" | ",and:" & "},
 py:{atom:a=>a[1]==="eq"?`(df["${a[0]}"] == ${a[2]})`:a[1]==="in"?`df["${a[0]}"].isin([${a[2].join(", ")}])`:`~df["${a[0]}"].isin([${a[2].join(", ")}])`,or:" | ",and:" & "},
};
function condText(cond,lang){ const L=REND[lang];
 if(!cond.length) return lang==="py"?"True":"1==1";
 return cond.map(cl=>cl.length>1?"("+cl.map(L.atom).join(L.or)+")":L.atom(cl[0])).join(L.and); }
function condPlain(cond){
 const NM={fd_hist:"history of forced displacement",fleeloc:"FleeLoc",locliv:"LocLiv",citloc:"CitLoc",fleecross:"FleeCross",mnths12:"12Mnths",apply:"Apply",intapply:"IntApply",outcome:"Outcome",legal:"Legal",loc_now_idppost:"current location = IDPPost",loc_now_idploc:"current location = IDPLoc"};
 const VAL={fleeloc:{1:"survey country",2:"other country"},locliv:{1:"yes",2:"no"},citloc:{1:"yes",2:"no"},fleecross:{1:"yes",2:"no"},mnths12:{1:"under 12 months",2:"12 months or more"},apply:{1:"yes",2:"no"},intapply:{1:"yes",2:"no"},outcome:{1:"granted",2:"denied",3:"pending",4:"withdrawn"},fd_hist:{1:"yes",0:"no"},loc_now_idppost:{1:"yes",0:"no"},loc_now_idploc:{1:"yes",0:"no"}};
 const at=a=>{ const n=NM[a[0]]||a[0], vv=x=>(VAL[a[0]]&&VAL[a[0]][x]!=null)?VAL[a[0]][x]:x;
  if(a[1]==="eq") return `${n} = ${vv(a[2])}`;
  if(a[0]==="legal") return a[1]==="in"?`Legal in ${a[2][0]}–${a[2][a[2].length-1]} (${a[2][0]===9?"permanent residence or citizenship":"protected status"})`:`Legal not in ${a[2][0]}–${a[2][a[2].length-1]}`;
  return `${n} ${a[1]==="in"?"in":"not in"} (${a[2].map(vv).join(", ")})`; };
 if(!cond.length) return "any remaining case";
 return cond.map(cl=>cl.length>1?"("+cl.map(at).join(" or ")+")":at(cl[0])).join(" and "); }

// ---- the derivation sheet ----
function derivationCode(R,lang){
 const codes=R.filter(r=>r.code!==90);
 const lab=r=>r.label.replace(/"/g,"'");
 if(lang==="stata") return [
  `* Derived inputs`,
  `gen byte fd_hist = (frcfl_1==1 | frcfl_2==1 | frcfl_3==1 | frcfl_4==1 | frcfl_5==1 | frcfl_6==1 | frcfl_7==1${itemActive("frcoth")?" | frcoth_valid==1":""})`,
  `* loc_now_idppost / loc_now_idploc: build from your admin codes before this block`,
  `gen fdcat = .`,
  ...codes.map(r=>`replace fdcat = ${r.code} if missing(fdcat) & ${condText(r.cond,"stata")}`),
  `replace fdcat = 90 if missing(fdcat)`,
  `label define fdcat ${codes.map(r=>`${r.code} "${lab(r)}"`).join(" ")} 90 "Not classifiable"`,
  `label values fdcat fdcat`,
  `tab fdcat`].join("\\n");
 if(lang==="r") return [
  `library(dplyr)`,
  `df <- df %>% mutate(`,
  `  fd_hist = as.integer(frcfl_1==1 | frcfl_2==1 | frcfl_3==1 | frcfl_4==1 | frcfl_5==1 | frcfl_6==1 | frcfl_7==1${itemActive("frcoth")?" | frcoth_valid==1":""}),`,
  `  # loc_now_idppost / loc_now_idploc: build from your admin codes before this`,
  `  fdcat = case_when(`,
  ...codes.map(r=>`    ${condText(r.cond,"r")} ~ ${r.code}L,`),
  `    TRUE ~ 90L),`,
  `  fdcat_lab = factor(fdcat, levels = c(${codes.map(r=>r.code).join(", ")}, 90),`,
  `    labels = c(${codes.map(r=>`"${lab(r)}"`).join(", ")}, "Not classifiable")))`,
  `table(df$fdcat_lab, useNA = "ifany")`].join("\\n");
 return [
  `import numpy as np, pandas as pd`,
  `df["fd_hist"] = (df[["frcfl_1","frcfl_2","frcfl_3","frcfl_4","frcfl_5","frcfl_6","frcfl_7"]].eq(1).any(axis=1)${itemActive("frcoth")?' | df["frcoth_valid"].eq(1)':""}).astype(int)`,
  `# loc_now_idppost / loc_now_idploc: build from your admin codes before this`,
  `conds = [`,
  ...codes.map(r=>`    ${condText(r.cond,"py")},`),
  `]`,
  `codes = [${codes.map(r=>r.code).join(", ")}]`,
  `df["fdcat"] = np.select(conds, codes, default=90)`,
  `labels = {${codes.map(r=>`${r.code}: "${lab(r)}"`).join(", ")}, 90: "Not classifiable"}`,
  `df["fdcat_lab"] = df["fdcat"].map(labels)`,
  `print(df["fdcat_lab"].value_counts(dropna=False))`].join("\\n");
}
function buildDerivationHTML(iso){
 const v=Q[iso], R=ruleSet(), mode=fwMode();
 const subs=SUBCATS.filter(subActive);
 let h=`<!DOCTYPE html><html><head><meta charset="utf-8"><title>${esc(v.name)} &mdash; derivation sheet</title><style>${EXPORT_CSS}${DERIV_CSS}</style></head><body>`;
 h+=`<h1>${esc(v.name)} &mdash; derivation sheet</h1>`+
  `<p class="lede">How the answers to the identification questions become population categories, for the questionnaire as configured on the page `+
  `(${mode==="idp"?"IDP-only, IRIS":mode==="ref"?"refugee-only, IRRS":"combined refugee and IDP"}; `+
  `${subs.length} framework categories identified). The rules are the Classification Table of the revised module mapped onto the IRRS and IRIS categories of the 2023 paper, `+
  `restricted to what the questionnaire actually asks: where an optional item is left out, the categories it would have separated are merged and the merge is noted. `+
  `First rule that fits wins. Draft for review.</p>`;
 const A=itemActive;
 const keep=new Set(["FrcFl","derived","FleeLoc","FleeCross","Apply"]);
 if(A("frcoth")) keep.add("FrcOth"); if(A("locliv")){keep.add("LocLiv");keep.add("CitLoc");}
 if(A("mnths12")) keep.add("12Mnths"); if(A("intapply")&&mode!=="idp") keep.add("IntApply");
 if(mode!=="idp") keep.add("Outcome"); if(A("legal")) keep.add("Legal");
 h+=`<h2>1. Variables</h2><table class="dv"><tr><th>Variable</th><th>From</th><th>Values</th></tr>`+
  VARS.filter(([n,from])=>keep.has(from)&&!(n==="frcoth_valid"&&!A("frcoth"))&&!(n==="loc_now_idppost"&&!A("idppost"))&&!(n==="loc_now_idploc"&&!A("idploc")))
   .map(([n,from,val])=>`<tr><td><code>${esc(n)}</code></td><td>${esc(from)}</td><td>${esc(val.replace("{frcoth}",frcothNames(iso).join("; ")||"nothing selected"))}</td></tr>`).join("")+`</table>`+
  `<p class="note">Code the FrcFl options as separate 0/1 variables${ADMIN==="grid"?" (each option is asked as its own Yes/No question, so they arrive that way)":" (it is a choose-all-that-apply question)"}. <code>frcoth_valid</code> is 1 when the reason recorded at FrcOth is one of: ${esc(frcothNames(iso).join("; ")||"nothing selected yet")} &mdash; ${esc(v.name)}'s own decision, to be documented with the dataset. `+
  `Location comparisons for the IDP sub-categories are made at the lowest administrative level both places are coded to.</p>`;
 // Framework coverage: every IRRS / IRIS category and how this questionnaire reaches it.
 const cov=SUBCATS.filter(c=>c.fw!=="shared"&&((c.fw==="refugee"&&mode!=="idp")||(c.fw==="idp"&&mode!=="ref")));
 h+=`<h2>2. Framework coverage</h2><p class="note">Every population category of the two statistical frameworks (2023 methodological paper), and whether this questionnaire identifies it.</p>`+
  `<table class="dv"><tr><th>Framework</th><th>Category</th><th>In this questionnaire</th></tr>`+
  cov.map(c=>{ const st=c.na?NA_LONG[c.na]+" — not from these questions":c.core?"identified by the core items":subActive(c)?`identified (adds ${c.items.map(k=>OPT_ITEMS[k].name).join(" + ")})`:`<i>not selected</i> — would need ${c.items.map(k=>OPT_ITEMS[k].name).join(" + ")}`;
   return `<tr><td>${c.fw==="idp"?"IRIS":"IRRS"} ${esc(c.grp)}</td><td>${esc(c.label)}<div class="note">${esc(c.cond)}</div></td><td>${st}</td></tr>`; }).join("")+`</table>`;
 h+=`<h2>3. Rules</h2><table class="dv"><tr><th>Code</th><th>Category</th><th>Condition</th></tr>`+
  R.map(r=>`<tr><td><code>${r.code}</code></td><td><b>${esc(r.label)}</b> <span class="fwref">${esc(r.fwref||"")}</span>${r.note?`<div class="note">${esc(r.note)}</div>`:""}</td><td>${esc(condPlain(r.cond))}</td></tr>`).join("")+`</table>`;
 h+=`<p class="note"><b>Household-roster categories.</b> Children, spouses and other family members living with a refugee, a naturalised former refugee, a repatriated refugee or an IDP are classified from the roster's relationship and parent-identification variables, not from these questions: a child of a person with <code>fdcat</code> in (11, 12, 25) is a &ldquo;child residing with a refugee parent&rdquo;, and so on. Only parents alive and in the same household can be linked.</p>`;
 h+=`<h2>4. Code</h2><p class="note">Each block assumes a dataset with the variables above and writes <code>fdcat</code> with the codes in section 3.</p>`;
 [["Stata","stata"],["R","r"],["Python (pandas)","py"]].forEach(([nm,lg])=>{ h+=`<h3>${nm}</h3><pre>${esc(derivationCode(R,lg))}</pre>`; });
 h+=stampHTML()+`</body></html>`;
 return h;
}
const DERIV_CSS=`
table.dv{border-collapse:collapse;width:100%;font-size:9.5pt;margin:6pt 0 10pt}
table.dv th{text-align:left;padding:4pt 6pt;border-bottom:1pt solid #1d2940;color:#5a6884;font-size:8.5pt;text-transform:uppercase;letter-spacing:.04em}
table.dv td{vertical-align:top;padding:4pt 6pt;border-bottom:0.5pt solid #dde1e8}
table.dv code,p.note code{font-family:Consolas,Menlo,monospace;font-size:9pt;color:#14234c}
p.note,div.note{font-size:9pt;color:#5a6884;margin:3pt 0 8pt}
.fwref{font-size:8pt;color:#3b71b9;font-weight:700;white-space:nowrap}
h3{font-family:Georgia,serif;color:#14234c;font-size:11pt;margin:12pt 0 4pt}
pre{font-family:Consolas,Menlo,monospace;font-size:8.5pt;line-height:1.4;background:#f4f7fc;border:0.5pt solid #c9d6ea;padding:8pt 10pt;white-space:pre-wrap;word-break:break-word}
`;

// ---- walkthrough ----
const WK_PRESETS=[
 {k:"none",label:"Clear"},
 {k:"ref",label:"Recognised refugee",a:{frcfl:1,fleeloc:2,locliv:1,fleecross:1,mnths12:2,apply:1,outcome:1,legal:13}},
 {k:"as",label:"Asylum seeker, pending",a:{frcfl:1,fleeloc:2,locliv:1,fleecross:1,mnths12:2,apply:1,outcome:3,legal:12}},
 {k:"pros",label:"Fled abroad, plans to apply",a:{frcfl:1,fleeloc:2,locliv:1,fleecross:1,mnths12:1,apply:2,intapply:1,legal:1}},
 {k:"nat",label:"Former refugee, now a citizen",a:{frcfl:1,fleeloc:2,locliv:1,fleecross:1,mnths12:2,apply:1,outcome:1,legal:10}},
 {k:"tp",label:"Temporary protection holder",a:{frcfl:1,fleeloc:2,locliv:1,fleecross:1,mnths12:2,apply:2,intapply:2,legal:16}},
 {k:"reflike",label:"Fled, here on a visa, never applied",a:{frcfl:1,fleeloc:2,locliv:1,fleecross:1,mnths12:2,apply:2,intapply:2,legal:4}},
 {k:"idp",label:"IDP, still displaced",a:{frcfl:1,fleeloc:1,locliv:1,fleecross:2,curloc:"post",legal:10}},
 {k:"idpret",label:"IDP who returned home",a:{frcfl:1,fleeloc:1,locliv:1,fleecross:2,curloc:"pre",legal:10}},
 {k:"idpbrief",label:"Fled abroad briefly, came back",a:{frcfl:1,fleeloc:1,locliv:1,fleecross:1,mnths12:1,apply:2,curloc:"other",legal:10}},
 {k:"rep",label:"Repatriated refugee",a:{frcfl:1,fleeloc:1,locliv:1,fleecross:1,mnths12:2,apply:1,outcome:1,curloc:"pre",legal:10}},
 {k:"retmig",label:"Citizen back after years abroad",a:{frcfl:1,fleeloc:1,locliv:1,fleecross:1,mnths12:2,apply:2,curloc:"other",legal:10}},
 {k:"never",label:"Never displaced",a:{frcfl:0,legal:10}},
 {k:"docnoflee",label:"Never displaced, holds a refugee document",a:{frcfl:0,legal:13}},
];
const WK_FIELDS=[
 ["frcfl","FrcFl — any valid threat?",[[1,"yes, a listed threat"],[8,"only ‘a different threat’"],[0,"none of the above"]]],
 ["frcoth","FrcOth — is that other threat valid here?",[[1,"yes (valid under this country's rules)"],[0,"no"]]],
 ["fleeloc","FleeLoc — country of the home fled",[[1,"survey country"],[2,"other country"]]],
 ["locliv","LocLiv — always lived there before?",[[1,"yes"],[2,"no"]]],
 ["citloc","CitLoc — citizen of it when fled?",[[1,"yes"],[2,"no"]]],
 ["fleecross","FleeCross — moved to another country?",[[1,"yes"],[2,"no"]]],
 ["mnths12","12Mnths — how long abroad",[[1,"under 12 months"],[2,"12 months or more"]]],
 ["apply","Apply — applied for protection?",[[1,"yes"],[2,"no"]]],
 ["intapply","IntApply — intended to apply?",[[1,"yes"],[2,"no"]]],
 ["outcome","Outcome",[[1,"granted"],[2,"denied"],[3,"still being decided"],[4,"withdrawn"]]],
 ["legal","Legal — main document",[[1,"no documents"],[2,"tourist visa"],[3,"student visa"],[4,"work visa"],[5,"humanitarian visa"],[6,"family visa"],[7,"other visa"],[8,"regional free-movement agreement"],[9,"permanent resident document"],[10,"passport (survey country)"],[11,"other citizenship document"],[12,"asylum applicant document"],[13,"refugee"],[14,"recognised stateless person"],[15,"complementary / subsidiary protection"],[16,"temporary protection"],[17,"enrolment document"],[18,"other"]]],
 ["curloc","Where they live now",[["post","the first place they moved to (IDPPost)"],["pre","the home they fled (IDPLoc)"],["other","somewhere else"]]],
];
let WK={preset:"none",a:{}};
// Which items get asked for this respondent, following the module's skip
// rules and the framework version - the same logic the questionnaire prints.
function walkPath(a){
 const A=itemActive, mode=fwMode(), asked=[];
 asked.push("FrcFl");
 const valid=a.frcfl===1||(a.frcfl===8&&a.frcoth===1);
 if(a.frcfl===8&&A("frcoth")) asked.push("FrcOth");
 if(A("legal")&&!valid){ asked.push("Legal"); return {asked,valid}; }
 if(!valid) return {asked,valid};
 asked.push("FleeLoc");
 if(mode==="idp"&&a.fleeloc===2) { if(A("legal")) asked.push("Legal"); return {asked,valid,end:"out of scope"}; }
 if(a.fleeloc===1&&A("idploc")) asked.push("IDPLoc");
 if(A("locliv")){ asked.push("LocLiv"); asked.push("CitLoc"); }
 // FleeCross only for a home fled inside the survey country
 const askCross=a.fleeloc===1;
 if(askCross) asked.push("FleeCross");
 if(mode==="ref"&&a.fleeloc===1&&a.fleecross===2){ if(A("legal")) asked.push("Legal"); return {asked,valid,end:"out of scope"}; }
 if(a.fleeloc===1&&a.fleecross===2&&A("idppost")) asked.push("IDPPost");
 if(askCross&&a.fleecross===1&&A("mnths12")) asked.push("12Mnths");
 // Apply: fled abroad, or crossed a border after fleeing here
 if(a.fleeloc===2||(askCross&&a.fleecross===1)){
  asked.push("Apply");
  if(mode!=="idp"){
   if(a.apply===2&&A("intapply")) asked.push("IntApply");
   if(a.apply===1) asked.push("Outcome");
  }
 }
 if(A("legal")) asked.push("Legal");
 return {asked,valid};
}
function walkAnswers(){
 const a=WK.a, p=walkPath(a), on=n=>p.asked.includes(n);
 const ans={fd_hist:(a.frcfl===1||(a.frcfl===8&&a.frcoth===1))?1:0};
 if(on("FleeLoc")) ans.fleeloc=a.fleeloc;
 if(on("LocLiv")) ans.locliv=a.locliv; if(on("CitLoc")) ans.citloc=a.citloc;
 if(on("FleeCross")) ans.fleecross=a.fleecross; if(on("12Mnths")) ans.mnths12=a.mnths12;
 if(on("Apply")) ans.apply=a.apply; if(on("IntApply")) ans.intapply=a.intapply; if(on("Outcome")) ans.outcome=a.outcome;
 if(on("Legal")) ans.legal=a.legal;
 if(a.curloc){ ans.loc_now_idppost=a.curloc==="post"?1:0; ans.loc_now_idploc=a.curloc==="pre"?1:0; }
 return {ans,path:p};
}
function walkRender(){
 const pre=document.getElementById('wkpre'), grid=document.getElementById('wkgrid'), res=document.getElementById('wkres');
 const form=document.getElementById('regform'); if(!pre) return;
 pre.innerHTML=WK_PRESETS.map(p=>`<button data-k="${p.k}" class="${WK.preset===p.k?"on":""}">${p.label}</button>`).join("");
 pre.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{
  const p=WK_PRESETS.find(x=>x.k===b.dataset.k); WK.preset=p.k; WK.a=p.a?Object.assign({},p.a):{}; walkRender(); }));
 const active=WK.preset!=="none";
 form.classList.toggle('walking',active);
 form.querySelectorAll('.modq').forEach(el=>el.classList.remove('wk-asked'));
 if(!active){ grid.innerHTML=""; res.innerHTML="Pick a profile above, or set the answers yourself, to see which questions are asked and the category that results."; return; }
 const {ans,path}=walkAnswers();
 const A=itemActive, mode=fwMode();
 const inQ={frcfl:true,frcoth:A("frcoth"),fleeloc:true,locliv:A("locliv"),citloc:A("locliv"),fleecross:true,mnths12:A("mnths12"),apply:true,intapply:A("intapply")&&mode!=="idp",outcome:mode!=="idp",legal:A("legal"),curloc:A("idploc")||A("idppost")};
 const askedKey={frcfl:"FrcFl",frcoth:"FrcOth",fleeloc:"FleeLoc",locliv:"LocLiv",citloc:"CitLoc",fleecross:"FleeCross",mnths12:"12Mnths",apply:"Apply",intapply:"IntApply",outcome:"Outcome",legal:"Legal"};
 grid.innerHTML=WK_FIELDS.filter(([k])=>inQ[k]).map(([k,lab,opts])=>{
  const asked=k==="curloc"?(ans.fleeloc===1&&path.asked.includes("FleeLoc")):path.asked.includes(askedKey[k]);
  return `<label class="${asked?"":"off"}"><span>${lab}${asked?"":" <i>(not asked)</i>"}</span><select data-k="${k}"${asked?"":" disabled"}>`+
   `<option value="">—</option>`+opts.map(([val,t])=>`<option value="${val}"${String(WK.a[k])===String(val)?" selected":""}>${t}</option>`).join("")+`</select></label>`; }).join("");
 grid.querySelectorAll('select').forEach(s=>s.addEventListener('change',()=>{
  const k=s.dataset.k, val=s.value; WK.preset="custom";
  if(val==="") delete WK.a[k]; else WK.a[k]=(k==="curloc")?val:+val;
  walkRender(); }));
 if(WK.preset==="custom"&&!pre.querySelector('[data-k="custom"]')) pre.insertAdjacentHTML('beforeend',`<button data-k="custom" class="on">Your own answers</button>`);
 const r=classify(ans);
 res.innerHTML=`<b>${esc(r.label)}</b> <span class="wkcode">fdcat = ${r.code}</span>`+
  (path.end?` &middot; ${esc(path.end)}`:"")+
  (r.note?`<div class="wkpath">${esc(r.note)}</div>`:"")+
  `<div class="wkpath">Asked: ${path.asked.join(" → ")}${r.code!==90?` &middot; rule: ${esc(condPlain(r.cond))}`:""}</div>`;
 form.querySelectorAll('.modq[data-item]').forEach(el=>{ if(path.asked.includes(el.dataset.item)) el.classList.add('wk-asked'); });
}

// ---- what the map says about this country (mapfacts.json) ----
const CAUSE_NAME={1:"armed conflict",2:"widespread violence",3:"persecution",4:"human-rights violations",5:"other violence",6:"natural disasters",7:"man-made events"};
function mapFacts(iso){ return (MF&&MF[iso])||null; }
const fmtK=n=>n>=1e6?(n/1e6).toFixed(1).replace(/\.0$/,"")+" million":n>=1e3?Math.round(n/1e3)+",000":String(n);
function causeList(o){ return Object.entries(o||{}).sort((a,b)=>b[1]-a[1]).slice(0,2).map(([c,sh])=>`${CAUSE_NAME[c]||c} ${Math.round(sh*100)}%`).join(", "); }
// The map's evidence as the opening of the instructions' Part A: why this
// questionnaire is configured the way it is for this country.
function whyHereHTML(iso){
 const v=Q[iso], f=mapFacts(iso), cu=effCust(iso), r=effReg(iso), mode=fwMode();
 if(!f) return "";
 const tot=f.idps+f.refugees;
 const recs=(v.localised||[]).slice().sort(), gaps=[1,2,3,4,5,6,7].filter(c=>!recs.includes(c));
 let h=`<h3>A0. Why the questionnaire looks like this in ${esc(v.name)}</h3>`;
 h+=`<p><b>Who is here.</b> ${fmtK(f.idps)} IDPs and ${fmtK(f.refugees)} refugees and asylum seekers hosted${f.origins&&f.origins.length?`, mostly from ${f.origins.map(esc).join(", ")}`:""}. `+
  `This questionnaire is the ${mode==="idp"?"IDP-only (IRIS)":mode==="ref"?"refugee-only (IRRS)":"combined refugee and IDP"} version${tot>0?`; ${f.idps>=10000&&f.refugees>=10000?"both populations are sizeable here":f.refugees>f.idps?"refugees are the larger population here":"IDPs are the larger population here"}`:""}.</p>`;
 if(f.idps>0||f.refugees>0) h+=`<p><b>What displaced them.</b> ${f.idps>0?`IDPs: ${causeList(f.idp_causes)||"cause not recorded"}. `:""}${f.refugees>0?`Refugees hosted, by the cause mix of their origin country: ${causeList(f.ref_causes)||"cause not recorded"}. `:""}`+
  `${recs.length?`Options ${recs.join(", ")} of the forced-to-flee question carry examples drafted from the recorded events; `:""}${gaps.length?`options ${gaps.join(", ")} use the questionnaire's generic wording because no source records that cause here — not because it is rare.`:""}</p>`;
 if(f.areas&&f.areas.length) h+=`<p><b>Where.</b> Most recorded violence is in ${f.areas.map(esc).join(", ")}; these are the example areas for IDPLoc and IDPPost and the strata to check in the sample.</p>`;
 if(r) h+=`<p><b>How claims are lodged.</b> ${r.reg==="NONE"?"No registration or protection procedure exists, so Apply is a screener only.":`Claims are registered by ${r.reg==="BOTH"?"both the Government and UNHCR":r.reg==="UNHCR"?"UNHCR":"the Government"}${r.org?` at ${esc(r.org)}`:""}${r.da||r.dr?`, producing ${esc(r.da||r.dr)}`:""}; ${r.mis?"the office wording does not work well here, so Version B (the document) is preferred":"Version A (the office) and Version B (the document) are both usable"}.`}</p>`;
 h+=`<p class="note">Sources: UNHCR population statistics, IDMC, UCDP GED, IOM DTM, help.unhcr.org/RIMAP; see the map page for the figures and the events behind each example.</p>`;
 return h;
}

// ---- checks before fielding ----
function checksList(iso){
 const v=Q[iso], r=effReg(iso), mode=fwMode(), A=itemActive, cu=effCust(iso);
 const L=[]; const add=(lvl,text)=>L.push({lvl,text});
 add("must",`<b>Placement and respondent.</b> The questions are asked about each individual, in the household roster or the individual questionnaire (paper, para. 50). Decide the administration option &mdash; member-by-member through a proxy respondent, or group-then-exceptions &mdash; and write the proxy rule into the interviewer instructions; the paper does not recommend asking every member directly unless the survey already does.`);
 const f=mapFacts(iso);
 if(f){
  if(FW.idp&&f.idps<2000&&f.refugees>=10000) add("check",`<b>Few IDPs recorded.</b> The map records ${fmtK(f.idps)} IDPs against ${fmtK(f.refugees)} refugees hosted; consider the refugee-only questionnaire, or keep the IDP items only if internal displacement matters for your reporting.`);
  if(FW.refugee&&f.refugees<2000&&f.idps>=10000) add("check",`<b>Few refugees recorded.</b> The map records ${fmtK(f.refugees)} refugees and asylum seekers against ${fmtK(f.idps)} IDPs; consider the IDP-only questionnaire, keeping Apply as the screener for repatriated refugees.`);
  const dis=(f.idp_causes||{})["6"]||0;
  if(dis>=0.5) add("check",`<b>Disaster displacement dominates</b> (${Math.round(dis*100)}% of IDPs). Make sure option 6 names the actual events (the named floods, storms or droughts) and that interviewers do not treat disaster displacement as out of scope.`);
  if(f.origins&&f.origins.length&&FW.refugee) add("note",`<b>Populations to preview.</b> Refugees here come mostly from ${f.origins.map(esc).join(", ")}; check the forced-to-flee examples with each origin's own (More options, step 3) before printing a version for a camp or settlement survey.`);
 }
 add("must",`<b>Variables the survey already carries.</b> Check the roster for country of birth, citizenship, and always-lived-here items; the module must not duplicate them${A("locliv")?", and LocLiv/CitLoc can be dropped if citizenship at the time of displacement is captured elsewhere (record which variable)":""}. Do not filter these questions on migrant status or citizenship (paper, paras 58&ndash;59).`);
 const gen=CODES.filter(c=>c!==8).filter(c=>{ const ed=edEg("eg"+c); if(ed) return false; const {data,region}=formData(); const it=codeItems(data,region,c); return !it.real; });
 if(gen.length) add("check",`<b>Forced to flee examples.</b> Options ${gen.join(", ")} have no country-specific examples (generic wording or none). Draft examples from local knowledge &mdash; click the blue &ldquo;e.g.&rdquo; to add them &mdash; and check the recorded ones for actor names that could anchor or offend.`);
 else add("note",`<b>Forced to flee examples.</b> Every option has country-specific examples; review them for actor names that could anchor or offend before printing.`);
 if(LANG!=="en") add("must",`<b>Translation.</b> The ${esc(LANGS[LANG][0])} text is an unreviewed draft. Run a proper translation and reconciliation (TRAPD or forward-and-back) using the translation template, then cognitive-test the translated version.`);
 else add("must",`<b>Survey language.</b> The questionnaire is in English. Download the translation template for the survey language; the notes in it list the terms that must not be translated literally.`);
 if(FW.refugee||mode==="idp"){
  if(!r) add("must",`<b>Apply localisation.</b> No office or document is on record for ${esc(v.name)}; draft Version A and B with the registrar (Government or UNHCR) before fielding.`);
  else if(r.reg==="NONE") add("note",`<b>Apply.</b> No registration or protection procedure exists here; confirm this is still the case and keep the item only as a screener.`);
  else{
   if(r.cf!=="HIGH") add("check",`<b>Confirm with the registrar</b> (source confidence ${esc(r.cf)}): the office &ldquo;${esc(r.org||"—")}&rdquo; and the document &ldquo;${esc(r.da||r.dr||"—")}&rdquo; are what respondents would recognise today.`);
   else add("note",`<b>Office and document names</b> are HIGH confidence (${esc(r.org||"—")}; ${esc(r.da||r.dr||"—")}); still confirm the everyday names and colours with field staff.`);
   if(r.mis) add("must",`<b>Use Version B (the document).</b> The office wording does not work well here &mdash; claims are actually lodged like this: ${esc(r.how||"")}.`);
   if(r.reg==="BOTH") add("check",`<b>Registration vs application.</b> Both the Government and UNHCR register people here; train interviewers that registering for assistance is not applying for protection, and probe what document was received.`);
   if(r.cav) add("check",`<b>History to listen for.</b> ${esc(r.cav)}`);
   const sp=SPEC[iso];
   if(!(sp&&sp.images&&sp.images.length)) add("check",`<b>Show card.</b> No specimen image of the document is on file${r.reg==="UNHCR"?" (UNHCR-issued: ask the operation for one)":""}; obtain one for the show card, or use Version B without it and describe the document.`);
   else add("note",`<b>Show card.</b> A specimen image is included in the questionnaire download; confirm it is the current design.`);
  }
 }
 if(A("frcoth")) add("must",`<b>FrcOth valid-reason list.</b> Confirm which &ldquo;other&rdquo; reasons count as valid causes of forced displacement under ${esc(v.name)}'s rules (1951 Convention only, or a broader OAU/Cartagena definition) &mdash; currently set to: ${esc(frcothNames(iso).join("; ")||"nothing")}. Change it with the tick boxes on the FrcOth item${cu.dtm&&cu.dtm.length?`; reasons displaced people here have given include ${cu.dtm.map(x=>esc(x[0])).join(", ")}`:""}.`);
 if(A("legal")) add("must",`<b>Legal options.</b> Localise the options under each header (keep the headers): the documents actually issued here${r&&(r.da||r.dr)?` &mdash; ${[r.da,r.dr].filter(Boolean).map(esc).join(", ")}`:""}${r&&r.svd&&r.svd.length?`; UNHCR issues ${r.svd.map(x=>esc(x.toLowerCase())).join(", ")}`:""} &mdash; and citizenship documents. Record the final code list with the dataset.`);
 if(A("idploc")||A("idppost")) add("must",`<b>Location coding.</b> Provide interviewers with the administrative area list at the levels you will code (province, district, locality)${cu.adm&&cu.adm.length?`; the areas most often named will include ${cu.adm.map(esc).join(", ")}`:""}, and the rule for people displaced more than once (the first home fled). The IDP sub-categories are formed by comparing these locations with the current dwelling.`);
 if(mode==="idp") add("check",`<b>IDP-only version.</b> FleeCross, 12Mnths and Apply are kept only as IRIS exclusion conditions. Decide whether Apply stays (it is the only way to exclude repatriated refugees) or is dropped to shorten the module.`);
 if(mode==="ref") add("note",`<b>Refugee-only version.</b> A respondent displaced only within ${esc(v.name)} leaves the module at FleeCross; confirm this is acceptable for your reporting.`);
 add("check",`<b>Mode.</b> Paper: no text-fills &mdash; the country name is printed. Telephone: no show card &mdash; describe the document (name, colour) instead. CAPI/KoBo: programme the soft check (home fled in another country but FleeCross = No) and the skip rules exactly as printed; use the walkthrough on this page to test the programmed form.`);
 add("must",`<b>Pretest.</b> Cognitive-test the customised questions before fielding &mdash; the protocol in the instructions download lists the quotas and the probes for what is uncertain in ${esc(v.name)}.`);
 const ed=editedRows(iso);
 if(ed.length) add("note",`<b>Your edits.</b> ${ed.length} value${ed.length===1?" was":"s were"} changed on this page (${ed.map(e=>esc(e.label)).join("; ")}); they are listed in the customisation table of every download and must be carried into the translation.`);
 return L;
}
function chkRender(){
 const p=document.getElementById('chkpanel'); if(!p||p.hidden) return;
 const L=checksList(sel.value);
 p.innerHTML=`<b>Checks before fielding in ${esc(Q[sel.value].name)}</b> &mdash; generated from what is and is not on record for this country and the questionnaire as configured. The same list, with the placement guidance and pretest protocol, opens the instructions download.<ul>`+
  L.map(x=>`<li><span class="lvl lvl-${x.lvl}">${x.lvl==="must"?"required":x.lvl==="check"?"confirm":"note"}</span>${x.text}</li>`).join("")+`</ul>`;
}

// The coordinator part of the instructions download: placement and
// administration (from the paper's "Administration of the recommended
// questions" section), the checks list, and the pretest protocol built from
// the project's cognitive-interviewing material.
function coordinatorHTML(iso){
 const v=Q[iso], r=effReg(iso), mode=fwMode(), A=itemActive;
 let h=`<h2>Part A &mdash; for the survey coordinator</h2>`;
 h+=whyHereHTML(iso);
 h+=`<h3>A1. Where the questions go, and who answers</h3>`+
  `<p><b>Individual level, always.</b> Being forcibly displaced is a characteristic of a person, not a household; households are mixed. Place the module in the household roster or in the individual questionnaire, and identify through the questionnaire even when the sample frame is a camp or a registration database &mdash; frames are heterogeneous in practice.</p>`+
  `<p><b>Three ways to administer it.</b> (1) Member by member through a proxy &mdash; the head or another knowledgeable adult answers for each member; (2) member by member, each person directly; (3) group then exceptions &mdash; the household's situation first, then whether any member differs, with follow-up only for them. Option 2 is the most accurate but rarely feasible unless the survey already interviews every member directly. Between 1 and 3 there is no evidence either is more accurate: choose by questionnaire flow &mdash; option 1 where the survey already has an extensive roster, option 3 where it is built around household-level questions. Write the proxy rule into Part B.</p>`+
  `<p><b>Reuse what the survey already asks.</b> Country of birth, citizenship and &ldquo;always lived here&rdquo; are usually in the roster; do not ask them twice${A("locliv")?", and drop LocLiv/CitLoc if citizenship at the time of displacement is captured there (note the variable in the dataset documentation)":""}. Do <i>not</i> use them as a filter: asking the module only of migrants or non-citizens misses naturalised former refugees, children born in the country of asylum, and people displaced within their own administrative area.</p>`+
  `<p><b>Age and reference period.</b> The questions cover the respondent's whole life (&ldquo;in your lifetime&rdquo;), the first home fled; children born after their parents' displacement are identified through the roster, not these questions. Apply the survey's own age rule for proxy answers about children.</p>`+
  `<p><b>Mode.</b> Paper: no text-fills, so the country name and examples are printed as in the questionnaire. Telephone: the show card cannot be used; read Version B and describe the document. CAPI: programme the skip rules and the soft check at FleeCross (a home fled in another country but no move reported), and test the form with the respondent profiles on the page.</p>`;
 if(mode==="idp") h+=`<p><b>IDP-only version.</b> FleeCross, 12Mnths and Apply are retained only as IRIS's exclusion conditions (established residence abroad; sought protection abroad); Outcome, IntApply and Legal are dropped and a home fled in another country is out of scope.</p>`;
 if(mode==="ref") h+=`<p><b>Refugee-only version.</b> The IDP location items are dropped; a respondent displaced only within ${esc(v.name)} leaves the module at FleeCross.</p>`;
 h+=`<h3>A2. Checks before fielding</h3><ul class="chk">`+checksList(iso).map(x=>`<li><b>${x.lvl==="must"?"Required":x.lvl==="check"?"Confirm":"Note"}.</b> ${x.text.replace(/<b>|<\/b>/g,"")}</li>`).join("")+`</ul>`;
 h+=`<h3>A3. Pretest protocol</h3>`+
  `<p>A short cognitive-interviewing round on the customised questions, before translation is finalised. The design follows the project's mission terms of reference.</p>`+
  `<p><b>Participants: 14 minimum.</b> Non-citizens: 6 &mdash; at least 2 asylum seekers and 2 refugees, plus 2 migrants who are neither. Citizens: 6 &mdash; at least 2 IDPs, other citizens with a displacement history (returnees, naturalised), plus 2 who have moved between regions without displacement. Secondary quotas: at least 5 men and 5 women; at least 3 in each of 18&ndash;30, 30&ndash;55, 55+; at least 3 with less than completed primary education; literacy not required; all aged 18+, informed consent, local language, reasonable adaptations.</p>`+
  `<p><b>Method.</b> Ask the question as printed, then probe: think-aloud where it comes naturally, otherwise retrospective probes &mdash; &ldquo;what does &lsquo;had to flee a home&rsquo; mean to you?&rdquo;, &ldquo;how did you arrive at that answer?&rdquo;, &ldquo;was there anything in that question you would say differently?&rdquo;. Two interviewers, one to ask and one to note; 45&ndash;60 minutes.</p>`+
  `<p><b>What to test in ${esc(v.name)}.</b></p><ul>`+
  `<li><b>FrcFl</b> &mdash; mental models of leaving home: do participants recognise pre-emptive departures and being unable to return as &ldquo;had to flee&rdquo;? Comprehension of persecution, human-rights violation, widespread violence, man-made events; whether any of the examples${(()=>{const rows=P.filter(x=>x.iso3===iso&&x.localised&&x.kind!=="generic"); return rows.length?` (${rows.slice(0,4).map(x=>esc(x.example)).join("; ")}${rows.length>4?", …":""})`:"";})()} anchor answers or cause offence; whether a valid local reason is missing from the list; and whether non-displaced participants produce false positives (eviction by a landlord, moving for work).</li>`+
  (A("frcoth")?`<li><b>FrcOth</b> &mdash; what &ldquo;other threats&rdquo; participants name in their own words, and whether interviewers can code them against the local valid/invalid list.</li>`:"")+
  `<li><b>FleeLoc</b> &mdash; can participants name the country of the first home fled; what people who fled more than once report; whether &ldquo;abroad&rdquo; and &ldquo;another country&rdquo; are understood where borders are porous or recent.</li>`+
  (A("locliv")?`<li><b>LocLiv / CitLoc</b> &mdash; whether citizenship, nationality or &ldquo;always lived&rdquo; is the clearer concept here; how people with complex histories answer.</li>`:"")+
  `<li><b>FleeCross</b> &mdash; whether short or informal crossings are reported; whether &ldquo;move to another country&rdquo; works better than &ldquo;cross a border&rdquo;.</li>`+
  ((A("idploc")||A("idppost"))?`<li><b>IDPLoc / IDPPost</b> &mdash; how much location detail participants can give, which place they name after multiple moves, and how &ldquo;where you moved first&rdquo; is understood after transit stops.</li>`:"")+
  (FW.refugee&&r&&r.reg!=="NONE"?`<li><b>Apply</b> &mdash; whether ${r.org?`&ldquo;${esc(r.org)}&rdquo;`:"the office"} is recognised as the place a claim is lodged (Version A) and whether ${r.da||r.dr?`&ldquo;${esc(r.da||r.dr)}&rdquo;`:"the document"}${r.cols&&r.cols.length?` &mdash; or its colour name${r.cols.length>1?"s":""} ${esc(r.cols.join(", "))} &mdash;`:""} is recognised (Version B); whether participants who registered for assistance say &ldquo;yes&rdquo; wrongly; whether &ldquo;apply for asylum or refugee status&rdquo; would be clearer than &ldquo;international protection&rdquo;.</li>`:"")+
  (A("legal")?`<li><b>Legal</b> &mdash; whether the localised options are named as people name their documents; whether participants will show the document.</li>`:"")+
  `</ul><p><b>Record</b> per question: comprehension problems, retrieval problems, judgement (social desirability, &ldquo;chose to leave&rdquo;), response mapping; then a one-line verdict &mdash; keep, reword, drop. Revise the customisation on the page, regenerate the questionnaire and translation template, and document the changes with the dataset.</p>`;
 return h;
}

// ---- the translation template ----
// One row per piece of text a translator needs, with the six UN languages
// side by side (unreviewed drafts, as flagged on the page), any local-language
// name scraped for this country, an empty column for the survey language, and
// a note on what must not be translated literally. Proper nouns - office and
// document names, place names - are marked "keep".
function translationRows(iso){
 const v=Q[iso], r=effReg(iso), cu=effCust(iso), A=itemActive, mode=fwMode();
 const LL=Object.keys(LANGS);
 const rows=[]; const add=(item,element,texts,note)=>{ const o={Item:item,Element:element}; LL.forEach(l=>o[LANGS[l][0]]=texts[l]||""); o["Local name (as printed on source pages)"]=texts.local||""; o["Survey language (fill in)"]=""; o["Notes"]=note||""; rows.push(o); };
 const tt=l=>T[l]||T.en, mt=l=>M[l]||M.en;
 const strip=s=>String(s).replace(/<[^>]+>/g,"").replace(/&mdash;/g,"—").replace(/&ldquo;|&rdquo;/g,'"').replace(/&lsquo;|&rsquo;/g,"'").replace(/&nbsp;/g," ").replace(/&amp;/g,"&");
 const per=f=>{ const o={}; LL.forEach(l=>{ try{ o[l]=strip(f(l)); }catch(e){ o[l]=""; } }); return o; };
 add("FrcFl","Item label",per(l=>tt(l).item));
 add("FrcFl","Ask instruction",per(l=>tt(l).ask));
 add("FrcFl","Introduction, sentence 1",per(l=>tt(l).stem1),"Keep 'had to flee a home' as compelled departure, not panic - see terminology notes.");
 add("FrcFl","Definition, sentence 2",per(l=>VER===3?tt(l).stem2:VERSION_DEFS[VER].stem2),"'A home, or land' - keep the reference to land.");
 add("FrcFl","Lead-in",per(l=>tt(l).lead),"'In your lifetime' - a concrete reference period; do not shorten to 'ever' if that translates badly.");
 add("FrcFl","Interviewer instruction",per(l=>tt(l).instr),"Not read aloud.");
 if(VER===3){
  CODES.forEach(c=>{
   add("FrcFl",`Option ${c}`,per(l=>tt(l).opts[c]),c===3?"'Persecution' is a legal term of art - translate the threshold, not everyday harassment.":c===8?"Followed by [SPECIFY].":"");
   const ed=edEg("eg"+c); const items=ed||baseItems(c);
   if(items.length){ const o=per(l=>{ if(l==="en"||ed) return items.join(", "); const {data,region}=formData(); if(region&&region.ex[String(c)]) return items.join(", "); const row=(data.form||[]).find(x=>x.code===c); return row&&row.eg_t?row.eg_t.join(", "):items.join(", "); });
    add("FrcFl",`Option ${c} - examples`,o,(ed?"Hand-edited on the page. ":"")+"Country-specific: actor and place names are proper nouns (keep), event descriptions are translated."); }
  });
  add("FrcFl","Example label",per(l=>tt(l).eg));
  add("FrcFl","'+n more' note",per(l=>tt(l).more));
  add("FrcFl","None of the above",per(l=>tt(l).none)); add("FrcFl","Exclusive-code tag",per(l=>tt(l).excl),"Not read aloud.");
 }else VERSION_DEFS[VER].buckets.forEach((b,i)=>{ const ed=edEg(`b${VER}_${i}`); add("FrcFl",`Option ${i+1} (${VERSION_DEFS[VER].label})`,{en:strip(b.label)},"English-only variant."); if(ed) add("FrcFl",`Option ${i+1} - examples`,{en:ed.join(", ")},"Hand-edited on the page."); });
 const u=l=>mt(l).ui;
 add("Module","Yes / No",per(l=>u(l).yes+" / "+u(l).no));
 add("Module","Go-to arrow",per(l=>u(l).goto),"{x} is the item name.");
 add("Module","Ask all",per(l=>u(l).ask_all));
 const modItem=(key,name,extra)=>{ const it=l=>mt(l)[key];
  add(name,"Skip rule",per(l=>it(l).skip),"Not read aloud.");
  add(name,"Question",per(l=>it(l).stem.split("{country}").join(v.name)));
  if(extra) extra(it); };
 if(A("frcoth")) modItem("frcoth","FrcOth",it=>{ add("FrcOth","Instruction",per(l=>it(l).note),"Not read aloud."); it("en").list.forEach((x,i)=>add("FrcOth",`Back-coding list ${i+1}`,per(l=>it(l).list[i][0]),"Office coding list - not read to respondents; localise valid codes.")); if(cu.dtm&&cu.dtm.length) add("FrcOth","Reasons heard here",{en:cu.dtm.map(x=>x[0]).join(", ")},"Country-specific, from IOM DTM or hand-edited."); });
 modItem("fleeloc","FleeLoc",it=>{ add("FleeLoc","Option 1",per(l=>it(l).opts[0]+" — "+v.name),"Country name: keep."); add("FleeLoc","Option 2",per(l=>it(l).opts[1])); if(cu.origins&&cu.origins.length) add("FleeLoc","Other-country examples",{en:cu.origins.join(", ")},"Country names - use the survey language's standard names."); });
 if(A("idploc")) modItem("idploc","IDPLoc",it=>{ add("IDPLoc","Instruction",per(l=>u(l).open),"Not read aloud."); if(cu.adm&&cu.adm.length) add("IDPLoc / IDPPost","Subnational examples",{en:cu.adm.join(", ")},"Place names: use official spellings in the survey language."); });
 if(A("locliv")){ modItem("locliv","LocLiv"); modItem("citloc","CitLoc"); }
 modItem("fleecross","FleeCross",it=>{ if(cu.dest&&cu.dest.length) add("FleeCross","Destination examples",{en:cu.dest.join(", ")},"Country names."); if(mode==="idp") add("FleeCross","Note (IDP version)",per(l=>u(l).note_fleecross_idp)); if(mode==="ref") add("FleeCross","Note (refugee version)",per(l=>u(l).note_fleecross_ref.split("{country}").join(v.name))); });
 if(A("idppost")) modItem("idppost","IDPPost",it=>add("IDPPost","Instruction",per(l=>it(l).note),"Not read aloud."));
 if(A("mnths12")) modItem("mnths12","12Mnths",it=>it("en").opts.forEach((x,i)=>add("12Mnths",`Option ${i+1}`,per(l=>it(l).opts[i]))));
 modItem("apply","Apply",it=>{
  add("Apply","Lead-in to the two versions",per(l=>u(l).loc_two),"Not read aloud."); add("Apply","Version A / B labels",per(l=>u(l).verA+" / "+u(l).verB),"Not read aloud.");
  if(r&&r.reg!=="NONE"){
   if(r.org) add("Apply","Version A probe",Object.assign(per(l=>it(l).probe_office.split("{name}").join(r.org)),{local:r.orgL||""}),"The office name is a proper noun: keep it, or use its official name in the survey language"+(r.alt&&r.alt.length?`; older or other names heard: ${r.alt.join("; ")}`:"")+".");
   const dn=r.da||r.dr; if(dn) add("Apply","Version B probe",Object.assign(per(l=>it(l).probe_doc.split("{name}").join(dn)),{local:(r.da?r.daL:r.drL)||""}),"The document name is a proper noun: keep it, or use its official name in the survey language"+((r.da?r.daC:r.drC)?`; everyday name: ${r.da?r.daC:r.drC}`:"")+(r.cols&&r.cols.length?`; colour names: ${r.cols.join(", ")}`:"")+".");
  }
  add("Apply","Interviewer instruction",per(l=>u(l).instr+(r&&r.mis?" "+u(l).instr_misfire:"")),"Not read aloud.");
  if(mode==="idp"){ add("Apply","Screening arrow (IDP version)",per(l=>u(l).notidp_apply)); add("Apply","Note (IDP version)",per(l=>u(l).note_apply_idp)); }
 });
 if(A("intapply")&&mode!=="idp") modItem("intapply","IntApply");
 if(mode!=="idp") modItem("outcome","Outcome",it=>it("en").opts.forEach((x,i)=>add("Outcome",`Option ${i+1}`,per(l=>it(l).opts[i]))));
 if(A("legal")) modItem("legal","Legal",it=>{ add("Legal","Instruction",per(l=>it(l).note),"Not read aloud.");
  it("en").cats.forEach(([head,opts],i)=>{ add("Legal",`Header ${i+1}`,per(l=>it(l).cats[i][0]),"Keep the headers; localise the options under them.");
   opts.forEach((o,j)=>{ let note=""; if(i===4&&j===0&&r&&r.da) note=`Here: ${r.da}${r.daL?` / ${r.daL}`:""}`; if(i===4&&j===1&&r&&r.dr) note=`Here: ${r.dr}${r.drL?` / ${r.drL}`:""}`; add("Legal",`Option ${i+1}.${j+1}`,per(l=>it(l).cats[i][1][j].split("{country}").join(v.name)),note); }); });
  if(r&&r.svd&&r.svd.length) add("Legal","UNHCR-issued types here",{en:r.svd.join(", ")},"From UNHCR's registration survey."); });
 return rows;
}
const TERMINOLOGY=[
 ["had to flee a home","Compelled departure - leaving because of a threat - not fleeing in panic. Five of the UN-language drafts use a duress construction for this reason. A verb that means 'run away in fear' makes people who left deliberately answer no."],
 ["a home, or land","Keep 'or land': for many rural respondents the land is the home."],
 ["in your lifetime","A concrete reference period; 'ever' translated badly in earlier testing."],
 ["persecution","A legal term of art (the refugee definition). In everyday registers it reads as ordinary harassment - a different threshold. Prefer the legal term with the examples, and test it."],
 ["widespread violence / generalised violence","Violence affecting an area or population, not a personal dispute."],
 ["man-made events","Evictions for infrastructure, pollution and industrial events - not 'man-made disaster' in the sense of war."],
 ["move to another country","Preferred to 'cross an international border': borders can be porous or unmarked and respondents may think of checkpoints."],
 ["apply for international protection","Poorly understood on its own; the localised example (office or document) carries the meaning. Do not translate the office or document name - use its official local name."],
 ["register / registered","Registering for assistance is not applying for protection. Keep the distinction in the survey language."],
 ["refugee status granted","The formal decision, not holding a card."],
 ["main document that allows you to stay","The document giving the right to stay - not a ration card, appointment slip or enrolment token."],
 ["Office and document names, place names, actor names","Proper nouns: keep them, or use the official name in the survey language. Never translate an acronym."],
 ["Text in capitals or brackets","Interviewer instructions - translated for the interviewer, never read aloud."],
];
function buildTranslationWorkbook(iso){
 const v=Q[iso], rows=translationRows(iso);
 const wb=XLSX.utils.book_new();
 const ws=XLSX.utils.json_to_sheet(rows);
 ws['!cols']=[{wch:10},{wch:26},{wch:44},{wch:44},{wch:44},{wch:44},{wch:44},{wch:44},{wch:30},{wch:44},{wch:48}];
 XLSX.utils.book_append_sheet(wb,ws,"Text to translate");
 const ws2=XLSX.utils.aoa_to_sheet([["Term","How to handle it"]].concat(TERMINOLOGY));
 ws2['!cols']=[{wch:40},{wch:110}];
 XLSX.utils.book_append_sheet(wb,ws2,"Terminology");
 const langName=(LANGS[LANG]&&LANGS[LANG][0])||LANG;
 const ed=editedRows(iso);
 const about=[["Translation template",v.name],["Generated",new Date().toISOString().slice(0,10)],["Questionnaire",`${VERSION_DEFS[VER]?VERSION_DEFS[VER].label:"Long"} version, ${LEN==="showcard"?"show card":"read-aloud"} length, page language ${langName}, ${fwMode()==="idp"?"IDP-only":fwMode()==="ref"?"refugee-only":"combined"} questionnaire`],
  ["Items",CORE_ITEMS+(activeItemNames().length?", "+activeItemNames().join(", "):"")],
  ["UN-language columns","Unreviewed draft translations - a starting point for the translator, not approved text."],
  ["Your edits",ed.length?ed.map(e=>`${e.label}: ${e.value}`).join(" | "):"none"],
  ["Method","Translate the survey-language column, then reconcile (TRAPD or forward-and-back translation) and cognitive-test the result."],
  ["Set-up link",shareURL()],["Corrections",issueURL()]];
 const ws3=XLSX.utils.aoa_to_sheet(about); ws3['!cols']=[{wch:22},{wch:120}];
 XLSX.utils.book_append_sheet(wb,ws3,"About");
 return XLSX.write(wb,{bookType:"xlsx",type:"array"});
}


// =====================================================================
// XLSForm export - the module as a KoBo / ODK / SurveyCTO form.
// The routing below is the one printed on the page: FleeCross only for a
// home fled inside the survey country, Apply reached either by FleeLoc =
// other country or by FleeCross = Yes, CitLoc asked of everyone who fled.
// Every label carries the coordinator's edits and all six UN languages.
// =====================================================================
const XLS_LANGS=["en","fr","es","ar","ru","zh"];
const XLS_LANGNAME={en:"English (en)",fr:"Français (fr)",es:"Español (es)",ar:"العربية (ar)",ru:"Русский (ru)",zh:"中文 (zh)"};
// Text with the page's markup removed: an XLSForm label is plain text (with
// markdown bold, which KoBo renders).
const xt=h=>String(h==null?"":h)
  .replace(/<span class="modq-vtag">[AB]<\/span>/g,"")
  .replace(/<br\s*\/?>/gi,"\\n").replace(/<\/li>/gi,"\\n").replace(/<[^>]+>/g,"")
  .replace(/&mdash;/g,"—").replace(/&ndash;/g,"–").replace(/&nbsp;/g," ")
  .replace(/&ldquo;|&rdquo;/g,'"').replace(/&lsquo;|&rsquo;/g,"'")
  .replace(/&middot;/g,"·").replace(/&hellip;/g,"…").replace(/&amp;/g,"&")
  .replace(/&lt;/g,"<").replace(/&gt;/g,">")
  .replace(/[ \\t]+\\n/g,"\\n").replace(/\\n{3,}/g,"\\n\\n").trim();
// Per-language text for one item, as a {en:…, fr:…} object the row builder
// turns into label:: columns.
const perLang=f=>{const o={}; XLS_LANGS.forEach(l=>{ try{ o[l]=xt(f(M[l]||M.en,l)); }catch(e){ o[l]=""; } }); return o;};

function xlsFormRows(iso){
 const v=Q[iso], r=effReg(iso), cu=effCust(iso), A=itemActive, mode=fwMode();
 const C=v.name, rows=[], choices=[];
 const row=(type,name,lab,extra)=>{ const o=Object.assign({type,name},extra||{});
   if(lab) XLS_LANGS.forEach(l=>{ o["label::"+XLS_LANGNAME[l]]=lab[l]||lab.en||""; });
   rows.push(o); };
 const hint=(o,h)=>{ XLS_LANGS.forEach(l=>{ o["hint::"+XLS_LANGNAME[l]]=h[l]||h.en||""; }); return o; };
 const ch=(list,name,lab,filter)=>{ const o={list_name:list,name:String(name)};
   XLS_LANGS.forEach(l=>{ o["label::"+XLS_LANGNAME[l]]=lab[l]||lab.en||""; });
   if(filter) o.filter=filter; choices.push(o); };
 // ---- shared choice lists ----
 ch("ynr",1,perLang(m=>m.ui.yes)); ch("ynr",2,perLang(m=>m.ui.no));
 ch("ynr",99,{en:"Refuse to answer",fr:"Refus de répondre",es:"Se niega a responder",ar:"يرفض الإجابة",ru:"Отказ от ответа",zh:"拒绝回答"});
 ch("yndr",1,perLang(m=>m.ui.yes)); ch("yndr",2,perLang(m=>m.ui.no));
 ch("yndr",98,{en:"Don't know",fr:"Ne sait pas",es:"No sabe",ar:"لا يعرف",ru:"Не знаю",zh:"不知道"});
 ch("yndr",99,{en:"Refuse to answer",fr:"Refus de répondre",es:"Se niega a responder",ar:"يرفض الإجابة",ru:"Отказ от ответа",zh:"拒绝回答"});

 rows.push({type:"begin_group",name:"idq",appearance:"field-list",
   ...Object.fromEntries(XLS_LANGS.map(l=>["label::"+XLS_LANGNAME[l], l==="en"?"Identification questions":xt((M[l]||M.en).ui.ask_all)]))});

 // ---- FrcFl ----
 const stem2=VER===3?null:VERSION_DEFS[VER].stem2;
 row("note","FrcFl_intro",perLang((m,l)=>{const tt=T[l]||T.en; return tt.stem1+"\\n\\n"+(stem2||tt.stem2);}));
 const codes=VER===3?CODES:VERSION_DEFS[VER].buckets.map((b,i)=>i+1);
 const optLabel=(c)=>{ if(VER===3) return perLang((m,l)=>{const tt=T[l]||T.en; return tt.opts[c];});
   const b=VERSION_DEFS[VER].buckets[c-1]; return {en:xt(b.label)+(b.specify?" [SPECIFY]":"")}; };
 // the examples that go with each option, as a hint (they are read out)
 const optHint=(c)=>{ let items=null;
   if(VER===3){ const ed=edEg("eg"+c); items=ed||baseItems(c); }
   else { const ed=edEg(`b${VER}_${c-1}`); const b=VERSION_DEFS[VER].buckets[c-1];
          items=ed; if(!items){ const {data,region}=formData(); let acc=[];
            b.codes.forEach(code=>{ const rr=codeItems(data,region,code); if(rr.real) acc=acc.concat(rr.items); });
            items=acc.length?acc:(b.generic?[b.generic]:[]); } }
   if(!items||!items.length) return null;
   const lim=LEN==="read_out"?3:items.length;
   const txt=items.slice(0,lim).join(", ");
   return perLang((m,l)=>((T[l]||T.en).eg||"e.g.")+" "+txt); };
 if(ADMIN==="grid"){
  row("note","FrcFl_q",perLang((m,l)=>(T[l]||T.en).lead),{appearance:"field-list"});
  codes.forEach(c=>{ const o={type:"select_one ynr",name:"FrcFl_"+c,appearance:"list-nolabel",required:"yes"};
    XLS_LANGS.forEach(l=>{ o["label::"+XLS_LANGNAME[l]]=optLabel(c)[l]||optLabel(c).en; });
    const hh=optHint(c); if(hh) hint(o,hh); rows.push(o); });
  row("select_one ynr","FrcFl_none",perLang((m,l)=>(T[l]||T.en).none),{appearance:"list-nolabel",required:"yes"});
 }else{
  codes.forEach(c=>{ const lab=optLabel(c), hh=optHint(c), o={};
    XLS_LANGS.forEach(l=>{ o[l]=(lab[l]||lab.en)+(hh?"  ("+(hh[l]||hh.en)+")":""); });
    ch("frcfl",c,o); });
  ch("frcfl",99,perLang((m,l)=>(T[l]||T.en).none));
  const o={type:"select_multiple frcfl",name:"FrcFl",required:"yes",
    constraint:"not(selected(.,'99') and count-selected(.)>1)"};
  XLS_LANGS.forEach(l=>{ o["label::"+XLS_LANGNAME[l]]=xt((T[l]||T.en).lead);
    o["constraint_message::"+XLS_LANGNAME[l]]=l==="en"?"'None of the above' cannot be combined with another answer.":"";
    o["hint::"+XLS_LANGNAME[l]]=xt(ADMIN==="grid"?(M[l]||M.en).ui.instr_grid:(T[l]||T.en).instr); });
  rows.push(o);
 }
 // valid reason from FrcFl: codes 1-7 in the Long version, 1-3 in the shorter ones
 const validCodes=VER===3?[1,2,3,4,5,6,7]:codes.slice(0,-1);
 rows.push({type:"calculate",name:"FrcFl_valid",
   calculation:ADMIN==="grid"?`if(${validCodes.map(c=>"${FrcFl_"+c+"}=1").join(" or ")}, 1, 2)`
                             :`if(${validCodes.map(c=>"selected(${FrcFl},'"+c+"')").join(" or ")}, 1, 2)`});
 // ---- FrcOth ----
 const othCode=VER===3?8:codes[codes.length-1];
 if(A("frcoth")){
  const list=M.en.frcoth.list||[], valid=frcothValid(iso);
  list.forEach(([txt],i)=>ch("FrcOth",i+1,perLang(m=>(m.frcoth.list[i]||[""])[0])));
  ch("FrcOth",99,{en:"Other reason (specify)",fr:"Autre raison (préciser)",es:"Otra razón (especificar)",ar:"سبب آخر (يُحدَّد)",ru:"Другая причина (уточнить)",zh:"其他原因（请说明）"});
  row("select_multiple FrcOth","FrcOth",perLang(m=>m.frcoth.stem),
    {relevant:ADMIN==="grid"?`\${FrcFl_${othCode}}=1`:`selected(\${FrcFl},'${othCode}')`,required:"yes",
     ...Object.fromEntries(XLS_LANGS.map(l=>["hint::"+XLS_LANGNAME[l], xt((M[l]||M.en).frcoth.note)]))});
  row("text","FrcOth_specify",{en:"Please specify the reason.",fr:"Veuillez préciser la raison.",es:"Especifique la razón.",ar:"يرجى تحديد السبب.",ru:"Уточните причину.",zh:"请说明原因。"},
    {relevant:"selected(${FrcOth},'99')"});
  rows.push({type:"calculate",name:"FrcOth_valid",
    calculation:valid.length?`if(${valid.map(i=>"selected(${FrcOth},'"+(i+1)+"')").join(" or ")}, 1, 2)`:"2"});
  rows.push({type:"calculate",name:"flee_valid",calculation:"if(${FrcFl_valid}=1 or ${FrcOth_valid}=1, 1, 2)"});
 }else{
  rows.push({type:"calculate",name:"flee_valid",calculation:"${FrcFl_valid}"});
 }
 const FV="${flee_valid}=1";

 // ---- FleeLoc ----
 ch("FleeLoc",1,{en:C,fr:C,es:C,ar:C,ru:C,zh:C});
 (cu.origins||[]).forEach((o,i)=>ch("FleeLoc",10+i,{en:o,fr:o,es:o,ar:o,ru:o,zh:o}));
 ch("FleeLoc",2,perLang(m=>m.fleeloc.opts[1]));
 row("select_one FleeLoc","FleeLoc",perLang(m=>m.fleeloc.stem),{relevant:FV,required:"yes"});
 row("text","FleeLoc_specify",{en:"If other country, please specify",fr:"Si autre pays, veuillez préciser",es:"Si es otro país, especifique",ar:"إذا كان بلداً آخر، يرجى التحديد",ru:"Если другая страна, уточните",zh:"如为其他国家，请说明"},
   {relevant:"${FleeLoc}=2"});
 rows.push({type:"calculate",name:"fled_here",calculation:"if(${FleeLoc}=1, 1, 2)"});
 const HERE="${fled_here}=1";

 // ---- IDPLoc ----
 if(A("idploc")){
  row("note","IDPLoc",perLang(m=>m.idploc.stem),{relevant:`${HERE} and ${FV}`});
  ["Admin1","Admin2","Admin3"].forEach((lv,i)=>
    row("select_one_from_file "+iso.toLowerCase()+"_admin.csv","IDPLoc_"+lv,
      {en:["Province / region","District","Sub-district"][i]},{relevant:`${HERE} and ${FV}`}));
  row("text","IDPLoc_Admin4",{en:"Village or town"},{relevant:`${HERE} and ${FV}`});
 }
 // ---- LocLiv / CitLoc ----
 if(A("locliv")){
  row("select_one ynr","LocLiv",perLang(m=>m.locliv.stem.split("{country}").join(C)),{relevant:FV,required:"yes"});
  row("select_one ynr","CitLoc",perLang(m=>m.citloc.stem.split("{country}").join(C)),{relevant:FV,required:"yes"});
 }
 // ---- FleeCross ----
 row("select_one ynr","FleeCross",perLang(m=>m.fleecross.stem),{relevant:`${HERE} and ${FV}`,required:"yes"});
 if(A("idppost")){
  row("note","IDPPost",perLang(m=>m.idppost.stem),{relevant:`${HERE} and \${FleeCross}=2`});
  ["Admin1","Admin2","Admin3"].forEach((lv,i)=>
    row("select_one_from_file "+iso.toLowerCase()+"_admin.csv","IDPPost_"+lv,
      {en:["Province / region","District","Sub-district"][i]},{relevant:`${HERE} and \${FleeCross}=2`}));
  row("text","IDPPost_Admin4",{en:"Village or town"},{relevant:`${HERE} and \${FleeCross}=2`});
 }
 if(A("mnths12")){
  M.en.mnths12.opts.forEach((o,i)=>ch("_12Mnths",i+1,perLang(m=>m.mnths12.opts[i])));
  row("select_one _12Mnths","_12Mnths",perLang(m=>m.mnths12.stem),{relevant:"${FleeCross}=1",required:"yes"});
 }
 // ---- Apply ----
 const applyRel=`\${FleeLoc}!=1 or \${FleeCross}=1`;
 if(FW.refugee||mode==="idp"){
  const n=applyNames(iso,r||{});
  const ex=(r&&r.reg!=="NONE")?(r.mis||!n.office?
      (n.doc?perLang(m=>m.apply.probe_doc.split("{name}").join(n.doc)):null)
    : perLang(m=>m.apply.probe_office.split("{name}").join(n.office))):null;
  const o={type:"select_one yndr",name:"Apply",relevant:applyRel,required:"yes"};
  XLS_LANGS.forEach(l=>{ o["label::"+XLS_LANGNAME[l]]=xt((M[l]||M.en).apply.stem)+(ex?"\\n"+(ex[l]||ex.en):""); });
  rows.push(o);
  if(A("intapply")&&mode!=="idp") row("select_one yndr","IntApply",perLang(m=>m.intapply.stem),{relevant:"${Apply}=2",required:"yes"});
  if(mode!=="idp"){
   M.en.outcome.opts.forEach((x,i)=>ch("Outcome",i+1,perLang(m=>m.outcome.opts[i])));
   ch("Outcome",98,{en:"Don't know",fr:"Ne sait pas",es:"No sabe",ar:"لا يعرف",ru:"Не знаю",zh:"不知道"});
   row("select_one Outcome","Outcome",perLang(m=>m.outcome.stem),{relevant:"${Apply}=1",required:"yes"});
  }
 }
 // ---- Legal, with the paper's headers kept as a prefix on every label ----
 if(A("legal")){
  let code=0; const docFor=(ci,oi)=>ci===4?(oi===0?(r&&r.da):oi===1?(r&&r.dr):null):null;
  M.en.legal.cats.forEach((cat,ci)=>{ cat[1].forEach((opt,oi)=>{ code++;
    const extra=docFor(ci,oi);
    ch("Legal",code,perLang((m,l)=>{ const cc=m.legal.cats[ci];
      const head=xt(cc[0]).toUpperCase(), body=xt(cc[1][oi]).split("{country}").join(C);
      return head+": "+body+(extra?" — "+extra:""); }));
  }); });
  // UNHCR-issued types that are not already named on the asylum/refugee lines
  const otherCode=code, already=[r&&r.da,r&&r.dr].filter(Boolean).map(x=>String(x).toLowerCase());
  if(r&&r.svd&&r.svd.length) r.svd.filter(d=>!already.includes(String(d).toLowerCase()))
    .forEach(d=>{ code++; ch("Legal",code,{en:"PROTECTED STATUS: "+d+" (issued by UNHCR)"}); });
  row("select_one Legal","Legal",perLang(m=>m.legal.stem.split("{country}").join(C)),
    {required:"yes",...Object.fromEntries(XLS_LANGS.map(l=>["hint::"+XLS_LANGNAME[l],xt((M[l]||M.en).legal.note)]))});
  row("text","Legal_specify",{en:"Specify the other document."},{relevant:"selected(${Legal},'"+otherCode+"')"});
  // ---- document verification ----
  ch("Legal_see",1,{en:"Yes, document seen"}); ch("Legal_see",2,{en:"No, document not seen"});
  row("select_one Legal_see","Legal_see",{en:"Can I see the document?"},{});
  row("select_one ynr","Legal_pic_yn",{en:"Can I take a picture of the document?"},{relevant:"${Legal_see}=1"});
  row("image","Legal_pic",{en:"Take the picture"},{relevant:"${Legal_pic_yn}=1",parameters:"max-pixels=1024"});
  row("text","Legal_num",{en:"Record the document or registration number."},{relevant:"${Legal_see}=1 and ${Legal_pic_yn}!=1"});
 }
 rows.push({type:"end_group",name:""});
 rows.push({type:"calculate",name:"idq_seconds",calculation:"(decimal-date-time(${idq_end}) - decimal-date-time(${idq_start})) * 86400"});
 // timing brackets, placed around the group
 const gi=rows.findIndex(x=>x.type==="begin_group"&&x.name==="idq");
 rows.splice(gi,0,{type:"calculate",name:"idq_start",calculation:"once(now())"});
 const ge=rows.findIndex(x=>x.type==="end_group");
 rows.splice(ge,0,{type:"calculate",name:"idq_end",calculation:"once(now())"});
 return {rows,choices};
}

function buildXlsForm(iso){
 const v=Q[iso], {rows,choices}=xlsFormRows(iso);
 const cols=["type","name"]
   .concat(XLS_LANGS.map(l=>"label::"+XLS_LANGNAME[l]))
   .concat(XLS_LANGS.map(l=>"hint::"+XLS_LANGNAME[l]))
   .concat(["appearance","relevant","constraint"])
   .concat(["parameters"])
   .concat(XLS_LANGS.map(l=>"constraint_message::"+XLS_LANGNAME[l]))
   .concat(["calculation","required","choice_filter"]);
 const survey=rows.map(r=>{const o={}; cols.forEach(c=>o[c]=r[c]!==undefined?r[c]:""); return o;});
 const ccols=["list_name","name"].concat(XLS_LANGS.map(l=>"label::"+XLS_LANGNAME[l])).concat(["filter"]);
 const chs=choices.map(r=>{const o={}; ccols.forEach(c=>o[c]=r[c]!==undefined?r[c]:""); return o;});
 const wb=XLSX.utils.book_new();
 const ws=XLSX.utils.json_to_sheet(survey,{header:cols});
 ws['!cols']=cols.map(c=>({wch:c.startsWith("label")?46:c.startsWith("hint")?30:c==="type"?26:c==="relevant"?30:c==="calculation"?38:14}));
 XLSX.utils.book_append_sheet(wb,ws,"survey");
 const ws2=XLSX.utils.json_to_sheet(chs,{header:ccols});
 ws2['!cols']=ccols.map(c=>({wch:c.startsWith("label")?44:14}));
 XLSX.utils.book_append_sheet(wb,ws2,"choices");
 const stem=safeFileStem(v.name).toLowerCase();
 const ws3=XLSX.utils.aoa_to_sheet([
  ["form_title","form_id","version","default_language","style"],
  [`EGRISS identification questions — ${v.name}`,`idq_${stem}`,new Date().toISOString().slice(0,10).replace(/-/g,""),XLS_LANGNAME[LANG]||XLS_LANGNAME.en,"pages"]]);
 XLSX.utils.book_append_sheet(wb,ws3,"settings");
 // a read-me sheet so whoever opens the file knows what was decided
 const ed=editedRows(iso), mode=fwMode();
 const notes=[["EGRISS identification questions — XLSForm",v.name],
  ["Generated",new Date().toISOString().slice(0,10)],
  ["Questionnaire",`${VERSION_DEFS[VER]?VERSION_DEFS[VER].label:"Long"} version of the forced-to-flee question, ${ADMIN==="grid"?"read out one by one (Yes/No each)":"choose all that apply"}, ${LEN==="showcard"?"show card":"read aloud"} examples; ${mode==="idp"?"IDP-only (IRIS)":mode==="ref"?"refugee-only (IRRS)":"combined refugee and IDP"}`],
  ["Items",CORE_ITEMS+(activeItemNames().length?", "+activeItemNames().join(", "):"")],
  ["Routing","FleeCross is asked only when the home fled was in "+v.name+"; Apply is reached by FleeLoc = another country, or FleeCross = Yes; CitLoc is asked of everyone who fled. This follows the FDS as fielded rather than the 2023 paper's narrower conditions — see the derivation sheet."],
  ["frcoth_valid",A_frcothNote(iso)],
  ["Localisation",(function(){const r=effReg(iso); if(!r) return "no office or document on record"; if(r.reg==="NONE") return "no registration procedure exists"; const n=applyNames(iso,r); return `Apply names ${r.mis?"the document (Version B) because the office wording does not work well here":"the office (Version A)"}: ${r.mis?(n.doc||"—"):(n.office||"—")}`;})()],
  ["Your edits",ed.length?ed.map(e=>`${e.label}: ${e.value}`).join(" | "):"none"],
  ["Set-up link",shareURL()],
  ["Before you upload","Add your own admin choice file for the location items (a CSV named "+iso.toLowerCase()+"_admin.csv), decide whether the module repeats per household member, and check the module against the derivation sheet's rules."],
  ["Corrections",issueURL()]];
 const ws4=XLSX.utils.aoa_to_sheet(notes); ws4['!cols']=[{wch:22},{wch:130}];
 XLSX.utils.book_append_sheet(wb,ws4,"read me");
 return XLSX.write(wb,{bookType:"xlsx",type:"array"});
}
function A_frcothNote(iso){
 if(!itemActive("frcoth")) return "FrcOth is not in this questionnaire";
 const names=frcothNames(iso);
 return names.length?`1 when FrcOth is one of: ${names.join("; ")} (this country's decision, set on the page)`:"nothing is currently marked valid — set it on the FrcOth item";
}

function safeFileStem(name){
 return (name||'country').replace(/[^\w\-]+/g,'_').replace(/^_+|_+$/g,'')||'country';
}

function setDlStatus(msg,isErr){
 const el=document.getElementById('dlStatus');
 el.textContent=msg||'';
 el.classList.toggle('err',!!isErr);
}

function saveBlob(filename,blob){
 const url=URL.createObjectURL(blob);
 const a=document.createElement('a');
 a.href=url;a.download=filename;
 document.body.appendChild(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(url),4000);
}

// Rasterizes the export HTML through the browser's own text engine
// (html2canvas) rather than drawing text with jsPDF's built-in fonts —
// see the same technique/rationale in the specimen show-card tool:
// jsPDF's standard fonts only cover WinAnsi/Latin-1 (no Arabic, Korean,
// Cyrillic, or even a plain em dash), and this dataset is full of
// exactly that.
async function generatePdfBytesQ(htmlStr){
 if(!window.jspdf||!window.html2canvas) throw new Error('pdf libraries not loaded');
 const {jsPDF}=window.jspdf;
 const iframe=document.createElement('iframe');
 iframe.style.cssText='position:fixed;left:-10000px;top:0;width:760px;height:200px;border:0;';
 document.body.appendChild(iframe);
 await new Promise(resolve=>{iframe.onload=resolve;iframe.srcdoc=htmlStr;});
 const idoc=iframe.contentDocument;
 const target=idoc.body;
 if(idoc.fonts&&idoc.fonts.ready){try{await idoc.fonts.ready;}catch(e){}}
 await new Promise(r=>setTimeout(r,60));
 let canvas;
 try{
  canvas=await window.html2canvas(target,{scale:2,backgroundColor:'#ffffff',useCORS:false,logging:false});
 }finally{ iframe.remove(); }
 const pageW=595.28,pageH=841.89; // A4 in pt
 const pxPerPt=canvas.width/pageW;
 const pageHpx=Math.floor(pageH*pxPerPt);
 const doc=new jsPDF({unit:'pt',format:'a4'});
 let renderedPx=0,first=true;
 while(renderedPx<canvas.height){
  const sliceH=Math.min(pageHpx,canvas.height-renderedPx);
  const pageCanvas=document.createElement('canvas');
  pageCanvas.width=canvas.width;pageCanvas.height=sliceH;
  const ctx=pageCanvas.getContext('2d');
  ctx.fillStyle='#ffffff';ctx.fillRect(0,0,pageCanvas.width,pageCanvas.height);
  ctx.drawImage(canvas,0,renderedPx,canvas.width,sliceH,0,0,canvas.width,sliceH);
  const imgData=pageCanvas.toDataURL('image/jpeg',0.92);
  if(!first) doc.addPage();
  doc.addImage(imgData,'JPEG',0,0,pageW,sliceH/pxPerPt);
  renderedPx+=sliceH;first=false;
 }
 return doc.output('arraybuffer');
}

function wireDownload(btnId,builder,suffix,asPdf){
 document.getElementById(btnId).addEventListener('click',async()=>{
  const iso=sel.value,v=Q[iso]; if(!v) return;
  setDlStatus(asPdf?'Building the PDF…':'Building the Word document…');
  try{
   const html=builder(iso);
   const fn=safeFileStem(v.name)+suffix+(asPdf?'.pdf':'.docx');
   if(asPdf){
    const arrbuf=await generatePdfBytesQ(html);
    saveBlob(fn,new Blob([arrbuf],{type:'application/pdf'}));
   }else{
    if(!window.htmlDocx){setDlStatus('The Word-export library did not load — try again in a moment.',true);return;}
    saveBlob(fn,window.htmlDocx.asBlob(html));
   }
   setDlStatus('Downloaded '+fn);
  }catch(e){ setDlStatus(asPdf?'Couldn\u2019t build the PDF. The page\u2019s PDF library may not have loaded \u2014 reload the page and try again, or download the Word version.':'Couldn\u2019t build the Word document. The page\u2019s Word library may not have loaded \u2014 reload the page and try again, or download the PDF instead.',true); }
 });}
wireDownload('docxBtn',buildExportHTML,'_questionnaire',false);
wireDownload('pdfBtn',buildExportHTML,'_questionnaire',true);
wireDownload('insDocxBtn',buildInstructionsHTML,'_instructions',false);
wireDownload('insPdfBtn',buildInstructionsHTML,'_instructions',true);
wireDownload('derDocxBtn',buildDerivationHTML,'_derivation_sheet',false);
wireDownload('derPdfBtn',buildDerivationHTML,'_derivation_sheet',true);
document.getElementById('xlsfBtn').addEventListener('click',()=>{
 const iso=sel.value,v=Q[iso]; if(!v) return;
 if(!window.XLSX){ setDlStatus('The spreadsheet library did not load \u2014 reload the page and try again.',true); return; }
 setDlStatus('Building the XLSForm\u2026');
 try{
  const fn=safeFileStem(v.name)+'_identification_xlsform.xlsx';
  saveBlob(fn,new Blob([buildXlsForm(iso)],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}));
  setDlStatus('Downloaded '+fn+' \u2014 upload it to KoBo, ODK or SurveyCTO. Read the \u201cread me\u201d sheet first: it lists the routing, the valid-reason rule and what you still have to add.');
 }catch(e){ setDlStatus('Couldn\u2019t build the XLSForm. Reload the page and try again; if it keeps failing, use \u201cReport a correction\u201d and say which country.',true); }
});
document.getElementById('xlsBtn').addEventListener('click',()=>{
 const iso=sel.value,v=Q[iso]; if(!v) return;
 if(!window.XLSX){ setDlStatus('The spreadsheet library did not load — try again in a moment.',true); return; }
 setDlStatus('Building the translation template…');
 try{
  const fn=safeFileStem(v.name)+'_translation_template.xlsx';
  saveBlob(fn,new Blob([buildTranslationWorkbook(iso)],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}));
  setDlStatus('Downloaded '+fn);
 }catch(e){ setDlStatus('Couldn\u2019t build the translation template. Reload the page and try again; if it keeps failing, use \u201cReport a correction\u201d and say which country.',true); }
});

// Deep link from map.html's country panel ("View the full drafted question
// for X" -> questions.html?c=ISO3) -- preselects that country in place of the
// NGA/first-country default, so the two pages actually connect instead of
// each just restating what the other already showed.
// ---- the editor popover for hand edits --------------------------------------
const EP={slot:null};
function slotDefault(slot){
 const iso=sel.value, q=Q[iso]||{}, r=REG[iso]||{}, cu=q.cust||{};
 if(slot==="org") return r.org||"";
 if(slot==="da") return r.da||"";
 if(slot==="dr") return r.dr||"";
 if(["origins","dest","adm"].includes(slot)) return (cu[slot]||[]).join(", ");
 if(slot==="dtm") return (cu.dtm||[]).map(x=>x[0]).join(", ");
 let m=/^eg(\d)$/.exec(slot);
 if(m) return baseItems(+m[1]).join(", ");
 m=/^b(\d)_(\d)$/.exec(slot);
 if(m){ const def=VERSION_DEFS[+m[1]], b=def&&def.buckets[+m[2]]; if(!b) return "";
  const {data,region}=formData(); let items=[];
  b.codes.forEach(code=>{ const r2=codeItems(data,region,code); if(r2.real) items=items.concat(r2.items); });
  return items.length?items.join(", "):(b.generic||""); }
 return "";
}
function openEditor(el){
 const slot=el.dataset.slot, def=SLOTS[slot]; if(!def) return;
 EP.slot=slot;
 const pop=document.getElementById('editpop');
 document.getElementById('epLab').textContent=def.label;
 const cur=edGet(sel.value,slot), dflt=slotDefault(slot);
 document.getElementById('epText').value=cur!==undefined?cur:dflt;
 document.getElementById('epHint').textContent=def.hint+(cur!==undefined?` Database value: ${dflt||"(none)"}.`:"")+
  " Save with the box empty to leave this out of the questionnaire. Ctrl+Enter saves, Esc cancels.";
 pop.hidden=false;
 const rect=el.getBoundingClientRect();
 const left=Math.max(8,Math.min(rect.left+window.scrollX, window.scrollX+document.documentElement.clientWidth-pop.offsetWidth-16));
 pop.style.top=(rect.bottom+window.scrollY+6)+"px"; pop.style.left=left+"px";
 document.getElementById('epText').focus();
}
function closeEditor(){ document.getElementById('editpop').hidden=true; EP.slot=null; }
function rerenderAll(){ render(); renderReg(sel.value); }
document.addEventListener('click',e=>{
 const pop=document.getElementById('editpop');
 if(pop.contains(e.target)) return;
 const t=e.target.closest('[data-slot]');
 if(t){ e.preventDefault(); openEditor(t); return; }
 if(!pop.hidden) closeEditor();
});
document.getElementById('epSave').addEventListener('click',()=>{
 if(!EP.slot) return;
 const val=document.getElementById('epText').value.trim();
 // An empty save is a deliberate "show nothing": kept as an edit to "" so the
 // database value does not come back.
 EDITS[sel.value]=EDITS[sel.value]||{}; EDITS[sel.value][EP.slot]=val; edSave();
 closeEditor(); rerenderAll(); });
document.getElementById('epReset').addEventListener('click',()=>{ if(EP.slot) edSet(sel.value,EP.slot,null); closeEditor(); rerenderAll(); });
document.getElementById('epCancel').addEventListener('click',closeEditor);
document.getElementById('epText').addEventListener('keydown',e=>{
 if(e.key==="Escape") closeEditor();
 if(e.key==="Enter"&&(e.ctrlKey||e.metaKey)) document.getElementById('epSave').click(); });
// Reset is destructive: first click asks, second click within 4 s does it,
// and the status line offers Undo (the removed edits are kept in memory).
let UNDO=null;
document.getElementById('resetBtn').addEventListener('click',()=>{
 const rb=document.getElementById('resetBtn'), n=edCount(sel.value);
 if(!rb.dataset.arm){ rb.dataset.arm="1"; rb.textContent=`Reset ${n} edit${n===1?"":"s"}? Click again to confirm`;
  setTimeout(()=>{ if(rb.dataset.arm){ delete rb.dataset.arm; rb.textContent=`Reset your ${edCount(sel.value)} edit${edCount(sel.value)===1?"":"s"}`; } },4000); return; }
 delete rb.dataset.arm;
 UNDO={iso:sel.value,edits:Object.assign({},EDITS[sel.value]||{})};
 edClear(sel.value); rerenderAll();
 const el=document.getElementById('dlStatus');
 el.innerHTML=`Your ${n} edit${n===1?" was":"s were"} removed and the database values are back. <a href="#" id="undoReset">Undo</a>`; el.classList.remove('err');
 document.getElementById('undoReset').addEventListener('click',ev=>{ ev.preventDefault(); if(!UNDO) return;
  EDITS[UNDO.iso]=UNDO.edits; edSave(); UNDO=null; rerenderAll(); setDlStatus(`Your edits are back.`); });
});
document.getElementById('linkBtn').addEventListener('click',async()=>{
 const url=shareURL(); let ok=false;
 try{ await navigator.clipboard.writeText(url); ok=true; }catch(e){}
 if(!ok){ try{ const i=document.createElement('input'); i.value=url; document.body.appendChild(i); i.select(); ok=document.execCommand('copy'); i.remove(); }catch(e){} }
 setDlStatus(ok?'Link copied \u2014 it opens this country with the same version, populations, language and your edits.':'Couldn\u2019t copy automatically \u2014 the address bar holds the same link; copy it from there.'); });
document.getElementById('chkBtn').addEventListener('click',e=>{
 const p=document.getElementById('chkpanel'); p.hidden=!p.hidden; e.target.classList.toggle('on',!p.hidden);
 if(!p.hidden){ chkRender(); p.scrollIntoView({behavior:"smooth",block:"nearest"}); } });

// Deep link: map.html's country panel links to questions.html?c=ISO3, and
// the "Copy link" button produces questions.html#c=ISO3&v=…&e=… (the whole
// set-up, hand edits included). The hash wins when both are present.
const HS=hashState();
buildModPicker();
const deepC=((HS&&HS.get("c"))||new URLSearchParams(location.search).get('c')||"").toUpperCase();
sel.value = (deepC && Q[deepC]) ? deepC : (Q["NGA"] ? "NGA" : Object.keys(Q)[0]);
cpickLabel();
pickCountry();
if(HS){ applyHashAfterPick(HS); buildLangs(); buildPops(Q[sel.value]); buildModPicker(); render(); renderReg(sel.value); }
renderFooter();
</script></body></html>"""


def survey_note():
    """Extra paragraph for the notes panel, only when the UNHCR Registration
    Baseline Survey overlay is present (see protection.py's load())."""
    try:
        from protection import SURVEY
    except Exception:
        return ""
    if not SURVEY.exists():
        return ""
    return ("<b>Cross-checked against UNHCR&rsquo;s internal Registration Baseline "
            "Survey (2024/25).</b> Where the operation itself answered, the note under "
            "the module records what it said &mdash; joint, parallel or split "
            "registration, the year registration was handed over to the Government, "
            "which document types UNHCR issues &mdash; and flags the handful of "
            "countries where its answer doesn&rsquo;t match the office named here. "
            "It also adds 29 countries the public scrape never covered, with the "
            "registrar known but no office or document named yet (LOW confidence)."
            "<br><br>")


def write_page(out, rows, reg=None, spec=None, meta=None, mapfacts=None):
    reg = reg or {}
    spec = spec or {}
    meta = meta or {}
    mapfacts = mapfacts or {}
    html = (PAGE.replace("__DATA__", json.dumps(out, separators=(",", ":")))
                .replace("__PROV__", json.dumps(rows, separators=(",", ":")))
                .replace("__T__", json.dumps(T, separators=(",", ":")))
                .replace("__LANGS__", json.dumps(LANGS, separators=(",", ":")))
                .replace("__REG__", json.dumps(reg, separators=(",", ":")))
                .replace("__REGLABEL__", json.dumps(REGISTRAR_LABEL, separators=(",", ":")))
                .replace("__SPEC__", json.dumps(spec, separators=(",", ":")))
                .replace("__M__", json.dumps(MODULE_T, separators=(",", ":"), ensure_ascii=False))
                .replace("__META__", json.dumps(meta, separators=(",", ":")))
                .replace("__MF__", json.dumps(mapfacts, separators=(",", ":")))
                .replace("__SURVEYNOTE__", survey_note()))
    open(f"{OUT}/idq_localised_questions.html", "w").write(html)
    print(f"\nwrote idq_localised_questions.html "
          f"({len(html)/1e6:.2f} MB, {len(out)} countries)")


if __name__ == "__main__":
    main()

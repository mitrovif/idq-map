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
    write_page(out, rows, reg, spec)
    print("\nExample — Nigeria:")
    if "NGA" in out:
        print("   " + out["NGA"]["question"].replace("\n", "\n   "))


PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Identification questions — customised by country</title><style>
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
.dlstatus{font-size:12.5px;color:var(--m);max-width:60ch}
.regcard .dlbar{margin:0 0 14px}
.dlstatus.err{color:#d03b3b}
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
@media print{body{background:#fff}.bar,select,h1,p.lede,h2,table,.warn,.dlbar,.modpicker,.verhint{display:none}
 .form{box-shadow:none;border:0;padding:0}}
@media(max-width:700px){.form{padding:22px 18px}select{min-width:0;width:100%}}
</style>
<script src="https://cdn.jsdelivr.net/npm/html-docx-js@0.3.1/dist/html-docx.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dompurify@3.2.4/dist/purify.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/jspdf@2.5.2/dist/jspdf.umd.min.js"></script>
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
<h1>Identification questions &mdash; customised by country</h1>
<p class="lede">The forced-to-flee question and the international protection item,
rendered as they would appear on a form, with the parts the instrument allows to
vary &mdash; the examples after each &ldquo;e.g.&rdquo;, the office and document
named in the Apply item &mdash; drafted from what was recorded in that country and
shown in <span class="eg">blue</span>. <b>The questions and response options never
change.</b> Below the two customised cards sits the full questionnaire, in the
version you choose, with the same customisations carried through.</p>

<div class="bar">
  <span class="grp">Country &amp; area</span>
  <select id="pick" hidden></select>
  <div class="cpick" id="cpick">
    <button type="button" class="cpick-btn" id="cpickBtn" aria-haspopup="listbox" aria-expanded="false">
      <span id="cpickLabel">Choose a country</span><span class="cpick-caret">&#9662;</span></button>
    <div class="cpick-menu" id="cpickMenu" hidden>
      <input type="search" id="cpickSearch" placeholder="Type a country&hellip;" autocomplete="off" spellcheck="false">
      <div class="cpick-key"><span class="loc loc-hi">5&ndash;7 localised</span><span class="loc loc-mid">3&ndash;4</span>
        <span class="loc loc-lo">0&ndash;2</span><span class="spec">&#9646; specimen</span></div>
      <div class="cpick-list" id="cpickList" role="listbox"></div>
    </div>
  </div>
  <span class="lbl">Level</span>
  <select id="lvl"></select>
</div>
<div class="bar">
  <span class="grp">Which version of the question</span>
  <button class="ver on" data-v="3">Long</button>
  <button class="ver" data-v="2">Mid-length</button>
  <button class="ver" data-v="1">Shortest</button>
</div>
<p class="verhint" id="verhint" style="display:none">Shortest and Mid-length are the
other two official variants from the question-testing document — each merges some of
the Long version's options into broader categories, and Mid-length uses an alternate
definition of "forced to flee". Only drafted in English so far; pick English to use them.</p>
<div class="bar">
  <span class="grp">Format &amp; language</span>
  <button class="len on" data-l="read_out">Read aloud</button>
  <button class="len" data-l="showcard">Showcard</button>
  <span class="lbl">Language</span>
  <span id="langs"></span>
</div>

<div class="popsection" id="popsection" style="display:none">
  <p class="sectitle">Customise for a specific population</p>
  <span id="pops"></span>
  <p class="pophint">Pick one population to preview the form with THEIR own
  examples in place of the examples below — a refugee from a different origin
  isn't well served by this country's own examples.</p>
</div>

<div class="form" id="form"></div>
<div class="warn" id="warn"></div>

<!-- The Apply item as its own localisable card, same shape as the forced-to-flee
     form above: fixed stem, and only the blue example varies by country. Two
     localisation versions are shown - A names the office (the paper's version),
     B names the document (proposed after the paper), with the document's
     specimen as a show card. Hidden when the IRRS/refugee framework is switched
     off in the picker below, since Apply serves refugee identification. -->
<div class="applysec" id="applysec">
<div class="form" id="applyform"></div>
<div class="warn" id="regwarn" style="display:none"></div>
<div class="cav" id="regcav" style="display:none"></div>
</div>

<div class="regcard" id="regcard">
<h2>Full questionnaire &mdash; international protection &amp; displacement module</h2>
<p class="sub">The whole combined refugee/IDP module of the revised instrument, with the
customisations from the two cards above carried into it. A handful of items &mdash; Forced
to flee, Location of displacement, Whether ever crossed a border, Applied for protection,
Outcome &mdash; are always needed for baseline classification and always shown; everything
else is added by the populations you choose to identify.</p>
<div class="dlbar">
  <button id="docxBtn">Download questionnaire &amp; instructions (.docx)</button>
  <button id="pdfBtn" class="secondary">Download as PDF</button>
  <span class="dlstatus" id="dlStatus">The two customised cards above, the full questionnaire
  below and a summary of every customisation, in the version, language and settings shown.</span>
</div>
<div class="modpicker" id="modpicker">
 <p class="sectitle">Which populations do you need to identify?</p>
 <div class="modpresets" id="modpresets">
  <button class="preset" data-p="core">Short &mdash; core only</button>
  <button class="preset" data-p="refugee">Refugees (IRRS)</button>
  <button class="preset" data-p="idp">IDPs (IRIS)</button>
  <button class="preset on" data-p="both">Refugees and IDPs &mdash; full</button>
  <span class="modsummary" id="modsummary"></span>
 </div>
 <div id="moditems"></div>
</div>
<span class="badges" id="regbadges"></span>
<div class="regform" id="regform"></div>
<p class="pmiss" id="regmiss" style="display:none">No drafted registration example for
this country yet.</p>
<button class="help" id="regnotesbtn">Read this before using it</button>
<div class="warn" id="regnotespanel" hidden>
<b>These are drafts for review, not enumerator text.</b> The naming rule
throughout: name where the claim is <b>lodged</b>, never who adjudicates it
&mdash; eligibility panels, appeals boards and hotlines are excluded even where
they are well known, because a respondent never went near them.<br><br>
<b>The office doesn't travel everywhere.</b> In many countries the claim is
lodged online, by post, at a police station, or happens automatically with no
office a respondent would visit &mdash; those are flagged above with the actual
channel, so the wording can be adapted rather than asked as written.<br><br>
<b>Confidence is HIGH/MEDIUM/LOW per country.</b> LOW rows are almost entirely
small Pacific and Caribbean states; check MEDIUM and LOW against a country
source before fielding.<br><br>__SURVEYNOTE__
<b>Internal displacement is deliberately absent.</b> Of the major contexts
checked, only a handful have a verifiable IDP status document; most have none at
all, which is a finding about the instruments, not a gap in the search.
</div>
</div>

<h2>Where each example comes from</h2>
<table id="prov"><thead><tr><th>Option</th><th>Example</th><th>Type</th>
<th>Source</th><th>Evidence</th></tr></thead><tbody></tbody></table>

<h2>Read this before using any of it</h2>
<p class="sub" style="margin:-2px 0 8px">These are drafts for review, not
enumerator text &mdash; translations are unreviewed, actor names are
UCDP&rsquo;s not a respondent&rsquo;s, and identity groups are never named.</p>
<button class="help" id="notesbtn">Show the full notes</button>
<div class="warn" id="notespanel" hidden>
<b>These are drafts for review, not enumerator text.</b><br><br>
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
<p style="font-size:12.5px;color:var(--m);margin-top:24px">Sources: UCDP GED for
conflict, IDMC for hazards. Generated by
<code>prototype-python/build_questions.py</code>. Ctrl/Cmd-P prints the form alone.</p>
</div><script>
const Q=__DATA__, P=__PROV__, T=__T__, LANGS=__LANGS__, REG=__REG__, REGLABEL=__REGLABEL__, SPEC=__SPEC__, M=__M__;
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
function locBadge(n){ return `<span class="loc ${n>=5?"loc-hi":n>=3?"loc-mid":"loc-lo"}">${n}/7 localised</span>`; }
function specBadge(r){
 if(r.nImg) return `<span class="spec">&#9646; ${r.nImg===1?"specimen":r.nImg+" specimens"}</span>`;
 if(r.nLinks) return `<span class="spec spec-links">&#9646; reference only</span>`;
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
 lvl.innerHTML=`<option value="-1">Whole country</option>`+
  (v.adm1||[]).map((r,i)=>`<option value="${i}">${esc(r.name)} — ${r.events.toLocaleString()} events</option>`).join("");
 lvl.disabled=!(v.adm1&&v.adm1.length);
 if(ADM>=(v.adm1||[]).length)ADM=-1;
 lvl.value=String(ADM);}

// Builds the "<ol class=opts>" list for any population's own form/localised data —
// shared by the main form (region-aware) and the per-population preview blocks
// below (national form, no region — see the design note on why previews don't
// cross with the selected admin1 level).
function optsListHTML(data, lang, t, lim, region){
 let h=`<ol class="opts">`;
 CODES.forEach(c=>{
  // region examples override the national ones for the codes they cover
  let items=null, generic=false;
  if(region&&region.ex[String(c)]){
   items=region.ex[String(c)].map(e=>e.text);
  }else{
   const row=(data.form||[]).find(x=>x.code===c);
   if(row&&row.n){items=(lang==="en"?row.eg:row.eg_t);
     generic=!(data.localised||[]).includes(c);}
  }
  let eg="";
  if(items&&items.length){
   const use=items.slice(0,lim), more=items.length-use.length;
   eg=` <span class="eg ${generic?'gen':''}"><span class="lab">${esc(t.eg)}</span> `+
      `${esc(use.join(", "))}</span>`+
      (more?` <span class="more">${esc(t.more.replace("{n}",more))}</span>`:``);}
  h+=`<li><span class="box"></span><span class="num">${c}</span>`+
     `<span class="otext">${t.opts[c]}${c===8?" "+esc(t.specify):""}${eg}</span></li>`;});
 h+=`<li><span class="box"></span><span class="num">99</span>`+
    `<span class="otext">${esc(t.none)} <span class="excl">${esc(t.excl)}</span>`+
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
 let h=`<ol class="opts">`, nReal=0, nBeyond=0;
 def.buckets.forEach((b,i)=>{
  let items=[];
  b.codes.forEach(code=>{
   const r=codeItems(data, region, code);
   if(r.real) items=items.concat(r.items);
  });
  let eg="", generic=false;
  if(items.length){
   nReal++;
   const use=items.slice(0,lim), more=items.length-use.length;
   nBeyond+=Math.max(0,more);
   eg=` <span class="eg"><span class="lab">e.g.</span> ${esc(use.join(", "))}</span>`+
      (more?` <span class="more">+${more} more recorded</span>`:``);
  } else if(b.generic){
   generic=true;
   eg=` <span class="eg gen"><span class="lab">e.g.</span> ${esc(b.generic)}</span>`;
  }
  h+=`<li><span class="box"></span><span class="num">${i+1}</span>`+
     `<span class="otext">${b.label}${b.specify?" [SPECIFY]":""}${eg}</span></li>`;});
 h+=`<li><span class="box"></span><span class="num">99</span>`+
    `<span class="otext">None of the above <span class="excl">[EXCLUSIVE CODE]</span>`+
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
  const label=p.kind==="national"?`National / IDPs — ${esc(p.name)}`:
              p.kind==="refugee"?`Refugees from ${esc(p.name)}`:esc(p.name);
  return `<button class="pop${POP===i?' on':''}${p.has_data?'':' nodata'}" `+
   `data-i="${i}" data-kind="${p.kind}" `+
   `title="${p.has_data?'':'no country-specific examples available — '}${fmtN(p.n)} people">`+
   `${label} <span style="opacity:.7">(${fmtN(p.n)})</span></button>`;}).join(" ");
 wrap.querySelectorAll('.pop').forEach(b=>b.addEventListener('click',()=>{
  const i=+b.dataset.i;
  POP=(b.dataset.kind==="national"||POP===i)?null:i;
  if(POP!=null){ADM=-1;lvl.value="-1";}   // a region of the HOST doesn't apply to another population's own form
  buildPops(v); render();}));}

function render(){
 const iso=sel.value, v=Q[iso], t=T[LANG]||T.en, dir=(LANGS[LANG]||["","ltr"])[1];
 const lim=LEN==="read_out"?3:8;

 // POP picks which population's own data flips into the SAME form/warn/provenance
 // area below — the host's own view (region-aware) when POP is null, or that
 // population's own origin-country data (Q[pop.iso3]) when it's set. No source
 // means the generic wording only, rendered honestly rather than falling back to
 // the host's examples.
 const pop=(POP!=null)?(v.populations||[])[POP]:null;
 const usingPop=!!(pop&&pop.kind!=="national");
 const dataIso=usingPop&&pop.has_data&&pop.iso3&&Q[pop.iso3]?pop.iso3:null;
 const data=usingPop?(dataIso?Q[dataIso]:{form:[],localised:[]}):v;
 const region=(!usingPop&&ADM>=0)?(v.adm1||[])[ADM]:null;
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
   `<div class="instr">${esc(t.instr)}</div>`;
 const verResult=VER===3?null:versionOptsHTML(data, lim, region);
 h+=VER===3?optsListHTML(data, LANG, t, lim, region):verResult.html;
 f.innerHTML=h;

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
    `than belong in a read-aloud list — the showcard length includes them. `:``)+
  (!usingPop?((v.adm1&&v.adm1.length)?`<b>${v.adm1.length} subnational sets</b> differ from the `+
    `national one and are in the Level menu. `:`No subnational set differs enough from `+
    `the national one to be worth showing. `):``)+
  (LANG!=="en"?`<b>The ${LANGS[LANG][0]} text is an unreviewed draft translation.</b>`:``)
  ):(
  `<b>${verResult.nReal} of ${verResult.nBuckets} options carry country-specific `+
  `examples</b> once the Long version's options are merged into ${VERSION_DEFS[VER].label}'s `+
  `broader categories. ${verResult.nBuckets-verResult.nReal} use generic wording or none at all. `+
  (verResult.nBeyond?`<b>${verResult.nBeyond} more examples are recorded</b> than belong in a `+
    `read-aloud list — the showcard length includes them. `:``)+
  `<b>${VERSION_DEFS[VER].label} is drafted in English only</b> — the official variant from `+
  `the question-testing document, not yet translated.`
  );
 document.querySelector('#prov tbody').innerHTML=rows.map(r=>
  `<tr><td>${LBL[r.code_id]||r.code_id}</td><td>${esc(r.example||"—")}</td>`+
  `<td><span class="k k-${r.kind}">${r.kind}</span></td><td>${r.source||"—"}</td>`+
  `<td style="color:var(--i2)">${esc(r.evidence||"")}`+
  (r.in_read_out===false?`<div class="ro">showcard only</div>`:``)+`</td></tr>`).join("");}

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
// What the core items alone can already identify, per the Classification Table.
const CORE_IDENTIFIES=[
 "any history of forced displacement",
 "whether the first displacement was inside or outside the survey country",
 "refugees (status granted), asylum seekers (pending), failed or withdrawn applications",
 "repatriated refugees and asylum seekers",
];
// Sub-categories from the paper's Classification Table that need an item beyond
// the core, each with the condition the paper gives and the item(s) it adds.
// Ticking a sub-category is what switches its items on; the items themselves
// are never picked directly, so the questionnaire always follows from a
// population someone actually wants to identify.
const SUBCATS=[
 {key:"prospective", group:"refugee", label:"Prospective asylum seekers",
  cond:"Apply = No and IntApply = Yes", items:["intapply"]},
 {key:"nointent", group:"refugee", label:"Displaced abroad with no intention to seek asylum",
  cond:"Apply = No and IntApply = No", items:["intapply"]},
 {key:"naturalised", group:"refugee", label:"Naturalised former refugees",
  cond:"Apply = Yes, Outcome = granted, Legal = permanent residence or citizenship", items:["legal"]},
 {key:"proctype", group:"refugee", label:"Refugees by type of protection (temporary, complementary, permanent)",
  cond:"Outcome = granted, read against the Legal protected-status categories", items:["legal"]},
 {key:"protnoflee", group:"refugee", label:"Protected status without a forced-displacement history",
  cond:"FrcFl = none of the above and Legal = protected status", items:["legal"]},
 {key:"idpcit", group:"idp", label:"IDP stock with the citizenship condition asked here",
  cond:"LocLiv = Yes or CitLoc = Yes; skip if citizenship at displacement is captured elsewhere in the survey",
  items:["locliv"]},
 {key:"idpdisp", group:"idp", label:"IDPs in location of displacement",
  cond:"current location = the first location moved to (IDPPost)", items:["idppost"]},
 {key:"idpret", group:"idp", label:"IDPs in location of return",
  cond:"current location = the location fled from (IDPLoc)", items:["idploc"]},
 {key:"idpother", group:"idp", label:"IDPs in other settlement locations",
  cond:"current location is neither IDPLoc nor IDPPost", items:["idploc","idppost"]},
 {key:"retmig", group:"idp", label:"Citizens returning after 12 months or more abroad (not IDPs)",
  cond:"FleeCross = Yes, 12Mnths = 12 months or more, Apply = No", items:["mnths12"]},
 {key:"frcoth", group:"shared", label:"Other or locally-defined reasons for fleeing",
  cond:"FrcOth coded to a locally valid reason; also screens out false positives", items:["frcoth"]},
];
let SUB={}; SUBCATS.forEach(c=>SUB[c.key]=true);
let FW={idp:true, refugee:true};

function subActive(c){
 if(!SUB[c.key]) return false;
 if(c.group==="idp"&&!FW.idp) return false;
 if(c.group==="refugee"&&!FW.refugee) return false;
 return true;
}
function itemActive(key){
 return SUBCATS.some(c=>subActive(c)&&c.items.includes(key));
}
function activeItemNames(){
 return Object.keys(OPT_ITEMS).filter(itemActive).map(k=>OPT_ITEMS[k].name);
}
function setAllSubs(on){ SUBCATS.forEach(c=>SUB[c.key]=on); }
// Presets: one click sets both the frameworks and the sub-categories.
function applyPreset(p){
 if(p==="core"){ FW.idp=true; FW.refugee=true; setAllSubs(false); }
 else if(p==="refugee"){ FW.idp=false; FW.refugee=true; setAllSubs(true); }
 else if(p==="idp"){ FW.idp=true; FW.refugee=false; setAllSubs(true); }
 else { FW.idp=true; FW.refugee=true; setAllSubs(true); }
 buildModPicker(); renderReg(sel.value);
}
function currentPreset(){
 const all=SUBCATS.every(c=>SUB[c.key]), none=SUBCATS.every(c=>!SUB[c.key]);
 if(FW.idp&&FW.refugee&&none) return "core";
 if(FW.idp&&FW.refugee&&all) return "both";
 if(FW.refugee&&!FW.idp&&all) return "refugee";
 if(FW.idp&&!FW.refugee&&all) return "idp";
 return null;
}

function buildModPicker(){
 const cur=currentPreset();
 document.querySelectorAll('.preset').forEach(b=>b.classList.toggle('on',b.dataset.p===cur));
 const names=activeItemNames();
 document.getElementById('modsummary').innerHTML=
  `<b>${5+names.length} items</b>: core${names.length?" + "+names.join(", "):" only"}`;
 const card=(key,title,on,cats,coreText)=>{
  const toggle=key?`<label class="modtoggle"><input type="checkbox" class="fw-cb" data-fw="${key}" ${on?"checked":""}> ${title}</label>`
                   :`<span class="modtoggle">${title}</span>`;
  const body=key&&!on?`<p class="modoff">Not being identified. Tick to add its sub-categories.</p>`
   :(coreText||"")+(cats||[]).map(c=>
     `<label class="moditem" title="${esc(c.cond)}"><input type="checkbox" class="moditem-cb" data-k="${c.key}" ${SUB[c.key]?"checked":""}>`+
     `<span class="modlabel">${c.label}</span><span class="modadds">+${c.items.map(k=>OPT_ITEMS[k].name).join(" +")}</span></label>`).join("");
  return `<div class="modcard${key&&!on?" off":""}">${toggle}${body}</div>`;};
 const shared=SUBCATS.filter(c=>c.group==="shared");
 let h=`<div class="modgrid">`+
  card(null,"Core &mdash; always asked",true,shared,
   `<p class="modcoretext">${CORE_ITEMS}.<br>Identifies: ${CORE_IDENTIFIES.join("; ")}.</p>`)+
  card("refugee","Refugees (IRRS)",FW.refugee,SUBCATS.filter(c=>c.group==="refugee"))+
  card("idp","IDPs (IRIS)",FW.idp,SUBCATS.filter(c=>c.group==="idp"))+
  `</div><p class="modhint">Each ticked sub-category adds the question it needs (shown as +Item); hover a line for the paper&rsquo;s condition. The questionnaire below and the download follow this.</p>`;
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
function modq(name,skip,stem,body){
 return `<div class="modq"><div class="modq-name">${name}</div>`+
  (skip?`<div class="modq-skip">${skip}</div>`:"")+
  `<div class="modq-stem">${stem}</div>${body||""}</div>`;}
function optRows(opts,arrows){
 return `<div class="modq-opts">`+opts.map((o,i)=>
  `<div class="modq-opt"><span class="box"></span>${i+1}. ${o}`+
  (arrows&&arrows[i]?`<span class="modq-arrow">${arrows[i]}</span>`:"")+`</div>`).join("")+`</div>`;}
function yesno(t,arrows){ return optRows([t.ui.yes,t.ui.no],arrows); }

function itemHTML(key){
 const t=MT(), u=t.ui, goto=x=>u.goto.replace("{x}",x);
 switch(key){
  case "frcoth": return modq("FrcOth",t.frcoth.skip,t.frcoth.stem,
   `<div class="modq-note">${t.frcoth.note}</div><ul class="modq-list">`+
   t.frcoth.list.map(([txt,soft])=>`<li>${txt}${soft?` <span class="modq-softcheck">${soft}</span>`:""}</li>`).join("")+
   `</ul>`);
  case "fleeloc": return modq("FleeLoc",t.fleeloc.skip,t.fleeloc.stem,optRows(t.fleeloc.opts));
  case "idploc": return modq("IDPLoc",t.idploc.skip,t.idploc.stem,`<div class="modq-note">${u.open}</div>`);
  case "locliv": return modq("LocLiv",t.locliv.skip,t.locliv.stem,yesno(t,[null,goto("CitLoc")]))+
                        modq("CitLoc",t.citloc.skip,t.citloc.stem,yesno(t));
  case "fleecross": return modq("FleeCross",t.fleecross.skip,t.fleecross.stem,yesno(t));
  case "idppost": return modq("IDPPost",t.idppost.skip,t.idppost.stem,`<div class="modq-note">${t.idppost.note}</div>`);
  case "mnths12": return modq("12Mnths",t.mnths12.skip,t.mnths12.stem,optRows(t.mnths12.opts));
  case "intapply": return modq("IntApply",t.intapply.skip,t.intapply.stem,yesno(t));
  case "outcome": return modq("Outcome",t.outcome.skip,t.outcome.stem,optRows(t.outcome.opts));
  case "legal": return modq("Legal",t.legal.skip,t.legal.stem,
   `<div class="modq-note">${t.legal.note}</div><div class="modq-cats">`+
   t.legal.cats.map(([head,opts])=>`<div class="modq-cathead">${head}</div>`+
     opts.map(o=>`<div class="modq-catopt">${o}</div>`).join("")).join("")+`</div>`);
 }
 return "";
}

// Assembles the fixed-wording part of the chain (everything before Apply) in
// item order, honouring the sub-category picker.
function buildFrontChain(){
 let h="";
 if(itemActive("frcoth")) h+=itemHTML("frcoth");
 h+=itemHTML("fleeloc");
 if(itemActive("idploc")) h+=itemHTML("idploc");
 if(itemActive("locliv")) h+=itemHTML("locliv");
 h+=itemHTML("fleecross");
 if(itemActive("idppost")) h+=itemHTML("idppost");
 if(itemActive("mnths12")) h+=itemHTML("mnths12");
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
const probeHTML=(tpl,name)=>tpl.replace("{name}",`<span class="eg">${esc(name)}</span>`);

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
  `<span class="fask">{${t.apply.skip}}</span>`+
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
  a+=`<p class="aprobe">${probeHTML(t.apply.probe_office,n.office)}</p>`+gloss(n.officeGloss,null);
  if(v.alt&&v.alt.length) a+=`<div class="why">${u.also_seen.replace("{n}",esc(v.alt.join("; ")))}</div>`;
  if(v.ow) a+=`<div class="why">${esc(v.ow)}</div>`;
 }else a+=`<p class="pmiss">${u.noA}${v.how?` ${esc(v.how)}`:``}</p>`;
 a+=`</div>`;
 let b=`<div class="aver"><span class="avertag">${u.verB}</span>`;
 if(n.doc){
  b+=`<p class="aprobe">${probeHTML(t.apply.probe_doc,n.doc)}</p>`+gloss(n.docGloss,n.docColloq);
  if(v.da&&v.dr&&v.dr!==v.da) b+=`<div class="why">${u.on_recog.replace("{n}",esc(v.dr)+(v.drC?` (&ldquo;${esc(v.drC)}&rdquo;)`:""))}</div>`;
  if(v.dw) b+=`<div class="why">${esc(v.dw)}</div>`;
  b+=`<div class="specimens" id="regspecimens">${renderSpecimenHTML(iso,v)}</div>`;
 }else b+=`<p class="pmiss">${u.noB}${v.dw?` ${esc(v.dw)}`:``}</p>`;
 b+=`</div>`;
 const instr=`<div class="ainstr">${u.instr}${v.mis?` ${u.instr_misfire}`:``}</div>`;
 f.innerHTML=head+`<p class="lead">${u.loc_two}</p>`+a+b+opts+instr;
}

function renderReg(iso){
 const v=REG[iso], t=MT(), u=t.ui, goto=x=>u.goto.replace("{x}",x);
 const badges=document.getElementById('regbadges'), form=document.getElementById('regform'),
       warn=document.getElementById('regwarn'), cav=document.getElementById('regcav'),
       miss=document.getElementById('regmiss');
 renderApply(iso,v);
 form.setAttribute('dir',RTL()?"rtl":"ltr");
 miss.style.display="none";form.style.display="";
 const legalHTML=itemActive("legal")?itemHTML("legal"):"";
 const tail=()=>(itemActive("intapply")?itemHTML("intapply"):"")+itemHTML("outcome")+legalHTML;
 const applyOpts=yesno(t,[goto("Outcome"),itemActive("intapply")?goto("IntApply"):null]);
 if(!v){
  badges.innerHTML="";
  form.innerHTML=buildFrontChain()+modq("Apply",t.apply.skip,t.apply.stem,
   `<div class="pmiss">${u.no_example}</div>`+applyOpts)+tail();
  warn.style.display="none";cav.style.display="none";
  return;
 }
 badges.innerHTML=
  `<span class="badge b-reg">${esc(REGLABEL[v.reg]||v.reg)} registers claims</span>`+
  `<span class="badge b-cf-${v.cf}">${v.cf} confidence</span>`;
 if(v.reg==="NONE"){
  form.innerHTML=buildFrontChain()+modq("Apply",t.apply.skip,t.apply.stem,
   `<div class="pmiss">${u.none_proc}</div>`)+legalHTML;
  warn.style.display="none";cav.style.display="none";
  return;
 }
 // In the full questionnaire the Apply item carries the SAME two customised
 // examples as the card above - the selected customisation travels with the
 // questionnaire - set in the example style (italic, name in blue).
 const n=applyNames(iso,v);
 let ex="";
 if(n.office) ex+=`<div class="modq-example"><span class="modq-vtag">A</span> ${probeHTML(t.apply.probe_office,n.office)}</div>`;
 if(n.doc) ex+=`<div class="modq-example"><span class="modq-vtag">B</span> ${probeHTML(t.apply.probe_doc,n.doc)}</div>`;
 if(!ex) ex=`<div class="pmiss">${u.no_example_short}</div>`+
   (v.ow?`<div class="why">${esc(v.ow)}</div>`:"")+(v.dw?`<div class="why">${esc(v.dw)}</div>`:"");
 let h=buildFrontChain()+modq("Apply",t.apply.skip,t.apply.stem,ex+applyOpts)+tail();
 form.innerHTML=h;
 if(v.mis){warn.style.display="";
  warn.innerHTML=`<b>The Apply localisation example likely needs rewording here.</b> ${esc(v.how)}`;
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
// Same collapsed-panel pattern as map.html's "How to read this" etc.
function panelToggle(btnId,panelId,openTxt,shutTxt){
 document.getElementById(btnId).addEventListener('click',e=>{
  e.stopPropagation(); const h=document.getElementById(panelId);
  h.hidden=!h.hidden; e.target.classList.toggle('on',!h.hidden);
  e.target.textContent=h.hidden?openTxt:shutTxt;
  if(!h.hidden)h.scrollIntoView({behavior:"smooth",block:"nearest"});});}
panelToggle('notesbtn','notespanel',"Show the full notes","Hide");
panelToggle('regnotesbtn','regnotespanel',"Read this before using it","Hide");
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
 tmp.querySelectorAll('img').forEach(im=>im.remove());
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
.num{color:#8b93a8;margin-right:6pt}
.eg{color:#3b71b9}
.eg .lab{font-style:italic;color:#5a6884}
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
 const formHTML=document.getElementById('form').innerHTML;
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
 h+=`<p><small class="gen-note">Generated ${new Date().toISOString().slice(0,10)} from the EGRISS `+
  `identification-questions dataset. Translations are unreviewed drafts; a specimen document `+
  `listed above has not been visually verified &mdash; confirm before fielding.</small></p>`;
 h+=`</body></html>`;
 return h;
}

// "How this questionnaire was customised" - every choice made on the page,
// in one place at the top of the download, so whoever receives the file can
// see what was localised, which version of each item they hold, and which
// populations the item set can identify. This is the instructions half of
// "questionnaire & instructions".
function customisationHTML(iso){
 const v=Q[iso], r=REG[iso];
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
 h+=row("Length",LEN==="showcard"?"Showcard &mdash; all recorded examples":"Read aloud &mdash; up to three examples per option");
 h+=row("Language",esc(langName)+(LANG!=="en"?" (unreviewed draft translation)":""));
 h+=row("Frameworks",fw.length?fw.join(" and "):"none selected");
 h+=row("Core items, always asked",CORE_ITEMS+`. These alone identify: ${CORE_IDENTIFIES.join("; ")}.`);
 h+=row("Sub-categories selected",subs.length?`<ul>`+subs.map(c=>`<li>${c.label} <small>(${esc(c.cond)}; adds ${c.items.map(k=>OPT_ITEMS[k].name).join(" + ")})</small></li>`).join("")+`</ul>`:"none &mdash; core questionnaire only (short version)");
 h+=row("Items added beyond the core",items.length?`<ul>`+items.map(k=>`<li><b>${OPT_ITEMS[k].name}</b> &mdash; ${OPT_ITEMS[k].label}. <small>${OPT_ITEMS[k].why}</small></li>`).join("")+`</ul>`:"none");
 if(r&&r.reg!=="NONE"&&FW.refugee){
  h+=row("Apply localisation",`Version A (office): ${r.org?"<b>"+esc(r.org)+"</b>":"cannot be worded here"} &middot; `+
    `Version B (document): ${(r.da||r.dr)?"<b>"+esc(r.da||r.dr)+"</b>":"cannot be worded here"}`+
    (r.mis?` &middot; the office framing is flagged as likely to misfire in this country`:``)+
    ` &middot; source confidence ${esc(r.cf)}`);
 }else if(r&&r.reg==="NONE"){
  h+=row("Apply localisation","No registration or protection procedure exists in this country; the Apply sequence does not apply.");
 }
 h+=`</table>`;
 return h;
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

document.getElementById('docxBtn').addEventListener('click',async()=>{
 const iso=sel.value,v=Q[iso]; if(!v) return;
 setDlStatus('Building the Word document…');
 try{
  const html=buildExportHTML(iso);
  if(!window.htmlDocx){setDlStatus('The Word-export library did not load — try again in a moment.',true);return;}
  const blob=window.htmlDocx.asBlob(html);
  const fn=safeFileStem(v.name)+'_questionnaire.docx';
  saveBlob(fn,blob);
  setDlStatus('Downloaded '+fn);
 }catch(e){ setDlStatus('Could not build the Word document.',true); }
});

document.getElementById('pdfBtn').addEventListener('click',async()=>{
 const iso=sel.value,v=Q[iso]; if(!v) return;
 setDlStatus('Building the PDF…');
 try{
  const html=buildExportHTML(iso);
  const arrbuf=await generatePdfBytesQ(html);
  const fn=safeFileStem(v.name)+'_questionnaire.pdf';
  saveBlob(fn,new Blob([arrbuf],{type:'application/pdf'}));
  setDlStatus('Downloaded '+fn);
 }catch(e){ setDlStatus('Could not build the PDF.',true); }
});

// Deep link from map.html's country panel ("View the full drafted question
// for X" -> questions.html?c=ISO3) -- preselects that country in place of the
// NGA/first-country default, so the two pages actually connect instead of
// each just restating what the other already showed.
buildModPicker();
const deepC=(new URLSearchParams(location.search).get('c')||"").toUpperCase();
sel.value = (deepC && Q[deepC]) ? deepC : (Q["NGA"] ? "NGA" : Object.keys(Q)[0]);
cpickLabel();
pickCountry();
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


def write_page(out, rows, reg=None, spec=None):
    reg = reg or {}
    spec = spec or {}
    html = (PAGE.replace("__DATA__", json.dumps(out, separators=(",", ":")))
                .replace("__PROV__", json.dumps(rows, separators=(",", ":")))
                .replace("__T__", json.dumps(T, separators=(",", ":")))
                .replace("__LANGS__", json.dumps(LANGS, separators=(",", ":")))
                .replace("__REG__", json.dumps(reg, separators=(",", ":")))
                .replace("__REGLABEL__", json.dumps(REGISTRAR_LABEL, separators=(",", ":")))
                .replace("__SPEC__", json.dumps(spec, separators=(",", ":")))
                .replace("__M__", json.dumps(MODULE_T, separators=(",", ":"), ensure_ascii=False))
                .replace("__SURVEYNOTE__", survey_note()))
    open(f"{OUT}/idq_localised_questions.html", "w").write(html)
    print(f"\nwrote idq_localised_questions.html "
          f"({len(html)/1e6:.2f} MB, {len(out)} countries)")


if __name__ == "__main__":
    main()

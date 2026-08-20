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
import json
import re

import pandas as pd

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

    out, rows = {}, []
    isos = set(conflicts) | set(disasters)
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
    write_page(out, rows)
    print("\nExample — Nigeria:")
    if "NGA" in out:
        print("   " + out["NGA"]["question"].replace("\n", "\n   "))


PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Forced to flee — localised question form</title><style>
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
.bar span.lbl{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;
 color:var(--m);font-weight:680;margin-left:6px}
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
@media print{body{background:#fff}.bar,select,h1,p.lede,h2,table,.warn{display:none}
 .form{box-shadow:none;border:0;padding:0}}
@media(max-width:700px){.form{padding:22px 18px}select{min-width:0;width:100%}}
</style></head><body><div class="w">
<h1>Forced to flee &mdash; localised question form</h1>
<p class="lede">Version 3 of the item, rendered as it would appear on a form, with
the text after each &ldquo;e.g.&rdquo; drafted from what was recorded in that
country. <b>The response options never change</b> &mdash; only the examples, which
the question variants document permits localising and which the desk review found
respondents depend on.</p>

<div class="bar">
  <select id="pick"></select>
  <span class="lbl">Level</span>
  <select id="lvl"></select>
</div>
<div class="bar">
  <span class="lbl">Length</span>
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

<h2>Where each example comes from</h2>
<table id="prov"><thead><tr><th>Option</th><th>Example</th><th>Type</th>
<th>Source</th><th>Evidence</th></tr></thead><tbody></tbody></table>

<h2>Read this before using any of it</h2>
<div class="warn">
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
const Q=__DATA__, P=__PROV__, T=__T__, LANGS=__LANGS__;
const CODES=[1,2,3,4,5,6,7,8];
const LBL={1:"1. Armed conflict",2:"2. Widespread violence",3:"3. Persecution",
 4:"4. HR violations",5:"5. Other violence",6:"6. Natural disasters",
 7:"7. Man-made events",8:"8. A different threat"};
let LEN="read_out", LANG=null, ADM=-1, POP=null;   // POP: index into v.populations, or null (= national/default)
const sel=document.getElementById('pick'), lvl=document.getElementById('lvl');
function fmtN(n){
 n=+n||0;
 if(n>=1000000)return (n/1000000).toFixed(1).replace(/\.0$/,"")+"M";
 if(n>=1000)return (n/1000).toFixed(1).replace(/\.0$/,"")+"k";
 return String(n);}
Object.entries(Q).sort((a,b)=>a[1].name.localeCompare(b[1].name))
 .forEach(([k,v])=>{const o=document.createElement('option');
  o.value=k;o.textContent=`${v.name} — ${v.n_localised}/7 options localised`;
  sel.appendChild(o);});
function esc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;");}

function buildLangs(){
 document.getElementById('langs').innerHTML=Object.entries(LANGS)
  .map(([k,v])=>`<button class="lang${k===LANG?' on':''}" data-k="${k}">${v[0]}</button>`)
  .join(" ");
 document.querySelectorAll('.lang').forEach(b=>b.addEventListener('click',()=>{
  LANG=b.dataset.k; buildLangs(); render();}));}

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
 let h=banner+`<div class="fhead"><span class="fitem">${t.item}</span>`+
   `<span class="fask">${esc(t.ask)}</span>`+
   `<span class="fcountry">${esc(v.name)}${region?" · "+esc(region.name):""}`+
   `${usingPop?" · "+esc(pop.name):""}</span></div>`+
   `<p class="stem">${t.stem1}</p><p class="stem">${t.stem2}</p>`+
   `<p class="lead">${esc(t.lead)}</p>`+
   `<div class="instr">${esc(t.instr)}</div>`;
 h+=optsListHTML(data, LANG, t, lim, region);
 f.innerHTML=h;

 const provIso=usingPop?dataIso:iso;
 const rows=P.filter(r=>r.iso3===provIso);
 const miss=rows.filter(r=>r.kind==="generic"||r.kind==="none").length;
 document.getElementById('warn').innerHTML=(usingPop&&!dataIso)?
  `<b>No source data exists yet for ${esc(pop.name)} in this pipeline.</b> `+
  `All 8 options show the questionnaire's generic wording, the same as any `+
  `country this project hasn't reached.`:
  `<b>${data.n_localised} of 7 options carry country-specific examples, `+
  `${data.n_available} in total.</b> ${miss} still use the questionnaire's generic `+
  `wording or none at all. `+
  (data.n_beyond_read_out?`<b>${data.n_beyond_read_out} more examples are recorded</b> `+
    `than belong in a read-aloud list — the showcard length includes them. `:``)+
  (!usingPop?((v.adm1&&v.adm1.length)?`<b>${v.adm1.length} subnational sets</b> differ from the `+
    `national one and are in the Level menu. `:`No subnational set differs enough from `+
    `the national one to be worth showing. `):``)+
  (LANG!=="en"?`<b>The ${LANGS[LANG][0]} text is an unreviewed draft translation.</b>`:``);
 document.querySelector('#prov tbody').innerHTML=rows.map(r=>
  `<tr><td>${LBL[r.code_id]||r.code_id}</td><td>${esc(r.example||"—")}</td>`+
  `<td><span class="k k-${r.kind}">${r.kind}</span></td><td>${r.source||"—"}</td>`+
  `<td style="color:var(--i2)">${esc(r.evidence||"")}`+
  (r.in_read_out===false?`<div class="ro">showcard only</div>`:``)+`</td></tr>`).join("");}

function pickCountry(){
 const v=Q[sel.value]; LANG=v.lang||"en"; ADM=-1; POP=null;
 buildLangs(); buildLevels(v); buildPops(v); render();}
sel.addEventListener('change',pickCountry);
lvl.addEventListener('change',()=>{ADM=+lvl.value;render();});
document.querySelectorAll('.len').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.len').forEach(x=>x.classList.remove('on'));
 b.classList.add('on');LEN=b.dataset.l;render();}));
// Deep link from map.html's country panel ("View the full drafted question
// for X" -> questions.html?c=ISO3) -- preselects that country in place of the
// NGA/first-country default, so the two pages actually connect instead of
// each just restating what the other already showed.
const deepC=(new URLSearchParams(location.search).get('c')||"").toUpperCase();
sel.value = (deepC && Q[deepC]) ? deepC : (Q["NGA"] ? "NGA" : Object.keys(Q)[0]);
pickCountry();
</script></body></html>"""


def write_page(out, rows):
    html = (PAGE.replace("__DATA__", json.dumps(out, separators=(",", ":")))
                .replace("__PROV__", json.dumps(rows, separators=(",", ":")))
                .replace("__T__", json.dumps(T, separators=(",", ":")))
                .replace("__LANGS__", json.dumps(LANGS, separators=(",", ":"))))
    open(f"{OUT}/idq_localised_questions.html", "w").write(html)
    print(f"\nwrote idq_localised_questions.html "
          f"({len(html)/1e6:.2f} MB, {len(out)} countries)")


if __name__ == "__main__":
    main()

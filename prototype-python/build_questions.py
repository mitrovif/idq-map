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


def main():
    conflicts = json.load(open(f"{TIDY}/ged_conflicts.json"))
    disasters = json.load(open(f"{TIDY}/disaster_register.json"))
    regions = {r["iso_code"]: r["name"]
               for r in json.load(open(f"{TIDY}/regions.json"))}
    try:
        dtm = pd.read_parquet(f"{TIDY}/dtm_reported.parquet")
    except FileNotFoundError:
        dtm = pd.DataFrame(columns=["iso3", "code_id", "people"])

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
        )
        rows.extend(prov)

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
<title>Localised examples for the forced-to-flee question</title><style>
:root{color-scheme:light dark;--s:#fcfcfb;--p:#f9f9f7;--i:#0b0b0b;--i2:#52514e;
 --m:#898781;--g:#e1e0d9;--a:#2a78d6;--w:#fab219}
@media(prefers-color-scheme:dark){:root{--s:#1a1a19;--p:#0d0d0d;--i:#fff;
 --i2:#c3c2b7;--g:#2c2c2a;--a:#3987e5}}
*{box-sizing:border-box}
body{margin:0;background:var(--p);color:var(--i);font:15.5px/1.6 ui-sans-serif,
 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.w{max-width:900px;margin:0 auto;padding:44px 22px 80px}
h1{font-size:26px;margin:0 0 10px;letter-spacing:-.02em;font-weight:660}
p.lede{color:var(--i2);margin:0 0 18px}
.ctl{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}
.ctl button{font:inherit;font-size:13.5px;padding:8px 13px;border-radius:9px;
 border:1px solid var(--g);background:var(--s);color:var(--i);cursor:pointer}
.ctl button.on{background:var(--i);color:var(--s);border-color:var(--i)}
.ctl button em{font-style:normal;display:block;font-size:10.5px;color:var(--m);
 margin-top:1px}
.ctl button.on em{color:var(--s);opacity:.7}
select{font:inherit;font-size:15px;padding:9px 13px;border-radius:9px;
 border:1px solid var(--g);background:var(--s);color:var(--i);width:100%;max-width:420px}
.q{background:var(--s);border:1px solid var(--g);border-radius:12px;padding:20px 22px;
 margin-top:16px;white-space:pre-wrap;font-size:15.5px;line-height:1.75}
.q b{font-weight:640}
.eg{color:var(--a);font-weight:560}
.gen{color:var(--m);font-style:italic}
.warn{background:color-mix(in srgb,var(--w) 13%,transparent);
 border:1px solid color-mix(in srgb,var(--w) 42%,transparent);border-radius:10px;
 padding:13px 16px;margin-top:16px;font-size:14px;color:var(--i2)}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin-top:14px}
th,td{padding:7px 9px;border-bottom:1px solid var(--g);text-align:left;vertical-align:top}
th{color:var(--m);font-size:11px;text-transform:uppercase;letter-spacing:.04em}
h2{font-size:16px;margin:30px 0 4px;font-weight:640}
.k{font-size:10px;text-transform:uppercase;letter-spacing:.05em;padding:2px 6px;
 border-radius:4px;font-weight:700}
.k-actor{background:color-mix(in srgb,var(--a) 16%,transparent);color:var(--a)}
.k-category{background:color-mix(in srgb,#0ca30c 16%,transparent);color:#0ca30c}
.k-generic{background:transparent;color:var(--m);border:1px solid var(--g)}
.k-none{background:transparent;color:var(--m);border:1px dashed var(--g)}
.k-actor-merged{background:color-mix(in srgb,var(--a) 16%,transparent);color:var(--a)}
.ro{font-size:10px;color:var(--m)}
</style></head><body><div class="w">
<h1>Localised examples for the forced-to-flee question</h1>
<p class="lede">Version 3 of the item, with the text after each &ldquo;e.g.&rdquo;
drafted from what was actually recorded in that country. <b>The response options do
not change</b> &mdash; only the examples, which the question variants document
permits localising and which the desk review found respondents depend on.</p>
<select id="pick"></select>
<div class="ctl">
  <button class="len on" data-l="read_out">Read aloud <em>short</em></button>
  <button class="len" data-l="showcard">Showcard <em>everything recorded</em></button>
</div>
<div class="q" id="q"></div>
<div class="warn" id="warn"></div>
<h2>Where each example comes from</h2>
<table id="prov"><thead><tr><th>Option</th><th>Example</th><th>Type</th>
<th>Source</th><th>Evidence</th></tr></thead><tbody></tbody></table>
<h2>Read this before using any of it</h2>
<div class="warn">
<b>These are drafts for review, not enumerator text.</b><br><br>
<b>The names are UCDP&rsquo;s, not a respondent&rsquo;s.</b> UCDP writes
&ldquo;JAS&rdquo; where a Nigerian respondent says Boko Haram. A handful of the
best-known are translated here; the rest need someone in the country.<br><br>
<b>Naming actors risks anchoring.</b> Someone displaced by a group not named may
conclude the option does not cover them &mdash; the opposite of what an example is
for. Where the data allowed, a category phrase was preferred to a name, and each
example is tagged with which it is.<br><br>
<b>Identity groups are never named.</b> UCDP codes communal violence as, for
example, &ldquo;Christians (Nigeria) &ndash; Muslims (Nigeria)&rdquo;. Correct as
conflict coding, unusable in an instrument a government enumerator reads aloud.
Those become &ldquo;communal or intercommunal violence&rdquo;.<br><br>
<b>Options 3 and 7 stay generic almost everywhere</b> because no event source
records discrimination, persecution or development-induced displacement. That is a
finding about the data, not about those countries.
</div>
<p style="font-size:13px;color:var(--m);margin-top:26px">Sources: UCDP GED for
conflict, IDMC for hazards. Generated by
<code>prototype-python/build_questions.py</code>.</p>
</div><script>
const Q=__DATA__, P=__PROV__;
const LBL={1:"1. Armed conflict or war",2:"2. Widespread violence",
 3:"3. Discrimination or persecution",4:"4. HR violations by authorities",
 5:"5. Other threats of violence",6:"6. Natural disasters",
 7:"7. Man-made events",8:"8. A different threat"};
const sel=document.getElementById('pick');
Object.entries(Q).sort((a,b)=>a[1].name.localeCompare(b[1].name))
 .forEach(([k,v])=>{const o=document.createElement('option');
  o.value=k;o.textContent=`${v.name} — ${v.n_localised} of 7 options localised`;
  sel.appendChild(o);});
function esc(s){return s.replace(/&/g,"&amp;").replace(/</g,"&lt;");}
let LEN="read_out";
function show(iso){
 const v=Q[iso];
 document.getElementById('q').innerHTML=esc(v[LEN]||v.question)
   .replace(/e\.g\. (.+)/g,(m,p1)=>`<span class="eg">e.g. ${p1}</span>`)
   .replace(/^- /gm,"— ");
 const rows=P.filter(r=>r.iso3===iso);
 const miss=rows.filter(r=>r.kind==="generic"||r.kind==="none").length;
 document.getElementById('warn').innerHTML=
  `<b>${v.n_localised} of 7 response options have country-specific examples`+
  `, ${v.n_available} examples in total.</b> ${miss} options still carry the `+
  `generic wording or none at all — see the table. `+
  (v.n_beyond_read_out
    ? `<b>${v.n_beyond_read_out} more</b> are recorded than fit a read-aloud list; `+
      `the showcard version includes them.`
    : `Everything recorded fits the read-aloud list.`);
 document.querySelector('#prov tbody').innerHTML=rows.map(r=>
  `<tr><td>${LBL[r.code_id]||r.code_id}</td><td>${esc(r.example||"—")}</td>`+
  `<td><span class="k k-${r.kind}">${r.kind}</span></td><td>${r.source||"—"}</td>`+
  `<td style="color:var(--i2)">${esc(r.evidence||"")}`+
  (r.in_read_out===false?`<div class="ro">showcard only</div>`:``)+
  `</td></tr>`).join("");}
sel.addEventListener('change',()=>show(sel.value));
document.querySelectorAll('.len').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.len').forEach(x=>x.classList.remove('on'));
 b.classList.add('on');LEN=b.dataset.l;show(sel.value);}));
sel.value = Q["NGA"] ? "NGA" : Object.keys(Q)[0];
show(sel.value);
</script></body></html>"""


def write_page(out, rows):
    html = (PAGE.replace("__DATA__", json.dumps(out, separators=(",", ":")))
                .replace("__PROV__", json.dumps(rows, separators=(",", ":"))))
    open(f"{OUT}/idq_localised_questions.html", "w").write(html)
    print(f"\nwrote idq_localised_questions.html "
          f"({len(html)/1e6:.2f} MB, {len(out)} countries)")


if __name__ == "__main__":
    main()

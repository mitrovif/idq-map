"""
Fetch IOM DTM data with your subscription key, and save it as CSV.

WHY THIS RUNS ON YOUR MACHINE AND NOT IN THE CHAT
-------------------------------------------------
Neither the Cowork cloud sandbox nor the on-device shell can reach dtmapi.iom.int
- both are behind a proxy that refuses the connection. So the key cannot be used
from the assistant side at all, and pasting it into a conversation would only put
a credential in a transcript for no benefit. IOM says the same thing in their own
docs: "Never share your API key or commit it to version control."

This script uses the key locally and writes plain CSVs. The CSVs contain no
credential, so those are the thing to share.

HOW TO RUN
----------
    cd ~/Downloads
    python3 -m pip install --user dtmapi pandas
    DTM_KEY=your-key-here python3 fetch_dtm.py

It creates ~/Downloads/dtm_data/ with one CSV per country and level, plus a
summary of which reasons for displacement each country actually reports. Tell me
when it is done and I will pick the folder up.

WHAT WE ACTUALLY NEED FROM IT
-----------------------------
The reason-for-displacement field, not the headcounts. Every other source in this
project tells you what a monitor could observe; DTM is the only one where the
reason comes from the displaced person. Many DTM rounds record only location and
numbers - those rounds are not useful here, and the summary at the end says which
countries carry a usable reason field so we do not chase the ones that do not.
"""
import os
import sys
import traceback
from pathlib import Path

KEY = os.environ.get("DTM_KEY", "").strip()
if not KEY:
    sys.exit("DTM_KEY is not set. Run:  DTM_KEY=your-key-here python3 fetch_dtm.py")

try:
    import pandas as pd
    from dtmapi import DTMApi
except ImportError as e:
    sys.exit(f"Missing package ({e}). Run:  python3 -m pip install --user dtmapi pandas")

OUT = Path(__file__).resolve().parent / "dtm_data"
OUT.mkdir(exist_ok=True)

# The largest displacement contexts, which are also where DTM is most likely to
# record a reason rather than only a headcount.
WANT = [
    "Sudan", "Ethiopia", "Somalia", "Democratic Republic of the Congo",
    "Nigeria", "Afghanistan", "Yemen", "South Sudan", "Mali", "Burkina Faso",
    "Mozambique", "Iraq", "Haiti", "Chad", "Central African Republic",
    "Libya", "Ukraine", "Myanmar", "Bangladesh", "Niger", "Cameroon",
]

api = DTMApi(subscription_key=KEY)


def save(df, name):
    if df is None or not hasattr(df, "__len__") or len(df) == 0:
        return 0
    df.to_csv(OUT / f"{name}.csv", index=False)
    return len(df)


print(f"writing to {OUT}\n")

# ---- resolve country names against DTM's own list -------------------------
available = []
try:
    countries = api.get_all_countries()
    save(countries, "countries")
    col = next((c for c in countries.columns if "name" in c.lower()), countries.columns[0])
    names = set(countries[col].astype(str))
    for w in WANT:
        hit = next((n for n in names if n.strip().lower() == w.lower()), None)
        if hit is None:  # DTM's spelling can differ, e.g. "Congo, DR"
            hit = next((n for n in names
                        if w.split()[-1].lower() in n.lower()), None)
        if hit:
            available.append(hit)
        else:
            print(f"  not in DTM's country list, skipping: {w}")
    print(f"\n{len(available)} of {len(WANT)} target countries available\n")
except Exception:
    print("could not fetch the country list; falling back to the names as written\n")
    traceback.print_exc(limit=1)
    available = WANT

# ---- pull each country at each admin level --------------------------------
GETTERS = [("admin0", api.get_idp_admin0_data),
           ("admin1", api.get_idp_admin1_data),
           ("admin2", api.get_idp_admin2_data)]

summary = []
for country in available:
    got = {}
    for level, fn in GETTERS:
        try:
            df = fn(CountryName=country)
            n = save(df, f"idp_{level}_{country.replace(' ', '_').replace(',', '')}")
            got[level] = n
            # does this country report a REASON, which is the whole point?
            if n and level == "admin0":
                cols = [c for c in df.columns
                        if any(k in c.lower() for k in ("reason", "cause", "driver"))]
                got["reason_cols"] = cols
                if cols:
                    vals = sorted(set(df[cols[0]].dropna().astype(str)))[:12]
                    got["reasons"] = vals
        except Exception as e:
            got[level] = f"error: {str(e)[:60]}"
    summary.append((country, got))
    r = got.get("reason_cols")
    flag = "REASON FIELD" if r else "no reason field"
    print(f"  {country[:34]:<35} a0={got.get('admin0')} a1={got.get('admin1')} "
          f"a2={got.get('admin2')}   {flag}")

# ---- what we can actually use ---------------------------------------------
print("\n" + "=" * 68)
usable = [(c, g) for c, g in summary if g.get("reason_cols")]
print(f"{len(usable)} of {len(summary)} countries report a reason for displacement")
for c, g in usable:
    print(f"\n  {c}  (column: {g['reason_cols'][0]})")
    for v in g.get("reasons", [])[:12]:
        print(f"      {v}")

with open(OUT / "_summary.txt", "w") as f:
    for c, g in summary:
        f.write(f"{c}\t{g}\n")

print(f"\nfiles in {OUT}")
for p in sorted(OUT.iterdir()):
    print(f"  {p.stat().st_size/1024:8.1f} KB  {p.name}")
print("\nIf most calls errored, paste the error text back — DTM has changed this "
      "API between versions and I cannot test it from here.")

"""
Run every visualisation step, in dependency order.

Called from run_all.R via system2(), or standalone:  python3 run_all.py
Paths resolve from IDQ_ROOT, or from this file's location if that is unset.
"""
import sys, traceback
from paths import ROOT, RAW, TIDY, OUT

STEPS = [
    ("harmonize",                "tidy the source exports into one evidence table"),
    ("profile_countries",        "country cause profiles and showcard recommendations"),
    ("build_vdem_layer",         "V-Dem severity for codes 3 and 4"),
    ("disaster_register",        "named disaster events"),
    ("attribute_unknown",        "UCDP attribution of unattributed displacement"),
    ("build_ged",                "UCDP GED: named conflicts, admin1, evidence"),
    ("subnational_points",       "geocoded displacement points"),
    ("build_crosswalk_explorer", "crosswalk explorer"),
    ("build_subreason_explorer", "sub-reason taxonomy"),
    ("build_allcauses",          "all-causes map"),
    ("build_evidence_map",       "counted vs documented map"),
    ("build_population_map",     "main population map"),
]

def main():
    print(f"project root: {ROOT}")
    ok, skipped = [], []
    for mod, desc in STEPS:
        print(f"\n--- {mod}: {desc}")
        try:
            m = __import__(mod)
            if hasattr(m, "main"):
                m.main()
            ok.append(mod)
        except FileNotFoundError as e:
            print(f"    SKIPPED - missing input: {e}")
            skipped.append((mod, str(e)))
        except Exception:
            traceback.print_exc()
            skipped.append((mod, "error - see traceback"))
    print(f"\n{'='*60}\n{len(ok)} steps completed, {len(skipped)} skipped")
    for m, why in skipped:
        print(f"  {m}: {why}")
    print(f"\noutputs in {OUT}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())

"""
Project paths, resolved once.

Every script imports from here rather than hardcoding a location, so the project
runs from wherever it is unzipped. Resolution order:
  1. IDQ_ROOT environment variable, if set (this is what run_all.R passes)
  2. the parent of this file's directory (prototype-python/ sits inside the project)
"""
import os
from pathlib import Path

ROOT = Path(os.environ.get("IDQ_ROOT") or Path(__file__).resolve().parent.parent)
RAW = ROOT / "data" / "raw"
UP = RAW / "uploads"
TIDY = ROOT / "data" / "tidy"
OUT = ROOT / "outputs"
TOPO = ROOT / "data" / "world" / "countries-110m.json"

for d in (RAW, UP, TIDY, OUT, TOPO.parent):
    d.mkdir(parents=True, exist_ok=True)

# str() forms, since most of the code interpolates these into f-strings
ROOT_S, RAW_S, UP_S, TIDY_S, OUT_S, TOPO_S = (str(ROOT), str(RAW), str(UP),
                                              str(TIDY), str(OUT), str(TOPO))

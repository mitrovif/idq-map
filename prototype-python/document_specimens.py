"""
Specimen images for the registration/international-protection documents named
in protection.py -- "what it looks like", for interviewer training and
respondent show cards.

WHY THIS IS SEPARATE FROM protection.py
protection.py names the document ("Yellow Card", "Kimlik", "BRP") from a text
scrape of help.unhcr.org / rimap.unhcr.org. Neither of those sites reliably
publishes a photograph of the thing itself, and finding one is a different kind
of work -- picture research, not text extraction -- with a completely different
coverage pattern. Keeping it in its own file and its own JSON means the (much
larger) text dataset doesn't wait on the (much slower, much patchier) image one.

WHAT "PILOT" MEANS HERE
config/document_specimens.json is hand-curated, a handful of countries at a
time -- not a scrape, not a claim of completeness. Every entry's image is
hotlinked to its original publisher (gov.uk, an NGO) rather than re-hosted here:
that keeps provenance and licensing attached to the image, and it's also the
only option from a build sandbox with no general internet access to actually
fetch and re-host a copy. It also means a dead link on the publisher's end will
show as a broken-image placeholder rather than take the page down -- see the
onerror handling in build_questions.py.

A country absent from the JSON is not an error. Most of the 151 will be absent
for a long time; the front end shows an honest "no specimen found yet" note
rather than hiding the section, so the gap is visible and inviteable rather
than silent.
"""
from paths import ROOT
import json

DATA = ROOT / "config" / "document_specimens.json"


def load():
    """Per-country specimen entries, keyed by ISO3. Missing countries are the
    normal case, not a bug -- callers should treat a missing key the same as
    an explicit empty entry."""
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)["countries"]


def _selfcheck():
    countries = load()
    n_images = sum(len(v.get("images", [])) for v in countries.values())
    n_links_only = sum(1 for v in countries.values() if not v.get("images") and v.get("links"))
    print(f"{len(countries)} countries with a specimen entry")
    print(f"  {n_images} images total")
    print(f"  {n_links_only} countries with reference links only (no image)")
    for iso, v in countries.items():
        for im in v.get("images", []):
            for k in ("label", "img", "source", "source_name", "license"):
                assert im.get(k), f"{iso}: image missing {k!r}"
    print("self-check passed")
    return countries


if __name__ == "__main__":
    _selfcheck()

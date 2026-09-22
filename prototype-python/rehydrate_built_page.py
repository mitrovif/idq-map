"""Re-render a published page from an edited template WITHOUT the data pipeline.

WHY THIS EXISTS
Every page here is one Python template plus a handful of JSON blobs substituted
into it. That means the blobs can be read back out of a page that was already
published, and the page re-rendered from an edited template -- which is how the
EGRISS restyle was applied and checked without re-running the fifteen-step
pipeline. It is a tool for design and copy changes, not a substitute for a real
build: anything that changes the DATA still needs run_all.py.

USAGE
    python3 rehydrate_built_page.py <template-file> <built-page> <vals.json>
`recover` requires the built page to match the template exactly outside the
placeholders, and says so loudly if it does not. `recover_anchored` is the
fallback for a page built from a slightly older template: it locates each blob
by the text immediately around it instead.

Recover the data blobs injected into a built page, so the page can be
re-rendered from an edited template without re-running the data pipeline.

The built page is PAGE with every __PLACEHOLDER__ replaced by a JSON blob.
Walk the template's literal segments through the built HTML and capture what
sits between them.  Round-trip is checked by re-rendering with the ORIGINAL
template and comparing byte for byte."""
import re, sys, json, pathlib

def split_template(tpl):
    parts, names, pos = [], [], 0
    for m in re.finditer(r"__[A-Z_]+__", tpl):
        parts.append(tpl[pos:m.start()]); names.append(m.group(0)); pos = m.end()
    parts.append(tpl[pos:])
    return parts, names

def recover(tpl, built):
    parts, names = split_template(tpl)
    if not built.startswith(parts[0]):
        raise SystemExit("template head does not match the built page - "
                         "the page was built from a different version")
    vals, pos = {}, len(parts[0])
    for name, nxt in zip(names, parts[1:]):
        if nxt == "":
            end = len(built)
        else:
            end = built.find(nxt, pos)
            if end < 0: raise SystemExit(f"cannot locate the segment after {name}")
        v = built[pos:end]
        if name in vals and vals[name] != v:
            raise SystemExit(f"{name} appears twice with different values")
        vals[name] = v
        pos = end + len(nxt)
    if pos != len(built):
        raise SystemExit("trailing content in the built page did not match")
    return vals

def render(tpl, vals):
    for k, v in vals.items(): tpl = tpl.replace(k, v)
    return tpl

if __name__ == "__main__":
    tpl_file, built_file, out = sys.argv[1], sys.argv[2], sys.argv[3]
    tpl = pathlib.Path(tpl_file).read_text(encoding="utf8")
    built = pathlib.Path(built_file).read_text(encoding="utf8")
    vals = recover(tpl, built)
    round_trip = render(tpl, vals)
    print(f"placeholders recovered: {len(vals)}")
    for k, v in vals.items(): print(f"  {k:16s} {len(v):>10,} chars")
    print("round-trip identical:", round_trip == built)
    json.dump(vals, open(out, "w"))
    print("saved", out)


def recover_anchored(tpl, built, anchor=160):
    """Recover blobs when the built page came from a slightly different version
    of the template: instead of requiring the whole page to match, locate each
    placeholder by the literal text immediately around it. Fails loudly if an
    anchor is missing or ambiguous."""
    parts, names = split_template(tpl)
    vals, pos = {}, 0
    for i, name in enumerate(names):
        pre, post = parts[i][-anchor:], parts[i + 1][:anchor]
        if not pre or not post:
            raise SystemExit(f"{name}: no anchor text around it")
        a = built.find(pre, pos)
        if a < 0: raise SystemExit(f"{name}: leading anchor not found")
        if built.find(pre, a + 1) >= 0: raise SystemExit(f"{name}: leading anchor not unique")
        start = a + len(pre)
        b = built.find(post, start)
        if b < 0: raise SystemExit(f"{name}: trailing anchor not found")
        vals[name] = built[start:b]
        pos = b
    return vals

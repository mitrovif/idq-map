"""Sub-reason explorer: the mechanisms underneath each response option."""
from paths import ROOT_S, RAW_S, UP_S, TIDY_S, OUT_S, TOPO_S
import json, os
import pandas as pd
from subreasons import SUB, NOT_FORCED

OUT = OUT_S

def main():
    rows = []
    for code, (label, subs) in SUB.items():
        for i, (name, desc, phrase, srcs, counted) in enumerate(subs, 1):
            rows.append(dict(code=code, code_label=label, sub_id=f"{code}.{i}",
                             mechanism=name, description=desc,
                             respondent_phrasing=phrase,
                             sources="; ".join(srcs), counted=counted))
    df = pd.DataFrame(rows)
    df.to_csv(f"{OUT}/subreason_taxonomy.csv", index=False)

    stats = dict(total=len(df),
                 uncounted=int((df.counted == "no").sum()),
                 partial=int((df.counted == "partial").sum()),
                 counted=int((df.counted == "yes").sum()))
    payload = dict(sub={str(k): dict(label=v[0], items=[
        dict(n=a, d=b, p=c, s=d, c=e) for a, b, c, d, e in v[1]])
        for k, v in SUB.items()},
        notforced=[dict(n=a, d=b, p=c) for a, b, c in NOT_FORCED],
        stats=stats)
    open(f"{OUT}/idq_subreasons.html", "w").write(
        TPL.replace("__DATA__", json.dumps(payload, separators=(",", ":"))))
    print(f"wrote {len(df)} mechanisms across {len(SUB)} options")
    print(df.groupby(["code", "counted"]).size().unstack(fill_value=0).to_string())

TPL = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sub-reasons beneath the response options</title><style>
:root{color-scheme:light;--surface-1:#fcfcfb;--plane:#f9f9f7;--ink:#0b0b0b;--ink-2:#52514e;
 --muted:#898781;--grid:#e1e0d9;--c1:#2a78d6;--good:#0ca30c;--warning:#fab219;--crit:#d03b3b;}
:root[data-theme="dark"]{color-scheme:dark;--surface-1:#1a1a19;--plane:#0d0d0d;--ink:#fff;
 --ink-2:#c3c2b7;--grid:#2c2c2a;--c1:#3987e5;}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;
 --surface-1:#1a1a19;--plane:#0d0d0d;--ink:#fff;--ink-2:#c3c2b7;--grid:#2c2c2a;--c1:#3987e5;}}
*{box-sizing:border-box}
body{margin:0;background:var(--plane);color:var(--ink);
 font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1120px;margin:0 auto;padding:26px 20px 60px}
h1{font-size:23px;margin:0 0 6px;letter-spacing:-.015em;font-weight:640}
.sub{color:var(--ink-2);margin:0 0 14px;max-width:86ch;font-size:14.5px}
.stats{display:flex;gap:20px;flex-wrap:wrap;margin:14px 0}
.stat{background:var(--surface-1);border:1px solid var(--grid);border-radius:10px;padding:11px 16px}
.stat .n{font-size:23px;font-weight:660;letter-spacing:-.02em}
.stat .l{font-size:12px;color:var(--ink-2)}
.ctl{display:flex;gap:7px;flex-wrap:wrap;margin:12px 0}
button{font:inherit;font-size:13px;padding:6px 11px;border-radius:8px;border:1px solid var(--grid);
 background:var(--surface-1);color:var(--ink);cursor:pointer}
button.on{background:var(--ink);color:var(--surface-1);border-color:var(--ink)}
.opt{background:var(--surface-1);border:1px solid var(--grid);border-radius:12px;
 padding:14px 16px;margin-top:12px}
.opt h2{font-size:16px;margin:0 0 2px;font-weight:640;letter-spacing:-.01em}
.opt .cnt{font-size:12px;color:var(--muted);margin-bottom:8px}
.m{border-top:1px solid var(--grid);padding:11px 0}
.m:first-of-type{border-top:0}
.mh{display:flex;gap:8px;align-items:baseline}
.mn{font-weight:600;font-size:13.5px;flex:1}
.badge{font-size:9.5px;font-weight:700;letter-spacing:.05em;padding:2px 6px;border-radius:4px;
 text-transform:uppercase;white-space:nowrap}
.b-yes{background:color-mix(in srgb,var(--good) 16%,transparent);color:var(--good)}
.b-partial{background:color-mix(in srgb,var(--warning) 26%,transparent);color:#8a5d00}
:root[data-theme="dark"] .b-partial{color:var(--warning)}
.b-no{background:color-mix(in srgb,var(--crit) 14%,transparent);color:var(--crit)}
.md{font-size:12.5px;color:var(--ink-2);margin-top:3px}
.mp{font-size:12.5px;margin-top:6px;padding:7px 10px;background:var(--plane);
 border-left:2.5px solid var(--c1);border-radius:0 6px 6px 0;font-style:italic}
.ms{font-size:11.5px;color:var(--muted);margin-top:5px}
.note{font-size:12.5px;color:var(--ink-2);margin-top:18px;max-width:92ch}
.nf{background:var(--surface-1);border:1.5px solid var(--crit);border-radius:12px;
 padding:14px 16px;margin-top:20px}
</style></head><body><div class="wrap">
<h1>What sits underneath each response option</h1>
<p class="sub">The options classify a category of threat. What a respondent experienced is a
mechanism — a checkpoint, a bulldozer, a 72-hour ultimatum, three failed rainy seasons. The
gap between the two is where measurement error lives: a respondent who cannot find their
mechanism in an option answers "none of the above". Built from the source vocabularies, the
documented country research, and plain respondent phrasing.</p>
<div class="stats" id="stats"></div>
<div class="ctl">
 <button class="f on" data-f="all">All mechanisms</button>
 <button class="f" data-f="no">Counted by nobody</button>
 <button class="f" data-f="partial">Partially counted</button>
 <button class="f" data-f="yes">Counted</button>
 <button id="theme" style="margin-left:auto">Dark mode</button>
</div>
<div id="body"></div>
<div class="nf">
 <h2 style="font-size:15px;margin:0 0 4px;font-weight:640">Not causes of forced displacement</h2>
 <p class="md" style="margin-bottom:6px">Listed so enumerators can recognise and exclude them.
 DTM records people giving these reasons, so they will arrive in the field — and the share who
 give them is a direct estimate of false-positive risk in the instrument.</p>
 <div id="nf"></div>
</div>
<p class="note"><b>How to keep enriching this.</b> The three inputs used here are finite:
source vocabularies are already exhausted at 68 categories, the country research covers 20 of
182, and phrasing is inferred rather than observed. The only inputs that can extend it further
are <b>observed</b>: verbatim [SPECIFY] text from code 8, DTM's own open-text reason fields,
and cognitive interview transcripts. Those are the mechanisms nobody has anticipated — which
is precisely why code 8 exists and why its open text must be collected rather than discarded.</p>
</div><script>
const D=__DATA__;
const B={yes:["b-yes","Counted"],partial:["b-partial","Partial"],no:["b-no","Counted by nobody"]};
let F="all";
const S=D.stats;
document.getElementById('stats').innerHTML=[
 [S.total,"mechanisms identified"],[S.no||S.uncounted,"counted by no database anywhere"],
 [S.partial,"only partially counted"],[S.counted,"counted"]
].map(([n,l])=>`<div class="stat"><div class="n">${n}</div><div class="l">${l}</div></div>`).join('');
function render(){
 document.getElementById('body').innerHTML=Object.entries(D.sub).map(([k,v])=>{
  const items=v.items.filter(i=>F==="all"||i.c===F);
  if(!items.length)return"";
  const nc=v.items.filter(i=>i.c==="no").length;
  return `<div class="opt"><h2>${k}. ${v.label}</h2>
   <div class="cnt">${v.items.length} mechanisms · ${nc} counted by nobody</div>`+
   items.map(i=>`<div class="m"><div class="mh"><span class="mn">${i.n}</span>
     <span class="badge ${B[i.c][0]}">${B[i.c][1]}</span></div>
     <div class="md">${i.d}</div>
     ${i.p!=="-"?`<div class="mp">“${i.p}”</div>`:``}
     <div class="ms">${i.s.join(" · ")}</div></div>`).join('')+`</div>`;}).join('');
}
document.getElementById('nf').innerHTML=D.notforced.map(i=>
 `<div class="m"><div class="mn">${i.n}</div><div class="md">${i.d}</div>
  <div class="mp">“${i.p}”</div></div>`).join('');
document.querySelectorAll('.f').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.f').forEach(x=>x.classList.remove('on'));
 b.classList.add('on');F=b.dataset.f;render();}));
document.getElementById('theme').addEventListener('click',()=>{
 const c=document.documentElement.getAttribute('data-theme');
 document.documentElement.setAttribute('data-theme',c==='dark'?'light':'dark');});
render();
</script></body></html>"""

if __name__ == "__main__":
    main()

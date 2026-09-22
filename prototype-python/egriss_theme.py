"""
The EGRISS brand layer, shared by every page this project publishes.

WHY THIS FILE EXISTS
Each page used to carry its own palette, and questions.html carried a block of
!important overrides bolted on top of a warm-grey base to make it look roughly
EGRISS. That is a recolour, not a brand. This module is the single source: the
tokens come from the EGRISS design system (palette, type, spacing, radius,
shadow, motion), and the three signature primitives it names -- the teal accent
rule, the all-caps eyebrow, the key figure -- are implemented here once.

HOW A PAGE USES IT
A page template carries three placeholders, substituted when the module that
owns it is imported, before any data goes in:
    __EGRISSFONTS__  the webfont links, in <head>
    __EGRISSCSS__    tokens first, base and primitives last, inside <style>
    __EGRISSMAST__   the navy masthead band, first thing in <body>
Tokens are declared FIRST so the page's own rules can use them, and the base
layer LAST so it wins on element selectors without a single !important.

THE SHORT VARIABLE NAMES
The pages were written against --s --p --i --i2 --m --g --a --w --paper. Those
are kept and remapped onto the brand, so every existing rule is rebranded in
place rather than rewritten. New work should use the --egriss-* names.

TWO REGISTERS, NO DARK MODE
The brand has one light reading register (paper / tint) and navy grounds for
hero bands and chart panels. The old prefers-color-scheme dark block is gone:
it was never designed against the palette and produced unreadable pairings on
the navy surfaces.

THE LOGO IS THE REAL ONE
The white horizontal lockup from the EGRISS branding package, downsampled to
560px and stored as a grey+alpha PNG (the artwork is pure white, so no colour
is lost). Never redraw the mark.
"""

LOGO_WHITE = "data:image/png;base64,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"

# --- webfonts -------------------------------------------------------------
# Obvia is licensed and not redistributable, so headings render in Figtree,
# the free geometric-humanist the design system names as its fallback. Both
# stacks end in a system font so a page with no network still reads correctly.
FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    'family=Figtree:wght@500;600;700;800&'
    'family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&'
    'family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">'
)

# --- tokens, straight from the design system ------------------------------
TOKENS = """
:root{
 /* brand */
 --egriss-navy:#14234c;--egriss-deep:#072d62;--egriss-blue:#3b71b9;
 --egriss-teal:#4cc3c9;--egriss-coral:#f06667;
 /* neutrals */
 --egriss-ink:#1d2940;--egriss-muted:#5a6884;--egriss-line:#d9e2ef;
 --egriss-tint:#eef3fa;--egriss-tint-2:#dde8f5;--egriss-paper:#f7fafd;
 --egriss-border-strong:#b9c7dc;
 /* data-visualisation ramp, matching the GAIN chart outputs */
 --gain-blue-1:#cfe0f4;--gain-blue-2:#8db8e3;--gain-blue-3:#3b71b9;
 --gain-blue-4:#1f4a8f;--gain-teal:#4cc3c9;--gain-gold:#e0a93b;
 --gain-sand:#e3c3a0;--gain-na:#d7dde6;
 /* status */
 --ok:#2e9e7b;--warn:#e0a93b;--error:#f06667;
 /* type */
 --font-head:"Obvia","Figtree",system-ui,-apple-system,"Segoe UI",sans-serif;
 --font-body:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
 --font-mono:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,monospace;
 --lh-tight:1.08;--lh-snug:1.28;--lh-body:1.65;
 --ls-tight:-.02em;--ls-wide:.04em;--ls-caps:.12em;
 /* space, radius, shadow, motion */
 --space-1:.25rem;--space-2:.5rem;--space-3:.75rem;--space-4:1rem;
 --space-5:1.5rem;--space-6:2rem;--space-7:3rem;--space-8:4rem;--space-9:6rem;
 --radius-xs:3px;--radius-sm:6px;--radius-md:10px;--radius-lg:16px;--radius-pill:999px;
 --shadow-xs:0 1px 2px rgba(20,35,76,.06);
 --shadow-sm:0 1px 3px rgba(20,35,76,.08),0 1px 2px rgba(20,35,76,.06);
 --shadow-md:0 4px 14px rgba(20,35,76,.10);
 --shadow-lg:0 12px 34px rgba(20,35,76,.14);
 --focus-ring:0 0 0 3px rgba(59,113,185,.35);
 --ease:cubic-bezier(.2,0,.1,1);--dur-fast:120ms;--dur-base:200ms;
 /* The short names every existing rule on these pages is written against,
    remapped onto the brand so they rebrand in place. The old third grey
    (--m: #8b93a8) reached only 3.07:1 on white -- below AA for body text --
    and the brand names one muted, so --i2 and --m now share it. The navy
    register rebinds --eg-muted, since #5a6884 on navy is 2.4:1. */
 --s:#fff;--p:var(--egriss-paper);--i:var(--egriss-ink);--i2:var(--egriss-muted);
 --m:var(--eg-muted,#5a6884);--g:var(--egriss-line);--a:var(--egriss-blue);
 --w:var(--gain-gold);--paper:#fff;
 /* map page names */
 --surface-1:#fff;--plane:var(--egriss-paper);--ink:var(--egriss-ink);
 --ink-2:var(--egriss-muted);--muted:var(--eg-muted,#5a6884);--grid:var(--egriss-line);
 --land:var(--egriss-tint);
 color-scheme:light;
}
"""

# --- base layer and the signature primitives ------------------------------
# Loaded LAST inside the page's own <style>, so element rules win on
# specificity alone. Nothing here uses !important.
BASE = """
/* --eg-page-bg / --eg-page-ink let a page switch to the navy register without
   fighting this rule; unset, they fall back to the light one. */
body{font-family:var(--font-body);color:var(--eg-page-ink,var(--egriss-ink));
 background:var(--eg-page-bg,var(--egriss-paper));
 -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
h1,h2,h3,h4{font-family:var(--font-head);color:var(--eg-head-ink,var(--egriss-navy));
 letter-spacing:var(--ls-tight);line-height:var(--lh-snug);text-wrap:balance}
h1{line-height:var(--lh-tight)}
a{color:var(--egriss-blue);text-decoration:none}
a:hover{text-decoration:underline}
*:focus-visible{outline:2px solid var(--egriss-blue);outline-offset:2px;border-radius:var(--radius-xs)}
::selection{background:rgba(76,195,201,.32)}
code,kbd,samp,pre{font-family:var(--font-mono)}

/* ---- signature primitive 1: the teal accent rule ---- */
.eg-rule{height:3px;width:72px;border:0;border-radius:var(--radius-pill);margin:14px 0 0;
 background:linear-gradient(90deg,var(--egriss-teal),rgba(76,195,201,0))}
.eg-rule.on-light{background:linear-gradient(90deg,var(--egriss-blue),rgba(59,113,185,0))}

/* ---- signature primitive 2: the all-caps eyebrow ---- */
.eg-eyebrow{font-family:var(--font-head);font-weight:700;font-size:12px;
 letter-spacing:var(--ls-caps);text-transform:uppercase;color:var(--egriss-blue);
 display:block;margin:0 0 8px}
.eg-eyebrow.on-navy{color:var(--egriss-teal)}

/* ---- signature primitive 3: the key figure ---- */
.eg-figure{font-family:var(--font-mono);font-weight:600;font-size:2.25rem;line-height:1;
 color:var(--egriss-navy);letter-spacing:var(--ls-tight);display:block}
.eg-figure.teal{color:var(--egriss-teal)}
.eg-figure-cap{font-size:12px;color:var(--egriss-muted);margin-top:6px;display:block}

/* ---- the navy masthead every page opens with ---- */
.eg-mast{background:var(--egriss-navy);color:#fff;padding:18px 0 0}
.eg-mast-in{max-width:var(--eg-container,1200px);margin:0 auto;padding:0 24px;
 display:flex;align-items:center;gap:20px;flex-wrap:wrap}
.eg-logo{height:46px;width:auto;display:block;flex:0 0 auto}
.eg-logo-link{display:block;line-height:0}
.eg-nav{margin-left:auto;display:flex;gap:2px;flex-wrap:wrap}
.eg-nav a{color:rgba(255,255,255,.74);font-size:12.5px;font-weight:500;
 padding:7px 11px;border-radius:var(--radius-sm);white-space:nowrap;
 transition:background var(--dur-fast) var(--ease),color var(--dur-fast) var(--ease)}
.eg-nav a:hover{background:rgba(255,255,255,.10);color:#fff;text-decoration:none}
.eg-nav a[aria-current="page"]{color:var(--egriss-navy);background:var(--egriss-teal);font-weight:600}
.eg-hero{max-width:var(--eg-container,1200px);margin:0 auto;padding:26px 24px 32px}
.eg-hero h1{color:#fff;margin:0;font-size:31px;font-weight:700;max-width:26ch}
.eg-hero .eg-lede{color:rgba(255,255,255,.80);font-size:14.5px;line-height:1.6;
 margin:12px 0 0;max-width:72ch}
.eg-hero .eg-lede a{color:var(--egriss-teal)}
.eg-mast-edge{height:4px;background:linear-gradient(90deg,
 var(--egriss-teal) 0 26%,var(--egriss-blue) 26% 62%,var(--egriss-deep) 62% 100%)}

/* ---- the site footer ---- */
.eg-foot{background:var(--egriss-deep);color:rgba(255,255,255,.72);margin-top:56px;
 padding:30px 0;font-size:12.5px;line-height:1.7}
.eg-foot-in{max-width:var(--eg-container,1200px);margin:0 auto;padding:0 24px;
 display:flex;gap:26px;flex-wrap:wrap;align-items:flex-start}
.eg-foot a{color:var(--egriss-teal)}
.eg-foot .eg-logo{height:38px;opacity:.9}
.eg-foot p{margin:0;max-width:64ch}

@media(max-width:640px){
 .eg-hero h1{font-size:23px}
 .eg-nav{margin-left:0;width:100%}
 .eg-mast-in{gap:12px}
}
@media(prefers-reduced-motion:reduce){
 *,*::before,*::after{animation-duration:.01ms !important;transition-duration:.01ms !important}
}
@media print{
 .eg-mast,.eg-foot,.eg-nav{display:none !important}
}
"""

CSS = TOKENS + BASE

# --- the masthead ---------------------------------------------------------
# Site-relative names, as published: publish_site.py renames the build outputs.
NAV = [("map.html", "Step 0 · Evidence"),
       ("questions.html", "Steps 1–6 · Build"),
       ("crosswalk.html", "Option reference"),
       ("counted-vs-documented.html", "Coverage reference")]


def masthead(here="", eyebrow="", title="", lede="", home="index.html"):
    """The navy band each page opens with: the real lockup, the section nav,
    then the eyebrow / heading / lede / teal rule stack. `here` is the
    published filename of the current page, so its nav item is marked."""
    items = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == here else ""
        items.append('<a href="%s"%s>%s</a>' % (href, cur, label))
    nav = "".join(items)
    hero = ""
    if title:
        eb = '<span class="eg-eyebrow on-navy">%s</span>' % eyebrow if eyebrow else ""
        ld = '<p class="eg-lede">%s</p>' % lede if lede else ""
        hero = ('<div class="eg-hero">%s<h1>%s</h1>%s<hr class="eg-rule"></div>'
                % (eb, title, ld))
    return ('<header class="eg-mast"><div class="eg-mast-in">'
            '<a class="eg-logo-link" href="%s">'
            '<img class="eg-logo" src="%s" '
            'alt="EGRISS \u2014 Expert Group on Refugee, IDP and Statelessness Statistics">'
            '</a><nav class="eg-nav">%s</nav></div>%s</header>'
            '<div class="eg-mast-edge"></div>' % (home, LOGO_WHITE, nav, hero))


def sitefoot(extra=""):
    """The deep-blue footer. `extra` carries the page's own source note."""
    return ('<footer class="eg-foot"><div class="eg-foot-in">'
            '<img class="eg-logo" src="%s" alt="EGRISS">'
            '<p>%s</p></div></footer>' % (LOGO_WHITE, extra))

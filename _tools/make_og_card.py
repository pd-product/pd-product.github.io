"""Draws assets/og/default.png in full, from values.

The share card is a picture of text. The headline is pixels, not markup, so
rewording the h1 leaves every link preview quoting the old claim. Nothing in the
Jekyll build touches the card, so this is what keeps the two in step.

This is an AUTHORING step, not a build step, in the same sense README.md already
uses for share cards. Nothing runs at deploy time and the site never depends on
it -- the card is committed, and this only regenerates it.

THE LEADING UNDERSCORE ON _tools/ IS LOAD-BEARING. Jekyll skips entries starting
with `_`, which is why this file needs no entry in `exclude:` the way temp/ does.
Rename the directory to tools/ and the script deploys as a live URL on
pdiggins.com. The note above `exclude:` in _config.yml owns that rule.

WHERE THE VALUES COME FROM

Every value below is a design value, not a measurement of the previous card. The
card is no longer the authority; these are. An earlier version composited a
headline band onto the committed PNG and copied the rest through, because nothing
in the repo knew what the rest was made of. It does now.

The card's type is the site's own rules enlarged, which is the whole reason it
can be specified at all:

    element    site rule it comes from
    eyebrow    .intro .eyebrow      mono 400, uppercase, --accent
    headline   .intro h1            Space Grotesk 400, -.03em, --text
    wordmark   .site-title          mono 500, lowercase, --text
    url        .site-nav a          mono 400, --nav-muted

Two of those were recovered rather than recalled, and the recovery has a limit
worth stating: a monospace advance is `size x (0.6 + tracking)`, so the two are
not separately recoverable from a raster. The eyebrow fits its measured advance
equally well at 21.0px/.14em, 21.6px/.12em and 22.2px/.10em. 21px is chosen
because at .14em the eyebrow and the url resolve to ONE size, which no other
point on that ridge does. Changing either number changes the card.

USING IT

    python _tools/make_og_card.py            # draws and gates; installs nothing
    python _tools/make_og_card.py --write    # also installs assets/og/default.png
    python _tools/make_og_card.py --replace  # installs a card that DIFFERS from HEAD

To reword, edit HEADLINE and break it by hand. Breaks are editorial -- they fall
on sense units and no algorithm finds them -- so the tool validates them and
never rewraps. A headline that does not fit is refused, with the offending line
named. It is never shrunk: 64px is the one value on this card that was never in
doubt, and quietly abandoning it to fit a long sentence trades the design for the
copy without telling anyone.

Changing the line count is free below the block. The rule and the footer do not
move, because the headline is centred between the eyebrow's baseline and the rule
rather than anchored at a fixed cap-top, so it grows into the space above it. It
is NOT free above the block, and it is not free in _config.yml: `og_image.alt`
names the line count, and this refuses to write a card that would make it false.

A per-story card is a call, not a second code path -- `draw()` takes its eyebrow
and its lines. Nothing calls it that way yet, and switching per-story cards on
needs more than this tool: _layouts/default.html emits og:image:width, height and
both alt tags only when a page uses the default card, so a story with its own
card would ship with none of them. Fix that block first or do not ship them.

WHAT THE GATE PROVES, AND THE ONE THING IT CANNOT

There are two checks here doing different jobs, and confusing them is how a
generator ends up trusted for something it does not do.

The per-element checks prove THE RENDER MATCHES THE VALUES. Against the font
outlines, per element: the ink box on every edge, the dominant ink colour, the
weight, and -- on the mono elements -- where every interior glyph sits. They
catch a font that did not load, a browser that drew something else, a right-
aligned element that drifted, subpixel fringing.

They CANNOT catch a wrong value, and no amount of them ever will. They predict
from the same constants they drew from, so editing one moves both sides and they
still agree. Set the wordmark to 24px and every one of them passes, because 24px
is then what the card is supposed to be. That is exactly how a whole-card version
once shipped a 9px-narrow wordmark: its checks were self-consistent too.

What catches that is the comparison against the committed card, which is why a
redraw that changes anything needs --replace. The resting state is a run that
reproduces the committed card byte for byte.

The interior check is still worth having, for a narrower reason. On a monospace
string size and tracking trade off EXACTLY, so a wrong pair keeps the outer box
while walking every glyph inside it -- fitting to the box alone picks 21.3px/.12em
for the eyebrow with a PERFECT box match and interior glyphs out by up to 3px. It
is checked as OCCUPANCY -- predicted gaps stay empty, predicted glyphs have ink --
rather than run for run, because the rasteriser merges glyphs that sit closer than
about a pixel and a run count would measure that instead.

The headline does not get that check and does not need it. Space Grotesk carries
a `kern` feature and these outlines are unshaped, so a rendered line runs
NARROWER than predicted; the gate allows that as one-sided slack rather than
pretending to shape the text. And the ambiguity it exists for is specific to
monospace: in a proportional face tracking is uniform while glyph widths scale,
so a wrong size cannot be hidden by a compensating tracking.

Weight is checked against THE SAME STRING RENDERED BOTH WAYS, not against filled
outlines. Chrome's edges inflate coverage by about a quarter, which is wider than
the gap between Regular and Medium, so an outline comparison structurally prefers
the heavier face -- on the url it separates by 80.0 against 76.5, which is a coin
toss, not a check. Rendering both references makes the inflation common to each
side and cancels it.

REQUIREMENTS

Pillow, numpy, fontTools with brotli, and websocket-client. Headless Chrome on
9351 -- launched with --disable-lcd-text, which is not optional and which the
gate checks -- and the font fixture on 8731; see temp/README.md. The card uses no
stylesheet and no markup from the site, so regenerating it does NOT need a Jekyll
build -- the fixture it renders through holds the four woff2 files and nothing
else. This tool is not needed to build or serve the site.
"""
import base64
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.request

import numpy as np
import websocket
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from PIL import Image

PORT = 9351
FIXTURE = "http://127.0.0.1:8731"
ROOT = pathlib.Path(__file__).resolve().parent.parent
SHIPPED = ROOT / "assets/og/default.png"
CONFIG = ROOT / "_config.yml"
SERVED = ROOT / "temp/og-fixture"          # fonts + the scratch page, nothing else
OUT = ROOT / "temp/og-render"              # scratch; gitignored

# --- The card ---------------------------------------------------------------

EYEBROW = "solving problems with ai"       # index.html's .intro .eyebrow, verbatim
HEADLINE = ["I build products", "that solve problems",
            "people have learned", "to work around."]

# --- Canvas and column ------------------------------------------------------

WIDTH, HEIGHT = 1200, 630
BG = (16, 18, 20)                          # --bg

# The rule spans the content column and is what declares it. Every element sits
# on one of its two edges: the eyebrow, the headline and the wordmark on the
# left, the url on the right. The url is right-ALIGNED and not placed from a left
# origin on purpose -- the domain printed here has already changed once, and a
# left origin puts the new one in a different place.
COL_LEFT, COL_RIGHT = 78, 1122

# --- Type -------------------------------------------------------------------
#
# family, weight, size, tracking in em, colour.

MONO, DISPLAY = "Site Mono", "Space Grotesk"
INK_TEXT = (233, 231, 228)                 # --text
INK_ACCENT = (99, 183, 155)                # --accent
INK_MUTED = (127, 134, 141)                # --nav-muted
INK_BORDER = (35, 40, 44)                  # --border

EYEBROW_TYPE = (MONO, 400, 21, 0.14, INK_ACCENT)
HEAD_TYPE = (DISPLAY, 400, 64, -0.03, INK_TEXT)
WORDMARK_TYPE = (MONO, 500, 25, 0.0, INK_TEXT)
URL_TYPE = (MONO, 400, 21, 0.0, INK_MUTED)

WORDMARK = "pat diggins"
URL = "pdiggins.com"

# --- Fixed positions --------------------------------------------------------
#
# These do not move, at any line count, on any card.

EYEBROW_BASELINE = 96                      # cap-top y81 plus mono's 698/1000 cap
RULE_Y = 497
FOOTER_BASELINE = 550                      # the wordmark and the url share it
LINE_PITCH = 69

# --- Fitting ----------------------------------------------------------------
#
# The headline is centred between the eyebrow's baseline and the rule. Six lines
# leaves 6px between the eyebrow and the headline, so five is the ceiling and the
# floor it meets, exactly, is 40px of clearance.

MAX_LINES = 5
MIN_CLEARANCE = 40
# The widest line on the card as designed is 580px. This is about one 64px em of
# headroom over that, and it keeps at least 400px of air to the right of the
# longest line, which is what makes the card read as display type rather than as
# a paragraph.
MAX_LINE_WIDTH = 640

NUMBER_WORD = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}


def _check_constants():
    """MAX_LINES is a stated ceiling; MIN_CLEARANCE is what actually enforces it.

    Nothing else holds the two in agreement, so changing a size, the pitch or the
    eyebrow's baseline could leave a ceiling that admits a card the clearance
    rejects, or rejects one it would allow. The alt text spells the line count, so
    its vocabulary has to reach the ceiling too.
    """
    at, over = (head_cap_top(MAX_LINES) - EYEBROW_BASELINE,
                head_cap_top(MAX_LINES + 1) - EYEBROW_BASELINE)
    if not over < MIN_CLEARANCE <= at:
        raise SystemExit(
            f"MAX_LINES={MAX_LINES} and MIN_CLEARANCE={MIN_CLEARANCE}px disagree: "
            f"{MAX_LINES} lines leave {at}px and {MAX_LINES + 1} leave {over}px. "
            f"Move one to match the other.")
    missing = set(range(1, MAX_LINES + 1)) - set(NUMBER_WORD)
    if missing:
        raise SystemExit(f"NUMBER_WORD has no word for {sorted(missing)}, and "
                         f"og_image.alt spells the line count.")

# Composition, never transcription. Someone who hears this is about to meet the
# headline again as page text; repeating it here makes them listen to it twice
# and tells them nothing about the image. The rule was already being followed --
# it just was not written down anywhere a tool could check it.
ALT = ("A dark share card: a small green monospace line reading {eyebrow}, "
       "above a large {n}-line headline, with the name pat diggins and "
       "pdiggins.com along the bottom.")

FONT_FILE = {(MONO, 400): "IBMPlexMono-Regular", (MONO, 500): "IBMPlexMono-Medium",
             (DISPLAY, 400): "SpaceGrotesk-Regular",
             (DISPLAY, 500): "SpaceGrotesk-Medium"}

TEMPLATE = """<!doctype html>
<meta charset="utf-8">
<style>
{faces}
  html, body {{ margin: 0; padding: 0; }}
  body {{ width: {w}px; height: {h}px; background: {bg}; position: relative;
         overflow: hidden; -webkit-font-smoothing: antialiased; }}
  .el {{ position: absolute; white-space: pre; }}
{rules}
</style>
{body}
"""

_fonts = {}
_seq = 0
_ws = None


# --- Font outlines ----------------------------------------------------------

def font(family, weight):
    """Glyph advance, bounds and filled area, straight from the shipped woff2.

    Read rather than tabulated, so re-subsetting a face cannot leave a stale copy
    of its metrics in here disagreeing with what the browser loads.
    """
    key = (family, weight)
    if key not in _fonts:
        f = TTFont(ROOT / f"assets/fonts/{FONT_FILE[key]}.woff2")
        gs, hm, upm = f.getGlyphSet(), f["hmtx"], f["head"].unitsPerEm
        glyphs = {}
        for cp, name in f.getBestCmap().items():
            bounds = BoundsPen(gs)
            gs[name].draw(bounds)
            glyphs[chr(cp)] = (hm[name][0], bounds.bounds)
        _fonts[key] = (glyphs, upm, f["OS/2"].sCapHeight)
    return _fonts[key]


def cap_height(family, weight, size):
    glyphs, upm, cap = font(family, weight)
    return cap * size / upm


def glyph_spans(text, type_, origin):
    """Every glyph's ink interval and the pen position after the last one.

    Intervals that touch or overlap are merged, because the renderer draws them
    as one run of ink and the gate compares runs.
    """
    family, weight, size, track, _ = type_
    glyphs, upm, _cap = font(family, weight)
    k = size / upm
    pen, spans = float(origin), []
    for ch in text:
        advance, bounds = glyphs[ch]
        if bounds:
            spans.append([pen + bounds[0] * k, pen + bounds[2] * k])
        pen += advance * k + track * size
    merged = []
    for span in spans:
        if merged and span[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], span[1])
        else:
            merged.append(list(span))
    return merged, pen


def vertical_span(text, type_, baseline):
    """Ink top and bottom edges, from the tallest and deepest glyph in the string."""
    family, weight, size, _track, _ = type_
    glyphs, upm, _cap = font(family, weight)
    k = size / upm
    tops = [bounds[3] for ch in text for _a, bounds in [glyphs[ch]] if bounds]
    bottoms = [bounds[1] for ch in text for _a, bounds in [glyphs[ch]] if bounds]
    return baseline - max(tops) * k, baseline - min(bottoms) * k


def advance_width(text, type_):
    """Width of the string's advance boxes, with no trailing letter-spacing.

    CSS adds letter-spacing after the LAST character too. That is invisible on a
    left-aligned element and shifts a right-aligned one, so it is subtracted here
    rather than left to be discovered on the url the first time it is tracked.
    """
    _family, _weight, size, track, _ink = type_
    _spans, pen = glyph_spans(text, type_, 0)
    return pen - track * size


# --- Layout -----------------------------------------------------------------

def head_cap_top(n):
    """Cap-top of the first headline line, for a block of n lines.

    Centred between the eyebrow's baseline and the rule, so the rule and the
    footer never move. The block is measured cap-top to last baseline: what reads
    as the block's edges is its caps and its baseline, not the ascender box.
    """
    band = RULE_Y - EYEBROW_BASELINE
    block = (n - 1) * LINE_PITCH + cap_height(*HEAD_TYPE[:2], HEAD_TYPE[2])
    return round(EYEBROW_BASELINE + (band - block) / 2)


def fit(lines):
    """Reasons this copy cannot be set. Empty means it can."""
    problems = []
    if not lines:
        return ["the headline is empty"]
    if len(lines) > MAX_LINES:
        problems.append(
            f"{len(lines)} lines; the card holds {MAX_LINES}. That many would "
            f"leave {head_cap_top(len(lines)) - EYEBROW_BASELINE}px under the "
            f"eyebrow, against a floor of {MIN_CLEARANCE}px")
    for i, line in enumerate(lines, 1):
        spans, _pen = glyph_spans(line, HEAD_TYPE, COL_LEFT)
        if not spans:
            problems.append(f"L{i} has no ink")
            continue
        width = spans[-1][1] - spans[0][0]
        if width > MAX_LINE_WIDTH:
            problems.append(f"L{i} sets {width:.0f}px wide, over the {MAX_LINE_WIDTH}px "
                            f"measure by {width - MAX_LINE_WIDTH:.0f}px: {line!r}")
    clearance = head_cap_top(len(lines)) - EYEBROW_BASELINE
    if clearance < MIN_CLEARANCE:
        problems.append(f"{clearance}px of clearance under the eyebrow, against a floor "
                        f"of {MIN_CLEARANCE}px")
    return problems


def elements(eyebrow, lines):
    """Every drawn element: name, text, type, where its baseline goes, alignment.

    One list, so the drawing and the gate cannot disagree about what is on the
    card or where it belongs.
    """
    cap_top = head_cap_top(len(lines))
    base = cap_top + cap_height(*HEAD_TYPE[:2], HEAD_TYPE[2])
    out = [("eyebrow", eyebrow.upper(), EYEBROW_TYPE, EYEBROW_BASELINE, "left")]
    for i, line in enumerate(lines):
        out.append((f"L{i + 1}", line, HEAD_TYPE, base + i * LINE_PITCH, "left"))
    out.append(("wordmark", WORDMARK, WORDMARK_TYPE, FOOTER_BASELINE, "left"))
    out.append(("url", URL, URL_TYPE, FOOTER_BASELINE, "right"))
    return out


# --- CDP --------------------------------------------------------------------

def cmd(method, **params):
    global _seq
    _seq += 1
    _ws.send(json.dumps({"id": _seq, "method": method, "params": params}))
    while True:
        msg = json.loads(_ws.recv())
        if msg.get("id") == _seq:
            if "error" in msg:
                raise RuntimeError(f"{method}: {msg['error']}")
            return msg.get("result", {})


def connect():
    global _ws
    targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
    pages = [t for t in targets if t["type"] == "page"]
    if not pages:
        # Chrome stays alive on the debugging port with every tab closed, so this
        # is a live endpoint with nothing to drive. Worth naming: the bare
        # IndexError it used to raise reads like a protocol fault.
        sys.exit(f"Chrome on {PORT} has no page target open.\n"
                 f"  Relaunch it; see temp/README.md for the command.")
    _ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=60)
    cmd("Page.enable")
    cmd("Network.enable")
    # The scratch page is one constant URL, so without this a re-run renders the
    # previous card and reports it as current.
    cmd("Network.setCacheDisabled", cacheDisabled=True)
    cmd("Emulation.setDeviceMetricsOverride", width=WIDTH, height=HEIGHT,
        deviceScaleFactor=1, mobile=False)


def preflight():
    if not (SERVED / "assets/fonts").is_dir():
        sys.exit(f"{SERVED}/assets/fonts does not exist.\n"
                 f"  Copy the four woff2 files there, or run with the fixture rebuilt.")
    try:
        urllib.request.urlopen(f"{FIXTURE}/assets/fonts/SpaceGrotesk-Regular.woff2",
                               timeout=5)
    except Exception as exc:
        sys.exit(f"{FIXTURE} is not serving the font fixture ({exc}).\n"
                 f"  python -m http.server 8731 --directory temp/og-fixture")
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=5)
    except Exception as exc:
        sys.exit(f"No headless Chrome on {PORT} ({exc}).\n"
                 f"  See temp/README.md for the launch command.")
    OUT.mkdir(parents=True, exist_ok=True)


def sync_fixture():
    """Serve the faces the repo ships, not a copy that drifted from them."""
    dest = SERVED / "assets/fonts"
    dest.mkdir(parents=True, exist_ok=True)
    for src in sorted((ROOT / "assets/fonts").glob("*.woff2")):
        shutil.copyfile(src, dest / src.name)


# --- Drawing ----------------------------------------------------------------

def face_rules():
    seen, out = set(), []
    for family, weight in FONT_FILE:
        if (family, weight) in seen:
            continue
        seen.add((family, weight))
        out.append(f'  @font-face {{ font-family: "{family}"; font-weight: {weight};\n'
                   f'    src: url("/assets/fonts/{FONT_FILE[(family, weight)]}.woff2") '
                   f'format("woff2"); }}')
    return "\n".join(out)


def css_colour(rgb):
    return "#%02x%02x%02x" % rgb


def page(placed, rule=True):
    """The whole card as one document. `placed` is (id, text, type, top, align)."""
    rules, body = [], []
    for i, (_name, text, type_, top, align) in enumerate(placed):
        family, weight, size, track, ink = type_
        edge = f"left: {COL_LEFT}px" if align == "left" else \
               f"right: {WIDTH - COL_RIGHT}px"
        rules.append(
            f"  #e{i} {{ {edge}; top: {top}px; font: {weight} {size}px/normal "
            f'"{family}"; letter-spacing: {track}em; color: {css_colour(ink)}; }}')
        body.append(f'<div class="el" id="e{i}">{text}</div>')
    if rule:
        rules.append(f"  #rule {{ left: {COL_LEFT}px; top: {RULE_Y}px; "
                     f"width: {COL_RIGHT - COL_LEFT}px; height: 1px; "
                     f"background: {css_colour(INK_BORDER)}; }}")
        body.append('<div class="el" id="rule"></div>')
    return TEMPLATE.format(faces=face_rules(), rules="\n".join(rules),
                           body="\n".join(body), w=WIDTH, h=HEIGHT,
                           bg=css_colour(BG))


def render(html, name):
    (SERVED / "og-card.html").write_text(html, encoding="utf-8")
    cmd("Page.navigate", url=f"{FIXTURE}/og-card.html")
    time.sleep(1.6)
    shot = cmd("Page.captureScreenshot", format="png")
    path = OUT / name
    path.write_bytes(base64.b64decode(shot["data"]))
    return Image.open(path).convert("RGB")


def draw(eyebrow, lines):
    """Place every element by measuring a probe, then translating it into place.

    CSS positions a line BOX and the spec positions a baseline, and the offset
    between them is half-leading, which rounds per family and per size. Deriving
    it from font metrics is not exact; measuring it is. Each probe is translated
    by a whole number of pixels, so the placed element rasterises identically to
    the probe rather than merely close to it.
    """
    els = elements(eyebrow, lines)
    probe_top = 200
    placed, weights = [], {}
    for name, text, type_, baseline, align in els:
        family, weight, size, track, ink = type_
        want_top, _bottom = vertical_span(text, type_, baseline)
        probe = render(page([(name, text, type_, probe_top, align)], rule=False),
                       f"probe-{name}.png")
        got = ink_rows(np.asarray(probe))
        if not got:
            sys.exit(f"probe for {name} drew nothing")
        placed.append((name, text, type_, probe_top + int(want_top) - got[0], align))

        # A second probe at the OTHER weight, through the same rasteriser, so the
        # gate can tell them apart. Comparing the drawn area to filled outlines
        # instead cannot: Chrome's edges inflate coverage by about a quarter,
        # which is wider than the gap between Regular and Medium, so an outline
        # comparison structurally prefers the heavier face. Measured on the url
        # it separates by 80.0 against 76.5 -- a coin toss. Rendering both makes
        # the inflation common to each side and cancels it.
        alt = (family, 500 if weight == 400 else 400, size, track, ink)
        other = render(page([(name, text, alt, probe_top, align)], rule=False),
                       f"probe-{name}-alt.png")
        weights[name] = (area_of(np.asarray(probe), ink),
                         area_of(np.asarray(other), ink), alt[1])
    return els, placed, weights, render(page(placed), "card.png")


# --- Measuring --------------------------------------------------------------

def area_of(arr, ink, y0=0, y1=HEIGHT - 1, x0=0, x1=WIDTH - 1):
    """Total ink coverage in square pixels, projected onto this element's colour."""
    px = arr[y0:y1 + 1, x0:x1 + 1]
    d = np.array(ink, float) - np.array(BG, float)
    cover = ((px.astype(float) - np.array(BG, float)) * d).sum(axis=2) / (d * d).sum()
    return float(np.clip(cover, 0, 1)[ink_mask(arr)[y0:y1 + 1, x0:x1 + 1]].sum())


def ink_mask(arr):
    return np.abs(arr.astype(np.int16) - np.array(BG, dtype=np.int16)).max(axis=2) > 24


def ink_rows(arr):
    return list(np.where(ink_mask(arr).any(axis=1))[0])


def measure(arr, y0, y1, x0=0, x1=WIDTH - 1, ink=None):
    """Ink box, column runs, coverage area and dominant colour in a window."""
    m = ink_mask(arr)[y0:y1 + 1, x0:x1 + 1]
    ys = np.where(m.any(axis=1))[0]
    xs = np.where(m.any(axis=0))[0]
    if not len(xs):
        return None
    px = arr[y0:y1 + 1, x0:x1 + 1]
    out = {"x0": int(xs[0]) + x0, "x1": int(xs[-1]) + x0,
           "y0": int(ys[0]) + y0, "y1": int(ys[-1]) + y0,
           "cols": np.where(m.any(axis=0))[0] + x0}
    values, counts = np.unique(px[m], axis=0, return_counts=True)
    out["colour"] = tuple(int(v) for v in values[counts.argmax()])
    if ink is not None:
        d = np.array(ink, float) - np.array(BG, float)
        cover = ((px.astype(float) - np.array(BG, float)) * d).sum(axis=2) / (d * d).sum()
        out["area"] = float(np.clip(cover, 0, 1)[m].sum())
    return out


def x_windows(arr, els):
    """An x-window per element, so two elements in one row are measured apart.

    The wordmark and the url share the footer row, and a measurement of either
    that can reach the other is not a measurement of it. The split comes from the
    RENDER -- the widest empty column between them -- not from where the values
    say they should be, so it cannot launder a placement error into agreement.
    """
    bands, anchor = {}, {}
    for name, text, type_, baseline, align in els:
        top, bottom = vertical_span(text, type_, baseline)
        bands[name] = (int(top) - 3, int(bottom) + 3)
        anchor[name] = COL_LEFT if align == "left" else \
            COL_RIGHT - advance_width(text, type_)

    clusters = []
    for name, (y0, y1) in bands.items():
        for c in clusters:
            if any(bands[m][0] <= y1 and bands[m][1] >= y0 for m in c):
                c.append(name)
                break
        else:
            clusters.append([name])

    out = {}
    for c in clusters:
        if len(c) == 1:
            out[c[0]] = (0, WIDTH - 1)
            continue
        lo = min(bands[m][0] for m in c)
        hi = max(bands[m][1] for m in c)
        cols = np.where(ink_mask(arr)[lo:hi + 1].any(axis=0))[0]
        gaps = sorted(((int(cols[i + 1] - cols[i]), int(cols[i]), int(cols[i + 1]))
                       for i in range(len(cols) - 1)), reverse=True)
        cuts = sorted((g[1] + g[2]) // 2 for g in gaps[:len(c) - 1])
        edges = [0] + cuts + [WIDTH - 1]
        # Sorted by where the values put each element, NOT by the order they were
        # declared in. Those agree today -- the footer declares the wordmark
        # before the url -- and a right-aligned element declared first would
        # silently hand each one the other's window.
        for i, name in enumerate(sorted(c, key=lambda n: anchor[n])):
            out[name] = (edges[i], edges[i + 1])
    return out


# --- The gate ---------------------------------------------------------------

def interior_drift(cols, spans):
    """How far the drawn glyphs sit from where the outlines put them.

    Compared as OCCUPANCY rather than as a run-for-run match: at -.03em a display
    face merges adjacent glyphs into one run of ink, and at these sizes so do `a`
    and `t` in the wordmark, so counting runs measures the rasteriser rather than
    the placement. Instead every gap the outlines predict WIDE ENOUGH to survive
    antialiasing must be empty, and every glyph must have ink where it belongs.

    This is the check an ink box cannot do. A wrong advance keeps the box while
    walking every interior glyph -- which is how a whole-card version once set
    the wordmark 9px narrow -- and it puts ink in the predicted gaps.
    """
    have = set(int(c) for c in cols)
    misplaced = 0
    for i, (left, right) in enumerate(spans):
        if not any(x in have for x in range(int(left), int(right) + 1)):
            misplaced += 1
        if i + 1 < len(spans):
            gap0, gap1 = right, spans[i + 1][0]
            if gap1 - gap0 < 2.5:
                continue
            intruders = [x for x in range(int(gap0) + 2, int(gap1) - 1) if x in have]
            if intruders:
                misplaced += 1
    return misplaced


def check(arr, els, placed, weights):
    """Every element, against its outlines. Returns the failures."""
    fails = []
    windows = x_windows(arr, els)
    for name, text, type_, baseline, align in els:
        family, weight, size, _track, ink = type_
        origin = COL_LEFT if align == "left" else COL_RIGHT - advance_width(text, type_)
        spans, _pen = glyph_spans(text, type_, origin)
        top, bottom = vertical_span(text, type_, baseline)
        x0, x1 = windows[name]
        got = measure(arr, max(0, int(top) - 3), min(HEIGHT - 1, int(bottom) + 3),
                      x0, x1, ink=ink)
        if got is None:
            fails.append(f"{name}: nothing drawn where its values put it")
            continue
        want = {"x0": int(spans[0][0]), "x1": int(spans[-1][1]),
                "y0": int(top), "y1": int(bottom)}
        # Space Grotesk carries a `kern` feature and these outlines are unshaped,
        # so a rendered display line is NARROWER than predicted. The subset mono
        # has an empty GPOS feature list, so it is held exactly. Allowing the
        # slack on both is how a real defect would hide.
        kerns = family == DISPLAY
        for edge in ("x0", "y0", "y1"):
            if abs(got[edge] - want[edge]) > 1.5:
                fails.append(f"{name} {edge} is {got[edge]}, outlines say {want[edge]}")
        slack = got["x1"] - want["x1"]
        if kerns:
            floor = -0.012 * (want["x1"] - want["x0"])
            if not floor <= slack <= 1.5:
                fails.append(f"{name} right edge {got['x1']}, unkerned outlines say "
                             f"{want['x1']} ({slack:+.0f}px; kerning allows "
                             f"{floor:.0f} to +1.5)")
        elif abs(slack) > 1.5:
            fails.append(f"{name} x1 is {got['x1']}, outlines say {want['x1']}")

        # Only where the outlines are the whole story. Shaping a kerned line
        # against unshaped outlines measures the kerning, not the placement -- and
        # the ambiguity this check exists for is specific to monospace, where size
        # and tracking trade off EXACTLY and the box cannot separate them. In a
        # proportional face they do not: tracking is uniform while glyph widths
        # scale, so a wrong size cannot be hidden by a compensating tracking.
        if not kerns:
            drift = interior_drift(got["cols"], spans)
            if drift:
                fails.append(f"{name}: {drift} of {len(spans)} glyphs are not where "
                             f"the outlines put them, while the ink box matches")

        if got["colour"] != ink:
            fails.append(f"{name} ink is {css_colour(got['colour'])}, "
                         f"should be {css_colour(ink)}")

        # Weight, against the SAME string drawn both ways through this rasteriser
        # rather than against a tolerance. Both references carry Chrome's edge
        # inflation equally, so it cancels instead of deciding the answer.
        mine, theirs, other = weights[name]
        if abs(got["area"] - mine) >= abs(got["area"] - theirs):
            fails.append(f"{name}: drawn area {got['area']:.0f} is nearer {family} "
                         f"{other} ({theirs:.0f}) than the {weight} it declares "
                         f"({mine:.0f})")
    return fails


def check_fringing(arr):
    """No pixel may carry a hue the card's tokens cannot produce.

    Chrome antialiases LARGE glyphs to greyscale and SMALL ones to LCD subpixels,
    so the 64px headline comes back clean while the 21px eyebrow comes back with
    orange and blue fringes down every stem. That is correct for text on a screen
    at 1:1 and wrong for a file: a share card is rescaled and recomposited by
    whoever renders the preview, and the fringes travel with it as colour.

    It is invisible in the diff, invisible in a thumbnail, and it does not move
    any element, so nothing else in this gate can see it. It needs
    --disable-lcd-text on the Chrome that renders the card; this is what proves
    the flag was actually there.
    """
    a = arr.astype(float)
    bg = np.array(BG, float)
    flat = a.reshape(-1, 3)
    lit = flat[np.linalg.norm(flat - bg, axis=1) > 1.5]
    if not len(lit):
        return ["the card is blank"]
    worst = np.full(len(lit), np.inf)
    for ink in (INK_TEXT, INK_ACCENT, INK_MUTED, INK_BORDER):
        u = np.array(ink, float) - bg
        alpha = np.clip((lit - bg) @ u / (u @ u), 0, 1)[:, None]
        worst = np.minimum(worst, np.linalg.norm((lit - bg) - alpha * u, axis=1))
    off = int((worst > 12).sum())
    if off:
        return [f"{off} of {len(lit)} ink pixels carry a hue no token can make "
                f"(worst {worst.max():.0f}). Subpixel antialiasing: relaunch Chrome "
                f"with --disable-lcd-text"]
    return []


def check_rule(arr):
    fails = []
    row = arr[RULE_Y]
    xs = np.where(np.abs(row.astype(np.int16)
                         - np.array(BG, dtype=np.int16)).max(axis=1) > 2)[0]
    if not len(xs) or xs[0] != COL_LEFT or xs[-1] != COL_RIGHT - 1:
        got = f"x{xs[0]}-{xs[-1]}" if len(xs) else "nothing"
        fails.append(f"rule at y{RULE_Y} is {got}, should be x{COL_LEFT}-{COL_RIGHT - 1}")
    elif not (row[COL_LEFT:COL_RIGHT] == np.array(INK_BORDER, dtype=row.dtype)).all():
        fails.append(f"rule at y{RULE_Y} is not a uniform {css_colour(INK_BORDER)}")
    for y in (RULE_Y - 1, RULE_Y + 1):
        if (np.abs(arr[y].astype(np.int16)
                   - np.array(BG, dtype=np.int16)).max(axis=1) > 2).any():
            fails.append(f"the rule bleeds onto y{y}; it must be exactly 1px")
    return fails


def check_alt(n, eyebrow):
    """og_image.alt names the line count, so a re-broken headline can falsify it.

    Scoped to the og_image block rather than to the first `alt:` in the file. A
    per-story card would add a second one, and matching whichever came first
    would check the wrong card's description against this one.
    """
    text = CONFIG.read_text(encoding="utf-8")
    block = re.search(r"^og_image:\n((?:[ \t]+.*\n|\n)*)", text, re.M)
    if not block:
        return [f"no og_image block in {CONFIG.name}"]
    match = re.search(r'^\s+alt:\s*"(.*)"\s*$', block.group(1), re.M)
    if not match:
        return [f"no alt in the og_image block of {CONFIG.name}"]
    want = ALT.format(eyebrow=eyebrow, n=NUMBER_WORD[n])
    if match.group(1) != want:
        return [f"og_image.alt does not describe this card.\n"
                f"     in {CONFIG.name}: {match.group(1)}\n"
                f"     should read:    {want}"]
    return []


def committed_card():
    """The card as committed, or None if it is not in HEAD yet."""
    r = subprocess.run(["git", "show", f"HEAD:{SHIPPED.relative_to(ROOT).as_posix()}"],
                       cwd=ROOT, capture_output=True)
    if r.returncode != 0:
        return None
    path = OUT / "committed.png"
    path.write_bytes(r.stdout)
    return Image.open(path).convert("RGB")


def check_against_committed(before, after):
    """Refuse to change the card unless the change was asked for.

    THE REST OF THE GATE CANNOT DO THIS, and the difference is worth being exact
    about. Everything else here proves the render matches the VALUES: it predicts
    from the same constants it drew from, so editing one moves both sides and the
    gate still agrees. Set the wordmark to 24px and every geometry check passes,
    because 24px is then what the card is supposed to be. That is precisely the
    class of mistake that shipped a 9px-narrow wordmark, and only a comparison
    against the card already committed can see it.

    So a redraw that changes the card needs --replace, and the resting state is a
    run that reproduces it byte for byte.
    """
    a, b = np.asarray(before).astype(np.int16), np.asarray(after).astype(np.int16)
    if a.shape != b.shape:
        return [f"the committed card is {a.shape[1]}x{a.shape[0]} and this is "
                f"{b.shape[1]}x{b.shape[0]}"]
    d = np.abs(a - b).max(axis=2)
    if not d.any():
        return []
    rows = np.where(d.any(axis=1))[0]
    return [f"this differs from the committed card: {int((d > 0).sum())} pixels, "
            f"y{rows[0]}-{rows[-1]}, largest change {int(d.max())} of 255.\n"
            f"     If the copy or a design value changed on purpose, pass --replace.\n"
            f"     If it did not, something moved that nobody asked to move."]


def report(before, after, els):
    """What moved against the committed card, so a redraw is legible as a diff.

    The bands come from the elements rather than being written down, because a
    five-line headline reaches y475 and a fixed band would quietly stop counting
    the part that moved.
    """
    print("\n   against the committed card:")
    groups = {"eyebrow": [], "headline": [], "footer": []}
    for name, text, type_, baseline, _align in els:
        key = "headline" if name.startswith("L") else \
            ("eyebrow" if name == "eyebrow" else "footer")
        top, bottom = vertical_span(text, type_, baseline)
        groups[key].append((top, bottom))
    a, b = np.asarray(before).astype(np.int16), np.asarray(after).astype(np.int16)
    for key, spans in groups.items():
        y0 = max(0, int(min(s[0] for s in spans)) - 4)
        y1 = min(HEIGHT - 1, int(max(s[1] for s in spans)) + 4)
        d = np.abs(a[y0:y1 + 1] - b[y0:y1 + 1]).max(axis=2)
        changed = int((d > 0).sum())
        print(f"     y{y0}-{y1} ({key}): {changed} pixels differ, "
              f"largest change {int(d.max())} of 255")


def main():
    _check_constants()
    preflight()
    sync_fixture()

    problems = fit(HEADLINE)
    if problems:
        print("THIS HEADLINE DOES NOT FIT:")
        for p in problems:
            print("   " + p)
        sys.exit("Rewrite or re-break it. The card is not shrunk to fit.")

    n = len(HEADLINE)
    alt = check_alt(n, EYEBROW)
    if alt:
        print("ALT TEXT DISAGREES WITH THIS CARD:")
        for a in alt:
            print("   " + a)
        sys.exit("Fix og_image.alt in _config.yml first. Not writing.")

    connect()
    print(f"headline: {n} lines, cap-top y{head_cap_top(n)}, "
          f"{head_cap_top(n) - EYEBROW_BASELINE}px under the eyebrow")

    els, placed, weights, card = draw(EYEBROW, HEADLINE)
    arr = np.asarray(card)

    fails = check(arr, els, placed, weights) + check_rule(arr) + check_fringing(arr)
    if fails:
        print("GATE FAILED -- the card does not match its own values:")
        for f in fails:
            print("   " + f)
        sys.exit("Not writing.")
    print("gate: every element matches its outlines, box and interior")

    committed = committed_card()
    if committed is not None:
        report(committed, card, els)
        drift = check_against_committed(committed, card)
        if drift and "--replace" not in sys.argv:
            print("\nTHIS REDRAW CHANGES THE CARD:")
            for d in drift:
                print("   " + d)
            sys.exit("Not writing.")
        if not drift:
            print("   the committed card is reproduced exactly")

    # The committed card is RGBA with a uniformly opaque alpha channel. Preserving
    # that keeps the written file different from the previous one only in its
    # pixels, not in its channel layout as well -- and the preview is written the
    # same way, so what is previewed is what gets installed.
    card = card.convert("RGBA")
    if "--write" in sys.argv or "--replace" in sys.argv:
        card.save(SHIPPED)
        print(f"\nwritten to {SHIPPED}")
    else:
        card.save(OUT / "preview.png")
        print(f"\nnot installed; preview at {OUT / 'preview.png'} "
              f"(pass --write to install)")


if __name__ == "__main__":
    main()

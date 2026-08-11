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
outlines, per element: the canvas size, the ink box on every edge, every interior
glyph edge, the dominant ink colour, and the weight. They catch a font that did
not load, a browser that drew something else, a right-aligned element that
drifted, subpixel fringing, a card of the wrong size.

They CANNOT catch a wrong value, and no amount of them ever will. They predict
from the same constants they drew from, so editing one moves both sides and they
still agree. Set the wordmark to 24px and every one of them passes, because 24px
is then what the card is supposed to be. That is exactly how a whole-card version
once shipped a 9px-narrow wordmark: its checks were self-consistent too.

What catches that is the comparison against the committed card, which is why a
redraw that changes anything needs --replace. The resting state is a run that
reproduces the committed card byte for byte.

The interior check earns its place on gross drift, not on close calls. It asks
whether every drawn column falls inside some predicted glyph and every predicted
glyph drew something -- CONTAINMENT, not a run-for-run pairing. Pairing fails
both ways on real input: one glyph can draw two runs (Space Grotesk's `"` is two
contour groups 2.4px apart at 64px) and one run can cover several glyphs, and
then only that group's outer edges get checked while ink floods the gap inside.

It does NOT separate a compensating size and tracking pair: eyebrow 20px/.18em
against 21px/.14em moves the last glyph 1.3px and narrows each by 0.6px, both
under the antialiasing floor. That is why the original card's size and tracking
were not separately recoverable, and it is another thing only the committed-card
comparison sees.

BOTH faces are predicted KERNED, because the browser kerns. Predicting from
unshaped outlines runs a display line up to 4.5px wide of what Chrome draws, and
the error cannot be allowed in one direction either -- over the characters this
subset carries, `kern` resolves to 1003 non-zero pairs of which 28 are POSITIVE.
Resolution follows OpenType rather than a flattened dictionary: the FIRST subtable
covering a pair wins, and this face disagrees with itself where that matters
(`f`+`t` is -17 in its Format 1 subtable and -120 in its Format 2). Ligatures are
not modelled at all -- substitution changes which glyphs exist -- so copy forming
one of `ff ffi ffj ffl fi fj fl tt` is refused by `fit()` instead. No current copy
forms one.

Weight is checked against THE SAME STRING RENDERED BOTH WAYS, not against filled
outlines. Chrome's edges inflate coverage by about a quarter, which is wider than
the gap between Regular and Medium, so an outline comparison structurally prefers
the heavier face -- on the url it separates by 80.0 against 76.5, which is a coin
toss, not a check. Rendering both references makes the inflation common to each
side and cancels it.

REQUIREMENTS

Pillow, numpy, fontTools with brotli, and websocket-client. Headless Chrome on
9351 -- launched with --disable-lcd-text, which is not optional and which the
gate checks -- and the font fixture on 8731; see README.md's Tools section. The card uses no
stylesheet and no markup from the site, so regenerating it does NOT need a Jekyll
build -- the fixture it renders through holds the four woff2 files and nothing
else. This tool is not needed to build or serve the site.
"""
import base64
import html
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

EYEBROW = "building with ai"               # index.html's .intro .eyebrow, verbatim
HEADLINE = ["Always learning.", "Often solving problems."]

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
# How far right a headline line may reach, measured from COL_LEFT to its last
# ink. A line may not fill the column: what makes the card read as display type
# rather than as a paragraph is the air left to the right of the longest line,
# and this keeps that above a third of the 1044px column.
#
# The floor is the durable half. Copy that reaches past it is re-broken or
# rewritten -- never shrunk, and never admitted by moving this number to suit one
# sentence, which would leave a measure that refuses nothing.
MAX_LINE_REACH = 690

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
       "above a large {n}-line headline, with the name {wordmark} and "
       "{url} along the bottom.")

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

def _feature_lookups(table, tag):
    """Lookup indices reached by one feature tag."""
    out = set()
    if table is None:
        return out
    fl = table.table.FeatureList
    for i in range(fl.FeatureCount):
        if fl.FeatureRecord[i].FeatureTag == tag:
            out.update(fl.FeatureRecord[i].Feature.LookupListIndex)
    return out


def _kern_subtables(f, key):
    """The `kern` feature's pair-positioning subtables, IN LOOKUP ORDER.

    Kept as subtables rather than flattened into one pair dictionary, because
    OpenType resolves a lookup by taking the FIRST subtable that covers the pair
    and flattening loses that. This face puts a Format 1 and a Format 2 subtable
    in one lookup and they disagree: `f`+`t` is -17 in the first and -120 in the
    second. A dictionary built by overwriting ends on -120 and mispredicts any
    line containing "after" by 6.6px at 64px.

    Applied at all because the browser applies it. Predicting from unshaped
    outlines runs a display line up to 4.5px wide of what Chrome draws, and the
    error cannot be allowed in one direction either -- this face carries positive
    pairs as well as negative.

    `kern` is the only positioning feature that can apply here. The other
    default-on candidate, `locl`, is registered on this face under the CAT and
    TRK language systems only, and the card sets no language.

    Anything this does not model is a hard error rather than a silent zero: the
    point of reading the shipped font is that re-subsetting cannot leave a stale
    assumption behind, and quietly skipping a structure would defeat that.
    """
    subtables = []
    if "GPOS" not in f:
        return subtables
    gp = f["GPOS"].table
    for li in sorted(_feature_lookups(f["GPOS"], "kern")):
        lookup = gp.LookupList.Lookup[li]
        if lookup.LookupType == 9:
            raise SystemExit(f"{FONT_FILE[key]}: kern lookup {li} is an extension "
                             f"lookup, which this does not resolve. Predict geometry "
                             f"with a real shaper or drop the feature.")
        if lookup.LookupType != 2:
            raise SystemExit(f"{FONT_FILE[key]}: kern lookup {li} is type "
                             f"{lookup.LookupType}, not pair positioning. This models "
                             f"pair positioning only.")
        group = []
        for st in lookup.SubTable:
            # Only "advance the first glyph in x" is modelled. Every other field
            # OpenType allows in a ValueRecord -- placement, y advance, device and
            # variation tables -- would change the geometry, and a non-empty
            # ValueFormat2 also changes how the pair is traversed. Silently
            # ignoring one would defeat the reason for reading the shipped font.
            vf1 = getattr(st, "ValueFormat1", 0)
            vf2 = getattr(st, "ValueFormat2", 0)
            if vf1 & ~0x0004 or vf2:
                raise SystemExit(
                    f"{FONT_FILE[key]}: a kern subtable carries ValueFormat1="
                    f"0x{vf1:04X} ValueFormat2=0x{vf2:04X}. Only x-advance on the "
                    f"first glyph (0x0004) is modelled; predict geometry with a real "
                    f"shaper before re-subsetting with anything else.")
            if st.Format == 1:
                pairs = {}
                for gi, first in enumerate(st.Coverage.glyphs):
                    for rec in st.PairSet[gi].PairValueRecord:
                        pairs[(first, rec.SecondGlyph)] = (
                            getattr(rec.Value1, "XAdvance", 0) or 0)
                group.append(("pairs", pairs))
            elif st.Format == 2:
                # CLASS 0 IS EVERY GLYPH THE ClassDef DOES NOT MENTION, and it is
                # not listed there. Resolving classes with `.get(glyph, 0)` gets it
                # right; building the class lists from `classDefs` alone does not,
                # and 8 non-zero adjustments in this face involve class 0.
                group.append(("classes", (set(st.Coverage.glyphs),
                                          st.ClassDef1.classDefs,
                                          st.ClassDef2.classDefs,
                                          st.Class1Record)))
            else:
                raise SystemExit(f"{FONT_FILE[key]}: kern subtable format "
                                 f"{st.Format} is not modelled.")
        subtables.append(group)
    return subtables


def kern_between(subtables, left, right):
    """The x adjustment a browser applies between two glyphs.

    First covering subtable wins WITHIN a lookup; lookups accumulate.
    """
    total = 0
    for group in subtables:
        for kind, data in group:
            if kind == "pairs":
                if (left, right) in data:
                    total += data[(left, right)]
                    break
            else:
                covered, cd1, cd2, records = data
                if left in covered:
                    rec = records[cd1.get(left, 0)].Class2Record[cd2.get(right, 0)]
                    total += getattr(getattr(rec, "Value1", None), "XAdvance", 0) or 0
                    break
    return total


def _ligature_sequences(f):
    """Glyph-name sequences the `liga` feature would substitute.

    Not applied -- substitution changes which glyphs exist, so predicting it means
    reimplementing a shaper. Copy that would trigger one is refused instead. No
    current copy does; `ff`, `fi`, `fl` and `tt` are the ones to watch.
    """
    out = set()
    if "GSUB" not in f:
        return out
    gs = f["GSUB"].table
    for li in sorted(_feature_lookups(f["GSUB"], "liga")):
        lookup = gs.LookupList.Lookup[li]
        if lookup.LookupType != 4:
            continue
        for st in lookup.SubTable:
            for first, ligs in (getattr(st, "ligatures", {}) or {}).items():
                for lig in ligs:
                    out.add((first, *lig.Component))
    return out


def font(family, weight):
    """Glyph metrics, kern pairs and ligature sequences from the shipped woff2.

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
            glyphs[chr(cp)] = (name, hm[name][0], bounds.bounds)
        _fonts[key] = (glyphs, upm, f["OS/2"].sCapHeight,
                       _kern_subtables(f, key), _ligature_sequences(f))
    return _fonts[key]


def unsupported(text, type_):
    """Characters this face cannot set, and sequences it would reshape.

    The faces are SUBSET to the glyphs the site renders, so a curly quote or an
    accented letter pasted into a headline is genuinely absent rather than merely
    unusual. Without this the tool raises a bare KeyError deep inside a geometry
    helper instead of naming the line, which is what it promises to do.
    """
    family, weight, _size, _track, _ink = type_
    glyphs, _upm, _cap, _kern, ligs = font(family, weight)
    # Reported as code points, never as the characters themselves: unambiguous
    # (a curly quote and a straight one are the same shape in an error message)
    # and safe to print on any console. Echoing the character raised
    # UnicodeEncodeError on this machine's cp1252 terminal.
    missing = sorted(f"U+{ord(ch):04X}" for ch in set(text) if ch not in glyphs)
    names = [glyphs[ch][0] for ch in text if ch in glyphs]
    formed = sorted({"".join(seq) for seq in ligs
                     for i in range(len(names) - len(seq) + 1)
                     if tuple(names[i:i + len(seq)]) == seq})
    return missing, formed


def cap_height(family, weight, size):
    _glyphs, upm, cap, _kern, _ligs = font(family, weight)
    return cap * size / upm


def glyph_spans(text, type_, origin):
    """Every glyph's ink interval and the pen position after the last one.

    Kerned, because the browser kerns. Intervals closer than a pixel are merged
    so that a span is one contiguous region to test containment against; the gate
    no longer pairs runs to spans, so the merge is about keeping the predicted
    region honest rather than about matching counts.
    """
    family, weight, size, track, _ = type_
    glyphs, upm, _cap, kern, _ligs = font(family, weight)
    k = size / upm
    pen, spans, prev = float(origin), [], None
    for ch in text:
        name, advance, bounds = glyphs[ch]
        if prev is not None:
            pen += kern_between(kern, prev, name) * k
        if bounds:
            spans.append([pen + bounds[0] * k, pen + bounds[2] * k])
        pen += advance * k + track * size
        prev = name
    merged = []
    for span in spans:
        if merged and span[0] - merged[-1][1] < 1.0:
            merged[-1][1] = max(merged[-1][1], span[1])
        else:
            merged.append(list(span))
    return merged, pen


def vertical_span(text, type_, baseline):
    """Ink top and bottom edges, from the tallest and deepest glyph in the string."""
    family, weight, size, _track, _ = type_
    glyphs, upm, _cap, _kern, _ligs = font(family, weight)
    k = size / upm
    tops = [b[3] for ch in text for _n, _a, b in [glyphs[ch]] if b]
    bottoms = [b[1] for ch in text for _n, _a, b in [glyphs[ch]] if b]
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


def fit(eyebrow, lines):
    """Reasons this card cannot be set. Empty means it can.

    Covers EVERY element, not just the headline. The eyebrow, the wordmark and
    the url are all set in a subset face too, and `draw()` is meant to take an
    eyebrow and lines so a per-story card is a call rather than a second code
    path. Validating only the headline left that call raising KeyError out of a
    geometry helper on `draw("cafe with an accent", ...)`, which is the opposite
    of naming the problem.
    """
    problems = []
    # WHITESPACE AT AN EDGE MOVES THE ELEMENT, and only the headline is measured
    # for where it ends up. The eyebrow, the wordmark and the url have no reach
    # constraint at all, so a leading space silently indents one of them and
    # every check still agrees -- they predict from the same shift. Caught here
    # for all four rather than left to the one measure that would notice.
    # Refused rather than stripped: the breaks are editorial, and silently
    # rewriting one is the thing this tool does not do.
    for label, text in [("the eyebrow", eyebrow), ("the wordmark", WORDMARK),
                        ("the url", URL)] + \
                       [(f"L{i}", line) for i, line in enumerate(lines, 1)]:
        if text != text.strip():
            problems.append(f"{label} has whitespace at an edge: {text!r}")
    for label, text, type_ in [("the eyebrow", eyebrow.upper(), EYEBROW_TYPE),
                               ("the wordmark", WORDMARK, WORDMARK_TYPE),
                               ("the url", URL, URL_TYPE)]:
        # ORDER MATTERS. unsupported() first, because glyph_spans() indexes the
        # cmap and raises KeyError on a character the subset lacks -- checking for
        # ink first sends an unsettable eyebrow through that path and loses the
        # named refusal this exists to give.
        missing, formed = unsupported(text, type_)
        if missing:
            problems.append(f"{label} uses {', '.join(missing)}, which the subset "
                            f"face does not carry")
            continue
        if formed:
            problems.append(f"{label} contains {', '.join(formed)}, which the face "
                            f"substitutes as a ligature and this does not reshape")
            continue
        # Draws no ink -- empty, or nothing but spaces. Tested on the spans rather
        # than on the string, so a space-only value is caught for the same reason
        # an empty one is instead of reaching vertical_span() and raising there.
        if not glyph_spans(text, type_, 0)[0]:
            problems.append(f"{label} draws no ink; every element on this card is "
                            f"required content")
    if not lines:
        problems.append("the headline is empty")
        return problems
    if len(lines) > MAX_LINES:
        problems.append(
            f"{len(lines)} lines; the card holds {MAX_LINES}. That many would "
            f"leave {head_cap_top(len(lines)) - EYEBROW_BASELINE}px under the "
            f"eyebrow, against a floor of {MIN_CLEARANCE}px")
    for i, line in enumerate(lines, 1):
        missing, formed = unsupported(line, HEAD_TYPE)
        if missing:
            problems.append(f"L{i} uses {', '.join(missing)}, which the subset face "
                            f"does not carry")
            continue
        if formed:
            problems.append(f"L{i} contains {', '.join(formed)}, which the face "
                            f"substitutes as a ligature. This predicts geometry from "
                            f"outlines and does not reshape, so it will not set a "
                            f"line it cannot measure")
            continue
        spans, _pen = glyph_spans(line, HEAD_TYPE, COL_LEFT)
        if not spans:
            problems.append(f"L{i} has no ink")
            continue
        # Measured to where the ink ENDS, from the column's left edge, not as the
        # span between first and last ink. The two differ by the first glyph's
        # left side bearing, and only the first one is the air the measure exists
        # to protect -- a line is refused for reaching too far right, which is
        # where it is seen, not for being wide somewhere else on the canvas.
        reach = spans[-1][1] - COL_LEFT
        if reach > MAX_LINE_REACH:
            problems.append(f"L{i} reaches {reach:.0f}px from the column's left edge, "
                            f"over the {MAX_LINE_REACH}px measure by "
                            f"{reach - MAX_LINE_REACH:.0f}px: {line!r}")
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
                 f"  Relaunch it; see README.md's Tools section for the command.")
    _ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=60)
    cmd("Page.enable")
    cmd("Network.enable")
    # The scratch page is one constant URL, so without this a re-run renders the
    # previous card and reports it as current.
    cmd("Network.setCacheDisabled", cacheDisabled=True)
    cmd("Emulation.setDeviceMetricsOverride", width=WIDTH, height=HEIGHT,
        deviceScaleFactor=1, mobile=False)


def preflight():
    # BUILD the fixture before demanding it. temp/ is gitignored, so on a fresh
    # clone this directory does not exist -- and it is made entirely of files the
    # repo already has, so telling the author to copy them by hand asks for the
    # one thing that can put a stale face in front of the browser.
    sync_fixture()
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
                 f"  See README.md's Tools section for the launch command.")
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
        # ESCAPED. The copy is validated against the FONT, so markup characters
        # pass that check and are then parsed rather than drawn. A bare `&` before
        # a space survives, but `research &copy design` loses four characters to a
        # copyright sign and `<em>` disappears entirely.
        body.append(f'<div class="el" id="e{i}">{html.escape(text)}</div>')
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
    problems = fit(eyebrow, lines)
    if problems:
        sys.exit("this card cannot be set:\n   " + "\n   ".join(problems))
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
        if len(cuts) < len(c) - 1:
            # Not enough separated ink to tell the row's elements apart. Give them
            # all the full row: check() then reports what is actually missing,
            # instead of this raising an IndexError on a partial `edges`.
            for name in c:
                out[name] = (0, WIDTH - 1)
            continue
        edges = [0] + cuts + [WIDTH - 1]
        # Sorted by where the values put each element, NOT by the order they were
        # declared in. Those agree today -- the footer declares the wordmark
        # before the url -- and a right-aligned element declared first would
        # silently hand each one the other's window.
        for i, name in enumerate(sorted(c, key=lambda n: anchor[n])):
            out[name] = (edges[i], edges[i + 1])
    return out


# --- The gate ---------------------------------------------------------------

def interior_drift(cols, spans, tol=2.0):
    """Where the ink is, against where the outlines put every glyph.

    Compared as CONTAINMENT, not by aligning runs to spans. Alignment fails in
    both directions on real input. A glyph can draw more than one run -- Space
    Grotesk's `"` is two contour groups 2.4px apart at 64px -- so pairing runs to
    spans rejects a correct quotation mark. And absorbing several spans into one
    run only checks that group's outer edges, so ink flooding a predicted gap
    between two glyphs passes.

    Containment has neither failure. Every drawn column must fall inside some
    predicted glyph, widened by the antialiasing floor; every predicted glyph must
    draw something. Ink in a gap is outside every span. A glyph that walked is
    outside its own. A glyph drawn in pieces is still inside.

    The tolerance is the antialiasing floor, which does NOT scale with type size --
    it is the width of the rasteriser's edge, not a fraction of the glyph. Measured
    on this card, the widest overhang past an outline is 1.00px on the 21px
    eyebrow, 1.10px on the 25px wordmark and 1.31px on the 64px headline, so 2.0px
    sits at roughly twice the observed need at both ends of the scale. A tolerance
    proportional to size would be far too slack on the headline.

    WHAT THIS DOES NOT CATCH, so it is not mistaken for more: a compensating size
    and tracking pair on a monospace string. Eyebrow 20px/.18em against 21px/.14em
    moves the last glyph 1.3px and narrows each by 0.6px, both under the floor.
    That is why the original card's size and tracking were not separately
    recoverable, and only the committed-card comparison sees it.
    """
    have = set(int(c) for c in cols)
    allowed = set()
    for left, right in spans:
        allowed.update(range(int(left - tol), int(right + tol) + 1))
    stray = sorted(have - allowed)
    if stray:
        return (f"{len(stray)} columns of ink where no glyph is predicted, "
                f"x{stray[0]} to x{stray[-1]}")
    for i, (left, right) in enumerate(spans, 1):
        if not any(x in have for x in range(int(left), int(right) + 2)):
            return f"glyph {i} of {len(spans)} drew no ink"
    return None


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
        for edge in ("x0", "x1", "y0", "y1"):
            if abs(got[edge] - want[edge]) > 1.5:
                fails.append(f"{name} {edge} is {got[edge]}, outlines say {want[edge]}")

        drift = interior_drift(got["cols"], spans)
        if drift:
            fails.append(f"{name}: {drift}, while the ink box matches")

        if got["colour"] != ink:
            fails.append(f"{name} ink is {css_colour(got['colour'])}, "
                         f"should be {css_colour(ink)}")

        # How much ink, against the SAME string drawn through this rasteriser at
        # this weight. Placement is a whole-pixel translation of that probe, so the
        # two rasterise identically and the measured difference is 0.00% on every
        # element -- which makes this an ABSOLUTE bound rather than a comparison.
        # A relative "nearer this weight than the other" test cannot see a sparse
        # or partly missing render that stays on the correct side.
        mine, theirs, other = weights[name]
        if mine <= 0:
            fails.append(f"{name}: its probe drew nothing to compare against")
        elif abs(got["area"] - mine) / mine > 0.02:
            fails.append(f"{name}: drew {got['area']:.0f} of ink against {mine:.0f} "
                         f"for the same string at {family} {weight} "
                         f"({100 * (got['area'] - mine) / mine:+.1f}%)")
        elif abs(theirs - mine) / mine <= 0.02:
            # The bound only pins the weight while the weights are separable by it.
            fails.append(f"{name}: {family} {weight} and {other} differ by "
                         f"{100 * abs(theirs - mine) / mine:.1f}%, inside the 2% "
                         f"bound, so this cannot tell them apart")
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


def check_size(arr):
    """The canvas itself, before anything is measured on it.

    Every other check windows into the array, so a card one pixel short passes
    all of them and only fails later, as a numpy shape error inside the report.
    Open Graph consumers reserve a box from og:image:width and height, and
    _config.yml states 1200x630 as fact.
    """
    if arr.shape != (HEIGHT, WIDTH, 3):
        return [f"the card is {arr.shape[1]}x{arr.shape[0]}, and _config.yml's "
                f"og_image says {WIDTH}x{HEIGHT}"]
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
    want = ALT.format(eyebrow=eyebrow, n=NUMBER_WORD[n],
                      wordmark=WORDMARK, url=URL)
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

    The bands PARTITION the card rather than tracking the elements. A band drawn
    around the new elements stops counting where the old card had ink and the new
    one does not, which is precisely what happens when a four-line headline
    becomes one line: the rows the old lines used to occupy go unreported.
    """
    print("\n   against the committed card:")
    a, b = np.asarray(before).astype(np.int16), np.asarray(after).astype(np.int16)
    d = np.abs(a - b).max(axis=2)
    head = [vertical_span(t, ty, bl) for n, t, ty, bl, _al in els if n.startswith("L")]
    top, bottom = int(min(h[0] for h in head)), int(max(h[1] for h in head))
    for key, y0, y1 in [("above the headline", 0, top - 1),
                        ("the headline", top, bottom),
                        ("below the headline", bottom + 1, HEIGHT - 1)]:
        band = d[max(0, y0):min(HEIGHT - 1, y1) + 1]
        print(f"     y{y0}-{y1} ({key}): {int((band > 0).sum())} pixels differ, "
              f"largest change {int(band.max())} of 255")


def main():
    _check_constants()
    preflight()

    problems = fit(EYEBROW, HEADLINE)
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

    fails = (check_size(arr) or
         check(arr, els, placed, weights) + check_rule(arr)
         + check_fringing(arr))
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

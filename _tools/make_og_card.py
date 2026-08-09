"""Replaces the headline in assets/og/default.png, and nothing else.

The share card is a picture of text. The headline is pixels, not markup, so
rewording the h1 leaves every link preview quoting the old claim. Nothing in the
Jekyll build touches the card: it arrived from design as a finished PNG with no
source file, which is why this exists.

This is an AUTHORING step, not a build step, in the same sense README.md already
uses for share cards. Nothing runs at deploy time and the site never depends on
it -- the card is committed, and this only regenerates it.

THE LEADING UNDERSCORE ON _tools/ IS LOAD-BEARING. Jekyll skips entries starting
with `_`, which is why this file needs no entry in `exclude:` the way temp/ does.
Rename the directory to tools/ and the script deploys as a live URL on
pdiggins.com. The note above `exclude:` in _config.yml owns that rule.

WHAT IT DOES

Renders the headline alone in the site's own subset faces and tokens, then
composites that one horizontal band into the committed card. Everything outside
the band is copied through, so the eyebrow, the rule, the wordmark and the URL
cannot move. An earlier version redrew the whole card and silently set the
wordmark 9px narrower; compositing makes that class of drift impossible rather
than merely unlikely.

USING IT

    python _tools/make_og_card.py            # renders and gates; installs nothing
    python _tools/make_og_card.py --write    # also installs assets/og/default.png

To reword: set NEW_LINES to the new copy, broken by hand into the same number of
lines as CURRENT_LINES. Then, AFTER the new card is committed, move BASE_REF to
that commit and set CURRENT_LINES to what the card now says. Those two go
together; the control below fails loudly if they disagree, which is the point.

Line count is not free. The rule and footer are placed under a four-line block,
so a headline broken to three leaves a hole above the rule and makes
`og_image.alt` in _config.yml ("a large four-line headline") false.

WHAT THE CONTROL PROVES, AND WHAT IT NO LONGER PROVES

Before writing, it sets CURRENT_LINES with these same values and checks them
against the card at BASE_REF, per line: left edge and vertical extent within
1px, width within 1%, ink colour exact, ink density within 5%, and the ink
profile correlated above 0.90 on both axes.

For the first card this was a fidelity check: the base was design's own PNG, so
matching it proved these values were the design's values. That is no longer
true. The current card's headline band was produced BY this script, so the
control now proves reproducibility, not fidelity to a design source. Treat the
values below as the design of record until a canonical generator replaces them.

REQUIREMENTS

The CDP harness in temp/: the dark fixture served on 8731 and headless Chrome on
9351. See temp/README.md. Also Pillow, numpy and websocket-client. This tool is
not needed to build or serve the site.
"""
import base64, json, pathlib, subprocess, sys, time, urllib.request
import numpy as np
import websocket
from PIL import Image, ImageChops

PORT = 9351
FIXTURE = "http://127.0.0.1:8731"
ROOT = pathlib.Path(__file__).resolve().parent.parent
SHIPPED = ROOT / "assets/og/default.png"
SERVED = ROOT / "temp/_site_dark"          # the harness fixture this renders through
OUT = ROOT / "temp/og-render"              # scratch; gitignored

# The card this composites onto, pinned to a COMMIT rather than to a branch. A
# moving ref would silently rebase the composite onto whatever the card became,
# and the control would be checking the copy against the wrong card.
BASE_REF = "f96f9a6:assets/og/default.png"

# What the card at BASE_REF currently says, and what it should say next. Equal
# values are the resting state: a run then reproduces the committed card exactly,
# which is a live check that the tool still works.
CURRENT_LINES = ["I build products", "that solve problems",
                 "people have learned", "to work around."]
NEW_LINES = ["I build products", "that solve problems",
             "people have learned", "to work around."]

# Measured off design's original PNG. Not derived from anything, so changing one
# changes the card.
MARGIN = 78
HEAD_SIZE = 64
HEAD_TRACK = -0.03          # the site's own .intro h1 tracking
LINE_PITCH = 69
CAP_TOP = 172               # where line 1's cap-top must land
INK = (233, 231, 228)       # --text
BG = (16, 18, 20)           # --bg

# The composited band: full width, y140 to y469 inclusive. Headline ink runs
# y172-436, and nothing else on the card falls inside it -- the eyebrow ends at
# y95 and the rule sits at y497.
BAND_TOP, BAND_BOTTOM = 140, 469

TEMPLATE = """<!doctype html>
<meta charset="utf-8">
<style>
  @font-face {{ font-family: "Space Grotesk"; font-weight: 400;
    src: url("/assets/fonts/SpaceGrotesk-Regular.woff2") format("woff2"); }}
  html, body {{ margin: 0; padding: 0; }}
  body {{ width: 1200px; height: 630px; background: #101214; position: relative;
         overflow: hidden; -webkit-font-smoothing: antialiased; }}
  .headline {{ position: absolute; white-space: pre; left: {margin}px; top: {top}px;
    font: 400 {size}px/{pitch}px "Space Grotesk";
    letter-spacing: {track}em; color: #e9e7e4; }}
</style>
<div class="headline">{lines}</div>
"""

seq = 0
ws = None


def preflight():
    """Fail with instructions rather than a protocol error deep in a render."""
    if not SERVED.is_dir():
        sys.exit(f"{SERVED} does not exist.\n"
                 f"  Build the fixtures first:  python temp/make-fixtures.py")
    try:
        urllib.request.urlopen(f"{FIXTURE}/assets/fonts/SpaceGrotesk-Regular.woff2",
                               timeout=5)
    except Exception as exc:
        sys.exit(f"{FIXTURE} is not serving the dark fixture ({exc}).\n"
                 f"  python -m http.server 8731 --directory temp/_site_dark")
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=5)
    except Exception as exc:
        sys.exit(f"No headless Chrome on {PORT} ({exc}).\n"
                 f"  See temp/README.md for the launch command.")
    if len(CURRENT_LINES) != len(NEW_LINES):
        sys.exit(f"CURRENT_LINES has {len(CURRENT_LINES)} lines and NEW_LINES has "
                 f"{len(NEW_LINES)}. The rule and footer are placed under a block of "
                 f"a fixed height; changing the count moves them and makes "
                 f"og_image.alt in _config.yml wrong.")
    OUT.mkdir(parents=True, exist_ok=True)


def cmd(method, **params):
    global seq
    seq += 1
    ws.send(json.dumps({"id": seq, "method": method, "params": params}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == seq:
            if "error" in msg:
                raise RuntimeError(f"{method}: {msg['error']}")
            return msg.get("result", {})


def connect():
    global ws
    page = [t for t in json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
            if t["type"] == "page"][0]
    ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=60)
    cmd("Page.enable")
    cmd("Network.enable")
    # style.css and the scratch page are constant URLs; without this a re-run
    # renders the previous copy and reports it as current.
    cmd("Network.setCacheDisabled", cacheDisabled=True)
    cmd("Emulation.setDeviceMetricsOverride", width=1200, height=630,
        deviceScaleFactor=1, mobile=False)


def base_card():
    blob = subprocess.run(["git", "show", BASE_REF], cwd=ROOT,
                          capture_output=True, check=True).stdout
    path = OUT / "base.png"
    path.write_bytes(blob)
    return path


def render(lines, top, name):
    html = TEMPLATE.format(lines="".join(f"<div>{l}</div>" for l in lines),
                           margin=MARGIN, top=top, size=HEAD_SIZE,
                           pitch=LINE_PITCH, track=HEAD_TRACK)
    (SERVED / "og-card.html").write_text(html, encoding="utf-8")
    cmd("Page.navigate", url=f"{FIXTURE}/og-card.html")
    time.sleep(1.6)
    shot = cmd("Page.captureScreenshot", format="png")
    path = OUT / name
    path.write_bytes(base64.b64decode(shot["data"]))
    return Image.open(path).convert("RGB")


def ink_top(img):
    px = img.load()
    for y in range(img.size[1]):
        if any(px[x, y] != BG for x in range(0, 1200, 2)):
            return y
    return None


def line_boxes(img):
    """Ink box of each headline line, measured PER LINE.

    Per line, not per band: an aggregate over the whole headline cannot see one
    line move or resize while the outermost extents stay put, which is how an
    earlier whole-card version redrew the wordmark without failing its own gate.
    """
    px = img.load()
    rows = [y for y in range(BAND_TOP, BAND_BOTTOM + 1)
            if any(px[x, y] != BG for x in range(0, 1200, 2))]
    groups, run = [], []
    for y in rows:
        if run and y != run[-1] + 1:
            groups.append(run)
            run = []
        run.append(y)
    if run:
        groups.append(run)
    out = []
    for g in groups:
        xs = [x for y in g for x in range(1200) if px[x, y] != BG]
        out.append((min(xs), max(xs), g[0], g[-1]))
    return out


def _ink(img, box):
    x0, x1, y0, y1 = box
    a = np.asarray(img.convert("RGB"), dtype=np.int16)[y0:y1 + 1, x0:x1 + 1]
    return np.abs(a - np.array(BG, dtype=np.int16)).max(axis=2) > 24


def ink_density(img, box):
    return int(_ink(img, box).sum())


def ink_colour(img, box):
    x0, x1, y0, y1 = box
    a = np.asarray(img.convert("RGB"))[y0:y1 + 1, x0:x1 + 1].reshape(-1, 3)
    mask = np.abs(a.astype(np.int16) - np.array(BG)).max(axis=1) > 24
    if not mask.any():
        return None
    vals, counts = np.unique(a[mask], axis=0, return_counts=True)
    return tuple(int(v) for v in vals[counts.argmax()])


def _corr(pa, pb):
    """Correlate two ink profiles, resampled to a common length.

    Resampled because two rasterisers differ by a sub-pixel advance, so the boxes
    sit a few pixels apart. Shape is compared, not registration.
    """
    n = 512
    ra = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(pa)), pa)
    rb = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(pb)), pb)
    if ra.std() == 0 or rb.std() == 0:
        return 0.0
    return float(np.corrcoef(ra, rb)[0, 1])


def profile_correlation(img_a, box_a, img_b, box_b):
    """Correlate the lines' ink profiles on BOTH axes, and take the worse.

    Column sums alone are blind to vertical arrangement: flip a line inside its
    own box and the box, the density and every column sum are unchanged, so a
    horizontal-only check returns 1.0 on upside-down type. Row sums are not
    symmetric under that flip, because ascenders and descenders are not mirror
    images.
    """
    ia, ib = _ink(img_a, box_a), _ink(img_b, box_b)
    return min(_corr(ia.sum(axis=0).astype(float), ib.sum(axis=0).astype(float)),
               _corr(ia.sum(axis=1).astype(float), ib.sum(axis=1).astype(float)))


def control(base, top):
    """Set CURRENT_LINES and require them to reproduce the card at BASE_REF.

    Thresholds come from measuring deliberately wrong templates rather than from
    whatever the correct one scored. Measured against design's original card:

      variant                 min corr   max density drift   geometry
      correct                   0.9473               2.4%    ok
      size 60px                 0.9390              12.5%    fails
      size 68px                 0.9381              10.2%    fails
      tracking 0em              0.6555               1.9%    fails
      pitch 63px                0.9473               2.4%    fails
      wrong family (mono)       0.0963              47.8%    fails
      four solid rectangles     0.0000             293.4%    ok
      each line flipped        -0.1237               2.4%    ok

    Geometry alone rejects every wrong size, tracking, pitch and family. The last
    two rows are what geometry cannot see -- right box, wrong marks -- and are
    why correlation takes the worse axis. Separation is 0.9473 against 0.0000 and
    -0.1237, hence the 0.90 and 5% limits.
    """
    rendered = render(CURRENT_LINES, top, "control.png")
    sb, cb = line_boxes(base), line_boxes(rendered)
    fails = []
    if len(sb) != len(cb):
        return [f"line count {len(sb)} on the card vs {len(cb)} rendered"]
    for i, (s, c) in enumerate(zip(sb, cb), 1):
        w_s, w_c = s[1] - s[0], c[1] - c[0]
        drift = abs(w_c - w_s) / w_s
        dens_s, dens_c = ink_density(base, s), ink_density(rendered, c)
        dens_drift = abs(dens_c - dens_s) / dens_s
        corr = profile_correlation(base, s, rendered, c)
        print(f"   L{i}: card x{s[0]}-{s[1]} y{s[2]}-{s[3]}  "
              f"rendered x{c[0]}-{c[1]} y{c[2]}-{c[3]}  width {drift*100:+.2f}%, "
              f"ink {dens_drift*100:+.1f}%, correlation {corr:.4f}")
        if abs(c[0] - s[0]) > 1:
            fails.append(f"L{i} left edge {s[0]} vs {c[0]}")
        if drift > 0.01:
            fails.append(f"L{i} width {w_s} vs {w_c} ({drift*100:.2f}%)")
        if abs(c[2] - s[2]) > 1 or abs(c[3] - s[3]) > 1:
            fails.append(f"L{i} vertical {s[2]}-{s[3]} vs {c[2]}-{c[3]}")
        if ink_colour(rendered, c) != INK:
            fails.append(f"L{i} ink colour {ink_colour(rendered, c)}, expected {INK}")
        if dens_drift > 0.05:
            fails.append(f"L{i} ink density {dens_s} vs {dens_c} ({dens_drift*100:.1f}%)")
        if corr < 0.90:
            fails.append(f"L{i} ink profile correlation {corr:.4f}")
    return fails


def outside_band_identical(a, b):
    diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    px = diff.load()
    bad = []
    for y in range(diff.size[1]):
        if BAND_TOP <= y <= BAND_BOTTOM:
            continue
        for x in range(diff.size[0]):
            if px[x, y] != (0, 0, 0):
                bad.append((x, y))
                if len(bad) > 8:
                    return bad
    return bad


def main():
    preflight()
    connect()
    base_path = base_card()

    # Place line 1's cap-top on CAP_TOP. One pass is exact, since placement is a
    # pure translation; deriving it from font metrics is not, because
    # half-leading rounds per family.
    probe = render(CURRENT_LINES, CAP_TOP, "calibration.png")
    top = CAP_TOP + (CAP_TOP - ink_top(probe))
    print(f"calibration: cap-top landed at {ink_top(probe)}, target {CAP_TOP} -> "
          f"top {top}")

    base = Image.open(base_path).convert("RGB")
    fails = control(base, top)
    if fails:
        print("CONTROL FAILED -- CURRENT_LINES do not reproduce the card at "
              f"{BASE_REF}:")
        for f in fails:
            print("   " + f)
        sys.exit("Either the type values are wrong, or CURRENT_LINES is stale. "
                 "Not writing.")
    print("control: the current copy reproduces the committed card")

    # The base keeps its own mode. The card is RGBA with a uniformly opaque alpha
    # channel; preserving that means the written file differs from the previous
    # one only in the band's pixels, not in its channel layout as well.
    full = Image.open(base_path)
    card = full.copy()
    box = (0, BAND_TOP, 1200, BAND_BOTTOM + 1)
    card.paste(render(NEW_LINES, top, "new-headline.png").crop(box)
               .convert(full.mode), box)

    bad = outside_band_identical(card, full)
    if bad:
        sys.exit(f"GATE FAILED -- {len(bad)}+ pixels changed outside the headline "
                 f"band, first at {bad[:4]}. Not writing.")
    print(f"gate: every pixel outside y{BAND_TOP}-{BAND_BOTTOM} matches the "
          f"committed card")

    if "--write" in sys.argv:
        card.save(SHIPPED)
        print(f"written to {SHIPPED}")
    else:
        card.save(OUT / "composited.png")
        print(f"not installed; preview at {OUT / 'composited.png'} "
              f"(pass --write to install)")


if __name__ == "__main__":
    main()

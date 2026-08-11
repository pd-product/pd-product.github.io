"""Names every character the site renders that its subset faces do not carry.

Both self-hosted families are SUBSET -- that is what keeps each file at 11-12KB
instead of 46KB -- and a character outside the subset does not fail. The browser
silently drops to the next family in the stack, so one glyph mid-word arrives in
a different typeface at a different width. README.md records that behaviour; this
is what finds it.

WHY A BROWSER

The question is not whether the site contains a character the fonts lack. It is
whether a character REACHES a face that lacks it, and only the cascade knows.
Body copy is set in --sans, a system stack with no subset, and cannot fail this
way; the same character in a story title is set in Space Grotesk and can. Reading
the stylesheet to decide which is which duplicates the cascade in a second place
that goes stale the first time a selector moves.

WHAT IT CHECKS

A run is one element's own text, or one pseudo-element's content, including CSS
escapes and attr() values. Each carries its own computed style; they are not
interchangeable. Runs are collected at six viewport widths either side of both
breakpoints, because generated content is breakpoint-dependent. Weight picks the
file. Chrome is asked what it painted at any element with a miss, so a finding
carries the fallback family rather than an inference.

Characters are checked against the FIRST family in the stack and no other. That
is exact while every governed family leads its stack, and wrong the moment one
does not -- CSS matches per character across the whole list. Two invariants
enforce it rather than trusting it, and either failing stops the run:

    a governed family anywhere but first in a computed stack
    a governed family declared by more than one @font-face, or with a
      unicode-range, which makes it a composite face this cannot model

TESTING A CHANGE TO THIS

Plant a character in a face it GOVERNS. Body copy and the mobile tradeoff labels
are --sans and are correctly ignored, so a planted character there produces
silence that means nothing.

NOT COVERED

Text from a CSS counter: `content: counter(x)` yields digits, which both subsets
carry, and the computed value does not expose the resolved string.

USING IT

    python -m http.server 8731 --directory <built site>
    python _tools/check_subset_coverage.py            # every page in the sitemap
    python _tools/check_subset_coverage.py --url http://127.0.0.1:8732

Exits non-zero when anything is found, so it can gate. Needs fontTools,
websocket-client, and the same headless Chrome on 9351 the card generator uses;
see the Tools section of README.md for the launch command. This one does NOT need
--disable-lcd-text: it reads the DOM and never looks at a pixel.
"""
import json
import pathlib
import re
import sys
import time
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET

import websocket
from fontTools.ttLib import TTFont

PORT = 9351
ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets/fonts"

# The two self-hosted families, by the name the stylesheet declares. "Site Mono"
# is a rename the SIL OFL requires for a modified IBM Plex; README.md owns why.
# A family NOT listed here is a system face with no subset and nothing to check.
SELF_HOSTED = {
    "Site Mono": {400: "IBMPlexMono-Regular", 500: "IBMPlexMono-Medium"},
    "Space Grotesk": {400: "SpaceGrotesk-Regular", 500: "SpaceGrotesk-Medium"},
}

# CSS matches family names case-insensitively: `font-family: site mono` selects
# the webfont, and an exact-case lookup would walk past it.
SELF_HOSTED_CI = {name.casefold(): name for name in SELF_HOSTED}

_cmaps = {}


def governed(family):
    """The canonical name for a computed family, or None if we do not host it."""
    return SELF_HOSTED_CI.get(family.strip().strip('"\'').casefold())


def charname(ch):
    """A name for a character this file may not print, and the console may not
    encode. Unicode has no name for a control character, so fall back to the
    code point rather than raising while reporting."""
    return unicodedata.name(ch, f"U+{ord(ch):04X}, unnamed")


def cmap(family, weight):
    """The codepoints one shipped file actually carries."""
    stem = SELF_HOSTED[family][weight]
    if stem not in _cmaps:
        path = FONTS / f"{stem}.woff2"
        if not path.exists():
            raise SystemExit(f"{path} is missing; nothing to check against.")
        _cmaps[stem] = set(TTFont(path).getBestCmap())
    return _cmaps[stem]


def face_weight(css_weight):
    """The site declares 400 and 500 and ships a file for each.

    Anything else is a real problem rather than something to round: a 700 here
    means the browser is synthesising bold from one of these faces, which the
    subset cannot answer for either.
    """
    try:
        w = int(float(css_weight))
    except (TypeError, ValueError):
        return None
    return w if w in (400, 500) else None


_seq = 0


def cmd(ws, method, **params):
    global _seq
    _seq += 1
    ws.send(json.dumps({"id": _seq, "method": method, "params": params}))
    while True:
        r = json.loads(ws.recv())
        if r.get("id") == _seq:
            if "error" in r:
                raise RuntimeError(f"{method}: {r['error']}")
            return r.get("result", {})


# Walks elements rather than text nodes, because the computed font belongs to the
# element. `own` is the element's DIRECT text -- a parent's text and a child's are
# separate runs and can resolve to different faces.
COLLECT = """(() => {
  const out = [];
  const quoted = /"((?:[^"\\\\]|\\\\.)*)"|'((?:[^'\\\\]|\\\\.)*)'/g;
  const attrFn = /attr\\(\\s*([-\\w]+)[^)]*\\)/g;
  const unescape = s => s.replace(/\\\\([0-9a-fA-F]{1,6})\\s?/g,
    (_, h) => String.fromCodePoint(parseInt(h, 16))).replace(/\\\\(.)/g, '$1');
  const path = el => {
    const bits = [];
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      let b = n.tagName.toLowerCase();
      if (n.id) { bits.unshift(b + '#' + n.id); break; }
      if (n.classList.length) b += '.' + n.classList[0];
      bits.unshift(b);
      if (bits.length > 3) break;
    }
    return bits.join(' > ');
  };
  let probe = 0;
  const stacks = [];
  for (const el of document.body.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    // checkVisibility() answers for the ANCESTOR chain. Testing an element's own
    // display only says the element itself was not hidden, so every descendant
    // of a hidden container was still collected and could be reported for text
    // nobody can see. Opacity is deliberately not part of the test: text at zero
    // opacity still selects a face, and .sr-only is clipped rather than hidden
    // and is real text a screen reader reaches.
    if (!el.checkVisibility({ contentVisibilityAuto: true,
                              visibilityProperty: true })) continue;
    // Tagged so a miss can be traced to THIS element and asked what Chrome
    // painted there. A page-wide font list always contains a system face,
    // because the body copy is set in one, and so proves nothing.
    el.setAttribute('data-subset-probe', String(++probe));
    const first = s => s.fontFamily.split(',')[0].trim().replace(/^["']|["']$/g, '');
    let own = '';
    for (const n of el.childNodes) if (n.nodeType === 3) own += n.nodeValue;
    const texts = [];
    if (own.trim()) texts.push(['text', own, first(cs), cs.fontWeight]);
    // A pseudo-element carries its own font. The pager proves it: its anchors
    // are display type and their ::before labels are mono.
    for (const pseudo of ['::before', '::after']) {
      const ps = getComputedStyle(el, pseudo);
      const c = ps.content;
      if (!c || c === 'none' || c === 'normal') continue;
      let m;
      while ((m = quoted.exec(c)) !== null) {
        const lit = unescape(m[1] !== undefined ? m[1] : m[2]);
        if (lit.trim()) texts.push([pseudo, lit, first(ps), ps.fontWeight]);
      }
      quoted.lastIndex = 0;
      // attr() is rendered text set in the pseudo-element's face. The mobile
      // tradeoff labels are built this way and appear in no quoted literal.
      let a;
      while ((a = attrFn.exec(c)) !== null) {
        const v = el.getAttribute(a[1].trim());
        if (v && v.trim()) texts.push([pseudo + ' attr()', v, first(ps), ps.fontWeight]);
      }
      attrFn.lastIndex = 0;
    }
    for (const [where, text, family, weight] of texts) {
      out.push({ family, weight, where, text, path: path(el), probe: probe });
    }
    // Every stack seen, so the first-family assumption can be enforced rather
    // than relied on.
    stacks.push([path(el), cs.fontFamily]);
    for (const pseudo of ['::before', '::after']) {
      stacks.push([path(el) + pseudo, getComputedStyle(el, pseudo).fontFamily]);
    }
  }
  // @font-face is per DOCUMENT, so the faces travel with the page. A face
  // declared on one page only is invisible to a single-page check.
  const faces = [];
  document.fonts.forEach(f => faces.push([f.family, f.weight, f.unicodeRange]));
  return JSON.stringify({ runs: out, stacks: stacks, faces: faces });
})()"""


def pages(base):
    """Every published page, from the site's own sitemap, plus 404.

    The sitemap is the site's own statement of what it publishes, so a page added
    later is covered without editing this. 404.html is deliberately absent from
    it -- it is not a destination -- and is added by hand for that reason.
    """
    try:
        with urllib.request.urlopen(f"{base}/sitemap.xml", timeout=10) as r:
            xml = r.read()
    except Exception as exc:
        raise SystemExit(f"no sitemap at {base}/sitemap.xml ({exc}).\n"
                         f"  Is the BUILT site being served there?")
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [loc.text for loc in ET.fromstring(xml).iterfind(".//s:loc", ns)]
    paths = [re.sub(r"^https?://[^/]+", "", u) or "/" for u in urls]
    return [f"{base}{p}" for p in paths] + [f"{base}/404.html"]


# Generated content is breakpoint-dependent -- the stylesheet has ::before rules
# that only exist below 640 -- so a single width checks a subset of the site and
# calls it the site. These span both breakpoints from either side. The viewport is
# also set EXPLICITLY rather than inherited: this shares a Chrome target with the
# card generator, which leaves it at 1200x630, so an inherited viewport makes the
# result depend on what ran before.
VIEWPORTS = [1280, 961, 960, 641, 640, 390]


def check(ws, url):
    # Scripts stay on. No element in a governed face is invisible at load on any
    # page at any of these widths; the only governed text ever hidden is the
    # tradeoff thead below 640, which is read at the wider viewports here.
    found, seen, stacks, faces = [], set(), {}, {}
    for width in VIEWPORTS:
        cmd(ws, "Emulation.setDeviceMetricsOverride", width=width, height=900,
            deviceScaleFactor=1, mobile=width <= 640)
        cmd(ws, "Emulation.setScrollbarsHidden", hidden=width <= 640)
        cmd(ws, "Page.navigate", url=url)
        time.sleep(1.0)
        cmd(ws, "Runtime.evaluate", expression="document.fonts.ready",
            awaitPromise=True, returnByValue=True)
        got = json.loads(cmd(ws, "Runtime.evaluate", expression=COLLECT,
                             returnByValue=True)["result"]["value"])
        for path, stack in got["stacks"]:
            stacks.setdefault(stack, path)
        # COUNTED PER RENDER, then kept at the highest count any single render
        # showed. A set would collapse two identical @font-face rules into one
        # and make "declared more than once" unfireable for the exact case it
        # names; summing across renders would instead count one declaration six
        # times, once per viewport.
        here = {}
        for family, weight, urange in got["faces"]:
            key = (family, weight, urange)
            here[key] = here.get(key, 0) + 1
        for key, n in here.items():
            faces[key] = max(faces.get(key, 0), n)
        for run in got["runs"]:
            canonical = governed(run["family"])
            if canonical is None:
                continue
            run["family"] = canonical
            weight = face_weight(run["weight"])
            if weight is None:
                key = (run["path"], run["where"], run["weight"])
                if key not in seen:
                    seen.add(key)
                    found.append((run, None, width, "",
                                  f"weight {run['weight']}, which ships no file"))
                continue
            have = cmap(canonical, weight)
            for ch in run["text"]:
                if ch in " \t\n\r":
                    continue
                if ord(ch) in have:
                    continue
                # Deduped across viewports: the same run is collected at each
                # width, and reporting one character six times buries the rest.
                key = (run["path"], run["where"], run["family"], ch)
                if key not in seen:
                    seen.add(key)
                    # Asked at THIS width, while the probe still identifies this
                    # element. Probe numbers are reassigned on every render.
                    found.append((run, ch, width, painted_at(ws, run["probe"]),
                                  None))
    return found, stacks, faces


def painted_at(ws, probe):
    """What Chrome actually painted at the ONE element that has a miss.

    Scoped to that element deliberately. A page-wide font list always contains a
    system face, because the body copy is set in one on purpose, so it reads as
    alarming on a clean page and proves nothing on a dirty one. Asked here, a
    second family IS the fallback, and the glyph counts show how much of the
    element went elsewhere.
    """
    doc = cmd(ws, "DOM.getDocument", depth=-1)
    node = cmd(ws, "DOM.querySelector", nodeId=doc["root"]["nodeId"],
               selector=f'[data-subset-probe="{probe}"]')
    if not node.get("nodeId"):
        return ""
    fonts = cmd(ws, "CSS.getPlatformFontsForNode",
                nodeId=node["nodeId"]).get("fonts", [])
    return ", ".join(f"{f['familyName']} ({f['glyphCount']})" for f in fonts)


def stack_violations(stacks):
    """Stacks where a governed family is NOT first, which this cannot judge.

    The rule here reads entry zero and nothing else, which is sound only while
    every self-hosted family is entry zero. CSS does not guarantee that: the list
    is a set of prioritised alternatives, and a browser walks past an unavailable
    family or one lacking the character. A subset sitting second would then be
    the face that answers, and this would skip it. Reported as a failure rather
    than absorbed, because the alternative is a checker that is quietly wrong
    about the one thing it exists to decide.
    """
    bad = []
    for stack, path in sorted(stacks.items()):
        for i, fam in enumerate(stack.split(",")):
            name = governed(fam)
            if name is not None and i != 0:
                bad.append(f"{path}: {name} is #{i + 1} in {stack!r}")
    return bad


def composite_faces(faces):
    """Governed families delivered as more than one file, which this cannot model.

    Several @font-face rules sharing a family name and differing only by
    `unicode-range` are ONE composite face to CSS, and the computed style still
    names a single family. This maps a family and weight to exactly one file, so
    against a composite face it would check whichever file it holds rather than
    the one the browser chose. The site declares one file per family and weight;
    that is asserted here rather than assumed, for the same reason the first-
    family rule is.

    Takes the per-document counts collected from EVERY page, because @font-face
    is a property of a document.
    """
    seen, bad = {}, []
    for (family, weight, urange), count in sorted(faces.items()):
        name = governed(family)
        if name is None:
            continue
        if urange and urange.replace(" ", "").upper() not in ("U+0-10FFFF", ""):
            bad.append(f"{name} {weight} declares unicode-range {urange!r}, so the "
                       f"family is delivered by more than one file")
        key = (name, weight)
        seen[key] = seen.get(key, 0) + count
    for (name, weight), n in sorted(seen.items()):
        if n > 1:
            bad.append(f"{name} {weight} is declared by {n} @font-face rules")
    return sorted(set(bad))


def main():
    base = "http://127.0.0.1:8731"
    if "--url" in sys.argv:
        base = sys.argv[sys.argv.index("--url") + 1].rstrip("/")
    try:
        targets = [t for t in json.load(
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=5))
            if t["type"] == "page"]
    except Exception as exc:
        raise SystemExit(f"No headless Chrome on {PORT} ({exc}).\n"
                         f"  See the Tools section of README.md for the launch command.")
    # A live endpoint with every tab closed is a different failure from no Chrome
    # at all, and indexing into an empty list reports it as a traceback.
    if not targets:
        raise SystemExit(f"Chrome is on {PORT} but has no page target open.\n"
                         f"  Relaunch it; see the Tools section of README.md.")
    ws = websocket.create_connection(targets[0]["webSocketDebuggerUrl"], timeout=60)
    cmd(ws, "Page.enable")
    cmd(ws, "Runtime.enable")
    cmd(ws, "Network.enable")
    cmd(ws, "Network.setCacheDisabled", cacheDisabled=True)

    cmd(ws, "DOM.enable")
    cmd(ws, "CSS.enable")
    urls = pages(base)
    print(f"{len(urls)} page(s) from {base}, "
          f"at {', '.join(str(w) for w in VIEWPORTS)}px\n")
    total = 0
    all_stacks, all_faces = {}, {}
    for url in urls:
        found, stacks, page_faces = check(ws, url)
        all_stacks.update(stacks)
        for key, n in page_faces.items():
            all_faces[key] = max(all_faces.get(key, 0), n)
        if not found:
            print(f"  ok    {url}")
            continue
        print(f"  FAIL  {url}")
        for run, ch, width, painted, note in found:
            total += 1
            if note:
                print(f"        {run['path']} asks for {note}")
                continue
            # ASCII only: the character being reported is one the console may
            # not encode, and a checker that dies printing its finding is worse
            # than none. The code point and name identify it exactly.
            print(f"        {run['path']} ({run['where']}) sets "
                  f"U+{ord(ch):04X} {charname(ch)}, first seen at {width}px\n"
                  f"        in {run['family']} {run['weight']}, "
                  f"which does not carry it\n"
                  f"        text:    {ascii(run['text'].strip()[:70])}\n"
                  f"        painted: {painted or '(not resolved)'}")
    print()
    violations = stack_violations(all_stacks) + composite_faces(all_faces)
    if violations:
        print("THIS CHECKER'S ASSUMPTION NO LONGER HOLDS:")
        for v in violations:
            print(f"   {v}")
        sys.exit("This maps one family and weight to one file and reads only the "
                 "first family in a stack. Both hold on the site as written, and "
                 "one of them no longer does, so a clean run here would not mean "
                 "what it says. Restore the invariant, or resolve per character "
                 "across the whole stack and per unicode-range across the faces.")
    if total:
        sys.exit(f"{total} character(s) reach a face that does not carry them. "
                 f"Either re-subset with fonttools to include them, or use a "
                 f"character the face already has.")
    print(f"every character the site renders is carried by the face it is set in, "
          f"and every self-hosted family leads its stack")


if __name__ == "__main__":
    main()

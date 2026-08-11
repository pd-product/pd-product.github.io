"""Rebuilds Site Mono from upstream IBM Plex Mono and proves it byte for byte.

Both mono faces in assets/fonts/ are subsets. A subset cannot be checked by
looking at it: it renders every character the site uses whether or not it was
built from the release the design was measured against, and it is still called
"Site Mono" either way. This rebuilds the CURRENT subset from upstream and
compares every decompressed table with the shipped file. That comparison is the
whole point of the script.

THE REPRODUCTION IS THE GATE. Growing the subset is the optional part:

    python _tools/resubset_mono.py                        # prove the shipped face reproduces
    python _tools/resubset_mono.py --add U+2713           # also build one with a codepoint added
    python _tools/resubset_mono.py --add U+2713 --write   # install the grown face

With no --add it builds nothing installable and installs nothing. That run is
still worth making: it answers whether the shipped face is the one this recipe
produces, which is the question no other check in this repo can answer.

The leading underscore on _tools/ is load-bearing; README.md's Tools section
owns that rule.

WHY A BYTE COMPARISON AND NOT A FIELD LIST

Enumerating the fields that "matter" is the mistake this file exists to stop
making. A field list is a guess about what a font carries, and two separate
guesses here both looked thorough and both had holes -- one missed the layout
features and 39 glyphs, the other missed .notdef's outline and the hinting
programs. Neither hole moved a single character the site draws, so nothing that
compared characters could see either one. Comparing all 17 decompressed tables
needs no guess. Everything below the table comparison is diagnostics: it exists
to say WHICH thing moved once the bytes have already said that something did.

UPSTREAM IS FETCHED, NOT COMMITTED

The complete faces are third-party OFL binaries and this repository is all
rights reserved, so they are not committed. They are downloaded once from a
pinned release, verified against a recorded digest, and cached under temp/,
which is gitignored. A digest mismatch is a hard stop rather than a warning: it
means the release no longer serves the bytes this subset was built from, and
every reproduction claim below it would be measured against the wrong face.

The rename to "Site Mono" is required by the SIL OFL, which reserves the name
"Plex" and forbids a modified version -- a subset is one -- from carrying it.
The name table is copied from the shipped file rather than regenerated: it holds
that rename, the "subset" qualifier and the redistribution notice, all written
by hand, and copying it is exact where rebuilding it from flags would be
guesswork.
"""
import hashlib
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request
from collections import Counter

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets/fonts"
CACHE = ROOT / "temp/upstream"
OUT = ROOT / "temp/resubset"
WEIGHTS = ["Regular", "Medium"]

# IBM Plex Mono 2.004, as published in the @ibm/plex npm package. The digests are
# of the complete upstream faces, not of anything this repository ships.
UPSTREAM_RELEASE = "6.4.1"
UPSTREAM_URL = ("https://unpkg.com/@ibm/plex@{release}/IBM-Plex-Mono/fonts/"
                "complete/woff2/IBMPlexMono-{weight}.woff2")
UPSTREAM_SHA256 = {
    "Regular": "49ce58b41a0e1cb921c0f58d9a5b8b96a2cc21437c7066f3ba4f24873076d131",
    "Medium": "8c2c290cbd998fa1f647e4572aca6ebbd72589551b0f3f9f8bb8628fbb8219d5",
}


def upstream(weight):
    """The complete upstream face, cached under temp/ and pinned by digest.

    A cached file whose digest does not match is re-fetched rather than trusted,
    so a truncated download repairs itself. A FETCHED file whose digest does not
    match stops the run: that is upstream having changed under the pin, which no
    script should paper over.
    """
    want = UPSTREAM_SHA256[weight]
    path = CACHE / f"IBMPlexMono-{weight}.woff2"
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == want:
        return path

    url = UPSTREAM_URL.format(release=UPSTREAM_RELEASE, weight=weight)
    print(f"   fetching IBM Plex Mono {UPSTREAM_RELEASE} {weight}")
    try:
        data = urllib.request.urlopen(url, timeout=60).read()
    except (urllib.error.URLError, TimeoutError) as e:
        sys.exit(f"cannot fetch {url}\n"
                 f"  {e}\n"
                 f"  This needs network access once; the file is then cached in "
                 f"{CACHE} and reused.")
    got = hashlib.sha256(data).hexdigest()
    if got != want:
        sys.exit(f"UPSTREAM HAS CHANGED under the pin, refusing to continue.\n"
                 f"  {url}\n"
                 f"  expected sha256 {want}\n"
                 f"  received sha256 {got}\n"
                 f"  The shipped subset was built from the expected bytes. Do not\n"
                 f"  update the pin to match: a different upstream face is a "
                 f"different\n  design, and every comparison below this line would "
                 f"then be measured\n  against it.")
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def facts(path):
    """Everything about a face the site or the card generator depends on."""
    f = TTFont(path)
    gs = f.getGlyphSet()
    cmap = f.getBestCmap()
    out = {"cmap": {}, "adv": {}, "bounds": {}, "upem": f["head"].unitsPerEm,
           "hhea": (f["hhea"].ascent, f["hhea"].descent, f["hhea"].lineGap)}
    hmtx = f["hmtx"]
    for cp, name in cmap.items():
        out["cmap"][cp] = name
        out["adv"][cp] = hmtx[name][0]
        pen = BoundsPen(gs)
        gs[name].draw(pen)
        out["bounds"][cp] = pen.bounds
    out["kern"] = kern_pairs(f, cmap)
    return out


def kern_pairs(f, cmap):
    """Resolved kern values for every ordered pair of MAPPED glyphs.

    Compared because the card generator predicts line geometry from these, so a
    face whose kerning moved would move the committed card without moving a
    single outline. Resolution mirrors OpenType -- first covering subtable wins.
    """
    if "GPOS" not in f:
        return {}
    gp = f["GPOS"].table
    lookups = set()
    fl = gp.FeatureList
    for i in range(fl.FeatureCount):
        if fl.FeatureRecord[i].FeatureTag == "kern":
            lookups.update(fl.FeatureRecord[i].Feature.LookupListIndex)
    subtables = []
    for li in sorted(lookups):
        lk = gp.LookupList.Lookup[li]
        if lk.LookupType != 2:
            continue
        subtables.extend(lk.SubTable)
    names = sorted(set(cmap.values()))
    pairs = {}
    for st in subtables:
        if st.Format == 1:
            for gi, first in enumerate(st.Coverage.glyphs):
                ps = st.PairSet[gi]
                for rec in ps.PairValueRecord:
                    key = (first, rec.SecondGlyph)
                    v = getattr(rec.Value1, "XAdvance", 0) or 0
                    pairs.setdefault(key, v)
        elif st.Format == 2:
            c1 = st.ClassDef1.classDefs
            c2 = st.ClassDef2.classDefs
            cov = set(st.Coverage.glyphs)
            for a in names:
                if a not in cov:
                    continue
                for b in names:
                    rec = st.Class1Record[c1.get(a, 0)].Class2Record[c2.get(b, 0)]
                    v = getattr(rec.Value1, "XAdvance", 0) or 0
                    if v:
                        pairs.setdefault((a, b), v)
    return {k: v for k, v in pairs.items() if k[0] in names and k[1] in names}


def subset(src, dst, codepoints):
    dst.parent.mkdir(parents=True, exist_ok=True)
    unicodes = ",".join(f"U+{c:04X}" for c in sorted(codepoints))
    # --layout-features='*' is not a preference. The shipped face retains the
    # stylistic sets, the alternates and the figure features, which is where its
    # 79 unmapped glyphs come from; the default feature list drops all of them
    # and produces a smaller file that still passes an outline-for-outline
    # comparison. profile() is what notices.
    # --notdef-outline keeps the .notdef box. Without it the subsetter empties
    # that glyph, which no comparison of MAPPED codepoints can see -- .notdef has
    # no codepoint by definition. It is the glyph a reader sees when nothing else
    # matches, so shipping it hollow replaces a visible box with nothing.
    subprocess.run([sys.executable, "-m", "fontTools.subset", str(src),
                    f"--unicodes={unicodes}", "--layout-features=*",
                    "--notdef-outline", "--flavor=woff2",
                    f"--output-file={dst}"], check=True, capture_output=True)


def raw_tables(path):
    """Every table's decompressed bytes, keyed by tag. THE GATE IS THIS."""
    f = TTFont(path, lazy=True)
    return {tag: f.reader[tag] for tag in f.reader.keys()}


def normalise(tag, data):
    """Zeroes the two head fields that CANNOT match and say nothing.

    checkSumAdjustment is a checksum over the whole file, so it changes whenever
    anything else does, and `created`/`modified` are build timestamps. Every
    other byte of head is real: unitsPerEm, macStyle, the global bounding box and
    the flags all change rendering.
    """
    if tag != "head":
        return data
    b = bytearray(data)
    b[8:12] = b"\0\0\0\0"        # checkSumAdjustment
    b[20:36] = b"\0" * 16        # created, modified
    return bytes(b)


def table_diff(before, after, allowed):
    """Tables that differ, minus the ones a change legitimately touches."""
    problems = []
    if set(before) != set(after):
        problems.append(f"table list differs: only-before "
                        f"{sorted(set(before) - set(after))}, only-after "
                        f"{sorted(set(after) - set(before))}")
        return problems
    for tag in sorted(before):
        a, b = normalise(tag, before[tag]), normalise(tag, after[tag])
        if a != b and tag not in allowed:
            problems.append(f"table {tag!r} differs ({len(a)} vs {len(b)} bytes) "
                            f"and nothing in this change should touch it")
    return problems


def signatures(path):
    """One fingerprint per glyph in the file, MAPPED OR NOT.

    A comparison of codepoints leaves every glyph without one unchecked --
    .notdef, and the 79 alternates the stylistic sets reach. Contours, bounds
    and the instruction program are what a subsetter silently drops.
    """
    f = TTFont(path)
    gs = f.getGlyphSet()
    glyf = f["glyf"]
    hmtx = f["hmtx"]
    out = {}
    for name in f.getGlyphOrder():
        pen = BoundsPen(gs)
        gs[name].draw(pen)
        g = glyf[name]
        program = getattr(g, "program", None)
        out[name] = (g.numberOfContours, pen.bounds, hmtx[name][0],
                     len(program.getBytecode()) if program else 0)
    return out


def profile(path):
    """The shape of the FILE, not of its outlines.

    A subset can match every glyph the site draws and still be a different
    delivery: fewer glyphs behind the features, a dropped feature list, hinting
    stripped. None of that moves a shipped character, so nothing else here sees
    it -- and the file getting SMALLER while gaining a codepoint is the tell.
    """
    f = TTFont(path)

    def feats(tag):
        if tag not in f:
            return []
        fl = f[tag].table.FeatureList
        return sorted({fl.FeatureRecord[i].FeatureTag for i in range(fl.FeatureCount)})

    return {"glyphs": f["maxp"].numGlyphs, "tables": sorted(f.keys()),
            "GSUB": feats("GSUB"), "GPOS": feats("GPOS"),
            "hinting": [t for t in ("fpgm", "prep", "cvt ") if t in f]}


def copy_names(donor, target):
    """The shipped name table, verbatim, including the OFL rename and notice."""
    d, t = TTFont(donor), TTFont(target)
    t["name"] = d["name"]
    t.save(target)


def compare(a, b, label):
    problems = []
    if set(a["cmap"]) != set(b["cmap"]):
        only_a = sorted(set(a["cmap"]) - set(b["cmap"]))
        only_b = sorted(set(b["cmap"]) - set(a["cmap"]))
        problems.append(f"codepoint sets differ: "
                        f"shipped-only {[f'U+{c:04X}' for c in only_a]}, "
                        f"rebuilt-only {[f'U+{c:04X}' for c in only_b]}")
        return problems
    for cp in sorted(a["cmap"]):
        if a["adv"][cp] != b["adv"][cp]:
            problems.append(f"U+{cp:04X} advance {a['adv'][cp]} vs {b['adv'][cp]}")
        if a["bounds"][cp] != b["bounds"][cp]:
            problems.append(f"U+{cp:04X} outline bounds {a['bounds'][cp]} vs "
                            f"{b['bounds'][cp]}")
    for k in ("upem", "hhea"):
        if a[k] != b[k]:
            problems.append(f"{k} {a[k]} vs {b[k]}")
    if a["kern"] != b["kern"]:
        ka, kb = a["kern"], b["kern"]
        diff = [k for k in set(ka) | set(kb) if ka.get(k) != kb.get(k)]
        problems.append(f"{len(diff)} kern pair(s) differ, e.g. "
                        f"{[(k, ka.get(k), kb.get(k)) for k in sorted(diff)[:4]]}")
    return problems


def parse_add(argv):
    """The codepoints named by --add, as ints. `U+2713`, `2713` and `0x2713`."""
    out = []
    for i, a in enumerate(argv):
        if a != "--add":
            continue
        if i + 1 >= len(argv):
            sys.exit("--add needs a codepoint, e.g. --add U+2713")
        raw = argv[i + 1]
        text = raw[2:] if raw[:2].lower() in ("u+", "0x") else raw
        try:
            out.append(int(text, 16))
        except ValueError:
            sys.exit(f"--add {raw}: not a hex codepoint. Write it as U+2713.")
    return out


def reproduce(weight, shipped, source):
    """Rebuild the shipped codepoints and report everything that differs."""
    have = facts(shipped)
    codepoints = set(have["cmap"])
    same = OUT / f"reproduce-{weight}.woff2"
    subset(source, same, codepoints)
    copy_names(shipped, same)

    problems = compare(have, facts(same), weight)
    shape_before, shape_after = profile(shipped), profile(same)
    for key in ("glyphs", "tables", "GSUB", "GPOS", "hinting"):
        if shape_before[key] != shape_after[key]:
            problems.append(f"{key}: shipped {shape_before[key]} vs "
                            f"rebuilt {shape_after[key]}")
    sig_before, sig_after = signatures(shipped), signatures(same)
    for name in sorted(set(sig_before) | set(sig_after)):
        if sig_before.get(name) != sig_after.get(name):
            problems.append(f"glyph {name}: {sig_before.get(name)} vs "
                            f"{sig_after.get(name)}")
    # Nothing may differ in a rebuild of the SAME codepoints. No allowlist.
    raw_shipped = raw_tables(shipped)
    problems += table_diff(raw_shipped, raw_tables(same), allowed=set())
    return have, codepoints, raw_shipped, sig_before, shape_before, problems


def grow(weight, shipped, source, have, codepoints, raw_shipped, sig_before,
         shape_before, add):
    """Build the subset with `add` included and report what moved that should not."""
    grown = OUT / f"IBMPlexMono-{weight}.woff2"
    subset(source, grown, codepoints | set(add))
    copy_names(shipped, grown)
    after = facts(grown)
    added = sorted(set(after["cmap"]) - codepoints)

    kept = compare(have,
                   {**after,
                    "cmap": {c: after["cmap"][c] for c in codepoints},
                    "adv": {c: after["adv"][c] for c in codepoints},
                    "bounds": {c: after["bounds"][c] for c in codepoints},
                    "kern": {k: v for k, v in after["kern"].items()
                             if k in have["kern"]}}, weight)
    print(f"   with {', '.join(f'U+{c:04X}' for c in sorted(add))}: added "
          f"{[f'U+{c:04X}' for c in added]}, {grown.stat().st_size} bytes "
          f"against {shipped.stat().st_size}")
    # Compared as a MULTISET of fingerprints rather than by name. Adding a glyph
    # can renumber the generic glyph000NN names the subsetter mints, so matching
    # by name would report the whole tail as changed.
    grew = Counter(signatures(grown).values()) - Counter(sig_before.values())
    shrank = Counter(sig_before.values()) - Counter(signatures(grown).values())
    if shrank:
        kept.append(f"{sum(shrank.values())} glyph(s) present before are gone: "
                    f"{list(shrank)[:3]}")
    if sum(grew.values()) != len(add):
        kept.append(f"expected exactly {len(add)} new glyph(s), got "
                    f"{sum(grew.values())}: {list(grew)[:3]}")
    # The FILE's shape, which the byte allowlist below cannot police. Adding a
    # codepoint must not change the table list, drop a layout feature or strip
    # the hinting programs, and must move the glyph count by exactly what was
    # asked for.
    shape_after = profile(grown)
    for key in ("tables", "GSUB", "GPOS", "hinting"):
        if shape_before[key] != shape_after[key]:
            kept.append(f"{key}: shipped {shape_before[key]} vs grown "
                        f"{shape_after[key]}")
    if shape_after["glyphs"] != shape_before["glyphs"] + len(add):
        kept.append(f"glyph count {shape_before['glyphs']} -> "
                    f"{shape_after['glyphs']}, expected +{len(add)}")

    # THIS LIST WAS MEASURED, NOT REASONED OUT, and the difference matters: an
    # earlier list of six was derived from a single added arrow and silently did
    # not generalise. Building the same subset with and without one added
    # codepoint, for three characters in three different blocks:
    #
    #     U+20AC  GSUB OS/2 cmap glyf head hmtx loca maxp
    #     U+2022  GSUB      cmap glyf head hmtx loca maxp
    #     U+00E9  GSUB GDEF cmap glyf head hmtx loca maxp
    #
    # so GSUB always moves, and OS/2 or GDEF move depending on which block the
    # character sits in and whether it carries mark data. Widening the list this
    # far would cost the gate its teeth on its own -- which is what the shape
    # comparison above is for. It checks the feature TAGS, the table list and
    # the hinting inside the three tables this list now waves through.
    kept += table_diff(raw_shipped, raw_tables(grown),
                       allowed={"head", "maxp", "hmtx", "cmap", "loca", "glyf",
                                "GSUB", "GDEF", "OS/2"})
    return kept


def main():
    add = parse_add(sys.argv[1:])
    write = "--write" in sys.argv
    if write and not add:
        sys.exit("--write installs the grown face, so it needs at least one "
                 "--add.\n  With no --add the rebuild is the shipped file; there "
                 "is nothing to install.")

    # Why the run failed, not just that it did. These three fail for unrelated
    # reasons and a single message for all of them names the wrong cause: a
    # codepoint that is already shipped says nothing about the reproduction,
    # which by then has already passed.
    reasons = set()
    ok = True
    for weight in WEIGHTS:
        shipped = FONTS / f"IBMPlexMono-{weight}.woff2"
        print(f"{weight}:")
        source = upstream(weight)
        have, codepoints, raw_shipped, sig_before, shape_before, problems = (
            reproduce(weight, shipped, source))
        print(f"   rebuilding the CURRENT {len(codepoints)} codepoints from "
              f"upstream")
        if problems:
            ok = False
            reasons.add("the rebuild does not reproduce the shipped face")
            for p in problems[:8]:
                print(f"   MISMATCH  {p}")
        else:
            print(f"   reproduces the shipped file: all {len(raw_shipped)} "
                  f"tables byte-for-byte, bar head's checksum and build "
                  f"timestamp")

        if not add:
            continue
        # Asked for BEFORE subsetting. fontTools.subset does not complain about a
        # codepoint the source face lacks -- it just produces a subset without
        # it, and the only downstream symptom is a glyph count that came up
        # short. That reads as the subsetter having dropped something, which is a
        # different and much more alarming problem than the real one.
        missing = sorted(c for c in add
                         if c not in TTFont(source).getBestCmap())
        if missing:
            ok = False
            reasons.add("a requested codepoint is not in the upstream face")
            print(f"   NOT IN UPSTREAM  "
                  f"{', '.join(f'U+{c:04X}' for c in missing)} is absent from "
                  f"IBM Plex Mono {UPSTREAM_RELEASE} itself, so no subset of it "
                  f"can carry that character")
            continue
        already = sorted(c for c in add if c in codepoints)
        if already:
            ok = False
            reasons.add("a requested codepoint is already in the shipped face")
            print(f"   ALREADY PRESENT  "
                  f"{', '.join(f'U+{c:04X}' for c in already)} is in the shipped "
                  f"face; there is nothing to add")
            continue
        kept = grow(weight, shipped, source, have, codepoints, raw_shipped,
                    sig_before, shape_before, add)
        if kept:
            ok = False
            reasons.add("growing the subset moved something it should not have")
            for p in kept[:8]:
                print(f"   REGRESSION  {p}")
        else:
            print("   every previously shipped codepoint is unchanged, and "
                  "every glyph fingerprint survives with exactly "
                  f"{len(add)} added")

    if not ok:
        raise SystemExit("\nrefusing to install: " + "; ".join(sorted(reasons)) + ".")
    if write:
        for weight in WEIGHTS:
            (FONTS / f"IBMPlexMono-{weight}.woff2").write_bytes(
                (OUT / f"IBMPlexMono-{weight}.woff2").read_bytes())
            print(f"installed assets/fonts/IBMPlexMono-{weight}.woff2")
    elif add:
        print(f"\nnot installed; built in {OUT} (pass --write to install)")
    else:
        print("\nverify only; nothing built to install")


if __name__ == "__main__":
    main()

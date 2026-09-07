"""Feeds the card generator values that are WRONG, and reports any it accepts.

A checker that passes everything proves nothing about the values it guards, and
that is the recurring defect in this repo rather than a hypothetical one. Each
probe below is a mistake an author could actually make; the pass condition is
that the tool refuses it AND that it still accepts the copy the card ships. A
run with no controls would go green on a gate that refuses everything.

Reads _config.yml and writes only into temp/. The repo file is never edited --
check_alt is pointed at a doctored copy instead.
"""
import importlib.util
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("og", ROOT / "_tools/make_og_card.py")
og = importlib.util.module_from_spec(spec)
spec.loader.exec_module(og)

EYEBROW, HEADLINE = og.EYEBROW, og.HEADLINE
failures = []


def probe(name, held, detail="", want="refused"):
    """`held` is whether the tool did what this probe wanted, not whether it refused.

    Printed as the outcome rather than as pass/fail, because a control wants the
    value ACCEPTED and a run that labels that "refused" reads as the gate firing
    on the shipped copy.
    """
    got = want if held else ("accepted" if want == "refused" else "REFUSED")
    print(f"  {got:>8}  {name}")
    if detail:
        print(f"              {detail}")
    if not held:
        failures.append(name)


print("fit(), against the 690px measure:")

def reach_of(line):
    """Where the ink ENDS, from the column's left edge -- what fit() measures."""
    spans = og.glyph_spans(line, og.HEAD_TYPE, og.COL_LEFT)[0]
    return spans[-1][1] - og.COL_LEFT


# THE BOUNDARY, not a line far past it. A cap that refuses nothing is the failure
# mode the comment on MAX_LINE_REACH names, and a probe 165px over the cap would
# be refused by any cap between 640 and 855 -- so it would pass while proving
# nothing about the value actually in force. The line is grown one letter at a
# time until it just crosses.
line = "Often solving problems"
while reach_of(line) <= og.MAX_LINE_REACH:
    line += "s"
probe(f"a line reaching {reach_of(line):.0f}px, just over the {og.MAX_LINE_REACH}px measure",
      bool(og.fit(EYEBROW, ["Always learning.", line])), repr(line))

# And the other side of it. The shipped L2 sets 681px, just under the cap, so the
# control below is also the under-boundary case -- named here because that is
# easy to miss, and a boundary tested from one side only is half tested.
probe(f"(control) a line reaching {reach_of(HEADLINE[-1]):.0f}px, just under it",
      not og.fit(EYEBROW, ["Always learning.", HEADLINE[-1]]), want="accepted")

# The span-versus-reach hole. Leading spaces leave the ink SPAN identical while
# moving the whole line right, so a measure written as last_ink - first_ink
# accepts a line that crosses the column and even one that leaves the canvas --
# and the per-element checks agree, because they predict from the same shift.
for n in (1, 25, 40):
    shifted = " " * n + "Often solving problems."
    right = og.glyph_spans(shifted, og.HEAD_TYPE, og.COL_LEFT)[0][-1][1]
    where = ("off the 1200px canvas" if right > og.WIDTH else
             f"past the column's right edge at {og.COL_RIGHT}" if right > og.COL_RIGHT
             else "still inside the column, but into the air the measure protects")
    probe(f"{n} leading space(s), ink ending at {right:.0f}px -- {where}",
          bool(og.fit(EYEBROW, ["Always learning.", shifted])))
probe("a trailing space",
      bool(og.fit(EYEBROW, ["Always learning.", "Often solving problems. "])))

probe("six lines, over the five-line ceiling",
      bool(og.fit(EYEBROW, ["one", "two", "three", "four", "five", "six"])))
probe("an empty headline", bool(og.fit(EYEBROW, [])))
probe("an eyebrow of nothing but spaces", bool(og.fit("   ", HEADLINE)))
# U+00E9, written as an escape because source here is ASCII-only. NOT an em dash:
# the Space Grotesk subset carries U+2014 as one of its five non-ASCII extras, so
# an em-dash probe passes the tool and proves nothing. Verified against the
# shipped cmap, which holds U+00A0, U+00B7, U+2013, U+2014 and U+2019 and no
# accented latin at all.
probe("a character the subset face does not carry",
      bool(og.fit(EYEBROW, ["Always learning.", "Often r\u00e9solving problems."])),
      "U+00E9, which the subset does not hold")
probe("copy the face substitutes as a ligature",
      bool(og.fit(EYEBROW, ["Always fitting.", "Often solving problems."])),
      "'fi' in 'fitting'")

# The line the card actually sets must still be accepted, or the probes above
# are passing for the wrong reason.
probe("(control) the copy the card ships",
      not og.fit(EYEBROW, HEADLINE), want="accepted")
if og.fit(EYEBROW, HEADLINE):
    failures.append("the shipped copy is refused")

print("\ncheck_alt(), against a doctored _config.yml:")
doctored = ROOT / "temp/probe-config.yml"
real = (ROOT / "_config.yml").read_text(encoding="utf-8")
og.CONFIG = doctored

CASES = [
    ("a stale line count", "two-line headline", "three-line headline"),
    ("a stale eyebrow", "reading building with ai", "reading solving problems with ai"),
    ("a stale wordmark", "the name pat diggins", "the name p diggins"),
    ("a stale url", "and pdiggins.com along", "and pd-product.github.io along"),
]
for name, find, replace in CASES:
    if find not in real:
        probe(name, False, f"probe is stale: {find!r} is not in _config.yml")
        continue
    doctored.write_text(real.replace(find, replace), encoding="utf-8")
    probe(name, bool(og.check_alt(len(HEADLINE), EYEBROW)))

doctored.write_text(real, encoding="utf-8")
probe("(control) the alt _config.yml ships",
      not og.check_alt(len(HEADLINE), EYEBROW), want="accepted")
doctored.unlink()

print()
if failures:
    raise SystemExit(f"{len(failures)} wrong value(s) got through: {failures}")
print("every wrong value was refused, and the shipped values were not")

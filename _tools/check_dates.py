"""Lists what each page claims about its last change, next to what git shows.

`last_modified_at` drives the JSON-LD `dateModified` and the sitemap's `lastmod`,
it is updated by hand, and forgetting it is silent: the page goes on telling
search engines it has not changed since the day it was published. This is the
reminder.

    python _tools/check_dates.py

ADVISORY, AND DELIBERATELY DUMB. It compares dates, not pages. It cannot tell a
content edit from a comment edit, so a flagged page may be perfectly fine -- the
job is to make you look, not to be right. Clear a flag either by bumping the date
or by satisfying yourself the commit changed nothing a reader sees.

A version of this that could tell the difference was built and thrown away. It
had to build the site once per commit to do it, and it ended up several times the
size of the four dates it was guarding. For three stories that is the wrong
trade; the comparison below is worth about a tenth as much and costs about a
hundredth. If the story count ever grows enough to change that arithmetic, the
approach that worked was to render each candidate commit and compare the page
rather than the source.
"""
import datetime
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ["_data/off-hours.yml", "_data/path-here.yml"]


def stories():
    return sorted(f"_work/{p.name}" for p in ROOT.glob("_work/*.md"))


def sources(page):
    """The home page prints every story's title and lesson, so a story dates it."""
    return ["index.html"] + DATA + stories() if page == "index.html" else [page]


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True).stdout


def since_declared(page, paths):
    """(date, sha, path) of the newest change SINCE this page's date was last set.

    The question is not "when was this file last touched" -- answering that leaves
    the tool permanently red, because the commit that writes the date is itself a
    touch, and so is any later comment tidy. The question is "has anything changed
    since I last declared a date", which settles everything before that commit by
    construction and needs no baseline to be maintained by hand.

    It also makes the tool self-clearing. Look at a flag, decide the commit was
    cosmetic, and there is nothing to do but re-declare the same date -- which
    moves the marker forward and turns it green, with the decision recorded in
    history rather than in someone's memory.
    """
    anchor = git("log", "-1", "--format=%H", "-S", "last_modified_at", "--", page).strip()
    span = f"{anchor}..HEAD" if anchor else "HEAD"
    best = None
    for p in paths:
        out = git("log", "-1", "--format=%ad %h", "--date=short", span, "--", p)
        if out.strip():
            date, sha = out.split()
            if best is None or date > best[0]:
                best = (date, sha, p)
    if best:
        return best
    # Nothing committed since. An uncommitted edit that leaves the date line alone
    # is the same situation one commit earlier, and is the state you are actually
    # in when you have just revised a story.
    for p in paths:
        if git("diff", "--", p).strip() and not git("diff", "-S", "last_modified_at",
                                                    "--", p).strip():
            return (datetime.date.today().isoformat(), "uncommitted", p)
    return ("", "", "")


def main():
    problems = []
    print("page                            says         changed since that date")
    for page in ["index.html"] + stories():
        text = (ROOT / page).read_text(encoding="utf-8")
        if re.search(r"^published:\s*false", text, re.M):
            continue
        m = re.search(r"^last_modified_at:\s*(\S+)", text, re.M)
        says = m.group(1).strip("\"'") if m else None
        when, sha, via = since_declared(page, sources(page))
        note = "" if via == page else f"  via {via}"

        if says is None:
            state = "MISSING"
            problems.append(f"{page}: no last_modified_at")
        elif not valid(says):
            state = "MALFORMED"
            problems.append(f"{page}: {says!r} is not a real YYYY-MM-DD date")
        elif says > datetime.date.today().isoformat():
            state = "FUTURE"
            problems.append(f"{page}: says {says}, which has not happened yet")
        elif says < when:
            state = "LOOK"
            problems.append(f"{page}: {via} changed {when} ({sha}), after this date "
                            f"was set. Bump it, or re-declare the same date if that "
                            f"change was cosmetic.")
        else:
            state = "ok"
        shown = f"{when} ({sha}){note}" if when else "nothing"
        print(f"  {page:30} {says or '-':12} {shown:34} {state}")

    if problems:
        print()
        for p in problems:
            print(f"  {p}")
        raise SystemExit(f"\n{len(problems)} page(s) worth a look.")
    print("\nnothing has changed since these dates were declared")


def valid(text):
    try:
        return datetime.date.fromisoformat(text).isoformat() == text
    except ValueError:
        return False


if __name__ == "__main__":
    main()

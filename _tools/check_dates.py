"""Finds pages whose `last_modified_at` is older than their content.

Every page here declares two dates and they answer different questions. `date`
is when the page was published and never moves. `last_modified_at` is when its
content last changed, and it is the one a person has to remember -- which is why
this exists. Forgetting it is otherwise silent: the page keeps telling search
engines it has not changed since the day it went up, the sitemap keeps saying
there is nothing to re-read, and nothing on the page looks wrong.

    python _tools/check_dates.py

No browser, no server, no build. It reads the working tree and git history.

WHY BOTH FIELDS EXIST

jekyll-seo-tag and jekyll-sitemap read the same key, so one field feeds both:
seo-tag falls back `seo.date_modified` -> `last_modified_at` -> `date` for the
JSON-LD `dateModified`, and jekyll-sitemap uses `last_modified_at | default:
date` for a collection document's `<lastmod>`. With `last_modified_at` unset,
BOTH silently answer the modification question with the publication date -- so a
revised story reports itself unrevised in two places at once, and they agree with
each other, which is what makes it look right.

A regular page such as index.html is different again: jekyll-sitemap emits
`<lastmod>` for it ONLY if `last_modified_at` is set. Without it the page has no
freshness signal at all rather than a wrong one.

WHAT COUNTS AS A CONTENT CHANGE

Not "the file was touched". Comments do not reach the page, and neither does
reformatting, so a commit that only reworded a comment must not make a date look
stale -- otherwise the check cries wolf and gets ignored, which is worse than not
having it. `content_hash` strips what cannot render:

    - YAML `#` comment lines inside the front matter block
    - Liquid `{% comment %}` blocks
    - HTML comments
    - blank lines and trailing whitespace

That is a real distinction and not a theoretical one: the commit that promoted
these tools reworded comments in all four pages and changed the rendered bytes of
none of them.

The working tree is checked too, not just history. The moment you need this is
BEFORE committing a revision, when git has not seen it yet.
"""
import hashlib
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORIES = sorted(ROOT.glob("_work/*.md"))

# What each page's content is made of. A page is stale if ANY of its sources
# changed after its declared date -- the home page prints each story's title,
# lesson and category, so revising a story revises the home page too, and the
# two data files are the Off hours and The path here sections outright.
#
# SITE CHROME IS DELIBERATELY OUT OF SCOPE, and this is a boundary rather than an
# oversight. `_config.yml`, `_includes/nav.html`, `_includes/footer.html` and the
# layouts all reach the rendered page, but they reach EVERY page: treating them
# as sources would date every page in the site on any nav or footer edit, which
# is both untrue -- the content did not change -- and useless, because a signal
# that fires on everything carries nothing. `lastmod` and `dateModified` are
# claims about the document, not about the site it sits in. The cost is real and
# worth naming: reword a nav label or a contact link and no date moves.
DATA = ["_data/off-hours.yml", "_data/path-here.yml"]


def sources(page):
    if page == "index.html":
        return ["index.html"] + DATA + [f"_work/{s.name}" for s in STORIES]
    return [page]


def git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def content_hash(text):
    """A fingerprint of only what can reach the rendered page."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        end = next((i for i, l in enumerate(lines[1:], 1) if l.strip() == "---"), None)
        if end is not None:
            # `last_modified_at` is excluded from the fingerprint of the thing it
            # describes, or the check eats its own tail: writing the date is a
            # front-matter edit, so it would count as a content change, so the
            # date you just wrote would be stale the moment you wrote it, and the
            # only way to satisfy the check would be a date that is always today.
            front = [l for l in lines[1:end]
                     if not l.lstrip().startswith("#")
                     and not l.lstrip().startswith("last_modified_at:")]
            body = "\n".join(lines[end + 1:])
        else:
            front, body = [], text
    else:
        front, body = [], text
    body = re.sub(r"\{%-?\s*comment\s*-?%\}.*?\{%-?\s*endcomment\s*-?%\}", "",
                  body, flags=re.S)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    joined = "\n".join(l.rstrip() for l in ("\n".join(front) + "\n" + body).splitlines()
                       if l.strip())
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def last_content_change(path):
    """(date, sha) of the newest commit that changed what this file renders.

    Returns ("uncommitted", None) when the working tree already differs, because
    that is the state you are in when you have just revised a story and are about
    to be told you forgot the date.
    """
    disk = (ROOT / path).read_text(encoding="utf-8")
    log = [c.split() for c in git("log", "--format=%H %ad", "--date=short",
                                  "--", path).split("\n") if c.strip()]
    if not log:
        return "uncommitted", None
    if content_hash(git("show", f"{log[0][0]}:{path}")) != content_hash(disk):
        return "uncommitted", None
    for sha, date in log:
        cur = content_hash(git("show", f"{sha}:{path}"))
        parent = git("show", f"{sha}^:{path}")
        if not parent or content_hash(parent) != cur:
            return date, sha[:7]
    return log[-1][1], log[-1][0][:7]


def declared(path):
    """The page's `last_modified_at`, read without a YAML parser.

    Deliberately literal: this checks what is WRITTEN in the file, so a value the
    parser would coerce -- an unquoted date, a quoted one, a stray time -- is
    reported as it stands rather than normalised into looking correct.
    """
    text = (ROOT / path).read_text(encoding="utf-8")
    m = re.search(r"^last_modified_at:\s*(\S+)", text, re.M)
    return m.group(1).strip('"\'') if m else None


def main():
    pages = ["index.html"] + [f"_work/{s.name}" for s in STORIES]
    problems = []
    print("page                            declared     content last changed")
    for page in pages:
        text = (ROOT / page).read_text(encoding="utf-8")
        if re.search(r"^published:\s*false", text, re.M):
            print(f"  {page:30} -            (published: false, skipped)")
            continue
        says = declared(page)
        changes = [(p, *last_content_change(p)) for p in sources(page)]
        newest = max(changes, key=lambda c: ("9999" if c[1] == "uncommitted" else c[1]))
        when, sha = newest[1], newest[2]
        via = "" if newest[0] == page else f"  via {newest[0]}"
        if says is None:
            state = "MISSING"
            problems.append(f"{page}: no last_modified_at")
        elif when == "uncommitted":
            state = "UNCOMMITTED"
            problems.append(f"{page}: {newest[0]} has uncommitted content changes; "
                            f"set last_modified_at to the day you commit them")
        elif says < when:
            state = "STALE"
            problems.append(f"{page}: says {says}, content changed {when} ({sha})"
                            f"{via}")
        else:
            state = "ok"
        print(f"  {page:30} {says or '-':12} {when}{' (' + sha + ')' if sha else ''}"
              f"{via}   {state}")

    if problems:
        print()
        for p in problems:
            print(f"  {p}")
        raise SystemExit(f"\n{len(problems)} page(s) misreport when they last changed.")
    print("\nevery page's last_modified_at is at or after its last content change")


if __name__ == "__main__":
    main()

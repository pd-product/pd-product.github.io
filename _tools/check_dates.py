"""Finds pages whose `last_modified_at` is older or newer than their content.

Every page here declares two dates and they answer different questions. `date` is
when the page was published and never moves. `last_modified_at` is when its
content last changed, and it is the one a person has to remember -- which is why
this exists. Forgetting it is otherwise silent: the page keeps telling search
engines it has not changed since the day it went up, the sitemap keeps saying
there is nothing to re-read, and nothing on the page looks wrong.

    python _tools/check_dates.py

No browser and no server. It does run Jekyll, repeatedly, which is the whole
method -- see below.

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

IT BUILDS THE PAGE RATHER THAN READING THE SOURCE

The question "did the content change" cannot be answered by looking at the file,
and the first version of this script tried anyway. It stripped YAML comments,
Liquid comments, HTML comments and whitespace, on the theory that what remained
was what rendered. Every one of those rules was wrong somewhere:

    - `_data/*.yml` has no front matter, so its `#` comments were never stripped
      at all and editing one dated the home page.
    - Rewrapping a paragraph changed the fingerprint; Markdown renders it the
      same.
    - HTML comments do NOT reliably vanish. Liquid executes inside them -- the
      comment on `{% seo %}` in index.html records a tag that expanded inside a
      `<!-- -->` block and closed the comment early, leaking text onto the page.
    - The home page's dependencies had to be listed by hand, so an unpublished
      template counted as a source and a story's BODY dated a page that never
      prints it.

Each fix was a better guess about the renderer. The renderer is right there, so
this asks it instead: take the current tree, swap in the page's source files as
they were at a given commit, build, and compare what the page actually renders.
Nothing needs to know which syntax is a comment.

Isolating content from presentation falls out of the same trick. Templates,
layouts, includes and config stay at their CURRENT versions in every build, so
only the authored sources vary between two runs. A layout change therefore does
not date anything -- `lastmod` and `dateModified` are claims about a document,
not about the site design around it.

WHAT IS COMPARED

`<main>`, plus the page's `<title>` and meta description. That is the page's own
content and its own search-visible metadata. Site chrome -- the header, nav and
footer -- sits outside `<main>` and is excluded, deliberately: those reach every
page, so a nav edit would date the whole site at once, which is both untrue and
useless. The `<head>` is otherwise excluded because it carries the very dates
being checked, and a fingerprint that included them would change every time the
answer was written down.
"""
import datetime
import hashlib
import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
STAGE = ROOT / "temp/_dates/stage"
GEMFILE = ROOT / "temp/Gemfile"

# The authored sources behind each page. Everything else -- layouts, includes,
# _config.yml, the stylesheet -- is held at its current version, so it cannot
# move a date.
DATA = ["_data/off-hours.yml", "_data/path-here.yml"]


def stories():
    return sorted(f"_work/{p.name}" for p in ROOT.glob("_work/*.md"))


def sources(page):
    """Which files, if changed, could change what this page renders.

    The home page prints every published story's title, lesson and category, so a
    story is one of its sources. It does not print their bodies -- but this list
    does not need to know that, because the comparison is of rendered output and
    a body edit simply does not move it.
    """
    return ["index.html"] + DATA + stories() if page == "index.html" else [page]


def built_path(page):
    if page == "index.html":
        return "index.html"
    return f"work/{pathlib.Path(page).stem}/index.html"


def git(*args, binary=False):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                       text=not binary)
    return (r.stdout if r.returncode == 0 else (b"" if binary else ""))


def stage_tree():
    """A build-ready copy of the CURRENT tree, made once and reused."""
    if STAGE.exists():
        shutil.rmtree(STAGE, ignore_errors=True)
    STAGE.mkdir(parents=True)
    for rel in git("ls-files").split("\n"):
        if not rel.strip() or rel.startswith("temp/"):
            continue
        src = ROOT / rel
        if not src.exists():
            continue
        dst = STAGE / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    shutil.copy2(GEMFILE, STAGE / "Gemfile")


_cache = {}


def render(overrides, key):
    """Build the staged tree with these sources swapped in; fingerprint each page.

    `overrides` maps a repo path to its bytes at some commit, or to None when the
    file did not exist there.
    """
    if key in _cache:
        return _cache[key]
    saved = {}
    for rel, content in overrides.items():
        p = STAGE / rel
        saved[rel] = p.read_bytes() if p.exists() else None
        if content is None:
            if p.exists():
                p.unlink()
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content)
    out = STAGE / "_out"
    shutil.rmtree(out, ignore_errors=True)
    env = {**os.environ, "TZ": "UTC", "BUNDLE_GEMFILE": str(STAGE / "Gemfile")}
    # shutil.which, because on Windows `bundle` is a .bat and CreateProcess will
    # not resolve it from a bare name the way a shell does.
    bundle = shutil.which("bundle")
    if not bundle:
        sys.exit("bundle is not on PATH; this needs the same toolchain a local "
                 "build uses.")
    r = subprocess.run([bundle, "exec", "jekyll", "build", "--destination", str(out)],
                       cwd=STAGE, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        sys.exit(f"jekyll build failed for {key}:\n"
                 f"{r.stdout[-800:]}{r.stderr[-800:]}")
    result = {}
    for page in ["index.html"] + stories():
        f = out / built_path(page)
        result[page] = fingerprint(f.read_text(encoding="utf-8")) if f.exists() else None
    for rel, content in saved.items():
        p = STAGE / rel
        if content is None:
            if p.exists():
                p.unlink()
        else:
            p.write_bytes(content)
    _cache[key] = result
    return result


def fingerprint(html):
    """The page's own content and search-visible metadata, and nothing else.

    Runs of whitespace collapse to one space before hashing, because that is what
    a browser does with them. Kramdown carries the source's line breaks into the
    HTML it emits, so rewrapping a paragraph in a story moves the bytes without
    moving one pixel of what anyone reads -- and a check that fired on that would
    be teaching the owner to ignore it.

    The bounded cost: whitespace inside a `<pre>` IS significant, and this would
    not see a change that was only whitespace there. README's authoring contract
    does not support code blocks in story prose, so there is no `<pre>` on this
    site to miss one in. Adding support for one means revisiting this.
    """
    main = re.search(r"<main[^>]*>(.*?)</main>", html, re.S)
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    desc = re.search(r'<meta name="description" content="(.*?)"', html, re.S)
    parts = [main.group(1) if main else "", title.group(1) if title else "",
             desc.group(1) if desc else ""]
    text = re.sub(r"\s+", " ", "\x00".join(parts)).strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def at_commit(sha, paths):
    return {p: (git("show", f"{sha}:{p}", binary=True) or None) for p in paths}


def declared(page):
    text = (ROOT / page).read_text(encoding="utf-8")
    m = re.search(r"^last_modified_at:\s*(\S+)", text, re.M)
    return m.group(1).strip("\"'") if m else None


def is_published(page):
    if page == "index.html":
        return True
    return not re.search(r"^published:\s*false",
                         (ROOT / page).read_text(encoding="utf-8"), re.M)


def main():
    if not GEMFILE.exists():
        sys.exit(f"needs {GEMFILE} to build with; see temp/README.md")
    print("staging the current tree")
    stage_tree()
    today = datetime.date.today().isoformat()

    pages = ["index.html"] + [s for s in stories() if is_published(s)]
    src = sorted({p for page in pages for p in sources(page)})
    log = [c.split() for c in
           git("log", "--format=%H %ad", "--date=short", "--", *src).split("\n")
           if c.strip()]

    work = render({p: (ROOT / p).read_bytes() if (ROOT / p).exists() else None
                   for p in src}, "WORKTREE")
    head = render(at_commit(log[0][0], src), log[0][0])

    expected = {}
    for page in pages:
        if work[page] != head[page]:
            expected[page] = (today, "uncommitted")
            continue
        found = None
        for i, (sha, date) in enumerate(log):
            cur = render(at_commit(sha, src), sha)
            parent = git("rev-parse", f"{sha}^").strip()
            prev = render(at_commit(parent, src), parent) if parent else None
            if prev is None or prev.get(page) != cur.get(page):
                found = (date, sha[:7])
                break
        expected[page] = found or (log[-1][1], log[-1][0][:7])

    problems = []
    print("\npage                            declared     content last changed")
    for page in pages:
        when, sha = expected[page]
        says = declared(page)
        if says is None:
            state, why = "MISSING", f"{page}: no last_modified_at; set it to {when}"
        elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", says):
            state, why = "MALFORMED", f"{page}: {says!r} is not YYYY-MM-DD"
        elif says < when:
            state = "STALE"
            why = f"{page}: says {says}, content last changed {when} ({sha})"
        elif says > today:
            # The only over-declaration worth failing on. A date in the future is
            # not a claim anyone can act on, and a typed year is the realistic way
            # to get one.
            state = "FUTURE"
            why = (f"{page}: says {says}, which has not happened yet "
                   f"(today is {today})")
        elif says > when:
            # Ahead of the detected change but not in the future. Not a failure:
            # a story's `lesson` renders on the HOME page and not on its own, so
            # revising it moves that page's date and not this one, and an owner
            # who bumps both is being careful rather than wrong. Reported so the
            # difference is visible, since it is the surprising part of the model.
            state, why = "ahead", None
            print(f"  note: {page} declares {says}; its own page last changed "
                  f"{when} ({sha}). Harmless -- a field that renders only on "
                  f"another page will do this.")
        else:
            state, why = "ok", None
        if why:
            problems.append(why)
        print(f"  {page:30} {says or '-':12} {when} ({sha})   {state}")

    if problems:
        print()
        for p in problems:
            print(f"  {p}")
        raise SystemExit(f"\n{len(problems)} page(s) misreport when they last changed.")
    print("\nevery page's last_modified_at matches its last content change")


if __name__ == "__main__":
    main()

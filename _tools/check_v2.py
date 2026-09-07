"""Validate the built Soda Fountain site.

Usage: python _tools/check_v2.py temp/_site
"""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import sys

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
BUILT = (ROOT / (sys.argv[1] if len(sys.argv) > 1 else "temp/_site")).resolve()


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.hrefs = []
        self.sources = []
        self.h1 = 0
        self.main = 0
        self.footer = 0
        self.missing_alt = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a" and "href" in attrs:
            self.hrefs.append(attrs["href"])
        if tag in {"img", "script", "link"}:
            key = "href" if tag == "link" else "src"
            if key in attrs:
                self.sources.append(attrs[key])
        if tag == "img" and "srcset" in attrs:
            for candidate in attrs["srcset"].split(","):
                self.sources.append(candidate.strip().split()[0])
            assert attrs.get("sizes"), "responsive image missing sizes"
        if tag == "img" and "alt" not in attrs:
            self.missing_alt.append(attrs.get("src", "unknown"))
        if tag == "h1":
            self.h1 += 1
        if tag == "main":
            self.main += 1
        if tag == "footer":
            self.footer += 1


def target_for(page, url):
    parts = urlsplit(url)
    if parts.scheme or url.startswith(("mailto:", "tel:")):
        return None, parts.fragment
    target = BUILT / parts.path.lstrip("/") if parts.path.startswith("/") else page.parent / parts.path
    if not parts.path or parts.path.endswith("/"):
        target /= "index.html"
    return target.resolve(), parts.fragment


expected = {
    "404.html",
    "about/index.html",
    "index.html",
    "work/personal-finance-tools/index.html",
    "work/targeting-architecture/index.html",
    "work/testing-the-fix/index.html",
}
files = sorted(BUILT.rglob("*.html"))
actual = {path.relative_to(BUILT).as_posix() for path in files}
assert actual == expected, {"missing": expected - actual, "extra": actual - expected}

pages = {}
for path in files:
    page = Page()
    page.feed(path.read_text(encoding="utf-8"))
    relative = path.relative_to(BUILT).as_posix()
    assert len(page.ids) == len(set(page.ids)), f"duplicate id: {relative}"
    assert page.h1 == 1, f"expected one h1: {relative}"
    assert page.main == 1 and page.footer == 1, f"missing landmark: {relative}"
    assert not page.missing_alt, f"image without alt: {relative}"
    pages[relative] = page

for relative, page in pages.items():
    source = BUILT / relative
    for url in page.hrefs:
        target, fragment = target_for(source, url)
        if target is None:
            continue
        assert target.exists(), f"broken link in {relative}: {url}"
        if fragment and target.suffix.lower() == ".html":
            other = pages[target.relative_to(BUILT).as_posix()]
            assert fragment in other.ids, f"broken fragment in {relative}: {url}"
    for url in page.sources:
        target, _ = target_for(source, url)
        if target is not None:
            assert target.exists(), f"missing asset in {relative}: {url}"

assert not (BUILT / "archive").exists(), "archive was published"
for authoring in ("_originals", "_tools", "temp"):
    assert not (BUILT / authoring).exists(), f"{authoring} was published"
assert not list((BUILT / "assets/img/pints").rglob("*.png")), "PNG masters were published"
frames = list((BUILT / "assets/img/pints").rglob("frame-*.webp"))
assert len(frames) == 186, f"expected 186 tiered pint frames, found {len(frames)}"
lean_frames, rich_frames = [], []
for flavor in ("publisher", "evidence", "compound"):
    directory = BUILT / "assets/img/pints" / flavor
    lean = sorted(directory.glob("frame-*.webp"))
    motion = sorted((directory / "motion-600").glob("frame-*.webp"))
    stills = sorted((directory / "still-800").glob("frame-*.webp"))
    assert [p.name for p in lean] == [f"frame-{i:02d}.webp" for i in range(31)]
    assert [p.name for p in motion] == [f"frame-{i:02d}.webp" for i in range(1, 30)]
    assert [p.name for p in stills] == ["frame-00.webp", "frame-30.webp"]
    for paths, dimensions in ((lean, (400, 600)), (motion, (600, 900)), (stills, (800, 1200))):
        for path in paths:
            with Image.open(path) as image:
                assert image.size == dimensions, (path, image.size)
    lean_frames.extend(lean)
    rich_frames.extend(motion + stills)
assert sum(path.stat().st_size for path in lean_frames) < 800_000, "lean frame budget exceeded"
assert sum(path.stat().st_size for path in rich_frames) < 2_000_000, "retina frame budget exceeded"

with Image.open(BUILT / "assets/og/default.jpg") as image:
    assert image.size == (1200, 630), image.size

print(f"ok: {len(files)} pages, 93 lean + 93 retina pint frames, srcsets, routes, fragments, assets, landmarks, image alt, and share card")

"""Build the shared 1200x630 Soda Fountain social card.

Run without --write to verify the committed file. Use --write to replace it.
"""
from io import BytesIO
from pathlib import Path
import argparse

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "_originals/site-v2/soda-fountain-family-front.png"
TARGET = ROOT / "assets/og/default.jpg"


def render():
    source = Image.open(SOURCE).convert("RGB")
    if source.size != (1200, 600):
        raise SystemExit(f"expected a 1200x600 source, got {source.size}")
    card = Image.new("RGB", (1200, 630), "#f8edd9")
    card.paste(source, (0, 30))
    output = BytesIO()
    card.save(output, format="JPEG", quality=88, optimize=True, progressive=True)
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = render()
    if args.write:
        TARGET.write_bytes(result)
        print(f"wrote {TARGET} ({len(result)} bytes)")
        return
    if not TARGET.exists() or TARGET.read_bytes() != result:
        raise SystemExit("share card differs; inspect it, then run with --write")
    print(f"share card matches ({len(result)} bytes)")


if __name__ == "__main__":
    main()

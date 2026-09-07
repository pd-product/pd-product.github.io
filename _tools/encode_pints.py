"""Encode both delivery tiers from approved native 800x1200 studio masters.

Usage: python _tools/encode_pints.py PATH_TO_MASTERS
The source directory must contain publisher/, evidence/, compound/ with 31 PNGs
each. PNGs and Blender scenes are local authoring inputs, never site assets.
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def encode(masters):
    report = {"masters": "Native 800x1200, Cycles 64 samples, seed 37", "files": []}
    for flavor in ("publisher", "evidence", "compound"):
        for frame in range(31):
            source = masters / flavor / f"frame-{frame:02d}.png"
            endpoint = frame in (0, 30)
            width, quality = (800, 92) if endpoint else (600, 85)
            target = ROOT / "assets/img/pints" / flavor / ("still-800" if endpoint else "motion-600") / f"frame-{frame:02d}.webp"
            with Image.open(source) as image:
                assert image.size == (800, 1200), (source, image.size)
                image = image.convert("RGB")
                lean = ROOT / "assets/img/pints" / flavor / f"frame-{frame:02d}.webp"
                lean_quality = 90 if endpoint else 75
                image.resize((400, 600), Image.Resampling.LANCZOS).save(lean, "WEBP", quality=lean_quality, method=6)
                report["files"].append(dict(path=lean.relative_to(ROOT).as_posix(), width=400,
                                            quality=lean_quality, bytes=lean.stat().st_size,
                                            source_sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
                if not endpoint:
                    image = image.resize((600, 900), Image.Resampling.LANCZOS)
                target.parent.mkdir(exist_ok=True, parents=True)
                image.save(target, "WEBP", quality=quality, method=6)
            report["files"].append(dict(path=target.relative_to(ROOT).as_posix(), width=width,
                                        quality=quality, bytes=target.stat().st_size,
                                        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
    report["total_bytes"] = sum(row["bytes"] for row in report["files"])
    report["lean_bytes"] = sum(row["bytes"] for row in report["files"] if row["width"] == 400)
    report["retina_bytes"] = report["total_bytes"] - report["lean_bytes"]
    (masters.parent / "delivery-encoding.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Encoded {len(report['files'])} responsive files: {report['total_bytes']:,} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("masters", type=Path)
    args = parser.parse_args()
    encode(args.masters.resolve())

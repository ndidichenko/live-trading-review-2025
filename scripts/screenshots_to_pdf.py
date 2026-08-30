"""Bundle a folder of KCEX order-history screenshots into one PDF.

Usage:  python3 scripts/screenshots_to_pdf.py <src_dir> <out.pdf> [max_width_px]

Pages are ordered by filename, which for macOS screenshots is chronological
(the capture timestamp is in the name). Output stays in private/ and is never
committed.
"""
import sys
from pathlib import Path

from PIL import Image

MAX_W_DEFAULT = 2200


def main(src: Path, out: Path, max_w: int = MAX_W_DEFAULT) -> None:
    files = sorted(p for p in src.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"})
    if not files:
        raise SystemExit(f"no images in {src}")

    pages = []
    for p in files:
        im = Image.open(p).convert("RGB")
        if im.width > max_w:
            im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
        pages.append(im)

    out.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(out, save_all=True, append_images=pages[1:], resolution=150.0, quality=88)
    print(f"{out}  <-  {len(pages)} pages from {src.name}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        raise SystemExit(__doc__)
    main(Path(a[0]), Path(a[1]), int(a[2]) if len(a) > 2 else MAX_W_DEFAULT)

"""Page rendering with pdftoppm, and crops with Pillow."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image

from .sources import DATA, scan_path


class RenderError(Exception):
    pass


def page_png(key: str, page: int, dpi: int = 200, root: Path = DATA) -> Path:
    """Render one page (1-based) of a county's scan to data/pages/<key>/pNN-<dpi>.png; cached."""
    out = root / "pages" / key / f"p{page:02d}-{dpi}.png"
    if out.exists():
        return out
    if shutil.which("pdftoppm") is None:
        raise RenderError("pdftoppm is not installed; install poppler-utils (apt install poppler-utils)")
    pdf = scan_path(key, root)
    if not pdf.exists():
        raise RenderError(f"{pdf} is missing; run `crossfoot fetch --county {key}` first")
    out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["pdftoppm", "-png", "-r", str(dpi), "-f", str(page), "-l", str(page),
                        "-singlefile", str(pdf), str(out.with_suffix(""))],
                       capture_output=True, text=True)
    if r.returncode != 0 or not out.exists():
        raise RenderError(f"pdftoppm failed for {pdf} page {page}: {r.stderr.strip()}")
    return out


def crop(png: Path, box: tuple[int, int, int, int], dest: Path) -> Path:
    """Crop (x0, y0, x1, y1) out of an image and save it."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(png) as im:
        im.crop(box).save(dest)
    return dest
